"""Wedge-driven clamshell gearing: stepper step -> tip Z motion.

Physical picture (the AS-BUILT rig, WedgeDesign v37, session 8)
---------------------------------------------------------------
The QTPanda approach stage is a hinged lever driven through a 4-stage
reduction chain.  One motor step propagates like this:

  Stage 1  MOTOR      one 28BYJ-48 half-step = 1/4096 of an output rev
  Stage 2  RACK       the z=10, module-1 pinion advances the push stick
                      by (10 * pi) mm per rev            -> s  per step
  Stage 3  WEDGE      the stick is glued to the M12 wedge; sliding it by
                      s changes the height under the lid lip by
                          dz_wedge = s * tan(theta_w)
  Stage 4  LEVER      that lift acts at the lip arm d_w from the hinge
                      pin, rotating the lid by
                          dphi = dz_wedge / d_w
                      and the tip (under the piezo at r_p, with a collet
                      standoff c below the plate) moves
                          dz_tip = dphi * (r_p*cos(phi) + c*sin(phi))
                          dx_tip = dphi * (c*cos(phi) - r_p*sin(phi))

At closure (phi ~ 0) these reduce to the working formulas:

    dz_tip = s * tan(theta_w) * (r_p / d_w)        per step  (approach)
    dx_tip = s * tan(theta_w) * (c   / d_w)        per step  (Abbe walk)

Because the lip contact is OUTBOARD of the piezo (r_p < d_w) the lever
is a genuine second reduction on top of the wedge.

Geometry constants below were measured live from the Fusion model
(WedgeDesign v37, 2026-07-07, session 8): hinge pin axis at
(x, y) = (35.0, 85.7) mm ON the parting plane (swaged hinge); piezo disc
axis as seated at x = -41.26 mm -> lever r_p = 76.26 mm; lid lip contact
arm 120.15 mm; wedge rise 3.5 mm over its 27.5 mm run (crest 89.20 at
x = -85.15, thin edge flush 85.7 at x = -57.65) -> tan(theta_w) exactly
3.5/27.5.  The drive is the session-8 `Pinion_v3`: a TRUE involute,
module 1, z = 10, alpha = 20 deg (the printed rack's flank angle
atan(0.82/2.25) = 20.0 deg and pitch = pi mm identify it as a standard
module-1 rack) -> 10*pi = 31.4159 mm of stick travel per pinion rev.

All lengths mm, angles degrees at the boundary; nm for per-step outputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --- AS-BUILT geometry (Fusion WedgeDesign v37, session 8, mm) ---------------
PIVOT_XY_MM = (35.0, 85.7)     # hinge pin axis, ON the parting plane
ASBUILT_LEVER_MM = 76.26       # r_p: pin -> piezo disc axis (x = -41.26, seated)
LIP_ARM_MM = 120.15            # d_w: pin -> lid lip contact (117.5 lid + lip)
COLLET_STANDOFF_MM = 8.0       # collet + tip, perpendicular below piezo center

# Wedge, as modeled (M12 beveled washer in the 2.5 mm inset channel):
WEDGE_RISE_MM = 3.5            # crest 89.20 - flush 85.70
WEDGE_RUN_ASBUILT_MM = 27.5    # crest x -85.15 -> thin edge x -57.65
WEDGE_TAN = WEDGE_RISE_MM / WEDGE_RUN_ASBUILT_MM          # exactly 0.1272727..
WEDGE_ANGLE_ASBUILT_DEG = math.degrees(math.atan(WEDGE_TAN))   # 7.2527 deg
CONTACT_INCLUDED_DEG = 1.669   # lid angle at full wedge insertion (crest contact)

# --- AS-BUILT drive: 28BYJ-48 + printed rack-pinion --------------------------
# Session 8 (`Pinion_v3`): true involute, module m = 1 mm, z = 10, alpha = 20
# deg.  Pitch-line advance = z * pi * m per pinion revolution.  (The earlier
# 3.00 mm/tooth figure came from STL vertex clustering; in-model measurement
# and the involute identification fix the pitch at exactly pi.)
PINION_MODULE_MM = 1.0
PINION_TEETH = 10
MM_PER_REV = PINION_TEETH * math.pi * PINION_MODULE_MM     # 31.41593 mm/rev
RACK_PITCH_MM = math.pi * PINION_MODULE_MM                 # pi mm/tooth

MOTOR_HALF_STEPS_PER_REV_NOMINAL = 4096      # nominal "64:1" gearbox
MOTOR_GEARBOX_TRUE = 63.68395                # true ratio -> 4075.77 half-steps/rev
MOTOR_HALF_STEPS_PER_REV_TRUE = 64 * MOTOR_GEARBOX_TRUE


def rack_travel_per_step_nm(teeth: int = PINION_TEETH,
                            pitch_mm: float = RACK_PITCH_MM,
                            steps_per_rev: float = MOTOR_HALF_STEPS_PER_REV_NOMINAL) -> float:
    """Stick travel per motor half-step for the printed rack-pinion drive.

    One output rev advances the rack by (teeth x pitch); the motor needs
    ``steps_per_rev`` half-steps per output rev.
    """
    return teeth * pitch_mm * 1e6 / steps_per_rev


# --- alternative drive: M3 leadscrew (meeting note 23, round-2 option) -------
BASELINE_TRAVEL_PER_STEP_NM = 0.5e6 / 4096.0   # 0.5 mm/rev / 4096 steps = 122.07

# --- legacy layout rules (kept for the design-space scenario sweeps) ---------
PIVOT_X_MM = 35.0
REAR_EDGE_OFFSET_MM = 2.65   # plate rear edge sits this far in front of the pin
BORE_SETBACK_MM = 16.0       # bore keeps this setback to the plate front edge
PLATE_LENGTH_NOW_MM = 90.0   # current plate length (the lid adds a 27.5 mm lip)
LID_LENGTH_NOW_MM = 117.5

# --- Glarks beveled-washer kit (off-the-shelf-wedge-washers.md) --------------
WEDGE_ANGLES_DEG = {
    "M8": 7.70, "M10": 9.06, "M12": 7.26, "M16": 8.68, "M18": 9.39, "M20": 9.65,
}
WEDGE_RUN_MM = {
    "M8": 17.0, "M10": 21.3, "M12": 27.5, "M16": 33.4, "M18": 39.3, "M20": 40.0,
}

# --- context scales -----------------------------------------------------------
TUNNELING_WINDOW_NM = 1.0
PIEZO_REACH_UM = (15.0, 50.0)
BEST_LONGBOARD_NM_PER_STEP = 26.63


def lever_from_plate_length(plate_length_mm: float) -> float:
    """Scenario rule: piezo lever r_p for a plate of the given length.

    (Rear edge stays REAR_EDGE_OFFSET_MM in front of the pin; bore keeps
    BORE_SETBACK_MM to the front edge.)  Used only by the design-space
    sweeps; the as-built lever is the measured ASBUILT_LEVER_MM.
    """
    return plate_length_mm + REAR_EDGE_OFFSET_MM - BORE_SETBACK_MM


def wedge_arm_from_plate_length(plate_length_mm: float) -> float:
    """Scenario rule: wedge contact d_w assumed at the plate front edge."""
    return plate_length_mm + REAR_EDGE_OFFSET_MM


@dataclass(frozen=True)
class StepGearing:
    """Per-step motion of the clamshell tip for one geometry + drive."""

    plate_length_mm: float
    lever_mm: float           # r_p
    wedge_arm_mm: float       # d_w
    wedge_angle_deg: float
    travel_per_step_nm: float # horizontal stick/wedge travel per motor step (s)
    collet_mm: float
    opening_deg: float

    dz_wedge_nm: float        # lift at the lip contact per step
    dphi_rad: float           # lid rotation per step
    dz_tip_nm: float          # vertical tip motion per step (approach)
    dx_tip_nm: float          # lateral tip motion per step (collet Abbe)

    @property
    def lever_ratio(self) -> float:
        return self.lever_mm / self.wedge_arm_mm

    @property
    def steps_per_window(self) -> float:
        """Motor steps to cross the ~1 nm tunneling window (fractional)."""
        return TUNNELING_WINDOW_NM / self.dz_tip_nm

    def steps_across_reach_um(self, reach_um: float) -> float:
        """Motor steps to traverse a piezo Z reach given in micrometres."""
        return reach_um * 1e3 / self.dz_tip_nm


def step_gearing(plate_length_mm: float,
                 wedge_angle_deg: float = WEDGE_ANGLES_DEG["M12"],
                 travel_per_step_nm: float = BASELINE_TRAVEL_PER_STEP_NM,
                 gear_ratio: float = 1.0,
                 collet_mm: float = COLLET_STANDOFF_MM,
                 opening_deg: float = 0.0,
                 wedge_arm_mm: float | None = None,
                 lever_mm: float | None = None) -> StepGearing:
    """Exact per-step tip motion for one geometry, wedge and drive.

    ``gear_ratio`` divides the horizontal travel per step (an extra
    reduction between motor and slide).  ``wedge_arm_mm`` / ``lever_mm``
    override the scenario layout rules with measured values.
    """
    r_p = lever_mm if lever_mm is not None else lever_from_plate_length(plate_length_mm)
    d_w = wedge_arm_mm if wedge_arm_mm is not None else wedge_arm_from_plate_length(plate_length_mm)
    s = travel_per_step_nm / gear_ratio
    phi = math.radians(opening_deg)
    theta = math.radians(wedge_angle_deg)

    dz_wedge = s * math.tan(theta)
    dphi = dz_wedge / (d_w * 1e6)          # nm / nm -> rad
    dz_tip = dphi * (r_p * math.cos(phi) + collet_mm * math.sin(phi)) * 1e6
    dx_tip = dphi * (collet_mm * math.cos(phi) - r_p * math.sin(phi)) * 1e6
    return StepGearing(
        plate_length_mm=plate_length_mm,
        lever_mm=r_p,
        wedge_arm_mm=d_w,
        wedge_angle_deg=wedge_angle_deg,
        travel_per_step_nm=s,
        collet_mm=collet_mm,
        opening_deg=opening_deg,
        dz_wedge_nm=dz_wedge,
        dphi_rad=dphi,
        dz_tip_nm=dz_tip,
        dx_tip_nm=dx_tip,
    )


def as_built_gearing(steps_per_rev: float = MOTOR_HALF_STEPS_PER_REV_NOMINAL,
                     **kw) -> StepGearing:
    """THE as-built chain (WedgeDesign v37 + session-8 Pinion_v3 drive).

    28BYJ-48 half-stepping -> module-1 z=10 involute pinion (31.4159
    mm/rev) -> push stick glued to the M12 wedge -> lid lip contact at
    120.15 mm -> piezo lever 76.26 mm.  Every default is the measured
    model value.
    """
    kw.setdefault("wedge_angle_deg", WEDGE_ANGLE_ASBUILT_DEG)
    kw.setdefault("wedge_arm_mm", LIP_ARM_MM)
    kw.setdefault("lever_mm", ASBUILT_LEVER_MM)
    kw.setdefault("travel_per_step_nm",
                  rack_travel_per_step_nm(steps_per_rev=steps_per_rev))
    return step_gearing(PLATE_LENGTH_NOW_MM, **kw)


def leadscrew_gearing(**kw) -> StepGearing:
    """Round-2 alternative: same geometry, M3 leadscrew drive (0.5 mm/rev)."""
    kw.setdefault("travel_per_step_nm", BASELINE_TRAVEL_PER_STEP_NM)
    return as_built_gearing(**kw)


# Back-compat alias: the "simulated system" IS the as-built system now.
def simulated_system_gearing(teeth: int = PINION_TEETH,
                             steps_per_rev: float = MOTOR_HALF_STEPS_PER_REV_NOMINAL,
                             **kw) -> StepGearing:
    kw.setdefault("travel_per_step_nm",
                  rack_travel_per_step_nm(teeth, steps_per_rev=steps_per_rev))
    return as_built_gearing(steps_per_rev=steps_per_rev, **kw)


def full_slide_range_mm(plate_length_mm: float,
                        wedge_size: str = "M12",
                        wedge_arm_mm: float | None = None,
                        lever_mm: float | None = None) -> float:
    """Total tip Z change over the wedge's full run (its square width)."""
    r_p = lever_mm if lever_mm is not None else lever_from_plate_length(plate_length_mm)
    d_w = wedge_arm_mm if wedge_arm_mm is not None else wedge_arm_from_plate_length(plate_length_mm)
    theta = math.radians(WEDGE_ANGLES_DEG[wedge_size])
    return WEDGE_RUN_MM[wedge_size] * math.tan(theta) * (r_p / d_w)


def asbuilt_full_range_mm() -> float:
    """As-built total tip Z over the full 27.5 mm wedge run."""
    return WEDGE_RISE_MM * (ASBUILT_LEVER_MM / LIP_ARM_MM)


def asbuilt_full_stroke_steps(steps_per_rev: float = MOTOR_HALF_STEPS_PER_REV_NOMINAL) -> float:
    """Motor half-steps to run the wedge end to end (27.5 mm of stick)."""
    return WEDGE_RUN_ASBUILT_MM * 1e6 / rack_travel_per_step_nm(steps_per_rev=steps_per_rev)
