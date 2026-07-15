# emulator/ — transient dev harness (NOT for the public repo)

A software stand-in for the Teensy firmware, so the PC continuous-scan path
can be exercised and regression-tested without an instrument.

> **Status: transient.** This folder is intentionally excluded from the
> public/shippable tree (`.gitignore`). It exists only to de-risk the
> software before the `SMOKE_TEST.md` bench validation. It models the
> serial *protocol and frame bytes*, not analog physics — it is not a
> control-loop simulator and is no substitute for the bench.

## Why it's isolated

- It must never ship in the public repo.
- It must never be on the import path of the real software by default.
  `stm_control.STM_Control.open()` imports it **lazily and only when the
  device name is `EMU`**. Deleting this entire folder cannot break the
  shippable code — `open()` with a real port name never references it.

## Use

GUI (no hardware): open the serial port with device name **`EMU`** instead
of a `COM*` port.

Headless smoke-rehearsal:

```
cd dans-software-port
python emulator/firmware_emulator.py
```

This drives the real `SerialReaderThread` through `SMOKE_TEST.md` steps
C5 (ENGA gated by setpoint) → C4 → C6 (RUN) → D2 (mid-scan `IPLN`) →
C7/C8 (HALT) → E1/E2 (lock-in `'M'` frames) and prints frame counts.

## What it does / does not cover

| Covered | Not covered |
|---|---|
| 4-char command dispatch & arg parsing | Real PI / control-loop dynamics |
| `'L'` / `'M'` frame bytes (byte-exact to `binary_frame.hpp`) | ISR timing / jitter (`SMOKE_TEST.md` A3) |
| `ENGA` setpoint gate, `is_scanning` flag, `GSTS` 10-int line | Picometre-level Z behaviour (B3) |
| Mid-scan `IPLN`/`LRAT`/`SETD` changes (D2/D6 shape) | Analog topography (surface is synthetic) |
| Reader-thread / live-raster wiring & throughput | Anything requiring the actual instrument |
