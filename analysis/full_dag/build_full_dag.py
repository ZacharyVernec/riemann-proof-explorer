#!/usr/bin/env python3
"""Build a deterministic, refactor-resilient layout and binary dataset for the full Lean module DAG."""

from __future__ import annotations

import argparse
import base64
import colorsys
import gzip
import json
import math
import sqlite3
import struct
import subprocess
import sys
import time
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = ROOT / "analysis" / "data" / "graph.sqlite"
DEFAULT_OUT_DIR = ROOT / "analysis" / "full_dag"
BUILD_INDEX_SCRIPT = ROOT / "analysis" / "build_index.py"

MAGIC = b"LDAG"
FORMAT_VERSION = 1

BASE_PALETTE = [
    "#2563eb",
    "#ea580c",
    "#ca8a04",
    "#0d9488",
    "#059669",
    "#c026d3",
    "#7c3aed",
    "#64748b",
    "#4f46e5",
    "#111827",
]


def hex_to_rgb(hex_color: str) -> list[int]:
    """Convert '#rrggbb' hex string to [r, g, b] ints."""
    h = hex_color.lstrip("#")
    return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]


def group_color(idx: int) -> str:
    """Return a crisp light-theme categorical color for group index idx."""
    if idx < len(BASE_PALETTE):
        return BASE_PALETTE[idx]
    # Deterministic golden-angle HSL fallback for additional top-level directories
    hue = ((idx - len(BASE_PALETTE)) * 0.618033988749895) % 1.0
    sat = 0.72
    lit = 0.42
    r, g, b = colorsys.hls_to_rgb(hue, lit, sat)
    return f"#{int(round(r * 255)):02x}{int(round(g * 255)):02x}{int(round(b * 255)):02x}"


def encode_varint(buf: bytearray, val: int) -> None:
    """Append unsigned LEB128 varint to buf."""
    while val >= 0x80:
        buf.append((val & 0x7F) | 0x80)
        val >>= 7
    buf.append(val)


def pad4(buf: bytearray) -> None:
    """Pad bytearray with zero bytes to a 4-byte boundary."""
    rem = len(buf) & 3
    if rem:
        buf.extend(b"\x00" * (4 - rem))


def pav_isotonic_layer(nodes: list[int], target_x: dict[int, float], x_coords: list[float], gap: float = 1.0) -> None:
    """O(k) Pool-Adjacent-Violators L2 projection onto x[i+1] - x[i] >= gap."""
    blocks: list[list[float]] = []  # [sum_shifted_target, count]
    for i, u in enumerate(nodes):
        t = target_x[u] - i * gap
        blocks.append([t, 1.0])
        while len(blocks) >= 2 and blocks[-2][0] * blocks[-1][1] > blocks[-1][0] * blocks[-2][1]:
            b2 = blocks.pop()
            blocks[-1][0] += b2[0]
            blocks[-1][1] += b2[1]

    idx = 0
    for s_val, cnt_f in blocks:
        cnt = int(cnt_f)
        mean_z = s_val / cnt
        for _ in range(cnt):
            x_coords[nodes[idx]] = mean_z + idx * gap
            idx += 1


