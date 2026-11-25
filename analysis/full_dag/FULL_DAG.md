# Full Lean Module Dependency DAG (`community-9211277d`)

This document describes the repeatable layout pipeline, binary data packaging, graph-simplification modes, and WebGL visualization behind the interactive full-graph viewer:

- **Interactive Viewer:** [full_dag.html](full_dag.html) (pan and zoom across all modules and import edges, with a **Layout** picker switching between Sugiyama and depth-based layouts, three composable simplification switches: **Collapse existing theory** `C`, **Hide redundant imports** `H`, and **Collapse chains & leaves** `L`, plus the **Max depth** BFS filter `[` / `]`)
- **Layout Generator:** [build_full_dag.py](build_full_dag.py)
- **Layout Summary:** [layout_summary.json](layout_summary.json)
- **SQLite Indexer:** [build_index.py](../build_index.py)
- **Existing-Theory Inventory & Methodology:** [PUBLISHED_THEOREMS_INVENTORY.html](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.html) ([Markdown](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md))

> **Direction Convention:** Every node represents a `.lean` module under `src`. A directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Top-level theorem modules sit at the top (`layer 0`), and foundational definitions and leaf modules sit below (`layer 1..53`).

---

## 1. Why Modules Rather Than Individual Statements?

In Lean 4, a **module** corresponds 1-to-1 with a single `.lean` source file under `src/` (the compilation unit that produces one `.olean` binary). For instance, `src/Main.lean` is module `Main`, and `src/New/Main.lean` is module `New.Main`. Each module begins with explicit `import` headers declaring its dependencies, and because Lean forbids circular imports, the module import graph is guaranteed to be a strict DAG.

Inside those modules live individual **declarations** (`theorem`, `lemma`, `def`, `structure`, `class`, `inductive`, `abbrev`, `instance`). A finer-grained **declaration-level DAG**—linking every declaration to the exact constants referenced in its type and proof term—is not tracked here for three reasons:

1. **Accurate extraction requires full compilation:** Lean 4 proofs rely heavily on tactics (`simp`, `linarith`, `ring`, `aesop`, etc.), typeclass synthesis, coercions, and `open`ed namespaces, so many dependencies never appear explicitly by name in raw `.lean` source text. Recovering true declaration-level edges requires compiling the entire codebase to `.olean` files and inspecting Lean's elaborated `Environment` (for example, `Expr.getUsedConstants` on each `ConstantInfo`). By contrast, module `import` statements are explicit syntax at the top of every file, allowing [build_index.py](../build_index.py) to extract the exact module DAG deterministically from `src/` using only Python.
2. **Scale and architectural clarity:** Across reachable modules, the codebase contains **23,235** declarations (28.9× the **803** modules). Including tactic-elaborated and typeclass-synthesized edges would expand the graph to millions of edges, dramatically increasing layout and browser rendering cost while obscuring macro-level mathematical structure under low-level algebraic and tactic plumbing.
3. **Modules here are fine-grained:** Across the **803** reachable modules in `src/`, the median module contains **26** declarations (mean `28.94`), and **5 modules (0.6%)** contain a single declaration. The module DAG therefore closely tracks theorem-level architecture while grouping small local helper lemmas together.

---

## 2. End-to-End Repeatable Pipeline

The visualization is generated deterministically from the Lean source tree with zero hardcoded module paths, directory names, layer counts, or fixed directory-to-color mappings. Rebuilding this version runs a single orchestrator command:

```bash
python3 analysis/build_all.py --version community-9211277d --steps full_dag
```

Or directly via `build_full_dag.py` against SQLite:

```bash
python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/community-9211277d/data/graph.sqlite --out-dir analysis/versions/community-9211277d/full_dag
```

The pipeline executes five stages:

