"""Query: does moving the piezo/sample toward the hinge buy precision?

Reference question (user, from the 3D-printer's feedback): the piezo + sample
junction sits at the FAR end of the clamshell (near the wedge); would putting it
closer to the hinge — e.g. reseating the piezo and the "roman arch" tie-down
rails, and the matching sample cavity on the bottom plate, back toward the pin —
give finer steps?

Physics.  The drive is unchanged: the rack-pinion still slides the M12 wedge at
the lid lip, d_w = 120.15 mm from the pin, lifting it dz_wedge = 976.2 nm per
motor step (that is fixed by the wedge + drive, NOT by where the piezo sits).
The lid rotation per step is therefore also fixed: dphi = dz_wedge / d_w.  Only
the piezo's lever arm r_p changes, and

    dz_tip = dphi * r_p          -> LINEAR in r_p   (finer as r_p shrinks)
    dz_range = dphi_total * r_p  -> LINEAR in r_p   (less Z reach, the cost)
    dx_tip = dphi * c            -> INDEPENDENT of r_p (absolute lateral fixed)
    dx/dz  = c / r_p             -> grows as 1/r_p  (Abbe ratio worsens)

So moving the piezo toward the hinge is a *free lever reduction*: no new parts,
finer steps, paid for in Z range and a worse Abbe ratio.  This query sweeps r_p
across the reseat band that the tie-down arches (x = -16..+24 mm) actually allow.
"""

from __future__ import annotations

from pathlib import Path

from models import Investigation
from physics import wedge_lever as wl
from rendering import figures_piezo

SLUG = "wedge-piezo-position"

# Candidate piezo centres (label, x in the pin frame; r_p = 35 - x).
# as-built x = -41.26 (r_p 76.26); the arch rails sit at x = -16 .. +24.
DEFAULT_POSITIONS = [
    ("as-built", -41.26),
    ("−25 mm", -25.0),
    ("−13 mm (front arch)", -13.0),
    ("−3 mm (mid arch)", -3.0),
]


def _row(label: str, x_mm: float) -> dict:
    r_p = wl.PIVOT_X_MM - x_mm
    g = wl.as_built_gearing(lever_mm=r_p)
    g0 = wl.as_built_gearing()  # as-built reference
    return {
        "label": label,
        "x": x_mm,
        "r_p": r_p,
        "ratio": g.lever_ratio,
        "dz": g.dz_tip_nm,
        "gain": g0.dz_tip_nm / g.dz_tip_nm,
        "dx": g.dx_tip_nm,
        "abbe": wl.COLLET_STANDOFF_MM / r_p * 100.0,
        "range_mm": wl.WEDGE_RISE_MM * g.lever_ratio,
        "steps_lo": g.steps_across_reach_um(wl.PIEZO_REACH_UM[0]),
        "steps_hi": g.steps_across_reach_um(wl.PIEZO_REACH_UM[1]),
    }


def _table(rows) -> str:
    head = ("piezo x   r_p     ratio    tip Z/step   vs as-built   Z range    "
            "Abbe c/r_p   steps 15-50um")
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r['x']:6.1f}  {r['r_p']:5.1f}   {r['ratio']:.4f}   "
            f"{r['dz']:7.1f} nm   {r['gain']:5.2f}x       {r['range_mm']:.3f} mm   "
            f"{r['abbe']:5.1f} %      {r['steps_lo']:,.0f}-{r['steps_hi']:,.0f}")
    lines.append("-" * len(head))
    lines.append("(drive fixed: rack-pinion, dz_wedge = 976.2 nm/step at the lip; "
                 "d_w = 120.15 mm; c = 8 mm)")
    return "\n".join(lines)


