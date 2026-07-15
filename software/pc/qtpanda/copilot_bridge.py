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
  POST /command           {"cmd": "STRM 200"}        raw send — ONLY protocol
                          cmds with no GUI control (STRM/RAWD/SPPX/VERS/SETD)
  POST /motor             {"steps": -10}             sets spnMot, clicks the
                          real Retract (neg) / Approach (pos) motor button
  POST /bias              {"dac": 32768}             sets spnBias, clicks Set Bias
  POST /dac               {"x":..,"y":..,"z":..,"bias":..}  sets spinboxes,
                          clicks Set All DAC (sends all four from screen)
  POST /approach          {"target_dac":.., "steps":..}  sets leTargetDAC /
                          leSteps (omitted = keep screen value), clicks
                          Auto Approach
  POST /cc                {"on": true, "target": 300}    clicks CC On / CC Off

  ALL actuation is GUI-first: endpoints drive the real on-screen widgets and
  click the real buttons, so agent actions run the identical handler path as
  human clicks, are visible on screen, and journal with src='agent'.  No
  side-channel serial writes (bench incident 2026-07-14: a direct APRH used
  step_interval=50 while the GUI showed 1).
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
                elif path == "/frames/status":
                    self._reply(bridge.invoker.run(
                        lambda: bridge.widget._frame_logger.status()))
                elif path == "/raw/status":
                    self._reply(bridge.invoker.run(
                        lambda: bridge.widget._raw_logger.status()))
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

                if path == "/quit":
                    # Graceful shutdown: close recordings/logs/serial in
                    # order, then quit Qt.  Runs on the main thread; the
                    # reply is sent before the deferred quit fires.
                    def _shutdown():
                        w2 = bridge.widget
                        try:
                            if w2.stab_running:
                                w2.stab_stop(show_fourier=False)
                        except Exception:
                            pass
                        try:
                            if getattr(w2, "_scan_ctrl", None) \
                                    and w2._scan_ctrl.is_running():
                                w2._on_cs_halt()
                        except Exception:
                            pass
                        try:
                            w2._frame_logger.stop()
                        except Exception:
                            pass
                        try:
                            # Persist the DACX/DACY operating point while
                            # the port is still open (status is truth).
                            w2._save_dac_xy()
                        except Exception:
                            pass
                        try:
                            w2._stop_session_recording()
                        except Exception:
                            pass
                        try:
                            session_journal.stop()
                        except Exception:
                            pass
                        try:
                            if w2.stm.is_opened:
                                w2.stm.stm_serial.close()
                                w2.stm.is_opened = False
                        except Exception:
                            pass
                        QtCore.QCoreApplication.quit()

                    def arm_quit():
                        logger.info("[copilot] graceful shutdown requested")
                        QtCore.QTimer.singleShot(200, _shutdown)
                        return {"ok": True, "quitting": True}

                    return self._reply(bridge.invoker.run(arm_quit))

                if not bridge.allow_actuation:
                    return self._reply(
                        {"ok": False,
                         "error": "actuation disabled (POST /gate to enable)"},
                        403)

                # Everything below moves hardware or GUI state: run it on
                # the Qt main thread, serialized with the GSTS poll.
                def act():
                    # GUI-first actuation: every endpoint below sets the real
                    # on-screen widgets and clicks the real buttons, so the
                    # agent exercises the exact same code path as a human and
                    # the screen always reflects what was commanded.  No
                    # side-channel serial writes (bench incident 2026-07-14:
                    # a direct APRH used step_interval=50 while the GUI was
                    # configured for 1).
                    def agent_click(button):
                        w.stm.src_override = "agent"
                        try:
                            button.click()
                        finally:
                            w.stm.src_override = None

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
                        # Escape hatch ONLY for protocol commands that have
                        # no GUI control.  Anything with an on-screen widget
                        # must go through its GUI-first endpoint.
                        cmd = str(body.get("cmd", "")).strip()
                        if not cmd:
                            raise ValueError("missing 'cmd'")
                        NO_GUI = ("STRM", "RAWD", "SPPX", "VERS", "SETD")
                        if not cmd.upper().startswith(NO_GUI):
                            raise PermissionError(
                                f"{cmd.split()[0]!r} has a GUI control — "
                                "use its endpoint (/bias /dac /approach "
                                "/motor /cc /stop /scan/*); raw sends are "
                                "limited to " + ",".join(NO_GUI))
                        logger.info(f"[copilot] CMD {cmd}")
                        w.stm.send_cmd(cmd, src="agent")
                        return {"ok": True, "cmd": cmd}
                    if path == "/motor":
                        steps = int(body["steps"])
                        w.ui.spnMot.setValue(abs(steps))
                        btn = w.ui.cmdMotDown if steps < 0 else w.ui.cmdMotUp
                        logger.info(f"[copilot] motor click "
                                    f"{btn.objectName()} amount={abs(steps)}")
                        agent_click(btn)
                        return {"ok": True, "steps": steps,
                                "button": btn.objectName(),
                                "auto_mtof": True}
                    if path == "/bias":
                        dac = int(body["dac"])
                        w.ui.spnBias.setValue(dac)
                        logger.info(f"[copilot] bias click Set Bias "
                                    f"dac={w.ui.spnBias.value()}")
                        agent_click(w.ui.cmdSendBias)
                        return {"ok": True, "dac": w.ui.spnBias.value()}
                    if path == "/dac":
                        # 'Set All DAC' sends bias+X+Y+Z from the spinboxes;
                        # update the ones provided, then click — the reply
                        # reports everything the click actually sent.
                        spins = {"x": w.ui.spnDACX, "y": w.ui.spnDACY,
                                 "z": w.ui.spnDACZ, "bias": w.ui.spnBias}
                        for key, box in spins.items():
                            if key in body:
                                box.setValue(int(body[key]))
                        agent_click(w.ui.cmdSetDAC)
                        sent = {k: b.value() for k, b in spins.items()}
                        logger.info(f"[copilot] Set All DAC click {sent}")
                        return {"ok": True, "sent": sent}
                    if path == "/approach":
                        # Fields are optional: omitted ones use whatever is
                        # on screen, exactly like a human clicking the button.
                        if "target_dac" in body:
                            w.ui.leTargetDAC.setText(str(int(body["target_dac"])))
                        if "steps" in body:
                            w.ui.leSteps.setText(str(int(body["steps"])))
                        target = int(w.ui.leTargetDAC.text() or 0)
                        steps = int(w.ui.leSteps.text() or 0)
                        logger.info(f"[copilot] Auto Approach click "
                                    f"target={target} steps={steps}")
                        agent_click(w.ui.cmdApproach)
                        return {"ok": True, "target_dac": target,
                                "steps": steps}
                    if path == "/cc":
                        # The GUI control is the chkConstCurrent checkbox
                        # (there are no cmdCCOn/cmdCCOff buttons in the form).
                        on = bool(body.get("on"))
                        if on and "target" in body:
                            w.ui.leCCVal.setText(str(int(body["target"])))
                        logger.info(f"[copilot] CC checkbox -> {on} "
                                    f"target={w.ui.leCCVal.text()}")
                        w.stm.src_override = "agent"
                        try:
                            w.ui.chkConstCurrent.setChecked(on)
                        finally:
                            w.stm.src_override = None
                        return {"ok": True, "on": on,
                                "target": int(w.ui.leCCVal.text() or 0)}
                    if path == "/stop":
                        logger.info("[copilot] Stop click")
                        agent_click(w.ui.cmdStop)
                        return {"ok": True}
                    if path == "/scan/run":
                        logger.info("[copilot] scan RUN")
                        w.stm.src_override = "agent"
                        try:
                            w._on_cs_run()
                        finally:
                            w.stm.src_override = None
                        return {"ok": w._scan_ctrl.is_running(),
                                "status": w._cs_status_lbl.text(),
                                "frames": w._frame_logger.status()}
                    if path == "/scan/halt":
                        logger.info("[copilot] scan HALT")
                        w.stm.src_override = "agent"
                        try:
                            w._on_cs_halt()
                        finally:
                            w.stm.src_override = None
                        return {"ok": True,
                                "frames": w._frame_logger.status()}
                    if path == "/scan/engage":
                        logger.info("[copilot] ENGA")
                        w._scan_ctrl.engage()
                        return {"ok": True}
                    if path == "/scan/retract":
                        logger.info("[copilot] RTRC")
                        w._scan_ctrl.retract()
                        return {"ok": True}
                    if path == "/scan/settings":
                        # Set the GUI spinboxes (so the screen matches
                        # reality), then push via the normal Apply path.
                        spin = {"scan_size_nm": w._cs_scansize,
                                "pixels_per_line": w._cs_pixels,
                                "line_rate_hz": w._cs_linerate,
                                "x_offset_nm": w._cs_xofs,
                                "y_offset_nm": w._cs_yofs,
                                "setpoint_pa": w._cs_setpoint,
                                "kp": w._cs_kp,
                                "ki": w._cs_ki}
                        applied = {}
                        for key, box in spin.items():
                            if key in body:
                                box.setValue(type(box.value())(body[key]))
                                applied[key] = box.value()
                        w._on_cs_apply_settings()
                        logger.info(f"[copilot] scan settings {applied}")
                        return {"ok": True, "applied": applied}
                    if path == "/ui":
                        # Generic GUI field setter: {"field": "leSamples",
                        # "value": "2"}.  Looks on w.ui then w; supports the
                        # editable field types only.
                        from PySide6 import QtWidgets as QW
                        name = str(body.get("field", ""))
                        obj = getattr(w.ui, name, None) or getattr(w, name,
                                                                   None)
                        if obj is None:
                            raise LookupError(f"no UI field {name!r}")
                        val = body.get("value")
                        if isinstance(obj, (QW.QSpinBox, QW.QDoubleSpinBox)):
                            obj.setValue(type(obj.value())(val))
                        elif isinstance(obj, QW.QLineEdit):
                            obj.setText(str(val))
                        elif isinstance(obj, QW.QComboBox):
                            obj.setEditText(str(val)) if obj.isEditable() \
                                else obj.setCurrentText(str(val))
                        elif isinstance(obj, (QW.QCheckBox,)):
                            obj.setChecked(bool(val))
                        elif isinstance(obj, QW.QPushButton):
                            # Generic GUI-first button click with agent
                            # attribution (value ignored).
                            w.stm.src_override = "agent"
                            try:
                                obj.click()
                            finally:
                                w.stm.src_override = None
                        elif isinstance(obj, QW.QTabWidget):
                            # value: tab title (case-insensitive) or index
                            if isinstance(val, str):
                                for i in range(obj.count()):
                                    if (obj.tabText(i).strip().lower()
                                            == val.strip().lower()):
                                        obj.setCurrentIndex(i)
                                        break
                                else:
                                    raise LookupError(f"no tab {val!r}")
                            else:
                                obj.setCurrentIndex(int(val))
                        else:
                            raise TypeError(
                                f"unsupported field type {type(obj).__name__}")
                        logger.info(f"[copilot] ui {name} = {val!r}")
                        return {"ok": True, "field": name, "value": val}
                    if path == "/raw/start":
                        decim = int(body.get("decim", 1))
                        logger.info(f"[copilot] RAWD {decim} (raw capture)")
                        return w.raw_start(decim, src="agent")
                    if path == "/raw/stop":
                        logger.info("[copilot] RAWD 0 (raw capture stop)")
                        return {"ok": True, "path": w.raw_stop(src="agent"),
                                **w._raw_logger.status()}
                    if path == "/stab/start":
                        if not w.stab_running:
                            w.stab_start()
                        return {"ok": True, "csv": w.stab_log_path,
                                "journal": session_journal.active_path()}
                    if path == "/stab/stop":
                        if w.stab_running:
                            w.stab_stop(show_fourier=False)
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
