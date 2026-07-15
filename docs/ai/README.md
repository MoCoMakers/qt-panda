# docs/ai

AI-assisted tooling and artifacts for the qt-panda project.

| folder | what it is |
|---|---|
| [`research-harness/`](research-harness/) | Ask a physics question → get it grounded in closed-form equations, computed with Python, plotted with Matplotlib, and synthesized into a reloadable static report. Open `research-harness/output/index.html` for all reports. Includes an agent-driven graphics-review loop (professionalism, scientific accuracy, presentation). |

### Reports currently in the harness
- **Piezo tip displacement** vs tip length at a 2° offset (Abbe/cosine error).
- **Gold atom thermal (Brownian) displacement** at room temperature, grounded
  in gold's density (Debye–Waller; average ≈ 14 pm).

## Conventions
- Each tool is self-describing: a `README.md`, a runnable entry point, and a
  `requirements.txt` if it has dependencies.
- Generated artifacts live under the tool's own `output/` directory and are
  safe to delete and regenerate.
