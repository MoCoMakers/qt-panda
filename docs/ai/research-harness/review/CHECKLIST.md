# Graphics review checklist

The harness writes `output/review_manifest.json` after every run. An agent
(Claude Code, via its image-reading ability) opens each figure listed there
and scores it against the three criteria below. Anything that fails becomes a
concrete edit to `rendering/figures.py` or `rendering/style.py`, then the
harness is re-run and the figure re-reviewed. Repeat until clean.

## 1. Professionalism
- [ ] No overlapping/colliding text (titles, legends, annotations, captions).
- [ ] Nothing clipped at the figure edges; captions fully visible.
- [ ] Consistent house style (fonts, palette, grid) across all figures.
- [ ] Colour-blind-safe palette; colours map to consistent semantic roles.
- [ ] Legends present where >1 series; placed off the data.

## 2. Scientific accuracy
- [ ] Axis labels include units; magnitudes match the computed table.
- [ ] Any not-to-scale / exaggerated drawing is explicitly labelled as such.
- [ ] Equations shown match the equations actually computed.
- [ ] Log/linear scale choice is appropriate and labelled.
- [ ] Annotated numeric values agree with `output/review_manifest.json` /
      the printed results table (no stale or rounded-wrong figures).

## 3. Presentation / communication
- [ ] Each figure makes one clear point stated in its title.
- [ ] The headline comparison (1 mm vs 10 mm) is immediately readable.
- [ ] Callouts guide the eye to the key result, not clutter.
- [ ] Figure ordering tells a story: geometry → components → scaling laws.

## How to run a review pass
1. `python harness.py` (or with `--ask "..."`).
2. Read `output/review_manifest.json`.
3. Open each `figures/*.png` and grade against the lists above.
4. Record findings in `review/REVIEW_LOG.md`.
5. Fix code, re-run, re-review the changed figures only.
