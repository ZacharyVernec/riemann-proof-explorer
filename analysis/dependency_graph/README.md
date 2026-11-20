# Theory-Level Dependency Graph Analysis

This directory contains aggregated dependency graphs, static diagrams, and an interactive explorer mapping the logical relationships across the mathematical domains and sub-theories of the proof.

> **Direction Convention:** Throughout all data files, diagrams, and tools in this directory, a directed edge **`A -> B`** means **`A` depends on `B`** (`A` imports mathematical definitions or theorems from `B`). Conversely, `B` supplies results to `A`.

---

## 1. Deliverables & Quick Links

| Artifact | Description |
| :--- | :--- |
| [build_dep_graphs.py](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/build_dep_graphs.py) | Script querying `graph.sqlite` to aggregate Depth 1/2/3 theory dependencies, strongly connected components (SCCs), and cross-boundary bridges. |
| [dir_graph.json](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/dir_graph.json) | Aggregated dependency graph across Depth 1 (top-level theories), Depth 2 (sub-theories), Depth 3 (topic modules), and the hierarchical tree. |
| [top_level_graph.mmd](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/top_level_graph.mmd) | Mermaid `flowchart TD` diagram of the top-level mathematical domains and cross-domain flows. |
| [top_level_graph.dot](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/top_level_graph.dot) / [top_level_graph.svg](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/top_level_graph.svg) | Graphviz source and rendered SVG of the top-level theory dependency graph. |
| [depth2_major_graph.dot](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/depth2_major_graph.dot) / [depth2_major_graph.svg](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/depth2_major_graph.svg) | Readable 47-node Depth-2 architectural projection (`Development/*`, `CompanionTheory/*`, `PositivityTheory/*`, `GroundTheory/*`, `ReciprocityTheory/*`, `Supplements/Kernels`, `Lemmata/*`, plus top `Formalism/*` hubs). |
| [dependency_explorer.html](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/dependency_explorer.html) | Self-contained offline HTML/CSS/Canvas/JS interactive explorer with Depth 1→2→3 expand/collapse, height-stratified pan/zoom layout, upstream/downstream/mutual highlighting, and search. |

---

## 2. Macro-Dependency Structure (Top-Level Theories)

All modules in the proof are reachable from [Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean) and form a **strict acyclic DAG** at the module level. At the top-level directory level, the proof is organized into distinct mathematical domains:

| Top-Level Domain | Mathematical & Architectural Role |
| :--- | :--- |
| `(root)` | Top-level theorem statements and entry point ([Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean), [Statements.lean](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean)) |
| `Supplements` | Theorem-assembly kernel (`Supplements/Kernels/*`) bridging `Main.lean` into the main proof tracks |
| `Development` | Primary proof synthesis engine: abelian varieties, automorphic arithmetic, automorphic spectrum, Weil bound, étale cohomology, discrete groups, and resolution of singularities |
| `CompanionTheory` | Spectral geometry, real reductive groups, Harish-Chandra modules, and automorphic companion results |
| `PositivityTheory` | Automorphic positivity estimates, Rankin-Selberg integrals, and weight-1 Hilbert Eisenstein series |
| `Formalism` | Foundational analytic and algebraic specification contracts: local-to-global theta lifts, sharp restriction, period integrals, Hermitian curvature, and local Bloch-Kato cohomology |
| `ReciprocityTheory` | Reductive groups, PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, $L^2$ $\bar\partial$-estimates, and reciprocity laws |
| `GroundTheory` | Arakelov heights, theta functions, global/local fields, Whittaker multiplicity one, profinite Poitou-Tate cohomology, and $p$-adic Hodge theory |
| `Lemmata` | Standalone linear-algebraic and matrix-determinant lemma units (e.g., Cauchy-Binet and Weyl pullback identities) |
| `BuildAid` | Library-suggestion namespace configuration leaves (`D1.lean`–`D5.lean`) |

### Key Structural Observations
1. **The Entry Chain:** [Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean) depends on [Statements.lean](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean) and [Supplements/Kernels/MainTheoremsAll.lean](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheoremsAll.lean). From there, `Supplements/Kernels` draws on the main proof synthesis in `Development/AutomorphicArithmetic` and the functional-equation reflection theorem in `Formalism/GammaFactorNonvanishing` ([CritLine.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean)).
2. **Synthesis vs. Foundation Split:** `Development` serves as the central consumer and synthesis engine, drawing heavily on the specification contracts and foundational theorems in `Formalism`, `ReciprocityTheory`, and `GroundTheory`, while co-evolving with `CompanionTheory` and `PositivityTheory`.

