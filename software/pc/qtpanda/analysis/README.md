# Analysis tools

| File | What it is |
|---|---|
| `fiducial_drift.py` | **General drift tool.** Measures lateral drift between sweeps by fiducial hopping (grid templates, error + Z channels must agree, skip-one pairs, robust fit of drift + up/down-sweep offset + restart jumps). `python fiducial_drift.py <day> <first_sweep> <last_sweep> [--out DIR]` → JSON + PNG with an example reference chain. Validated on 2026-Oct-22 #20–#31 and 2026-Sep-24 #1586–#1599. Uses the error channel and trace+retrace Z (see test plan OI-7: trace-only Z still to do). |
| `sim/` | Simulations (feedback loop, stage tracking). See `sim/README.md`. |
| `oct22/` | **Archive of the 2026-10-22/23 session scripts** that produced the Oct 22 report (drift proof, drift model, KIGA re-analysis, blob case study, contour stack, 3D mound, live-trail simulation, report and artifact builders, KIGA-sweep automation with guards, GUI mockup). They are kept for provenance and reuse; most hard-code paths (session scratchpad, `2026-Oct-22`) and chain into each other with `exec`, so adapt before reusing. Outputs live in `TeamUpdate/data/2026-Oct-22/` (gitignored) and the published report (see that folder's `report/README.md`). |

Run with the GUI's Python (`C:\Program Files\Python311\python.exe`, which has numpy/scipy/matplotlib/PySide6).
