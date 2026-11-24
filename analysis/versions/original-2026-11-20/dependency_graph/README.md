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

### Key Structural Observations
1. **The Entry Chain:** [Main.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean) depends on [Statements.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Statements.lean) and `Supplements/Kernels/MainTheoremsAll.lean`. From there, `Supplements/Kernels` draws on the main proof synthesis in `Development/AutomorphicArithmetic` and the functional-equation reflection theorem in `Formalism/GammaFactorNonvanishing`.
2. **Synthesis vs. Foundation Split:** `Development` serves as the central consumer and synthesis engine, drawing heavily on the specification contracts and foundational theorems in `Formalism`, `ReciprocityTheory`, and `GroundTheory`, while co-evolving with `CompanionTheory` and `PositivityTheory`.

---

## 3. Topical Directory Cycles vs. Strict Module-Level DAG

Even though the underlying module-level dependency graph has **zero cycles** (`is_dag = True`), aggregating dependencies by topical folder produces bidirectional couplings (strongly connected components) between directories: Depth 1 contains **1** top-level SCC (spanning 7 domains), and Depth 2 contains **4** nontrivial sub-theory SCCs (largest spanning **99** sub-theories; **124** mutual bidirectional pairs).

### Why Directory Cycles Coexist with a Module-Level DAG
Directories organize the proof by **mathematical topic** rather than strict topological build height. Low-height specification or definition modules inside a high-level directory are referenced by higher-height proof modules in a foundational directory, while high-height synthesis modules in the first directory depend on the foundational directory:

- **Specification-to-Realization Back-Flows:** `Development` depends heavily on `Formalism` and `ReciprocityTheory`, while a small number of modules in `Formalism` reference low-height parameter/character helpers inside `Development`.
- **Co-Evolving Mathematical Pillars:** At Depth 1, `Development <-> CompanionTheory` and `Development <-> PositivityTheory` exhibit two-way interplay; at Depth 2, **`Development/WeilBound <-> Development/AutomorphicSpectrum`** are tightly coupled, as spectral decomposition and Weil-bound / Moriwaki-bigness arguments alternate across inductive stages.

---

## 4. Major Cross-Theory Mathematical Flows (Depth 2)

| Source Sub-Theory (`depends on →`) | Target Sub-Theory (`← supplies`) | Import Edges | Source → Target Files | Mathematical Connection |
|:---|:---|---:|---|:---|
| `Development/AbelianVarietyTheory` | `ReciprocityTheory/ReductiveGroups` | 28,406 | 10,269 → 775 | PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, and polarized abelian scheme laws |
| `Development/AbelianVarietyTheory` | `Formalism/LocalToGlobal` | 20,139 | 10,287 → 1,515 | Indefinite/definite unitary theta-lift stages, Siegel lattice theory, and seesaw/doubling identities |
| `Development/AutomorphicArithmetic` | `Development/AbelianVarietyTheory` | 11,790 | 5,995 → 6,616 | Covolume bounds, literature packages (`LitN`), local Langlands axioms, and CM period comparisons |
| `Development/AbelianVarietyTheory` | `Formalism/SharpRestriction` | 10,065 | 6,573 → 588 | Formal differential theta-expression chart independence, local Bloch–Kato cohomology (`LocCoh`), and Schur norm bounds |
| `Development/AutomorphicSpectrum` | `Development/AbelianVarietyTheory` | 7,076 | 3,133 → 1,720 | Polarized abelian scheme realizations, divisor proofs, and discrete series branching |
| `Development/WeilBound` | `Development/AutomorphicSpectrum` | 6,183 | 1,731 → 3,457 | Mutual interplay between spectral geometry / good root towers and Moriwaki arithmetic bigness / regularized Siegel–Weil |
| `Development/AutomorphicSpectrum` | `Development/WeilBound` | 6,148 | 4,804 → 1,005 | Regularized Siegel–Weil inputs feeding back into automorphic spectral & geometric tower stages |
| `Development/WeilBound` | `Development/AbelianVarietyTheory` | 5,157 | 1,750 → 2,214 | De Rham/crystalline comparisons, Nef Riemann–Roch, and Nadel vanishing pairs |
| `Development/AutomorphicSpectrum` | `ReciprocityTheory/ReductiveGroups` | 4,336 | 2,298 → 202 | Boundary charts on toroidal compactifications and semiabelian scheme models |
| `Development/AutomorphicSpectrum` | `GroundTheory/HeightsAndTheta` | 3,325 | 1,332 → 1,023 | Arakelov Hermitian vector bundles, Bost–Zhang slope inequalities, and DVR pairing flag independence |
| `Development/AbelianVarietyTheory` | `Formalism/LocalRingCardinality` | 3,205 | 2,601 → 81 | Master CM host and self-dual Hermitian lattice package (`D7`) and Fontaine period-ring identifications (`LocTied`) |
| `Development/AutomorphicArithmetic` | `Development/WeilBound` | 1,444 | 991 → 903 | Moriwaki bigness, étale finiteness, and resolution inputs feeding automorphic-arithmetic thresholds |
| `Development/AbelianVarietyTheory` | `ReciprocityTheory/AnalyticForms` | 1,151 | 1,004 → 67 | Cross-theory module dependency flow |
| `Development/WeilBound` | `GroundTheory/HeightsAndTheta` | 1,087 | 250 → 740 | Cross-theory module dependency flow |
| `Development/AutomorphicSpectrum` | `CompanionTheory/SpectralGeometry` | 954 | 368 → 212 | Cross-theory module dependency flow |

---

## 5. Regenerating & Validating

```bash
# Rebuild dependency graphs for this Lean version via the orchestrator
python3 analysis/build_all.py --version original-2026-11-20 --steps dep_graphs

# Or run standalone against specific SQLite/source paths:
python3 analysis/dependency_graph/build_dep_graphs.py --help
```

