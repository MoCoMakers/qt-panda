# qt-panda STM — User Guide (Dan-style port)

This guide covers day-to-day operation of the PC control software in
`dans-software-port/pc/qtpanda/`. It is written for an operator running
the instrument, not for firmware developers. For the firmware build flow,
the serial protocol, and binary frame formats see
[`../README.md`](../README.md). For bench-validation status see
[`../SMOKE_TEST.md`](../SMOKE_TEST.md).

> **What this software is.** A Dan-Berard-style control front-end for the
> qt-panda STM (Teensy 4.1, 4× AD5761 DACs, LTC2326-16 ADC). It keeps every
> capability of the original qt-panda v1 software (motorised approach,
> IV/dIdV/dIdZ/grid spectroscopy, one-shot raster, noise scan) and adds a
> continuous bidirectional scan workflow with live trace/retrace imaging,
> physical-unit controls, and an in-app calibration editor.

---

## 1. Before you start

**Prerequisites**

- Python 3.11 (the environment v1 already uses).
- Dependencies: PySide6, pyqtgraph, pyserial, numpy, tifffile, gwyfile.
  These match v1 — see `qtpanda/` packaging files.
- Firmware from `dans-software-port/teensy/arduinosrc/main/` flashed to the
  Teensy 4.1 (see `../README.md` for the Arduino IDE flow).

**Launching**

```
cd dans-software-port/pc/qtpanda
python widget.py
```

`setup.py` is a packaging script, **not** the launcher. Always run
`widget.py`.

The window opens with no instrument connected. Nothing is sent to the
hardware until you open a serial port.

---

## 2. The interface at a glance

The window has two regions:

```
+-------------------------+--------------------------------------------------+
|  LEFT PANEL             |  RIGHT PANEL (tabbed)                            |
|  (tbLeft: 2 sub-tabs)   |  Main | dI/dV | dI/dZ | Grid | Noise |          |
|                         |  Continuous Scan | Calibration                   |
|  - Configuration        |                                                  |
|  - Scanning             |                                                  |
+-------------------------+--------------------------------------------------+
```

**Left panel — "Configuration" sub-tab**

| Control | Purpose |
|---|---|
| Port combo + **Refresh** | Pick the serial port (auto-enumerated) |
| **Open / Reset / Clear** | Connect; firmware `RSET`; clear history |
| DAC X / Y / Z spinboxes (+ V labels) + **Set DAC** | Manual scanner positioning |
| Bias spinbox (+ V label) + **Send Bias** | Sample bias (the single bias control — the Continuous Scan tab deliberately does not duplicate it) |
| **Approach / Stop**, Target DAC, Steps | Motorised coarse approach |
| Settle times (X/Y/Z/Bias µs) + **Settle** | Per-axis DAC settle delays |
| Motor direction, **Off / Down / Up**, step size | Stepper jog |
| Raw command box + **Send** | Send any 4-char firmware command directly |
| Log pane | Firmware responses / diagnostics |

**Left panel — "Scanning" sub-tab**

Draggable scan-box selector, X/Y start/end/resolution, PID gains
(`Kp/Ki/Kd` + Set PID), constant-current checkbox + target, one-shot
**Scan** / multi-scan, and the legacy save path. These drive the legacy
one-shot raster (firmware `SCST`) and are unchanged from v1.

**Right panel tabs**

1. **Main** — live current vs time, approach steps vs time, scan ADC/Z maps, colormap picker.
2. **dI/dV Curve** — IV + differential conductance spectroscopy.
3. **dI/dZ Curve** — current-distance spectroscopy.
4. **grid spectroscopy** — 3-D bias cube with a bias slider and click-to-extract spectrum.
5. **Noise Scan** — fixed-position noise map.
6. **Continuous Scan** — the Dan-style live scanning workflow (Section 5).
7. **Calibration** — hardware-constant editor (Section 7).

---

## 3. First-time setup: calibration

**Do this once per instrument, before trusting any physical-unit display.**

Open the **Calibration** tab. It lists ten hardware constants:

| Field | Meaning | Default basis |
|---|---|---|
| `dac_x/y/bias_v_per_lsb` | DAC volts per LSB | AD5761 ±5 V / 2¹⁶ |
| `dac_z_v_per_lsb` | Z DAC volts per LSB | AD5761 ±10 V / 2¹⁶ |
| `piezo_x/y/z_nm_per_v` | Piezo nm per volt | **Placeholder — calibrate per scanner/tip** |
| `adc_v_per_lsb` | ADC volts per LSB | LTC2326-16 ±10.24 V / 2¹⁶ |
| `preamp_a_per_v`, `preamp_v_per_a` | Trans-impedance | 100 MΩ feedback |

