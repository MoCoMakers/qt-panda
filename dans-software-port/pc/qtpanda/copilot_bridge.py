"""copilot_bridge — in-process HTTP control channel for the live GUI (Phase 6 host/live).

Runs a small JSON-over-HTTP server on 127.0.0.1 inside the GUI process so an
external agent (Claude, scripts, curl) can observe AND actuate the running
instrument.  This is the live counterpart of copilot_api: where copilot_api is
the Qt-free offline tool layer, this bridge is the transport that exposes the
same observe/annotate surface plus Tier-2 actuation against the real widget.

Safety model:
  * binds to localhost only — nothing off-machine can reach it;
  * every actuation is funneled onto the Qt MAIN thread (never concurrent
    with the GSTS poll or a GUI handler), through the same STM methods the
    buttons use;
  * every wire command is journaled at the existing send_cmd choke point
    with src='agent', so the session log attributes who did what;
  * a gate flag (default ON, per operator request) can disable all actuation
    at runtime via POST /gate {"enabled": false} — observe stays available.

Endpoints (all JSON):
  GET  /health            liveness + port/scan/stab flags
  GET  /status            full latest STM status (raw DAC/ADC + physical units)
  GET  /samples?n=200     recent history samples (tm, adc, current_A, ...)
  GET  /journal?n=50      tail of the active session journal (or latest file)
  GET  /ports             enumerated serial ports
  GET  /screenshot        grab the GUI window to PNG, returns the path
  POST /open              {"port": "COM5"}           open serial port
  POST /command           {"cmd": "MTMV 10"}         raw firmware command
  POST /motor             {"steps": -10}             MTMV
  POST /bias              {"dac": 32768}             BIAS
  POST /dac               {"x":..,"y":..,"z":..}     DACX/DACY/DACZ (each optional)
  POST /approach          {"target_dac":.., "steps":..}  APRH
  POST /cc                {"on": true, "target": 300}    CCON / CCOF
  POST /stop              {}                         STOP
  POST /stab/start|stop|clear                        stability recording
  POST /note              {"text": "..."}            journal note, src='agent'
  POST /gate              {"enabled": false}         enable/disable actuation
"""
import json
import logging
import os
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PySide6 import QtCore

import session_journal
import stm_control

logger = logging.getLogger("stm")

DEFAULT_PORT = 8765


class _InvokeEvent(QtCore.QEvent):
    TYPE = QtCore.QEvent.Type(QtCore.QEvent.registerEventType())

    def __init__(self, fn, done, box):
        super().__init__(self.TYPE)
        self.fn, self.done, self.box = fn, done, box


class _Invoker(QtCore.QObject):
    """Executes callables on the Qt main thread (create it there); other
    threads call run() and block until the GUI thread has executed fn."""

    def event(self, ev):
        if isinstance(ev, _InvokeEvent):
            try:
                ev.box["result"] = ev.fn()
            except Exception as e:  # propagate to the calling thread
                ev.box["error"] = e
                ev.box["trace"] = traceback.format_exc()
            ev.done.set()
            return True
        return super().event(ev)

    def run(self, fn, timeout=10.0):
        done = threading.Event()
        box = {}
        QtCore.QCoreApplication.postEvent(self, _InvokeEvent(fn, done, box))
        if not done.wait(timeout):
            raise TimeoutError("GUI main thread did not respond "
                               f"within {timeout}s")
        if "error" in box:
            raise box["error"]
        return box.get("result")


