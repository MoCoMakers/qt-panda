# Research harness

Ask a physics question → get it grounded in closed-form equations, computed
with NumPy, drawn with Matplotlib (plus ASCII schematics), and synthesized
into a single self-contained **`output/report.html`** you can reload any time.

Shipped questions:

1. *"Show me the tip displacement for a centrally located tip on a piezo if its
   length is 1 mm vs 10 mm, for a 2 degree offset."* (`tip-displacement-length`)
2. *"What is the expected Brownian/thermal displacement from center for a gold
   atom at room temperature — what is average?"* (`thermal-displacement-gold`,
   grounded in gold's density)

## Software mockup (Docker) — run the real PC code vs. an emulated Arduino

`software-mockup/` is a `docker compose up` environment that runs the actual
`pc/qtpanda` software against a **software-emulated STM controller** (faithful
firmware serial protocol + a tunneling-current signal model with configurable
noise / drift / in-out-of-zone behavior). No hardware needed. It validates the
Stability tab, raw-CSV logging, and the drift/jitter math end to end. See
[`software-mockup/README.md`](software-mockup/README.md).

## Quick start

```bash
cd docs/ai/research-harness
pip install -r requirements.txt          # numpy + matplotlib

python harness.py                        # run the default (tip) query
python harness.py --query thermal-displacement-gold
python harness.py --ask "brownian displacement of a gold atom at room temperature"
python harness.py --ask "tip displacement, 1mm vs 10mm tip, 2 degree offset"
python harness.py --theta 2 --lengths 1 10
python harness.py --temperature 4        # gold atom at 4 K, etc.
python harness.py --list                 # list registered queries
```

Open **`output/index.html`** for the landing page that links every report, or
go straight to a report at `output/<slug>/report.html`. Each report is fully
self-contained (figures embedded as base64, no network needed) — reload it
after any run to see the latest result.

## What you get (`output/`)
```
output/
├── index.html                       # links to all reports
├── tip-displacement-length/
│   ├── report.html                  # self-contained, reloadable
│   ├── figures/*.png
│   └── review_manifest.json         # figure list for the agent-review loop
└── thermal-displacement-gold/
    ├── report.html
    ├── figures/*.png
    └── review_manifest.json
```

## How it's structured

```
research-harness/
├── harness.py            # CLI orchestrator: question → physics → figures → report
├── models.py             # Investigation dataclass passed between layers
├── physics/
│   ├── piezo_tip.py         # closed-form Abbe/cosine-error geometry
│   └── thermal_vibration.py # Debye–Waller thermal displacement (density-grounded)
├── rendering/
│   ├── style.py             # one house style for every figure
│   ├── figures.py           # tip-displacement figures
│   ├── figures_thermal.py   # thermal-vibration figures
│   ├── ascii_art.py         # text schematics + results tables
│   └── report.py            # assembles the self-contained report.html
├── queries/
│   ├── tip_displacement_length.py     # piezo tip-tilt question
│   └── thermal_displacement_gold.py   # gold thermal-jitter question
├── review/
│   ├── CHECKLIST.md      # the three review criteria
│   └── REVIEW_LOG.md     # audit trail of agent graphics reviews
└── output/               # generated artifacts (report, figures, manifest)
```

## The science (grounded, not guessed)

A rigid tip of standoff length `L` whose mount is tilted by an angle `θ` sweeps
its apex through an arc — the classic **Abbe / cosine error**:

```
Δx = L · sin θ              lateral apex displacement (dominant)
Δz = L · (1 − cos θ)        vertical foreshortening
Δr = 2L · sin(θ/2)          total apex displacement
small angle:  Δx ≈ Lθ,  Δz ≈ Lθ²/2
```

For θ = 2°: a 1 mm tip moves **34.9 µm** laterally, a 10 mm tip **349 µm** — a
10× difference that exactly tracks the length ratio, because Δx is linear in L.

### Gold thermal displacement (`thermal-displacement-gold`)

A gold atom bound at its lattice site jitters thermally about that site. The
**density** sets the lattice scale, and the Debye model sets the amplitude:

```
n  = ρ·N_A / M     →  a = (4/n)^⅓,  d_nn = a/√2   (density → 288 pm spacing)
⟨u²⟩ = (9ħ²T / m·k_B·Θ_D²)·[Φ(Θ_D/T) + Θ_D/4T]     (Debye, with zero-point)
σ = √(⟨u²⟩/3),  ⟨|u|⟩ = √(8/π)·σ,  rms = √3·σ
```

At 293 K the **average** displacement is **⟨|u|⟩ ≈ 14 pm** (3-D RMS 15.5 pm,
σ ≈ 9 pm/axis) — only **5.4%** of the 288 pm spacing. Cross-checks: classical
and quantum agree to <0.5% (room T ≫ Θ_D = 165 K); a 5.8 pm zero-point floor
remains at 0 K; and the Lindemann ratio hits 11% right at gold's melting point.

## Adding a new question
1. Create `queries/<your_query>.py` exposing `SLUG` and
   `run(out_dir, **kwargs) -> Investigation`.
2. Add physics to `physics/` as pure, documented functions.
3. Add figures to `rendering/figures.py` (return the path; append to the manifest).
4. Register it in `queries/__init__.py`.

## Checking the graphics (agent-review loop)

The harness intentionally does **not** trust its own plots. After each run it
emits `output/review_manifest.json`; an agent (Claude Code) opens every figure
and grades it against `review/CHECKLIST.md` for **professionalism, scientific
accuracy, and presentation**, logs findings in `review/REVIEW_LOG.md`, fixes
`rendering/figures.py`, and re-runs until clean. See `review/` for the protocol
and the audit trail from the first build.
```bash
# kick off a review pass yourself:
python harness.py
#   → then ask Claude: "review the figures in output/ against review/CHECKLIST.md"
```
