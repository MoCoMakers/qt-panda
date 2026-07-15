"""Query: Brownian / thermal displacement of a gold atom at room temperature.

Reference question (from the user):

  "Describe the expected Brownian-motion displacement from center for an atom
   of gold at room temperature -- what displacement might be average?"
   (+ "leverage the density of gold and factor that in")
"""

from __future__ import annotations

from pathlib import Path

from models import Investigation
import physics.thermal_vibration as tv
from rendering import figures_thermal
from rendering.ascii_art import thermal_schematic, thermal_table

SLUG = "thermal-displacement-gold"

DEFAULT_T = 293.15  # room temperature, K (20 C)


def run(out_dir: Path, temperature_K: float = DEFAULT_T) -> Investigation:
    T = float(temperature_K)
    d = tv.gold_at(T)                     # full Debye
    c = tv.gold_at(T, model="classical")  # classical cross-check
    n = tv.number_density()
    a_nn_pm = tv.A_NN_AU * 1e12

    fig_dir = Path(out_dir) / "figures"
    manifest = figures_thermal.generate_all(fig_dir, T)

    summary = (
        f"A gold atom is not free &mdash; it is held at its lattice site by its bonds, "
        f"so its thermal (&ldquo;Brownian&rdquo;) motion is a bounded jitter about that site, "
        f"not unbounded diffusion. At <b>{T:.0f}&nbsp;K</b> the <b>average</b> distance from "
        f"the site is <b>&#10216;|u|&#10217; &asymp; {d.mean_mag_pm:.1f}&nbsp;pm</b> "
        f"(&asymp; {d.mean_mag_pm/100:.3f}&nbsp;&Aring;), with a 3-D RMS of "
        f"<b>{d.rms_pm:.1f}&nbsp;pm</b> and a per-axis spread of "
        f"&sigma; = {d.sigma_pm:.1f}&nbsp;pm. Gold&rsquo;s <b>density (19.30&nbsp;g/cm&sup3;)</b> "
        f"fixes the packing: n = {n*1e-27:.1f} atoms/nm&sup3;, giving a nearest-neighbour "
        f"spacing of {a_nn_pm:.0f}&nbsp;pm &mdash; so the jitter is only "
        f"<b>{d.lindemann_ratio*100:.1f}%</b> of the interatomic distance at room temperature."
    )

    findings = [
        f"<b>Average displacement &asymp; {d.mean_mag_pm:.0f} pm</b> "
        f"(mean magnitude &#10216;|u|&#10217;); 3-D RMS = {d.rms_pm:.1f} pm; "
        f"most-probable = {d.most_probable_pm:.1f} pm. All are a few tens of picometres "
        f"&mdash; a fraction of an &aring;ngstr&ouml;m.",
        f"<b>Density does the work</b> of setting the lattice scale: "
        f"n = &rho;N<sub>A</sub>/M = {n:.2e}&nbsp;m<sup>&minus;3</sup> &rarr; FCC spacing "
        f"{a_nn_pm:.0f}&nbsp;pm, which is the yardstick the jitter is measured against.",
        f"At room temperature the <b>classical</b> estimate ({c.rms_pm:.1f}&nbsp;pm) and the "
        f"full <b>quantum Debye</b> result ({d.rms_pm:.1f}&nbsp;pm) agree to &lt;1%, because "
        f"293&nbsp;K is well above gold&rsquo;s Debye temperature (&Theta;<sub>D</sub> &asymp; 165&nbsp;K). "
        f"A quantum <b>zero-point</b> floor of {tv.gold_at(0).rms_pm:.1f}&nbsp;pm remains even at 0&nbsp;K.",
        f"Sanity check &mdash; the <b>Lindemann criterion</b>: amplitude reaches "
        f"{tv.gold_at(tv.T_MELT_AU).lindemann_ratio*100:.0f}% of the spacing exactly at gold&rsquo;s "
        f"melting point ({tv.T_MELT_AU:.0f}&nbsp;K), matching the empirical ~10&ndash;15% melt rule.",
    ]

    equations = [
        ("n = &rho;&middot;N<sub>A</sub> / M &nbsp;&rarr;&nbsp; a = (4/n)<sup>1/3</sup>, &nbsp; d<sub>nn</sub> = a/&radic;2",
         "Density &rarr; number density &rarr; FCC lattice spacing (the Lindemann yardstick)."),
        ("&#10216;u&sup2;&#10217; = 9&#295;&sup2;T / (m k<sub>B</sub> &Theta;<sub>D</sub>&sup2;)",
         "Classical / high-T (T &gt; &Theta;<sub>D</sub>) 3-D mean-square displacement."),
        ("&#10216;u&sup2;&#10217; = (9&#295;&sup2;T / m k<sub>B</sub> &Theta;<sub>D</sub>&sup2;) [ &Phi;(&Theta;<sub>D</sub>/T) + &Theta;<sub>D</sub>/4T ]",
         "Full Debye result; the &Theta;<sub>D</sub>/4T term is quantum zero-point motion."),
        ("&sigma; = &radic;(&#10216;u&sup2;&#10217;/3),&nbsp; &#10216;|u|&#10217; = &radic;(8/&pi;)&middot;&sigma;,&nbsp; rms = &radic;3&middot;&sigma;",
         "Per-axis Gaussian &rarr; 3-D Maxwell magnitude: most-probable &radic;2&sigma;, mean &radic;(8/&pi;)&sigma;, rms &radic;3&sigma;."),
    ]

    assumptions = [
        "The atom is bound at a lattice site (harmonic/Debye solid), not a free gas "
        "atom. A genuinely free atom diffuses without bound (<r^2> = 6Dt) and has no "
        "finite 'average displacement from center' -- so that is the ill-posed case.",
        "Isotropic 3-D harmonic motion; surface/edge atoms (relevant to STM) actually "
        "vibrate ~1.5-2x more than bulk atoms -- treat these as bulk lower bounds.",
        f"Gold parameters: M = 196.97 g/mol, rho = 19.30 g/cm^3, Theta_D = "
        f"{tv.THETA_D_AU:.0f} K, FCC structure, melting point {tv.T_MELT_AU:.0f} K.",
        "Debye model with a single Theta_D; real phonon spectra differ in detail but "
        "the room-temperature amplitude is robust to ~10%.",
        "Quasi-harmonic: thermal expansion and anharmonicity (which soften Theta_D as T "
        "rises) are neglected, so the high-T amplitude is a slight under-estimate.",
    ]

    return Investigation(
        slug=SLUG,
        title="Thermal (Brownian) Displacement of a Gold Atom at Room Temperature",
        question=("What is the expected Brownian-motion displacement from center for an "
                  "atom of gold at room temperature, and what displacement is average? "
                  "(grounded in gold's density)"),
        params={
            "temperature T": f"{T:.2f} K ({T-273.15:.1f} C)",
            "density rho": "19.30 g/cm^3  ->  n = %.3e /m^3" % n,
            "nn spacing (from rho)": f"{a_nn_pm:.0f} pm (FCC)",
            "Debye temperature": f"{tv.THETA_D_AU:.0f} K",
            "model": "Debye mean-square displacement (quantum) + classical cross-check",
            "engine": "NumPy (closed form + numeric Debye integral) + Matplotlib",
        },
        summary=summary,
        findings=findings,
        equations=equations,
        assumptions=assumptions,
        table_text=thermal_table(T),
        ascii_blocks=[
            ("Atom in its potential well (schematic)", thermal_schematic(T)),
            ("Computed displacement statistics", thermal_table(T)),
        ],
        figures=manifest,
        references=[
            "Debye-Waller factor / mean-square displacement: <u^2> = "
            "(9 hbar^2 T)/(m kB ThetaD^2)[Phi(ThetaD/T) + ThetaD/4T] "
            "(Ashcroft & Mermin, Solid State Physics, ch. 23-24).",
            "Lindemann melting criterion: a solid melts when RMS vibration reaches "
            "~10-15% of the nearest-neighbour spacing (F. Lindemann, 1910).",
            "Gold properties: rho = 19.30 g/cm^3, M = 196.97 g/mol, FCC a = 407.8 pm, "
            "Theta_D ~= 165 K, Tm = 1337 K; nn spacing here is derived from rho.",
            "Maxwell distribution of displacement magnitude for an isotropic 3-D "
            "Gaussian (chi distribution, 3 dof): mean = sqrt(8/pi) sigma.",
            "Context: qt-panda STM images gold surface atoms -- this ~15 pm thermal "
            "blur is the intrinsic limit thermal motion places on apparent atom position.",
        ],
    )
