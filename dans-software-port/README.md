# dans-software-port

A Dan-Berard-style control architecture for the qt-panda STM, running on qt-panda hardware (Teensy 4.1, 4× AD5761, LTC2326-16, ULN2003 stepper).

The design rationale lives in [`../documentation/docs-for-ai/pivot-to-dan-style-control.md`](../documentation/docs-for-ai/pivot-to-dan-style-control.md).

## Relation to `../pc/` and `../teensy/`

The top-level `pc/qtpanda/` and `teensy/arduinosrc/` trees are the **v1 baseline** and remain **frozen** for the duration of this port. Bug-fixes and features land here, in `dans-software-port/`, not in v1.

This folder began as a byte-identical copy of v1 and has since evolved independently. When this port is proven on hardware, the long-term plan is for `dans-software-port/` to supersede v1.

## What's different (the "Dan-style" elements)

| Feature | v1 baseline | dans-software-port |
|---|---|---|
| Control loop | Cooperative `loop()`-driven, variable cadence | Deterministic `IntervalTimer` ISR at fixed 40 µs |
| Effective DAC resolution | 16 bits (AD5761 native) | 20 bits via sigma-delta dither |
| Scan acquisition | Cooperative reads in main loop | Ping-pong line buffers filled by ISR |
| Scan pattern | One-shot raster (`SCST`) | Continuous bidirectional trace/retrace + legacy one-shot retained |
| Streaming protocol | ASCII rows | Binary `'L'` frames over USB-Serial (921 600 baud) |
| PC threading | Synchronous `readline()` in UI thread | `QThread`-based reader, signals into the UI |
| Spectroscopy | IV / dIdV / dIdZ / grid (ASCII) | All retained, plus lock-in dI/dV (binary `'M'` frame) |
| Physical units in UI | LSB-only | LSB + physical (nm, V, pA) via `calibration.json` |