class CopilotBridge:
    def __init__(self, widget):
        self.widget = widget
        self.invoker = _Invoker()          # affinity = thread creating it
        self.allow_actuation = True
        self._server = None

    # ------------------------------------------------------------------
    # main-thread snapshot / action helpers (called via invoker)
    # ------------------------------------------------------------------
    def status_snapshot(self):
        w = self.widget
        s = w.stm.status
        scan_running = bool(getattr(w, "_scan_ctrl", None)
                            and w._scan_ctrl.is_running())
        return {
            "t": time.time(),
            "port_open": w.stm.is_opened,
            "busy": w.stm.busy,
            "firmware_tagged_status": w.stm.firmware_tagged_status,
            "stab_running": w.stab_running,
            "scan_running": scan_running,
            "actuation_enabled": self.allow_actuation,
            "journal": session_journal.active_path(),
            "stab_csv": w.stab_log_path,
            "status": {
                "bias": s.bias,
                "bias_V": stm_control.STM_Status.dac_to_bias_volts(s.bias),
                "dac_z": s.dac_z,
                "dac_z_V": stm_control.STM_Status.dac_to_dacz_volts(s.dac_z),
                "dac_x": s.dac_x,
                "dac_y": s.dac_y,
                "adc": s.adc,
                "current_A": stm_control.STM_Status.adc_to_amp(s.adc),
                "steps": s.steps,
                "is_approaching": s.is_approaching,
                "is_const_current": s.is_const_current,
                "is_scanning": s.is_scanning,
                "time_millis": s.time_millis,
            },
        }

    def samples_snapshot(self, n):
        hist = list(self.widget.stm.history)[-n:]
        return [{
            "time_millis": h.time_millis,
            "adc": h.adc,
            "current_A": stm_control.STM_Status.adc_to_amp(h.adc),
            "dac_z": h.dac_z,
            "bias": h.bias,
            "steps": h.steps,
            "is_approaching": h.is_approaching,
            "is_const_current": h.is_const_current,
            "is_scanning": h.is_scanning,
        } for h in hist]

    def screenshot(self, path=None):
        os.makedirs("logs", exist_ok=True)
        path = path or os.path.join(
            "logs", f"copilot_screen_{int(time.time() * 1000)}.png")
        ok = self.widget.grab().save(path)
        return {"ok": bool(ok), "path": os.path.abspath(path)}

    def journal_tail(self, n):
        path = session_journal.active_path()
        if not path:
            # No live session: fall back to the newest journal on disk so
            # the agent can still read the last session's record.
            try:
                files = sorted(
                    f for f in os.listdir("logs")
                    if f.startswith("session_") and f.endswith(".jsonl"))
                path = os.path.join("logs", files[-1]) if files else None
            except OSError:
                path = None
        if not path:
            return {"path": None, "records": []}
        try:
            with open(path) as f:
                recs = [json.loads(ln) for ln in f if ln.strip()]
        except OSError:
            recs = []
        return {"path": os.path.abspath(path), "records": recs[-n:]}

    # ------------------------------------------------------------------
    # HTTP plumbing
    # ------------------------------------------------------------------
    def start(self, port=DEFAULT_PORT):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            # keep the GUI console clean; stm.log gets the interesting lines
            def log_message(self, *args):
                pass

            def _reply(self, obj, code=200):
                body = json.dumps(obj).encode()
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _body(self):
                length = int(self.headers.get("Content-Length") or 0)
                if not length:
                    return {}
                return json.loads(self.rfile.read(length) or b"{}")

            def do_GET(self):
                try:
                    self._route_get()
                except Exception as e:
                    self._reply({"ok": False, "error": str(e),
                                 "trace": traceback.format_exc()}, 500)

            def do_POST(self):
                try:
                    self._route_post()
                except Exception as e:
                    self._reply({"ok": False, "error": str(e),
                                 "trace": traceback.format_exc()}, 500)

            # ---- GET routes -------------------------------------------
            def _route_get(self):
                path, _, query = self.path.partition("?")
                params = dict(kv.split("=", 1) for kv in query.split("&")
                              if "=" in kv)
                if path == "/health":
                    self._reply({"ok": True,
                                 **bridge.invoker.run(bridge.status_snapshot)})
                elif path == "/status":
                    self._reply(bridge.invoker.run(bridge.status_snapshot))
                elif path == "/samples":
                    n = int(params.get("n", 200))
                    self._reply({"samples":
                                 bridge.invoker.run(
                                     lambda: bridge.samples_snapshot(n))})
                elif path == "/journal":
                    n = int(params.get("n", 50))
                    self._reply(bridge.journal_tail(n))
                elif path == "/ports":
                    import serial.tools.list_ports as lp
                    self._reply({"ports": [
                        {"device": p.device, "description": p.description}
                        for p in lp.comports()]})
                elif path == "/screenshot":
                    out = params.get("path")
                    self._reply(bridge.invoker.run(
                        lambda: bridge.screenshot(out)))
                else:
                    self._reply({"ok": False, "error": f"no route {path}"},
                                404)

            # ---- POST routes ------------------------------------------
            def _route_post(self):
                path = self.path.partition("?")[0]
                body = self._body()
                w = bridge.widget

                # Observation-adjacent posts that don't move hardware:
                if path == "/note":
                    text = str(body.get("text", "")).strip()
                    if not text:
                        return self._reply(
                            {"ok": False, "error": "empty text"}, 400)
                    session_journal.note(text, src="agent")
                    return self._reply(
                        {"ok": True,
                         "journal_active": session_journal.is_active()})
                if path == "/gate":
                    bridge.allow_actuation = bool(body.get("enabled", True))
                    logger.info(f"[copilot] actuation gate -> "
                                f"{bridge.allow_actuation}")
                    return self._reply(
                        {"ok": True,
                         "actuation_enabled": bridge.allow_actuation})

                if not bridge.allow_actuation:
                    return self._reply(
                        {"ok": False,
                         "error": "actuation disabled (POST /gate to enable)"},
                        403)

                # Everything below moves hardware or GUI state: run it on
                # the Qt main thread, serialized with the GSTS poll.
                def act():
                    if path == "/open":
                        port_name = str(body.get("port", "")).strip()
                        if not port_name:
                            raise ValueError("missing 'port'")
                        idx = w.ui.lePort.findText(port_name)
                        if idx >= 0:
                            w.ui.lePort.setCurrentIndex(idx)
                        else:
                            w.ui.lePort.setEditText(port_name)
                        w.on_cmdOpen_clicked()
                        return {"ok": w.stm.is_opened, "port": port_name}
                    if path == "/command":
                        cmd = str(body.get("cmd", "")).strip()
                        if not cmd:
                            raise ValueError("missing 'cmd'")
                        logger.info(f"[copilot] CMD {cmd}")
                        w.stm.send_cmd(cmd, src="agent")
                        return {"ok": True, "cmd": cmd}
                    if path == "/motor":
                        steps = int(body["steps"])
                        logger.info(f"[copilot] MTMV {steps} (auto-MTOF)")
                        w.motor_move(steps, src="agent")
                        return {"ok": True, "steps": steps,
                                "auto_mtof": True}
                    if path == "/bias":
                        dac = int(body["dac"])
                        logger.info(f"[copilot] BIAS {dac}")
                        w.stm.send_cmd(f"BIAS {dac}", src="agent")
                        return {"ok": True, "dac": dac}
                    if path == "/dac":
                        sent = {}
                        for axis in ("x", "y", "z"):
                            if axis in body:
                                val = int(body[axis])
                                w.stm.send_cmd(f"DAC{axis.upper()} {val}",
                                               src="agent")
                                sent[axis] = val
                        logger.info(f"[copilot] DAC {sent}")
                        return {"ok": True, "sent": sent}
                    if path == "/approach":
                        target = int(body["target_dac"])
                        steps = int(body["steps"])
                        logger.info(f"[copilot] APRH {target} {steps}")
                        w.stm.send_cmd(f"APRH {target} {steps}", src="agent")
                        return {"ok": True}
                    if path == "/cc":
                        if body.get("on"):
                            target = int(body["target"])
                            logger.info(f"[copilot] CCON {target}")
                            w.stm.send_cmd(f"CCON {target}", src="agent")
                        else:
                            logger.info("[copilot] CCOF")
                            w.stm.send_cmd("CCOF", src="agent")
                        return {"ok": True}
                    if path == "/stop":
                        logger.info("[copilot] STOP")
                        w.stm.send_cmd("STOP", src="agent")
                        return {"ok": True}
                    if path == "/stab/start":
                        if not w.stab_running:
                            w.stab_start()
                        return {"ok": True, "csv": w.stab_log_path,
                                "journal": session_journal.active_path()}
                    if path == "/stab/stop":
                        if w.stab_running:
                            w.stab_stop()
                        return {"ok": True, "csv": w.stab_log_path}
                    if path == "/stab/clear":
                        w.stab_clear()
                        return {"ok": True}
                    raise LookupError(f"no route {path}")

                try:
                    self._reply(bridge.invoker.run(act))
                except LookupError as e:
                    self._reply({"ok": False, "error": str(e)}, 404)

        self._server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        t = threading.Thread(target=self._server.serve_forever,
                             name="copilot-bridge", daemon=True)
        t.start()
        logger.info(f"[copilot] bridge listening on http://127.0.0.1:{port}")
        return self

    def stop(self):
        if self._server is not None:
            self._server.shutdown()
            self._server = None


def start(widget, port=DEFAULT_PORT):
    """Create and start the bridge (call from the Qt main thread)."""
    return CopilotBridge(widget).start(port)
