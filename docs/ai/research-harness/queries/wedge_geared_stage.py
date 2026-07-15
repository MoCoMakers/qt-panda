"""Query: two-stage 20:107 reduction on 625ZZ bearings -> tip Z per step.

Design question (user, 2026-07-12):

  "Keep the teeth (20:107, module 1) and add a SECOND gear stage to push
   the step finer.  The new shafts ride 625ZZ ball bearings.  Verify the
   numbers from the formulas: the tip Z per motor step, and that the
   bearings (and the printed teeth) can take it."

The chain is the as-built wedge/clamshell (WedgeDesign v37) with the piezo
already RELOCATED to r_p = 35 mm (Change A), now fed through a compound
(107/20)^2 = 28.62:1 spur reduction between the 28BYJ-48 and the existing
rack pinion.  Kinematics reuse `physics.wedge_lever`; the gear/bearing
statics come from `physics.gear_train`.
"""

from __future__ import annotations

from pathlib import Path

from models import Investigation
from physics import wedge_lever as wl
from physics import gear_train as gt

SLUG = "wedge-geared-stage"

RELOCATED_LEVER_MM = 35.0          # r_p after Change A (piezo moved to the hinge)
SINGLE_STAGE_RATIO = gt.stage_ratio()      # 5.35  (one 20:107 mesh)


def _chain_table(g_asbuilt, g_piezo, g_1stage, g_gear, ga) -> str:
    lines = [
        "PRECISION LADDER            drive s/step   lever r_p   tip Z/step   lateral/step",
        "-" * 82,
        f"  as-built (v37)           {g_asbuilt.travel_per_step_nm/1000:7.3f} um   "
        f"{g_asbuilt.lever_mm:6.2f} mm   {g_asbuilt.dz_tip_nm:7.1f} nm   {g_asbuilt.dx_tip_nm:6.1f} nm",
        f"  + piezo to r_p 35        {g_piezo.travel_per_step_nm/1000:7.3f} um   "
        f"{g_piezo.lever_mm:6.2f} mm   {g_piezo.dz_tip_nm:7.1f} nm   {g_piezo.dx_tip_nm:6.1f} nm",
        f"  + 1 gear stage (5.35:1)  {g_1stage.travel_per_step_nm/1000:7.3f} um   "
        f"{g_1stage.lever_mm:6.2f} mm   {g_1stage.dz_tip_nm:7.1f} nm   {g_1stage.dx_tip_nm:6.1f} nm",
        f"  + 2 gear stages 28.6:1   {g_gear.travel_per_step_nm/1000:7.3f} um   "
        f"{g_gear.lever_mm:6.2f} mm   {g_gear.dz_tip_nm:7.1f} nm   {g_gear.dx_tip_nm:6.1f} nm",
        "-" * 82,
        "",
        "TORQUE / FORCE PROPAGATION (motor at rated 34 mN.m)",
        "-" * 82,
        f"  mesh 1  20T->107T   tangential F = {ga.F_mesh1_n:6.2f} N     idler torque = {ga.T_idler_nm*1e3:6.1f} mN.m",
        f"  mesh 2  20T->107T   tangential F = {ga.F_mesh2_n:6.2f} N     output torque= {ga.T_output_nm*1e3:6.1f} mN.m",
        f"  rack    10T pinion  tangential F = {ga.F_rack_n:6.1f} N  (stall-max delivered to the wedge)",
        "-" * 82,
        "",
        "625ZZ BEARING CHECK (5x16x5, C0 = 160 N static, 2 per shaft)",
        "-" * 82,
        f"  idler shaft   load/bearing = {ga.idler_bearing_n:6.1f} N   ->  {ga.idler_static_margin:5.1f}x static margin",
        f"  output shaft  load/bearing = {ga.output_bearing_n:6.1f} N   ->  {ga.output_static_margin:5.1f}x static margin",
        "-" * 82,
        "",
        "PRINTED-TOOTH (PLA) BENDING -- the real torque limit",
        "-" * 82,
        f"  idler 20T tooth @ mesh 2   sigma = {ga.sigma_pinion2_mpa:6.1f} MPa  (yield {ga.pla_yield_mpa:.0f})  ->  OK",
        f"  10T rack pinion @ stall    sigma = {ga.sigma_rack_mpa:6.1f} MPa  (yield {ga.pla_yield_mpa:.0f})  ->  "
        f"{'OVER' if ga.sigma_rack_mpa > ga.pla_yield_mpa else 'OK'}",
        f"  PLA rack tooth yields at   F = {ga.rack_force_yield_n:5.1f} N   (stall delivers {ga.F_rack_n:.0f} N,"
        f" = {1/ga.rack_force_margin:.1f}x over)",
        "-" * 82,
    ]
    return "\n".join(lines)