The 4× AD5761 chips on our board (vs Dan's single DAC8814) impose only a small constant CS-toggling overhead inside the ISR; Teensy 4.1 has ample headroom at 600 MHz.

## Project layout

```
dans-software-port/
├── README.md                              this file
├── teensy/arduinosrc/main/
│   ├── main.ino                           4-char command dispatcher, loop
│   ├── stm_firmware.hpp                   STM class: ISR, PI, scan, legacy
│   ├── sigma_delta.hpp                    three-line dither (Wescott)
│   ├── line_buffer.hpp                    ping-pong buffers + writePixel
│   ├── binary_frame.hpp                   'L' and 'M' frame emitters
│   ├── AD5761.{hpp,cpp}                   unchanged from v1
│   ├── LTC2326_16.{hpp,cpp}               unchanged from v1
│   ├── EfficientStepper.hpp               unchanged from v1
│   └── logTable.hpp                       unchanged from v1
└── pc/qtpanda/
    ├── widget.py                          main window (legacy tabs + continuous-scan tab)
    ├── stm_control.py                     command sender + ASCII parser
    ├── serial_reader.py                   QThread parsing binary 'L', 'M', and ASCII
    ├── scan_controller.py                 translates UI events into 4-char commands
    ├── live_raster.py                     pyqtgraph live Z + error images
    ├── calibration.py                     LSB ↔ nm / V / pA conversions
    ├── calibration.json                   tunable hardware constants
    ├── plotframe.py                       pyqtgraph wrapper (legacy)
    ├── form.ui / ui_form.py               Qt Designer layout for legacy tabs
    └── (other legacy files)
```

## Building the firmware

- Open `teensy/arduinosrc/main/main.ino` in the Arduino IDE.
- Tools → Board → **Teensy 4.1**
- Tools → USB Type → **Serial**
- Tools → CPU Speed → **600 MHz**
- Verify, then Upload.

Expected flash usage: ~57 KB code, ~210 KB RAM1 (most of which is the two 16 KB ping-pong buffers and existing scan arrays).

## Running the PC software

```
cd dans-software-port/pc/qtpanda
python widget.py
```

Dependencies (PySide6, pyqtgraph, pyserial, tifffile, gwyfile) match v1 — see `../../pc/qtpanda/pyproject.toml`.

## Command reference

All commands are exactly 4 ASCII characters. Arguments follow on the same line as decimal text, parsed by `Serial.parseInt()` / `parseFloat()`.

### Preserved from v1

| Cmd | Args | Meaning |
|---|---|---|
| `RSET` | — | Reset all DACs, stepper, status |
| `GSTS` | — | Get status (returns 10 comma-separated ints) |
| `BIAS` | `lsb` | Set bias DAC (16-bit code) |
| `DACX` `DACY` `DACZ` | `lsb` | Direct DAC write |
| `ADCR` | — | Read averaged ADC |
| `MTMV` | `steps` | Move stepper motor |
| `MTOF` | — | Disable stepper coils |
| `MTDR` | `dir` | Motor direction (1 or −1) |
| `APRH` | `target` `steps` | Coarse approach to tunneling threshold |
| `CCON` | `target` | Engage const-current PI (legacy, with bumpless transfer) |
| `CCOF` | — | Disengage PI |
| `PIDS` | `Kp Ki Kd` | Set legacy PI gains (also updates ISR gains) |
| `SETL` | `xµs yµs zµs biasµs` | Per-axis settle times |
| `IVME`/`IVGE` | `start end step` / — | Measure / fetch IV+dIdV curve |
| `DIME`/`DIGE` | `start end step` / — | Measure / fetch dI/dZ curve |
| `NOIS` | `xres yres spp µs` | Noise scan |
| `GSPC` | (10 args) | Grid spectroscopy (binary `'PX'` frames) |
| `SCST` | (7 args) | One-shot raster scan (ASCII rows) — deprecated; retained for back-compat |
| `TEST` | — | Piezo sweep self-test |
| `STOP` | — | Halt all active modes |

### New — Dan-style continuous scan

| Cmd | Args | Meaning |
|---|---|---|
| `RUN ` | — | Start continuous bidirectional scan (note trailing space) |
| `HALT` | — | Stop continuous scan |
| `ENGA` | — | Engage PI with bumpless transfer (refused if no setpoint) |
| `RTRC` | — | Retract: PI off, Z parked at safe value |
| `SCSZ` | `lsb` | Scan size in LSBs (range of X/Y sweep) |
| `IPLN` | `n` | Samples per line (= 2 × image pixels; trace + retrace) |
| `LRAT` | `hz×100` | Line rate in units of 0.01 Hz (100 → 1.00 Hz) |
| `XOFS`/`YOFS` | `lsb` | Scan offsets |
| `SETP` | `lsb` | Tunneling current setpoint |
| `KPGA`/`KIGA` | `value` | PI gains for ISR loop |
| `SETD` | `µs` | ISR period (10 … 1000 µs; defaults to 40) |
| `LIDV` | `bias_center bias_amp freq_hz n_periods` | Lock-in dI/dV measurement (binary `'M'` frames) |

## Binary frame formats

### `'L'` — continuous-scan line

```
byte 0      : 0x4C ('L')
bytes 1-2   : uint16  line_number       (big-endian)
bytes 3-4   : uint16  pixels_per_line   (big-endian)
bytes 5..   : int32   z[pixels_per_line]      (big-endian)
            : int32   err[pixels_per_line]    (big-endian)
last byte   : 0x0A
```

Total = `5 + 8·N + 1` bytes.

### `'M'` — lock-in dI/dV point

```
byte 0   : 0x4D ('M')
bytes 1-2: uint16  point_index   (big-endian)
bytes 3-6: int32   bias_lsb      (big-endian)
bytes 7-10: int32  in_phase      (big-endian)
bytes 11-14: int32 quadrature    (big-endian)
byte 15  : 0x0A
```

## Calibration

`pc/qtpanda/calibration.json` holds linear LSB ↔ physical-unit conversion factors:

| Field | Default | Source |
|---|---|---|
| `dac_x_v_per_lsb`, `dac_y_v_per_lsb`, `dac_bias_v_per_lsb` | 10/65536 | AD5761 ±5 V config |
| `dac_z_v_per_lsb` | 20/65536 | AD5761 ±10 V config |
| `piezo_*_nm_per_v` | 3-5 nm/V | Placeholder; per-tip calibration recommended |
| `adc_v_per_lsb` | 20.48/65536 | LTC2326-16 ±10.24 V input |
| `preamp_a_per_v` | 1/100 MΩ | Trans-impedance feedback resistor |

Edit the JSON or use `Calibration.from_json()` / `.to_json()` programmatically.

## References

- `../documentation/docs-for-ai/pivot-to-dan-style-control.md` — full design rationale
- `../documentation/docs-for-ai/dan-blog-electronics-review.md` — hardware ground-truth
- [Dan Berard, "Home-built STM"](https://dberard.com/home-built-stm/) — the design we're porting
- `../reference/Dans Software/Teensy/STM_Controller/` — Dan's original firmware (read-only reference; **not** redistributed)

## License & attribution

The qt-panda hardware design and v1 firmware are the project's own work. This port adopts the *architecture* described in Dan Berard's published electronics design — we translate his patterns to our chip set rather than redistributing his code.
