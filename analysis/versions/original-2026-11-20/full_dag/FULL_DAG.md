# Full Lean Module Dependency DAG (`original-2026-11-20`)

This document describes the repeatable layout pipeline, binary data packaging, graph-simplification modes, and WebGL visualization behind the interactive full-graph viewer:

- **Interactive Viewer:** [full_dag.html](full_dag.html) (pan and zoom across all modules and import edges, with a **Layout** picker switching between Sugiyama and depth-based layouts, three composable simplification switches: **Collapse existing theory** `C`, **Hide redundant imports** `H`, and **Collapse chains & leaves** `L`, plus the **Max depth** BFS filter `[` / `]`)
- **Layout Generator:** [build_full_dag.py](build_full_dag.py)
- **Layout Summary:** [layout_summary.json](layout_summary.json)
- **SQLite Indexer:** [build_index.py](../build_index.py)
- **Existing-Theory Inventory & Methodology:** [PUBLISHED_THEOREMS_INVENTORY.html](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.html) ([Markdown](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md))

> **Direction Convention:** Every node represents a `.lean` module under `lean/src`. A directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Top-level theorem modules sit at the top (`layer 0`), and foundational definitions and leaf modules sit below (`layer 1..202`).

---

## 1. Why Modules Rather Than Individual Statements?

In Lean 4, a **module** corresponds 1-to-1 with a single `.lean` source file under `lean/src/` (the compilation unit that produces one `.olean` binary). For instance, `lean/src/Main.lean` is module `Main`, and `lean/src/Supplements/Kernels/MainTheoremsAll.lean` is module `Supplements.Kernels.MainTheoremsAll`. Each module begins with explicit `import` headers declaring its dependencies, and because Lean forbids circular imports, the module import graph is guaranteed to be a strict DAG.

Inside those modules live individual **declarations** (`theorem`, `lemma`, `def`, `structure`, `class`, `inductive`, `abbrev`, `instance`). A finer-grained **declaration-level DAG**—linking every declaration to the exact constants referenced in its type and proof term—is not tracked here for three reasons:

1. **Accurate extraction requires full compilation:** Lean 4 proofs rely heavily on tactics (`simp`, `linarith`, `ring`, `aesop`, etc.), typeclass synthesis, coercions, and `open`ed namespaces, so many dependencies never appear explicitly by name in raw `.lean` source text. Recovering true declaration-level edges requires compiling the entire codebase to `.olean` files and inspecting Lean's elaborated `Environment` (for example, `Expr.getUsedConstants` on each `ConstantInfo`). By contrast, module `import` statements are explicit syntax at the top of every file, allowing [build_index.py](../build_index.py) to extract the exact module DAG deterministically from `lean/src/` using only Python.
2. **Scale and architectural clarity:** Across reachable modules, the codebase contains **1,057,807** declarations (6.0× the **175,187** modules). Including tactic-elaborated and typeclass-synthesized edges would expand the graph to millions of edges, dramatically increasing layout and browser rendering cost while obscuring macro-level mathematical structure under low-level algebraic and tactic plumbing.
3. **Modules here are fine-grained:** Across the **175,187** reachable modules in `lean/src/`, the median module contains **2** declarations (mean `6.04`), and **78,880 modules (45.0%)** contain a single declaration. The module DAG therefore closely tracks theorem-level architecture while grouping small local helper lemmas together.

---

## 2. End-to-End Repeatable Pipeline

The visualization is generated deterministically from the Lean source tree with zero hardcoded module paths, directory names, layer counts, or fixed directory-to-color mappings. Rebuilding this version runs a single orchestrator command:

```bash
python3 analysis/build_all.py --version original-2026-11-20 --steps full_dag
```

Or directly via `build_full_dag.py` against SQLite:

```bash
python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/original-2026-11-20/data/graph.sqlite --out-dir analysis/versions/original-2026-11-20/full_dag
```

The pipeline executes five stages:

