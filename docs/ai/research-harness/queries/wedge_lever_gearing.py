"""Query: wedge-driven clamshell — tip Z per stepper motor step (as built).

Reference question (user, 2026-07-07, session 8):

  "Use this rig, exactly as we have it now — how much Z-displacement at
   the tip, per stepper motor step?  Make it clearer and more
   step-by-step, grounded in physics, equations and figures."

Everything is the measured WedgeDesign v37 model: the session-8
`Pinion_v3` (true involute, module 1, z=10 -> 31.4159 mm of stick per
rev), the push stick glued to the M12 wedge (rise 3.5 over run 27.5),
the lid lip riding the wedge at 120.15 mm from the swaged hinge pin, and
the piezo seated at 76.26 mm.  The report walks ONE motor step through
the four reduction stages in order, then does the budgets.  The old
plate-length design sweeps are kept, clearly labeled, as an appendix.
"""

from __future__ import annotations

import math
from pathlib import Path

from models import Investigation
from physics import wedge_lever as wl
from rendering import figures_wedge

SLUG = "wedge-lever-gearing"

# Design-space appendix: previous build, current build, Faraday ceiling.
DEFAULT_LENGTHS_MM = (70.0, 90.0, 120.0)
DEFAULT_WEDGE = "M12"


def _stage_table() -> str:
    """The chain, one stage per row, nominal and true gearbox."""
    g_nom = wl.as_built_gearing()
    g_true = wl.as_built_gearing(steps_per_rev=wl.MOTOR_HALF_STEPS_PER_REV_TRUE)
    lines = [
        "stage  what happens                       factor          nominal      true-gearbox",
        "-" * 92,
        f"  1    one half-step of the 28BYJ-48     1/steps-per-rev  1/4096 rev   1/4075.77 rev",
        f"  2    pinion (m=1, z=10) turns the      x 31.4159 mm/rev {g_nom.travel_per_step_nm:8.1f} nm  {g_true.travel_per_step_nm:8.1f} nm",
        f"       rack: stick + wedge slide s",
        f"  3    wedge slope lifts the lid lip     x tan(7.2527 deg){g_nom.dz_wedge_nm:8.1f} nm  {g_true.dz_wedge_nm:8.1f} nm",
        f"       dz = s * (3.5/27.5)               = x 0.12727",
        f"  4    lever: lift at 120.15 mm arm,     x (76.26/120.15) {g_nom.dz_tip_nm:8.1f} nm  {g_true.dz_tip_nm:8.1f} nm",
        f"       tip under piezo at 76.26 mm       = x 0.63470",
        "-" * 92,
        f"       TIP Z PER MOTOR STEP                               {g_nom.dz_tip_nm:8.1f} nm  {g_true.dz_tip_nm:8.1f} nm",
        f"       (side effect: lateral Abbe walk   x (8/120.15)     {g_nom.dx_tip_nm:8.1f} nm  {g_true.dx_tip_nm:8.1f} nm)",
        "-" * 92,
        f"       lid rotation per step: {g_nom.dphi_rad*1e6:.2f} urad; full 27.5 mm stroke = "
        f"{wl.asbuilt_full_stroke_steps():,.0f} steps",
        f"       full-stroke tip range: {wl.asbuilt_full_range_mm():.3f} mm  "
        f"(lid {wl.CONTACT_INCLUDED_DEG:g} deg -> 0)",
    ]
    return "\n".join(lines)


def _schematic() -> str:
    return r"""
   hinge pin (pivot, ON the parting plane -- swaged hinge)
     o=========================================================.  lid (117.5 mm)
      \            top plate (piezo jaw)                        \
       \                      piezo center [O]                   \  LIP rides the
        \                      8 mm collet  |                 ____\  wedge slope
         \                         + tip    v        crest __/M12 |
   _______\____________________________________tip_______/_______|__________
   |       <-- r_p = 76.26 mm (pin -> piezo center) -->   ^      |
   |       <-- d_w = 120.15 mm (pin -> LIP contact) ------+ -->  |
   |  sample plate (static jaw)          wedge + glued stick <---+-- to pinion
   |_________________________________________________________________________|

   ONE STEP, STAGE BY STAGE:
     1. motor half-step        = 1/4096 output rev
     2. pinion m=1 z=10        -> stick slides s = 31.416 mm / 4096 = 7.671 um
     3. wedge slope 3.5/27.5   -> lip lift  s * tan(7.2527 deg)     = 976.3 nm
     4. lever 76.26/120.15     -> TIP Z     976.3 nm * 0.6347       = 619.7 nm
        (+ lateral Abbe        ->           976.3 nm * 8/120.15     =  65.0 nm)
"""


