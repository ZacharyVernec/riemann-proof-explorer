# Theory-Level Dependency Graph Analysis (community-307cef33)

This directory contains aggregated dependency graphs, static diagrams, and an interactive explorer mapping the logical relationships across the mathematical domains and sub-theories of `src/` (**59,836 reachable modules**, **367,774 edges**).

> **Direction Convention:** Throughout all data files, diagrams, and tools in this directory, a directed edge **`A -> B`** means **`A` depends on `B`** (`A` imports mathematical definitions or theorems from `B`). Conversely, `B` supplies results to `A`.

---

## 1. Deliverables & Quick Links

| Artifact | Description |
| :--- | :--- |
| `dir_graph_data.js` / `dir_graph.json` | Aggregated dependency graph across Depth 1 (top-level theories), Depth 2 (sub-theories), Depth 3 (topic modules), and the hierarchical tree. |
| `top_level_graph.mmd` / `top_level_graph.dot` / [top_level_graph.svg](top_level_graph.svg) | Mermaid and Graphviz diagrams of the top-level mathematical domains and cross-domain flows. |
| `depth2_major_graph.dot` / [depth2_major_graph.svg](depth2_major_graph.svg) | Readable 43-node Depth-2 architectural projection across sub-theories and major hubs. |
| [dependency_explorer.html](dependency_explorer.html) | Self-contained offline interactive explorer with Depth 1→2→3 expand/collapse, height-stratified pan/zoom layout, upstream/downstream/mutual highlighting, and search. |

---

## 2. Macro-Dependency Structure (Top-Level Theories)

All **59,836** modules reachable from [Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Main.lean) form a **strict acyclic DAG** (`is_dag = True`), organized across **8** active top-level directories:

| Top-Level Domain | Files | Lines | Dist Min | Max Height | Mathematical & Architectural Role |
| :--- |---:|---:|---:|---:|:---|
| `(root)` | 2 | 76 | 0 | 93 | Top-level theorem statements and entry point ([Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Main.lean), [Statements.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Statements.lean)) |
| `Development` | 41,263 | 11,657,315 | 1 | 92 | Primary proof synthesis engine: abelian varieties, automorphic arithmetic, automorphic spectrum, Weil bound, étale cohomology, discrete groups, and resolution of singularities |
| `CompanionTheory` | 685 | 178,444 | 3 | 69 | Spectral geometry, real reductive groups, Harish-Chandra modules, and automorphic companion results |
| `PositivityTheory` | 226 | 44,166 | 3 | 45 | Automorphic positivity estimates, Rankin-Selberg integrals, and weight-1 Hilbert Eisenstein series |
| `Formalism` | 9,901 | 2,765,150 | 3 | 56 | Foundational analytic and algebraic specification contracts: local-to-global theta lifts, sharp restriction, period integrals, Hermitian curvature, and local Bloch-Kato cohomology |
| `ReciprocityTheory` | 2,393 | 494,752 | 2 | 47 | Reductive groups, PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, $L^2$ $\bar\partial$-estimates, and reciprocity laws |
| `GroundTheory` | 5,217 | 868,235 | 2 | 41 | Arakelov heights, theta functions, global/local fields, Whittaker multiplicity one, profinite Poitou-Tate cohomology, and $p$-adic Hodge theory |
| `Lemmata` | 149 | 6,857 | 4 | 10 | Standalone linear-algebraic and matrix-determinant lemma units |

### Key Structural Observations
1. **The Entry Chain:** [Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Main.lean) imports [Statements.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Statements.lean) and `Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean` (alongside `ClaimStrip.lean`), feeding directly into the main character-box proof synthesis and its functional-equation reflection dependencies.
2. **Synthesis vs. Foundation Split:** `Development` serves as the central consumer and synthesis engine, drawing heavily on the specification contracts and foundational theorems in `Formalism`, `ReciprocityTheory`, and `GroundTheory`, while co-evolving with `CompanionTheory` and `PositivityTheory`.

---

## 3. Topical Directory Cycles vs. Strict Module-Level DAG

Even though the underlying module-level dependency graph has **zero cycles** (`is_dag = True`), aggregating dependencies by topical folder produces bidirectional couplings (strongly connected components) between directories: Depth 1 contains **1** top-level SCC (spanning 8 domains), and Depth 2 contains **4** nontrivial sub-theory SCCs (largest spanning **105** sub-theories; **145** mutual bidirectional pairs).

