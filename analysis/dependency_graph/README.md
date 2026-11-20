# Directory-Level Dependency Graph Analysis

This directory contains aggregated dependency graphs, static diagrams, and an interactive explorer derived from [graph.sqlite](file:///home/ubuntu/riemann_proof/analysis/data/graph.sqlite) and [meta.json](file:///home/ubuntu/riemann_proof/analysis/data/meta.json) for the Lean 4 repository at `/home/ubuntu/riemann_proof/lean/src`.

> **Direction Convention:** Throughout all data files, diagrams, and tools in this directory, a directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Conversely, `B` is **imported by** `A`.

---

## 1. Deliverables & Quick Links

| Artifact | Description |
| :--- | :--- |
| [build_dep_graphs.py](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/build_dep_graphs.py) | Python 3.11 stdlib script querying `graph.sqlite` (read-only) to aggregate Depth 1/2/3 edges, SCCs, and top cross-boundary files, and generating all diagrams and HTML. |
| [dir_graph.json](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/dir_graph.json) | Complete aggregated JSON across Depth 1 (`10` dirs, `33` edges), Depth 2 (`330` dirs, `1,222` edges), Depth 3 (`746` dirs, `4,818` edges), and the `877`-node hierarchical tree. |
| [top_level_graph.mmd](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/top_level_graph.mmd) | Mermaid `flowchart TD` diagram of all 10 top-level directories and all 33 cross-directory flows. |
| [top_level_graph.dot](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/top_level_graph.dot) / [top_level_graph.svg](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/top_level_graph.svg) | Graphviz source and rendered SVG of the top-level directory dependency graph (`10` nodes, `33` edges). |
| [depth2_major_graph.dot](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/depth2_major_graph.dot) / [depth2_major_graph.svg](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/depth2_major_graph.svg) | Readable 47-node Depth-2 architectural projection (`Development/*`, `CompanionTheory/*`, `PositivityTheory/*`, `GroundTheory/*`, `ReciprocityTheory/*`, `Supplements/Kernels`, `BuildAid`, `Lemmata/*`, plus top `Formalism/*` hubs and clustered minor tails). |
| [dependency_explorer.html](file:///home/ubuntu/riemann_proof/analysis/dependency_graph/dependency_explorer.html) | Self-contained offline HTML/CSS/Canvas/JS interactive explorer (zero external CDN URLs) with Depth 1→2→3 expand/collapse, height-stratified pan/zoom layout, upstream/downstream/mutual highlighting, weight slider, search, and inspector with `file://` links. |

---

## 2. Corpus & Multi-Scale Summary

From [meta.json](file:///home/ubuntu/riemann_proof/analysis/data/meta.json), the Lean codebase contains **175,187** `.lean` files (**17,374,215** lines, **1,030,531,854** bytes) and **753,261** internal file-to-file import edges. **100%** of files are reachable from [Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean) (`max_dist_from_main = 43`, `max_height_from_leaves = 202`), and the file-level import graph is a **strict DAG** (`is_dag = true`, zero file-level cycles).

Aggregating internal edges across directory boundaries at each hierarchy level yields:

| Aggregation Level | Directories | Cross-Dir Edges (Distinct Pairs) | Total Cross-Dir File Imports | % of All 753,261 Imports | Mutual Directory Pairs (`A <-> B`) | Non-Trivial SCCs (Size > 1) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| **Depth 1 (`top_dir`)** | 10 | 33 | 96,497 | 12.81% | 12 | 1 SCC (size `7`) |
| **Depth 2 (`depth2_dir`)** | 330 | 1,222 | 145,414 | 19.30% | 124 | 4 SCCs (sizes `99, 2, 2, 2`) |
| **Depth 3 (`depth3_dir`)** | 746 | 4,818 | 329,733 | 43.77% | 476 | 36 SCCs (sizes `400, 3`, and `34` pairs) |

The remaining **423,528** file imports (`56.23%`) stay completely internal to single Depth-3 directories (for instance, proof files importing sibling helper files within the same Depth-3 module).

---

## 3. Macro-Dependency Structure (Depth 1)

| Top-Level Directory | Files | Lines | Theorems | Min Dist from `Main` | Avg Dist | Max Height from Leaves | Cross-Top Out (`imports →`) | Cross-Top In (`← imported by`) | Architectural Role |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| `(root)` | 2 | 28 | 5 | 0 | 0.50 | 202 | 1 | 0 | Top-level entry point ([Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean), [Statements.lean](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean)) |
| `Supplements` | 3 | 22 | 4 | 1 | 2.00 | 201 | 7 | 1 | Thin theorem-assembly kernel (`Supplements/Kernels/*`) bridging `Main.lean` into proof tracks |
| `Development` | 141,928 | 12,232,663 | 548,600 | 2 | 15.03 | 198 | 90,406 | 2,385 | Primary proof engine (`81.0%` of files, `93.7%` of all cross-top-dir imports out) |
| `CompanionTheory` | 2,027 | 194,218 | 8,970 | 5 | 12.87 | 114 | 2,421 | 1,878 | Spectral geometry, real groups, Harish-Chandra & automorphic companion results |
| `PositivityTheory` | 449 | 55,130 | 2,633 | 6 | 9.55 | 111 | 753 | 1,057 | Automorphic positivity estimates tightly coupled with `Development` |
| `Formalism` | 18,254 | 3,200,748 | 148,219 | 4 | 13.80 | 93 | 704 | 43,538 | Foundational formal machinery (`45.1%` of all incoming cross-top-dir imports) |
| `ReciprocityTheory` | 3,845 | 563,016 | 23,374 | 6 | 12.78 | 76 | 334 | 39,723 | Reductive groups, algebraic/analytic reciprocity & estimates (`41.2%` of incoming cross-top-dir imports) |
| `GroundTheory` | 8,507 | 1,119,138 | 52,111 | 5 | 10.74 | 68 | 1,230 | 7,709 | Heights, theta functions, global/local fields, profinite & $p$-adic Hodge ground infrastructure |
| `Lemmata` | 167 | 9,232 | 176 | 8 | 13.69 | 17 | 641 | 168 | Small standalone lemma units (each in `Lemmata/<Name>`), mostly importing `Formalism` |
| `BuildAid` | 5 | 20 | 0 | 8 | 12.00 | 0 | 0 | 38 | Pure leaf build/suggestion configuration (`D1.lean`–`D5.lean`, `out_degree = 0`) |

### Key Structural Observations
1. **The Entry Chain:** [Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean) (`height = 202`) imports [Statements.lean](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean) and [Supplements/Kernels/MainTheoremsAll.lean](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheoremsAll.lean) (`height = 201`). From there, `Supplements/Kernels` imports `6` files in `Development/AutomorphicArithmetic` and `1` file in `Formalism/GammaFactorNonvanishing` ([CritLine.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean)).
2. **Star-like Consumer vs. Foundation Split:** `Development` initiates **90,406** of the **96,497** cross-top-dir imports (`93.69%`), primarily consuming `Formalism` (**41,857** imports), `ReciprocityTheory` (**38,051**), and `GroundTheory` (**7,532**). Meanwhile, `Formalism` and `ReciprocityTheory` are overwhelmingly import *targets* (`43,538` and `39,723` incoming cross-top-dir edges vs. only `704` and `334` outgoing).
3. **Pure Leaf Sink:** `BuildAid` (`D1.lean`–`D5.lean`) has `out_degree = 0` (`height = 0`) and is imported `35` times from `Development` and `3` times from `CompanionTheory`.

---

## 4. Directory-Level Cycles vs. File-Level DAG

Even though the underlying 175,187-file import graph has **zero cycles** (`is_dag = true`), aggregating edges at directory granularity produces strongly connected components (SCCs) at every level:

- **Depth 1:** `1` non-trivial SCC of size **7** containing `CompanionTheory`, `Development`, `Formalism`, `GroundTheory`, `Lemmata`, `PositivityTheory`, and `ReciprocityTheory` (while `(root)`, `Supplements`, and `BuildAid` remain singletons). There are **12 mutual directory pairs** out of 33 edges.
- **Depth 2:** `4` non-trivial SCCs — one giant **99-directory** core SCC plus three 2-directory cycles (`Formalism/CyclotomicNorms <-> Lemmata/GeneralBFactSecondBis`, `Formalism/GelfandTransference <-> Lemmata/DetNormLeProdRows`, and `ReciprocityTheory/GaloisValuations <-> ReciprocityTheory/Hypotheses`).
- **Depth 3:** `36` non-trivial SCCs — a **400-directory** core SCC, one size-3 SCC (`Formalism/CyclotomicNorms`, `Formalism/CyclotomicNorms/NonsquarefreeBounds`, `Lemmata/GeneralBFactSecondBis`), and `34` size-2 SCCs (mostly direct files in `Formalism/<Sub>` mutually coupled with `Formalism/<Sub>/<SubProofs>`).

### Why Directory Cycles Coexist with a File-Level DAG
Directories organize files by **mathematical topic** rather than strict topological build height. Low-height statement/interface files inside a high-level directory are imported by higher-height files in a foundational directory, while other high-height proof files in the first directory import the foundational directory:

- **Highly asymmetric back-flows:** `Development -> Formalism` has **41,857** imports (`20,174 -> 3,315` unique files), whereas `Formalism -> Development` has **236** imports (`177 -> 209` files) — e.g., [NandDIVb.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/AdmissibleParameterJoins/NandDIVb.lean) (`height = 25`) imports [TwistedPlaces.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/ResidueCharacters/TwistedPlaces.lean) (`height = 17`). Similarly, `Development -> ReciprocityTheory` (`38,051`) dwarfs `ReciprocityTheory -> Development` (`17`).
- **Co-evolving / near-symmetric pairs:** At Depth 1, `Development <-> CompanionTheory` (`1,874` vs. `1,437`) and `Development <-> PositivityTheory` (`1,057` vs. `632`) exhibit genuine two-way interplay. At Depth 2, the single largest bidirectional coupling is **`Development/WeilBound <-> Development/AutomorphicSpectrum`**, with **6,183** imports in one direction and **6,148** in the other!

---

## 5. Top Cross-Theory Flows (Depth 2 & Depth 3)

### Top 10 Depth-2 Cross-Directory Flows
| Rank | Source (`imports →`) | Target (`← imported by`) | Import Weight | Unique Src Files | Unique Dst Files | Reverse Weight |
|---:|:---|:---|---:|---:|---:|---:|
| 1 | `Development/AbelianVarietyTheory` | `ReciprocityTheory/ReductiveGroups` | 28,406 | 10,269 | 775 | 2 |
| 2 | `Development/AbelianVarietyTheory` | `Formalism/LocalToGlobal` | 20,139 | 10,287 | 1,515 | 8 |
| 3 | `Development/AutomorphicArithmetic` | `Development/AbelianVarietyTheory` | 11,790 | 5,995 | 6,616 | 744 |
| 4 | `Development/AbelianVarietyTheory` | `Formalism/SharpRestriction` | 10,065 | 6,573 | 588 | 2 |
| 5 | `Development/AutomorphicSpectrum` | `Development/AbelianVarietyTheory` | 7,076 | 3,133 | 1,720 | 30 |
| 6 | `Development/WeilBound` | `Development/AutomorphicSpectrum` | 6,183 | 1,731 | 3,457 | 6,148 |
| 7 | `Development/AutomorphicSpectrum` | `Development/WeilBound` | 6,148 | 4,804 | 1,005 | 6,183 |
| 8 | `Development/WeilBound` | `Development/AbelianVarietyTheory` | 5,157 | 1,750 | 2,214 | 48 |
| 9 | `Development/AutomorphicSpectrum` | `ReciprocityTheory/ReductiveGroups` | 4,336 | 2,298 | 202 | 0 |
| 10 | `Development/AutomorphicSpectrum` | `GroundTheory/HeightsAndTheta` | 3,325 | 1,332 | 1,023 | 0 |

### Top Cross-Boundary Hub Files
- Most imported file from outside `ReciprocityTheory`: [UniformisationConclusion.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean) (**2,379** incoming cross-top-dir imports), followed by [UnifUniqSt.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean) (**2,283**).
- Most imported file from outside `Formalism`: [ThExprUniqOfChartIndep2.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/Divisibility/GeneratorPowers/ThExprUniqOfChartIndep2.lean) (**871** incoming cross-top-dir imports), followed by [RhoDetPrimeEqMuTildeMulChiPow.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean) (**780**).
- Highest cross-top-dir importer inside `Development`: [KappaIntegralBound.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/CapelliComplements/KappaIntegralBound.lean) (**207** outgoing cross-top-dir imports).

---

## 6. Regenerating & Validating

```bash
python3 /home/ubuntu/riemann_proof/analysis/dependency_graph/build_dep_graphs.py
python3 -m json.tool /home/ubuntu/riemann_proof/analysis/dependency_graph/dir_graph.json > /dev/null
```
