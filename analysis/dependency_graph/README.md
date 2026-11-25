# Theory-Level Dependency Graph Analysis (community-9211277d)

This directory contains aggregated dependency graphs, static diagrams, and an interactive explorer mapping the logical relationships across the mathematical domains and sub-theories of `src/` (**803 reachable modules**, **1,733 edges**).

> **Direction Convention:** Throughout all data files, diagrams, and tools in this directory, a directed edge **`A -> B`** means **`A` depends on `B`** (`A` imports mathematical definitions or theorems from `B`). Conversely, `B` supplies results to `A`.

---

## 1. Deliverables & Quick Links

| Artifact | Description |
| :--- | :--- |
| `dir_graph_data.js` / `dir_graph.json` | Aggregated dependency graph across Depth 1 (top-level theories), Depth 2 (sub-theories), Depth 3 (topic modules), and the hierarchical tree. |
| `top_level_graph.mmd` / `top_level_graph.dot` / [top_level_graph.svg](top_level_graph.svg) | Mermaid and Graphviz diagrams of the top-level mathematical domains and cross-domain flows. |
| `depth2_major_graph.dot` / [depth2_major_graph.svg](depth2_major_graph.svg) | Readable 27-node Depth-2 architectural projection across sub-theories and major hubs. |
| [dependency_explorer.html](dependency_explorer.html) | Self-contained offline interactive explorer with Depth 1→2→3 expand/collapse, height-stratified pan/zoom layout, upstream/downstream/mutual highlighting, and search. |

---

## 2. Macro-Dependency Structure (Top-Level Theories)

All **803** modules reachable from [Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean) form a **strict acyclic DAG** (`is_dag = True`), organized across **3** active top-level directories:

| Top-Level Domain | Files | Lines | Dist Min | Max Height | Mathematical & Architectural Role |
| :--- |---:|---:|---:|---:|:---|
| `(root)` | 2 | 38 | 0 | 53 | Top-level theorem statements and entry point ([Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean), [Statements.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean)) |
| `New` | 306 | 191,998 | 1 | 52 | Novel proof architecture (`Main.lean`, `Reduction/`, `Derivatives/`, `UpperBound/`, `Spanning/`, `Determinant/`, `OneLift/`, `Congruences/`, `Appendix/`) |
| `Lib` | 495 | 285,088 | 4 | 36 | Self-contained background theories classed as known in the literature (imports zero modules from `New/`) |

### Key Structural Observations
1. **The Entry Chain:** [Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean) imports [Statements.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean) and `New/Main.lean`, which reduces RH and GRH via functional-equation reflection (`New.zeros_on_line`, `New.zeta_zeros_on_line`) to `New/Reduction/OneSidedBound.lean` (`New.grh`) and `New/Reduction/MainInequality.lean` (`star_inequality`).
2. **Clean `New` vs. `Lib` Boundary:** `New/` contains the proof argument across 8 topical folders (`Reduction`, `Derivatives`, `UpperBound`, `Spanning`, `Determinant`, `OneLift`, `Congruences`, `Appendix`), while `Lib/` contains self-contained background theory and imports **zero** modules from `New/` (so Depth 1 has 0 nontrivial SCCs).

---

## 3. Topical Directory Cycles vs. Strict Module-Level DAG

Even though the underlying module-level dependency graph has **zero cycles** (`is_dag = True`), aggregating dependencies by topical folder produces bidirectional couplings (strongly connected components) between directories: Depth 1 contains **1** top-level SCC (spanning 2 domains), and Depth 2 contains **2** nontrivial sub-theory SCCs (largest spanning **16** sub-theories; **47** mutual bidirectional pairs).

### Why Directory Cycles Coexist with a Module-Level DAG
Directories inside `New/` and `Lib/` organize modules by **mathematical topic** rather than strict build height (`GUIDE.md`: folders are not layers). While `Lib/` has zero imports from `New/`, topical sub-theories inside `New/` (and inside `Lib/`) exchange definitions and lemmas in both directions at different file heights.
- **Co-Evolving Mathematical Pillars:** At Depth 1 and Depth 2, co-evolving proof synthesis tracks alternate across inductive stages while remaining strictly acyclic at individual `.lean` file granularity.

---

## 4. Major Cross-Theory Mathematical Flows (Depth 2)

| Source Sub-Theory (`depends on →`) | Target Sub-Theory (`← supplies`) | Import Edges | Source → Target Files | Mathematical Connection |
|:---|:---|---:|---|:---|
| `Lib/Shimura` | `Lib/General` | 30 | 21 → 19 | Cross-theory module dependency flow |
| `Lib/Adelic` | `Lib/General` | 20 | 16 → 17 | Cross-theory module dependency flow |
| `Lib/Weil` | `Lib/Adelic` | 18 | 16 → 14 | Cross-theory module dependency flow |
| `New/UpperBound` | `Lib/Weil` | 18 | 14 → 17 | Cross-theory module dependency flow |
| `Lib/DiscreteSeries` | `Lib/General` | 17 | 14 → 13 | Cross-theory module dependency flow |
| `New/Spanning` | `Lib/DiscreteSeries` | 17 | 13 → 12 | Cross-theory module dependency flow |
| `Lib/Weil` | `Lib/General` | 15 | 12 → 13 | Cross-theory module dependency flow |
| `Lib/SiegelWeil` | `Lib/Weil` | 14 | 12 → 9 | Cross-theory module dependency flow |
| `New/Congruences` | `Lib/General` | 14 | 14 → 12 | Cross-theory module dependency flow |
| `Lib/General` | `Lib/Adelic` | 13 | 13 → 10 | Cross-theory module dependency flow |
| `Lib/ClassField` | `Lib/General` | 12 | 9 → 9 | Cross-theory module dependency flow |
| `Lib/Cohomology` | `Lib/General` | 12 | 9 → 9 | Cross-theory module dependency flow |
| `Lib/General` | `Lib` | 12 | 12 → 1 | Cross-theory module dependency flow |
| `Lib/Cohomology` | `Lib/PadicComparison` | 11 | 11 → 8 | Cross-theory module dependency flow |
| `New/Determinant` | `New/OneLift` | 11 | 8 → 10 | Cross-theory module dependency flow |

---

## 5. Regenerating & Validating

```bash
# Rebuild dependency graphs for this Lean version via the orchestrator
python3 analysis/build_all.py --version community-9211277d --steps dep_graphs

# Or run standalone against specific SQLite/source paths:
python3 analysis/dependency_graph/build_dep_graphs.py --help
```

