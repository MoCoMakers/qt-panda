# Test plans (living documents)

Plans for upcoming bench sessions and the open technical issues behind them. These files are
edited as results come in: each test records its outcome, date and data folder in place, and
each open issue keeps a running status. Nothing here is executed without the operator.

**Start here:** [roadmap.html](roadmap.html), the shareable overview: goals, milestones, every item scored (lead × ease × impact), session order, safety rules. Source: `build_roadmap.py` (edit the lists, run it to rebuild).

| File | What it covers |
|---|---|
| [2026-10-23-open-issues-and-tests.md](2026-10-23-open-issues-and-tests.md) | Safety rules, the proposed GUI control process, open issues after the Oct 22 KIGA sweep, test sequences T1–T9, and offline investigations |
| [../DECISIONS.md](../DECISIONS.md) | **Decision log and assumptions register**: what was decided, by whom, why, on which assumptions; read before auditing or changing code |
| [data-pipeline-v2-design.md](data-pipeline-v2-design.md) | Frame format v2, one shared reconstruction ("Run" mode for live view and replay), mode-first settings panel |
| [../SIMULATION.md](../SIMULATION.md) | Scan simulator: chain, reconstruction rules, verification ladder, back-test, path comparison, how to run |
| [../PHYSICS_MODELS.md](../PHYSICS_MODELS.md) | Registry of every physics model with value, status (measured/assumed/hypothesis) and how to improve it; hysteresis section; common STM practice |
| [scan-path-design.md](scan-path-design.md) | Experimental scan paths (rotated, cross-hatch, spirals, centre-return, rose): principles, reconstruction contract, timing audit, physics model, simulation plan |
| [RESUME.md](RESUME.md) | Where multi-session build work stands; read first when resuming |
| [phantom-offset-handoff.md](phantom-offset-handoff.md) | Standalone handoff on the scan-time ADC offset: firmware pseudo-code, ADC data points, hypotheses, design questions |
| [../stm-techniques-backlog.md](../stm-techniques-backlog.md) | Standard STM techniques to be aware of (drift, feedback, imaging, calibration, tip, scanning), with our status for each |

Conventions:

- **Status** values: `open`, `investigating`, `planned`, `done`, `dropped`.
- **Sweep halves:** up sweep (▲) = first half of each Y-cycle, down sweep (▼) = second half, as in the replay viewer. **Scan directions:** trace = left → right, retrace = right → left.
- Every test names its safety checks first and its pass/fail measurement last.
- Results link to the day folder (`TeamUpdate/data/<day>/`) and the report that analyses them.

Shared reports for Oct 22: v2 (current, peaks bright, drift removed line by line) https://claude.ai/artifact/LqRJEE9pjqCwkczBi2iM6p; v1 (reference, unchanged) https://claude.ai/artifact/9aZPBvpbLL48iMj1j89Rxy. Section 6 of the open-issues file holds the 2026-10-23 learnings and current priorities.
