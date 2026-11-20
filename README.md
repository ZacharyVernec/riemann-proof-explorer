# Understanding the Riemann Proof

This repository exists to help humans understand the Lean 4 proof of the Riemann Hypothesis based on Alpoge's work, announced in [alpo.ge/remark.pdf](https://alpo.ge/remark.pdf).

> **Note:** This repository itself is AI-generated. Its goal is human comprehension—mapping out proof structure, dependencies, interfaces, and mathematical architecture—rather than re-verifying or auditing the formal Lean proof.

## Lean Proof

The Lean proof is included in this repository both as the extracted source tree in `lean/` and as an archive in Git LFS (`lean.tar.gz`).

## Main Contributions

All contributions are located in the `analysis/` folder:

- [Inventory of `PublishedTheorems`](analysis/published_theorems/PUBLISHED_THEOREMS_INVENTORY.md) — Complete audit of all six `PublishedTheorems` directories (1,070 Lean files), comparing formalized statements against the peer-reviewed literature and cataloging untraceable scaffolding, helpers, and misnomers.
- [Canonical Import-Graph Index](analysis/build_index.py) — Python 3.11 stdlib indexer generating `analysis/data/graph.sqlite` and [meta.json](analysis/data/meta.json) across all 175,187 Lean files (17.37M lines, 753,261 internal edges, 1.06M declarations).
- [Directory-Level Dependency Graph](analysis/dependency_graph/README.md) ([interactive explorer](analysis/dependency_graph/dependency_explorer.html), [top-level SVG](analysis/dependency_graph/top_level_graph.svg), [depth-2 SVG](analysis/dependency_graph/depth2_major_graph.svg)) — Aggregates 753,261 file-level imports across Depth 1–3 directories with upstream/downstream tracing and SCC analysis.
- [Cross-Boundary Interface Extraction](analysis/interfaces/INTERFACES_REPORT.md) ([interactive browser](analysis/interfaces/interface_browser.html)) — Isolates the 5.29% of files imported across top-level directory boundaries, with compression ratios and plain-English public API translations for 59 key interface files.
- [Proof Spine & Dominator Analysis](analysis/proof_spine/PROOF_SPINE_REPORT.md) ([interactive dashboard](analysis/proof_spine/spine_dashboard.html)) — Cooper-Harvey-Kennedy dominator tree rooted at `Main.lean`, exact 202-edge critical path, stratigraphic height layers, and hub/bridge rankings.

## Contributing

Pull requests from **both humans and AI agents** are welcome!

Contributions based on **computationally expensive** or **token-expensive** results (e.g., full dependency graphs, module-level summaries, cross-referenced expositions, or deep structural analyses) are especially appreciated.
