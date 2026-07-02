#!/usr/bin/env bash
# Bridge a virtual serial port to the Arduino emulator's TCP socket, then run
# either the headless driver (default) or the full Qt GUI (GUI=1).
set -euo pipefail

ARDUINO_HOST="${ARDUINO_HOST:-arduino}"
ARDUINO_PORT="${ARDUINO_PORT:-9000}"
PTY_LINK="${STM_SERIAL_PORT:-/tmp/stm_pty}"

echo "[pc] bridging serial ${PTY_LINK} <-> tcp:${ARDUINO_HOST}:${ARDUINO_PORT}"
# socat creates the PTY immediately and retries the TCP connect until the
# emulator is accepting connections. The unmodified PC code then opens the PTY
# exactly like a real COM port.
socat pty,raw,echo=0,link="${PTY_LINK}" \
      "TCP:${ARDUINO_HOST}:${ARDUINO_PORT},retry=60,interval=1,forever" &

# Wait for the PTY link to show up.
for _ in $(seq 1 60); do
    [ -e "${PTY_LINK}" ] && break
    sleep 0.5
done

export PYTHONPATH="/app/qtpanda:${PYTHONPATH:-}"

if [ "${GUI:-0}" = "1" ]; then
    echo "[pc] launching GUI — type '${PTY_LINK}' in the COM field, then Open."
    export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
    cd /app/qtpanda
    exec python widget.py
else
    echo "[pc] running headless driver"
    exec python /app/mockup_driver.py
fi