def run(out_dir: Path, positions=DEFAULT_POSITIONS) -> Investigation:
    positions = list(positions)
    rows = [_row(lbl, x) for lbl, x in positions]
    ab = rows[0]                      # as-built is the first row
    near = rows[-1]                   # closest-to-hinge candidate

    fig_dir = Path(out_dir) / "figures"
    manifest = figures_piezo.generate_all(fig_dir, positions)

    summary = (
        f"<b>Yes — moving the piezo toward the hinge makes every step finer, and it "
        f"does so linearly and for free.</b> The wedge and its rack-pinion drive stay "
        f"where they are (at the lip, {wl.LIP_ARM_MM:.2f}&nbsp;mm from the pin), so the "
        f"per-step lift under the lip is unchanged at {ab['dz']/ab['ratio']:.0f}&nbsp;nm; "
        f"only the piezo's lever arm r<sub>p</sub> changes, and "
        f"&Delta;z<sub>tip</sub>&nbsp;=&nbsp;(lip lift)&nbsp;&times;&nbsp;r<sub>p</sub>/d<sub>w</sub>. "
        f"At the as-built r<sub>p</sub>&nbsp;=&nbsp;{ab['r_p']:.2f}&nbsp;mm the step is "
        f"<b>{ab['dz']:.0f}&nbsp;nm</b>; reseating the piezo over the tie-down arches to "
        f"r<sub>p</sub>&nbsp;=&nbsp;{near['r_p']:.0f}&nbsp;mm (x&nbsp;&asymp;&nbsp;"
        f"{near['x']:.0f}&nbsp;mm) drops it to <b>{near['dz']:.0f}&nbsp;nm/step</b> — a "
        f"<b>{near['gain']:.1f}&times;</b> precision gain with no new parts. The price is "
        f"proportional: full Z range shrinks from {ab['range_mm']:.2f} to "
        f"{near['range_mm']:.2f}&nbsp;mm (still far more than the 15–50&nbsp;µm piezo "
        f"handoff), and the Abbe lateral/Z ratio worsens from {ab['abbe']:.1f}% to "
        f"{near['abbe']:.1f}% (the absolute lateral walk stays {ab['dx']:.0f}&nbsp;nm/step, "
        f"since it depends on the collet, not r<sub>p</sub>)."
    )

    findings = [
        f"<b>The mechanism doesn't care where the piezo is — until the last lever.</b> "
        f"The motor→rack→wedge→lid-lift chain is fixed by the drive and the wedge at "
        f"d<sub>w</sub>&nbsp;=&nbsp;{wl.LIP_ARM_MM:.2f}&nbsp;mm: the lip rises "
        f"{ab['dz']/ab['ratio']:.1f}&nbsp;nm and the lid rotates "
        f"{wl.as_built_gearing().dphi_rad*1e6:.2f}&nbsp;µrad every step, no matter where "
        f"the piezo sits. The piezo only samples that rotation at its own radius.",
        f"<b>Precision is LINEAR in r<sub>p</sub> (a free lever reduction).</b> "
        f"&Delta;z<sub>tip</sub>&nbsp;=&nbsp;976.2&nbsp;nm&nbsp;&times;&nbsp;r<sub>p</sub>/"
        f"{wl.LIP_ARM_MM:.2f}. Halving the arm halves the step. This is exactly a gear "
        f"reduction, but bought with geometry instead of parts — and it stacks "
        f"multiplicatively with the slow-down gearbox and the leadscrew options.",
        f"<b>Reseat band (what the arches actually allow).</b> The tie-down rails span "
        f"x&nbsp;=&nbsp;&minus;16..+24&nbsp;mm, i.e. r<sub>p</sub>&nbsp;=&nbsp;11..51&nbsp;mm. "
        f"Moving the piezo from the as-built {ab['r_p']:.1f}&nbsp;mm to the front arch "
        f"(r<sub>p</sub>&nbsp;&asymp;&nbsp;{rows[2]['r_p']:.0f}&nbsp;mm) already gives "
        f"{rows[2]['gain']:.2f}&times; finer steps ({rows[2]['dz']:.0f}&nbsp;nm); the mid arch "
        f"(r<sub>p</sub>&nbsp;&asymp;&nbsp;{near['r_p']:.0f}&nbsp;mm) gives "
        f"{near['gain']:.1f}&times; ({near['dz']:.0f}&nbsp;nm).",
        f"<b>The cost #1 — Z range shrinks proportionally.</b> Full-stroke tip Z falls "
        f"from {ab['range_mm']:.2f}&nbsp;mm to {near['range_mm']:.2f}&nbsp;mm. That is still "
        f"~{near['range_mm']*1000/50:.0f}× the 50&nbsp;µm top of the piezo handoff window, so "
        f"the coarse approach has plenty of reach to spare — this is a genuinely cheap "
        f"trade, because we currently have far more Z range than we use.",
        f"<b>The cost #2 — Abbe ratio worsens as 1/r<sub>p</sub>.</b> The absolute lateral "
        f"walk is fixed at {ab['dx']:.0f}&nbsp;nm/step (it is &Delta;&phi;&middot;c, and "
        f"neither &Delta;&phi; nor the collet c change). But because each step now covers "
        f"less Z, the lateral-per-Z climbs from {ab['abbe']:.1f}% to {near['abbe']:.1f}%. "
        f"Keep it in check by keeping the collet standoff c small — c is the only lever on "
        f"the lateral term.",
        f"<b>Net.</b> The printer's instinct is correct: the piezo is on the wrong "
        f"(long) end of the lever for fine Z. Reseating it toward the hinge is the "
        f"single cheapest precision knob on the whole rig — finer than swapping the wedge "
        f"angle and free of the leadscrew/gearbox parts count — as long as you keep "
        f"&ge;~1&nbsp;mm of Z range and a short collet.",
    ]

    equations = [
        ("&Delta;z<sub>wedge</sub> = s &middot; tan&thinsp;&theta;<sub>w</sub> = 976.2 nm/step "
         "&emsp;(fixed by drive + wedge, independent of the piezo)",
         "The lip lift per step — set at the far end of the lid, not where the piezo is."),
        ("&Delta;&phi; = &Delta;z<sub>wedge</sub> / d<sub>w</sub> "
         f"= {wl.as_built_gearing().dphi_rad*1e6:.2f} µrad/step &emsp;(fixed)",
         "Lid rotation per step — also independent of r_p."),
        ("&Delta;z<sub>tip</sub> = &Delta;&phi; &middot; r<sub>p</sub> "
         "= 976.2 nm &middot; r<sub>p</sub> / 120.15",
         "THE knob: tip Z per step is linear in the piezo lever r_p."),
        ("&Delta;x<sub>tip</sub> = &Delta;&phi; &middot; c = 65 nm/step "
         "&emsp;(independent of r<sub>p</sub>);&emsp; &Delta;x/&Delta;z = c / r<sub>p</sub>",
         "Abbe walk: absolute value fixed by the collet; the RATIO to Z worsens as r_p shrinks."),
        ("Z<sub>range</sub> = &Delta;&phi;<sub>total</sub> &middot; r<sub>p</sub> "
         "= 3.5 mm &middot; r<sub>p</sub> / 120.15",
         "Full-stroke tip Z — the range you trade away, also linear in r_p."),
    ]

    assumptions = [
        "Rigid, quasi-static; the drive (rack-pinion), wedge (M12, 3.5/27.5) and lip arm "
        "d_w = 120.15 mm are held at the as-built values — ONLY the piezo/sample lever r_p "
        "is varied (the sample cavity on the bottom plate moves with it to stay under the tip).",
        "Per-step values at the closure limit (phi ~ 0); the <0.05% cos(phi) correction is "
        "the same as in the main gearing report.",
        "Reseat band r_p = 11..51 mm taken from the tie-down-rail span x = -16..+24 mm "
        "(RESUME v33). Going below ~30 mm buys precision but drops Z range under ~0.9 mm.",
        "Collet standoff c = 8 mm (design intent); the lateral term scales with c, so a "
        "shorter collet is the mitigation for the worsened Abbe ratio.",
        "Existing rack-pinion drive (s = 7.67 um/step). The same relocation multiplies "
        "whatever drive is used, including the leadscrew and any slow-down gearbox.",
    ]

    return Investigation(
        slug=SLUG,
        title="Move the Piezo Toward the Hinge? — Lever-Arm vs Precision",
        question=("The piezo/sample junction sits at the far (wedge) end of the "
                  "clamshell. If we reseat it — and the matching sample cavity — back "
                  "toward the hinge (into the tie-down-arch zone), how much finer do the "
                  "steps get, and what does it cost?"),
        params={
            "fixed drive": "rack-pinion, s = 7.67 um/step -> lip lift 976.2 nm/step",
            "fixed lip arm d_w": f"{wl.LIP_ARM_MM:.2f} mm (wedge stays at the lip)",
            "variable": "piezo lever r_p (pin -> piezo); sample cavity moves with it",
            "as-built r_p": f"{ab['r_p']:.2f} mm -> {ab['dz']:.0f} nm/step, range {ab['range_mm']:.2f} mm",
            "closest candidate": f"r_p {near['r_p']:.0f} mm -> {near['dz']:.0f} nm/step "
                                 f"({near['gain']:.1f}x finer), range {near['range_mm']:.2f} mm",
            "reseat band (arches)": "r_p 11..51 mm (rails x -16..+24)",
            "engine": "NumPy closed form + Matplotlib",
        },
        summary=summary,
        findings=findings,
        equations=equations,
        assumptions=assumptions,
        table_text=_table(rows),
        ascii_blocks=[("Piezo position sweep (drive + wedge fixed)", _table(rows))],
        figures=manifest,
        references=[
            "physics/wedge_lever.py: dz_tip = s*tan(theta)*(r_p/d_w); as_built_gearing("
            "lever_mm=r_p) varies only the piezo lever. Fixed as-built values from "
            "WedgeDesign v37.",
            "queries/wedge_lever_gearing.py: the as-built 620 nm/step baseline this "
            "compares against.",
            "RESUME v33: tie-down 'roman arch' rails at x = -16/+4/+24 mm define the "
            "physical reseat band for the piezo over the lid.",
        ],
    )
