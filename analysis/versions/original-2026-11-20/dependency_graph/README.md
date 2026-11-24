# Theory-Level Dependency Graph Analysis (original-2026-11-20)

This directory contains aggregated dependency graphs, static diagrams, and an interactive explorer mapping the logical relationships across the mathematical domains and sub-theories of `lean/src/` (**175,187 reachable modules**, **753,261 edges**).

> **Direction Convention:** Throughout all data files, diagrams, and tools in this directory, a directed edge **`A -> B`** means **`A` depends on `B`** (`A` imports mathematical definitions or theorems from `B`). Conversely, `B` supplies results to `A`.

---

## 1. Deliverables & Quick Links

| Artifact | Description |
| :--- | :--- |
| `dir_graph_data.js` / `dir_graph.json` | Aggregated dependency graph across Depth 1 (top-level theories), Depth 2 (sub-theories), Depth 3 (topic modules), and the hierarchical tree. |
| `top_level_graph.mmd` / `top_level_graph.dot` / [top_level_graph.svg](top_level_graph.svg) | Mermaid and Graphviz diagrams of the top-level mathematical domains and cross-domain flows. |
| `depth2_major_graph.dot` / [depth2_major_graph.svg](depth2_major_graph.svg) | Readable 47-node Depth-2 architectural projection across sub-theories and major hubs. |
| [dependency_explorer.html](dependency_explorer.html) | Self-contained offline interactive explorer with Depth 1→2→3 expand/collapse, height-stratified pan/zoom layout, upstream/downstream/mutual highlighting, and search. |

---

## 2. Macro-Dependency Structure (Top-Level Theories)

All **175,187** modules reachable from [Main.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean) form a **strict acyclic DAG** (`is_dag = True`), organized across **10** active top-level directories:

| Top-Level Domain | Files | Lines | Dist Min | Max Height | Mathematical & Architectural Role |
| :--- |---:|---:|---:|---:|:---|
| `(root)` | 2 | 28 | 0 | 202 | Top-level theorem statements and entry point ([Main.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean), [Statements.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Statements.lean)) |
| `Supplements` | 3 | 22 | 1 | 201 | Theorem-assembly kernel (`Supplements/Kernels/*`) bridging `Main.lean` into the main proof tracks |
| `Development` | 141,928 | 12,232,663 | 2 | 198 | Primary proof synthesis engine: abelian varieties, automorphic arithmetic, automorphic spectrum, Weil bound, étale cohomology, discrete groups, and resolution of singularities |
| `CompanionTheory` | 2,027 | 194,218 | 5 | 114 | Spectral geometry, real reductive groups, Harish-Chandra modules, and automorphic companion results |
| `PositivityTheory` | 449 | 55,130 | 6 | 111 | Automorphic positivity estimates, Rankin-Selberg integrals, and weight-1 Hilbert Eisenstein series |
| `Formalism` | 18,254 | 3,200,748 | 4 | 93 | Foundational analytic and algebraic specification contracts: local-to-global theta lifts, sharp restriction, period integrals, Hermitian curvature, and local Bloch-Kato cohomology |
| `ReciprocityTheory` | 3,845 | 563,016 | 6 | 76 | Reductive groups, PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, $L^2$ $\bar\partial$-estimates, and reciprocity laws |
| `GroundTheory` | 8,507 | 1,119,138 | 5 | 68 | Arakelov heights, theta functions, global/local fields, Whittaker multiplicity one, profinite Poitou-Tate cohomology, and $p$-adic Hodge theory |
| `Lemmata` | 167 | 9,232 | 8 | 17 | Standalone linear-algebraic and matrix-determinant lemma units |
| `BuildAid` | 5 | 20 | 8 | 0 | Library-suggestion namespace configuration leaves |

---

## 3. Major Cross-Theory Mathematical Flows (Depth 2)

| Source Sub-Theory (`depends on →`) | Target Sub-Theory (`← supplies`) | Import Edges | Source Files → Target Files |
|:---|:---|---:|---|
| `Development/AbelianVarietyTheory` | `ReciprocityTheory/ReductiveGroups` | 28,406 | 10,269 → 775 |
| `Development/AbelianVarietyTheory` | `Formalism/LocalToGlobal` | 20,139 | 10,287 → 1,515 |
| `Development/AutomorphicArithmetic` | `Development/AbelianVarietyTheory` | 11,790 | 5,995 → 6,616 |
| `Development/AbelianVarietyTheory` | `Formalism/SharpRestriction` | 10,065 | 6,573 → 588 |
| `Development/AutomorphicSpectrum` | `Development/AbelianVarietyTheory` | 7,076 | 3,133 → 1,720 |
| `Development/WeilBound` | `Development/AutomorphicSpectrum` | 6,183 | 1,731 → 3,457 |
| `Development/AutomorphicSpectrum` | `Development/WeilBound` | 6,148 | 4,804 → 1,005 |
| `Development/WeilBound` | `Development/AbelianVarietyTheory` | 5,157 | 1,750 → 2,214 |
| `Development/AutomorphicSpectrum` | `ReciprocityTheory/ReductiveGroups` | 4,336 | 2,298 → 202 |
| `Development/AutomorphicSpectrum` | `GroundTheory/HeightsAndTheta` | 3,325 | 1,332 → 1,023 |
| `Development/AbelianVarietyTheory` | `Formalism/LocalRingCardinality` | 3,205 | 2,601 → 81 |
| `Development/AutomorphicArithmetic` | `Development/WeilBound` | 1,444 | 991 → 903 |
| `Development/AbelianVarietyTheory` | `ReciprocityTheory/AnalyticForms` | 1,151 | 1,004 → 67 |
| `Development/WeilBound` | `GroundTheory/HeightsAndTheta` | 1,087 | 250 → 740 |
| `Development/AutomorphicSpectrum` | `CompanionTheory/SpectralGeometry` | 954 | 368 → 212 |

