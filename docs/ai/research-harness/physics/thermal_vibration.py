"""Thermal (Brownian) displacement of an atom bound at a lattice site.

Framing
-------
A *free* atom has no well-defined "average displacement from center": its
Brownian/thermal wander is diffusive, mean-square displacement <r^2> = 6 D t
grows without bound. The well-posed question -- and the physically relevant
one for a scanning-probe target like a gold surface atom -- is the thermal
vibration of an atom held at its lattice site by the surrounding bonds. The
atom sits in an (approximately harmonic) potential well and jitters about the
site with a temperature-dependent amplitude. That amplitude is what STM/AFM
"sees" smeared out, and it is what sets the Debye-Waller factor.

Models (both grounded, cross-checked against each other)
--------------------------------------------------------
1. Classical equipartition / high-T Debye:
       <u^2> = 9 hbar^2 T / (m kB ThetaD^2)
   Valid when T >> ThetaD. For gold ThetaD ~= 165 K, so room temperature
   (293 K) is already in this regime.

2. Full Debye (adds quantum statistics + zero-point motion):
       <u^2> = (9 hbar^2 T)/(m kB ThetaD^2) * [ Phi(ThetaD/T) + ThetaD/(4T) ]
   with the Debye function  Phi(x) = (1/x) * integral_0^x  xi/(e^xi - 1) dxi.
   The ThetaD/(4T) term is the zero-point motion that survives at T -> 0.

<u^2> here is the full 3-D mean-square displacement. Per Cartesian axis the
variance is sigma^2 = <u^2>/3 (isotropic). The displacement *magnitude*
r = |u| then follows a Maxwell distribution (chi with 3 dof, scale sigma):

    most-probable |u| = sqrt(2) * sigma
    mean          |u| = sqrt(8/pi) * sigma   ~= 1.596 sigma
    rms           |u| = sqrt(3) * sigma

Lindemann melting criterion: a crystal melts when the rms displacement
reaches ~10-15% of the nearest-neighbour spacing -- a useful sanity anchor.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# --- physical constants (SI) ---------------------------------------------
KB = 1.380649e-23        # Boltzmann constant, J/K
HBAR = 1.054571817e-34   # reduced Planck constant, J*s
AMU = 1.66053907e-27     # atomic mass unit, kg
N_A = 6.02214076e23      # Avogadro constant, 1/mol

# --- gold (Au) defaults ---------------------------------------------------
M_MOLAR_AU = 196.966570e-3   # molar mass of gold, kg/mol
M_AU = M_MOLAR_AU / N_A      # atomic mass of gold, kg (= 196.97 amu)
RHO_AU = 19300.0             # mass density of gold, kg/m^3 (19.30 g/cm^3)
THETA_D_AU = 165.0           # Debye temperature of gold, K (lit. ~165-170 K)
T_MELT_AU = 1337.33          # melting point of gold, K
R_ATOM_AU = 144.0e-12        # metallic radius of gold, m


def number_density(rho: float = RHO_AU, m_molar: float = M_MOLAR_AU) -> float:
    """Atoms per unit volume n = rho * N_A / M_molar  [1/m^3].

    This is where the bulk **density** enters: it fixes how tightly the
    atoms are packed, and hence the lattice spacing the thermal jitter is
    measured against (the Lindemann denominator).
    """
    return rho * N_A / m_molar


def fcc_lattice_constant(n: float = None) -> float:
    """FCC conventional cell edge a from number density (4 atoms/cell)."""
    if n is None:
        n = number_density()
    return (4.0 / n) ** (1.0 / 3.0)


def nn_distance_fcc(n: float = None) -> float:
    """FCC nearest-neighbour spacing = a / sqrt(2), derived from density."""
    return fcc_lattice_constant(n) / math.sqrt(2.0)


def wigner_seitz_radius(n: float = None) -> float:
    """Radius of the sphere whose volume is the per-atom volume 1/n."""
    if n is None:
        n = number_density()
    return (3.0 / (4.0 * math.pi * n)) ** (1.0 / 3.0)


# Nearest-neighbour spacing derived from gold's measured density (not hard-coded):
A_NN_AU = nn_distance_fcc()  # ~= 288 pm for FCC gold at 19.30 g/cm^3


def debye_function(x: float, n_pts: int = 2000) -> float:
    """Debye function Phi(x) = (1/x) * int_0^x xi/(e^xi-1) dxi.

    Phi(0) = 1; decreases monotonically for x > 0. Integrated numerically
    (trapezoid) so we carry no SciPy dependency.
    """
    if x <= 1e-9:
        return 1.0
    xi = np.linspace(0.0, x, n_pts)
    integrand = np.empty_like(xi)
    integrand[0] = 1.0  # limit of xi/(e^xi-1) as xi->0
    nz = xi[1:]
    integrand[1:] = nz / np.expm1(nz)
    return float(np.trapezoid(integrand, xi) / x)


def msd_classical(T: float, theta_D: float = THETA_D_AU, m: float = M_AU) -> float:
    """Classical / high-T 3-D mean-square displacement <u^2> [m^2]."""
    return 9.0 * HBAR**2 * T / (m * KB * theta_D**2)


def msd_debye(T: float, theta_D: float = THETA_D_AU, m: float = M_AU) -> float:
    """Full Debye 3-D mean-square displacement <u^2> [m^2] (with zero-point)."""
    if T <= 0:
        # pure zero-point limit
        return 9.0 * HBAR**2 / (4.0 * m * KB * theta_D)
    x = theta_D / T
    bracket = debye_function(x) + theta_D / (4.0 * T)
    return (9.0 * HBAR**2 * T) / (m * KB * theta_D**2) * bracket


@dataclass(frozen=True)
class ThermalDisplacement:
    """Thermal-vibration displacement statistics for one (T, material)."""

    T: float
    msd_m2: float            # full 3-D <u^2>, m^2
    a_nn_m: float = A_NN_AU  # nearest-neighbour spacing for Lindemann ratio

    @property
    def sigma_m(self) -> float:
        """Per-axis RMS (std-dev of one Cartesian component)."""
        return math.sqrt(self.msd_m2 / 3.0)

    @property
    def rms_m(self) -> float:
        """3-D RMS displacement = sqrt(<u^2>)."""
        return math.sqrt(self.msd_m2)

    @property
    def mean_mag_m(self) -> float:
        """Mean displacement magnitude <|u|> = sqrt(8/pi) * sigma."""
        return math.sqrt(8.0 / math.pi) * self.sigma_m

    @property
    def most_probable_m(self) -> float:
        """Most-probable magnitude = sqrt(2) * sigma."""
        return math.sqrt(2.0) * self.sigma_m

    @property
    def lindemann_ratio(self) -> float:
        """RMS displacement as a fraction of nearest-neighbour spacing."""
        return self.rms_m / self.a_nn_m

    # picometre views ------------------------------------------------------
    @property
    def sigma_pm(self) -> float:
        return self.sigma_m * 1e12

    @property
    def rms_pm(self) -> float:
        return self.rms_m * 1e12

    @property
    def mean_mag_pm(self) -> float:
        return self.mean_mag_m * 1e12

    @property
    def most_probable_pm(self) -> float:
        return self.most_probable_m * 1e12


def gold_at(T: float, theta_D: float = THETA_D_AU, m: float = M_AU,
            a_nn: float = A_NN_AU, model: str = "debye") -> ThermalDisplacement:
    """Convenience: thermal displacement of a gold atom at temperature ``T``."""
    msd = msd_debye(T, theta_D, m) if model == "debye" else msd_classical(T, theta_D, m)
    return ThermalDisplacement(T=T, msd_m2=msd, a_nn_m=a_nn)
