"""Geometry of tip displacement from an angular offset on a piezo scanner.

Physical picture
----------------
A scanning-probe tip is mounted on the end face of a piezo actuator
(tube or stack).  The tip sticks out by a length ``L`` from the mounting
face.  If the mounting face is tilted away from ideal by a small angular
offset ``theta`` (here 2 degrees), the *apex* of an otherwise rigid tip
is swept through an arc about the mounting point.

This is the classic **Abbe / cosine error**: an angular error is
amplified into a translational error in proportion to the standoff
length ``L`` between the point of rotation and the point of measurement
(the tip apex).

Decomposing the apex motion relative to its ideal (un-tilted) position:

    lateral displacement   dx = L * sin(theta)
    vertical foreshortening dz = L * (1 - cos(theta))
    total apex displacement dr = sqrt(dx**2 + dz**2) = 2 * L * sin(theta/2)

Small-angle behaviour (theta in radians):

    dx ~= L * theta            (linear in theta, linear in L)
    dz ~= L * theta**2 / 2     (quadratic in theta, linear in L)

So for a fixed offset angle the **lateral** error scales *linearly* with
tip length, while the **height** error scales linearly with length but is
~theta/2 smaller than the lateral term -- which is why long tips wreck
lateral registration far more than they hurt Z.

All lengths are SI (metres) internally; helpers accept/return convenient
units at the boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TipDisplacement:
    """Apex displacement of a rigid tip under an angular offset.

    Attributes are in metres / radians (SI).  Use the ``*_um`` and
    ``*_deg`` properties for human-friendly units.
    """

    length_m: float
    theta_rad: float
    lateral_m: float       # dx = L sin(theta)
    vertical_m: float      # dz = L (1 - cos theta)
    total_m: float         # dr = 2 L sin(theta/2)

    # --- convenience views -------------------------------------------------
    @property
    def length_mm(self) -> float:
        return self.length_m * 1e3

    @property
    def theta_deg(self) -> float:
        return math.degrees(self.theta_rad)

    @property
    def lateral_um(self) -> float:
        return self.lateral_m * 1e6

    @property
    def vertical_um(self) -> float:
        return self.vertical_m * 1e6

    @property
    def total_um(self) -> float:
        return self.total_m * 1e6


def tip_displacement(length_m: float, theta_rad: float) -> TipDisplacement:
    """Exact apex displacement for tip length ``L`` and offset ``theta``.

    Parameters
    ----------
    length_m : float
        Tip standoff length L from the pivot/mount face, in metres.
    theta_rad : float
        Angular offset of the mounting face, in radians.
    """
    dx = length_m * math.sin(theta_rad)
    dz = length_m * (1.0 - math.cos(theta_rad))
    dr = 2.0 * length_m * math.sin(theta_rad / 2.0)
    return TipDisplacement(
        length_m=length_m,
        theta_rad=theta_rad,
        lateral_m=dx,
        vertical_m=dz,
        total_m=dr,
    )


def tip_displacement_mm_deg(length_mm: float, theta_deg: float) -> TipDisplacement:
    """Same as :func:`tip_displacement` but takes mm and degrees."""
    return tip_displacement(length_mm * 1e-3, math.radians(theta_deg))


def small_angle_lateral_m(length_m: float, theta_rad: float) -> float:
    """Small-angle lateral estimate dx ~= L * theta (for error bounding)."""
    return length_m * theta_rad


def small_angle_vertical_m(length_m: float, theta_rad: float) -> float:
    """Small-angle vertical estimate dz ~= L * theta**2 / 2."""
    return length_m * theta_rad * theta_rad / 2.0
