import serial

import numpy as np
from dataclasses import dataclass
from collections import deque
import os
import time
import logging

import session_journal
import scst_logger

logger = logging.getLogger("stm")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter(
    "%(asctime)s  %(message)s",
    datefmt="%H:%M:%S"
)

# Persistent file log so port-open attempts (and everything else this module
# logs) survive past the GUI's txtLog pane -- checkable with no session
# running and no one watching the screen (e.g. "did it even try COM3?").
os.makedirs("logs", exist_ok=True)
_file_handler = logging.FileHandler(os.path.join("logs", "stm.log"))
_file_handler.setFormatter(formatter)
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    logger.addHandler(_file_handler)

@dataclass
class STM_Status:
    bias: int = 0
    dac_z: int = 0
    dac_x: int = 0
    dac_y: int = 0
    adc: int = 0
    steps: int = 0
    is_approaching: bool = False
    is_const_current: bool = False
    is_scanning: bool = False
    time_millis: int = 0

    @staticmethod
    def from_list(values):
        return STM_Status(bias=values[0],
                          dac_z=values[1],
                          dac_x=values[2],
                          dac_y=values[3],
                          adc=values[4],
                          steps=values[5],
                          is_approaching=bool(values[6]),
                          is_const_current=bool(values[7]),
                          is_scanning=bool(values[8]),
                          time_millis=values[9])

    # Preamp gain multiplier (operator-set: 1X or 5X, etc).  At NX gain the
    # same tunneling current yields N times the ADC counts, so dividing by
    # the gain recovers true amps.  Class attribute so every static
    # adc_to_amp() call across the app tracks the current setting.
    preamp_gain = 1.0

    @staticmethod
    def adc_to_amp(adc: int):
        return 1.0 * adc / 32768 * 10.24 / 100e6 / STM_Status.preamp_gain

    @staticmethod
    def dac_to_dacz_volts(dac: int):
        return 1.0 * (dac - 32768) / 32768 * 10.0 / 2.0

    @staticmethod
    def dac_to_dacx_volts(dac: int):
        return 1.0 * (dac - 32768) / 32768 * 10.0 / 2.0

    @staticmethod
    def dac_to_dacy_volts(dac: int):
        return 1.0 * (dac - 32768) / 32768 * 10.0 / 2.0

    @staticmethod
    def dac_to_bias_volts(dac: int):
        return -1.0 * (dac - 32768) / 32768 * 3.0

    def to_string(self):
        return """STM Status:
Bias: {} 
Z: {} 
X: {} 
Y: {} 
ADC: {} 
STEPS: {}
Appoaching: {} 
ConstCurrent: {} 
Scan: {}  
Time: {}""".format(self.bias, self.dac_z, self.dac_x, self.dac_y, self.adc, self.steps, self.is_approaching,  self.is_const_current, self.is_scanning, self.time_millis)


