# Common STM techniques: awareness backlog

**Why this exists:** on 2026-10-23 we worked out drift tracking by fiducials from our own data, then recognised it as an established STM technique. This list collects other standard techniques we should know about, so we can borrow instead of rediscover. It is a living backlog.

**Caveat:** written from general knowledge, not yet checked against primary sources. Investigation I-6 in `docs/test-plans/2026-10-23-open-issues-and-tests.md` is to verify each entry and add references. Names of specific products or papers are omitted until verified.

**Status here:** `have` (we do it), `partial`, `rediscovered` (we built it before knowing the name), `not yet`.

## Drift, creep and scanner nonlinearity

| Technique | What it is | Why it matters to us | Status |
|---|---|---|---|
| Drift measurement by image cross-correlation | Register consecutive images to measure lateral drift | Our D/F sections do exactly this | rediscovered |
| Atom / feature tracking | Lock the tip laterally onto a surface feature with a small modulation and a feedback loop, so drift is followed in real time | The real-time version of our "stage tracking" | not yet |
| Drift compensation (feed-forward) | Measure drift velocity, then apply a continuous X/Y (and Z) offset ramp | Our proposed tracker's correct mode | partial (designed) |
| Piezo creep compensation | Model the logarithmic creep after offset or size changes; settle or pre-compensate | Offset moves and scan restarts caused jumps on Oct 22 | not yet |
| Hysteresis / nonlinearity correction | Open-loop correction models, or closed-loop scanners with position sensors | Up/down-sweep offset (~1 nm) and trace/retrace mismatch | partial (measured, not corrected) |
| Settling time after approach / large moves | Wait for thermal and mechanical relaxation before imaging | The Oct 22 drift was 4 nm/min right after a crash and motor moves | partial (habit, not measured) |
| Orthogonal-scan drift correction | Scan the same area with the fast axis along X, then along Y; drift distorts the two differently and can be solved for (reported for STEM and scanning probe images, Ophus et al., Ultramicroscopy 2016, to verify) | Our cross-hatch sequence (OI-17) | partial (designed) |
| Lag / bandwidth deconvolution | Treat the fast-axis smear as a known convolution (loop lag, preamp RC) and invert it | `docs/ai/hypotheses/stretch-compensation.md`: a shift alone gave +0.006 end to end; deconvolution untested. The combined Z + current height estimate (scan simulator) removes loop lag without deconvolving | not yet |
| Line-by-line drift registration | Place each scan line by its own time instead of one shift per frame | Report v2: up ↔ down agreement 0.42 → 0.49 | rediscovered |
| Slope / tilt feed-forward | Pre-tilt the Z drive to match the sample plane so the loop only handles topography | Reduces the load on a slow loop and the lag tails | not yet |

## Feedback loop

| Technique | What it is | Why it matters | Status |
|---|---|---|---|
| Trace/retrace matching as the tuning criterion | Raise gain until forward and backward line profiles overlap, back off at ringing | Our direction-flip share is this measurement in number form | partial |
| PI tuning against mechanical resonance | Keep crossover well below the lowest Z-path resonance | KIGA 9 went unstable near 158.7 Hz | have (by ladder) |
| Notch filter in the Z loop | Suppress a known resonance so gain can go higher | 158.7 Hz resonance | not yet |
| Mechanical transfer function | Drive Z with a small sine sweep, read the response, map resonances | The planned Z sine-sweep test | not yet |
| Log-current feedback | Feed back on log(I) so the loop is linear in tip height | We do this | have |
| Preamp offset nulling | Measure and subtract the current amplifier's zero offset | Our idle offset (−15) and the scanning offset (−55) | not yet (OI-2, OI-3) |
| Capacitive crosstalk compensation | Subtract scan-drive pickup (C·dV/dt) from the current signal | Candidate cause of the scanning offset | not yet (T2) |

## Imaging and processing

