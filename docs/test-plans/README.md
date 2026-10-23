# Test plans (living documents)

Plans for upcoming bench sessions and the open technical issues behind them. These files are
edited as results come in: each test records its outcome, date and data folder in place, and
each open issue keeps a running status. Nothing here is executed without the operator.

**Start here:** [roadmap.html](roadmap.html), the shareable overview: goals, milestones, every item scored (lead × ease × impact), session order, safety rules. Source: `build_roadmap.py` (edit the lists, run it to rebuild).

| File | What it covers |
|---|---|
| [2026-10-23-open-issues-and-tests.md](2026-10-23-open-issues-and-tests.md) | Safety rules, the proposed GUI control process, open issues after the Oct 22 KIGA sweep, test sequences T1–T9, and offline investigations |
| [phantom-offset-handoff.md](phantom-offset-handoff.md) | Standalone handoff on the scan-time ADC offset: firmware pseudo-code, ADC data points, hypotheses, design questions |
| [../stm-techniques-backlog.md](../stm-techniques-backlog.md) | Standard STM techniques to be aware of (drift, feedback, imaging, calibration, tip, scanning), with our status for each |

Conventions:

- **Status** values: `open`, `investigating`, `planned`, `done`, `dropped`.
- **Sweep halves:** up sweep (▲) = first half of each Y-cycle, down sweep (▼) = second half, as in the replay viewer. **Scan directions:** trace = left → right, retrace = right → left.
- Every test names its safety checks first and its pass/fail measurement last.
- Results link to the day folder (`TeamUpdate/data/<day>/`) and the report that analyses them.
