#!/usr/bin/env sh
# run_offline.sh — one-command offline validation (Docker, no hardware).
# Runs the full test suite, the regression harness, and the capture demos.
# Docker Desktop needs Windows host paths; override REPO if yours differs.
set -e
REPO="${REPO:-C:/Users/enact/Projects/qt-panda}"
QT="$REPO/dans-software-port/pc/qtpanda"
EMU="$REPO/docs/ai/research-harness/software-mockup/emulator"
DATA="$REPO/TeamUpdate/data"
OUT="$REPO/documentation/docs-for-ai/StabilityResearch"
GUI=qtpanda-gui:latest
PC=software-mockup-pc:latest

echo "== 1. full pytest suite (+ real bench fixtures) =="
docker run --rm -v "$QT:/work" -v "$DATA:/data:ro" -w /work \
  -e QT_QPA_PLATFORM=offscreen -e QTPANDA_STAB_DATA=/data \
  --entrypoint sh "$GUI" -c "pip install -q pytest 2>/dev/null; python -m pytest tests/ -q"

echo "== 2. regression harness (synthetic + real verdicts) =="
docker run --rm -v "$QT:/work" -v "$DATA:/data:ro" -w /work \
  -e QTPANDA_STAB_DATA=/data --entrypoint python "$PC" stab_fixtures.py

echo "== 3. capture demos (analysis PNGs + guarded procedure) =="
for d in "copilot_demo.py --seconds 6 --out /out/harness-screens/ci_run" \
         "approach_hit_demo.py --out /out/harness-screens/ci_hit" \
         "procedure_runner.py --out /out/harness-screens/ci_proc"; do
  docker run --rm -v "$QT:/work" -v "$EMU:/emu:ro" -v "$OUT:/out" -w /work \
    -e QT_QPA_PLATFORM=offscreen --entrypoint python "$GUI" $d
done
echo "== offline validation complete =="
