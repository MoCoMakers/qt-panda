# Software mockup — real PC software vs. an emulated Arduino, in Docker

Run the **actual** `pc/qtpanda` code against a **software-emulated STM
controller** — no Teensy, no preamp, no tip. Two containers wired by a virtual
serial link, launched with one `docker compose up`.

The emulator speaks the *exact* firmware wire protocol (fixed 4-char commands +
`Serial.parseInt()` args, and the `GSTS` CSV status line from the firmware's
`to_char`), so the PC code connects **unmodified**. Its ADC signal model
reproduces the stability phenomenon under study — baseline noise, steady
tunneling, thermal-style **drift**, and **in/out-of-zone** wander — so the
Stability tab, the raw-CSV logging, and the live drift/jitter readout can be
exercised end to end.

```
software-mockup/
├── docker-compose.yml         # wires emulator + PC together
├── emulator/
│   ├── Dockerfile
│   └── stm_emulator.py        # faithful protocol + tunneling signal model
├── pc/
│   ├── Dockerfile             # headless driver image (socat + pyserial + numpy)
│   ├── Dockerfile.gui         # optional full PySide6 GUI image
│   ├── entrypoint.sh          # socat serial<->TCP bridge, then run
│   └── mockup_driver.py       # headless: drives the REAL stm_control.STM
└── out/                       # captured CSVs appear here
```

## Quick start

```bash
cd docs/ai/research-harness/software-mockup
docker compose up --build
```

You'll see the emulator accept a connection and the driver stream ~30 s of
status, then print the drift readout — the **same** `stab_metrics` math the GUI
uses — and write `out/mockup_stability.csv`. Expected (default `drift` mode):

```
[driver] DRIFT READOUT (same math as the GUI):
           v_z      = +40.xx pm/s  (R2=0.9x)     # recovers STM_DRIFT_PM_S
           jitter   = ~30 pm  (sigma_z)          # recovers STM_JITTER_PM
           skew(lnI)= ...
```

Recovering the injected `+40 pm/s` drift and `30 pm` jitter is the end-to-end
proof that the protocol, streaming, logging, and drift math all work.

## Scenarios (choose the fault to emulate)

Set `STM_MODE` (and optionally the parameters) on the command line:

| `STM_MODE` | what it emulates | histogram shape |
|---|---|---|
| `noise`  | tip **not** tunneling — electronics only | broad, symmetric (matches `realdata_not_approached_noise.png`) |
| `tunnel` | steady tunneling + jitter | narrow log-normal |
| `drift`  | linear thermal-style gap drift (default) | peak marches, spread grows |
| `inout`  | sinusoidal in/out of the good zone | bimodal / duty-cycled |

```bash
STM_MODE=noise  docker compose up --build
STM_MODE=inout  STM_PERIOD_S=15 STM_INOUT_AMP_PM=400 docker compose up
STM_DRIFT_PM_S=120 STM_JITTER_PM=15 docker compose up      # fast drift, quiet tip
RUN_SECONDS=120 docker compose up                          # longer capture
```

All knobs: `STM_MODE, STM_SETPOINT_PA, STM_DRIFT_PM_S, STM_JITTER_PM,
STM_INOUT_AMP_PM, STM_PERIOD_S, STM_NOISE_OFFSET, STM_NOISE_COUNTS`
(emulator) and `RUN_SECONDS, POLL_HZ` (driver). See `emulator/stm_emulator.py`.

## Optional: the real GUI in a container

```bash
xhost +local:docker            # allow the container to reach your X server
docker compose --profile gui up --build
```
In the window: enter `/tmp/stm_pty` in the COM field → **Open** → go to the
**Stability** tab → **Start**. Needs an X server (Linux or WSLg). This image is
heavier (PySide6); the headless path above needs neither Qt nor a display and is
the recommended default. GUI stability logs are written into the mounted
`pc/qtpanda` working copy (or set the Save field to `/out`).

## What's faithful vs. simplified

- **Faithful:** command framing (4-char + `parseInt`), `GSTS` status CSV and
  field order, CRLF line endings, 921600-baud serial semantics (via socat PTY),
  and the ADC↔current scaling (`adc_to_amp`).
- **Simplified:** scan / noise-scan / IV / dIdZ / grid replies return
  plausible synthetic data so those tabs don't hang — they are *not* a physics
  model. Only the **Stability / GSTS current stream** is physically grounded.
- The tunneling model uses `I = I0·exp(-2κz)` with φ = 4 eV, matching
  `pc/qtpanda/stab_metrics.py` (the single source of truth shared with the GUI).

## Notes

- The emulator handles one PC connection at a time; it accepts reconnects.
- Nothing here talks to real hardware — safe to run anywhere Docker runs.
