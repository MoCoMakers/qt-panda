"""copilot_api — Qt-free agent tool layer (Phase 6 core).

The tools an LLM co-pilot calls, decoupled from any transport.  Later, an
embedded MCP server (host/live) exposes these; here they are plain methods over
the journal + stab_runner + the data broker, so the whole observe/annotate/
verdict loop is buildable and testable headless with no MCP and no GUI.

Tiers (roadmap A1):
  * Tier 0 observe  — journal_tail, get_recent_samples, get_status
  * Tier 1 annotate — add_note (src='agent'), run_verdict
  * screenshot      — delegated to render_screens (Tier-1 capture) when a path
                      is given; kept out of the hot path here.

Actuation (Tier 2) is intentionally NOT in this layer — it belongs behind the
gate + approach_fsm envelope, added when the live app exists.
"""
import json

import session_journal
import stab_runner


class CopilotAPI:
    def __init__(self, broker=None, journal=session_journal):
        self._broker = broker
        self._journal = journal
        # Subscribe to the sample stream if a broker is present (drop-oldest,
        # so the agent falling behind never stalls acquisition).
        self._samples = broker.subscribe("sample", maxlen=2000) if broker else None
        self._status = broker.subscribe("status", latest_only=True) if broker else None

    # --- Tier 0: observe -------------------------------------------------
    def journal_tail(self, n=20):
        """Last n journal records (commands/notes/samples/etc.), or []."""
        path = self._journal.active_path()
        if not path:
            return []
        try:
            recs = [json.loads(ln) for ln in open(path) if ln.strip()]
        except OSError:
            return []
        return recs[-n:]

    def get_recent_samples(self, n=100):
        """Up to the most recent n samples buffered from the broker."""
        if self._samples is None:
            return []
        return self._samples.poll()[-n:]

    def get_status(self):
        """Latest status snapshot from the broker, or None."""
        return self._status.latest() if self._status else None

    # --- Tier 1: annotate / analyze -------------------------------------
    def add_note(self, text):
        """Write an agent-attributed annotation onto the shared journal bus."""
        self._journal.note(text, src="agent")
        return {"ok": True, "text": text}

    def run_verdict(self, csv_path):
        """Grade a session CSV with the same logic the GUI uses."""
        return stab_runner.analyze(csv_path)

    def query_point(self, target_tm, journal_path=None, csv_path=None):
        """Full instrument state at a firmware time_millis: nearest reading row
        (current/Z/bias/steps/flags) + reconstructed settings (scan window,
        setpoint, gains).  Uses the active journal unless one is given."""
        import session_query
        jp = journal_path or self._journal.active_path()
        if not jp:
            return None
        recs, rows = session_query.load(jp, csv_path)
        return session_query.state_at(recs, rows, target_tm)

    def screenshot(self, out_prefix, csv_path, views=("fourier", "hist", "current")):
        """Render the requested analysis plots for a session CSV to PNG (the
        Tier-1 capture, invoked as a tool).  Qt imported lazily so observe/
        annotate stay importable without PySide6."""
        import numpy as np
        from PySide6 import QtWidgets
        import render_screens

        d = stab_runner.load_session(csv_path)
        if d is None:
            return {"ok": False, "error": f"unreadable csv: {csv_path}"}
        QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        tms = np.asarray(d["time_millis"], float)
        cur = np.asarray(d["current_A"], float)
        made = []
        if "fourier" in views:
            render_screens.render_fourier(tms, cur, out_prefix)
            made += [out_prefix + "_psd.png", out_prefix + "_allan.png"]
        if "hist" in views:
            render_screens.render_histogram(cur, out_prefix)
            made.append(out_prefix + "_hist.png")
        if "current" in views:
            render_screens.render_timeseries(tms, cur, out_prefix)
            made.append(out_prefix + "_current.png")
        return {"ok": True, "paths": made}
