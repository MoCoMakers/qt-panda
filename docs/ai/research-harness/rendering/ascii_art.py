"""Plain-text schematics so the investigation reads even without images.

ASCII diagrams double as a fast sanity check in the terminal and as a
fallback in the HTML report (rendered in a <pre> block).
"""

from __future__ import annotations

from physics.piezo_tip import tip_displacement_mm_deg
import physics.thermal_vibration as _tv


def tilt_schematic(theta_deg: float, lengths_mm) -> str:
    lines = [
        "        ideal axis",
        "           |          tilted tip (theta = %g deg)" % theta_deg,
        "           |        /",
        "           |       /",
        "           |      /  <-- apex sweeps through arc",
        "           |     /",
        "           |    /",
        "           |   /",
        "           |  /) theta",
        "    _______|_/____________   <- piezo mounting face",
        "   |///////////////////////|",
        "   |///////////////////////|",
        "",
        "   apex displacement = standoff length L  x  angle (Abbe error)",
        "",
    ]
    return "\n".join(lines)


def results_table(theta_deg: float, lengths_mm) -> str:
    rows = [
        "  L (mm) | lateral dx (um) | vertical dz (um) | total dr (um)",
        "  -------+-----------------+------------------+--------------",
    ]
    for L in lengths_mm:
        d = tip_displacement_mm_deg(L, theta_deg)
        rows.append(
            "  %6.2f | %15.3f | %16.4f | %12.3f"
            % (L, d.lateral_um, d.vertical_um, d.total_um)
        )
    # Ratio line for the headline comparison.
    if len(lengths_mm) == 2:
        a = tip_displacement_mm_deg(lengths_mm[0], theta_deg)
        b = tip_displacement_mm_deg(lengths_mm[1], theta_deg)
        ratio = b.lateral_um / a.lateral_um if a.lateral_um else float("nan")
        rows.append("")
        rows.append(
            "  lateral error grows %.1fx from L=%g mm to L=%g mm"
            % (ratio, lengths_mm[0], lengths_mm[1])
        )
    return "\n".join(rows)


def thermal_schematic(T: float) -> str:
    d = _tv.gold_at(T)
    a_nn = _tv.A_NN_AU * 1e12
    return "\n".join([
        "   atom jitters in a (near-harmonic) well made by its bonds:",
        "",
        "        U(x)  \\                         /",
        "               \\          o            /     o = atom, rattling",
        "                \\       .' '.         /          about the bottom",
        "                 \\____ '     ' ____ /",
        "                       <-- a -->            a = jitter amplitude",
        "",
        "   <|u|> (mean)  ~ %5.1f pm    rms ~ %5.1f pm    sigma/axis ~ %5.1f pm" % (
            d.mean_mag_pm, d.rms_pm, d.sigma_pm),
        "   spacing (from density) = %5.0f pm  ->  jitter is %.1f%% of spacing" % (
            a_nn, d.lindemann_ratio * 100),
    ])


def thermal_table(T: float) -> str:
    d = _tv.gold_at(T)
    c = _tv.gold_at(T, model="classical")
    rows = [
        "  quantity                         value (pm)   formula",
        "  -------------------------------+------------+--------------------",
        "  per-axis RMS  (sigma)          | %8.2f   | sqrt(<u^2>/3)" % d.sigma_pm,
        "  most-probable |u|              | %8.2f   | sqrt(2) sigma" % d.most_probable_pm,
        "  MEAN displacement <|u|>        | %8.2f   | sqrt(8/pi) sigma" % d.mean_mag_pm,
        "  3-D RMS |u|                    | %8.2f   | sqrt(<u^2>)" % d.rms_pm,
        "  (classical-only 3-D RMS)       | %8.2f   | 9 hbar^2 T / m kB ThetaD^2" % c.rms_pm,
        "",
        "  Lindemann ratio rms/spacing = %.3f  (melts near ~0.10-0.15)" % d.lindemann_ratio,
    ]
    return "\n".join(rows)
