# Full Lean Module Dependency DAG

This document describes the repeatable layout pipeline, binary data packaging, and WebGL visualization behind the interactive full-graph viewer:

- **Interactive Viewer:** [full_dag.html](full_dag.html) (pan and zoom across all modules and import edges, with an interactive **Collapse existing theory** toggle)
- **Layout Generator:** [build_full_dag.py](build_full_dag.py)
- **Layout Summary:** [layout_summary.json](layout_summary.json)
- **SQLite Indexer:** [build_index.py](../build_index.py)
- **Existing-Theory Inventory & Methodology:** [PUBLISHED_THEOREMS_INVENTORY.html](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.html) ([Markdown](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md))

> **Direction Convention:** Every node represents a `.lean` module under `lean/src`. A directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Top-level theorem modules sit at the top (`layer 0`), and foundational definitions and leaf modules sit below (`layer 1..202`).

---

## 1. Why Modules Rather Than Individual Statements?

In Lean 4, a **module** corresponds 1-to-1 with a single `.lean` source file under `lean/src/` (the compilation unit that produces one `.olean` binary). For instance, `lean/src/Main.lean` is module `Main`, and `lean/src/Supplements/Kernels/MainTheoremsAll.lean` is module `Supplements.Kernels.MainTheoremsAll`. Each module begins with explicit `import` headers declaring its dependencies, and because Lean forbids circular imports, the module import graph is guaranteed to be a strict DAG.

Inside those modules live individual **declarations** (`theorem`, `lemma`, `def`, `structure`, `class`, `inductive`, `abbrev`, `instance`). A finer-grained **declaration-level DAG**—linking every declaration to the exact constants referenced in its type and proof term—is not tracked here for three reasons:

1. **Accurate extraction requires full compilation:** Lean 4 proofs rely heavily on tactics (`simp`, `linarith`, `ring`, `aesop`, etc.), typeclass synthesis, coercions, and `open`ed namespaces, so many dependencies never appear explicitly by name in raw `.lean` source text. Recovering true declaration-level edges requires compiling the entire codebase to `.olean` files and inspecting Lean's elaborated `Environment` (for example, `Expr.getUsedConstants` on each `ConstantInfo`). By contrast, module `import` statements are explicit syntax at the top of every file, allowing [build_index.py](../build_index.py) to extract the exact module DAG deterministically from `lean/src/` in ~25 seconds using only Python.
2. **Scale and architectural clarity:** The codebase contains **1,057,807** internal declarations (6× the **175,187** modules). Including tactic-elaborated and typeclass-synthesized edges would expand the graph to tens of millions of edges, dramatically increasing layout and browser rendering cost while obscuring macro-level mathematical structure under low-level algebraic and tactic plumbing.
3. **Modules here are already fine-grained:** Across the 175,187 modules in `lean/src/`, the median module contains just **2 declarations** (mean `6.04`), and **78,880 modules (45.0%)** contain a single declaration. The module DAG therefore already approximates a theorem-by-theorem dependency graph while naturally grouping small local helper lemmas together.

---

## 2. End-to-End Repeatable Pipeline

The visualization is generated deterministically from the Lean source tree with zero hardcoded module paths, directory names, layer counts, or fixed directory-to-color mappings. Whenever the underlying Lean codebase is refactored, regenerating the graph requires a single command:

```bash
python3 analysis/full_dag/build_full_dag.py --rebuild-index
```

If `analysis/data/graph.sqlite` is already up to date, omitting `--rebuild-index` skips re-scanning `lean/src` and rebuilds the layout and dataset directly from SQLite in ~30 seconds:

```bash
python3 analysis/full_dag/build_full_dag.py
```

The pipeline executes five stages:

1. **Source Indexing (`analysis/build_index.py`):** Walks `lean/src` in sorted relative-path order, parses `import` statements, builds the deduplicated internal module import graph, and writes `analysis/data/graph.sqlite` and `analysis/data/meta.json`.
2. **Acyclicity Verification (`load_graph` + Kahn's topological sort):** Loads all modules ordered deterministically by `(rel_path, id)` and runs Kahn's topological algorithm from roots ($\text{in\_degree} = 0$). If any import cycle exists, the pipeline aborts immediately with an error.
3. **Deterministic 3-Stage Sugiyama Layout (`compute_layout`):** Assigns integer layer coordinates $y(u)$ and continuous non-overlapping horizontal coordinates $x(u)$, then scales vertical spacing dynamically to preserve a readable widescreen aspect ratio.
4. **Existing-Theory Proof Collapse & Weighted Layout (`build_collapsed_dag`):** Applies the inventory-driven proof-frontier cut, contracts proof-only subtrees into axiom-sink **Literature Supernodes** with contracted import weights, and computes a compact weighted Sugiyama layout for the collapsed view.
5. **Canonical Re-Indexing & `LDAG` v2 Packaging:** Re-indexes both full and collapsed nodes in `(y, x, rel_path)` order, packs typed arrays and LEB128 varint adjacency lists into a 4-byte-aligned `LDAG` v2 binary buffer (reusing active-to-active edges across views), compresses deterministically (`gzip` with `mtime=0`), and emits [full_dag_data.js](full_dag_data.js) alongside [layout_summary.json](layout_summary.json).

---

## 3. Layout Algorithm

Drawing the complete import graph of 175,187 modules and 753,261 edges requires strict topological orientation (every edge pointing downward) while minimizing vertical edge spans and horizontal edge crossings.

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

2. **Permutation & Relaxation:** During the first 10 sweeps, each layer is re-sorted by $(\bar{x}(u), \text{rel\_path}(u))$ to eliminate crossings; during the final 6 sweeps, the layer ordering is held fixed while coordinates relax smoothly.
3. **Pool-Adjacent-Violators (PAV) Isotonic Projection:** Within each ordered layer $u_0, \dots, u_{m-1}$, coordinates are projected onto the non-overlap polytope $x(u_{i+1}) - x(u_i) \ge 1.0$ by solving the exact $O(m)$ isotonic $L_2$ regression problem $\min \sum_{i=0}^{m-1} (x_i - \bar{x}(u_i))^2$ via the Pool-Adjacent-Violators algorithm on $z_i = x_i - i$ with target $t_i = \bar{x}(u_i) - i$.

This stage reduces mean horizontal edge span $|\Delta x|$ nearly threefold, from **363.32** units to **121.839** units, while enforcing a strict minimum horizontal gap of **1.0** world unit between adjacent nodes in every layer.

Finally, layer vertical spacing $\Delta y$ is computed dynamically from the total horizontal span $W_x = x_{\max} - x_{\min}$ and layer count $K$ as $\Delta y = \text{clamp}\!\left(\frac{W_x}{1.85 \cdot (K - 1)},\, 4.0,\, 12.0\right)$, yielding $\Delta y = 9.3166$ and an overall aspect ratio of **1.85 : 1**.

---

## 4. Refactor-Resilience Guarantees

- **Zero Hardcoded Names or Counts:** Every top-level directory (`top_dir`) is discovered dynamically from `graph.sqlite`, sorted deterministically by `(-module_count, top_dir)`, and colored from a fixed high-contrast light-theme categorical palette (with a deterministic golden-angle HSL fallback if a refactor introduces more than 10 top-level directories).
- **Deterministic Tie-Breaking & Bit-Exact Output:** Node ordering ties break on `rel_path`, canonical IDs are sorted by `(layer, x, rel_path)`, and gzip compression uses `mtime=0`, ensuring repeated runs on unchanged sources emit byte-identical outputs.
- **Invariant Checks:** For both the full DAG and the collapsed DAG, the generator verifies zero self-loops, exact topological completeness (`len(topo) == N`), strict downward edge monotonicity ($y(u) < y(v)$ and $\text{id}(u) < \text{id}(v)$), intra-layer non-overlap ($\Delta x \ge 1.0$), and exact collapsed module conservation ($\text{active\_nodes} + \sum_T |S_T| = 175{,}187$) before writing output.

---

## 5. Existing-Theory Proof Collapse, Weighted Contraction & Rendering Architecture

### Existing-Theory Proof-Frontier Cut

The **"Collapse existing theory"** toggle in [full_dag.html](full_dag.html) (keyboard shortcut `C`) lets readers hide the subtrees of the Lean codebase proving already-established peer-reviewed mathematics while preserving every novel theorem, shared interface specification, and statement contract.

Following the identification methodology documented in [PUBLISHED_THEOREMS_INVENTORY.md](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md#methodology-identifying-collapsible-existing-theory-proof-subtrees), `build_full_dag.py`:

1. Parses all audited peer-reviewed `Prop` identifiers and bold canonical literature titles across Sections 1–11 of the inventory (`534` target symbols across `109` literature entries), excluding Section 12 project-specific statements and internal scaffolding.
2. Enforces the SQLite defining-module ancestor guard and scans final conclusion heads of `theorem`/`lemma` declarations while excluding `*/Definitions/*`, assumed hypothesis-bundle projections/dispatchers (`HypothesesU`, `OpenImageCondition`, `OpenLiteratureStatements`, etc.), novel headline modules, and `20` multi-topic re-export barrels (`ProvedMore`, `InputsOf`, `Multi`, `BridgesMore`, etc.).
3. Performs reachability from `Main` without crossing outgoing edges of detected proof roots while applying **targeted dead-import pruning** on `RiemannHypothesisOfEveryCharacter.lean` (ignoring `54` provably unreferenced imports whose targets lie strictly below the baseline published-theorem frontier so proof-only interiors cannot leak past the cut without falsely collapsing unrelated legacy modules).

### Literature Supernodes & Disjoint Ownership Conservation

Modules unreachable from `Main` past the proof-frontier cut form the **proof-only interior** $C$ (`39,314` modules), while the reached proof-root modules form the **frontier** $F$ (`420` modules). Merging frontier proof roots by literature topic while keeping outgoing `Supernode -> Shared Active` edges breaks DAG acyclicity whenever alternative proofs sit at different heights around shared definitions. To preserve a strict DAG:

- Frontier modules $F$ are grouped by their primary inventory row into **83 Literature Supernodes** $S_T$ rendered as **diamond axiom sinks** ($\text{out\_degree} = 0$).
- Every proof-only interior module $v \in C$ is assigned to a unique Literature Supernode $S_T$ via deterministic multi-source BFS from $F$ (ordered by distance from `Main` and in-degree), yielding a complete disjoint partition with zero unowned nodes:

$$|A| + \sum_{T} |S_T| = 135{,}453 + 39{,}734 = 175{,}187.$$

Each supernode displays its canonical literature title and exact collapsed module count in brackets alongside the diamond node (for example, `BLGGT / Caraiani Strong Local–Global Compatibility [13,455]`).

### Post-Collapse Edge Weights & Compact Layout

Contracting multiple frontier proof imports from an active module $u \in A$ to the same Literature Supernode $S_T$ induces integer **edge weights** measuring proof-import multiplicity:

$$w(u, v) = \begin{cases} |\{(u, f) \in E : f \in F_T\}| \ge 1 & \text{if } v = S_T \text{ is a Literature Supernode,} \\ 1 & \text{if } v \in A \text{ is an active module.} \end{cases}$$

In the current build, `6,289` contracted supernode edges represent `7,125` raw frontier imports, with **`711` edges carrying weight $w \ge 2$** (up to $w_{\max} = 8$). Both Stage 2 ($L_1$ weighted rank tightening with total gradient $\sum_{(p,u)} w(p,u) - \sum_{(u,c)} w(u,c)$) and Stage 3 (inverse-span barycenter weighted by $w(u, v) / \lvert y(u) - y(v) \rvert$) use these weights when computing the compact **177-layer** collapsed Sugiyama layout.

### Compact Offline Payload (`LDAG` v2 in `full_dag_data.js`)

Because browser `fetch()` requests to local files fail under `file://` CORS restrictions, the pipeline embeds the gzipped binary container as a Base64-encoded global assignment (`window.__FULL_DAG_GZ_B64__`) in `full_dag_data.js` and decompresses it client-side using the browser's built-in `DecompressionStream("gzip")`.

Inside the decompressed 4-byte-aligned little-endian `LDAG` v2 container:
- **Header JSON:** Counts, bounds, `layer_dy`, and discovered group palette metadata for both the full graph and the `"collapsed"` subgraph.
- **Typed Node Arrays & String Blobs:** `layer_offsets` (`Uint32Array[num_layers+1]`), `node_x` (`Float32Array[N]`), `node_group` (`Uint8Array[N]`), clamped `node_in_deg` / `node_out_deg` (`Uint16Array[N]`), `node_dir_id` (`Uint32Array[N]`), and newline-delimited unique directory paths and short module names.
- **Delta-Varint CSR Edges (Shared Across Views):** Outgoing neighbor counts and monotonically increasing target deltas encoded as unsigned LEB128 varints (yielding `1,809,565` raw bytes for all `753,261` edges prior to gzip).
- **Compact Collapsed Diff Sections:** Reuses the full CSR active-to-active edges with zero duplication, storing only `c_layer_offsets` (`Uint32Array`), `c_node_x` (`Float32Array`), `c_node_full_id` (`Int32Array`, mapping non-negative IDs to full nodes and negative IDs `-(sIdx + 1)` to Literature Supernodes), supernode counts/frontier counts/domains/titles, delta-varint `(target_delta, weight)` supernode edges (`159,866` raw bytes), and `54` canonical dead-edge pairs. On first toggle, `full_dag.html` lazily reconstructs the collapsed CSR and weighted edge buffers in memory.

### WebGL1 + 2D Canvas Hybrid Renderer (`full_dag.html`)

- **On-Demand WebGL Rendering:** Edges are uploaded into a stratified 8-bucket vertex buffer (`gl.LINES`) with endpoint colors interpolated between importer and dependency domains, and nodes are uploaded into a vertex buffer (`gl.POINTS`) rendered as anti-aliased discs scaled smoothly with `sqrt(zoom)` and strictly capped below $0.76 \cdot \text{zoom}$ at zoomed-in scales so adjacent nodes never overlap.
- **Zoom-Adaptive Edge Opacity & Responsive Pan/Zoom:** Edge opacity scales continuously with zoom so dense structural bundles remain legible at overview while individual links sharpen as you zoom in. During active drag/wheel gestures, if a full edge draw exceeded 20 ms, a stratified subset of buckets renders immediately and restores 100% of edges 90 ms after motion stops.
- **Binary-Search Viewport Culling & Progressive Overlay:** Because nodes are canonically ordered by `(layer, x)` in both views, the 2D overlay locates visible nodes per frame in $O(K_{\text{vis}} \log W)$ time via `layer_offsets` and binary search on `node_x`, drawing collision-free labels for visible landmarks/hubs/supernodes (plus directory or root-count subtitles at deep zoom) and directional arrowheads when zoomed into local neighborhoods.
- **Clean Light-Theme Navigation Interface:** The viewer exposes the full-viewport DAG canvas, mouse-wheel/pinch zoom, drag/keyboard pan, a collapsible bottom-left legend, zoom controls, and the single top-right **"Collapse existing theory"** toggle (`C` hotkey).

---

## 6. Viewer Legend and Visual Encoding

The interactive viewer ([full_dag.html](full_dag.html)) displays a compact, collapsible legend in the bottom-left corner so colors, node sizes, edge gradients, and optional supernodes can be read directly on the canvas:

- **Dynamic Corner Legend:** On load, the legend is populated directly from `header.groups` inside `full_dag_data.js` (sorted by descending module count with zero hardcoded directory names or colors). Each row pairs a circular swatch with a top-level directory (`top_dir`) and its module count. Clicking the **Legend** header collapses or expands the panel, and the 2D label renderer reserves the legend's live screen rectangle (`reserveUiRects`) so node labels never overlap it.
- **Node Color Palette (`top_dir`):** Every Lean module node is colored by its top-level directory under `lean/src/`, assigned deterministically in descending order of module count (tie-broken alphabetically) from `BASE_PALETTE` in [build_full_dag.py](build_full_dag.py) and recorded in [layout_summary.json](layout_summary.json):

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
| `(root)` (`Main`, `Statements`) | 2 | `#111827` | Charcoal / Near-black |

- **Future Refactor Fallback:** If a future refactor adds more than 10 top-level directories, `group_color()` in [build_full_dag.py](build_full_dag.py) assigns deterministic golden-angle HSL colors (`hue = ((idx - 10) * 0.618033988749895) % 1`, saturation `0.72`, lightness `0.42`) for indices `idx >= 10`.
- **Edges:** Import links linearly interpolate RGB color from the importer node (`A`) to the dependency node (`B`), with zoom-adaptive opacity and deep-zoom directional arrowheads pointing toward dependencies.
- **Node Size & Zoomed Rim:** Disc diameter grows gently with in-degree (and root modules with `in_degree = 0` are emphasized) and `sqrt(zoom)`. When zoomed in (disc diameter above ~5.5 CSS px), each disc gains a subtly darkened border rim (`col * 0.55`) to keep adjacent nodes distinct.
- **Collapsed Existing-Theory Mode (LDAG v2):** When the **Collapse existing theory** toggle (`C`) is enabled, diamond markers (`◆`) with lightened centers and `log1p(collapsedCount)` sizing represent contracted Literature Supernodes colored by their dominant `top_dir` and labeled `<Literature Title> [<collapsedCount>]`. Contracted supernode edges carry import-multiplicity weights $w \ge 1$ rendered via WebGL opacity multipliers, 2D overlay variable-thickness strokes scaled by $\log_2(w)$, weight-scaled deep-zoom arrowheads, and `×w` badges (`w >= 2`), while the legend automatically displays a diamond key row.

---

## 7. Current Graph & Layout Summary

### Full DAG Summary

| Metric | Value |
| :--- | ---: |
| Total Lean Modules (Nodes) | 175,187 |
| Total Internal Import Edges | 753,261 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers | 203 (`layer 0`..`202`) |
| Layer Width (min / median / p95 / max) | 1 / 712 / 2,042 / 3,480 |
| Vertical Layer Spacing (`layer_dy`) | 9.3166 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 18.926 $\to$ 17.288 |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 363.320 $\to$ 121.839 |
| Adjacent-Layer Edges ($\Delta y = 1$) | 190,823 |
| Short-Span Edges ($\Delta y \le 5$) | 352,622 |
| World Aspect Ratio | 1.85 : 1 |
| `LDAG` v2 Payload (`full_dag_data.js`) | 5,446,505 bytes (`4,084,854` B gzipped / `10,715,720` B raw) |

### Collapsed DAG Summary ("Collapse Existing Theory")

| Metric | Value |
| :--- | ---: |
| Collapsed View Nodes (`active + supernodes`) | 135,536 (`135,453` active + `83` literature supernodes) |
| Collapsed Modules Total (`frontier + interior`) | 39,734 (`22.68%` of codebase: `420` frontier + `39,314` interior) |
| Collapsed View Edges (`active + supernode`) | 593,000 (`586,711` active + `6,289` supernode edges) |
| Raw Frontier Imports Contracted / Max Weight | 7,125 raw imports / $w_{\max} = 8$ (`711` edges with $w \ge 2$) |
| Targeted Dead Bridge Imports Pruned (`RHEC`) | 54 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers (`c_num_layers`) | 177 (`layer 0`..`176`) |
| Collapsed Layer Width (min / median / p95 / max) | 1 / 752 / 1,739 / 2,914 |
| Vertical Layer Spacing (`c_layer_dy`) | 8.9466 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 18.218 $\to$ 16.342 (`148,231` at $\Delta y = 1$) |
| Mean Horizontal Span ($\lvert\Delta x\rvert$ before $\to$ after) | 294.990 $\to$ 96.408 |
| Min Intra-Layer Gap / World Aspect Ratio | 1.0 / 1.85 : 1 |

### Discovered Top-Level Domains & Collapse Breakdown

| Top-Level Directory | Total Modules | Active | Collapsed | Collapsed % | Palette Color | Layer Range (Full min / med / max) | Mean $x$ (Full) |
| :--- | ---: | ---: | ---: | ---: | :---: | :---: | ---: |
| `Development` | 141,928 | 104,931 | 36,997 | 26.1% | `#2563eb` | 4 / 151 / 202 | -161.56 |
| `Formalism` | 18,254 | 18,168 | 86 | 0.5% | `#ea580c` | 98 / 177 / 202 | 603.79 |
| `GroundTheory` | 8,507 | 6,627 | 1,880 | 22.1% | `#ca8a04` | 34 / 192 / 202 | 1,018.81 |
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

---

## 8. Regenerating After a Lean Refactor

```bash
# 1. Re-index lean/src into analysis/data/graph.sqlite and rebuild the full DAG payload
python3 /home/ubuntu/riemann_proof/analysis/full_dag/build_full_dag.py --rebuild-index

# 2. Re-render HTML versions of all Markdown reports (including FULL_DAG.html)
node /home/ubuntu/riemann_proof/analysis/render_reports.js

# 3. Open the local analysis portal or viewer directly
python3 -m http.server 8000 --directory /home/ubuntu/riemann_proof/analysis
```
