# Hardware notes: isolation, preamp, controller board

**Status:** working notes, started 2026-10-16 from the team's description and screenshots of the design files. Anything marked *unverified* was read from an image or inferred, not checked against the design files or the hardware.
**Related:** [DAC_BOOT_ORDER.md](DAC_BOOT_ORDER.md) (ALERT LEDs, power-up order), [refined-docs/1. PREAMP.md](refined-docs/1.%20PREAMP.md), image descriptions in [references/image_map.csv](references/image_map.csv) (PREAMP_*, CONTROL_BRD_COMPONENTS_*, TEENSY_BRD_1), firmware pin map in `software/firmware/arduinosrc/main/stm_firmware.hpp`, meeting notes 2026-10-15 (driver voltages measured on the bench).

## Physical stack and vibration isolation

From the outside in:

- **Base:** a 3D-printed case filled with a plaster and sand base for mass.
- **Isolation:** magnetic (inductive) damping. An aluminium plate is held on four brass-tube posts over neodymium magnets. The plate is meant to glide freely along the posts. Motion of the plate induces eddy currents in the aluminium, which damp vibration. The older spring-suspension method is no longer used. CAD lives in `hardware/CAD/maglev_vib_iso_table`; despite the folder name, the plate is damped by the magnets, not levitated.
- **Electronics cubby:** the controller board and the Teensy sit in a compartment in the case. The DSUB connectors come out of it and run by cable up to the floating platform.
- **Faraday cage:** on the platform. The cables enter through a small opening.
- **Inside the cage:** the current **"longboard"** head: the scanner (piezo disc with stem and tip), the sample plate, and the stepper-driven screw-and-lever coarse approach. The **wedge assembly** is a future replacement concept for the longboard (aimed at stiffness and thermal drift); it isn't built yet.

**Friction on the posts.** At the nanometre-to-micrometre motions that matter here, the plate may not glide at all. Brass sliding on brass can stick until enough force builds up, then slip (stick-slip, or friction lock). While stuck, the plate is effectively bolted to the case and passes floor vibration straight through. Each slip is a small sudden jump. Possible signatures in our data:
- noise or drift that changes in steps rather than smoothly;
- occasional single-event jumps in Z or image position;
- the ~3 Hz row wobble coming and going between sessions.

Tests:
1. Tap the base during a halted capture with the plate as it is, then again after gently nudging the plate so it's free, and compare the spectra.
2. Film or log the plate's motion when the table is tapped. A phone accelerometer resting on the plate is enough to see whether it bounces freely and at what frequency.
3. Look back through the 200 Hz status logs for step changes in noise level.

Possible fixes, if friction is confirmed: low-friction bushings (PTFE or graphite) on the posts, better post alignment, or flexure guides instead of sliding posts.

**Why it matters for noise:** the cables from the cubby to the floating platform are a mechanical path around the isolation. Stiff cables can short-circuit an isolation stage; the STM literature reports this for pumping lines. They are also the path for the preamp signal and the piezo drive.

**Documentation to-do**
- [ ] Photograph the isolation box: the case and base, the plate on its brass posts, the magnets, the electronics cubby and the cable route up to the cage. No photo exists yet. Add it to `docs/images/` and `references/image_map.csv`.
- [ ] Record the plate's mass, the post spacing and clearance, the magnet size and gap, and the cable type and length to the platform.

## Preamp V3 (QTPandaPreamp-V3, EasyEDA, created 2026-04-16, updated 2026-04-30)

![Preamp V3 schematic](images/hardware/preamp_v3_schematic.png)

| Part | Role | Notes |
|---|---|---|
| U1 OPA828IDGNR | Transimpedance stage: tip current → voltage | Feedback element "CapResSubassembly" between −IN (pin 2) and OUT. It is the gain resistor (100 MΩ in the GUI calibration, `preamp_v_per_a = 1e8`) with its parallel capacitance. The probe connects to −IN. The schematic notes the probe-side route must be as short as possible. |
| R3 3 kΩ + C11 1 nF | RC low-pass between stages | Corner ≈ 53 kHz. The schematic carries a note: "TODO. Maybe this should be 3.3 kΩ". |
| U3 OPA210IDR, R2 12 kΩ, R4 3 kΩ | Second stage, non-inverting | Gain 1 + 12k/3k = 5 *unverified* |
| R1 220 Ω | Series output resistor | Isolates the op-amp from cable capacitance |
| U4 MC78L12, U5 MC79L12 | ±15 V in → ±12 V regulators | With 4.7 µF and 2.2 µF bypass |
| H1, 5-pin | +15 V, signal out, ground, −15 V | Pin order *unverified* from the schematic image |

