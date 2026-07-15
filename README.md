# qt-panda — Homebuilt STM Control Software

Control software and firmware for a scanning tunneling microscope (STM)
built in the style of [Dan Berard's home-built STM](http://dberard.com/home-built-stm/).
A **Teensy 4.1** microcontroller runs the real-time control loop; a
**PySide6** desktop app on the PC drives it, streams data, images the
surface, and records everything for faithful replay.

> **This repo was reorganized 2026-07-15.** All code lives under
> `software/` (`software/pc/`, `software/firmware/`). The previous originals
> were moved to `Archive/`, and the
> superseded working tree `dans-software-port/` is retired (its useful
> parts were promoted; experimental/demo code is under
> `Archive/dans-experimental/`).

---

## Repository layout

| Path | What it is |
|---|---|
| `software/pc/qtpanda/` | **The PC application** (Python/PySide6). Entry point: `main.py`. |
| `software/firmware/arduinosrc/main/` | **The firmware** (Arduino/C++). Entry point: `main.ino`. |
| `software/pc/requirements.txt` | Python dependencies. |
| `software/pc/CHANGELOG.md` | Hard-won learnings and non-obvious fixes — **read this**. |
| `software/pc/qtpanda/emulator/` | Opt-in software firmware emulator (run the app with no hardware). |
| `docs/ai/research-harness/` | Physics modeling harness (drift, scan bandwidth, mechanics). |
| `Archive/` | Old originals + retired experimental code, kept for reference. |

### Key PC modules

- `main.py` — the GUI application (tabs, live raster, controls).
- `stm_control.py` — serial protocol + `STM_Status` (unit conversions live here).
- `scan_controller.py` — continuous-scan geometry, feedback, nm↔firmware units.
- `serial_reader.py` — threaded binary frame parser (scan lines, status, raw).
- `live_raster.py` — the continuous-scan image display (Y-fold, level tracking).
- `copilot_bridge.py` — **localhost HTTP control channel** for scripts/LLMs.
- Recorders: `session_journal.py` (commands+notes), `status_logger.py`
  (200 Hz CSV, true-time writer thread), `frame_logger.py` (verbatim scan
  frames), `raw_logger.py` (25 kHz raw), `scst_logger.py` (legacy scans).
- Replay/analysis: `replay_frames.py`, `raw_scan_reconstruct.py`,
  `superscan.py` (multi-frame super-resolution).
- `calibration.py` / `calibration.json` — physical-unit constants.

---

## Getting started (PC app)

### 1. Install

```bash
cd software/pc
python -m venv .venv && . .venv/Scripts/activate   # Windows Git Bash
pip install -r requirements.txt
```

Also install the **Arduino IDE** (bundles `arduino-cli`) if you will flash
firmware; the Teensy board support is `teensy:avr:teensy41`.

### 2. Run

```bash
cd software/pc/qtpanda
python main.py                       # opens the GUI, no port
python main.py --port COM5           # auto-open a serial port at startup
python main.py --port COM5 --copilot 8765   # + HTTP control on :8765
python main.py --port EMU            # software emulator, no hardware
```

### 3. First light (bench workflow)

1. **Open** the serial port (or launch with `--port`). Recording starts
   automatically and runs the whole session (journal + 200 Hz CSV).
2. **Set Bias** to a small value (e.g. −0.2 V) and pick the **Preamp gain**
   (1X / 5X) to match your hardware.
3. **Approach**: the motor + piezo close the gap until tunnelling current
   appears. *Down = toward the sample* on the Z slider.
4. **Continuous Scan** tab → set size (in nm), press **RUN**. Use
   **Auto Levels** and the Z/Err images. Or use the legacy **Scan** button
   on the Scanning tab for a slow, settled single frame.
5. Every image is saved verbatim and is replayable — see below.

### 4. Firmware flash (only when firmware changes)

```bash
# close any program holding the serial port first
arduino-cli compile --fqbn teensy:avr:teensy41 \
  --libraries "<Arduino15>/libraries" software/firmware/arduinosrc/main
arduino-cli upload  -p COM5 --fqbn teensy:avr:teensy41 software/firmware/arduinosrc/main
```
Flashing reboots the firmware (resets steps counter, bias, DACs). It is
also the software way to clear a wedged serial port.

---

## Data & replay

Everything on screen is reconstructible from disk (see CHANGELOG for the
principle). Recordings land under `software/pc/qtpanda/`:

- `logs/session_*.jsonl` — every command/note with attribution + timestamps.
- `images/*_stability_*.csv` — 200 Hz status stream.
- `scans/scan_*.frames` (+ `.json` sidecar) — verbatim continuous-scan lines.
- `scans/scst_*.scst` — verbatim legacy-scan rows.
- `raw/raw_*.raw` — 25 kHz raw ISR samples.

Replay a continuous scan offline: `python replay_frames.py scans/scan_*.frames`.

Export for **Gwyddion**: scans save as `.gsf` with physical units (m, A)
embedded, so they open at true nm scale.

---

## LLM / scripting harness (the copilot bridge)

Launch with `--copilot 8765` to expose a **localhost-only** JSON-over-HTTP
control channel. An LLM (or any script/`curl`) can then observe and actuate
the instrument. Every endpoint drives the *real* GUI widgets and clicks the
*real* buttons — so agent actions take the identical code path as a human,
appear on screen, and are journaled with `src="agent"`.

```bash
curl -s localhost:8765/status                    # full state
curl -s "localhost:8765/samples?n=200"           # recent current samples
curl -s localhost:8765/screenshot                # grab the window -> PNG path
curl -s -X POST localhost:8765/bias  -d '{"dac":35014}'
curl -s -X POST localhost:8765/motor -d '{"steps":-5}'      # retract 5
curl -s -X POST localhost:8765/scan/run  -d '{}'
curl -s -X POST localhost:8765/note  -d '{"text":"cage on"}'
```

Safety: binds to localhost only; a `POST /gate {"enabled":false}` disables
all actuation while leaving observation live. Motor/approach never move
toward the sample without an explicit request.

### Prompts & tips for driving it with an LLM

- **Give the agent the physics, not just the API.** "Higher Z DAC = toward
  the sample = more current" prevents a whole class of direction bugs.
- **Make it verify, not assume.** Ask it to poll `/status` before and after
  every actuation and compare, and to `/screenshot` and read the result.
- **Ground truth beats the display.** Have it rebuild images from the
  `.frames`/`.scst`/`.raw` files (see `replay_frames.py`,
  `raw_scan_reconstruct.py`) rather than trusting the on-screen render.
- **Cross-check two ways.** Legacy vs continuous scans of the same region;
  trace-vs-retrace correlation to separate real morphology from time noise.
- **Watch the safety rails.** Never approach toward the sample without an
  operator's OK; graceful-quit the app (don't force-kill — it can wedge the
  serial port); confirm the preamp gain and bias before trusting current.
- **Let it use the research harness** (`docs/ai/research-harness/`) to model
  what it's seeing — e.g. "at what line rate does preamp bandwidth start
  smearing a 3 nm feature?" — then design the bench test from the model.

---

## Physics research harness

`docs/ai/research-harness/` holds first-principles models (scan bandwidth,
thermal drift, wedge/piezo mechanics) with queries and rendered reports
under `output/`. Useful for turning "the image looks wrong" into a
quantitative prediction and a targeted experiment.
