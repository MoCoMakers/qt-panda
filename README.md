# QTPanda — Homebuilt STM Control Software

Control software and firmware for a scanning tunneling microscope (STM), in
the tradition of home-built STMs like
[Dan Berard's](http://dberard.com/home-built-stm/) and MechPanda's
[Red Panda STM](https://github.com/MechRedPanda/red-panda-stm)
([build video](https://www.youtube.com/watch?v=7N3OqTEq08g)). A **Teensy 4.1**
runs the real-time control loop; a **PySide6** desktop app drives it, images
the surface, and records everything for faithful replay.

## Getting Started

Install the Python dependencies:

```bash
pip install -r software/pc/requirements.txt
```

Run the app:

```bash
cd software/pc/qtpanda
python main.py                              # GUI only
python main.py --port COM5                  # connect to the instrument
python main.py --port COM5 --copilot 8765   # + let an LLM drive it (see below)
```

## Using the Software

Once connected (press **Open**, or launch with `--port`), a full-session
recording starts automatically — everything is saved verbatim and can be
replayed offline.

- **Scan** (Scanning tab) — a slow, settled single image; good for a first look.
- **Continuous Scan** tab — set the size in nanometres and press **RUN** for
  live imaging; use **Auto Levels** to see contrast.
- **Starting defaults worth considering**: a small bias (e.g. −0.2 V); the
  **preamp gain** (1X / 5X) set to match your hardware; and on the Z slider,
  remember **down = toward the sample** — approach gently.

## Control it with an LLM

Launch with `--copilot 8765` and an LLM like **Claude** can control every
aspect of the instrument and read every value — it drives the real on-screen
controls, so its actions appear in the GUI and are logged. Just ask in plain
language:

- *"Run a 30 nm continuous scan."*
- *"What does the journal say happened in the last 2 minutes?"*
- *"Set the bias to −0.2 V and retract 5 steps."*

*(The underlying HTTP API for scripting is documented separately in `software/pc/CHANGELOG.md` and the code.)*

## Firmware

The firmware is an Arduino sketch: open
`software/firmware/arduinosrc/main/main.ino` in the Arduino IDE and flash it
to the Teensy 4.1 (board: `teensy:avr:teensy41`).

## Testing without hardware

`python main.py --port EMU` runs the whole app against a software firmware
emulator (`software/pc/qtpanda/emulator/`) — handy for development with no
bench attached.

## More

- **Hard-won learnings & non-obvious fixes:** `software/pc/CHANGELOG.md`.
- **Physics modeling harness** (drift, scan bandwidth, mechanics):
  `docs/ai/research-harness/` — see its own README.
