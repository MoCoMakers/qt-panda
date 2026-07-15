"""Headless render of the app's real analysis plots to PNG (harness Tier 1).

Runs the actual ``plotframe.PlotFrame`` / pyqtgraph widgets under
``QT_QPA_PLATFORM=offscreen`` and exports each to a .png you can audit — no
display needed.  It mirrors ``widget.build_fourier_tab`` +
``refresh_fourier_analysis`` and the stability histogram, so the images reflect
exactly what the app draws (including any visual bug, e.g. a wrong axis).

This is the capture primitive both runtimes reuse:
  * Tier 1 (here): Docker headless -> PNG artifacts for CI / audit.
  * Tier 2 (later): the same PlotFrame.save_figure invoked live on the host,
    exposed to the co-pilot as a screenshot tool.

Usage (inside the PySide6 image, e.g. qtpanda-gui):
    QT_QPA_PLATFORM=offscreen python render_screens.py --out /out \\
        --csv /data/image_stability_1783032441387.csv --synth tunneling
"""
import argparse
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
from PySide6 import QtWidgets, QtCore
import pyqtgraph as pg
import pyqtgraph.exporters  # noqa: F401  (registers ImageExporter used by save_figure)

import plotframe
import stab_metrics
import stab_runner
import synth_source as ss

W, H = 780, 540


def _finalize(plt, path):
    plt.graphics.resize(W, H)
    QtWidgets.QApplication.processEvents()
    plt.save_figure(path)
    print("  wrote", path)


def render_fourier(times_ms, amps, out_prefix):
    """PSD + Allan, configured identically to widget.build_fourier_tab."""
    psd = stab_metrics.power_spectrum(times_ms, amps)
    allan = stab_metrics.allan_deviation(times_ms, amps)

    p = plotframe.PlotFrame()
    p.add_plot(label="PSD", xlabel="Frequency (Hz)", ylabel="Power (A^2/Hz)",
               pen=pg.mkPen("b", width=2))
    p.set_log_mode(x=True, y=True)
    p.disable_si_prefix()
    if psd is not None:
        p.update_plot(psd["freqs_hz"][1:], psd["psd"][1:])
        if psd["peak_significant"]:
            p.mark_point(psd["peak_freq_hz"], psd["peak_power"],
                         text=f'{psd["peak_freq_hz"]:.2f} Hz '
                              f'({psd["peak_snr"]:.1f}x floor)')
        _finalize(p, out_prefix + "_psd.png")

    a = plotframe.PlotFrame()
    a.add_plot(label="Allan deviation", xlabel="Averaging time tau (s)",
               ylabel="sigma_A (A)", pen=pg.mkPen("b", width=2))
    a.set_log_mode(x=True, y=True)
    a.disable_si_prefix()
    a.add_extra_curve("white", label="white noise (-1/2)",
                      pen=pg.mkPen("g", width=1,
                                   style=QtCore.Qt.PenStyle.DashLine))
    a.add_extra_curve("randomwalk", label="random-walk (+1/2)",
                      pen=pg.mkPen((255, 140, 0), width=1,
                                   style=QtCore.Qt.PenStyle.DashLine))
    a.add_extra_curve("drift", label="linear drift (+1)",
                      pen=pg.mkPen("r", width=1,
                                   style=QtCore.Qt.PenStyle.DashLine))
    if allan is not None:
        a.update_plot(allan["taus_s"], allan["sigma_a"])
        a.update_extra_curve("white", allan["taus_s"], allan["ref_white"])
        a.update_extra_curve("randomwalk", allan["taus_s"],
                             allan["ref_randomwalk"])
        a.update_extra_curve("drift", allan["taus_s"], allan["ref_drift"])
        a.mark_point(allan["tau_opt_s"], allan["sigma_min"],
                     text=f'best dwell ~{allan["tau_opt_s"]:.2f}s')
        _finalize(a, out_prefix + "_allan.png")


def render_timeseries(times_ms, currents, out_prefix, logy=False,
                      suffix="_current"):
    """Main-tab 'Current' trace (the red running-voltage zig-zag): red line,
    x = seconds relative to the latest sample, y = current in amps — configured
    like widget.py's pltCurrent.  With logy=True, plots |current| on a log axis
    so an approach shows the floor -> exponential tunneling climb -> contact
    across decades (negatives/zeros clamped to a 0.1 pA floor for the log)."""
    t = np.asarray(times_ms, float)
    y = np.asarray(currents, float)
    x_rel = (t - t.max()) / 1000.0 if t.size else t
    p = plotframe.PlotFrame()
    p.add_plot(label="Current", xlabel="time(s)",
               ylabel="|amp| (log)" if logy else "amp",
               pen=pg.mkPen("r", width=3))
    if logy:
        y = np.maximum(np.abs(y), 1e-13)
        p.set_log_mode(y=True)
        p.disable_si_prefix()
    p.update_plot(x_rel, y)
    _finalize(p, out_prefix + suffix + ".png")


def render_raster(image2d, out_prefix, label="Z topography", suffix="_raster"):
    """Render a scan raster (2D array, e.g. Z-trace topography) to PNG using the
    app's image widget — the scan-image counterpart to the analysis plots, and
    the per-timepoint 'frame' for the clip-series (frame_index)."""
    p = plotframe.PlotFrame()
    p.add_image(np.asarray(image2d, float), label=label)
    _finalize(p, out_prefix + suffix + ".png")


def render_histogram(amps, out_prefix):
    h = plotframe.PlotFrame()
    h.add_histogram(label="Current distribution", xlabel="Current (A)",
                    ylabel="count")
    counts, edges = np.histogram(amps, bins=60)
    centers = 0.5 * (edges[:-1] + edges[1:])
    h.update_histogram(centers, counts, current_index=len(centers) // 2)
    _finalize(h, out_prefix + "_hist.png")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", required=True, help="output dir for PNGs")
    ap.add_argument("--csv", action="append", default=[],
                    help="stability CSV to render (repeatable)")
    ap.add_argument("--synth", action="append", default=[],
                    choices=list(ss.PRESETS), help="synthetic preset (repeatable)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    jobs = []
    for c in args.csv:
        d = stab_runner.load_session(c)
        if d is None:
            print("skip (unreadable/empty):", c)
            continue
        jobs.append((os.path.splitext(os.path.basename(c))[0],
                     d["time_millis"], d["current_A"]))
    for kind in args.synth:
        kw, _ = ss.PRESETS[kind]
        g = ss.generate(seed=0, n=400, **kw)
        jobs.append(("synth_" + kind, g["time_millis"], g["current_A"]))

    for name, tms, amps in jobs:
        print("rendering", name)
        prefix = os.path.join(args.out, name)
        render_fourier(np.asarray(tms, float), np.asarray(amps, float), prefix)
        render_histogram(np.asarray(amps, float), prefix)

    print("done ->", args.out)


if __name__ == "__main__":
    main()