1. **Source Indexing (`analysis/build_index.py`):** Walks `lean/src/` in sorted relative-path order, parses `import` statements, builds the deduplicated internal module import graph, and writes `graph.sqlite` and `meta.json`.
2. **Acyclicity Verification (`load_graph` + Kahn's topological sort):** Loads all reachable modules ordered deterministically by `(rel_path, id)` and runs Kahn's topological algorithm from roots ($\text{in\_degree} = 0$). If any import cycle exists, the pipeline aborts immediately with an error.
3. **Deterministic 3-Stage Sugiyama Layout (`compute_layout`):** Assigns integer layer coordinates $y(u)$ and continuous non-overlapping horizontal coordinates $x(u)$, then scales vertical spacing dynamically to preserve a readable widescreen aspect ratio.
4. **Graph Simplification & Multi-View Weighted Layouts (`build_collapsed_dag`, `compute_transitive_reduction`, `simplify_chains_and_leaves`):**
   - Applies the inventory-driven proof-frontier cut to contract peer-reviewed background proofs into **83 Literature Supernodes** (`existing`).
   - Computes exact transitive reduction (Hasse diagrams) on both the full DAG (`full_hasse`) and existing-theory DAG (`existing_hasse`), packing 1-bit-per-edge masks for zero-jump in-place toggling.
   - Runs a 2-phase fixed-point chain/leaf collapse (`simplify_chains_and_leaves`) across all four `(existing, hasse)` combinations (`full_simp`, `full_hasse_simp`, `existing_simp`, `existing_hasse_simp`), computing weighted Sugiyama layouts using edge weights $w_E = \text{mult} + \text{chain}$.
5. **Canonical Re-Indexing & `LDAG` v3 Packaging:** Re-indexes every node-bearing layout in `(y, x, sort_key)` order, packs typed arrays, LEB128 delta-varint CSR adjacency lists, 1-bit Hasse masks, sparse weighted-anchor records, and 1-bit-flagged weighted edge streams into a 4-byte-aligned `LDAG` v3 binary buffer, compresses deterministically (`gzip` with `mtime=0`), and emits [full_dag_data.js](full_dag_data.js) alongside [layout_summary.json](layout_summary.json).

---

## 3. Layout Algorithm

Drawing the complete import graph of **175,187** modules and **753,261** edges requires strict topological orientation (every edge pointing downward) while minimizing vertical edge spans and horizontal edge crossings.

### Stage 1: Bottom-Aligned Longest-Path Layering

First, module heights $h(u)$ from leaf modules ($\text{out\_degree} = 0$) are computed in reverse topological order:

$$h(u) = \begin{cases} 0 & \text{if } \text{out}(u) = \emptyset, \\ 1 + \max_{(u, v) \in E} h(v) & \text{otherwise.} \end{cases}$$

Setting initial vertical rank $y_0(u) = H_{\max} - h(u)$ places the root entry module (`Main`, $h = 202$) at $y = 0$ and guarantees $y_0(v) \ge y_0(u) + 1$ for every edge $(u, v) \in E$.

### Stage 2: Feasible $L_1$ Vertical Rank Tightening

Bottom-aligned layering leaves intermediate modules with fewer outgoing than incoming dependencies sitting deeper than necessary. To reduce total vertical edge length $\sum_{(u,v)\in E} (y(v) - y(u))$ while strictly preserving the DAG invariant $y(v) \ge y(u) + 1$, the generator runs up to 25 alternating topological and reverse-topological coordinate-descent sweeps.

At each node $u$, the feasible integer interval imposed by its neighbors is:

$$\ell(u) = \begin{cases} 0 & \text{if } \text{in}(u) = \emptyset, \\ \max_{(p, u) \in E} y(p) + 1 & \text{otherwise,} \end{cases} \qquad r(u) = \begin{cases} H_{\max} & \text{if } \text{out}(u) = \emptyset, \\ \min_{(u, c) \in E} y(c) - 1 & \text{otherwise.} \end{cases}$$

Since the local derivative of total edge span with respect to $y(u)$ is $|\text{in}(u)| - |\text{out}(u)|$:
- If $|\text{in}(u)| > |\text{out}(u)|$, $u$ moves to $\ell(u)$ (pulled upward toward its importers).
- If $|\text{out}(u)| > |\text{in}(u)|$, $u$ moves to $r(u)$ (pulled downward toward its dependencies).
- If $|\text{in}(u)| = |\text{out}(u)|$, $u$ moves to the rounded mean of its neighbors clamped to $[\ell(u), r(u)]$.

Across the full graph, these sweeps reduce mean vertical edge span from **18.926** layers to **17.288** layers, placing **190,823** edges on adjacent layers ($\Delta y = 1$) and **352,622** edges within $\Delta y \le 5$.

### Stage 3: Weighted Barycenter Ordering & Isotonic $L_2$ Placement

Nodes are grouped into layers $L_0, \dots, L_{202}$, initially sorted by `rel_path` and centered with unit spacing. The generator then executes 16 alternating top-down and bottom-up sweeps:

1. **Inverse-Span Weighted Barycenter:** For every node $u \in L_k$, its target horizontal position $\bar{x}(u)$ averages both incoming and outgoing neighbors weighted by $w(u, v) = |y(u) - y(v)|^{-1}$ so short-span edges pull more strongly than long-span cross-layer edges:

$$\bar{x}(u) = \frac{\sum_{v \in \text{in}(u) \cup \text{out}(u)} \frac{x(v)}{|y(u) - y(v)|}}{\sum_{v \in \text{in}(u) \cup \text{out}(u)} \frac{1}{|y(u) - y(v)|}}.$$

2. **Permutation & Relaxation:** During the first 10 sweeps, each layer is re-sorted by $(\bar{x}(u), \text{rel\_path}(u))$ to eliminate crossings; during the final sweeps, the layer ordering is held fixed while coordinates relax smoothly.
3. **Pool-Adjacent-Violators (PAV) Isotonic Projection:** Within each ordered layer $u_0, \dots, u_{m-1}$, coordinates are projected onto the non-overlap polytope $x(u_{i+1}) - x(u_i) \ge 1.0$ by solving the exact $O(m)$ isotonic $L_2$ regression problem $\min \sum_{i=0}^{m-1} (x_i - \bar{x}(u_i))^2$ via the Pool-Adjacent-Violators algorithm on $z_i = x_i - i$ with target $t_i = \bar{x}(u_i) - i$.

This stage reduces mean horizontal edge span $|\Delta x|$ from **363.320** units to **121.839** units, while enforcing a strict minimum horizontal gap of **1.0** world unit between adjacent nodes in every layer.

Finally, layer vertical spacing $\Delta y$ is computed dynamically from total horizontal span $W_x = x_{\max} - x_{\min}$ and layer count $K$ as $\Delta y = \text{clamp}\!\left(\frac{W_x}{1.85 \cdot (K - 1)},\, 4.0,\, 12.0\right)$, yielding $\Delta y = 9.3166$ and an overall aspect ratio of **1.85 : 1**.

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
- **Invariant Checks:** Across all 8 composable views, the generator verifies zero self-loops, exact topological completeness (`len(topo) == N`), strict downward edge monotonicity ($y(u) < y(v)$ and $\text{id}(u) < \text{id}(v)$), intra-layer non-overlap ($\Delta x \ge 1.0$), exact Hasse bitmask counts (`386,211` for `full_hasse`, `305,256` for `existing_hasse`), zero remaining unprotected simple leaves or `(1,1)` pass-through nodes after fixed-point simplification, and exact module conservation ($\sum_{v \in V} w(v) + \sum_{e \in E} \text{chain}(e) = 175,187$) before writing output.

---

## 5. Simplification Modes, Weights & `LDAG` v3 Architecture

The viewer provides three orthogonal, composable toggles that switch smoothly between **8 pre-verified graph views**:

1. **Collapse existing theory (`C`):** Contracts established peer-reviewed mathematical proofs into **83 Literature Supernodes**.
2. **Hide redundant imports (`H`):** Applies exact transitive reduction (the Hasse diagram), hiding shortcut import edges that are already implied by longer dependency paths.
3. **Collapse chains & leaves (`L`):** Folds private simple-leaf subtrees upward into weighted parent anchor nodes (`Anchor [w]`) and contracts pass-through `(1,1)` chains onto weighted dependency edges.

### 5.1 Existing-Theory Proof-Frontier Cut ("Collapse existing theory")

The **"Collapse existing theory"** toggle in [full_dag.html](full_dag.html) (keyboard shortcut `C`) lets readers hide subtrees of the Lean codebase proving already-established peer-reviewed mathematics while preserving every novel theorem, shared interface specification, and statement contract.

Following the identification methodology in [PUBLISHED_THEOREMS_INVENTORY.md](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md#methodology-identifying-collapsible-existing-theory-proof-subtrees), `build_full_dag.py`:

1. Parses audited peer-reviewed `Prop` identifiers and bold canonical literature titles from Sections 1–11 of the active inventory (excluding Section 12 project-specific statements and internal scaffolding).
2. Enforces the SQLite defining-module ancestor guard and scans final conclusion heads of `theorem`/`lemma` declarations while excluding `*/Definitions/*`, assumed hypothesis-bundle projections/dispatchers (`OpenImageCondition`, `OpenLiteratureStatements`, etc.), novel headline modules, and multi-topic re-export barrels.
3. Performs reachability from `Main` without crossing outgoing edges of detected proof roots while pruning **54** provably dead bridge imports whose targets lie strictly below the baseline published-theorem frontier.

Modules unreachable from `Main` past the proof-frontier cut form the **proof-only interior** $C$ (`39,314` modules), while reached proof-root modules form the **frontier** $F$ (`420` modules). Grouping frontier roots into **83 Literature Supernodes** $S_T$ rendered as **diamond axiom sinks** ($\text{out\_degree} = 0$) and assigning every $v \in C$ via deterministic multi-source BFS yields a complete disjoint partition:

$$|A| + \sum_{T} |S_T| = 135,453 + 39,734 = 175,187.$$

Each supernode displays its canonical literature title and collapsed module count in brackets (for example, `BLGGT / Caraiani Strong Local–Global Compatibility [13,455]`). Contracting parallel frontier imports from an active module $u \in A$ to $S_T$ induces edge multiplicity weights (**6,289** contracted supernode edges from **7,125** raw frontier imports, with **711** edges having $w \ge 2$, up to $w_{\max} = 8$).

### 5.2 Transitive Reduction ("Hide redundant imports" / Hasse Diagram)

Lean modules frequently `import` both a downstream module $B$ and an ancestor $C$ that $B$ already imports (`A -> B -> C` alongside shortcut `A -> C`).

The **"Hide redundant imports"** toggle (`H` hotkey) displays the DAG's **exact transitive reduction** (its Hasse diagram), keeping an edge $(u, v)$ if and only if no indirect directed path $u \to \dots \to v$ of length $\ge 2$ exists:

- **Algorithm (`compute_transitive_reduction`):** Processes nodes in topological order using striped arbitrary-precision integer bitsets (stripe width $B = 16{,}384$) to compute 1-step reachability $R_1(u)$ and $\ge 2$-step reachability $R_2(u) = \bigvee_{(u, v) \in E} R_1(v)$; edge $(u, v)$ is redundant iff $v \in R_2(u)$.
- **Edge Reduction (Full DAG):** Removes **367,050** redundant edges (`48.73%`), leaving **386,211** covering edges (`full_hasse`).
- **Edge Reduction (Existing-Theory DAG):** Removes **287,744** redundant edges (`48.52%`), leaving **305,256** covering edges (`existing_hasse`).
- **In-Place Zero-Jump Filtering:** When *Collapse chains & leaves* is off, toggling `H` keeps node coordinates fixed and swaps CSR edges using compact 1-bit masks (`full_hasse_mask` = `94,158` B; `existing_hasse_mask` = `74,125` B).

### 5.3 Chain & Simple-Leaf Collapse ("Collapse chains & leaves")

The **"Collapse chains & leaves"** toggle (`L` hotkey) runs `simplify_chains_and_leaves`, a deterministic 2-phase fixed-point contraction loop (on the base DAG removing **5,576** leaves and **21,602** chain nodes; after transitive reduction removing **6,018** leaves and **64,547** chain nodes):

1. **Phase 1 — Simple-Leaf Folding into Node Weight (`in = 1, out = 0`):** Iteratively peels every unprotected node $u$ with a single importer $p$ and zero internal dependencies upward into $p$, transferring node weight and any edge chain weight:

$$w(p) \leftarrow w(p) + w(u) + \text{chain}(p, u).$$

Private leaf-trees collapse into weighted anchor nodes (for instance, `Imports` absorbs `19` leaves and `8` chain modules to reach weight `28`). When *Collapse existing theory* is also active, all **83 Literature Supernodes** are protected from absorption so diamond landmarks remain visible.
2. **Phase 2 — Pass-Through `(1,1)` Chain Contraction into Edge Weight:** Iteratively contracts every unprotected `(1, 1)` node $u$ along $p \to u \to c$ into a direct edge $(p, c)$, merging parallel paths:

$$\text{mult}(p, c) \mathrel{+}= \max\!\big(\text{mult}(p, u),\, \text{mult}(u, c)\big), \qquad \text{chain}(p, c) \mathrel{+}= \text{chain}(p, u) + \text{chain}(u, c) + w(u).$$

The combined edge weight used for layout attraction and stroke rendering is $w_E(e) = \text{mult}(e) + \text{chain}(e)$.
3. **Fixed-Point Iteration & Module Conservation:** Phases 1 and 2 repeat until convergence (running *after* Hasse reduction when both `H` and `L` are active), preserving exact module conservation across every surviving view:

$$\sum_{v \in V} w(v) + \sum_{e \in E} \text{chain}(e) = 175,187.$$

### 5.4 Node Labeling & Weight Encoding (Option A)

- **Weighted Anchor Nodes (`Anchor [w]`):** Any active module with weight $w > 1$ renders with increased disc diameter ($w_{\text{base}} + 0.55 \ln(w)$) and an **inner white halo ring** (`alphaByte = 128`), labeled with its bold domain-colored `[w]` suffix.
- **Deep-Zoom Breakdown Subtitles (`zoom >= 55`):** Single-leaf absorption ($k = 1$) names the absorbed module directly; multi-module absorption summarizes `+k collapsed (L leaves, C chain)` alongside its directory path.
- **Weighted Edges & Badges:** Contracted edges scale in WebGL opacity, 2D stroke width ($\log_2 w_E$), deep-zoom arrowheads, and collision-free `×m` / `+c` / `×m +c` badges at `zoom >= 6`.

### 5.5 Compact Offline Payload (`LDAG` v3 in `full_dag_data.js`)

Because browser `fetch()` fails under `file://` CORS restrictions, `build_full_dag.py` embeds the gzipped 4-byte-aligned little-endian `LDAG` binary container as `window.__FULL_DAG_GZ_B64__` in `full_dag_data.js` and decompresses it client-side via `DecompressionStream("gzip")`:

- **Container Sizes:** `19,365,504` raw bytes → `9,305,882` B gzipped (`mtime=0`) → `12,407,877` B JS payload (`format_version = 3`).
- **Base & Collapsed Sections (`v1 + v2`):** Header JSON, full-graph typed arrays & delta-varint CSR `edge_buf` (`1,809,565` B), collapsed supernode metadata (`c_super_edges_buf` = `159,866` B), and `54` pruned dead-edge pairs.
- **Hasse Bitmasks & 4 Simplified Views (`v3`):** `full_hasse_mask` (`94,158` B), `existing_hasse_mask` (`74,125` B), and 1-bit-flagged LEB128 CSR edge streams (`4,719,947` B across all 4 simplified views).

---

## 6. Viewer Legend and Visual Encoding

The interactive viewer ([full_dag.html](full_dag.html)) displays a collapsible corner legend populated dynamically from `header.groups` (sorted by descending module count) and a **Max depth** BFS filter bar:

| Top-Level Directory | Modules | Hex | Color |
| :--- | ---: | :--- | :--- |
| `Development` | 141,928 | `#2563eb` | Blue |
| `Formalism` | 18,254 | `#ea580c` | Orange |
| `GroundTheory` | 8,507 | `#ca8a04` | Gold / Amber |
| `ReciprocityTheory` | 3,845 | `#0d9488` | Teal |
| `CompanionTheory` | 2,027 | `#059669` | Emerald green |
| `PositivityTheory` | 449 | `#c026d3` | Fuchsia / Magenta |
| `Lemmata` | 167 | `#7c3aed` | Violet / Purple |
| `BuildAid` | 5 | `#64748b` | Slate gray |
| `Supplements` | 3 | `#4f46e5` | Indigo |
| `(root)` | 2 | `#111827` | Charcoal / Near-black |

- **Future Refactor Fallback:** Beyond 10 top-level directories, `group_color()` assigns deterministic golden-angle HSL colors.
- **Top-Right Control Stack:** **Layout** picker (**Sugiyama (L1 tightened)**, **Depth (BFS from root)**, **Depth (longest path)**), simplification toggles (**Collapse existing theory (`C`)**, **Hide redundant imports (`H`)**, **Collapse chains & leaves (`L`)**), and the **Max depth** shortest-path BFS depth control (`[` / `]` hotkeys and `All` toggle) filtering nodes and edges by distance from `Main` without altering coordinates.

---

## 7. Current Graph & Layout Summary

### 8-View Summary Matrix

| View (`Existing`, `Hasse`, `Chains/Leaves`) | Nodes | Edges | Layers | Layer Spacing | Avg $\Delta y$ | Avg $\lvert\Delta x\rvert$ | Weighted Anchors ($w > 1$) | Weighted Edges ($w_E \ge 2$) | Module Conservation |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **Full DAG** (`F, F, F`) | 175,187 | 753,261 | 203 | 9.3166 | 17.288 | 121.839 | — | — | `175,187 + 0 = 175,187` |
| **Full + Hide redundant imports** (`F, T, F`) | 175,187 | 386,211 | 203 | 9.3166 | *(in-place)* | *(in-place)* | — | — | `175,187 + 0 = 175,187` |
| **Existing Theory** (`T, F, F`) | 135,536 | 593,000 | 177 | 8.9466 | 16.342 | 96.408 | 83 supernodes | 711 | `175,187 + 0 = 175,187` |
| **Existing + Hide redundant imports** (`T, T, F`) | 135,536 | 305,256 | 177 | 8.9466 | *(in-place)* | *(in-place)* | 83 supernodes | *(in-place)* | `175,187 + 0 = 175,187` |
| **Full + Chains & Leaves** (`F, F, T`) | 148,009 | 712,764 | 202 | 6.3202 | 17.803 | 111.004 | 2,609 (`max w=25`) | 9,680 (`max=152`) | `152,920 + 22,267 = 175,187` |
| **Full + Hasse + Chains & Leaves** (`F, T, T`) | 104,622 | 307,224 | 151 | 6.2397 | 9.430 | 80.710 | 2,449 (`max w=28`) | 42,592 (`max=154`) | `109,360 + 65,827 = 175,187` |
| **Existing + Chains & Leaves** (`T, F, T`) | 115,374 | 563,733 | 177 | 6.1701 | 16.835 | 88.081 | 2,125 + 83 super | 8,336 (`max=112`) | `158,897 + 16,290 = 175,187` |
| **Existing + Hasse + Chains & Leaves** (`T, T, T`) | 83,150 | 247,282 | 151 | 5.2306 | 9.058 | 68.454 | 1,995 + 83 super | 32,629 (`max=95`) | `126,554 + 48,633 = 175,187` |

### Top Weighted Anchor Nodes & Contracted Edges (`full_hasse_simp`)

| Top Weighted Anchor Node (`Anchor [w]`) | Weight $w$ | Breakdown (`leaves` / `chains`) | Representative Absorbed Leaf |
| :--- | ---: | :---: | :--- |
| `UnitTraceSumBounds/Imports` | 28 | 19 / 8 | `CBFiLower` |
| `DivisorProofs/FirstDeRhamHomologyProjectiveOverTensorIntegers` | 25 | 24 / 0 | `AnnihilatorLiftOfMulEqP` |
| `ArchimedeanOrbitMeasures/CayDensEx` | 25 | 12 / 12 | `Imports` |
| `DivisorProofs/EtaleLocalVanishingCohomology` | 24 | 23 / 0 | `EtaleUniquePrimeLeMapMaximal` |
| `DivisorProofs/ExistsStrictHenselisation` | 24 | 23 / 0 | `ExistsNumDen` |

| Top Contracted Edge (`src → dst`) | Combined Weight $w_E$ | Multiplicity (`×mult`) | Contracted Chain (`+chain`) |
| :--- | ---: | ---: | ---: |
| `IsolateSpecHolds → IsolateSpec` | 154 | ×76 | +78 |
| `AbelianHodgeDeRham → H1CommutesBaseChange` | 126 | ×38 | +88 |
| `RsOf → UnramifiedEulerProductIntegral` | 95 | ×31 | +64 |
| `RsPoleOfInputs → ColumnConjugationMeasure` | 90 | ×44 | +46 |
| `HasRepresentingSchemePinchedBase → UnitsPatch` | 74 | ×23 | +51 |

### Full DAG Summary

| Metric | Value |
| :--- | ---: |
| Total Lean Modules (Nodes) | 175,187 |
| Total Internal Import Edges | 753,261 |
| Declarations Indexed (Reachable) | 1,057,807 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers | 203 (`layer 0`..`202`) |
| Layer Width (min / median / p95 / max) | 1 / 712 / 2,042 / 3,480 |
| Vertical Layer Spacing (`layer_dy`) | 9.3166 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 18.926 $\to$ 17.288 |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 363.320 $\to$ 121.839 |
| Adjacent / Short-Span Edges ($\Delta y = 1$ / $\Delta y \le 5$) | 190,823 / 352,622 |
| World Aspect Ratio | 1.85 : 1 |
| `LDAG` v3 Payload (`full_dag_data.js`) | 12,407,877 bytes (`9,305,882` B gzip / `19,365,504` B raw) |

### Collapsed DAG Summary ("Collapse Existing Theory")

| Metric | Value |
| :--- | ---: |
| Collapsed View Nodes (`active + supernodes`) | 135,536 (`135,453` active + `83` literature supernodes) |
| Collapsed Modules Total (`frontier + interior`) | 39,734 (`22.68%`: `420` frontier + `39,314` interior) |
| Collapsed View Edges (`active + supernode`) | 593,000 (`586,711` active + `6,289` supernode edges) |
| Raw Frontier Imports Contracted / Max Weight | 7,125 raw imports / $w_{\max} = 8$ (`711` edges with $w \ge 2$) |
| Targeted Dead Bridge Imports Pruned | 54 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers (`c_num_layers`) | 177 (`layer 0`..`176`) |
| Collapsed Layer Width (min / median / p95 / max) | 1 / 752 / 1,739 / 2,914 |
| Vertical Layer Spacing (`c_layer_dy`) | 8.9466 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 18.218 $\to$ 16.342 (`148,231` at $\Delta y = 1$) |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 294.990 $\to$ 96.408 |
| Min Intra-Layer Gap / World Aspect Ratio | 1.0 / 1.85 : 1 |

### Discovered Top-Level Domains & Collapse Breakdown

| Top-Level Directory | Total Modules | Active | Collapsed | Collapsed % | Palette Color | Layer Range (min / med / max) | Mean $x$ |
| :--- | ---: | ---: | ---: | ---: | :---: | :---: | ---: |
| `Development` | 141,928 | 104,931 | 36,997 | 26.1% | `#2563eb` | 4 / 151 / 202 | -161.56 |
| `Formalism` | 18,254 | 18,168 | 86 | 0.5% | `#ea580c` | 98 / 177 / 202 | 603.79 |
| `GroundTheory` | 8,507 | 6,627 | 1,880 | 22.1% | `#ca8a04` | 34 / 192 / 202 | 1018.81 |
| `ReciprocityTheory` | 3,845 | 3,780 | 65 | 1.7% | `#0d9488` | 86 / 189 / 202 | 780.37 |
| `CompanionTheory` | 2,027 | 1,388 | 639 | 31.5% | `#059669` | 88 / 167 / 202 | -518.52 |
| `PositivityTheory` | 449 | 384 | 65 | 14.5% | `#c026d3` | 67 / 105 / 202 | 643.54 |
| `Lemmata` | 167 | 167 | 0 | 0.0% | `#7c3aed` | 141 / 195 / 202 | 651.02 |
| `BuildAid` | 5 | 3 | 2 | 40.0% | `#64748b` | 143 / 157 / 185 | 171.43 |
| `Supplements` | 3 | 3 | 0 | 0.0% | `#4f46e5` | 1 / 2 / 3 | 24.93 |
| `(root)` | 2 | 2 | 0 | 0.0% | `#111827` | 0 / 1 / 1 | 20.19 |

### Top 20 Collapsed Literature Supernodes

| Literature Supernode Title | Owned Collapsed Modules | Full Cone Modules | Frontier Roots | Contracted In-Edges | Raw Imports |
| :--- | ---: | ---: | ---: | ---: | ---: |
| BLGGT / Caraiani Strong Local–Global Compatibility | 13,455 | 17,230 | 3 | 7 | 7 |
| PEL Shimura Toroidal Compactifications & Mumford Degeneration | 7,036 | 8,181 | 9 | 109 | 142 |
| Abelian de Rham, Crystalline & Gauss–Manin Comparisons | 1,276 | 1,708 | 10 | 31 | 37 |
| Standard Siegel–Weil & Eisenstein Continuation | 1,131 | 1,685 | 3 | 3 | 5 |
| Unitary-to-GLₙ Isobaric Base Change | 967 | 984 | 6 | 21 | 25 |
| Ichino / Kudla–Rallis Convergent Siegel–Weil | 903 | 1,056 | 4 | 6 | 9 |
| Arithmetic Hilbert–Samuel, Volume & Absolute Siegel | 841 | 879 | 4 | 12 | 18 |
| SGA 7 Semistable Reduction, Néron Models & Serre–Tate | 814 | 1,016 | 7 | 11 | 17 |
| Grothendieck–Messing Deformation & Dieudonné Crystals | 794 | 887 | 3 | 267 | 271 |
| Jacquet–Shalika Rigidity & Bounds | 772 | 836 | 6 | 80 | 84 |
| Kawamata–Viehweg, Nadel Vanishing & Angehrn–Siu | 771 | 868 | 3 | 2 | 6 |
| Chern–Weil Theory & Mumford Proportionality | 766 | 836 | 7 | 5 | 10 |
| Poincaré–Lelong Current Identity | 674 | 696 | 1 | 2 | 2 |
| Fargues–Tate Exactness & Hodge–Tate Map | 617 | 618 | 2 | 4 | 4 |
| Bhatt–Scholze Prismatic F-Crystals | 579 | 596 | 3 | 5 | 7 |
| Berger p-adic Monodromy Theorem | 563 | 582 | 1 | 3 | 3 |
| Hironaka Resolution of Singularities (Char. 0) | 540 | 545 | 3 | 2 | 6 |
| Harish-Chandra Discrete Series Classification | 494 | 507 | 13 | 1,179 | 1,325 |
| Convergent Siegel–Weil Formula (Weil 1965) | 492 | 527 | 3 | 2 | 3 |
| Global Galois Euler Characteristic & Cohomological Dimension | 471 | 589 | 3 | 82 | 84 |

### Top 15 Most Imported Hub Modules

| Top Imported Hub Module | In-Degree | Out-Degree | Layer |
|---|---:|---:|---:|
| `Development/AbelianVarietyTheory/Definitions/Divisors/CTSmallCone.lean` | 3,088 | 2 | 160 |
| `Development/AbelianVarietyTheory/Definitions/Divisors/SiegelWeilAnisotropicHermitian.lean` | 2,972 | 23 | 149 |
| `Development/AbelianVarietyTheory/Definitions/Divisors/DiscreteSeriesHermitianUnique.lean` | 2,518 | 62 | 152 |
| `Development/AbelianVarietyTheory/PublishedTheorems/AutomorphicForms₂/ExistsNormLeHeightPow.lean` | 2,426 | 4 | 160 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean` | 2,390 | 5 | 193 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean` | 2,284 | 1 | 187 |
| `Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/CohomologicalCsdTempered.lean` | 2,242 | 0 | 171 |
| `Development/AbelianVarietyTheory/Definitions/Divisors/ToKnownTheoremsOf.lean` | 1,838 | 20 | 115 |
| `Development/AbelianVarietyTheory/PublishedTheorems/TwistedTraceFormula/HarishChandraModulesOn.lean` | 1,653 | 4 | 168 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean` | 1,429 | 1 | 196 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean` | 1,340 | 1 | 191 |
| `Development/AbelianVarietyTheory/PublishedTheorems/TwistedTraceFormula/AdmissibleDiscreteSeriesOfHasParam.lean` | 1,323 | 5 | 166 |
| `Development/AbelianVarietyTheory/BlockTheory/DivisorBase/WeilTensorModels.lean` | 1,307 | 5 | 162 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean` | 1,206 | 2 | 195 |
| `Development/AbelianVarietyTheory/Definitions/Degenerations/AdmissibleBaseOfCompleteDvr.lean` | 1,063 | 6 | 168 |

---

## 8. Regenerating After a Lean Refactor

```bash
# 1. Rebuild only this version's full DAG payload & sync portal reports
python3 analysis/build_all.py --version original-2026-11-20 --steps index,inventory,full_dag

# 2. Or re-run build_full_dag.py standalone and regenerate HTML reports
python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/original-2026-11-20/data/graph.sqlite --out-dir analysis/versions/original-2026-11-20/full_dag --version-label original-2026-11-20
node analysis/render_reports.js

# 3. Open the local analysis portal or viewer
python3 -m http.server 8000 --directory analysis
```