| Technique | What it is | Why it matters | Status |
|---|---|---|---|
| Line flattening (offset, slope, median of differences) | Standard row alignment | Our row-levelling variants | have |
| Scar and streak removal | Detect and repair single-line glitches | Torn lines, dropped lines | not yet |
| Forward/backward averaging | Average trace and retrace after alignment | Our folded S; retrace alignment is manual (OI-7) | partial |
| Fixed colour scale vs auto-levels | Absolute colour mapping for comparable frames | Auto-levels change what "black" means per frame (OI-4) | partial |
| Standard analysis software and file formats | Established tools for SPM data (flattening, FFT, grain analysis) | Exporting our frames could save writing our own tools | partial (export exists in replay) |
| Double-tip and tip-change detection | Spot duplicated features and sudden contrast changes | Our autocorrelation and row-jump tests | rediscovered |
| Cross-hatch / rotated scans | Scan with the fast axis rotated and merge, to separate streaks from surface | Planned build | not yet |

## Spectroscopy and calibration

| Technique | What it is | Why it matters | Status |
|---|---|---|---|
| I(z) spectroscopy (apparent barrier height) | Measure current vs tip height at a point | Gives the real decay constant, turning setpoint steps and contours into nm (T5) | not yet |
| I(V) and dI/dV (lock-in) | Electronic structure at a point | Firmware has lock-in; worth a routine | partial |
| Lateral calibration on a known lattice | Graphite (0.246 nm) or Au(111) features | Our 5 nm/V is a placeholder (T8) | not yet |
| Z calibration on step heights | Monatomic steps (e.g. Au 0.235 nm) | Our 3 nm/V is a placeholder (T8) | not yet |
| Gap-resistance conventions | Choose bias and setpoint by R = V/I for imaging vs spectroscopy | T4 | not yet |

## Tip and mechanics

| Technique | What it is | Why it matters | Status |
|---|---|---|---|
| Tip conditioning by voltage pulses or field emission | Reshape or clean the apex in place | Recovering from crashes like Oct 22 | not yet |
| Controlled gentle indentation (on soft metals) | Reshape the tip by a small controlled contact | Alternative tip recovery | not yet |
| Vibration isolation and acoustic shielding | Springs, eddy-current damping, enclosure | Have a damped plate; 158.7 Hz mode to identify (T7) | partial |
| Safe auto-approach and retract | Step-and-check approach; retract that always moves away | RTRC moves toward the sample (safety item) | partial |

## Faster or smarter scanning

| Technique | What it is | Why it matters | Status |
|---|---|---|---|
| Adaptive line rate | Slow down where topography is steep | Lag-dominated images | not yet |
| Non-raster scans (spiral, Lissajous) | Smoother scanner motion, fewer turnarounds | Turnaround lag tails | not yet |
| Video-rate STM | Fast scanning with high-bandwidth mechanics | Context for what limits us | not yet |

## Scan paths

| Technique | What it is | Why it matters | Status |
|---|---|---|---|
| Rotated raster | Scan at an angle to the stage axes | Separates sample features from axis-bound artefacts; reveals X/Y calibration mismatch as shear | not yet (OI-17) |
| Spiral scanning | Archimedean or Fermat spirals driven by smooth sines, popular for fast scanning because there are no turnarounds | Smooth drive below the 158.7 Hz mode; loses trace/retrace lag cancellation unless run as out-in pairs | not yet (OI-17) |
| Lissajous / rose scanning | Each axis a pure sine; the pattern precesses to fill the area | Smoothest drive; uneven density; frequent centre crossings measure drift | not yet (OI-17) |
| Input shaping | Pre-filter the drive to cancel a known resonance | Lets rasters and returns run faster without ringing the 158.7 Hz mode | not yet |
| Piezo hysteresis models | Prandtl–Ishlinskii, Bouc–Wen: history-dependent commanded → actual position | Up/down offset and path-dependent distortion in the simulator | not yet |
