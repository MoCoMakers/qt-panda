# DAC Boot-Order Failure: "Set Bias Does Nothing"

## Symptom

Everything *looks* normal:

- The COM port opens and data feeds start (current plot, 200 Hz status stream, recording).
- Clicking **Set Bias** appears to work: the GUI shows the new bias value and voltage.

...but **no bias voltage appears on the line** (check with a multimeter). The X, Y and Z
outputs are dead the same way; bias is simply the easiest one to check.

**A dead bias is the quickest outside check for unconfigured DACs.** The other reliable
indicator, the 4 LEDs on the control board, is usually hidden once the rig is running:

| Control-board LEDs | Meaning |
|---|---|
| All 4 **lit** | DACs **not configured**: outputs stuck, commands ignored |
| All 4 **dark** | DACs configured, working normally |

Also seen when this happened (one session, 2026-09-24, so not yet confirmed as a reliable
sign): the current read about **−17 nA** with the tip fully retracted, instead of the normal
tens of pA.

## Fix

1. Make sure the analog supply (±15 V) is on.
2. In the GUI, click **Reset** (Connection Control section).
3. Set the bias again and check it on the line with a multimeter.

Reset sends the firmware `RSET`, which re-runs the DAC setup that normally only runs at boot.
With the analog rails already up, this setup now sticks and the LEDs go dark.

> **After Reset:** the GUI then sets X, Y, Z and bias to mid-scale (0 V). Bias is now 0 V,
> so set your bias again. Z goes from full retract to mid-range, so make sure the tip is not
> within Z range of the sample before you click Reset.

If bias is still dead after Reset with the rails confirmed on, the cause is something else:
check the bias DAC chip-select (Teensy pin 10), the DAC supply, and the output wiring.

## Prevention: power order

**Turn on the analog supply first, wait about 5 seconds, then plug in the Teensy's USB.**

If the Teensy is already powered (USB plugged in) when the analog rails come up, the DACs end
up unconfigured. When in doubt, just click **Reset** after opening the port, as in Step 2 of
the [System Launch Guide](SYSTEM_LAUNCH_GUIDE.md#step-2-reset-and-verify-current-reading).

## Why it happens

Each of the four AD5761 DACs (X, Y, Z, Bias) has to be *configured* before it outputs
anything. At boot, and on `RSET`, the firmware sends each chip two SPI writes
(`AD5761::reset()`):

1. **Software full reset** (command `0xF`)
2. **Write the control register** (command `0x4`), which sets the output range: ±3 V for
   X/Y/Bias (`RA=101`) and ±10 V for Z (`RA=000`)

Until step 2 takes effect, the chip holds its output at ground, and later writes that set a
value (e.g. `BIAS`) don't reach the output.

The chips' **digital side runs on 3.3 V**, which is on as soon as the Teensy has USB power, so
the boot-time writes do reach the chips. The problem comes afterwards: when the **±15 V analog
rails come up later**, the AD5761 treats it as a power-on and **resets itself**. That wipes the
control register, drives ALERT low (LEDs light) and clamps the outputs. The firmware never
finds out.

The same thing would happen after any **mid-session dip** in the analog supply: the DACs reset
silently and bias stops working without warning.

## Why the GUI can't tell

- **SPI has no acknowledgement.** The Teensy sends 24 bits and carries on; it can't tell
  whether a chip heard it.
- **The bias value the GUI shows is an echo, not a measurement.** The firmware stores what it
  sent (`stm_status.bias = value`) and reports that back.
- The AD5761 does have two ways to give feedback, but on this board neither reaches the Teensy:

| AD5761 feedback | What it tells you | On this control board |
|---|---|---|
| **ALERT** (pin 1, active-low, open-drain) | Low = not configured / brownout / output short | Goes **only to the LED** (3.3 V → R → LED → pin 1) |
| **SDO** (register readback) | Control register contents, plus brownout (BO) and short-circuit (SC) flags | Pads appear **unconnected** |

## Possible future checks

| Option | What it catches | Cost |
|---|---|---|
| **Bodge wire:** ALERT net (DAC pin 1) → spare Teensy pin (2, 3, 4, 5 are free), read with `INPUT_PULLUP` | Unconfigured DACs **and** mid-session brownouts; the only real check | Hardware wire + firmware + GUI banner |
| **Firmware boot delay** (~6 s before DAC setup) | Analog and Teensy powered on at the same time | Reflash |
| **GUI auto-Reset on Open** | Teensy booted before analog, with the GUI opened later (the usual order) | GUI only; resets bias/DAC state on every connect |
| **GUI reboot detection** (firmware `time_millis` jumps back near 0) | Teensy resets mid-session (e.g. USB drops) | GUI only; a hint, not proof |