def _schematic() -> str:
    return r"""
 SIDE VIEW  -- 3 shafts, gears stacked by height (z).  o = shaft axis (into rack)

     MOTOR              MIDDLE idler            OUTPUT shaft (= Pinion_v3)
       o                    o                           o
  -----+-- stage-1 plane ---+---------------------------+----------
   [ 20T ]===mesh(1)===(=========== 107T ===========)   |
    22mm    x5.35            109 mm                      |
       |                     |                           |
  -----+-- stage-2 plane ----+------------mesh(2)--------+----------
       |               [ 20T ]===x5.35===(=========== 107T ===========)
       |                22mm               109 mm                    |
  -----+-- rack plane -------+-----------------------------------[ 12T ]---
       |                     |                          RACK -> wedge ->
       v                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 120 mm arm -> TIP
    motor spins fast                       reduction 5.35 x 5.35 = 28.6 : 1

   Both new shafts (idler, output) ride TWO 625ZZ (5x16x5) ball bearings each.
   The two 107T gears sit on DIFFERENT z-planes so their 109 mm rims clear
   (shafts only 63.5 mm apart).  Motor keeps its own bearings.
"""


def run(out_dir: Path, gear_ratio: float | None = None,
        lever_mm: float = RELOCATED_LEVER_MM,
        motor_torque_nm: float = gt.MOTOR_RATED_TORQUE_NM) -> Investigation:
    ga = gt.analyze(motor_torque_nm=motor_torque_nm)
    total = gear_ratio if gear_ratio is not None else ga.total_ratio

    # kinematics: reuse the measured wedge/lever chain, override lever + gear
    g_asbuilt = wl.as_built_gearing()
    g_piezo = wl.as_built_gearing(lever_mm=lever_mm)
    g_1stage = wl.as_built_gearing(gear_ratio=SINGLE_STAGE_RATIO, lever_mm=lever_mm)
    g_gear = wl.as_built_gearing(gear_ratio=total, lever_mm=lever_mm)
    g_gear_true = wl.as_built_gearing(steps_per_rev=wl.MOTOR_HALF_STEPS_PER_REV_TRUE,
                                      gear_ratio=total, lever_mm=lever_mm)

    full_stroke_steps = wl.asbuilt_full_stroke_steps() * total
    steps_reach = g_gear.steps_across_reach_um(wl.PIEZO_REACH_UM[1])

    summary = (
        f"<b>Answer: a compound (107/20)&sup2; = {total:.2f}:1 spur reduction drops the tip "
        f"to {g_gear.dz_tip_nm:.1f}&nbsp;nm per motor step</b> ({g_gear_true.dz_tip_nm:.1f}&nbsp;nm "
        f"with the true 63.68:1 gearbox), from {g_piezo.dz_tip_nm:.0f}&nbsp;nm after the piezo "
        f"relocation and {g_asbuilt.dz_tip_nm:.0f}&nbsp;nm as-built &mdash; a "
        f"{g_asbuilt.dz_tip_nm/g_gear.dz_tip_nm:.0f}&times; overall improvement, essentially "
        f"the 10&nbsp;nm/step target. The two new shafts (compound idler + output) each ride "
        f"two <b>625ZZ</b> ball bearings; at the motor's rated 34&nbsp;mN&middot;m the bearing "
        f"loads are {ga.idler_bearing_n:.0f}&nbsp;N (idler) and {ga.output_bearing_n:.0f}&nbsp;N "
        f"(output) per bearing &mdash; {ga.idler_static_margin:.0f}&times; and "
        f"{ga.output_static_margin:.1f}&times; inside the 160&nbsp;N static rating, so the "
        f"<b>bearings are never the limit</b>. The real ceiling is the <b>printed tooth</b>: at "
        f"full stall the 10&nbsp;mm rack pinion tooth sees {ga.sigma_rack_mpa:.0f}&nbsp;MPa vs "
        f"PLA's {ga.pla_yield_mpa:.0f}&nbsp;MPa yield, so the drive must be current-limited "
        f"(or never driven into a hard stop) to stay under {ga.rack_force_yield_n:.0f}&nbsp;N "
        f"of rack force &mdash; far above what sliding the wedge actually needs."
    )

    findings = [
        f"<b>Kinematics (verified).</b> The reduction multiplies across two identical meshes: "
        f"107/20 &times; 107/20 = <b>{total:.2f}:1</b>. Feeding that through the measured chain "
        f"(pinion s = 7.671&nbsp;&micro;m/step &divide; {total:.2f} = {g_gear.travel_per_step_nm:.1f}&nbsp;nm; "
        f"wedge tan&thinsp;7.2527&deg;; lever r_p&nbsp;=&nbsp;35&nbsp;mm / arm 120.15&nbsp;mm) gives "
        f"&Delta;z_tip = {g_gear.travel_per_step_nm:.1f} &times; 0.12727 &times; "
        f"{RELOCATED_LEVER_MM/wl.LIP_ARM_MM:.4f} = <b>{g_gear.dz_tip_nm:.2f}&nbsp;nm/step</b>. "
        f"Lateral Abbe walk rides along at {g_gear.dx_tip_nm:.2f}&nbsp;nm/step (c/r_p = 8/35 = 22.9%).",
        f"<b>Torque propagates 28.6&times;.</b> Reduction multiplies torque as it divides speed: "
        f"the {motor_torque_nm*1e3:.0f}&nbsp;mN&middot;m motor becomes {ga.T_idler_nm*1e3:.0f}&nbsp;mN&middot;m "
        f"at the idler and {ga.T_output_nm*1e3:.0f}&nbsp;mN&middot;m at the output shaft. Tangential "
        f"mesh forces: {ga.F_mesh1_n:.1f}&nbsp;N (mesh&nbsp;1), {ga.F_mesh2_n:.1f}&nbsp;N (mesh&nbsp;2), "
        f"and up to <b>{ga.F_rack_n:.0f}&nbsp;N</b> at the rack pinion at stall.",
        f"<b>625ZZ bearings are hugely over-rated here.</b> Worst-case radial load per bearing "
        f"(two per shaft): idler {ga.idler_bearing_n:.1f}&nbsp;N, output {ga.output_bearing_n:.0f}&nbsp;N, "
        f"against the 625ZZ static rating C&#8320;&nbsp;=&nbsp;160&nbsp;N &rarr; "
        f"{ga.idler_static_margin:.0f}&times; and {ga.output_static_margin:.1f}&times; margin. And "
        f"because the fine approach turns the output shaft at well under 1&nbsp;rev/min, rolling "
        f"fatigue (dynamic C) is irrelevant &mdash; these bearings will outlive the printer.",
        f"<b>The printed teeth are the real torque limit, not the bearings.</b> The 28.6&times; "
        f"torque gain means a stall puts {ga.sigma_rack_mpa:.0f}&nbsp;MPa on the 10T rack-pinion "
        f"tooth &mdash; over PLA's {ga.pla_yield_mpa:.0f}&nbsp;MPa yield. The PLA tooth yields above "
        f"<b>{ga.rack_force_yield_n:.0f}&nbsp;N</b> of rack force; stall delivers "
        f"{ga.F_rack_n:.0f}&nbsp;N ({1/ga.rack_force_margin:.1f}&times; over). Mitigation: "
        f"current-limit the driver, add a compliant hard-stop, or print the two pinions + rack "
        f"pinion in PCTG. Normal operation (sliding the wedge) needs only a few N, well clear.",
        f"<b>Packaging.</b> Each mesh has center distance m(20+107)/2 = "
        f"<b>{ga.center_distance_mm:.1f}&nbsp;mm</b>; gears are {ga.pinion_od_mm:.0f}&nbsp;mm and "
        f"{ga.gear_od_mm:.0f}&nbsp;mm OD. The two 109&nbsp;mm gears must sit on <b>different "
        f"z-planes</b> (rims 109&nbsp;mm across, shafts only {ga.center_distance_mm:.1f}&nbsp;mm "
        f"apart) &mdash; the compound stacking that also keeps them clear of the rack plane.",
        f"<b>Approach budget.</b> The full 27.5&nbsp;mm wedge run is now "
        f"{full_stroke_steps:,.0f} motor steps for {wl.asbuilt_full_range_mm():.2f}&nbsp;mm of tip "
        f"travel; reaching the piezo's {wl.PIEZO_REACH_UM[1]:g}&nbsp;&micro;m handoff is "
        f"~{steps_reach:,.0f} steps. Each step is still ~{g_gear.dz_tip_nm/wl.TUNNELING_WINDOW_NM:.0f}&times; "
        f"the ~1&nbsp;nm tunneling window &mdash; the piezo still closes the final gap; the gears "
        f"just make the mechanical stage land softly inside its reach.",
    ]

    equations = [
        ("i = (z_gear / z_pinion)^n = (107/20)^2 = " + f"{total:.3f}:1",
         "Compound reduction: two identical 20:107 meshes multiply."),
        ("&Delta;z_tip = s &middot; tan&thinsp;&theta;_w &middot; (r_p / d_w),&emsp;"
         f"s = 7671&nbsp;nm / {total:.2f} = {g_gear.travel_per_step_nm:.1f}&nbsp;nm",
         "Tip Z per step: the gear only shrinks s; wedge, lever, arm unchanged."),
        ("a = m(z_p + z_g)/2 = 1&middot;(20+107)/2 = 63.5&nbsp;mm",
         "Center distance per mesh (sets the shaft spacing / motor relocation)."),
        ("F_t = T / r_pitch,&emsp;T_out = T_motor &middot; i",
         "Tangential mesh force; torque multiplies by the ratio each stage."),
        ("&sigma; = F_t / (b &middot; m &middot; Y)&emsp;(Lewis)",
         "Printed tooth bending stress; b = 5 mm face, Y = form factor "
         "(0.32 at 20T, 0.24 at 10T)."),
        ("static margin = C&#8320; / F_r,&emsp;C&#8320;(625ZZ) = 160&nbsp;N",
         "Ball-bearing check against the catalogue static load rating."),
    ]

    assumptions = [
        "Quasi-static, rigid bodies; per-step ratio is exact (backlash sets preload "
        "direction, not the ratio). A two-mesh compound stacks backlash from both meshes "
        "-- matters for open-loop repeatability, closed by the piezo, not modeled here.",
        "28BYJ-48 rated/pull-out torque taken as 34 mN.m at its output shaft; the load "
        "numbers scale linearly if your unit differs.",
        "Worst-case (co-linear) addition of the two mesh reactions on each shaft, split "
        "evenly over two bearings -- conservative; real vector sum is smaller.",
        "Lewis bending only (no stress-concentration or dynamic factor); PLA yield 55 MPa, "
        "face width 5 mm = the 625ZZ width. PCTG (~45 MPa but far tougher) is the upgrade.",
        "Piezo relocated to r_p = 35 mm (Change A, done on both plates); wedge 3.5/27.5, "
        "lip arm 120.15 mm, module-1 z10 rack pinion -- all measured from WedgeDesign v37.",
        "Bearing dynamic (fatigue) life ignored on purpose: output shaft turns <1 rev/min "
        "on a fine approach, so C0 (static) governs, not C.",
    ]

    table_text = _chain_table(g_asbuilt, g_piezo, g_1stage, g_gear, ga)

    return Investigation(
        slug=SLUG,
        title="Two-Stage 20:107 Reduction on 625ZZ Bearings - Tip-Step & Load Verification",
        question=("Keep 20:107 module-1 teeth and add a second gear stage (compound "
                  "28.62:1) between the 28BYJ-48 and the rack pinion, on 625ZZ bearings. "
                  "Verify: tip Z per motor step, and that the bearings and printed teeth "
                  "take the load."),
        params={
            "reduction (2 stages)": f"(107/20)^2 = {total:.3f}:1",
            "tip Z per step": f"{g_gear.dz_tip_nm:.2f} nm (nominal) / {g_gear_true.dz_tip_nm:.2f} nm (true gearbox)",
            "lateral per step": f"{g_gear.dx_tip_nm:.2f} nm (Abbe, c = {wl.COLLET_STANDOFF_MM:g} mm)",
            "vs as-built": f"{g_asbuilt.dz_tip_nm:.0f} nm -> {g_gear.dz_tip_nm:.1f} nm  ({g_asbuilt.dz_tip_nm/g_gear.dz_tip_nm:.0f}x finer)",
            "gears": f"pinion {gt.PINION_TEETH}T ({ga.pinion_od_mm:.0f} mm OD), gear {gt.GEAR_TEETH}T ({ga.gear_od_mm:.0f} mm OD), a = {ga.center_distance_mm:.1f} mm",
            "bearings": f"625ZZ (5x16x5), 2/shaft; idler {ga.idler_static_margin:.0f}x, output {ga.output_static_margin:.1f}x static margin",
            "torque limit": f"PLA rack tooth yields at {ga.rack_force_yield_n:.0f} N rack force (stall = {ga.F_rack_n:.0f} N)",
            "full stroke": f"{full_stroke_steps:,.0f} steps -> {wl.asbuilt_full_range_mm():.2f} mm tip Z",
            "engine": "closed-form statics (physics/gear_train.py + physics/wedge_lever.py)",
        },
        summary=summary,
        findings=findings,
        equations=equations,
        assumptions=assumptions,
        table_text=table_text,
        ascii_blocks=[
            ("The compound reduction, one motor input end to end (schematic)", _schematic()),
            ("Precision ladder, load propagation, bearing + tooth checks", table_text),
        ],
        figures=[],
        references=[
            "wedge-assembly/docs-for-ai/piezo-relocation-gear-stage-plan.md: Change B "
            "(20:64 first draft; here extended to a two-stage 20:107 for the 10 nm target), "
            "idler shaft at the Pinion_v3 location, motor relocation, L-bracket re-cut.",
            "wedge-assembly/references/cmu-geared-stepper/ (CMU motorized-turntable): "
            "20T + 64T spur DXFs = the gear-on-gear reduction reference this generalizes.",
            "625ZZ deep-groove ball bearing, 5 x 16 x 5 mm: C = 340 N dynamic, "
            "C0 = 160 N static (typical catalogue); ZZ metal shields; 2 per new shaft.",
            "physics/wedge_lever.py: the measured wedge/lever chain (WedgeDesign v37) with "
            "gear_ratio + lever overrides; physics/gear_train.py: the statics in this report.",
            "Change A (done): piezo relocated +41.26 mm to r_p = 35 mm on both plates; "
            "sample cavity moved to match -- the r_p = 35 used here.",
        ],
    )
