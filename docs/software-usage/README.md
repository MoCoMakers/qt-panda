# Software usage docs

How to use the qt-panda software as an operator: what the controls do, what the data means, and how to read it. Started 2026-10-16; add a page whenever a question needed a long discussion to answer.

| Page | Covers |
|---|---|
| [01 · Scan data streams](01-scan-data-streams.md) | The four data streams every scan records (trace and retrace, scan up and scan down), what each tool shows, and the recommended names |
| [TODO](TODO.md) | Software and firmware to-dos: trace/retrace comparison, surface checks in replay, line-rate helper, line-rate rounding bug, DIAG X extent, USB line transmission |

Related, older guides (to be folded in over time):
- `software/pc/USER_GUIDE.md`: the GUI, panel by panel.
- [`../replay-usability-guide.md`](../replay-usability-guide.md): the sweep player.
- [`../SYSTEM_LAUNCH_GUIDE.md`](../SYSTEM_LAUNCH_GUIDE.md): power-up and launch.
- [`../HARDWARE_NOTES.md`](../HARDWARE_NOTES.md): the instrument itself.

Proposed next pages:
- Scan settings and what they cost: scan size, pixels per line, line rate (requested vs realized), line re-scan, KIGA.
- Reading an image: Z vs error channel, levelling, colour scales, and the checks for "is this surface?"
- Zooming and offsets: centred zoom, offset moves, creep after a move.