**Bandwidth.** The Sept 17 data showed a ~400 µs time constant (~400 Hz corner). With 100 MΩ feedback that implies about 4 pF across the feedback resistor, counting strays. This fits the 0.3–3 pF range assumed in `docs/ai/research-harness/physics/scan_bandwidth.py` plus layout capacitance.

**Questions:** Is V3 the board installed on Sept 24, when the GUI reported preamp gain 1X? A fixed ×5 second stage would make the total gain 500 mV/nA, not 100. The controller board labels its input "diff pair from preamp", but V3's output looks single-ended (signal plus ground). Which is it?

## Piezo drive: how the four pad voltages are formed

The piezo disc's top electrode is split into four pads (a cross: two arms, X and Y). The driver (OPA2227P summing stages U9, U10, U13) makes each pad voltage by **adding a Z part and an X or Y part**:

| Pad | Voltage |
|---|---|
| Z+X | V<sub>Z</sub> + V<sub>X</sub> |
| Z−X | V<sub>Z</sub> − V<sub>X</sub> |
| Z+Y | V<sub>Z</sub> + V<sub>Y</sub> |
| Z−Y | V<sub>Z</sub> − V<sub>Y</sub> |

with, from the bench measurement of 2026-10-15:
- **V<sub>Z</sub> = −2 × Z DAC voltage.** The Z DAC's ±5 V becomes ±10 V at the pads, inverted.
- **V<sub>X</sub> = +0.6 × X DAC voltage**, and likewise for Y. The X DAC's ±5 V becomes ±3 V at the pads.

What that means:
- **Z sets the height.** It is the same on all four pads, so it lifts or lowers the whole cross without tilting it.
- **X is a see-saw on its arm.** It is added on one pad and subtracted on the other, so the two X pads differ by 2 × V<sub>X</sub>. That tilts the disc, and the stem turns the tilt into sideways tip motion. Y does the same on the other arm.
- **Each pad's voltage is the Z value plus or minus the X (or Y) value.** The extremes are therefore Z max ± X max: **±13 V** absolute (10 + 3), safely inside the ±15 V supply.
- **Bench check (2026-10-15):** Z at −10 V with X DAC at 2.5 V (X part 1.5 V) read −8.5 V and −11.5 V on the two X pads, exactly −10 ± 1.5.
- **Open question:** both summing inputs use 3 kΩ resistors, yet Z is scaled ×2 (inverted) and X ×0.6. The circuit around the summing stages must set the different gains; the schematic should be checked to confirm.

The interactive cross in the scan-resolution report (Figure 1) models exactly this and was confirmed by the team as matching their intent.

## Key chips and their speed limits

| Chip | Role | Where | Key speeds | Our setting |
|---|---|---|---|---|
| **Teensy 4.1** (NXP i.MX RT1062, Cortex-M7) | Real-time controller | Electronics cubby | 600 MHz; USB high speed (480 Mbit/s) | 100 kHz control tick (SETD 10); measured worst-case tick ~1 µs (DIAG) |
| **AD5761ARUZ** (×4, TSSOP-16; LCSC C650241 per the PCB properties). This is the version without an internal reference, so the DACs share an external reference (U5, net VREF1) | 16-bit DACs: X, Y, Z, bias | Controller board U1–U4 | Serial clock up to 50 MHz; output settling 7.5 µs; noise 35 nV/√Hz | SPI 40 MHz (`AD5761.hpp`) |
| **External voltage reference** (U5, part number not yet read) | Reference voltage for all four DACs (VREF1) | Controller board U5 | Its noise and drift add directly to X, Y, Z and bias | — |
| **OPA2227P** (dual, DIP-8; LCSC C1346534) ×3 | Piezo driver: summing stages making Z+X, Z−X, Z+Y, Z−Y, plus the bias buffer | Controller board U9, U10, U13 | 8 MHz gain-bandwidth; 2.3 V/µs; 3 nV/√Hz. Each stage has 3 kΩ inputs and 4.7 nF feedback, so the drive is rolled off near 11 kHz | — |
| **LT1469** (dual; LT1469IN8 in the BOM notes) ×1 | ADC input buffers for PREAMP+ and PREAMP− | Controller board U21 | 90 MHz gain-bandwidth; 22 V/µs; 16-bit settling in 900 ns. Each input has a 470 Ω + 3.3 nF filter (corner ~100 kHz) before the ADC | — |
| **LTC2326-16** | 16-bit ADC, tunnel current | Controller board U15 | Up to 250 ksps; internal conversion clock | SPI 40 MHz (`LTC2326_16.hpp`); BUSY not checked |
| **OPA828** | Preamp transimpedance stage (100 MΩ feedback) | Preamp V3, U1 | 45 MHz gain-bandwidth; 150 V/µs; JFET input, very low bias current | — |
| **OPA210** | Preamp second stage (gain ×5, *unverified*) | Preamp V3, U3 | 18 MHz gain-bandwidth; 6.4 V/µs; 2.2 nV/√Hz; bias 0.3 nA typical | — |
| **MC78L12 / MC79L12** | ±12 V regulators for the preamp | Preamp V3, U4/U5 | — | — |
| Regulators U17, U18, U16, U22 | +15 V, −15 V, 3.3 V and 5 V from the V++/V−− input (U19); LED5 and LED6 show the rails | Controller board | Linear regulators per the power-supply notes (image map POWER_1) | — |

