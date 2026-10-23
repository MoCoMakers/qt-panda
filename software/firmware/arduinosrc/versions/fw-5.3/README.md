# FW 5.3 — reconstructed reference build

Reconstructed 2026-07-31 for a regression A/B: the pre-session firmware
(git 429b9a1, prints "FW 5.2") plus ONLY the FW 5.3 line-rescan delta
(LRPT command, per-row pass averaging, droppedLineFrames counter,
dy/lineRepeat step change).  None of the later changes are present:
no DIAG/ISR self-timing (5.4), no GSPC abort / 16-block raw ring /
SETD-5 floor (5.5), no exact or rational stepping (5.5.1/5.6) — this
build has the original floored dx and the LIMIT-1 bounce.

Verification: compiled memory footprint is byte-identical to the
original 5.3 build flashed at 01:14 that night (FLASH code:58548,
RAM1 variables:250304).

Era notes for faithful behavior: run the ISR at 40 µs (SETD 40 /
calibration control_rate_hz=25000) and Ki 4.5776.

Flash:
    arduino-cli compile --fqbn teensy:avr:teensy41 \
      --libraries %LOCALAPPDATA%\Arduino15\libraries \
      --upload -p <teensy port> versions/fw-5.3/main
