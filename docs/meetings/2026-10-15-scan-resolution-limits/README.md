# Scan Resolution Limits (Oct 15, 2026 review) — reference copy

**Status:** historical reference. Its priorities were updated by later work, so do not plan from its ordering. Current priorities: [`../../test-plans/roadmap.html`](../../test-plans/roadmap.html) and section 6.1 of [`../../test-plans/2026-10-23-open-issues-and-tests.md`](../../test-plans/2026-10-23-open-issues-and-tests.md). Each of its action items 1–22 is tracked, with status after Oct 22, in section 4.1 of that file.

- **Original artifact:** https://claude.ai/artifact/KoVCVxhj7SdRCzrWGBnYcn (in another organisation; exported by the operator on 2026-10-23).
- **Open locally:** `index.html` (self-contained page; figures in `report/`).
- **Data analysed:** Sep 24 gold run, 1,125 full sweeps, including a zoom ladder from 30 nm.

## What still applies

1. **Three limits on resolution:**
   - **Sampling:** pixels per atom spacing. About **5–6 px per atom** are needed before atoms render evenly. Between 2 (the Nyquist minimum) and ~5, "sampling-phase scatter" makes atoms unevenly bright.
   - **Speed:** atoms passing the tip per second (2 × scan size × line rate ÷ atom spacing), against the signal chain's bandwidth.
   - **Slant.**
2. The sampling and speed rules are now an audit item for every scan path (`../../test-plans/scan-path-design.md`, §9 item 4).

## What has moved on since

1. The 159.5 vs 231 Hz question is settled at **158.7 Hz** (Oct 22 halted holds).
2. The KIGA sweep ran on Oct 22: 4.6 was the last stable gain.
3. The fold, repeat and zoom checks were extended by drift registration (report v2) and by the scan-path simulator.