**Controller board schematic v0.2 details** (EasyEDA, MoCo Maker Labs; pages DAC, ADC, Connectors):
- **DSUB1 (to the piezo):** Z+X, Z−X, Z+Y, Z−Y and AGND.
- **DSUB2 (to the preamp):** +15 V, −15 V, AGND, PREAMP+, PREAMP− and BIAS. The preamp is powered from the controller board, and the bias also travels on this cable. PREAMP− is most likely the preamp's own ground or reference, measured pseudo-differentially by the ADC, which rejects ground offsets between the boards *(to confirm against preamp V3's 5-pin header)*.
- **Grounds:** the schematic has two ground nets, GND (digital) and AGND. The Teensy header H1 connects to GND in the schematic, while the PCB silkscreen labels those pins AGND. Where the two nets join, and whether at a single point, is the key question for the grounding tests.
- **DAC output ranges:** `USER_GUIDE.md` lists X, Y and bias at ±5 V and Z at ±10 V, but the Sept 24 scan notes say the firmware's range bits select ±3 V for X, Y and bias. The bench measurement on 2026-10-15 (pads swing ±3 V from X/Y and ±10 V from Z) needs reconciling with both.
- **Overrides:** the BOM notes (`refined-docs/1. PREAMP.md`) list 3× OPA2227P and 1× LT1469IN8 for the controller board, which matches the CAD. No other part substitutions are recorded in the repo; any overrides kept elsewhere (meeting notes, Drive) should be copied here.

**What actually sets the loop's speed limit:**
- **DAC settling, 7.5 µs.** A new X, Y or Z value needs about 7.5 µs to settle, so control ticks much faster than about 130 kHz would write values before the previous ones settle. The current 10 µs tick sits just inside this.
- **ADC throughput, 250 ksps.** This caps the loop at 250 kHz, above the DAC limit.
- **SPI time per tick.** At 40 MHz, a 24-bit DAC write takes about 0.6 µs, so three axis writes plus one ADC read take about 2–3 µs of the 10 µs tick.
- **Signal bandwidth (~400 Hz measured).** This is set by the 100 MΩ feedback resistor and its stray capacitance (about 4 pF), not by the op-amps, whose bandwidths are tens of MHz.

None of these limits is the microcontroller.

## Tunnelling current (reference)

![Tunnelling current equation](images/hardware/tunneling_current_equation.gif)

The standard approximation: current ∝ exp(−2κs) × tip density of states × the sample's states integrated over the bias window, with κ = √(2mφ)/ħ. For a work function φ ≈ 4–5 eV, 2κ ≈ 2.1–2.3 per Å, so the current changes about **tenfold per ångström** of gap. That's why picometre vibrations show up in the current, and why Z, not the current, is the height signal in constant-current mode.

## Image processing caution: raw vs "coerced"

![Raw vs coerced 3D views](images/hardware/raw_vs_coerced_3d.png)

Gwyddion 3D views of the same scan. Left: the raw channel. Right: after Gwyddion's "Coerce" (value-distribution remapping) with lighting and a gold palette. Coercion reshapes the height histogram, so it can make texture look like morphology and changes relative heights. It's fine for illustration, but measurements and claims about structure should come from the raw or minimally levelled data, ideally passing the four-part acceptance test in the scan-resolution report (survives trace/retrace folding, repeats across frames, appears in both Y halves, scales with zoom). The axes read "1.00 m" because the file had no physical scale set.

## Controller board v0.4: what the design files show

From screenshots of the schematic and PCB layout (project "QT Panda - Scanning Tunneling Microscope", sheets 1. DAC, 2. ADC, 3. Connectors, and PCB1).

### Signal path

The PCB annotations number the path from tip back to piezo:

