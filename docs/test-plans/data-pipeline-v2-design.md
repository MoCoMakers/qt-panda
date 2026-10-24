# Data pipeline v2: frame format, shared reconstruction, live view and replay (design, living)

**Status:** design, 2026-10-23.
- **Approved by the operator:**
  - live view and replay share one "Run" pipeline (D31);
  - a mode-first settings panel (D32).
- **Proposed:** frame format v2 (D33).
- **Requested:** a GUI mockup.

Decisions and assumptions: [`../DECISIONS.md`](../DECISIONS.md). Why this is needed: [`../SIMULATION.md`](../SIMULATION.md). Rebuilding height from Z *plus the current* recreates a known truth at ≥ 99% in simulation, against 0.78 from Z alone.

---

## 1 · Frame format v2

**v1 today** (`frame_logger.py`):
- Per line: PC receive time, the stamped line number, and per pixel the mean Z and mean error, where error = log(setpoint) − log\|ADC\|.
- Sidecar: settings snapshot.

**What v1 cannot support:**
- **abs() merges no-current and real current.** The −55 phantom offset reads as +55 counts, so no-current ticks pollute the pixel mean.
- **No clip or loss counts:** a pixel can't say how many of its ticks carried height information.
- **No exact time:** PC times are batched, so there is no time base for drift registration or preamp inversion.
- **Wrong or missing settings:** samples per pixel recorded 4× low, the realised line rate absent, no scan path.

**v2 (proposed; readers accept v1 and v2, versioned):**

| Where | Field | Why |
|---|---|---|
| line header | 32-bit tick at the first bin; boot ID; segment or line index; sequence flags (e.g. cross-hatch swap) | exact time and epoch (D16, D17); segment = line for any path (scan-path-design §3) |
| per bin | mean Z (as now) | |
| per bin | mean error (as now) | backward compatible |
| per bin | count of valid, clipped and lost ticks | the reconstruction drops what carries no information (roadmap F5) |
| per bin | mean log-current over valid ticks, from the **signed** ADC with the offset removed | the combined height without abs() contamination |
| per frame | a few position checkpoints (tick, commanded x, y) | proves the reconstruction map (scan-path-design §5) |
| sidecar | `scan_path` block; real settings echoed by the firmware; calibration snapshot; reconstruction algorithm version | no orphan frames (D22); CR7 |

- **Size:** about +8 bytes per bin, roughly 40–80 kB/s at 10 Hz, 512 bins, which is trivial for USB.
- **Needs firmware:** this goes in the one-flash milestone with F2, F8 and F9.
- **The lossless route:** the 100 kHz raw tap (every tick's ADC, Z, error) allows the exact per-tick rebuild. Today it only records while halted (I-9). Fixing I-9 gives a gold-standard check of what the frames compress.

## 2 · One reconstruction module, used everywhere (D31)

Today the live raster, replay and analysis scripts each turn frames into images their own way. Proposed: `reconstruct.py` (PC), versioned like the scan paths, used by all three.

```
frames + sidecar
  -> position map           scan_paths.reconstruct: raster or any path, bit-exact
  -> combined height/bin    tip height - gap(current); offset removed; preamp undone along the
                            time order; clipped/lost bins masked
  -> drift registration     each line by its own tick time; Z-drift ramp removed
  -> gridding (hybrid)      -> height image + coverage map + validity map
```

- **Calibration inputs**, each a parameter with a status in `PHYSICS_MODELS.md`:
  - preamp f3dB (CN5);
  - phantom offset (measured live: the no-current level while scanning);
  - κ (I(z));
  - Z scale (gold steps);
  - lateral hysteresis (HY1–HY4);
  - drift (tracker or registration).

  Assumed values are used until measured, and the output records which values were assumed.
- **Legacy v1:** an *approximate* combined height (mean error ≈ mean log-current, assumption A5), clearly labelled; optional line-number-slip correction (D34 pending).
- **Every image carries its provenance:** the algorithm version and calibration values are stored with exports and shown in the viewer.

## 3 · Standardised "Run" mode for live view and replay (D31)

- **Same pipeline, two sources.**
  - Live: the scan reader feeds line frames into the reconstruction module as they arrive.
  - Replay: the recorded `.frames` are played through the **same** module at any speed.

  A replayed run shows exactly what the live view showed (or would show with newer calibrations), and differences between them can only come from the inputs.
- **Same channels in both:** Z, Err, **Height (Z + current)**, coverage and validity; peaks bright (D8).
- **Same overlays:** validity colours (clipped / no current), drift-registered view (I-11), acceptance checks (fold, repeat, both Y halves, scales with zoom; R15/CN2).
- **Same settings model** (section 4). Replay reads it from the sidecar, live from the panel.
- **The emulator** can feed simulated streams into the same path (scan-path-design §9 step 5), so the pipeline is tested end to end without hardware.

## 4 · Settings panel: scan mode first, settings below by mode (D32)

**Layout (Continuous Scan tab).**
1. **Scan path** dropdown, first: Raster (default) · Raster, rotated · Cross-hatch pair · Spiral · Centre-return loops · Spokes · Rose · Custom file. Non-raster entries are marked *experimental*. Modes whose firmware isn't flashed are greyed out, with the reason.
2. **Common settings** (shown for every mode, as today): scan size, offsets X/Y, bins per segment (pixels per line), line rate or tip speed, setpoint, KIGA, line repeat.
3. **Mode settings** (populated from the selection):

| Mode | Extra settings |
|---|---|
| Raster | none (today's behaviour) |
| Raster, rotated | angle (15°, 45°, 90°, custom) |
| Cross-hatch pair | swap or rotate-90; frames per pair |
| Spiral | Archimedean / Fermat; turns or pitch (nm); out / in / out-in; constant angular or constant tip speed; CW/CCW |
| Centre-return loops | loops; rotation per loop |
| Spokes | spokes per frame; stride |
| Rose | loops; precession |
| Custom file | file picker; validation result (format, hash, bit-exact check against its source if any) |

4. **Derived, read-only** (updates as settings change): realised line rate (not the requested one, CR8); tip speed; frame time; **px per atom across and along the path** (5–6 rule, Oct 15); atoms per second; expected coverage and largest hole; drive energy near 158.7 Hz. These are the scorecard numbers, shown *before* scanning.

**Recording:** the panel's state becomes the sidecar's `scan_path` block plus the real settings echoed by the firmware. The replay panel shows the same layout read-only.

**Mockup:** requested for later (roadmap UI1). Base it on the live raster tab and the compact stage-tracking panel (`docs/mockup-stage-tracking-compact-v2.png`).

## 5 · Order of work

1. RC1 offline: approximate combined height on v1 frames (Sep 24, Oct 22); test whether it repeats better between sweeps than Z or error. Real data has no truth, so repeatability is the measure.
2. HY1 and CN5 measurements.
3. Firmware milestone (one flash): F8 tick and boot ID, frame v2 fields, F9, F2, CR fixes.
4. `reconstruct.py` shared module; replay height channel; live height channel; validity colours.
5. Settings panel (mode first); GUI mockup (UI1) before building it.
6. Scan-path modes in firmware (if chosen, D29) and emulator playback.