1. **Source Indexing (`analysis/build_index.py`):** Walks `src/` in sorted relative-path order, parses `import` statements, builds the deduplicated internal module import graph, and writes `graph.sqlite` and `meta.json`.
2. **Acyclicity Verification (`load_graph` + Kahn's topological sort):** Loads all reachable modules ordered deterministically by `(rel_path, id)` and runs Kahn's topological algorithm from roots ($\text{in\_degree} = 0$). If any import cycle exists, the pipeline aborts immediately with an error.
3. **Deterministic 3-Stage Sugiyama Layout (`compute_layout`):** Assigns integer layer coordinates $y(u)$ and continuous non-overlapping horizontal coordinates $x(u)$, then scales vertical spacing dynamically to preserve a readable widescreen aspect ratio.
4. **Graph Simplification & Multi-View Weighted Layouts (`build_collapsed_dag`, `compute_transitive_reduction`, `simplify_chains_and_leaves`):**
   - Applies the inventory-driven proof-frontier cut to contract peer-reviewed background proofs into **16 Literature Supernodes** (`existing`).
   - Computes exact transitive reduction (Hasse diagrams) on both the full DAG (`full_hasse`) and existing-theory DAG (`existing_hasse`), packing 1-bit-per-edge masks for zero-jump in-place toggling.
   - Runs a 2-phase fixed-point chain/leaf collapse (`simplify_chains_and_leaves`) across all four `(existing, hasse)` combinations (`full_simp`, `full_hasse_simp`, `existing_simp`, `existing_hasse_simp`), computing weighted Sugiyama layouts using edge weights $w_E = \text{mult} + \text{chain}$.
5. **Canonical Re-Indexing & `LDAG` v3 Packaging:** Re-indexes every node-bearing layout in `(y, x, sort_key)` order, packs typed arrays, LEB128 delta-varint CSR adjacency lists, 1-bit Hasse masks, sparse weighted-anchor records, and 1-bit-flagged weighted edge streams into a 4-byte-aligned `LDAG` v3 binary buffer, compresses deterministically (`gzip` with `mtime=0`), and emits [full_dag_data.js](full_dag_data.js) alongside [layout_summary.json](layout_summary.json).

---

## 3. Layout Algorithm

Drawing the complete import graph of **803** modules and **1,733** edges requires strict topological orientation (every edge pointing downward) while minimizing vertical edge spans and horizontal edge crossings.

### Stage 1: Bottom-Aligned Longest-Path Layering

First, module heights $h(u)$ from leaf modules ($\text{out\_degree} = 0$) are computed in reverse topological order:

$$h(u) = \begin{cases} 0 & \text{if } \text{out}(u) = \emptyset, \\ 1 + \max_{(u, v) \in E} h(v) & \text{otherwise.} \end{cases}$$

Setting initial vertical rank $y_0(u) = H_{\max} - h(u)$ places the root entry module (`Main`, $h = 53$) at $y = 0$ and guarantees $y_0(v) \ge y_0(u) + 1$ for every edge $(u, v) \in E$.

### Stage 2: Feasible $L_1$ Vertical Rank Tightening

Bottom-aligned layering leaves intermediate modules with fewer outgoing than incoming dependencies sitting deeper than necessary. To reduce total vertical edge length $\sum_{(u,v)\in E} (y(v) - y(u))$ while strictly preserving the DAG invariant $y(v) \ge y(u) + 1$, the generator runs up to 25 alternating topological and reverse-topological coordinate-descent sweeps.

At each node $u$, the feasible integer interval imposed by its neighbors is:

$$\ell(u) = \begin{cases} 0 & \text{if } \text{in}(u) = \emptyset, \\ \max_{(p, u) \in E} y(p) + 1 & \text{otherwise,} \end{cases} \qquad r(u) = \begin{cases} H_{\max} & \text{if } \text{out}(u) = \emptyset, \\ \min_{(u, c) \in E} y(c) - 1 & \text{otherwise.} \end{cases}$$

Since the local derivative of total edge span with respect to $y(u)$ is $|\text{in}(u)| - |\text{out}(u)|$:
- If $|\text{in}(u)| > |\text{out}(u)|$, $u$ moves to $\ell(u)$ (pulled upward toward its importers).
- If $|\text{out}(u)| > |\text{in}(u)|$, $u$ moves to $r(u)$ (pulled downward toward its dependencies).
- If $|\text{in}(u)| = |\text{out}(u)|$, $u$ moves to the rounded mean of its neighbors clamped to $[\ell(u), r(u)]$.

Across the full graph, these sweeps reduce mean vertical edge span from **4.241** layers to **3.825** layers, placing **807** edges on adjacent layers ($\Delta y = 1$) and **1,363** edges within $\Delta y \le 5$.

### Stage 3: Weighted Barycenter Ordering & Isotonic $L_2$ Placement

Nodes are grouped into layers $L_0, \dots, L_{53}$, initially sorted by `rel_path` and centered with unit spacing. The generator then executes 16 alternating top-down and bottom-up sweeps:

1. **Inverse-Span Weighted Barycenter:** For every node $u \in L_k$, its target horizontal position $\bar{x}(u)$ averages both incoming and outgoing neighbors weighted by $w(u, v) = |y(u) - y(v)|^{-1}$ so short-span edges pull more strongly than long-span cross-layer edges:

$$\bar{x}(u) = \frac{\sum_{v \in \text{in}(u) \cup \text{out}(u)} \frac{x(v)}{|y(u) - y(v)|}}{\sum_{v \in \text{in}(u) \cup \text{out}(u)} \frac{1}{|y(u) - y(v)|}}.$$

2. **Permutation & Relaxation:** During the first 10 sweeps, each layer is re-sorted by $(\bar{x}(u), \text{rel\_path}(u))$ to eliminate crossings; during the final sweeps, the layer ordering is held fixed while coordinates relax smoothly.
3. **Pool-Adjacent-Violators (PAV) Isotonic Projection:** Within each ordered layer $u_0, \dots, u_{m-1}$, coordinates are projected onto the non-overlap polytope $x(u_{i+1}) - x(u_i) \ge 1.0$ by solving the exact $O(m)$ isotonic $L_2$ regression problem $\min \sum_{i=0}^{m-1} (x_i - \bar{x}(u_i))^2$ via the Pool-Adjacent-Violators algorithm on $z_i = x_i - i$ with target $t_i = \bar{x}(u_i) - i$.

This stage reduces mean horizontal edge span $|\Delta x|$ from **4.462** units to **2.564** units, while enforcing a strict minimum horizontal gap of **1.0** world unit between adjacent nodes in every layer.

Finally, layer vertical spacing $\Delta y$ is computed dynamically from total horizontal span $W_x = x_{\max} - x_{\min}$ and layer count $K$ as $\Delta y = \text{clamp}\!\left(\frac{W_x}{1.85 \cdot (K - 1)},\, 4.0,\, 12.0\right)$, yielding $\Delta y = 4.0000$ and an overall aspect ratio of **0.15 : 1**.

### Alternative Depth-Based Layouts (Client-Side Layout Picker)

Because the default Sugiyama layout bottom-aligns nodes to leaves and then tightens vertical ranks by $L_1$ edge length, modules at the same distance from `Main` can appear at different heights. The viewer's **Layout** picker in [full_dag.html](full_dag.html) lets readers switch on demand between three layout mechanisms across any active simplification mode:

1. **Sugiyama (L1 tightened)** *(default)*: The precomputed 3-stage layout described above, minimizing vertical edge span and horizontal crossings.
2. **Depth (BFS from root):** Assigns every module $u$ to the horizontal row equal to its shortest-path BFS distance $d_{\text{BFS}}(u)$ from root modules ($\text{in\_degree} = 0$, i.e., `Main` at row `0`, direct imports at row `1`, etc.). All modules at the same BFS depth sit at the exact same vertical height, aligning 1-to-1 with the **Max depth** filter slider (so filtering to depth $\le k$ displays rows `0..k`). Note that shared low-level utilities imported near the root may have edges connecting to the same or shallower BFS rows.
3. **Depth (longest path):** Assigns every module $u$ to its topological longest-path depth from roots:

$$d_{\text{LP}}(u) = \begin{cases} 0 & \text{if } \text{in}(u) = \emptyset, \\ 1 + \max_{(p, u) \in E} d_{\text{LP}}(p) & \text{otherwise.} \end{cases}$$

All modules at the same DAG depth sit at the exact same vertical height while preserving strict downward orientation ($d_{\text{LP}}(v) \ge d_{\text{LP}}(u) + 1$) on every edge.

For both depth layouts, horizontal coordinates $x(u)$ are computed on demand in the browser and cached per `(view, layout)` for visual clarity:
- **Warm-Started Barycenter Sweeps:** Each depth row is initialized from the Sugiyama $x$-ordering and refined with alternating top-down and bottom-up inverse-span weighted barycenter sweeps (using denominator $\max(1, |y(u) - y(v)|)$ so same-depth edges in BFS mode pull neighbors together cleanly, and weighting by $1 + \log_2 w_E$ on weighted/collapsed views).
- **Non-Overlapping PAV Projection & Aspect Ratio:** After each sweep, every depth row is projected onto $x(u_{i+1}) - x(u_i) \ge 1.0$ via the exact $O(m)$ Pool-Adjacent-Violators (PAV) isotonic $L_2$ solver, centered around $x = 0$, and assigned dynamic vertical row spacing $\Delta y = \text{clamp}\!\left(\frac{W_x}{1.85 \cdot (K - 1)},\, 4.0,\, \max(12.0,\, 0.45\, W_x)\right)$ so even shallow BFS-depth layouts retain a readable `1.85 : 1` aspect ratio.

---

## 4. Refactor-Resilience Guarantees

- **Zero Hardcoded Names or Counts:** Every top-level directory (`top_dir`) is discovered dynamically from `graph.sqlite`, sorted deterministically by `(-module_count, top_dir)`, and colored from a fixed high-contrast light-theme categorical palette (with a deterministic golden-angle HSL fallback beyond 10 directories).
- **Deterministic Tie-Breaking & Bit-Exact Output:** Node ordering ties break on `rel_path`, canonical IDs are sorted by `(layer, x, rel_path)`, and gzip compression uses `mtime=0`, ensuring repeated runs on unchanged sources emit byte-identical outputs.
- **Invariant Checks:** Across all 8 composable views, the generator verifies zero self-loops, exact topological completeness (`len(topo) == N`), strict downward edge monotonicity ($y(u) < y(v)$ and $\text{id}(u) < \text{id}(v)$), intra-layer non-overlap ($\Delta x \ge 1.0$), exact Hasse bitmask counts (`1,733` for `full_hasse`, `616` for `existing_hasse`), zero remaining unprotected simple leaves or `(1,1)` pass-through nodes after fixed-point simplification, and exact module conservation ($\sum_{v \in V} w(v) + \sum_{e \in E} \text{chain}(e) = 803$) before writing output.

---

## 5. Simplification Modes, Weights & `LDAG` v3 Architecture

The viewer provides three orthogonal, composable toggles that switch smoothly between **8 pre-verified graph views**:

1. **Collapse existing theory (`C`):** Contracts established peer-reviewed mathematical proofs into **16 Literature Supernodes**.
2. **Hide redundant imports (`H`):** Applies exact transitive reduction (the Hasse diagram), hiding shortcut import edges that are already implied by longer dependency paths.
3. **Collapse chains & leaves (`L`):** Folds private simple-leaf subtrees upward into weighted parent anchor nodes (`Anchor [w]`) and contracts pass-through `(1,1)` chains onto weighted dependency edges.

### 5.1 Existing-Theory Proof-Frontier Cut ("Collapse existing theory")

The **"Collapse existing theory"** toggle in [full_dag.html](full_dag.html) (keyboard shortcut `C`) lets readers hide subtrees of the Lean codebase proving already-established peer-reviewed mathematics while preserving every novel theorem, shared interface specification, and statement contract.

Following the identification methodology in [PUBLISHED_THEOREMS_INVENTORY.md](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md#methodology-identifying-collapsible-existing-theory-proof-subtrees), `build_full_dag.py`:

1. Detects the clean `New/` vs. `Lib/` separation in `src/`, where `Lib/` holds background mathematical theories classed as known in the literature and imports zero modules from `New/`.
2. Places the frontier cut at the `New/ → Lib/` boundary, keeping `Main.lean`, `Statements.lean`, and every `New/*` module active while grouping all `Lib/` modules by `Lib/<Subsystem>` into Literature Supernodes.
3. Performs reachability from `Main` without crossing outgoing edges of the `Lib/` frontier so each subsystem's internal dependency cone contracts cleanly behind its diamond supernode.

Modules unreachable from `Main` past the proof-frontier cut form the **proof-only interior** $C$ (`344` modules), while reached proof-root modules form the **frontier** $F$ (`151` modules). Grouping frontier roots into **16 Literature Supernodes** $S_T$ rendered as **diamond axiom sinks** ($\text{out\_degree} = 0$) and assigning every $v \in C$ via deterministic multi-source BFS yields a complete disjoint partition:

$$|A| + \sum_{T} |S_T| = 308 + 495 = 803.$$

Each supernode displays its canonical literature title and collapsed module count in brackets (for example, `Lib: Galois Representations [119]`). Contracting parallel frontier imports from an active module $u \in A$ to $S_T$ induces edge multiplicity weights (**183** contracted supernode edges from **208** raw frontier imports, with **21** edges having $w \ge 2$, up to $w_{\max} = 3$).

### 5.2 Transitive Reduction ("Hide redundant imports" / Hasse Diagram)

Lean modules frequently `import` both a downstream module $B$ and an ancestor $C$ that $B$ already imports (`A -> B -> C` alongside shortcut `A -> C`).

The **"Hide redundant imports"** toggle (`H` hotkey) displays the DAG's **exact transitive reduction** (its Hasse diagram), keeping an edge $(u, v)$ if and only if no indirect directed path $u \to \dots \to v$ of length $\ge 2$ exists:

- **Algorithm (`compute_transitive_reduction`):** Processes nodes in topological order using striped arbitrary-precision integer bitsets (stripe width $B = 16{,}384$) to compute 1-step reachability $R_1(u)$ and $\ge 2$-step reachability $R_2(u) = \bigvee_{(u, v) \in E} R_1(v)$; edge $(u, v)$ is redundant iff $v \in R_2(u)$.
- **Edge Reduction (Full DAG):** Removes **0** redundant edges (`0.00%`), leaving **1,733** covering edges (`full_hasse`).
- **Edge Reduction (Existing-Theory DAG):** Removes **93** redundant edges (`13.12%`), leaving **616** covering edges (`existing_hasse`).
- **In-Place Zero-Jump Filtering:** When *Collapse chains & leaves* is off, toggling `H` keeps node coordinates fixed and swaps CSR edges using compact 1-bit masks (`full_hasse_mask` = `217` B; `existing_hasse_mask` = `89` B).

### 5.3 Chain & Simple-Leaf Collapse ("Collapse chains & leaves")

The **"Collapse chains & leaves"** toggle (`L` hotkey) runs `simplify_chains_and_leaves`, a deterministic 2-phase fixed-point contraction loop (on the base DAG removing **2** leaves and **135** chain nodes; after transitive reduction removing **2** leaves and **135** chain nodes):

1. **Phase 1 — Simple-Leaf Folding into Node Weight (`in = 1, out = 0`):** Iteratively peels every unprotected node $u$ with a single importer $p$ and zero internal dependencies upward into $p$, transferring node weight and any edge chain weight:

$$w(p) \leftarrow w(p) + w(u) + \text{chain}(p, u).$$

Private leaf-trees collapse into weighted anchor nodes (for instance, `OneSidedBound` absorbs `1` leaves and `0` chain modules to reach weight `2`). When *Collapse existing theory* is also active, all **16 Literature Supernodes** are protected from absorption so diamond landmarks remain visible.
2. **Phase 2 — Pass-Through `(1,1)` Chain Contraction into Edge Weight:** Iteratively contracts every unprotected `(1, 1)` node $u$ along $p \to u \to c$ into a direct edge $(p, c)$, merging parallel paths:

$$\text{mult}(p, c) \mathrel{+}= \max\!\big(\text{mult}(p, u),\, \text{mult}(u, c)\big), \qquad \text{chain}(p, c) \mathrel{+}= \text{chain}(p, u) + \text{chain}(u, c) + w(u).$$

The combined edge weight used for layout attraction and stroke rendering is $w_E(e) = \text{mult}(e) + \text{chain}(e)$.
3. **Fixed-Point Iteration & Module Conservation:** Phases 1 and 2 repeat until convergence (running *after* Hasse reduction when both `H` and `L` are active), preserving exact module conservation across every surviving view:

$$\sum_{v \in V} w(v) + \sum_{e \in E} \text{chain}(e) = 803.$$

### 5.4 Node Labeling & Weight Encoding (Option A)

- **Weighted Anchor Nodes (`Anchor [w]`):** Any active module with weight $w > 1$ renders with increased disc diameter ($w_{\text{base}} + 0.55 \ln(w)$) and an **inner white halo ring** (`alphaByte = 128`), labeled with its bold domain-colored `[w]` suffix.
- **Deep-Zoom Breakdown Subtitles (`zoom >= 55`):** Single-leaf absorption ($k = 1$) names the absorbed module directly; multi-module absorption summarizes `+k collapsed (L leaves, C chain)` alongside its directory path.
- **Weighted Edges & Badges:** Contracted edges scale in WebGL opacity, 2D stroke width ($\log_2 w_E$), deep-zoom arrowheads, and collision-free `×m` / `+c` / `×m +c` badges at `zoom >= 6`.

### 5.5 Compact Offline Payload (`LDAG` v3 in `full_dag_data.js`)

Because browser `fetch()` fails under `file://` CORS restrictions, `build_full_dag.py` embeds the gzipped 4-byte-aligned little-endian `LDAG` binary container as `window.__FULL_DAG_GZ_B64__` in `full_dag_data.js` and decompresses it client-side via `DecompressionStream("gzip")`:

- **Container Sizes:** `61,696` raw bytes → `28,397` B gzipped (`mtime=0`) → `37,897` B JS payload (`format_version = 3`).
- **Base & Collapsed Sections (`v1 + v2`):** Header JSON, full-graph typed arrays & delta-varint CSR `edge_buf` (`3,376` B), collapsed supernode metadata (`c_super_edges_buf` = `825` B), and `0` pruned dead-edge pairs.
- **Hasse Bitmasks & 4 Simplified Views (`v3`):** `full_hasse_mask` (`217` B), `existing_hasse_mask` (`89` B), and 1-bit-flagged LEB128 CSR edge streams (`9,222` B across all 4 simplified views).

---

## 6. Viewer Legend and Visual Encoding

The interactive viewer ([full_dag.html](full_dag.html)) displays a collapsible corner legend populated dynamically from `header.groups` (sorted by descending module count) and a **Max depth** BFS filter bar:

| Top-Level Directory | Modules | Hex | Color |
| :--- | ---: | :--- | :--- |
| `Lib` | 495 | `#2563eb` | Blue |
| `New` | 306 | `#ea580c` | Orange |
| `(root)` | 2 | `#ca8a04` | Gold / Amber |

- **Future Refactor Fallback:** Beyond 10 top-level directories, `group_color()` assigns deterministic golden-angle HSL colors.
- **Top-Right Control Stack:** **Layout** picker (**Sugiyama (L1 tightened)**, **Depth (BFS from root)**, **Depth (longest path)**), simplification toggles (**Collapse existing theory (`C`)**, **Hide redundant imports (`H`)**, **Collapse chains & leaves (`L`)**), and the **Max depth** shortest-path BFS depth control (`[` / `]` hotkeys and `All` toggle) filtering nodes and edges by distance from `Main` without altering coordinates.

---

## 7. Current Graph & Layout Summary

### 8-View Summary Matrix

| View (`Existing`, `Hasse`, `Chains/Leaves`) | Nodes | Edges | Layers | Layer Spacing | Avg $\Delta y$ | Avg $\lvert\Delta x\rvert$ | Weighted Anchors ($w > 1$) | Weighted Edges ($w_E \ge 2$) | Module Conservation |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Full DAG** (`F, F, F`) | 803 | 1,733 | 54 | 4.0000 | 3.825 | 2.564 | — | — | `803 + 0 = 803` |
| **Full + Hide redundant imports** (`F, T, F`) | 803 | 1,733 | 54 | 4.0000 | *(in-place)* | *(in-place)* | — | — | `803 + 0 = 803` |
| **Existing Theory** (`T, F, F`) | 324 | 709 | 30 | 4.0000 | 3.911 | 2.374 | 16 supernodes | 21 | `803 + 0 = 803` |
| **Existing + Hide redundant imports** (`T, T, F`) | 324 | 616 | 30 | 4.0000 | *(in-place)* | *(in-place)* | 16 supernodes | *(in-place)* | `803 + 0 = 803` |
| **Full + Chains & Leaves** (`F, F, T`) | 666 | 1,594 | 50 | 4.0000 | 3.979 | 2.649 | 2 (`max w=2`) | 122 (`max=4`) | `668 + 135 = 803` |
| **Full + Hasse + Chains & Leaves** (`F, T, T`) | 666 | 1,594 | 50 | 4.0000 | 3.979 | 2.649 | 2 (`max w=2`) | 122 (`max=4`) | `668 + 135 = 803` |
| **Existing + Chains & Leaves** (`T, F, T`) | 266 | 648 | 29 | 4.0000 | 4.131 | 2.131 | 1 + 16 super | 69 (`max=4`) | `746 + 57 = 803` |
| **Existing + Hasse + Chains & Leaves** (`T, T, T`) | 244 | 532 | 26 | 4.0000 | 3.024 | 1.952 | 1 + 16 super | 66 (`max=5`) | `724 + 79 = 803` |

### Top Weighted Anchor Nodes & Contracted Edges (`full_hasse_simp`)

| Top Weighted Anchor Node (`Anchor [w]`) | Weight $w$ | Breakdown (`leaves` / `chains`) | Representative Absorbed Leaf |
| :--- | ---: | :---: | :--- |
| `Reduction/OneSidedBound` | 2 | 1 / 0 | `Statements` |
| `Lib/Base` | 2 | 1 / 0 | `Speed` |

| Top Contracted Edge (`src → dst`) | Combined Weight $w_E$ | Multiplicity (`×mult`) | Contracted Chain (`+chain`) |
| :--- | ---: | ---: | ---: |
| `GoodDatum → EdgePairEvaluation` | 4 | ×1 | +3 |
| `Cases → ThetaProducts` | 4 | ×1 | +3 |
| `StandardQuadrics → FinitePlaceDensity` | 4 | ×1 | +3 |
| `FillingData → LargeFunction` | 4 | ×2 | +2 |
| `LargeTriple → MatchingPartners` | 4 | ×2 | +2 |

### Full DAG Summary

| Metric | Value |
| :--- | ---: |
| Total Lean Modules (Nodes) | 803 |
| Total Internal Import Edges | 1,733 |
| Declarations Indexed (Reachable) | 23,235 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers | 54 (`layer 0`..`53`) |
| Layer Width (min / median / p95 / max) | 1 / 16 / 28 / 30 |
| Vertical Layer Spacing (`layer_dy`) | 4.0000 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 4.241 $\to$ 3.825 |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 4.462 $\to$ 2.564 |
| Adjacent / Short-Span Edges ($\Delta y = 1$ / $\Delta y \le 5$) | 807 / 1,363 |
| World Aspect Ratio | 0.15 : 1 |
| `LDAG` v3 Payload (`full_dag_data.js`) | 37,897 bytes (`28,397` B gzip / `61,696` B raw) |

### Collapsed DAG Summary ("Collapse Existing Theory")

| Metric | Value |
| :--- | ---: |
| Collapsed View Nodes (`active + supernodes`) | 324 (`308` active + `16` literature supernodes) |
| Collapsed Modules Total (`frontier + interior`) | 495 (`61.64%`: `151` frontier + `344` interior) |
| Collapsed View Edges (`active + supernode`) | 709 (`526` active + `183` supernode edges) |
| Raw Frontier Imports Contracted / Max Weight | 208 raw imports / $w_{\max} = 3$ (`21` edges with $w \ge 2$) |
| Targeted Dead Bridge Imports Pruned | 0 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers (`c_num_layers`) | 30 (`layer 0`..`29`) |
| Collapsed Layer Width (min / median / p95 / max) | 1 / 11 / 24 / 29 |
| Vertical Layer Spacing (`c_layer_dy`) | 4.0000 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 4.072 $\to$ 3.911 (`330` at $\Delta y = 1$) |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 3.543 $\to$ 2.374 |
| Min Intra-Layer Gap / World Aspect Ratio | 1.0 / 0.24 : 1 |

### Discovered Top-Level Domains & Collapse Breakdown

| Top-Level Directory | Total Modules | Active | Collapsed | Collapsed % | Palette Color | Layer Range (min / med / max) | Mean $x$ |
| :--- | ---: | ---: | ---: | ---: | :---: | :---: | ---: |
| `Lib` | 495 | 0 | 495 | 100.0% | `#2563eb` | 15 / 36 / 53 | -2.74 |
| `New` | 306 | 306 | 0 | 0.0% | `#ea580c` | 1 / 21 / 49 | 2.20 |
| `(root)` | 2 | 2 | 0 | 0.0% | `#ca8a04` | 0 / 3 / 3 | -0.94 |

### Top 16 Collapsed Literature Supernodes

| Literature Supernode Title | Owned Collapsed Modules | Full Cone Modules | Frontier Roots | Contracted In-Edges | Raw Imports |
| :--- | ---: | ---: | ---: | ---: | ---: |
| Lib: Galois Representations | 119 | 240 | 7 | 8 | 10 |
| Lib: Weil Representation & Theta Lifts | 67 | 135 | 30 | 30 | 34 |
| Lib: General Algebra, Analysis & Geometry | 57 | 143 | 31 | 44 | 49 |
| Lib: Class Field Theory & Cohomology | 53 | 132 | 14 | 15 | 20 |
| Lib: Adelic Groups & Trace Formula | 51 | 113 | 14 | 16 | 17 |
| Lib: Discrete Series of U(p,q) | 37 | 81 | 17 | 21 | 26 |
| Lib: Siegel–Weil & Rallis Formulas | 28 | 106 | 11 | 12 | 13 |
| Lib: Shimura & Abelian Varieties | 19 | 33 | 2 | 5 | 5 |
| Lib: Complex Multiplication | 14 | 34 | 6 | 6 | 6 |
| Lib: p-adic Hodge & Kisin Modules | 13 | 40 | 2 | 2 | 2 |
| Lib: Local & Finite GL_n | 12 | 26 | 4 | 6 | 6 |
| Lib: Analytic Number Theory & PNT | 10 | 10 | 6 | 5 | 7 |
| Lib: GL_n Schur & Branching | 8 | 30 | 4 | 7 | 7 |
| Lib: Cyclotomic Fields & Odd Ш | 4 | 50 | 1 | 2 | 2 |
| Lib: Base & Settings | 2 | 2 | 1 | 2 | 2 |
| Lib: Étale & Hodge Cohomology | 1 | 2 | 1 | 2 | 2 |

### Top 15 Most Imported Hub Modules

| Top Imported Hub Module | In-Degree | Out-Degree | Layer |
|---|---:|---:|---:|
| `Lib/Base.lean` | 20 | 1 | 52 |
| `Lib/General/NumberTheory/PadicLimitsValuation.lean` | 11 | 3 | 36 |
| `Lib/Shimura/Uniformisation/HolomorphicFamilies.lean` | 11 | 5 | 42 |
| `Lib/Cohomology/Etale/Basic.lean` | 10 | 1 | 50 |
| `Lib/General/Groups/CongruenceSubgroups.lean` | 10 | 1 | 51 |
| `Lib/General/Analysis/HolomorphicIntegrals.lean` | 9 | 4 | 49 |
| `Lib/General/LinearAlgebra/BlockEmbeddings.lean` | 9 | 2 | 30 |
| `Lib/General/LinearAlgebra/Eigenvalues.lean` | 9 | 1 | 41 |
| `New/UpperBound/Objects/Rows.lean` | 9 | 4 | 16 |
| `Lib/Adelic/Unitary/Defs.lean` | 8 | 3 | 48 |
| `Lib/Adelic/Witt/WittTheorem.lean` | 8 | 2 | 43 |
| `Lib/PadicComparison/Descent/TestCategory.lean` | 8 | 2 | 46 |
| `Lib/Shimura/HeckeTower/HeckeData.lean` | 8 | 3 | 39 |
| `Lib/Weil/Unramified/HeckeGL.lean` | 8 | 2 | 40 |
| `Lib/Adelic/Adeles/LocalFactors.lean` | 7 | 3 | 38 |

---

## 8. Regenerating After a Lean Refactor

```bash
# 1. Rebuild only this version's full DAG payload & sync portal reports
python3 analysis/build_all.py --version community-9211277d --steps index,inventory,full_dag

# 2. Or re-run build_full_dag.py standalone and regenerate HTML reports
python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/community-9211277d/data/graph.sqlite --out-dir analysis/versions/community-9211277d/full_dag --version-label community-9211277d
node analysis/render_reports.js

# 3. Open the local analysis portal or viewer
python3 -m http.server 8000 --directory analysis
```
