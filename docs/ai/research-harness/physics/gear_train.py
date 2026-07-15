"""Two-stage spur reduction + rolling-element bearing sizing (closed form).

The QTPanda approach-stage precision upgrade inserts a COMPOUND spur
reduction between the 28BYJ-48 and the existing rack pinion (`Pinion_v3`):

    motor 20T -> 107T  (stage 1)        [compound idler shaft]
          20T -> 107T  (stage 2)        [output shaft = Pinion_v3]
                       -> 12 mm rack pinion -> rack

Both new shafts (the compound idler and the output) ride 625ZZ deep-groove
ball bearings (5 mm bore x 16 mm OD x 5 mm wide), two per shaft.  The motor
keeps its own bearings.  Keeping teeth (20:107, module 1) fixes the ratio at
(107/20)^2 = 28.62:1 and the sizes at 22 mm / 109 mm OD.

Everything here is closed-form statics: torque and tangential force
propagate mesh by mesh, giving the bearing radial loads and the (printed)
tooth bending stress.  Angles deg at the boundary, SI (N, m, Pa) inside,
reported in friendly units by the query.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# --- 28BYJ-48 stepper, at the OUTPUT of its own ~63.68:1 internal gearbox ---
MOTOR_RATED_TORQUE_NM = 0.034     # ~34 mN.m rated / pull-out torque
MOTOR_SHAFT_DIA_MM = 5.0          # 5 mm D-shaft -> 20T pinion bore

# --- reduction stage design (per stage), module 1 ---------------------------
MODULE_MM = 1.0
PINION_TEETH = 20
GEAR_TEETH = 107
N_STAGES = 2
FACE_WIDTH_MM = 5.0               # gear face width (also the 625ZZ width)

# --- existing output rack pinion (session-8 Pinion_v3, m1 z10) --------------
RACK_PINION_TEETH = 10

# --- 625ZZ deep-groove ball bearing (5 x 16 x 5), typical catalogue ratings -
BEARING = "625ZZ"
BEARING_BORE_MM = 5.0
BEARING_OD_MM = 16.0
BEARING_WIDTH_MM = 5.0
BEARING_C_DYN_N = 340.0           # dynamic load rating C  (~0.34 kN)
BEARING_C0_STAT_N = 160.0         # static load rating  C0 (~0.16 kN)
BEARINGS_PER_SHAFT = 2

# --- printed gear material (PLA first draft) --------------------------------
PLA_YIELD_MPA = 55.0
LEWIS_Y_20T = 0.32                # Lewis form factor, 20T, 20 deg full-depth
LEWIS_Y_10T = 0.24                # ~10-12T
# PCTG (final) for reference only
PCTG_YIELD_MPA = 45.0


def pitch_dia_mm(teeth: int, module: float = MODULE_MM) -> float:
    return teeth * module


def outside_dia_mm(teeth: int, module: float = MODULE_MM) -> float:
    return (teeth + 2) * module


def center_distance_mm(t1: int, t2: int, module: float = MODULE_MM) -> float:
    return module * (t1 + t2) / 2.0


def stage_ratio() -> float:
    return GEAR_TEETH / PINION_TEETH


def total_ratio(n_stages: int = N_STAGES) -> float:
    return stage_ratio() ** n_stages


def _lewis_stress_mpa(force_n: float, teeth_form_factor: float,
                      module_mm: float = MODULE_MM,
                      face_mm: float = FACE_WIDTH_MM) -> float:
    """Lewis tooth bending stress: sigma = F / (b * m * Y)  [Pa -> MPa]."""
    b = face_mm / 1e3
    m = module_mm / 1e3
    return force_n / (b * m * teeth_form_factor) / 1e6


def safe_tangential_force_n(yield_mpa: float, form_factor: float,
                            module_mm: float = MODULE_MM,
                            face_mm: float = FACE_WIDTH_MM) -> float:
    """Tangential force at which a printed tooth reaches yield (SF = 1)."""
    b = face_mm / 1e3
    m = module_mm / 1e3
    return yield_mpa * 1e6 * b * m * form_factor


@dataclass(frozen=True)
class GearTrainAnalysis:
    motor_torque_nm: float
    stage_ratio: float
    total_ratio: float
    # per-mesh tangential forces and shaft torques
    F_mesh1_n: float          # motor 20T -> idler 107T
    T_idler_nm: float
    F_mesh2_n: float          # idler 20T -> output 107T
    T_output_nm: float
    F_rack_n: float           # output 10T rack pinion -> rack (stall-max)
    # bearing radial loads (worst-case, per bearing with 2/shaft)
    idler_bearing_n: float
    output_bearing_n: float
    C0_stat_n: float
    idler_static_margin: float
    output_static_margin: float
    # printed-tooth bending (the torque limit)
    sigma_pinion2_mpa: float  # idler 20T tooth at mesh 2
    sigma_rack_mpa: float     # 10T rack pinion tooth at stall
    pla_yield_mpa: float
    rack_force_yield_n: float # rack force that yields the PLA rack tooth
    rack_force_margin: float  # yield / stall
    # geometry
    center_distance_mm: float
    pinion_od_mm: float
    gear_od_mm: float


def analyze(motor_torque_nm: float = MOTOR_RATED_TORQUE_NM,
            n_stages: int = N_STAGES) -> GearTrainAnalysis:
    """Statics of the compound train at the motor's rated (stall-ish) torque."""
    r_pinion = pitch_dia_mm(PINION_TEETH) / 2 / 1e3     # m
    r_rack = pitch_dia_mm(RACK_PINION_TEETH) / 2 / 1e3  # m
    sr = stage_ratio()

    # torque multiplies by the ratio each stage; tangential force = T / r_pinion
    F1 = motor_torque_nm / r_pinion
    T_idler = motor_torque_nm * sr
    F2 = T_idler / r_pinion
    T_output = T_idler * sr
    F_rack = T_output / r_rack

    # worst-case (aligned) radial load per shaft, split over 2 bearings
    idler_load = (F1 + F2) / BEARINGS_PER_SHAFT
    output_load = (F2 + F_rack) / BEARINGS_PER_SHAFT

    sigma_p2 = _lewis_stress_mpa(F2, LEWIS_Y_20T)
    sigma_rack = _lewis_stress_mpa(F_rack, LEWIS_Y_10T)
    rack_yield = safe_tangential_force_n(PLA_YIELD_MPA, LEWIS_Y_10T)

    return GearTrainAnalysis(
        motor_torque_nm=motor_torque_nm,
        stage_ratio=sr,
        total_ratio=sr ** n_stages,
        F_mesh1_n=F1,
        T_idler_nm=T_idler,
        F_mesh2_n=F2,
        T_output_nm=T_output,
        F_rack_n=F_rack,
        idler_bearing_n=idler_load,
        output_bearing_n=output_load,
        C0_stat_n=BEARING_C0_STAT_N,
        idler_static_margin=BEARING_C0_STAT_N / idler_load,
        output_static_margin=BEARING_C0_STAT_N / output_load,
        sigma_pinion2_mpa=sigma_p2,
        sigma_rack_mpa=sigma_rack,
        pla_yield_mpa=PLA_YIELD_MPA,
        rack_force_yield_n=rack_yield,
        rack_force_margin=rack_yield / F_rack,
        center_distance_mm=center_distance_mm(PINION_TEETH, GEAR_TEETH),
        pinion_od_mm=outside_dia_mm(PINION_TEETH),
        gear_od_mm=outside_dia_mm(GEAR_TEETH),
    )
