#!/usr/bin/env python3
"""Arduino / Teensy STM-controller emulator.

Speaks the *exact* wire protocol the real firmware speaks
(``dans-software-port/teensy/arduinosrc/main/``) so the unmodified PC software
(``pc/qtpanda``) can drive it with no code changes:

  * Commands are fixed 4-char tags (``CMD_LENGTH = 4``) followed by
    ``Serial.parseInt()`` integer arguments, with NO line terminator.
  * ``GSTS`` -> one CSV status line, exactly as the firmware's ``to_char``:
        "%d,%d,%d,%d,%d,%d,%d,%d,%d,%lu"
        bias,dac_z,dac_x,dac_y,adc,steps,is_approaching,is_const_current,
        is_scanning,time_millis   (+ CRLF, matching Serial.println)

Transport is a plain TCP socket (the docker-compose PC container bridges it to
a virtual serial PTY with socat, so ``serial.Serial('/dev/…')`` just works).

The value of the emulator is the ADC signal model: it reproduces the *stability*
phenomenon under study — baseline electronics noise, steady tunneling, linear
thermal-style drift, and in/out-of-zone wander — so the Stability tab, the raw
CSV logging, and the live drift/jitter readout can be exercised end to end.

Configure via environment variables (all optional):
  STM_PORT           TCP port to listen on            (default 9000)
  STM_MODE           noise | tunnel | drift | inout   (default drift)
  STM_SETPOINT_PA    tunneling current at zero gap    (default 300  pA)
  STM_DRIFT_PM_S     linear gap drift velocity        (default 40   pm/s, + = opening)
  STM_JITTER_PM      RMS mechanical z-jitter          (default 30   pm)
  STM_INOUT_AMP_PM   sinusoidal in/out gap amplitude  (default 250  pm)
  STM_PERIOD_S       period of the in/out wander      (default 25   s)
  STM_NOISE_OFFSET   baseline ADC DC offset (counts)  (default -8)
  STM_NOISE_COUNTS   baseline ADC noise RMS (counts)  (default 11)
  STM_RATE_HZ        status generation cadence hint   (default 30)
  STM_SEED           RNG seed                          (default 1)
"""

import os
import re
import socket
import struct
import time

import numpy as np

# ADC <-> current: adc_to_amp(adc) = adc/32768 * 10.24/100e6  (see stm_control.py)
# => 1 count = 3.125 pA ; amp -> counts = amp / (10.24/100e6) * 32768.
COUNTS_PER_AMP = 32768.0 / (10.24 / 100e6)          # ~3.2e11 counts / A
KAPPA_PER_M = 0.5123e10 * (4.0 ** 0.5)              # phi = 4 eV -> ~1.02e10 /m


