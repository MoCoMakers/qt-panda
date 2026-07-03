"""Query: tip displacement for a centrally located tip vs tip length at a 2deg offset.

Reference question (verbatim from the user):

  "Show me the tip displacement for a centrally located tip on a piezo if
   its length is 1 mm vs 10 mm, for a 2 degree offset."
"""

from __future__ import annotations

from pathlib import Path

from models import Investigation
from physics.piezo_tip import tip_displacement_mm_deg
from rendering import figures
from rendering.ascii_art import tilt_schematic, results_table

SLUG = "tip-displacement-length"

# Defaults that encode the reference question.
DEFAULT_THETA_DEG = 2.0
DEFAULT_LENGTHS_MM = (1.0, 10.0)


def run(out_dir: Path, theta_deg: float = DEFAULT_THETA_DEG,
        lengths_mm=DEFAULT_LENGTHS_MM) -> Investigation:
    lengths_mm = tuple(lengths_mm)
    short_L, long_L = lengths_mm[0], lengths_mm[-1]
    short = tip_displacement_mm_deg(short_L, theta_deg)
    long = tip_displacement_mm_deg(long_L, theta_deg)
    ratio = long.lateral_um / short.lateral_um if short.lateral_um else float("nan")

    fig_dir = Path(out_dir) / "figures"
    manifest = figures.generate_all(fig_dir, theta_deg, lengths_mm)

    summary = (
        f"For a rigid tip tilted by a <b>{theta_deg:g}&deg;</b> offset, the apex "
        f"sweeps sideways by <b>&Delta;x = L&middot;sin&theta;</b>. A "
        f"<b>{short_L:g}&nbsp;mm</b> tip moves <b>{short.lateral_um:.1f}&nbsp;&micro;m</b> "
        f"laterally, while a <b>{long_L:g}&nbsp;mm</b> tip moves "
        f"<b>{long.lateral_um:.0f}&nbsp;&micro;m</b> &mdash; a <b>{ratio:.0f}&times;</b> "
        f"increase, exactly tracking the {long_L/short_L:.0f}&times; length ratio. "
        f"The vertical foreshortening (&Delta;z = L(1&minus;cos&theta;)) is far smaller: "
        f"{short.vertical_um:.2f}&nbsp;&micro;m and {long.vertical_um:.2f}&nbsp;&micro;m "
        f"respectively, because at small angles it grows with &theta;&sup2;/2 rather than &theta;."
    )

    findings = [
        f"Lateral apex error is <b>linear in tip length</b>: a 10&times; longer tip "
        f"gives a 10&times; larger lateral error ({short.lateral_um:.1f} &micro;m &rarr; "
        f"{long.lateral_um:.0f} &micro;m at {theta_deg:g}&deg;).",
        f"Vertical (height) error is second-order in angle: only "
        f"{short.vertical_um:.2f} &micro;m at 1&nbsp;mm and {long.vertical_um:.2f} &micro;m "
        f"at 10&nbsp;mm &mdash; ~{short.lateral_um/short.vertical_um:.0f}&times; smaller than the lateral term.",
        "This is the classic <b>Abbe / cosine error</b>: an angular offset is "
        "amplified into translation in proportion to the standoff length between "
        "the pivot and the measurement point (the apex).",
        "Practical implication for a scanning probe: keep the tip <b>short</b>. "
        "Every extra millimetre of standoff turns the same mounting tilt into "
        f"~{tip_displacement_mm_deg(1.0, theta_deg).lateral_um:.0f} &micro;m more lateral registration error.",
    ]

    equations = [
        ("&Delta;x = L &middot; sin&thinsp;&theta;",
         "Lateral displacement of the apex (dominant term)."),
        ("&Delta;z = L &middot; (1 &minus; cos&thinsp;&theta;)",
         "Vertical foreshortening of the apex."),
        ("&Delta;r = 2&thinsp;L &middot; sin(&theta;/2)",
         "Total apex displacement magnitude = &radic;(&Delta;x&sup2; + &Delta;z&sup2;)."),
        ("small angle:&nbsp; &Delta;x &asymp; L&theta;,&nbsp;&nbsp; &Delta;z &asymp; L&theta;&sup2;/2",
         "Why lateral error dominates: it is first-order in &theta;, vertical is second-order."),
    ]

    assumptions = [
        "The tip is treated as a rigid lever; bending/compliance of the tip itself is neglected.",
        "The angular offset is a fixed tilt of the mounting face (mechanical misalignment "
        "or piezo-induced tilt), not a function of scan position.",
        "'Centrally located' means the tip sits on the rotation axis of the face, so the "
        "displacement comes purely from the standoff length L, not an off-axis lever arm.",
        "Linear, quasi-static geometry; no dynamic/resonance effects, hysteresis, or creep.",
        "Angle and length are independent inputs; results scale exactly with L and "
        "with sin/cos of theta.",
    ]

    table_text = results_table(theta_deg, lengths_mm)
    schematic = tilt_schematic(theta_deg, lengths_mm)

    return Investigation(
        slug=SLUG,
        title="Piezo Tip Displacement vs. Tip Length at a 2&deg; Offset",
        question=("Show me the tip displacement for a centrally located tip on a piezo "
                  "if its length is 1 mm vs 10 mm, for a 2 degree offset."),
        params={
            "angular offset theta": f"{theta_deg:g} deg ({theta_deg*0.0174533:.5f} rad)",
            "tip lengths L": ", ".join(f"{L:g} mm" for L in lengths_mm),
            "model": "rigid-lever Abbe/cosine error, quasi-static",
            "engine": "NumPy (closed form) + Matplotlib",
        },
        summary=summary,
        findings=findings,
        equations=equations,
        assumptions=assumptions,
        table_text=table_text,
        ascii_blocks=[
            ("Tilt geometry (schematic)", schematic),
            ("Computed results", table_text),
        ],
        figures=manifest,
        references=[
            "Abbe error / cosine error: an angular error produces a translational "
            "error proportional to the standoff distance (Ernst Abbe, 1890).",
            "Standard rigid-body rotation of a point at radius L about a pivot: "
            "displacement components (L sin theta, L(1-cos theta)).",
            "Context: qt-panda STM uses an X/Y/Z piezo scanner; tip standoff geometry "
            "sets how mounting tilt couples into lateral scan registration error.",
        ],
    )
