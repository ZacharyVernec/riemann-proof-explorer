# Understanding the Riemann Proof

This repository exists to help humans understand the mathematical structure of the proof of the Riemann Hypothesis based on Alpoge's work, announced in [alpo.ge/remark.pdf](https://alpo.ge/remark.pdf).

> **Note:** This repository itself is AI-generated. Its goal is human mathematical comprehension—mapping out the proof architecture, logical dependencies, cross-theory mathematical interfaces, and key theorem milestones—rather than re-verifying or auditing the formal Lean code.

## Lean Proof

The Lean proof is included in this repository both as the extracted source tree in `lean/` and as an archive in Git LFS (`lean.tar.gz`).

## Main Contributions

All contributions are located in the `analysis/` folder:

- [Top-Down Mathematical Blueprint](analysis/blueprint/BLUEPRINT.md) ([HTML report](analysis/blueprint/BLUEPRINT.html), [interactive blueprint](analysis/blueprint/blueprint.html)) — Plain-English mathematical roadmap of 45 milestones across Stages 0–4 from the final RH/GRH statements down through the major theory pillars and foundational machinery.
- [Cross-Boundary Mathematical Interfaces](analysis/interfaces/INTERFACES_REPORT.md) ([HTML report](analysis/interfaces/INTERFACES_REPORT.html), [interactive browser](analysis/interfaces/interface_browser.html)) — Plain-English translations of the public mathematical contracts and key theorem/specification interfaces linking the major theories of the proof.
- [Proof Spine & Bottleneck Analysis](analysis/proof_spine/PROOF_SPINE_REPORT.md) ([HTML report](analysis/proof_spine/PROOF_SPINE_REPORT.html), [interactive dashboard](analysis/proof_spine/spine_dashboard.html)) — Dominator tree of mandatory mathematical bottlenecks, the critical dependency chain from the main theorems down to split tori, and cross-theory bridge theorems.
- [Theory-Level Dependency Graph](analysis/dependency_graph/README.md) ([HTML report](analysis/dependency_graph/README.html), [interactive explorer](analysis/dependency_graph/dependency_explorer.html), [top-level SVG](analysis/dependency_graph/top_level_graph.svg), [depth-2 SVG](analysis/dependency_graph/depth2_major_graph.svg)) — Maps the logical and topical dependencies across the top-level and sub-theory mathematical domains.
- [Inventory of `PublishedTheorems`](analysis/published_theorems/PUBLISHED_THEOREMS_INVENTORY.md) ([HTML version](analysis/published_theorems/PUBLISHED_THEOREMS_INVENTORY.html)) — Audit of all six `PublishedTheorems` directories, comparing formalized mathematical statements against the peer-reviewed literature and cataloging custom hypotheses, specializations, and internal proof scaffolding.
- [Full Lean Module DAG](analysis/full_dag/FULL_DAG.md) ([HTML report](analysis/full_dag/FULL_DAG.html), [interactive viewer](analysis/full_dag/full_dag.html)) — Minimal pan-and-zoom WebGL visualization of the entire Lean module import DAG and its deterministic, refactor-resilient layout pipeline.
- [Unified Analysis Portal](analysis/index.html) — Self-contained local HTML hub linking all interactive explorers, static dependency diagrams, and HTML reports.

## Portal & Interactive Suite

Start at the unified landing page:

- **Portal:** [analysis/index.html](analysis/index.html)

To browse all self-contained HTML pages cleanly in a browser (zero external CDN dependencies):

```bash
python3 -m http.server 8000 --directory analysis
```

## Contributing

Pull requests from **both humans and AI agents** are welcome!

Contributions based on **computationally expensive** or **token-expensive** results (e.g., full dependency graphs, module-level summaries, cross-referenced mathematical expositions, or deep structural analyses) are especially appreciated.
