# Understanding the Riemann Proof

This repository exists to help humans understand the mathematical structure of the proof of the Riemann Hypothesis based on Alpöge's work, announced in [alpo.ge/remark.pdf](https://alpo.ge/remark.pdf).

> **Note:** This repository itself is AI-generated. Its goal is human mathematical comprehension—mapping out the proof architecture, logical dependencies, cross-theory mathematical interfaces, and key theorem milestones—rather than re-verifying or auditing the formal Lean code.

## Lean Codebase Versions

Every page of the [Analysis Portal](analysis/index.html) includes a **Lean repo version** switcher (defaulting to the latest community version and remembering your selection across pages):

- **Community simplified (default — `community-307cef33`):** [`leanprover-community/riemann-hypothesis`](https://github.com/leanprover-community/riemann-hypothesis) at commit `307cef33f046955ee79dba47e0d828d06496d75f`, fetched into `lean_versions/community-307cef33/` (gitignored; downloaded automatically by the orchestrator if absent).
- **Original submission (`original-2026-11-20`):** The original extracted source tree in `lean/` (and Git LFS archive `lean.tar.gz`).

## Main Contributions

All contributions are located in the `analysis/` folder (with per-version datasets under `analysis/versions/<id>/` and canonical top-level views synced to the default version):

- [Top-Down Mathematical Blueprint](analysis/blueprint/BLUEPRINT.md) ([HTML report](analysis/blueprint/BLUEPRINT.html), [interactive blueprint](analysis/blueprint/blueprint.html)) — Plain-English mathematical roadmap across Stages 0–4 from the final RH/GRH statements down through the major theory pillars and foundational machinery.
- [Cross-Boundary Mathematical Interfaces](analysis/interfaces/INTERFACES_REPORT.md) ([HTML report](analysis/interfaces/INTERFACES_REPORT.html), [interactive browser](analysis/interfaces/interface_browser.html)) — Plain-English translations of the public mathematical contracts and key theorem/specification interfaces linking the major theories of the proof.
- [Proof Spine & Bottleneck Analysis](analysis/proof_spine/PROOF_SPINE_REPORT.md) ([HTML report](analysis/proof_spine/PROOF_SPINE_REPORT.html), [interactive dashboard](analysis/proof_spine/spine_dashboard.html)) — Dominator tree of mandatory mathematical bottlenecks, the critical dependency chain from the main theorems down to foundational leaves, and cross-theory bridge theorems.
- [Theory-Level Dependency Graph](analysis/dependency_graph/README.md) ([HTML report](analysis/dependency_graph/README.html), [interactive explorer](analysis/dependency_graph/dependency_explorer.html), [top-level SVG](analysis/dependency_graph/top_level_graph.svg), [depth-2 SVG](analysis/dependency_graph/depth2_major_graph.svg)) — Maps the logical and topical dependencies across the top-level and sub-theory mathematical domains.
- [Inventory of `PublishedTheorems`](analysis/published_theorems/PUBLISHED_THEOREMS_INVENTORY.md) ([HTML version](analysis/published_theorems/PUBLISHED_THEOREMS_INVENTORY.html)) — Audit of active `PublishedTheorems` directories and companion background theory, comparing formalized mathematical statements against the peer-reviewed literature and cataloging custom hypotheses, specializations, and internal proof scaffolding.
- [Full Lean Module DAG](analysis/full_dag/FULL_DAG.md) ([HTML report](analysis/full_dag/FULL_DAG.html), [interactive viewer](analysis/full_dag/full_dag.html)) — Minimal pan-and-zoom WebGL visualization of the entire Lean module import DAG and its deterministic, refactor-resilient layout pipeline.
- [Codebase Structural Histograms](analysis/codebase_histograms/CODEBASE_HISTOGRAMS.md) ([HTML report](analysis/codebase_histograms/CODEBASE_HISTOGRAMS.html), [interactive histograms](analysis/codebase_histograms/histograms.html)) — Empirical distributions of `@[…]` attributes, proof glue, typeclass tiers, conceptual proof strategies, equivalence bridges, non-`@[simp]` import fan-in, and file-order structure across the Lean codebase.
- [Unified Analysis Portal](analysis/index.html) — Self-contained local HTML hub linking all interactive explorers, static dependency diagrams, and HTML reports, plus the [Treemap & Sunburst explorer](analysis/size_treemap/treemap_sunburst.html) ([report](analysis/size_treemap/SIZE_ANALYSIS.md)).

## Portal & Interactive Suite

Browse the live site directly on GitHub Pages:

- **Live Portal:** [https://zacharyvernec.github.io/riemann-proof-explorer/](https://zacharyvernec.github.io/riemann-proof-explorer/)
- **Local Portal:** [analysis/index.html](analysis/index.html)

To browse all self-contained HTML pages cleanly in a browser (zero external CDN dependencies for local data):

```bash
python3 -m http.server 8000 --directory analysis
```

## Reproducing or Adding a Lean Version

Versions are registered in [`analysis/versions.json`](analysis/versions.json). To add and analyze a new version without re-running older versions:

```bash
# Run only the specified version (fetches source if needed) and sync portal metadata/HTML
python3 analysis/build_all.py --version <version-id>

# Or build a subset of steps / skip completed steps
python3 analysis/build_all.py --version <version-id> --steps spine,blueprint --skip-existing

# Sync manifest, canonical default files, and rendered HTML wrappers without re-running analysis
python3 analysis/build_all.py --only-sync

# Explicitly rebuild every version in analysis/versions.json
python3 analysis/build_all.py --all
```

## Contributing

Pull requests from **both humans and AI agents** are welcome!

Contributions based on **computationally expensive** or **token-expensive** results (e.g., full dependency graphs, module-level summaries, cross-referenced mathematical expositions, or deep structural analyses) are especially appreciated.

### Guidelines

- **Keep the style simple:** Use a minimal, clean visual presentation consistent with the repository's light theme and plain, readable formatting. Avoid heavy styling, decorative clutter, or unnecessary visual complexity.
- **Keep pages simple and focused:** Design every report and interactive page so it does not overload the reader with information. Favor clear hierarchy, concise summaries, and progressive disclosure over dense dashboards, excessive controls, or walls of secondary detail.
- **Anticipate Lean codebase refactors and keep methodologies repeatable:** Expect the underlying Lean proof codebase to be refactored, reorganized, or superseded by future Lean codebases. Write deterministic, scriptable analysis and visualization pipelines that derive structure dynamically from source rather than hardcoding module paths, directory layouts, counts, or ad-hoc assumptions, and document your methodology clearly so it can be cleanly re-run on refactored or future codebases.