class STM(object):
    def __init__(self, device=None):
        self.is_opened = False
        self.busy = False
        # True once a "STAT:"-tagged GSTS reply has been seen.  The tag is a
        # fingerprint of the pre-Phase-3 firmware (e077127 era): that build
        # prefixes status rows and has NO continuous-scan protocol (no RUN
        # handler, no binary 'L' frames), so a RUN sent to it is silently
        # ignored.  Current firmware prints the bare CSV.  Undocumented on
        # the wire — established by probing a flashed board (2026-07-02).
        self.firmware_tagged_status = False
        if device:
            self.open(device)

        self.status = STM_Status()
        self.hist_length = 1000
        self.history = deque()
        self.scan_adc = None
        self.scan_dacz = None
        self.scan_noise = None

        self.scan_config = [0, 100, 10, 0, 100, 10]
        self.scan_adc = np.ones([512, 512], dtype=np.float32)
        self.scan_dacz = np.ones([512, 512], dtype=np.float32)
        self.scan_noise = np.ones([512, 512], dtype=np.float32)

    def open(self, device):
        logger.info(f"OPEN attempt  device={device}")
        try:
            if device == "EMU":
                # Opt-in software firmware emulator (no hardware). Dev/test
                # aid living beside the code in ./emulator/ (repo-excluded);
                # imported lazily so shippable code never depends on it and
                # works unchanged if that folder is absent.
                import sys
                _emu_dir = os.path.normpath(os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "emulator"))
                if _emu_dir not in sys.path:
                    sys.path.insert(0, _emu_dir)
                try:
                    from firmware_emulator import EmulatedSerial
                except ImportError as exc:
                    raise RuntimeError(
                        "device 'EMU' requested but the emulator harness is not "
                        "available (dans-software-port/emulator/ is excluded from "
                        "the public repo)") from exc
                self.stm_serial = EmulatedSerial(timeout=1)
            elif "://" in device:
                # pyserial URL handler, e.g. socket://127.0.0.1:9000 — how the
                # docker software-mockup emulator is reached from the host
                # (its compose file exposes TCP 9000 for exactly this).
                self.stm_serial = serial.serial_for_url(device, timeout=1)
            else:
                self.stm_serial = serial.Serial(device, 921600, timeout=1) # 921600 # 115200
        except Exception as e:
            logger.error(f"OPEN failed  device={device}  ({e})")
            raise
        self.is_opened = True
        # Purge stale RX bytes (e.g. binary debris from a previous session's
        # crash mid-stream): garbage here made the STRM startup watchdog
        # falsely conclude "old firmware" and lock the whole session to the
        # 9 Hz poll (bench 2026-07-15).
        try:
            time.sleep(0.2)
            self.stm_serial.reset_input_buffer()
        except Exception:
            pass
        logger.info(f"OPEN ok  device={device}")

    def get_status(self):
        if self.busy:
            return
        if self.is_opened:
            if self.busy:
                print('busy')
                return self.history[-1]
            try:
                self.send_cmd('GSTS')
                status_str = self.stm_serial.readline().decode(errors='ignore').strip()
                #logger.info(f"RX  {status_str}")

                # Firmware sometimes tags status replies with a type prefix,
                # e.g. "STAT:0,0,0,0,-19,...". Strip any leading "TAG:" so
                # we parse just the CSV; plain CSV is left unchanged.  The
                # STAT tag also fingerprints the old-protocol firmware (see
                # __init__) — but only LATCH that fingerprint after the line
                # validates as a genuine full status row.  Latching on any
                # colon-containing garbage (a mid-frame fragment, an ASCII
                # log line) permanently and falsely locked out continuous
                # scan on new firmware (bench 2026-07-14).
                tagged = False
                if ':' in status_str:
                    prefix, status_str = status_str.rsplit(':', 1)
                    tagged = prefix.strip().upper() == "STAT"

                status_value = [int(x) for x in status_str.split(',') if x != '']

                # Need the full 10-field status; anything shorter is a
                # partial/garbled line (e.g. a log message) -> ignore it.
                if len(status_value) < 10:
                    raise ValueError(f"unparseable status: {status_str!r}")

                if tagged:
                    self.firmware_tagged_status = True

                self.status = STM_Status.from_list(status_value)
            except Exception as e:
                # No parseable reply this cycle; keep the last known status
                # instead of crashing or spamming the console.
                # ascii-safe: e may embed raw serial garbage; printing a
                # non-cp1252 char crashed the whole GUI (bench 2026-07-15).
                print(f"[STM] no response ({e})"
                      .encode("ascii", "replace").decode())
                return self.history[-1] if self.history else self.status
        else:
            self.status = STM_Status()
        self.history.append(self.status)
        if len(self.history) > self.hist_length:
            self.history.popleft()

        return self.status

    def reset(self):
        self.send_cmd('RSET')
        self.clear()

    def clear(self):
        self.history = deque()

    def send_cmd(self, cmd, src="human"):
        # Attribution override: the copilot bridge drives the real GUI
        # widgets (synthetic clicks), so commands arrive here through the
        # human handlers with their default src.  While src_override is set
        # it wins, keeping agent-initiated clicks labeled src="agent".
        src = getattr(self, "src_override", None) or src
        if self.is_opened:
            self.stm_serial.write(cmd.encode())
            #logger.info(f"TX  {cmd}")
            # Journal every command at this single choke point (no-op unless a
            # session is active).  Skip the ~9 Hz GSTS status poll — its reply
            # is captured as a 'sample' record, so logging the poll too would
            # just double the volume with no added information.
            if not cmd.strip().upper().startswith("GSTS"):
                session_journal.log_command(cmd, src=src)

    def move_motor(self, steps):
        self.send_cmd(f'MTMV {steps}')

    def approach(self, target_dac, steps):
        self.send_cmd(f'APRH {target_dac} {steps}')

    def stop(self):
        self.send_cmd('STOP')


    def start_noise_scan(self,xres,yres,samples,uS):
        print("[CMD] Noise Scan")
        print(f"      xres = {xres}")
        print(f"      yres  = {yres}")
        print(f"      samples  = {samples}")
        print(f"      uS  = {uS}")
        self.busy = True
        log_path = scst_logger.start({
            "op": "noise_scan", "x_res": xres, "y_res": yres,
            "samples": samples, "settle_uS": uS,
            "bias_dac": self.status.bias, "dac_z": self.status.dac_z,
            "adc_at_start": self.status.adc, "steps": self.status.steps,
        })
        session_journal.record("noise_scan_start", path=log_path)
        self.send_cmd(f'NOIS {xres} {yres} {samples} {uS}')
        self.scan_noise = np.ones([xres, yres], dtype=np.float32)
        self.scan_config = [0, 65535, xres, 0, 65535, yres]

        current_line = ''

        def _process_full_line(full_line):
            logger.info(f"RX  {full_line}")
            # Log BEFORE parsing: the verbatim record survives even rows the
            # parser rejects (same log-before-draw principle as frame_logger).
            scst_logger.log_line(full_line)
            data = full_line.split(',')
            data_type = data[0]
            if data_type == "N":
                x_i = int(data[1])
                data_content = data[2:]
                data_content = [int(x) for x in data_content]
                self.scan_noise[x_i, :] = data_content
            if data_type == "D":
                return True
            return False

        try:
            while (True):
                read_number = self.stm_serial.inWaiting()
                if (read_number == 0):
                    continue
                read_str = self.stm_serial.read(read_number).decode()
                if "\n" in read_str:
                    split_lines = read_str.split("\n")
                    for data_line in split_lines:
                        if len(data_line) == 0:
                            continue
                        current_line += data_line
                        if current_line[-1] == "\r":  # We have a full line
                            _process_full_line(current_line)
                            current_line = ''
                else:
                    current_line += read_str
                # We have a full line
                if current_line and current_line[-1] == "\r":
                    #_process_full_line(data_line)
                    _process_full_line(current_line)
                    current_line = ''
                if "D" in read_str:
                    break
        finally:
            # Same busy-latch + log-finalize guarantees as start_scan.
            self.busy = False
            done = scst_logger.stop()
            if done:
                session_journal.record("noise_scan_stop", path=done)
        print("Noise Scan Complete")
        return

    def measure_iv_curve(self, dac_start, dac_end, dac_step):
        self.send_cmd(f'IVME {dac_start} {dac_end} {dac_step}')
        # Wait for 0.1s for the STM to response
        time.sleep(2)
        return self.get_iv_curve()

    def get_iv_curve(self):
        bias = []
        current = []
        didv = []

        if self.is_opened:
            self.busy = True
            time.sleep(1)

            log_path = scst_logger.start({
                "op": "iv_curve",
                "bias_dac": self.status.bias, "dac_z": self.status.dac_z,
                "adc_at_start": self.status.adc, "steps": self.status.steps,
            })
            session_journal.record("iv_curve_start", path=log_path)
            self.send_cmd('IVGE')   # or whatever command triggers send_iv_didv_curve()

            data_str = self.stm_serial.readline().decode().strip()
            logger.info(f"RX  {data_str}")
            scst_logger.log_line(data_str)
            done = scst_logger.stop()
            if done:
                session_journal.record("iv_curve_stop", path=done)

            data = data_str.split(',')

            if data[0] == "IVD":
                try:
                    N = int(data[1])
                    values = [int(x) for x in data[2:]]

                    # Expect 3 values per point
                    if len(values) == 3 * N:
                        bias = np.array(values[0::3])
                        current = np.array(values[1::3])
                        didv = np.array(values[2::3])
                    else:
                        print("Unexpected IVD data length")

                except Exception as e:
                    print("IVD parse error:", e)

        self.busy = False

        print("Bias:", bias)
        print("Current:", current)
        print("dIdV:", didv)

        return bias, current, didv

    def measure_dIdZ_curve(self, dac_start, dac_end, dac_step):
        self.send_cmd(f'DIME {dac_start} {dac_end} {dac_step}')
        # Wait for 0.1s for the STM to response
        time.sleep(2)
        return self.get_dIdZ_curve()

    def get_dIdZ_curve(self):
        dIdZ_curve_values = [0, 0]
        if self.is_opened:
            self.busy = True
            time.sleep(1)
            log_path = scst_logger.start({
                "op": "didz_curve",
                "bias_dac": self.status.bias, "dac_z": self.status.dac_z,
                "adc_at_start": self.status.adc, "steps": self.status.steps,
            })
            session_journal.record("didz_curve_start", path=log_path)
            self.send_cmd('DIGE')
            data_str = self.stm_serial.readline().decode()
            logger.info(f"RX  {data_str}")
            scst_logger.log_line(data_str)
            done = scst_logger.stop()
            if done:
                session_journal.record("didz_curve_stop", path=done)
            data = data_str.split(',')
            if data[0] == "DI":
                dIdZ_curve_values = [int(x) for x in data[1:]]
        self.busy = False
        print(dIdZ_curve_values)
        return dIdZ_curve_values

    def set_bias(self, value):
        self.send_cmd(f"BIAS {value}")

    def set_dacz(self, value):
        self.send_cmd(f"DACZ {value}")

    def set_dacx(self, value):
        self.send_cmd(f"DACX {value}")

    def set_dacy(self, value):
        self.send_cmd(f"DACY {value}")

    def turn_on_const_current(self, target_adc):
        self.send_cmd(f"CCON {target_adc}")

    def turn_off_const_current(self):
        self.send_cmd(f"CCOF")

    def set_pid(self, Kp, Ki, Kd):
        self.send_cmd(f"PIDS {Kp} {Ki} {Kd}")

    def set_settle(self, x,y,z,bias):
        self.send_cmd(f"SETL {x} {y} {z} {bias}")

    def start_scan(self, x_start, x_end, x_resolution, y_start, y_end, y_resolution, sample_number):
        self.busy = True
        try:
            self._start_scan_inner(x_start, x_end, x_resolution,
                                   y_start, y_end, y_resolution,
                                   sample_number)
        finally:
            # A parse error must never leave busy latched True — that
            # silently halts the GSTS poll and every live display (bench
            # 2026-07-15: GUI 'nothing moving' after a corrupted scan).
            self.busy = False
            # Finalize the verbatim log whatever happened — a crash
            # mid-scan still leaves a valid partial record on disk.
            done = scst_logger.stop()
            if done:
                session_journal.record("scst_scan_stop", path=done)

    def _start_scan_inner(self, x_start, x_end, x_resolution, y_start,
                          y_end, y_resolution, sample_number):
        self.scan_config = [x_start, x_end,
                            x_resolution, y_start, y_end, y_resolution]
        # Verbatim log of every data row + full machine-state sidecar, so
        # legacy scans are reconstructible offline like continuous frames
        # (record-everything posture; gap closed 2026-07-15).
        log_path = scst_logger.start({
            "x_start": x_start, "x_end": x_end, "x_res": x_resolution,
            "y_start": y_start, "y_end": y_end, "y_res": y_resolution,
            "samples_per_pixel": sample_number,
            "bias_dac": self.status.bias,
            "dac_z": self.status.dac_z,
            "adc_at_start": self.status.adc,
            "steps": self.status.steps,
            "is_const_current": self.status.is_const_current,
        })
        session_journal.record("scst_scan_start", path=log_path)
        self.send_cmd(
            f"SCST {x_start} {x_end} {x_resolution} {y_start} {y_end} {y_resolution} {sample_number}")

        self.scan_adc = np.ones([x_resolution, y_resolution], dtype=np.float32)
        self.scan_dacz = np.ones([x_resolution, y_resolution], dtype=np.float32)

        current_line = ''

        def _process_full_line(full_line):
            logger.info(f"RX  {full_line}")
            # Log BEFORE parsing: the verbatim record survives even rows the
            # parser rejects (same log-before-draw principle as frame_logger).
            scst_logger.log_line(full_line)
            data = full_line.split(',')
            data_type = data[0]
            if data_type == "A":
                x_i = int(data[1])
                data_content = data[2:]
                data_content = [int(x) for x in data_content]
                self.scan_adc[x_i, :] = data_content
            if data_type == "Z":
                x_i = int(data[1])
                data_content = data[2:]
                data_content = [int(x) for x in data_content]
                self.scan_dacz[x_i, :] = data_content
            if data_type == "D":
                return True
            return False

        while (True):
            read_number = self.stm_serial.inWaiting()
            if (read_number == 0):
                continue
            read_str = self.stm_serial.read(read_number).decode()
            if "\n" in read_str:
                split_lines = read_str.split("\n")
                for data_line in split_lines:
                    if len(data_line) == 0:
                        continue
                    current_line += data_line
                    if current_line[-1] == "\r":  # We have a full line
                        _process_full_line(current_line)
                        current_line = ''
            else:
                current_line += read_str
            # We have a full line
            if current_line and current_line[-1] == "\r":
                #_process_full_line(data_line)
                _process_full_line(current_line)
                current_line = ''
            if "D" in read_str:
                break
        self.busy = False
        print("Scan Complete")
        return

    def parse_ascii_line(self, line: str) -> dict:
        """
        Parse one ASCII response line from the firmware.

        Returns a dict with at minimum key 'type', which is one of:
          'A'   — scan ADC row      → {'type':'A', 'row':int, 'data':[int,...]}
          'Z'   — scan DAC-Z row    → {'type':'Z', 'row':int, 'data':[int,...]}
          'N'   — noise scan row    → {'type':'N', 'row':int, 'data':[int,...]}
          'IVD' — IV+dIdV curve     → {'type':'IVD', 'N':int, 'values':[int,...]}
          'IV'  — raw IV curve      → {'type':'IV',  'values':[int,...]}
          'DI'  — dI/dZ curve       → {'type':'DI',  'values':[int,...]}
          'D'   — done sentinel     → {'type':'D'}
          'unknown'                 → {'type':'unknown', 'raw':str}
        Side-effects: updates self.scan_adc / scan_dacz / scan_noise arrays
        when an A/Z/N row is received.
        """
        line = line.strip()
        if not line:
            return {'type': 'unknown', 'raw': line}

        parts = line.split(',')
        tag   = parts[0]

        if tag in ('A', 'Z', 'N') and len(parts) >= 3:
            try:
                row  = int(parts[1])
                data = [int(x) for x in parts[2:] if x]
                if tag == 'A' and self.scan_adc is not None:
                    if row < self.scan_adc.shape[0]:
                        self.scan_adc[row, :len(data)] = data
                elif tag == 'Z' and self.scan_dacz is not None:
                    if row < self.scan_dacz.shape[0]:
                        self.scan_dacz[row, :len(data)] = data
                elif tag == 'N' and self.scan_noise is not None:
                    if row < self.scan_noise.shape[0]:
                        self.scan_noise[row, :len(data)] = data
                return {'type': tag, 'row': row, 'data': data}
            except (ValueError, IndexError):
                pass

        if tag == 'IVD' and len(parts) >= 2:
            try:
                N      = int(parts[1])
                values = [int(x) for x in parts[2:] if x]
                return {'type': 'IVD', 'N': N, 'values': values}
            except (ValueError, IndexError):
                pass

        if tag == 'IV':
            try:
                values = [int(x) for x in parts[1:] if x]
                return {'type': 'IV', 'values': values}
            except (ValueError, IndexError):
                pass

        if tag == 'DI':
            try:
                values = [int(x) for x in parts[1:] if x]
                return {'type': 'DI', 'values': values}
            except (ValueError, IndexError):
                pass

        if tag.startswith('D'):
            return {'type': 'D'}

        return {'type': 'unknown', 'raw': line}

    def startGridSpectroscopy(self,
                               x_start, x_end, x_resolution,
                               y_start, y_end, y_resolution,
                               bias_start, bias_end,
                               bias_points, mode, progress_callback=None):

        if not self.is_opened:
            return None

        self.busy = True

        # ---- Send command to firmware ----
        self.send_cmd(
            f'GSPC {x_start} {x_end} {x_resolution} '
            f'{y_start} {y_end} {y_resolution} '
            f'{bias_start} {bias_end} {bias_points} {mode}'
        )

        # ---- Allocate 3D data cube ----
        # grid_data[x, y, bias]
        grid_data = np.zeros(
            (x_resolution, y_resolution, bias_points),
            dtype=np.uint16
        )

        total_pixels = x_resolution * y_resolution
        received_pixels = 0

        print("Receiving grid spectroscopy data...")

        while received_pixels < total_pixels:

            # ---- Wait for sync bytes 'P','X' ----
            while True:
                byte = self.stm_serial.read(1)
                if byte == b'P':
                    second = self.stm_serial.read(1)
                    if second == b'X':
                        break

            # ---- Read header (remaining 7 bytes) ----
            header = self.stm_serial.read(7)

            x_i = int.from_bytes(header[0:2], 'little')
            y_i = int.from_bytes(header[2:4], 'little')
            pts = int.from_bytes(header[4:6], 'little')
            rx_mode = header[6]

            # ---- Safety checks ----
            if pts != bias_points:
                print("Bias point mismatch!")
                break

            # ---- Read spectral data ----
            data_bytes = self.stm_serial.read(2 * pts)

            spectrum = np.frombuffer(data_bytes, dtype=np.uint16)

            # ---- Store ----
            if x_i < x_resolution and y_i < y_resolution:
                grid_data[x_i, y_i, :] = spectrum

            received_pixels += 1

            if received_pixels % 100 == 0:
                print(f"{received_pixels}/{total_pixels} pixels received")
                if progress_callback:
                    progress = int((received_pixels / total_pixels) * 100)
                    progress_callback(progress)

        self.busy = False

        # Persist the full data cube + machine-state sidecar so the grid
        # display is reconstructible offline (record-everything posture).
        # Note: this is a parsed capture, not verbatim — the grid protocol
        # is binary; a byte-level tee is a future refinement.
        try:
            os.makedirs("scans", exist_ok=True)
            base = os.path.join("scans", f"gspc_{int(time.time() * 1000)}")
            np.savez_compressed(base + ".npz", grid=grid_data)
            with open(base + ".json", "w") as sf:
                import json as _json
                _json.dump({
                    "op": "grid_spectroscopy",
                    "x": [x_start, x_end, x_resolution],
                    "y": [y_start, y_end, y_resolution],
                    "bias": [bias_start, bias_end, bias_points],
                    "mode": mode,
                    "received_pixels": received_pixels,
                    "bias_dac": self.status.bias,
                    "dac_z": self.status.dac_z,
                    "steps": self.status.steps,
                    "finished": time.time(),
                }, sf, indent=2)
            session_journal.record("grid_spectroscopy_saved",
                                   path=base + ".npz")
            print(f"[GSPC] cube saved: {base}.npz")
        except Exception as e:
            print(f"[GSPC] WARNING: cube save failed: {e}")

        print("Grid Spectroscopy Complete")

        return grid_data
