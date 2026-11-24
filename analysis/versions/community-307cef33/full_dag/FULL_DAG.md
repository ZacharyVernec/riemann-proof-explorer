# Full Lean Module Dependency DAG (`community-307cef33`)

This document describes the repeatable layout pipeline, binary data packaging, graph-simplification modes, and WebGL visualization behind the interactive full-graph viewer:

- **Interactive Viewer:** [full_dag.html](full_dag.html) (pan and zoom across all modules and import edges, with three composable simplification switches: **Collapse existing theory** `C`, **Hide redundant imports** `H`, and **Collapse chains & leaves** `L`, plus the **Max depth** BFS filter `[` / `]`)
- **Layout Generator:** [build_full_dag.py](build_full_dag.py)
- **Layout Summary:** [layout_summary.json](layout_summary.json)
- **SQLite Indexer:** [build_index.py](../build_index.py)
- **Existing-Theory Inventory & Methodology:** [PUBLISHED_THEOREMS_INVENTORY.html](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.html) ([Markdown](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md))

> **Direction Convention:** Every node represents a `.lean` module under `src`. A directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Top-level theorem modules sit at the top (`layer 0`), and foundational definitions and leaf modules sit below (`layer 1..93`).

---

## 1. Why Modules Rather Than Individual Statements?

In Lean 4, a **module** corresponds 1-to-1 with a single `.lean` source file under `src/` (the compilation unit that produces one `.olean` binary). For instance, `src/Main.lean` is module `Main`, and `src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean` is module `Development.AutomorphicArithmetic.CharacterBoxes.ClaimStrip`. Each module begins with explicit `import` headers declaring its dependencies, and because Lean forbids circular imports, the module import graph is guaranteed to be a strict DAG.

Inside those modules live individual **declarations** (`theorem`, `lemma`, `def`, `structure`, `class`, `inductive`, `abbrev`, `instance`). A finer-grained **declaration-level DAG**—linking every declaration to the exact constants referenced in its type and proof term—is not tracked here for three reasons:

1. **Accurate extraction requires full compilation:** Lean 4 proofs rely heavily on tactics (`simp`, `linarith`, `ring`, `aesop`, etc.), typeclass synthesis, coercions, and `open`ed namespaces, so many dependencies never appear explicitly by name in raw `.lean` source text. Recovering true declaration-level edges requires compiling the entire codebase to `.olean` files and inspecting Lean's elaborated `Environment` (for example, `Expr.getUsedConstants` on each `ConstantInfo`). By contrast, module `import` statements are explicit syntax at the top of every file, allowing [build_index.py](../build_index.py) to extract the exact module DAG deterministically from `src/` using only Python.
2. **Scale and architectural clarity:** Across reachable modules, the codebase contains **761,777** declarations (12.7× the **59,836** modules). Including tactic-elaborated and typeclass-synthesized edges would expand the graph to millions of edges, dramatically increasing layout and browser rendering cost while obscuring macro-level mathematical structure under low-level algebraic and tactic plumbing.
3. **Modules here are fine-grained:** Across the **59,836** reachable modules in `src/`, the median module contains **6** declarations (mean `12.73`), and **10,034 modules (16.8%)** contain a single declaration. The module DAG therefore closely tracks theorem-level architecture while grouping small local helper lemmas together.

---

## 2. End-to-End Repeatable Pipeline

The visualization is generated deterministically from the Lean source tree with zero hardcoded module paths, directory names, layer counts, or fixed directory-to-color mappings. Rebuilding this version runs a single orchestrator command:

```bash
python3 analysis/build_all.py --version community-307cef33 --steps full_dag
```

Or directly via `build_full_dag.py` against SQLite:

```bash
python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/community-307cef33/data/graph.sqlite --out-dir analysis/versions/community-307cef33/full_dag
```

The pipeline executes five stages:

1. **Source Indexing (`analysis/build_index.py`):** Walks `src/` in sorted relative-path order, parses `import` statements, builds the deduplicated internal module import graph, and writes `graph.sqlite` and `meta.json`.
2. **Acyclicity Verification (`load_graph` + Kahn's topological sort):** Loads all reachable modules ordered deterministically by `(rel_path, id)` and runs Kahn's topological algorithm from roots ($\text{in\_degree} = 0$). If any import cycle exists, the pipeline aborts immediately with an error.
3. **Deterministic 3-Stage Sugiyama Layout (`compute_layout`):** Assigns integer layer coordinates $y(u)$ and continuous non-overlapping horizontal coordinates $x(u)$, then scales vertical spacing dynamically to preserve a readable widescreen aspect ratio.
4. **Graph Simplification & Multi-View Weighted Layouts (`build_collapsed_dag`, `compute_transitive_reduction`, `simplify_chains_and_leaves`):**
   - Applies the inventory-driven proof-frontier cut to contract peer-reviewed background proofs into **74 Literature Supernodes** (`existing`).
   - Computes exact transitive reduction (Hasse diagrams) on both the full DAG (`full_hasse`) and existing-theory DAG (`existing_hasse`), packing 1-bit-per-edge masks for zero-jump in-place toggling.
   - Runs a 2-phase fixed-point chain/leaf collapse (`simplify_chains_and_leaves`) across all four `(existing, hasse)` combinations (`full_simp`, `full_hasse_simp`, `existing_simp`, `existing_hasse_simp`), computing weighted Sugiyama layouts using edge weights $w_E = \text{mult} + \text{chain}$.
5. **Canonical Re-Indexing & `LDAG` v3 Packaging:** Re-indexes every node-bearing layout in `(y, x, sort_key)` order, packs typed arrays, LEB128 delta-varint CSR adjacency lists, 1-bit Hasse masks, sparse weighted-anchor records, and 1-bit-flagged weighted edge streams into a 4-byte-aligned `LDAG` v3 binary buffer, compresses deterministically (`gzip` with `mtime=0`), and emits [full_dag_data.js](full_dag_data.js) alongside [layout_summary.json](layout_summary.json).

---

## 3. Layout Algorithm

Drawing the complete import graph of **59,836** modules and **367,774** edges requires strict topological orientation (every edge pointing downward) while minimizing vertical edge spans and horizontal edge crossings.

### Stage 1: Bottom-Aligned Longest-Path Layering

First, module heights $h(u)$ from leaf modules ($\text{out\_degree} = 0$) are computed in reverse topological order:

$$h(u) = \begin{cases} 0 & \text{if } \text{out}(u) = \emptyset, \\ 1 + \max_{(u, v) \in E} h(v) & \text{otherwise.} \end{cases}$$

Setting initial vertical rank $y_0(u) = H_{\max} - h(u)$ places the root entry module (`Main`, $h = 93$) at $y = 0$ and guarantees $y_0(v) \ge y_0(u) + 1$ for every edge $(u, v) \in E$.

### Stage 2: Feasible $L_1$ Vertical Rank Tightening

Bottom-aligned layering leaves intermediate modules with fewer outgoing than incoming dependencies sitting deeper than necessary. To reduce total vertical edge length $\sum_{(u,v)\in E} (y(v) - y(u))$ while strictly preserving the DAG invariant $y(v) \ge y(u) + 1$, the generator runs up to 25 alternating topological and reverse-topological coordinate-descent sweeps.

At each node $u$, the feasible integer interval imposed by its neighbors is:

$$\ell(u) = \begin{cases} 0 & \text{if } \text{in}(u) = \emptyset, \\ \max_{(p, u) \in E} y(p) + 1 & \text{otherwise,} \end{cases} \qquad r(u) = \begin{cases} H_{\max} & \text{if } \text{out}(u) = \emptyset, \\ \min_{(u, c) \in E} y(c) - 1 & \text{otherwise.} \end{cases}$$

Since the local derivative of total edge span with respect to $y(u)$ is $|\text{in}(u)| - |\text{out}(u)|$:
- If $|\text{in}(u)| > |\text{out}(u)|$, $u$ moves to $\ell(u)$ (pulled upward toward its importers).
- If $|\text{out}(u)| > |\text{in}(u)|$, $u$ moves to $r(u)$ (pulled downward toward its dependencies).
- If $|\text{in}(u)| = |\text{out}(u)|$, $u$ moves to the rounded mean of its neighbors clamped to $[\ell(u), r(u)]$.

Across the full graph, these sweeps reduce mean vertical edge span from **16.340** layers to **15.095** layers, placing **66,253** edges on adjacent layers ($\Delta y = 1$) and **141,499** edges within $\Delta y \le 5$.

### Stage 3: Weighted Barycenter Ordering & Isotonic $L_2$ Placement

Nodes are grouped into layers $L_0, \dots, L_{93}$, initially sorted by `rel_path` and centered with unit spacing. The generator then executes 16 alternating top-down and bottom-up sweeps:

1. **Inverse-Span Weighted Barycenter:** For every node $u \in L_k$, its target horizontal position $\bar{x}(u)$ averages both incoming and outgoing neighbors weighted by $w(u, v) = |y(u) - y(v)|^{-1}$ so short-span edges pull more strongly than long-span cross-layer edges:

$$\bar{x}(u) = \frac{\sum_{v \in \text{in}(u) \cup \text{out}(u)} \frac{x(v)}{|y(u) - y(v)|}}{\sum_{v \in \text{in}(u) \cup \text{out}(u)} \frac{1}{|y(u) - y(v)|}}.$$

2. **Permutation & Relaxation:** During the first 10 sweeps, each layer is re-sorted by $(\bar{x}(u), \text{rel\_path}(u))$ to eliminate crossings; during the final sweeps, the layer ordering is held fixed while coordinates relax smoothly.
3. **Pool-Adjacent-Violators (PAV) Isotonic Projection:** Within each ordered layer $u_0, \dots, u_{m-1}$, coordinates are projected onto the non-overlap polytope $x(u_{i+1}) - x(u_i) \ge 1.0$ by solving the exact $O(m)$ isotonic $L_2$ regression problem $\min \sum_{i=0}^{m-1} (x_i - \bar{x}(u_i))^2$ via the Pool-Adjacent-Violators algorithm on $z_i = x_i - i$ with target $t_i = \bar{x}(u_i) - i$.

This stage reduces mean horizontal edge span $|\Delta x|$ from **255.935** units to **95.519** units, while enforcing a strict minimum horizontal gap of **1.0** world unit between adjacent nodes in every layer.

Finally, layer vertical spacing $\Delta y$ is computed dynamically from total horizontal span $W_x = x_{\max} - x_{\min}$ and layer count $K$ as $\Delta y = \text{clamp}\!\left(\frac{W_x}{1.85 \cdot (K - 1)},\, 4.0,\, 12.0\right)$, yielding $\Delta y = 10.7149$ and an overall aspect ratio of **1.85 : 1**.

---

## 4. Refactor-Resilience Guarantees

- **Zero Hardcoded Names or Counts:** Every top-level directory (`top_dir`) is discovered dynamically from `graph.sqlite`, sorted deterministically by `(-module_count, top_dir)`, and colored from a fixed high-contrast light-theme categorical palette (with a deterministic golden-angle HSL fallback beyond 10 directories).
- **Deterministic Tie-Breaking & Bit-Exact Output:** Node ordering ties break on `rel_path`, canonical IDs are sorted by `(layer, x, rel_path)`, and gzip compression uses `mtime=0`, ensuring repeated runs on unchanged sources emit byte-identical outputs.
- **Invariant Checks:** Across all 8 composable views, the generator verifies zero self-loops, exact topological completeness (`len(topo) == N`), strict downward edge monotonicity ($y(u) < y(v)$ and $\text{id}(u) < \text{id}(v)$), intra-layer non-overlap ($\Delta x \ge 1.0$), exact Hasse bitmask counts (`170,783` for `full_hasse`, `149,879` for `existing_hasse`), zero remaining unprotected simple leaves or `(1,1)` pass-through nodes after fixed-point simplification, and exact module conservation ($\sum_{v \in V} w(v) + \sum_{e \in E} \text{chain}(e) = 59,836$) before writing output.

---

## 5. Simplification Modes, Weights & `LDAG` v3 Architecture

The viewer provides three orthogonal, composable toggles that switch smoothly between **8 pre-verified graph views**:

1. **Collapse existing theory (`C`):** Contracts established peer-reviewed mathematical proofs into **74 Literature Supernodes**.
2. **Hide redundant imports (`H`):** Applies exact transitive reduction (the Hasse diagram), hiding shortcut import edges that are already implied by longer dependency paths.
3. **Collapse chains & leaves (`L`):** Folds private simple-leaf subtrees upward into weighted parent anchor nodes (`Anchor [w]`) and contracts pass-through `(1,1)` chains onto weighted dependency edges.

### 5.1 Existing-Theory Proof-Frontier Cut ("Collapse existing theory")

The **"Collapse existing theory"** toggle in [full_dag.html](full_dag.html) (keyboard shortcut `C`) lets readers hide subtrees of the Lean codebase proving already-established peer-reviewed mathematics while preserving every novel theorem, shared interface specification, and statement contract.

Following the identification methodology in [PUBLISHED_THEOREMS_INVENTORY.md](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md#methodology-identifying-collapsible-existing-theory-proof-subtrees), `build_full_dag.py`:

1. Parses audited peer-reviewed `Prop` identifiers and bold canonical literature titles from Sections 1–11 of the active inventory (excluding Section 12 project-specific statements and internal scaffolding).
2. Enforces the SQLite defining-module ancestor guard and scans final conclusion heads of `theorem`/`lemma` declarations while excluding `*/Definitions/*`, assumed hypothesis-bundle projections/dispatchers (`OpenImageCondition`, `OpenLiteratureStatements`, etc.), novel headline modules, and multi-topic re-export barrels.
3. Performs reachability from `Main` without crossing outgoing edges of detected proof roots so proof-only interiors are isolated without disconnecting active mathematical interfaces.

Modules unreachable from `Main` past the proof-frontier cut form the **proof-only interior** $C$ (`6,323` modules), while reached proof-root modules form the **frontier** $F$ (`291` modules). Grouping frontier roots into **74 Literature Supernodes** $S_T$ rendered as **diamond axiom sinks** ($\text{out\_degree} = 0$) and assigning every $v \in C$ via deterministic multi-source BFS yields a complete disjoint partition:

$$|A| + \sum_{T} |S_T| = 53,222 + 6,614 = 59,836.$$

Each supernode displays its canonical literature title and collapsed module count in brackets (for example, `PEL Shimura Toroidal Compactifications & Mumford Degeneration [1,343]`). Contracting parallel frontier imports from an active module $u \in A$ to $S_T$ induces edge multiplicity weights (**1,375** contracted supernode edges from **1,649** raw frontier imports, with **175** edges having $w \ge 2$, up to $w_{\max} = 7$).

### 5.2 Transitive Reduction ("Hide redundant imports" / Hasse Diagram)

Lean modules frequently `import` both a downstream module $B$ and an ancestor $C$ that $B$ already imports (`A -> B -> C` alongside shortcut `A -> C`).

The **"Hide redundant imports"** toggle (`H` hotkey) displays the DAG's **exact transitive reduction** (its Hasse diagram), keeping an edge $(u, v)$ if and only if no indirect directed path $u \to \dots \to v$ of length $\ge 2$ exists:

- **Algorithm (`compute_transitive_reduction`):** Processes nodes in topological order using striped arbitrary-precision integer bitsets (stripe width $B = 16{,}384$) to compute 1-step reachability $R_1(u)$ and $\ge 2$-step reachability $R_2(u) = \bigvee_{(u, v) \in E} R_1(v)$; edge $(u, v)$ is redundant iff $v \in R_2(u)$.
- **Edge Reduction (Full DAG):** Removes **196,991** redundant edges (`53.56%`), leaving **170,783** covering edges (`full_hasse`).
- **Edge Reduction (Existing-Theory DAG):** Removes **164,380** redundant edges (`52.31%`), leaving **149,879** covering edges (`existing_hasse`).
- **In-Place Zero-Jump Filtering:** When *Collapse chains & leaves* is off, toggling `H` keeps node coordinates fixed and swaps CSR edges using compact 1-bit masks (`full_hasse_mask` = `45,972` B; `existing_hasse_mask` = `39,283` B).

### 5.3 Chain & Simple-Leaf Collapse ("Collapse chains & leaves")

The **"Collapse chains & leaves"** toggle (`L` hotkey) runs `simplify_chains_and_leaves`, a deterministic 2-phase fixed-point contraction loop (on the base DAG removing **667** leaves and **2,361** chain nodes; after transitive reduction removing **1,319** leaves and **8,813** chain nodes):

1. **Phase 1 — Simple-Leaf Folding into Node Weight (`in = 1, out = 0`):** Iteratively peels every unprotected node $u$ with a single importer $p$ and zero internal dependencies upward into $p$, transferring node weight and any edge chain weight:

$$w(p) \leftarrow w(p) + w(u) + \text{chain}(p, u).$$

Private leaf-trees collapse into weighted anchor nodes (for instance, `ExistsMultiplicativeChartAtSplitPrime` absorbs `2` leaves and `11` chain modules to reach weight `14`). When *Collapse existing theory* is also active, all **74 Literature Supernodes** are protected from absorption so diamond landmarks remain visible.
2. **Phase 2 — Pass-Through `(1,1)` Chain Contraction into Edge Weight:** Iteratively contracts every unprotected `(1, 1)` node $u$ along $p \to u \to c$ into a direct edge $(p, c)$, merging parallel paths:

$$\text{mult}(p, c) \mathrel{+}= \max\!\big(\text{mult}(p, u),\, \text{mult}(u, c)\big), \qquad \text{chain}(p, c) \mathrel{+}= \text{chain}(p, u) + \text{chain}(u, c) + w(u).$$

The combined edge weight used for layout attraction and stroke rendering is $w_E(e) = \text{mult}(e) + \text{chain}(e)$.
3. **Fixed-Point Iteration & Module Conservation:** Phases 1 and 2 repeat until convergence (running *after* Hasse reduction when both `H` and `L` are active), preserving exact module conservation across every surviving view:

$$\sum_{v \in V} w(v) + \sum_{e \in E} \text{chain}(e) = 59,836.$$

### 5.4 Node Labeling & Weight Encoding (Option A)

- **Weighted Anchor Nodes (`Anchor [w]`):** Any active module with weight $w > 1$ renders with increased disc diameter ($w_{\text{base}} + 0.55 \ln(w)$) and an **inner white halo ring** (`alphaByte = 128`), labeled with its bold domain-colored `[w]` suffix.
- **Deep-Zoom Breakdown Subtitles (`zoom >= 55`):** Single-leaf absorption ($k = 1$) names the absorbed module directly; multi-module absorption summarizes `+k collapsed (L leaves, C chain)` alongside its directory path.
- **Weighted Edges & Badges:** Contracted edges scale in WebGL opacity, 2D stroke width ($\log_2 w_E$), deep-zoom arrowheads, and collision-free `×m` / `+c` / `×m +c` badges at `zoom >= 6`.

### 5.5 Compact Offline Payload (`LDAG` v3 in `full_dag_data.js`)

Because browser `fetch()` fails under `file://` CORS restrictions, `build_full_dag.py` embeds the gzipped 4-byte-aligned little-endian `LDAG` binary container as `window.__FULL_DAG_GZ_B64__` in `full_dag_data.js` and decompresses it client-side via `DecompressionStream("gzip")`:

- **Container Sizes:** `7,591,928` raw bytes → `4,219,851` B gzipped (`mtime=0`) → `5,626,501` B JS payload (`format_version = 3`).
- **Base & Collapsed Sections (`v1 + v2`):** Header JSON, full-graph typed arrays & delta-varint CSR `edge_buf` (`752,378` B), collapsed supernode metadata (`c_super_edges_buf` = `58,363` B), and `0` pruned dead-edge pairs.
- **Hasse Bitmasks & 4 Simplified Views (`v3`):** `full_hasse_mask` (`45,972` B), `existing_hasse_mask` (`39,283` B), and 1-bit-flagged LEB128 CSR edge streams (`2,205,438` B across all 4 simplified views).

---

## 6. Viewer Legend and Visual Encoding

The interactive viewer ([full_dag.html](full_dag.html)) displays a collapsible corner legend populated dynamically from `header.groups` (sorted by descending module count) and a **Max depth** BFS filter bar:

| Top-Level Directory | Modules | Hex | Color |
| :--- | ---: | :--- | :--- |
| `Development` | 41,263 | `#2563eb` | Blue |
| `Formalism` | 9,901 | `#ea580c` | Orange |
| `GroundTheory` | 5,217 | `#ca8a04` | Gold / Amber |
| `ReciprocityTheory` | 2,393 | `#0d9488` | Teal |
| `CompanionTheory` | 685 | `#059669` | Emerald green |
| `PositivityTheory` | 226 | `#c026d3` | Fuchsia / Magenta |
| `Lemmata` | 149 | `#7c3aed` | Violet / Purple |
| `(root)` | 2 | `#64748b` | Slate gray |

- **Future Refactor Fallback:** Beyond 10 top-level directories, `group_color()` assigns deterministic golden-angle HSL colors.
- **Top-Right Toggle Bar & Controls:** **Collapse existing theory (`C`)**, **Hide redundant imports (`H`)**, **Collapse chains & leaves (`L`)**, plus the **Max depth** shortest-path BFS depth control (`[` / `]` hotkeys and `All` toggle) filtering nodes and edges by distance from `Main` without altering coordinates.

---

## 7. Current Graph & Layout Summary

### 8-View Summary Matrix

| View (`Existing`, `Hasse`, `Chains/Leaves`) | Nodes | Edges | Layers | Layer Spacing | Avg $\Delta y$ | Avg $\lvert\Delta x\rvert$ | Weighted Anchors ($w > 1$) | Weighted Edges ($w_E \ge 2$) | Module Conservation |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Full DAG** (`F, F, F`) | 59,836 | 367,774 | 94 | 10.7149 | 15.095 | 95.519 | — | — | `59,836 + 0 = 59,836` |
| **Full + Hide redundant imports** (`F, T, F`) | 59,836 | 170,783 | 94 | 10.7149 | *(in-place)* | *(in-place)* | — | — | `59,836 + 0 = 59,836` |
| **Existing Theory** (`T, F, F`) | 53,296 | 314,259 | 84 | 11.4842 | 13.551 | 88.123 | 74 supernodes | 175 | `59,836 + 0 = 59,836` |
| **Existing + Hide redundant imports** (`T, T, F`) | 53,296 | 149,879 | 84 | 11.4842 | *(in-place)* | *(in-place)* | 74 supernodes | *(in-place)* | `59,836 + 0 = 59,836` |
| **Full + Chains & Leaves** (`F, F, T`) | 56,808 | 363,081 | 94 | 10.1192 | 15.225 | 91.813 | 526 (`max w=13`) | 1,542 (`max=57`) | `57,502 + 2,334 = 59,836` |
| **Full + Hasse + Chains & Leaves** (`F, T, T`) | 49,704 | 159,232 | 91 | 9.1231 | 8.412 | 75.646 | 884 (`max w=14`) | 6,707 (`max=60`) | `50,916 + 8,920 = 59,836` |
| **Existing + Chains & Leaves** (`T, F, T`) | 50,299 | 309,708 | 84 | 10.8694 | 13.685 | 84.522 | 535 + 74 super | 1,724 (`max=57`) | `57,550 + 2,286 = 59,836` |
| **Existing + Hasse + Chains & Leaves** (`T, T, T`) | 43,797 | 139,112 | 80 | 9.8820 | 7.885 | 69.627 | 846 + 74 super | 6,332 (`max=60`) | `51,497 + 8,339 = 59,836` |

### Top Weighted Anchor Nodes & Contracted Edges (`full_hasse_simp`)

| Top Weighted Anchor Node (`Anchor [w]`) | Weight $w$ | Breakdown (`leaves` / `chains`) | Representative Absorbed Leaf |
| :--- | ---: | :---: | :--- |
| `JetHarmonics/ExistsMultiplicativeChartAtSplitPrime` | 14 | 2 / 11 | `PowerSeriesHasSumAt` |
| `DivisorProofs/PicDivisibleDedekindFiniteTypeAlgClosed` | 14 | 13 / 0 | `NewtonPowerSeriesSurjectiveLinearizationSolution` |
| `HermitianForms/LiftStep` | 13 | 12 / 0 | `DistribHaarCharEqOneOfValuationEqOne` |
| `HermitianForms/Core` | 13 | 12 / 0 | `ComapMulVecCompactOpen` |
| `LocalFiniteness/InjectiveHolomorphicJacobianNeZeroHolds` | 13 | 12 / 0 | `StGenericNoetherNormalisation` |

| Top Contracted Edge (`src → dst`) | Combined Weight $w_E$ | Multiplicity (`×mult`) | Contracted Chain (`+chain`) |
| :--- | ---: | ---: | ---: |
| `IsolateSpecHolds → IsolateSpec` | 60 | ×30 | +30 |
| `TTypeEx → NonzeroLeviEigenvectorExists` | 48 | ×24 | +24 |
| `RsPoleOfInputs → ColumnConjugationMeasure` | 48 | ×24 | +24 |
| `ExistsChartLiftOfFiniteCover → LiftFactorization` | 46 | ×23 | +23 |
| `Imports → StatementsSchur` | 43 | ×21 | +22 |

### Full DAG Summary

| Metric | Value |
| :--- | ---: |
| Total Lean Modules (Nodes) | 59,836 |
| Total Internal Import Edges | 367,774 |
| Declarations Indexed (Reachable) | 761,777 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers | 94 (`layer 0`..`93`) |
| Layer Width (min / median / p95 / max) | 1 / 458 / 1,652 / 1,842 |
| Vertical Layer Spacing (`layer_dy`) | 10.7149 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 16.340 $\to$ 15.095 |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 255.935 $\to$ 95.519 |
| Adjacent / Short-Span Edges ($\Delta y = 1$ / $\Delta y \le 5$) | 66,253 / 141,499 |
| World Aspect Ratio | 1.85 : 1 |
| `LDAG` v3 Payload (`full_dag_data.js`) | 5,626,501 bytes (`4,219,851` B gzip / `7,591,928` B raw) |

### Collapsed DAG Summary ("Collapse Existing Theory")

| Metric | Value |
| :--- | ---: |
| Collapsed View Nodes (`active + supernodes`) | 53,296 (`53,222` active + `74` literature supernodes) |
| Collapsed Modules Total (`frontier + interior`) | 6,614 (`11.05%`: `291` frontier + `6,323` interior) |
| Collapsed View Edges (`active + supernode`) | 314,259 (`312,884` active + `1,375` supernode edges) |
| Raw Frontier Imports Contracted / Max Weight | 1,649 raw imports / $w_{\max} = 7$ (`175` edges with $w \ge 2$) |
| Targeted Dead Bridge Imports Pruned | 0 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers (`c_num_layers`) | 84 (`layer 0`..`83`) |
| Collapsed Layer Width (min / median / p95 / max) | 1 / 739 / 1,504 / 1,761 |
| Vertical Layer Spacing (`c_layer_dy`) | 11.4842 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 14.769 $\to$ 13.551 (`58,824` at $\Delta y = 1$) |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 234.869 $\to$ 88.123 |
| Min Intra-Layer Gap / World Aspect Ratio | 1.0 / 1.85 : 1 |

### Discovered Top-Level Domains & Collapse Breakdown

| Top-Level Directory | Total Modules | Active | Collapsed | Collapsed % | Palette Color | Layer Range (min / med / max) | Mean $x$ |
| :--- | ---: | ---: | ---: | ---: | :---: | :---: | ---: |
| `Development` | 41,263 | 35,988 | 5,275 | 12.8% | `#2563eb` | 1 / 65 / 93 | -268.49 |
| `Formalism` | 9,901 | 9,813 | 88 | 0.9% | `#ea580c` | 29 / 75 / 93 | 164.90 |
| `GroundTheory` | 5,217 | 4,211 | 1,006 | 19.3% | `#ca8a04` | 32 / 87 / 93 | 484.80 |
| `ReciprocityTheory` | 2,393 | 2,337 | 56 | 2.3% | `#0d9488` | 27 / 86 / 93 | 333.21 |
| `CompanionTheory` | 685 | 525 | 160 | 23.4% | `#059669` | 24 / 74 / 93 | -321.63 |
| `PositivityTheory` | 226 | 197 | 29 | 12.8% | `#c026d3` | 14 / 58 / 93 | 166.96 |
| `Lemmata` | 149 | 149 | 0 | 0.0% | `#7c3aed` | 51 / 86 / 93 | 173.70 |
| `(root)` | 2 | 2 | 0 | 0.0% | `#64748b` | 0 / 88 / 88 | -229.41 |

### Top 20 Collapsed Literature Supernodes

| Literature Supernode Title | Owned Collapsed Modules | Full Cone Modules | Frontier Roots | Contracted In-Edges | Raw Imports |
| :--- | ---: | ---: | ---: | ---: | ---: |
| PEL Shimura Toroidal Compactifications & Mumford Degeneration | 1,343 | 1,398 | 2 | 10 | 11 |
| Ichino / Kudla–Rallis Convergent Siegel–Weil | 882 | 899 | 4 | 3 | 5 |
| Poincaré–Lelong Current Identity | 547 | 547 | 1 | 1 | 1 |
| BLGGT / Caraiani Strong Local–Global Compatibility | 405 | 501 | 3 | 8 | 9 |
| Moriwaki Arithmetic Bigness & Hilbert–Samuel | 298 | 298 | 1 | 1 | 1 |
| Unitary-to-GLₙ Isobaric Base Change | 281 | 294 | 5 | 14 | 14 |
| Abelian de Rham, Crystalline & Gauss–Manin Comparisons | 226 | 239 | 14 | 47 | 65 |
| Chern–Weil Theory & Mumford Proportionality | 195 | 221 | 2 | 13 | 13 |
| Finiteness of Twisted Étale Cohomology | 161 | 161 | 2 | 2 | 2 |
| Global Galois Euler Characteristic & Cohomological Dimension | 158 | 209 | 3 | 10 | 12 |
| Kawamata–Viehweg, Nadel Vanishing & Angehrn–Siu | 154 | 179 | 3 | 1 | 3 |
| Harish-Chandra Discrete Series Classification | 133 | 153 | 12 | 67 | 83 |
| Bhatt–Scholze Prismatic F-Crystals | 130 | 143 | 2 | 3 | 4 |
| Arithmetic Hilbert–Samuel, Volume & Absolute Siegel | 118 | 199 | 2 | 4 | 4 |
| Fargues–Tate Exactness & Hodge–Tate Map | 112 | 112 | 1 | 1 | 1 |
| Gillet–Soulé Arithmetic Intersection & Chow Heights | 102 | 129 | 5 | 14 | 18 |
| Bernstein–Zelevinsky Smooth GLₙ(k) Theory | 101 | 139 | 22 | 65 | 96 |
| Zelevinsky–Langlands Segment Classification | 97 | 122 | 10 | 22 | 31 |
| Grothendieck–Messing Deformation & Dieudonné Crystals | 94 | 101 | 6 | 41 | 56 |
| Jacquet–Shalika Rigidity & Bounds | 87 | 93 | 5 | 71 | 77 |

### Top 15 Most Imported Hub Modules

| Top Imported Hub Module | In-Degree | Out-Degree | Layer |
|---|---:|---:|---:|
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsCompletedStrictHens.lean` | 1,138 | 0 | 93 |
| `Formalism/LocalToGlobal/IndefiniteReal/LinksDefs.lean` | 986 | 8 | 71 |
| `Formalism/SharpRestriction/LevelLetterCocycles/DataNLoc.lean` | 895 | 1 | 90 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/CubicalStructures/CubeSymmetricSwapFirst.lean` | 813 | 0 | 93 |
| `Development/AbelianVarietyTheory/BlockTheory/DivisorBase/WeilTensorModels.lean` | 713 | 5 | 69 |
| `Formalism/SharpRestriction/GlobalSchurBounds/GeneralLinearActions/GenusMassVolumes.lean` | 611 | 1 | 92 |
| `Formalism/LocalToGlobal/IndefiniteReal/LocalNewformFunction.lean` | 596 | 1 | 74 |
| `Formalism/LocalToGlobal/ProjectiveLattices/ErealAddIInf.lean` | 546 | 0 | 91 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean` | 540 | 3 | 88 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/DiscreteValuationRings/LBPull.lean` | 521 | 2 | 91 |
| `Development/AbelianVarietyTheory/Proofs/FoundationProofs/ExistsContinuousPadic.lean` | 500 | 3 | 86 |
| `Formalism/SharpRestriction/CuspSpanNormBounds/Point.lean` | 484 | 0 | 93 |
| `Formalism/LocalRingCardinality/DataTheta.lean` | 458 | 2 | 85 |
| `Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean` | 453 | 2 | 90 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/CocycleRightZeroThd.lean` | 450 | 0 | 93 |

---

## 8. Regenerating After a Lean Refactor

```bash
# 1. Rebuild only this version's full DAG payload & sync portal reports
python3 analysis/build_all.py --version community-307cef33 --steps index,inventory,full_dag

# 2. Or re-run build_full_dag.py standalone and regenerate HTML reports
python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/community-307cef33/data/graph.sqlite --out-dir analysis/versions/community-307cef33/full_dag --version-label community-307cef33
node analysis/render_reports.js

# 3. Open the local analysis portal or viewer
python3 -m http.server 8000 --directory analysis
```