def load_graph(db_path: Path) -> tuple[list[str], list[str], list[str], list[str], list[list[int]], list[list[int]]]:
    """Load deduplicated module DAG from SQLite into dense 0..N-1 structures sorted by rel_path."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()

    mod_rows = cur.execute(
        "SELECT id, name, rel_path, dir_path, top_dir FROM modules ORDER BY rel_path ASC, id ASC"
    ).fetchall()
    n_mod = len(mod_rows)
    if n_mod == 0:
        conn.close()
        raise RuntimeError(f"No modules found in {db_path}")

    db_to_idx: dict[int, int] = {}
    mod_name: list[str] = [""] * n_mod
    rel_path: list[str] = [""] * n_mod
    dir_path: list[str] = [""] * n_mod
    top_dir: list[str] = [""] * n_mod

    for i, (db_id, name, rp, dp, td) in enumerate(mod_rows):
        db_to_idx[db_id] = i
        mod_name[i] = name
        rel_path[i] = rp
        dir_path[i] = dp if dp else "(root)"
        top_dir[i] = td if td else "(root)"

    adj_out_sets: list[set[int]] = [set() for _ in range(n_mod)]
    for s_db, d_db in cur.execute("SELECT src_id, dst_id FROM edges"):
        u = db_to_idx.get(s_db)
        v = db_to_idx.get(d_db)
        if u is None or v is None:
            continue
        if u == v:
            raise RuntimeError(f"Self-loop detected in {db_path}: {rel_path[u]}")
        adj_out_sets[u].add(v)
    conn.close()

    adj_out: list[list[int]] = [sorted(s) for s in adj_out_sets]
    adj_in: list[list[int]] = [[] for _ in range(n_mod)]
    for u in range(n_mod):
        for v in adj_out[u]:
            adj_in[v].append(u)

    return mod_name, rel_path, dir_path, top_dir, adj_out, adj_in


def compute_layout(
    rel_path: list[str],
    adj_out: list[list[int]],
    adj_in: list[list[int]],
    y_iters: int,
    x_sweeps: int,
) -> tuple[list[int], list[float], float, dict[str, Any]]:
    """Run deterministic 3-stage Sugiyama-style layout (longest-path -> L1 rank tightening -> PAV barycenter)."""
    n_mod = len(rel_path)
    n_edges = sum(len(nbrs) for nbrs in adj_out)

    # Topological sort via Kahn's algorithm
    in_rem = [len(adj_in[i]) for i in range(n_mod)]
    q: deque[int] = deque(i for i in range(n_mod) if in_rem[i] == 0)
    topo: list[int] = []
    while q:
        u = q.popleft()
        topo.append(u)
        for v in adj_out[u]:
            in_rem[v] -= 1
            if in_rem[v] == 0:
                q.append(v)

    if len(topo) != n_mod:
        raise RuntimeError(
            f"Import graph is not a DAG! Topological sort processed {len(topo)} of {n_mod} modules."
        )

    # Stage 1: Bottom-aligned longest path to leaves
    height = [0] * n_mod
    for u in reversed(topo):
        h = 0
        for v in adj_out[u]:
            hv = height[v] + 1
            if hv > h:
                h = hv
        height[u] = h

    max_h = max(height, default=0)
    y = [max_h - height[i] for i in range(n_mod)]

    init_avg_y_span = (
        sum(y[v] - y[u] for u in range(n_mod) for v in adj_out[u]) / n_edges if n_edges else 0.0
    )

    # Stage 2: Feasible L1 rank tightening
    y_passes_run = 0
    for it in range(max(0, y_iters)):
        y_passes_run += 1
        order = topo if (it % 2 == 0) else reversed(topo)
        moved = 0
        for u in order:
            ins = adj_in[u]
            outs = adj_out[u]
            ni = len(ins)
            no = len(outs)
            if ni == 0 and no == 0:
                continue
            lo = max(y[p] for p in ins) + 1 if ins else 0
            hi = min(y[c] for c in outs) - 1 if outs else max_h
            if ni > no:
                ny = lo
            elif no > ni:
                ny = hi
            else:
                avg = (sum(y[p] for p in ins) + sum(y[c] for c in outs)) / (ni + no)
                ny = max(lo, min(hi, int(round(avg))))
            if ny != y[u]:
                y[u] = ny
                moved += 1
        if moved == 0:
            break

    min_y = min(y, default=0)
    if min_y != 0:
        for i in range(n_mod):
            y[i] -= min_y
    num_layers = (max(y) + 1) if n_mod else 0

    span_eq_1 = 0
    span_le_5 = 0
    total_y_span = 0
    for u in range(n_mod):
        yu = y[u]
        for v in adj_out[u]:
            sp = y[v] - yu
            if sp <= 0:
                raise RuntimeError(f"Invalid vertical order on edge {u}->{v}: y[u]={yu}, y[v]={y[v]}")
            total_y_span += sp
            if sp == 1:
                span_eq_1 += 1
            if sp <= 5:
                span_le_5 += 1
    final_avg_y_span = total_y_span / n_edges if n_edges else 0.0

    # Stage 3: Horizontal crossing minimization & isotonic PAV coordinate placement
    layers: list[list[int]] = [[] for _ in range(num_layers)]
    for u in range(n_mod):
        layers[y[u]].append(u)

    x = [0.0] * n_mod
    for nodes in layers:
        nodes.sort(key=lambda u: rel_path[u])
        half = 0.5 * (len(nodes) - 1)
        for i, u in enumerate(nodes):
            x[u] = i - half

    init_avg_x_span = (
        sum(abs(x[u] - x[v]) for u in range(n_mod) for v in adj_out[u]) / n_edges if n_edges else 0.0
    )

    sort_cutoff = max(1, x_sweeps - 6)
    for sweep in range(max(0, x_sweeps)):
        down = sweep % 2 == 0
        layer_range = range(num_layers) if down else range(num_layers - 1, -1, -1)
        for ly in layer_range:
            nodes = layers[ly]
            k = len(nodes)
            if k == 0:
                continue
            if k == 1:
                u = nodes[0]
                yu = y[u]
                num = 0.0
                den = 0.0
                for v in adj_in[u]:
                    w = 1.0 / (yu - y[v])
                    num += w * x[v]
                    den += w
                for v in adj_out[u]:
                    w = 1.0 / (y[v] - yu)
                    num += w * x[v]
                    den += w
                if den > 0.0:
                    x[u] = num / den
                continue

            bary: dict[int, float] = {}
            for u in nodes:
                yu = y[u]
                num = 0.0
                den = 0.0
                for v in adj_in[u]:
                    w = 1.0 / (yu - y[v])
                    num += w * x[v]
                    den += w
                for v in adj_out[u]:
                    w = 1.0 / (y[v] - yu)
                    num += w * x[v]
                    den += w
                bary[u] = (num / den) if den > 0.0 else x[u]

            if sweep < sort_cutoff:
                nodes.sort(key=lambda u: (bary[u], rel_path[u]))
            pav_isotonic_layer(nodes, bary, x, gap=1.0)

    if n_mod:
        min_x = min(x)
        max_x = max(x)
        mid_x = 0.5 * (min_x + max_x)
        for i in range(n_mod):
            x[i] -= mid_x
        min_x -= mid_x
        max_x -= mid_x
    else:
        min_x = max_x = 0.0

    final_avg_x_span = (
        sum(abs(x[u] - x[v]) for u in range(n_mod) for v in adj_out[u]) / n_edges if n_edges else 0.0
    )

    x_span = max_x - min_x
    layer_dy = round(min(12.0, max(4.0, x_span / (max(1, num_layers - 1) * 1.85))), 4)

    widths = sorted(len(nodes) for nodes in layers)
    width_stats = {
        "min": widths[0] if widths else 0,
        "median": widths[len(widths) // 2] if widths else 0,
        "p95": widths[min(len(widths) - 1, int(len(widths) * 0.95))] if widths else 0,
        "max": widths[-1] if widths else 0,
    }

    metrics = {
        "is_dag": True,
        "y_iters_requested": y_iters,
        "y_iters_run": y_passes_run,
        "x_sweeps_run": x_sweeps,
        "init_avg_y_span": round(init_avg_y_span, 3),
        "final_avg_y_span": round(final_avg_y_span, 3),
        "span_eq_1_edges": span_eq_1,
        "span_le_5_edges": span_le_5,
        "init_avg_x_span": round(init_avg_x_span, 3),
        "final_avg_x_span": round(final_avg_x_span, 3),
        "layer_widths": width_stats,
    }
    return y, x, layer_dy, metrics


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic Sugiyama layout and binary payload for the full Lean DAG."
    )
    parser.add_argument("--rebuild-index", action="store_true", help="Re-run analysis/build_index.py first")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to graph.sqlite")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory")
    parser.add_argument("--y-iters", type=int, default=25, help="Max L1 vertical rank-tightening sweeps")
    parser.add_argument("--x-sweeps", type=int, default=16, help="Horizontal barycenter + PAV sweeps")
    args = parser.parse_args()

    t0 = time.time()
    if args.rebuild_index or not args.db_path.exists():
        print(f"Running index builder: {BUILD_INDEX_SCRIPT}")
        subprocess.run([sys.executable, str(BUILD_INDEX_SCRIPT)], check=True)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Loading graph from {args.db_path}...")
    mod_name, rel_path, dir_path, top_dir, adj_out, adj_in = load_graph(args.db_path)
    n_mod = len(mod_name)
    n_edges = sum(len(nbrs) for nbrs in adj_out)
    print(f"Loaded {n_mod:,} modules and {n_edges:,} internal edges in {time.time() - t0:.2f}s")

    t_lay = time.time()
    y, x, layer_dy, layout_metrics = compute_layout(rel_path, adj_out, adj_in, args.y_iters, args.x_sweeps)
    num_layers = (max(y) + 1) if n_mod else 0
    print(
        f"Computed layout ({num_layers} layers, layer_dy={layer_dy}) in {time.time() - t_lay:.2f}s | "
        f"avg_y_span {layout_metrics['init_avg_y_span']:.2f} -> {layout_metrics['final_avg_y_span']:.2f} | "
        f"avg_x_span {layout_metrics['init_avg_x_span']:.2f} -> {layout_metrics['final_avg_x_span']:.2f}"
    )

    # Canonical re-indexing sorted by (layer, x, rel_path)
    order = sorted(range(n_mod), key=lambda u: (y[u], x[u], rel_path[u]))
    old_to_new = [0] * n_mod
    for new_id, old_id in enumerate(order):
        old_to_new[old_id] = new_id

    # Verify strict downward DAG order and per-layer horizontal separation
    layer_offsets = [0] * (num_layers + 1)
    prev_layer = -1
    prev_x = 0.0
    min_layer_gap = float("inf")
    for new_id, old_id in enumerate(order):
        ly = y[old_id]
        xv = x[old_id]
        if ly != prev_layer:
            for fill_l in range(prev_layer + 1, ly + 1):
                layer_offsets[fill_l] = new_id
            prev_layer = ly
        else:
            gap = xv - prev_x
            if gap < min_layer_gap:
                min_layer_gap = gap
            if gap < 1.0 - 1e-4:
                raise RuntimeError(f"Layer {ly} spacing violation at node {new_id}: gap={gap}")
        prev_x = xv
    for fill_l in range(prev_layer + 1, num_layers + 1):
        layer_offsets[fill_l] = n_mod

    new_adj_out: list[list[int]] = [[] for _ in range(n_mod)]
    for old_u in range(n_mod):
        nu = old_to_new[old_u]
        targets = sorted(old_to_new[old_v] for old_v in adj_out[old_u])
        for nv in targets:
            if nu >= nv:
                raise RuntimeError(f"Canonical ID ordering invariant violated: {nu} -> {nv}")
        new_adj_out[nu] = targets

    # Dynamic top-level group discovery and color assignment
    top_counts: Counter[str] = Counter(top_dir)
    sorted_top_dirs = [td for td, _ in sorted(top_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    top_to_gid = {td: idx for idx, td in enumerate(sorted_top_dirs)}
    groups_meta = []
    for idx, td in enumerate(sorted_top_dirs):
        col = group_color(idx)
        groups_meta.append(
            {
                "id": idx,
                "name": td,
                "color": col,
                "rgb": hex_to_rgb(col),
                "count": top_counts[td],
            }
        )

    # Distinct directory paths (ordered deterministically)
    unique_dirs = sorted(set(dir_path))
    dir_to_id = {dp: idx for idx, dp in enumerate(unique_dirs)}

    # Prepare dense arrays in canonical order
    node_x_f32 = [0.0] * n_mod
    node_group = bytearray(n_mod)
    node_in_deg_list = [0] * n_mod
    node_out_deg_list = [0] * n_mod
    node_dir_id = [0] * n_mod
    short_names: list[str] = [""] * n_mod

    group_x_acc: dict[str, list[float]] = defaultdict(list)
    group_y_acc: dict[str, list[int]] = defaultdict(list)

    for new_id, old_id in enumerate(order):
        # Round to exact float32 representation for consistent JS bounds
        xf = struct.unpack("<f", struct.pack("<f", x[old_id]))[0]
        node_x_f32[new_id] = xf
        td = top_dir[old_id]
        node_group[new_id] = top_to_gid[td]
        node_in_deg_list[new_id] = len(adj_in[old_id])
        node_out_deg_list[new_id] = len(adj_out[old_id])
        node_dir_id[new_id] = dir_to_id[dir_path[old_id]]
        short_names[new_id] = mod_name[old_id].rsplit(".", 1)[-1]
        group_x_acc[td].append(xf)
        group_y_acc[td].append(y[old_id])

    xmin = min(node_x_f32, default=0.0)
    xmax = max(node_x_f32, default=0.0)
    ymin = 0.0
    ymax = round(max(0, num_layers - 1) * layer_dy, 4)

    header_obj = {
        "node_count": n_mod,
        "edge_count": n_edges,
        "num_layers": num_layers,
        "layer_dy": layer_dy,
        "bounds": {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax},
        "groups": groups_meta,
        "dir_count": len(unique_dirs),
        "layout_metrics": layout_metrics,
    }
    header_bytes = json.dumps(header_obj, separators=(",", ":")).encode("utf-8")

    # Encode CSR edges via unsigned LEB128 delta-varints
    edge_buf = bytearray()
    for nu in range(n_mod):
        targets = new_adj_out[nu]
        encode_varint(edge_buf, len(targets))
        prev_v = 0
        for nv in targets:
            encode_varint(edge_buf, nv - prev_v)
            prev_v = nv

    dir_blob = "\n".join(unique_dirs).encode("utf-8")
    name_blob = "\n".join(short_names).encode("utf-8")

    # Assemble 4-byte-aligned little-endian binary payload
    raw_buf = bytearray()
    raw_buf.extend(MAGIC)
    raw_buf.extend(struct.pack("<II", FORMAT_VERSION, len(header_bytes)))
    raw_buf.extend(header_bytes)
    pad4(raw_buf)

    raw_buf.extend(struct.pack(f"<{num_layers + 1}I", *layer_offsets))
    raw_buf.extend(struct.pack(f"<{n_mod}f", *node_x_f32))

    raw_buf.extend(node_group)
    pad4(raw_buf)

    raw_buf.extend(struct.pack(f"<{n_mod}H", *(min(65535, d) for d in node_in_deg_list)))
    pad4(raw_buf)

    raw_buf.extend(struct.pack(f"<{n_mod}H", *(min(65535, d) for d in node_out_deg_list)))
    pad4(raw_buf)

    raw_buf.extend(struct.pack(f"<{n_mod}I", *node_dir_id))

    raw_buf.extend(struct.pack("<I", len(dir_blob)))
    raw_buf.extend(dir_blob)
    pad4(raw_buf)

    raw_buf.extend(struct.pack("<I", len(name_blob)))
    raw_buf.extend(name_blob)
    pad4(raw_buf)

    raw_buf.extend(struct.pack("<I", len(edge_buf)))
    raw_buf.extend(edge_buf)

    gz_bytes = gzip.compress(bytes(raw_buf), compresslevel=9, mtime=0)
    b64_str = base64.b64encode(gz_bytes).decode("ascii")

    data_js_path = args.out_dir / "full_dag_data.js"
    data_js_path.write_text(f'window.__FULL_DAG_GZ_B64__ = "{b64_str}";\n', encoding="utf-8")

    # Build layout_summary.json
    domain_summaries = []
    for g in groups_meta:
        td = g["name"]
        xs_g = sorted(group_x_acc[td])
        ys_g = sorted(group_y_acc[td])
        domain_summaries.append(
            {
                "name": td,
                "color": g["color"],
                "modules": g["count"],
                "min_layer": ys_g[0],
                "median_layer": ys_g[len(ys_g) // 2],
                "max_layer": ys_g[-1],
                "mean_x": round(sum(xs_g) / len(xs_g), 2),
            }
        )

    roots = [
        {
            "module": mod_name[order[nid]],
            "rel_path": rel_path[order[nid]],
            "layer": y[order[nid]],
            "in_degree": node_in_deg_list[nid],
            "out_degree": node_out_deg_list[nid],
        }
        for nid in range(n_mod)
        if node_in_deg_list[nid] == 0
    ]
    top_hubs = sorted(range(n_mod), key=lambda nid: (-node_in_deg_list[nid], rel_path[order[nid]]))[:15]
    hubs_summary = [
        {
            "module": mod_name[order[nid]],
            "rel_path": rel_path[order[nid]],
            "top_dir": top_dir[order[nid]],
            "layer": y[order[nid]],
            "in_degree": node_in_deg_list[nid],
            "out_degree": node_out_deg_list[nid],
        }
        for nid in top_hubs
    ]

    summary = {
        "node_count": n_mod,
        "edge_count": n_edges,
        "num_layers": num_layers,
        "layer_dy": layer_dy,
        "min_intra_layer_gap": round(min_layer_gap, 4) if math.isfinite(min_layer_gap) else None,
        "bounds": header_obj["bounds"],
        "aspect_ratio": round((xmax - xmin) / max(1e-6, ymax - ymin), 3),
        "layout_metrics": layout_metrics,
        "domains": domain_summaries,
        "roots": roots,
        "top_in_degree_hubs": hubs_summary,
        "payload": {
            "raw_binary_bytes": len(raw_buf),
            "gzip_bytes": len(gz_bytes),
            "js_file_bytes": data_js_path.stat().st_size,
            "edge_varint_bytes": len(edge_buf),
            "name_blob_bytes": len(name_blob),
            "dir_blob_bytes": len(dir_blob),
        },
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    summary_path = args.out_dir / "layout_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(
        f"Wrote {data_js_path} ({data_js_path.stat().st_size:,} bytes; "
        f"gz={len(gz_bytes):,}, raw={len(raw_buf):,}) and {summary_path} in {time.time() - t0:.2f}s"
    )


if __name__ == "__main__":
    main()
