# Full Lean Module Dependency DAG

This document describes the repeatable layout pipeline, binary data packaging, and WebGL visualization behind the interactive full-graph viewer:

- **Interactive Viewer:** [full_dag.html](full_dag.html) (pan and zoom across all modules and import edges)
- **Layout Generator:** [build_full_dag.py](build_full_dag.py)
- **Layout Summary:** [layout_summary.json](layout_summary.json)
- **SQLite Indexer:** [build_index.py](../build_index.py)

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

The pipeline executes four stages:

1. **Source Indexing (`analysis/build_index.py`):** Walks `lean/src` in sorted relative-path order, parses `import` statements, builds the deduplicated internal module import graph, and writes `analysis/data/graph.sqlite` and `analysis/data/meta.json`.
2. **Acyclicity Verification (`load_graph` + Kahn's topological sort):** Loads all modules ordered deterministically by `(rel_path, id)` and runs Kahn's topological algorithm from roots ($\text{in\_degree} = 0$). If any import cycle exists, the pipeline aborts immediately with an error.
3. **Deterministic 3-Stage Sugiyama Layout (`compute_layout`):** Assigns integer layer coordinates $y(u)$ and continuous non-overlapping horizontal coordinates $x(u)$, then scales vertical spacing dynamically to preserve a readable widescreen aspect ratio.
4. **Canonical Re-Indexing & Binary Packaging:** Re-indexes all nodes in `(y, x, rel_path)` order, packs compact typed arrays and LEB128 varint adjacency lists into a 4-byte-aligned binary buffer, compresses it deterministically (`gzip` with `mtime=0`), and emits [full_dag_data.js](full_dag_data.js) alongside [layout_summary.json](layout_summary.json).

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
- **Invariant Checks:** The generator verifies zero self-loops, exact topological completeness (`len(topo) == N`), strict downward edge monotonicity ($y(u) < y(v)$ and $\text{id}(u) < \text{id}(v)$), and intra-layer non-overlap ($\Delta x \ge 1.0$) before writing output.

---

## 5. Binary Serialization & Rendering Architecture

### Compact Offline Payload (`full_dag_data.js`)

Because browser `fetch()` requests to local files fail under `file://` CORS restrictions, the pipeline embeds the gzipped binary container as a Base64-encoded global assignment (`window.__FULL_DAG_GZ_B64__`) in `full_dag_data.js` and decompresses it client-side using the browser's built-in `DecompressionStream("gzip")`.

Inside the decompressed 4-byte-aligned little-endian `LDAG` v1 container:
- **Header JSON:** Graph counts, bounds, `layer_dy`, and discovered group palette metadata.
- **Typed Node Arrays:** `layer_offsets` (`Uint32Array[num_layers+1]`), `node_x` (`Float32Array[N]`), `node_group` (`Uint8Array[N]`), clamped `node_in_deg` / `node_out_deg` (`Uint16Array[N]`), and `node_dir_id` (`Uint32Array[N]`).
- **String Blobs:** Newline-delimited unique directory paths and short module names.
- **Delta-Varint CSR Edges:** Outgoing neighbor counts and monotonically increasing target deltas encoded as unsigned LEB128 varints (yielding `1,809,565` raw bytes for all 753,261 edges prior to gzip).

### WebGL1 + 2D Canvas Hybrid Renderer (`full_dag.html`)

- **On-Demand WebGL Rendering:** Edges are uploaded into a stratified 8-bucket vertex buffer (`gl.LINES`) with endpoint colors interpolated between importer and dependency domains, and nodes are uploaded into a vertex buffer (`gl.POINTS`) rendered as anti-aliased discs scaled smoothly with `sqrt(zoom)` and strictly capped below $0.76 \cdot \text{zoom}$ at zoomed-in scales so adjacent nodes never overlap.
- **Zoom-Adaptive Edge Opacity & Responsive Pan/Zoom:** Edge opacity scales continuously with zoom so dense structural bundles remain legible at overview while individual links sharpen as you zoom in. During active drag/wheel gestures, if a full edge draw exceeded 20 ms, a stratified subset of buckets renders immediately and restores 100% of edges 90 ms after motion stops.
- **Binary-Search Viewport Culling & Progressive Overlay:** Because nodes are canonically ordered by `(layer, x)`, the 2D overlay locates visible nodes per frame in $O(K_{\text{vis}} \log W)$ time via `layer_offsets` and binary search on `node_x`, drawing collision-free labels for visible landmarks/hubs (plus directory subtitles at deep zoom) and directional arrowheads when zoomed into local neighborhoods.
- **Pure Navigation Interface:** The viewer exposes only the full-viewport DAG canvas, mouse-wheel/pinch zoom, drag/keyboard pan, and minimal corner navigation/zoom buttons, with zero filters, tables, sidebars, or node-clicking handlers.

---

## 6. Current Graph & Layout Summary

| Metric | Value |
| :--- | ---: |
| Total Lean Modules (Nodes) | 175,187 |
| Total Internal Import Edges | 753,261 |
| Acyclic DAG Verified (`is_dag`) | `true` |
| Topological Layers | 203 (`layer 0`..`202`) |
| Layer Width (min / median / p95 / max) | 1 / 712 / 2,042 / 3,480 |
| Vertical Layer Spacing (`layer_dy`) | 9.3166 |
| Mean Vertical Span ($\Delta y$ before $\to$ after) | 18.926 $\to$ 17.288 |
| Mean Horizontal Span ($|\Delta x|$ before $\to$ after) | 363.320 $\to$ 121.839 |
| Adjacent-Layer Edges ($\Delta y = 1$) | 190,823 |
| Short-Span Edges ($\Delta y \le 5$) | 352,622 |
| World Aspect Ratio | 1.85 : 1 |

### Discovered Top-Level Domains

| Top-Level Directory | Modules | Palette Color | Layer Range (min / med / max) | Mean $x$ |
| :--- | ---: | :---: | :---: | ---: |
| `Development` | 141,928 | `#2563eb` | 4 / 151 / 202 | -161.56 |
| `Formalism` | 18,254 | `#ea580c` | 98 / 177 / 202 | 603.79 |
| `GroundTheory` | 8,507 | `#ca8a04` | 34 / 192 / 202 | 1,018.81 |
| `ReciprocityTheory` | 3,845 | `#0d9488` | 86 / 189 / 202 | 780.37 |
| `CompanionTheory` | 2,027 | `#059669` | 88 / 167 / 202 | -518.52 |
| `PositivityTheory` | 449 | `#c026d3` | 67 / 105 / 202 | 643.54 |
| `Lemmata` | 167 | `#7c3aed` | 141 / 195 / 202 | 651.02 |
| `BuildAid` | 5 | `#64748b` | 143 / 157 / 185 | 171.43 |
| `Supplements` | 3 | `#4f46e5` | 1 / 2 / 3 | 24.93 |
| `(root)` | 2 | `#111827` | 0 / 1 / 1 | 20.19 |

---

## 7. Regenerating After a Lean Refactor

```bash
# 1. Re-index lean/src into analysis/data/graph.sqlite and rebuild the full DAG payload
python3 /home/ubuntu/riemann_proof/analysis/full_dag/build_full_dag.py --rebuild-index

# 2. Re-render HTML versions of all Markdown reports (including FULL_DAG.html)
node /home/ubuntu/riemann_proof/analysis/render_reports.js

# 3. Open the local analysis portal or viewer directly
python3 -m http.server 8000 --directory /home/ubuntu/riemann_proof/analysis
```