def env_f(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return float(default)


def env_i(name, default):
    try:
        return int(float(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return int(default)


class Emulator:
    # How many integer args each command consumes (0 if none / unknown).
    ARGC = {
        "GSTS": 0, "RSET": 0, "STOP": 0, "CCOF": 0, "IVGE": 0, "DIGE": 0,
        "ADCR": 0, "MTOF": 0, "ENGA": 0, "RTRC": 0, "HALT": 0, "TEST": 0,
        "BIAS": 1, "DACX": 1, "DACY": 1, "DACZ": 1, "MTMV": 1, "MTDR": 1,
        "CCON": 1, "SETP": 1, "SCSZ": 1, "IPLN": 1, "LRAT": 1, "XOFS": 1,
        "YOFS": 1, "KPGA": 1, "KIGA": 1, "SETD": 1,
        "APRH": 2,
        "IVME": 3, "DIME": 3, "PIDS": 3,
        "NOIS": 4, "SETL": 4, "LIDV": 4,
        "SCST": 7,
        "GSPC": 10,
    }

    def __init__(self):
        self.mode = os.environ.get("STM_MODE", "drift").strip().lower()
        self.setpoint_pa = env_f("STM_SETPOINT_PA", 300.0)
        self.drift_pm_s = env_f("STM_DRIFT_PM_S", 40.0)
        self.jitter_pm = env_f("STM_JITTER_PM", 30.0)
        self.inout_amp_pm = env_f("STM_INOUT_AMP_PM", 250.0)
        self.period_s = max(env_f("STM_PERIOD_S", 25.0), 1e-3)
        self.noise_offset = env_f("STM_NOISE_OFFSET", -8.0)
        self.noise_counts = env_f("STM_NOISE_COUNTS", 11.0)
        self.rng = np.random.default_rng(env_i("STM_SEED", 1))

        # Mutable controller state (mirrors the firmware status struct).
        self.bias = 32768
        self.dac_x = 32768
        self.dac_y = 32768
        self.dac_z = 32768
        self.steps = 0
        self.is_approaching = False
        self.is_const_current = False
        self.is_scanning = False
        self.setpoint_adc = int(self.setpoint_pa / 3.125)
        self.iv_range = (0, 0, 1)
        self.didz_range = (0, 0, 1)
        self.t0 = time.monotonic()

    # ---- signal model ------------------------------------------------------
    def elapsed_ms(self):
        return int((time.monotonic() - self.t0) * 1000)

    def current_adc(self):
        """Return the emulated ADC reading (int counts) for this instant."""
        # Baseline electronics noise is always present.
        base = self.rng.normal(self.noise_offset, self.noise_counts)
        if self.mode == "noise":
            return int(np.clip(base, -32768, 32767))

        t = (time.monotonic() - self.t0)
        z_pm = 0.0
        if self.mode in ("drift", "inout"):
            z_pm += self.drift_pm_s * t
        if self.mode == "inout":
            z_pm += self.inout_amp_pm * np.sin(2.0 * np.pi * t / self.period_s)
        # A little of the fine-Z DAC leaks into the gap (1 count ~ 0.5 pm here),
        # so nudging DACZ in the GUI visibly shifts the distribution.
        z_pm += (self.dac_z - 32768) * 0.5
        # Const-current feedback (CCON) suppresses drift/wander, leaving jitter.
        if self.is_const_current:
            z_pm = (self.dac_z - 32768) * 0.5
        z_pm += self.rng.normal(0.0, self.jitter_pm)

        amp = self.setpoint_pa * 1e-12 * np.exp(-2.0 * KAPPA_PER_M * z_pm * 1e-12)
        adc = amp * COUNTS_PER_AMP + base
        return int(np.clip(adc, -32768, 32767))

    def status_line(self):
        return "{},{},{},{},{},{},{},{},{},{}\r\n".format(
            self.bias, self.dac_z, self.dac_x, self.dac_y, self.current_adc(),
            self.steps, int(self.is_approaching), int(self.is_const_current),
            int(self.is_scanning), self.elapsed_ms(),
        ).encode()

    # ---- command handling --------------------------------------------------
    def handle(self, cmd, args, sock):
        """Apply a command; write any reply straight to the socket."""
        if cmd == "GSTS":
            sock.sendall(self.status_line())
        elif cmd == "RSET":
            self.bias = self.dac_x = self.dac_y = self.dac_z = 32768
            self.steps = 0
            self.is_approaching = self.is_const_current = self.is_scanning = False
            self.t0 = time.monotonic()
        elif cmd == "BIAS":
            self.bias = args[0]
        elif cmd == "DACX":
            self.dac_x = args[0]
        elif cmd == "DACY":
            self.dac_y = args[0]
        elif cmd == "DACZ":
            self.dac_z = args[0]
        elif cmd == "MTMV":
            self.steps += args[0]
        elif cmd == "APRH":
            # Pretend to approach: land near the target, mark engaged.
            self.is_approaching = False
            self.steps += 100
            self.t0 = time.monotonic()
        elif cmd in ("CCON",):
            self.is_const_current = True
            if args:
                self.setpoint_adc = args[0]
        elif cmd == "CCOF":
            self.is_const_current = False
        elif cmd == "STOP":
            self.is_approaching = self.is_const_current = self.is_scanning = False
        elif cmd == "ADCR":
            sock.sendall(f"{self.current_adc()}\r\n".encode())
        elif cmd == "ENGA":
            sock.sendall(b"ENGA OK\r\n")
        elif cmd == "IVME":
            self.iv_range = (args[0], args[1], max(args[2], 1))
        elif cmd == "IVGE":
            self.send_iv(sock)
        elif cmd == "DIME":
            self.didz_range = (args[0], args[1], max(args[2], 1))
        elif cmd == "DIGE":
            self.send_didz(sock)
        elif cmd == "NOIS":
            self.send_line_scan(sock, args[0], args[1], kind="N")
        elif cmd == "SCST":
            self.send_scan(sock, args[2], args[5])
        elif cmd == "GSPC":
            self.send_grid(sock, args[2], args[5], args[8], args[9])
        # All other commands (SETL, PIDS, SETP, KPGA, …) just no-op / store.

    # ---- bulk-data replies (best-effort, keep the GUI from hanging) --------
    def _row_vals(self, x_i, n, kind):
        xs = np.arange(n)
        if kind == "N":
            vals = self.rng.normal(self.noise_offset, self.noise_counts, n)
        else:  # a smooth image: gradient + a gaussian bump + noise
            bump = 4000.0 * np.exp(-((xs - n / 2) ** 2 + (x_i - n / 2) ** 2) / (2 * (n / 6) ** 2))
            vals = 1000.0 + 20.0 * xs + bump + self.rng.normal(0, 60, n)
        return np.clip(vals, -32768, 32767).astype(int)

    def send_scan(self, sock, xres, yres):
        xres, yres = max(int(xres), 1), max(int(yres), 1)
        for x_i in range(xres):
            a = self._row_vals(x_i, yres, "A")
            z = self._row_vals(x_i, yres, "Z")
            sock.sendall(("A,{}," + ",".join(map(str, a)) + "\r\n").format(x_i).encode())
            sock.sendall(("Z,{}," + ",".join(map(str, z)) + "\r\n").format(x_i).encode())
        sock.sendall(b"D\r\n")

    def send_line_scan(self, sock, xres, yres, kind="N"):
        xres, yres = max(int(xres), 1), max(int(yres), 1)
        for x_i in range(xres):
            v = self._row_vals(x_i, yres, kind)
            sock.sendall((kind + ",{}," + ",".join(map(str, v)) + "\r\n").format(x_i).encode())
        sock.sendall(b"D\r\n")

    def send_iv(self, sock):
        start, end, step = self.iv_range
        step = step if step else 1
        biases = list(range(start, end, step)) or [start]
        n = len(biases)
        out = []
        for b in biases:
            cur = int(2000 * np.tanh(b / 20000.0) + self.rng.normal(0, 30))
            didv = int(200 + self.rng.normal(0, 20))
            out += [b, cur, didv]
        sock.sendall(("IVD,{}," + ",".join(map(str, out)) + "\r\n").format(n).encode())

    def send_didz(self, sock):
        start, end, step = self.didz_range
        step = step if step else 1
        zs = list(range(start, end, step)) or [start]
        out = []
        for z in zs:
            out += [z, int(self.setpoint_adc * np.exp(-z / 5000.0))]
        sock.sendall(("DI," + ",".join(map(str, out)) + "\r\n").encode())

    def send_grid(self, sock, xres, yres, pts, mode):
        xres, yres, pts = max(int(xres), 1), max(int(yres), 1), max(int(pts), 1)
        for x_i in range(xres):
            for y_i in range(yres):
                spec = np.clip(
                    1000 + 30 * np.arange(pts) + self.rng.normal(0, 50, pts),
                    0, 65535).astype("<u2")
                header = b"PX" + struct.pack("<HHHB", x_i, y_i, pts, int(mode) & 0xFF)
                sock.sendall(header + spec.tobytes())


# ---- byte-stream command parser (parseInt semantics, no terminators) -------
_INT_RE = re.compile(rb"-?\d+")


def serve(emu, port):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", port))
    srv.listen(1)
    print(f"[emulator] mode={emu.mode} setpoint={emu.setpoint_pa}pA "
          f"drift={emu.drift_pm_s}pm/s jitter={emu.jitter_pm}pm "
          f"listening on :{port}", flush=True)

    while True:
        conn, addr = srv.accept()
        print(f"[emulator] client connected: {addr}", flush=True)
        conn.settimeout(0.05)
        buf = b""
        stall_deadline = None   # give up waiting for args after a short spell
        try:
            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                except socket.timeout:
                    pass

                progressed = True
                while progressed:
                    progressed = False
                    # Re-align on every pass: skip whitespace before the tag.
                    buf = buf.lstrip(b" \r\n\t")
                    if len(buf) < 4:
                        break
                    cmd = buf[:4].decode("ascii", "ignore")
                    argc = emu.ARGC.get(cmd, 0)
                    if argc == 0:
                        buf = buf[4:]
                        emu.handle(cmd, [], conn)
                        stall_deadline = None
                        progressed = True
                        continue

                    ints = list(_INT_RE.finditer(buf, 4))
                    if len(ints) >= argc:
                        args = [int(m.group()) for m in ints[:argc]]
                        buf = buf[ints[argc - 1].end():]
                        emu.handle(cmd, args, conn)
                        stall_deadline = None
                        progressed = True
                        continue

                    # Not enough integer args yet. Normally more bytes are just
                    # in flight; wait one cycle. But don't wedge forever on a
                    # malformed command (e.g. a literal "MTMV {steps}").
                    if stall_deadline is None:
                        stall_deadline = time.monotonic() + 0.5
                    elif time.monotonic() > stall_deadline:
                        args = [int(m.group()) for m in ints] + [0] * (argc - len(ints))
                        buf = buf[ints[-1].end():] if ints else buf[4:]
                        emu.handle(cmd, args, conn)
                        stall_deadline = None
                        progressed = True
                    # else: break out and recv more bytes.
        except (ConnectionResetError, BrokenPipeError, OSError) as e:
            print(f"[emulator] client error: {e}", flush=True)
        finally:
            conn.close()
            print("[emulator] client disconnected", flush=True)


if __name__ == "__main__":
    serve(Emulator(), env_i("STM_PORT", 9000))
