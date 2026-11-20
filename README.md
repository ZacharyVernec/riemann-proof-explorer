# Understanding the Riemann Proof

This repository exists to help humans understand the Lean 4 proof of the Riemann Hypothesis based on Alpoge's work, announced in [alpo.ge/remark.pdf](https://alpo.ge/remark.pdf).

> **Note:** This repository itself is AI-generated. Its goal is human comprehension—mapping out proof structure, dependencies, interfaces, and mathematical architecture—rather than re-verifying or auditing the formal Lean proof.

## Lean Proof

The Lean proof is included in this repository both as the extracted source tree in `lean/` and as an archive in Git LFS (`lean.tar.gz`).

## Main Contributions

All contributions are located in the `analysis/` folder:

- [Inventory of `PublishedTheorems`](analysis/published_theorems/PUBLISHED_THEOREMS_INVENTORY.md) ([HTML version](analysis/published_theorems/PUBLISHED_THEOREMS_INVENTORY.html)) — Complete audit of all six `PublishedTheorems` directories (1,070 Lean files), comparing formalized statements against the peer-reviewed literature and cataloging untraceable scaffolding, helpers, and misnomers.
- [Canonical Import-Graph Index](analysis/build_index.py) — Python 3.11 stdlib indexer generating `analysis/data/graph.sqlite` and [meta.json](analysis/data/meta.json) across all 175,187 Lean files (17.37M lines, 753,261 internal edges, 1.06M declarations).
- [Directory-Level Dependency Graph](analysis/dependency_graph/README.md) ([HTML report](analysis/dependency_graph/README.html), [interactive explorer](analysis/dependency_graph/dependency_explorer.html), [top-level SVG](analysis/dependency_graph/top_level_graph.svg), [depth-2 SVG](analysis/dependency_graph/depth2_major_graph.svg)) — Aggregates 753,261 file-level imports across Depth 1–3 directories with upstream/downstream tracing and SCC analysis.
- [Cross-Boundary Interface Extraction](analysis/interfaces/INTERFACES_REPORT.md) ([HTML report](analysis/interfaces/INTERFACES_REPORT.html), [interactive browser](analysis/interfaces/interface_browser.html)) — Isolates the 5.29% of files imported across top-level directory boundaries, with compression ratios and plain-English public API translations for 59 key interface files.
- [Proof Spine & Dominator Analysis](analysis/proof_spine/PROOF_SPINE_REPORT.md) ([HTML report](analysis/proof_spine/PROOF_SPINE_REPORT.html), [interactive dashboard](analysis/proof_spine/spine_dashboard.html)) — Cooper-Harvey-Kennedy dominator tree rooted at `Main.lean`, exact 202-edge critical path, stratigraphic height layers, and hub/bridge rankings.
- [Size Treemap & Sunburst](analysis/size_treemap/SIZE_ANALYSIS.md) ([HTML report](analysis/size_treemap/SIZE_ANALYSIS.html), [interactive visualizer](analysis/size_treemap/treemap_sunburst.html)) — Zoomable squarified treemap and radial sunburst across all 3,615 nested directory nodes by files, lines, theorems, and definitions.
- [Top-Down Mathematical Blueprint](analysis/blueprint/BLUEPRINT.md) ([HTML report](analysis/blueprint/BLUEPRINT.html), [interactive blueprint](analysis/blueprint/blueprint.html)) — Plain-English mathematical roadmap of 45 verified milestones across Stages 0–4 from `Main.lean` down through the major theory pillars, plus static assumptions audit.
- [Unified Analysis Portal](analysis/index.html) — Self-contained local HTML hub linking all interactive visualizers, static SVGs, and HTML reports.

## Portal & Interactive Suite

Start at the unified landing page:

- **Portal:** [analysis/index.html](analysis/index.html)

To browse all 6 self-contained HTML pages cleanly in a browser (zero external CDN dependencies):

```bash
python3 -m http.server 8000 --directory analysis
```

## Contributing

Pull requests from **both humans and AI agents** are welcome!

Contributions based on **computationally expensive** or **token-expensive** results (e.g., full dependency graphs, module-level summaries, cross-referenced expositions, or deep structural analyses) are especially appreciated.