| # | Block | Parts (from the layout) | Notes |
|---|---|---|---|
| 1 | Differential input from the preamp | DSUB2 | Preamp outputs a differential pair |
| 2 | Buffer amplifier and low-pass filter | LT1469 dual U21, with R23–R26 (470 Ω) and C27–C30 (3.3 nF) | Buffers PREAMP+ and PREAMP− into the ADC |
| 3 | ADC | U15 | LTC2326-16 in firmware (`LTC2326_16`) |
| 4 | Header to the microcontroller | H1, 26-pin | Annotated "I2C", but the signals are SPI (see below) |
| 5 | DACs | U1–U4, one per channel, each with an LED | AD5761 in firmware. The LEDs are the ALERT indicators (lit = not configured; see DAC_BOOT_ORDER.md). The annotation names U3 as the DAC that "gets piezo state" |
| 6 | Piezo driver | OPA2227P duals U9, U10, U13 | Adds and subtracts Z with X and Y to make the four pad voltages Z+X, Z−X, Z+Y, Z−Y; also buffers the bias |
| 7 | Output to the piezo | DSUB1 | Four quadrant pads |
| – | Supplies | U19 (V++ / V−− input), regulators U17 (+15 V), U18 (−15 V), U16 (3.3 V), U22 (5 V) | LED5 and LED6 show the rails |

### Header H1 (board to Teensy)

From the "3. Connectors" schematic sheet and the PCB silkscreen:

| Pin | Net | Pin | Net |
|---|---|---|---|
| 1 | GND (AGND) | 2 | ADC_CNV |
| 3 | GND (AGND) | 4 | ADC_BUSY |
| 5 | GND (AGND) | 6 | ADC_SDI |
| 7 | GND (AGND) | 8 | ADC_SCK |
| 9 | GND (AGND) | 10 | ADC_SDO |
| 11 | GND (AGND) | 12 | SCLK (DAC SPI clock) |
| 13 | GND (AGND) | 14 | SDI (DAC SPI data) |
| 15 | GND (AGND) | 16 | SYNC4 |
| 17 | GND (AGND) | 18 | SYNC2 |
| 19 | GND (AGND) | 20 | SYNC3 |
| 21 | GND (AGND) | 22 | SYNC1 |
| 23 | GND (AGND) | 24 | not connected |
| 25 | GND (AGND) | 26 | not connected |

SYNC1–4 are the AD5761 chip selects. The firmware drives them on Teensy pins 7 (X), 9 (Y), 8 (Z) and 10 (bias). The ADC uses pins 38 (CS), 39 (MISO), 19 (CNV) and 18 (BUSY). Which SYNC goes to which Teensy pin depends on the cable or adapter between H1 and the Teensy, which isn't in these screenshots.

### Observations

- **Ground labelling.** All 13 odd header pins are labelled AGND on the PCB silkscreen but connect to the digital GND net in the schematic (see the schematic details above). The Teensy's digital ground, and therefore the USB ground from the PC, joins the analog ground directly through this header. The header sheet shows no separate digital ground. Digital return currents (SPI clocks every control tick, USB traffic) can therefore flow in the same ground as the ADC and DAC references.
  - Measured effect so far: with the tip not tunnelling, the current shows a pattern locked to each scan line of about 0.7 pA (Sept 24, 03:11–03:13, 32.6 Hz lines). That's small compared with the 1 nA setpoint, but not zero.
  - The Sept 24 fix that tied a floating DSUB spare wire to the cage ground cut raw noise from 48 to 20 pA, so grounding matters on this rig.
- **The ADC BUSY line is wired** (header pin 4, Teensy pin 18), but the firmware doesn't wait on BUSY before reading. This is code-review item "SETD floor": at fast control rates, a read could start before the conversion finishes.
- **A 3.3 V trace runs along the header** *(unverified: may be the Teensy's 3.3 V supplying board logic)*.
- **Annotation 4 says "I2C"**, but every signal on H1 is SPI (clock, data, chip selects) plus the ADC's convert and busy lines. The label should be corrected to avoid confusion.

### Open questions

1. Where do the GND and AGND nets join, and is it a single point? Are the header pins on GND or AGND in the as-built board?
2. Which part is the external DAC reference U5, and what are its noise and drift?
3. Does the Teensy's 3.3 V power anything on this board?
4. How is H1 cabled to the Teensy (ribbon or adapter), and how long is it?
5. Where does the preamp get its supply and ground: from this board through DSUB2, or separately?
6. Which output range is each AD5761 actually configured for (±3, ±5 or ±10 V)?

### Suggested grounding tests

Easiest first:
1. Run a scan and a halted capture with the laptop on battery (charger unplugged), to break any ground loop through the PC.
2. With the tip not tunnelling, run a scan at 195 Hz lines and check the current for a pattern locked to each line. The existing check was at 32.6 Hz.
3. Scope analog ground against the USB shield, and the Z DAC output, triggered once per scan line.
4. Try a ferrite on the USB cable, or a powered hub. Most USB isolators run at full speed only (12 Mbit/s); the 100 kHz raw tap alone needs about 1 MB/s, so an isolator would break it.