The **Examples (live)** box shows conversions as you edit, so you can
sanity-check (e.g. "Scan 30 nm → N LSB span", "Setpoint 1000 pA → N LSB").

Buttons:

- **Apply** — push edited values into the running session (every
  physical-unit control immediately uses them).
- **Save to JSON** — persist to `calibration.json` for next session.
- **Reset defaults** — restore datasheet defaults in memory (does not
  touch the JSON until you Save).

> The UI is the source of truth. `calibration.json` is only the
> save/reload backend — you never need to hand-edit it.

The piezo `nm_per_v` values are the ones you must determine for your
hardware (e.g. by imaging a known calibration grating, or from the
manufacturer's piezo coefficient). Until then, nm/pA readouts are
indicative, not absolute.

---

## 4. Connecting and positioning

1. **Plug in** the Teensy. In the Configuration sub-tab, click
   **Refresh**, select the port, click **Open**. The last-used port is
   remembered between sessions.
2. **Reset** (optional) sends firmware `RSET` for a clean state.
3. Use the **DAC X/Y/Z** spinboxes + **Set DAC** to centre the scanner,
   and **Send Bias** to set the sample bias. The V labels next to each
   show the converted voltage.
4. Set **Settle** times if your piezo needs longer to stabilise.

---

## 5. Continuous scanning (the Dan-style workflow)

This is the centrepiece. Open the **Continuous Scan** tab.

### 5.1 Layout

```
+----------------+--------------+----------+-----------------+
| Scan geometry  | Feedback     | Z-piezo  | Control         |
| Scan size (nm) | Setpoint(pA) | gauge    | Apply settings  |
| Pixels/line    | Kp           | Extended | Engage (ENGA)   |
| Line rate (Hz) | Ki           |  ▮▮▮     | Retract (RTRC)  |
| X offset (nm)  |              |  ▮▮      | ▶ RUN           |
| Y offset (nm)  |              | Retracted| ■ HALT          |
+----------------+--------------+----------+-----------------+
|  Z trace        |  Z retrace        |  [Z histogram]      |
|  err trace      |  err retrace      |  [err histogram]    |
|  Z-trace 1D plot of the most-recent line (x in nm)        |
+-----------------------------------------------------------+
```

All inputs are in **physical units** (nm, pA, Hz). Conversion to firmware
LSB uses the Calibration model.

### 5.2 Procedure

1. **Coarse approach first.** Use the Configuration sub-tab
   **Approach** (with a Target DAC) until the tip is within piezo range
   of the surface. The firmware prints `Approached!` in the log.
2. In the Continuous Scan tab set:
   - **Setpoint** — tunnel-current target (default 1000 pA ≈ 1 nA; a
     realistic STM value). *Sub-nA setpoints round to zero LSB and the
     firmware will refuse to engage — see Safety.*
   - **Scan size**, **Pixels/line**, **Line rate**, **offsets**.
   - **Kp / Ki** — feedback gains (defaults: Kp 0, Ki 4.5776, a pure-I
     loop matching Dan's reference).
3. Click **Apply settings**. This pushes everything to the firmware and
   sizes the image buffers.
4. Click **Engage (ENGA)**. The PI loop takes over Z with a bumpless
   transfer (no tip jump). Status shows "Engaged". *If you skipped the
   setpoint, the firmware refuses and the log shows
   `ENGA refused: no setpoint (use SETP first)`.*
5. Click **▶ RUN**. Lines stream live into the four images.
6. Click **■ HALT** to stop streaming (tip stays engaged at the last
   position). **Retract (RTRC)** disengages PI and parks Z at a safe
   retracted value.

### 5.3 Reading the live raster

- **Four images, always live:** Z trace / Z retrace (top), error trace /
  error retrace (bottom). A feature present in both trace *and* retrace
  is real; one that flips or only appears one way is drift/creep/an
  artifact.
- **Histograms:** drag the level region on the right of each row to clamp
  the colour range and bring out subtle features (auto-leveling washes
  them out). The retrace twin mirrors the trace's levels automatically.
- **Auto levels** button — 2–98 percentile stretch on both rows.
- **Z-trace 1D plot** — the most recent line's Z profile, x-axis in nm.
  This is your real-time view of surface topography.
- **Z-piezo gauge** — the vertical bar shows where Z sits in its range.
  Watch it: if it pins toward "Extended" or "Retracted" the loop is
  running out of travel (drift, wrong setpoint, or tip about to crash).

### 5.4 Right-click to recentre

Right-click anywhere in either Z image to move the scan centre there.
The X/Y offset fields update and the new offset is sent immediately.
This is the fastest way to navigate to a feature.

### 5.5 Saving frames

- **Change folder…** sets a persistent destination (remembered between
  sessions).
- **Save frame** writes four TIFFs (Z/err × trace/retrace) plus a raw
  `.bin` (per row: uint16 line + int32 Z[W] + int32 err[W], trace).
  After the first use it saves silently into the remembered folder with a
  timestamped name.

---

## 6. Spectroscopy and legacy scans

These tabs are unchanged from v1 and use the ASCII protocol.

- **dI/dV Curve** — set bias start/end/step, **Scan IV**. Plots IV and
  differential conductance. **Save IV** writes a Gwyddion ASCII curve.
- **dI/dZ Curve** — set Z start/end/step, **Scan dIdZ**.
- **grid spectroscopy** — define an X/Y region (Scanning sub-tab box) and
  bias range, choose dI/dV or dI/dZ, **Grid Spectro**. Use the bias
  slider to step through the cube; click a pixel to extract its spectrum
  on the chart below.
- **Noise Scan** — resolution + samples + delay, **Noise Scan**.
- **Legacy one-shot raster** — Scanning sub-tab: define the box, samples,
  optionally enable constant current, **Scan** (or multi-scan). Output
  appears on the Main tab maps and can be saved as TIFF/GSF/ASCII.

> **Do not run a legacy scan or spectroscopy while a continuous scan is
> RUNning.** Stop with **HALT** first. The two paths share the serial
> port; running both at once races for it. (The continuous-scan reader
> thread is stopped automatically on HALT.)

---

## 7. The Calibration tab in depth

See Section 3 for the field meanings. Operational notes:

- Editing a field and clicking **Apply** takes effect immediately for
  every physical-unit control (e.g. raising `piezo_z_nm_per_v` rescales
  the Z-trace plot and the nm meaning of scan size).
- Values span ~1e-4 to 1e8, so fields are free-text with scientific-
  notation validation rather than spin boxes.
- **Save to JSON** is the only action that writes `calibration.json`.
  Quitting without Save discards edits.

---

## 8. Safety and tip protection

STM tips are fragile and a crash is expensive. Build these into your
routine:

1. **Always coarse-approach before engaging.** Engaging far from the
   surface with an aggressive Ki drives the tip hard toward the sample.
2. **Set a real setpoint.** The firmware refuses `ENGA` when the
   setpoint is zero LSB (sub-nA at a 100 MΩ preamp). This is a safety
   feature, not a bug — give it a real value (≈ 1 nA default).
3. **Watch the Z-piezo gauge.** Pinning to a rail means the loop is out
   of travel. Halt/retract and investigate before it crashes.
4. **Retract before disconnecting.** Click **Retract**, then close the
   port. Pulling USB mid-scan is recovered gracefully by the software but
   leaves the tip wherever it was.
5. **Engage is bumpless** — it pre-loads Z from the current DAC code, so
   engaging after manual positioning will not jerk the tip. Still,
   approach properly first.
6. **Mid-scan parameter changes** (scan size / pixels / line rate) cause
   one transient bad line, then recover. This is expected.

---

## 9. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Port combo empty | Teensy not enumerated — replug, click **Refresh** |
| "cannot start reader: serial port not open" in console | Click **Open** before **RUN** |
| `ENGA refused: no setpoint` in log | Set a Setpoint (≥ ~1 nA), Apply, then Engage |
| Continuous scan images blank | Not engaged, or setpoint never reached — check the live current and the Z gauge |
| UI sluggish during legacy GSTS polling | Polling pauses automatically while a continuous scan runs; if it persists, HALT and retry |
| Legacy scan hangs while continuous scan active | You started a legacy operation without HALT — stop the continuous scan first |
| nm / pA values look wrong | Calibration constants (esp. piezo nm/V) not set for your hardware — see Section 3 |
| Saved frame went nowhere | First save prompts for a folder; use **Change folder…** to reset it |
| Tip crashed on engage | Approach was too far / Ki too high / setpoint wrong — re-approach, lower Ki, verify setpoint |

---

## 10. Quick reference

**Continuous-scan procedure:** Approach → set Setpoint/geometry → Apply →
Engage → RUN → (observe, right-click to navigate, Save) → HALT → Retract.

**Units:** Continuous Scan tab and Calibration tab are physical
(nm / pA / Hz / V). Legacy tabs (Main / IV / dIdZ / Grid / Noise /
Scanning) remain in LSB as in v1.

**Bias** has one home: the left-panel Bias control. It is intentionally
not duplicated on the Continuous Scan tab.

**Persisted between sessions:** last serial port, save folder,
`calibration.json` (only when you click Save).

For firmware commands, binary frame layouts, and the build flow, see
[`../README.md`](../README.md).