---

## 3. Topical Directory Cycles vs. Strict Module-Level DAG

Even though the underlying module-level dependency graph has **zero cycles** (`is_dag = true`), aggregating dependencies by topical folder produces bidirectional couplings (strongly connected components) between directories.

### Why Directory Cycles Coexist with a Module-Level DAG
Directories organize the proof by **mathematical topic** rather than strict topological build height. Low-height specification or definition modules inside a high-level directory are referenced by higher-height proof modules in a foundational directory, while high-height synthesis modules in the first directory depend on the foundational directory:

- **Specification-to-Realization Back-Flows:** `Development` depends heavily on `Formalism` and `ReciprocityTheory`, while a small number of modules in `Formalism` reference low-height definitions in `Development` — e.g., [NandDIVb.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/AdmissibleParameterJoins/NandDIVb.lean) depends on [TwistedPlaces.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/ResidueCharacters/TwistedPlaces.lean).
- **Co-Evolving Mathematical Pillars:** At Depth 1, `Development <-> CompanionTheory` and `Development <-> PositivityTheory` exhibit genuine two-way mathematical interplay. At Depth 2, **`Development/WeilBound <-> Development/AutomorphicSpectrum`** are tightly coupled, as spectral decomposition and Weil-bound / Moriwaki-bigness arguments alternate across inductive stages.

---

## 4. Major Cross-Theory Mathematical Flows (Depth 2)

| Source Sub-Theory (`depends on →`) | Target Sub-Theory (`← supplies`) | Mathematical Connection |
|:---|:---|:---|
| `Development/AbelianVarietyTheory` | `ReciprocityTheory/ReductiveGroups` | PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, and polarized abelian scheme laws |
| `Development/AbelianVarietyTheory` | `Formalism/LocalToGlobal` | Indefinite/definite unitary theta-lift stages, Siegel lattice theory, and seesaw/doubling identities |
| `Development/AutomorphicArithmetic` | `Development/AbelianVarietyTheory` | Covolume bounds, literature packages (`LitN`), local Langlands axioms, and CM period comparisons |
| `Development/AbelianVarietyTheory` | `Formalism/SharpRestriction` | Formal differential theta-expression chart independence, local Bloch-Kato cohomology (`LocCoh`), and Schur norm bounds |
| `Development/AutomorphicSpectrum` | `Development/AbelianVarietyTheory` | Polarized abelian scheme realizations, divisor proofs, and discrete series branching |
| `Development/WeilBound` | `Development/AutomorphicSpectrum` | Mutual interplay between spectral geometry / good root towers and Moriwaki arithmetic bigness / regularized Siegel-Weil |
| `Development/WeilBound` | `Development/AbelianVarietyTheory` | De Rham/crystalline comparisons, Nef Riemann-Roch, and Nadel vanishing pairs |
| `Development/AutomorphicSpectrum` | `ReciprocityTheory/ReductiveGroups` | Boundary charts on toroidal compactifications and semiabelian scheme models |
| `Development/AutomorphicSpectrum` | `GroundTheory/HeightsAndTheta` | Arakelov Hermitian vector bundles, Bost-Zhang slope inequalities, and DVR pairing flag independence |
| `Development/AbelianVarietyTheory` | `Formalism/LocalRingCardinality` | Master CM host and self-dual Hermitian lattice package (`D7`) and Fontaine period-ring identifications (`LocTied`) |

### Key Cross-Boundary Mathematical Hubs
- **Toroidal & Semiabelian Uniformisation (`ReciprocityTheory`):** [UniformisationConclusion.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean) and [UnifUniqSt.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean) serve as the primary geometric contracts for PEL Shimura toroidal models and uniqueness of Mumford degeneration data.
- **Formal Theta Differential Operators & CM Host Contracts (`Formalism`):** [ThExprUniqOfChartIndep2.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/Divisibility/GeneratorPowers/ThExprUniqOfChartIndep2.lean) and [RhoDetPrimeEqMuTildeMulChiPow.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean) coordinate chart-independent formal differential operators and the master arithmetic-automorphic data structure `D7`.
- **Capelli & Archimedean Integral Casts (`Development`):** [KappaIntegralBound.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/CapelliComplements/KappaIntegralBound.lean) aggregates archimedean Capelli identity and integral-bound prerequisites across theories.

---

## 5. Regenerating & Validating

```bash
python3 /home/ubuntu/riemann_proof/analysis/dependency_graph/build_dep_graphs.py
python3 -m json.tool /home/ubuntu/riemann_proof/analysis/dependency_graph/dir_graph.json > /dev/null
```