def run(out_dir: Path, lengths_mm=DEFAULT_LENGTHS_MM,
        wedge_size: str = DEFAULT_WEDGE, gear_ratio: float = 1.0) -> Investigation:
    lengths_mm = tuple(lengths_mm)
    g = wl.as_built_gearing(gear_ratio=gear_ratio)
    g_true = wl.as_built_gearing(steps_per_rev=wl.MOTOR_HALF_STEPS_PER_REV_TRUE,
                                 gear_ratio=gear_ratio)
    g_lead = wl.leadscrew_gearing(gear_ratio=gear_ratio)

    fig_dir = Path(out_dir) / "figures"
    manifest = figures_wedge.generate_all(fig_dir, lengths_mm, wedge_size)

    summary = (
        f"<b>Answer: one motor step moves the tip {g.dz_tip_nm:.0f}&nbsp;nm in Z</b> "
        f"(nominal 4096 half-steps/rev; {g_true.dz_tip_nm:.0f}&nbsp;nm with the true "
        f"63.684:1 gearbox). The chain, in order: one half-step is 1/4096 of a pinion "
        f"rev (Stage&nbsp;1); the module-1, z&nbsp;=&nbsp;10 involute pinion advances the "
        f"push stick s&nbsp;=&nbsp;31.416&nbsp;mm&nbsp;/&nbsp;4096&nbsp;=&nbsp;"
        f"{g.travel_per_step_nm/1000:.3f}&nbsp;µm (Stage&nbsp;2); the stick is glued to "
        f"the M12 wedge, whose 3.5/27.5 slope converts that slide into a "
        f"{g.dz_wedge_nm:.0f}&nbsp;nm lift under the lid lip (Stage&nbsp;3); the lift acts "
        f"on a {g.wedge_arm_mm:.2f}&nbsp;mm arm while the tip hangs at "
        f"{g.lever_mm:.2f}&nbsp;mm, so the lever multiplies by "
        f"{g.lever_ratio:.4f} to give <b>{g.dz_tip_nm:.0f}&nbsp;nm of tip Z per step</b> "
        f"(Stage&nbsp;4). The same rotation walks the tip sideways "
        f"{g.dx_tip_nm:.0f}&nbsp;nm/step through the 8&nbsp;mm collet standoff (Abbe). "
        f"Full wedge stroke = {wl.asbuilt_full_stroke_steps():,.0f} steps for "
        f"{wl.asbuilt_full_range_mm():.2f}&nbsp;mm of tip travel."
    )

    findings = [
        # The answer, stage by stage.
        f"<b>Stage 1 — motor.</b> The 28BYJ-48 is half-stepped: 64 half-steps per motor "
        f"rev &times; the internal gearbox = <b>{wl.MOTOR_HALF_STEPS_PER_REV_NOMINAL:,} "
        f"half-steps per output revolution</b> (nominal 64:1). The true gearbox is "
        f"63.68395:1 &rarr; 4075.77 half-steps/rev; both columns are carried through the "
        f"table and differ by only 0.5%.",
        f"<b>Stage 2 — rack &amp; pinion.</b> `Pinion_v3` (session 8) is a true involute "
        f"gear: module m&nbsp;=&nbsp;1&nbsp;mm, z&nbsp;=&nbsp;10, &alpha;&nbsp;=&nbsp;20&deg; "
        f"(identified from the printed rack itself: flank angle atan(0.82/2.25) = 20.0&deg;, "
        f"pitch = &pi;&nbsp;mm). One pinion rev advances the rack z&middot;&pi;&middot;m = "
        f"<b>31.4159&nbsp;mm</b>, so one motor step slides stick + wedge "
        f"s = 31.4159&nbsp;mm / 4096 = <b>{g.travel_per_step_nm/1000:.4f}&nbsp;µm</b>.",
        f"<b>Stage 3 — wedge.</b> The stick butts (glued) against the M12 wedge riding the "
        f"2.5&nbsp;mm inset channel. Its slope is exactly rise/run = 3.5/27.5 = 0.12727 "
        f"(&theta;<sub>w</sub> = {wl.WEDGE_ANGLE_ASBUILT_DEG:.4f}&deg;, measured from the "
        f"model: crest 89.20 at x&nbsp;&minus;85.15, thin edge flush 85.70 at "
        f"x&nbsp;&minus;57.65). Sliding s changes the height under the lid lip by "
        f"&Delta;z = s&middot;tan&theta;<sub>w</sub> = <b>{g.dz_wedge_nm:.1f}&nbsp;nm per "
        f"step</b>.",
        f"<b>Stage 4 — lever.</b> The lip contact sits d<sub>w</sub> = 120.15&nbsp;mm from "
        f"the hinge pin; the lift rotates the lid by &Delta;&phi; = &Delta;z/d<sub>w</sub> "
        f"= {g.dphi_rad*1e6:.3f}&nbsp;µrad/step. The piezo (and the tip 8&nbsp;mm below "
        f"it) sits INBOARD at r<sub>p</sub> = 76.26&nbsp;mm, so the tip sees only "
        f"r<sub>p</sub>/d<sub>w</sub> = 0.6347 of the lift: <b>&Delta;z<sub>tip</sub> = "
        f"{g.dz_tip_nm:.1f}&nbsp;nm per motor step</b> ({g_true.dz_tip_nm:.1f} with the "
        f"true gearbox).",
        f"<b>Stage 4b — the sideways cost.</b> The same &Delta;&phi; acting on the 8&nbsp;mm "
        f"collet standoff walks the tip laterally {g.dx_tip_nm:.1f}&nbsp;nm/step (Abbe "
        f"error). Invariant: lateral/Z = c/r<sub>p</sub> = 8/76.26 = "
        f"{wl.COLLET_STANDOFF_MM/wl.ASBUILT_LEVER_MM*100:.1f}% of every approach step, "
        f"whatever the drive — remember it when landing on a specific surface site.",
        # Budgets.
        f"<b>Approach budget.</b> Full wedge run 27.5&nbsp;mm = "
        f"{wl.asbuilt_full_stroke_steps():,.0f} steps (0.875 pinion rev) for "
        f"{wl.asbuilt_full_range_mm():.3f}&nbsp;mm of total tip travel (lid "
        f"{wl.CONTACT_INCLUDED_DEG:g}&deg; &rarr; 0&deg;). Crossing the piezo's "
        f"{wl.PIEZO_REACH_UM[0]:g}–{wl.PIEZO_REACH_UM[1]:g}&nbsp;µm Z reach takes "
        f"<b>{g.steps_across_reach_um(wl.PIEZO_REACH_UM[0]):,.0f}–"
        f"{g.steps_across_reach_um(wl.PIEZO_REACH_UM[1]):,.0f} steps</b> — enough for a "
        f"guarded approach (step &rarr; piezo sweep &rarr; check), but each single step is "
        f"~{g.dz_tip_nm/wl.TUNNELING_WINDOW_NM:,.0f}&times; the ~1&nbsp;nm tunneling "
        f"window, so the LAST gap must always be closed by the piezo, never by a step.",
        f"<b>Upgrade path (round 2): M3 leadscrew.</b> Swapping the rack-pinion for the "
        f"documented 0.5&nbsp;mm/rev leadscrew divides Stage 2 by "
        f"{g.travel_per_step_nm/g_lead.travel_per_step_nm:.1f}&times;: s = 122.07&nbsp;nm/step "
        f"&rarr; tip Z = <b>{g_lead.dz_tip_nm:.2f}&nbsp;nm/step</b> — finer than the best "
        f"documented longboard stack ({wl.BEST_LONGBOARD_NM_PER_STEP:g}&nbsp;nm/step) and "
        f"~160 steps per µm of tip travel. Same geometry, same equations; only "
        f"s changes.",
        f"<b>Context.</b> At {g.dz_tip_nm:.0f}&nbsp;nm/step the rig is ~23&times; coarser "
        f"than the best documented longboard fine-approach "
        f"({wl.BEST_LONGBOARD_NM_PER_STEP:g}&nbsp;nm/step) but covers its full range in "
        f"under one pinion turn — it is the COARSE approach stage by design; fineness "
        f"beyond the piezo handoff is the leadscrew's job (previous finding). "
        f"Design-space sweeps (plate length, other washers in the kit) are in the "
        f"appendix figures; the lever ratio and wedge angle remain the only real "
        f"gearing knobs — plate length barely matters.",
    ]

    equations = [
        ("s = z &middot; &pi; &middot; m / N = 31.4159 mm / 4096 = 7.671 µm per half-step",
         "Stage 2 — stick travel per motor half-step (module-1, z=10 involute pinion; "
         "N = half-steps per output rev; true N = 4075.77)."),
        ("&Delta;z<sub>wedge</sub> = s &middot; tan&thinsp;&theta;<sub>w</sub>,&emsp;"
         "tan&thinsp;&theta;<sub>w</sub> = 3.5 / 27.5 = 0.12727",
         "Stage 3 — lift under the lid lip per step (wedge slope measured from the model)."),
        ("&Delta;&phi; = &Delta;z<sub>wedge</sub> / d<sub>w</sub>,&emsp;d<sub>w</sub> = 120.15 mm",
         "Stage 4 — lid rotation per step (lift acting at the lip arm)."),
        ("&Delta;z<sub>tip</sub> = &Delta;&phi; &middot; (r<sub>p</sub>cos&phi; + c&thinsp;sin&phi;) "
         "&asymp; &Delta;&phi; &middot; r<sub>p</sub> = s &middot; tan&thinsp;&theta;<sub>w</sub> "
         "&middot; r<sub>p</sub>/d<sub>w</sub>",
         "Tip approach per step at opening &phi; (&phi; &le; 1.67&deg; &rarr; cos&phi; &ge; 0.9996, "
         "so the closed-gap form is exact to 0.04%)."),
        ("&Delta;x<sub>tip</sub> &asymp; &Delta;&phi; &middot; c = s &middot; "
         "tan&thinsp;&theta;<sub>w</sub> &middot; c/d<sub>w</sub>,&emsp;c = 8 mm",
         "Stage 4b — lateral tip walk from the collet standoff (Abbe error)."),
        ("&Delta;z<sub>tip</sub> = 7671 nm &times; 0.12727 &times; 0.63470 = 619.7 nm/step",
         "The whole chain, numbers in: THE answer (622.8 nm with the true 63.684:1 gearbox)."),
    ]

    assumptions = [
        "Rigid bodies, quasi-static: no compliance in plates, hinge, wedge contact, stick, "
        "or gear mesh; no backlash (the ~0.29 mm rack-pinion backlash and the clamshell "
        "bias spring set the preload direction but do not change the per-step ratio).",
        "As-built geometry from WedgeDesign v37 (2026-07-07): lip arm 120.15 mm, piezo "
        "lever 76.26 mm (disc axis as seated; the bore axis is 76.18 — a 0.1% difference), "
        "wedge slope exactly 3.5/27.5.",
        "Per-step values at closure (phi = 0); the lid never opens past 1.67 deg in "
        "operation, so cos(phi) corrections stay below 0.05%.",
        "Tip rigidly attached 8 mm below the piezo center (collet standoff, design intent — "
        "the collet mockup is still to be modeled); piezo actuation excluded (motor chain "
        "only).",
        "28BYJ-48 half-step positions treated as uniform; real step-to-step nonuniformity "
        "and load-dependent lag are not modeled (they matter for open-loop position "
        "accuracy, not for the mean per-step ratio).",
        "Design-space appendix keeps the old layout rules (wedge at plate front edge, bore "
        "setback 16 mm) and catalog wedge angles for comparison only.",
    ]

    table_text = _stage_table()

    return Investigation(
        slug=SLUG,
        title="Tip Z per Motor Step — the As-Built Wedge/Clamshell Drive Chain",
        question=("Use the rig exactly as built (WedgeDesign v37): how much tip Z "
                  "displacement per stepper motor step? Step-by-step chain: 28BYJ-48 "
                  "half-step -> m1 z10 involute pinion -> rack/stick -> glued M12 wedge "
                  "-> lid lip lever -> tip."),
        params={
            "STAGE 1  motor": f"28BYJ-48, {wl.MOTOR_HALF_STEPS_PER_REV_NOMINAL:,} half-steps/rev nominal (4075.77 true)",
            "STAGE 2  pinion/rack": f"m=1, z=10 involute (Pinion_v3) -> {wl.MM_PER_REV:.4f} mm/rev -> s = {g.travel_per_step_nm/1000:.4f} um/step",
            "STAGE 3  wedge": f"M12, slope 3.5/27.5 = 0.12727 ({wl.WEDGE_ANGLE_ASBUILT_DEG:.4f} deg) -> {g.dz_wedge_nm:.1f} nm/step at the lip",
            "STAGE 4  lever": f"d_w = {wl.LIP_ARM_MM:.2f} mm, r_p = {wl.ASBUILT_LEVER_MM:.2f} mm -> ratio {g.lever_ratio:.4f}",
            "ANSWER  tip Z per step": f"{g.dz_tip_nm:.1f} nm (nominal) / {g_true.dz_tip_nm:.1f} nm (true gearbox)",
            "side effect  lateral/step": f"{g.dx_tip_nm:.1f} nm (Abbe, c = {wl.COLLET_STANDOFF_MM:g} mm)",
            "full stroke": f"{wl.asbuilt_full_stroke_steps():,.0f} steps -> {wl.asbuilt_full_range_mm():.3f} mm of tip Z",
            "engine": "NumPy (closed form) + Matplotlib",
        },
        summary=summary,
        findings=findings,
        equations=equations,
        assumptions=assumptions,
        table_text=table_text,
        ascii_blocks=[
            ("The as-built chain, one step end to end (schematic)", _schematic()),
            ("Stage table (nominal and true-gearbox columns)", table_text),
        ],
        figures=manifest,
        references=[
            "Fusion model WedgeDesign v37 (2026-07-07, session 8): pin axis (35, 85.7) ON "
            "the parting plane (swaged hinge); piezo disc axis x = -41.26 -> r_p = 76.26 mm; "
            "lid lip arm 120.15 mm; M12 wedge crest 89.20 at x -85.15, thin edge flush "
            "85.70 at x -57.65 (slope 3.5/27.5); Pinion_v3 = true involute m=1 z=10 "
            "alpha=20 deg; rig = Rotor_revolute + Rack_slider + Lid_revolute + two "
            "MotionLinks (one rotor drag runs the whole chain).",
            "wedge-assembly/docs-for-ai/session8-pinion-involute-anim-piezo.md: the "
            "involute identification (rack flank atan(0.82/2.25) = 20.0 deg, pitch = pi) "
            "and the drive-chain rig.",
            "Meeting note '23. Mechanical Optimizations': M3 leadscrew alternative, "
            "0.5 mm/rev / 4096 = 122.07 nm/step; best documented longboard stack "
            "~26.6 nm/step.",
            "wedge-assembly/docs-for-ai/off-the-shelf-wedge-washers.md and "
            "wedge-size-guide-extrapolation.md: Glarks beveled-washer kit geometry "
            "(M12: 27.5 mm square, 2.5->6.0 mm; catalog angle 7.26 deg vs modeled 7.2527).",
            "physics/piezo_tip.py (tip-displacement report): the Abbe/cosine framework "
            "the collet lateral term reuses.",
        ],
    )