### Why Directory Cycles Coexist with a Module-Level DAG
Directories organize the proof by **mathematical topic** rather than strict topological build height. Low-height specification or definition modules inside a high-level directory are referenced by higher-height proof modules in a foundational directory, while high-height synthesis modules in the first directory depend on the foundational directory:

- **Specification-to-Realization Back-Flows:** `Development` depends heavily on `Formalism` and `ReciprocityTheory`, while a small number of modules in `Formalism` reference low-height parameter/character helpers inside `Development`.
- **Co-Evolving Mathematical Pillars:** At Depth 1, `Development <-> CompanionTheory` and `Development <-> PositivityTheory` exhibit two-way interplay; at Depth 2, **`Development/WeilBound <-> Development/AutomorphicSpectrum`** are tightly coupled, as spectral decomposition and Weil-bound / Moriwaki-bigness arguments alternate across inductive stages.

---

## 4. Major Cross-Theory Mathematical Flows (Depth 2)

| Source Sub-Theory (`depends on →`) | Target Sub-Theory (`← supplies`) | Import Edges | Source → Target Files | Mathematical Connection |
|:---|:---|---:|---|:---|
| `Development/AutomorphicArithmetic` | `Development/AbelianVarietyTheory` | 24,704 | 2,860 → 8,582 | Covolume bounds, literature packages (`LitN`), local Langlands axioms, and CM period comparisons |
| `Development/AbelianVarietyTheory` | `ReciprocityTheory/ReductiveGroups` | 15,358 | 5,353 → 835 | PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, and polarized abelian scheme laws |
| `Development/AbelianVarietyTheory` | `Formalism/LocalToGlobal` | 14,160 | 5,997 → 1,557 | Indefinite/definite unitary theta-lift stages, Siegel lattice theory, and seesaw/doubling identities |
| `Development/WeilBound` | `Development/AbelianVarietyTheory` | 5,463 | 1,274 → 2,041 | De Rham/crystalline comparisons, Nef Riemann–Roch, and Nadel vanishing pairs |
| `Development/AbelianVarietyTheory` | `Formalism/SharpRestriction` | 5,142 | 3,140 → 551 | Formal differential theta-expression chart independence, local Bloch–Kato cohomology (`LocCoh`), and Schur norm bounds |
| `Development/AutomorphicSpectrum` | `Development/AbelianVarietyTheory` | 4,154 | 1,126 → 1,533 | Polarized abelian scheme realizations, divisor proofs, and discrete series branching |
| `Development/WeilBound` | `Development/AutomorphicSpectrum` | 3,871 | 830 → 1,931 | Mutual interplay between spectral geometry / good root towers and Moriwaki arithmetic bigness / regularized Siegel–Weil |
| `Development/AutomorphicSpectrum` | `Development/WeilBound` | 2,500 | 1,401 → 697 | Regularized Siegel–Weil inputs feeding back into automorphic spectral & geometric tower stages |
| `Development/AutomorphicArithmetic` | `Formalism/LocalToGlobal` | 2,397 | 594 → 702 | Local-to-global theta-kernel stages and definite/indefinite lift contracts |
| `Development/AutomorphicSpectrum` | `ReciprocityTheory/ReductiveGroups` | 2,344 | 848 → 276 | Boundary charts on toroidal compactifications and semiabelian scheme models |
| `Development/AutomorphicArithmetic` | `Development/WeilBound` | 2,020 | 589 → 1,026 | Moriwaki bigness, étale finiteness, and resolution inputs feeding automorphic-arithmetic thresholds |
| `Development/AutomorphicSpectrum` | `GroundTheory/HeightsAndTheta` | 1,994 | 472 → 972 | Arakelov Hermitian vector bundles, Bost–Zhang slope inequalities, and DVR pairing flag independence |
| `Development/AbelianVarietyTheory` | `Formalism/LocalRingCardinality` | 1,907 | 1,489 → 77 | Master CM host and self-dual Hermitian lattice package (`D7`) and Fontaine period-ring identifications (`LocTied`) |
| `GroundTheory/HeightsAndTheta` | `ReciprocityTheory/ReductiveGroups` | 1,347 | 764 → 142 | Cross-theory module dependency flow |
| `Development/AutomorphicArithmetic` | `Formalism/SharpRestriction` | 1,305 | 586 → 315 | Cross-theory module dependency flow |

---

## 5. Regenerating & Validating

```bash
# Rebuild dependency graphs for this Lean version via the orchestrator
python3 analysis/build_all.py --version community-307cef33 --steps dep_graphs

# Or run standalone against specific SQLite/source paths:
python3 analysis/dependency_graph/build_dep_graphs.py --help
```

