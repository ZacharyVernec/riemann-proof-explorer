#!/usr/bin/env python3
"""Structural DAG analysis for the Lean 4 Riemann Hypothesis proof graph."""

from __future__ import annotations

import json
import math
import random
import sqlite3
import time
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

DB_PATH = Path("/home/ubuntu/riemann_proof/analysis/data/graph.sqlite")
META_PATH = Path("/home/ubuntu/riemann_proof/analysis/data/meta.json")
OUT_DIR = Path("/home/ubuntu/riemann_proof/analysis/proof_spine")
METRICS_PATH = OUT_DIR / "spine_metrics.json"


def percentile_sorted(vals: list[int], q: float) -> float:
    if not vals:
        return 0.0
    if len(vals) == 1:
        return float(vals[0])
    idx = q * (len(vals) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(vals[lo])
    frac = idx - lo
    return vals[lo] * (1.0 - frac) + vals[hi] * frac


def load_graph() -> tuple[list[tuple[Any, ...]], list[list[int]], list[list[int]], int]:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    nodes = conn.execute(
        """
        SELECT id, name, rel_path, dir_path, top_dir, depth2_dir, depth3_dir,
               lines, bytes, n_theorems, n_lemmas, n_defs, n_structures, n_other_decls,
               external_imports, reachable_from_main, dist_from_main, height_from_leaves,
               in_degree, in_degree_main, out_degree
        FROM modules
        ORDER BY id
        """
    ).fetchall()
    n = len(nodes)
    adj_out: list[list[int]] = [[] for _ in range(n)]
    adj_in: list[list[int]] = [[] for _ in range(n)]
    for s, d in conn.execute("SELECT src_id, dst_id FROM edges ORDER BY src_id, dst_id"):
        u = s - 1
        v = d - 1
        adj_out[u].append(v)
        adj_in[v].append(u)
    conn.close()

    main_candidates = [r[0] - 1 for r in nodes if r[1] == "Main"]
    assert len(main_candidates) == 1, f"Expected 1 Main node, got {main_candidates}"
    return nodes, adj_out, adj_in, main_candidates[0]


def fetch_declarations_for(mod_ids: set[int]) -> dict[int, list[dict[str, Any]]]:
    if not mod_ids:
        return {}
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    id_list = sorted(mod_ids)
    # Query in chunks to stay well under SQLite parameter limit
    for start in range(0, len(id_list), 500):
        chunk = id_list[start : start + 500]
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"SELECT module_id, kind, name, line_no FROM declarations WHERE module_id IN ({placeholders}) ORDER BY module_id, line_no",
            chunk,
        ).fetchall()
        for mid, kind, dname, line_no in rows:
            out[mid].append({"kind": kind, "name": dname, "line_no": line_no})
    conn.close()
    return out


def verify_bfs_and_rpo(
    nodes: list[tuple[Any, ...]],
    adj_out: list[list[int]],
    main_idx: int,
) -> tuple[list[int], list[int], list[int], list[int], list[int]]:
    n = len(nodes)
    # 1. Independent BFS from Main
    dist = [-1] * n
    dist[main_idx] = 0
    q: deque[int] = deque([main_idx])
    reached = 0
    while q:
        u = q.popleft()
        reached += 1
        du1 = dist[u] + 1
        for v in adj_out[u]:
            if dist[v] == -1:
                dist[v] = du1
                q.append(v)

    assert reached == n, f"Expected {n} reachable nodes, got {reached}"
    dist_mismatches = sum(1 for i in range(n) if dist[i] != nodes[i][16])
    assert dist_mismatches == 0, f"Found {dist_mismatches} dist_from_main mismatches"

    # 2. Iterative DFS postorder from Main
    visited = [False] * n
    postorder: list[int] = []
    stack: list[tuple[int, int]] = [(main_idx, 0)]
    visited[main_idx] = True
    while stack:
        u, pos = stack[-1]
        nbrs = adj_out[u]
        if pos < len(nbrs):
            stack[-1] = (u, pos + 1)
            v = nbrs[pos]
            if not visited[v]:
                visited[v] = True
                stack.append((v, 0))
        else:
            stack.pop()
            postorder.append(u)

    assert len(postorder) == n, f"DFS visited {len(postorder)} != {n}"
    rpo = postorder[::-1]
    rpo_num = [0] * n
    for pos, u in enumerate(rpo):
        rpo_num[u] = pos

    # Confirm strict DAG property: every edge u -> v has rpo_num[u] < rpo_num[v]
    for u in range(n):
        ru = rpo_num[u]
        for v in adj_out[u]:
            assert ru < rpo_num[v], f"Cycle or non-DAG edge detected: {u} -> {v}"

    # 3. Independently verify height_from_leaves in bottom-up postorder
    height = [0] * n
    for u in postorder:
        nbrs = adj_out[u]
        if nbrs:
            height[u] = 1 + max(height[v] for v in nbrs)
    h_mismatches = sum(1 for i in range(n) if height[i] != nodes[i][17])
    assert h_mismatches == 0, f"Found {h_mismatches} height_from_leaves mismatches"

    return dist, height, postorder, rpo, rpo_num


def compute_dominators(
    nodes: list[tuple[Any, ...]],
    adj_out: list[list[int]],
    adj_in: list[list[int]],
    main_idx: int,
    postorder: list[int],
    rpo: list[int],
    rpo_num: list[int],
) -> tuple[list[int], list[int], list[int], list[int], list[int], list[int], int]:
    """Exact Cooper-Harvey-Kennedy iterative dominator algorithm."""
    n = len(nodes)
    idom = [-1] * n
    idom[main_idx] = main_idx

    def intersect(b1: int, b2: int) -> int:
        f1, f2 = b1, b2
        while f1 != f2:
            while rpo_num[f1] > rpo_num[f2]:
                f1 = idom[f1]
            while rpo_num[f2] > rpo_num[f1]:
                f2 = idom[f2]
        return f1

    passes = 0
    changed = True
    while changed:
        changed = False
        passes += 1
        for b in rpo[1:]:
            new_idom = -1
            for p in adj_in[b]:
                if idom[p] != -1:
                    if new_idom == -1:
                        new_idom = p
                    else:
                        new_idom = intersect(p, new_idom)
            assert new_idom != -1
            if idom[b] != new_idom:
                idom[b] = new_idom
                changed = True

    # Build dominator tree children, depth, subtree size, lines, theorems
    dom_depth = [0] * n
    dom_children: list[list[int]] = [[] for _ in range(n)]
    for u in rpo[1:]:
        p = idom[u]
        dom_children[p].append(u)
        dom_depth[u] = dom_depth[p] + 1

    dom_size = [1] * n
    dom_lines = [nodes[i][7] for i in range(n)]
    dom_theorems = [nodes[i][9] for i in range(n)]
    for u in postorder:
        if u != main_idx:
            p = idom[u]
            dom_size[p] += dom_size[u]
            dom_lines[p] += dom_lines[u]
            dom_theorems[p] += dom_theorems[u]

    assert dom_size[main_idx] == n, f"Root dom_size={dom_size[main_idx]} != {n}"
    for u in range(n):
        child_sum = sum(dom_size[c] for c in dom_children[u])
        assert child_sum + 1 == dom_size[u], f"Tree invariant broken at {u}"

    # Verify top 40 non-Main dominators by direct cut-BFS from Main
    top40 = [i for i in sorted(range(n), key=lambda x: (-dom_size[x], x)) if i != main_idx][:40]
    for target in top40:
        vis = [False] * n
        vis[main_idx] = True
        q: deque[int] = deque([main_idx])
        reached_wo = 0
        while q:
            u = q.popleft()
            reached_wo += 1
            for v in adj_out[u]:
                if v != target and not vis[v]:
                    vis[v] = True
                    q.append(v)
        cut_count = n - reached_wo
        assert cut_count == dom_size[target], (
            f"Dominator verification failed for {nodes[target][1]}: cut={cut_count}, dom_size={dom_size[target]}"
        )

    return idom, dom_depth, dom_size, dom_lines, dom_theorems, top40, passes


def compute_critical_paths(
    nodes: list[tuple[Any, ...]],
    adj_out: list[list[int]],
    main_idx: int,
    height: list[int],
    postorder: list[int],
) -> dict[str, Any]:
    n = len(nodes)
    max_h = height[main_idx]
    assert max_h == max(height), "Main should have maximum height"

    # Count longest paths from each node down to a leaf
    crit_ways = [0] * n
    for u in postorder:
        hu = height[u]
        if hu == 0:
            crit_ways[u] = 1
        else:
            crit_ways[u] = sum(crit_ways[v] for v in adj_out[u] if height[v] == hu - 1)

    # Extract entire critical-path subgraph reachable from Main
    on_crit = [False] * n
    on_crit[main_idx] = True
    q: deque[int] = deque([main_idx])
    crit_edges: list[tuple[int, int]] = []
    crit_by_h: list[list[int]] = [[] for _ in range(max_h + 1)]
    while q:
        u = q.popleft()
        hu = height[u]
        crit_by_h[hu].append(u)
        for v in adj_out[u]:
            if height[v] == hu - 1:
                crit_edges.append((u, v))
                if not on_crit[v]:
                    on_crit[v] = True
                    q.append(v)

    crit_nodes = [i for i in range(n) if on_crit[i]]
    mandatory_heights = sum(1 for h in range(max_h + 1) if len(crit_by_h[h]) == 1)

    # Reconstruct canonical longest chain (deterministic: highest crit_ways, then lowest id)
    canonical_chain: list[int] = [main_idx]
    curr = main_idx
    while height[curr] > 0:
        hc = height[curr]
        cands = [v for v in adj_out[curr] if height[v] == hc - 1]
        assert cands, f"Dead end on critical path at {curr}"
        cands.sort(key=lambda v: (-crit_ways[v], v))
        curr = cands[0]
        canonical_chain.append(curr)
    assert len(canonical_chain) == max_h + 1

    # Also compute longest chain strictly within each top_dir
    top_dirs = [r[4] for r in nodes]
    intra_height = [0] * n
    for u in postorder:
        tu = top_dirs[u]
        best = 0
        for v in adj_out[u]:
            if top_dirs[v] == tu:
                cand = 1 + intra_height[v]
                if cand > best:
                    best = cand
        intra_height[u] = best

    intra_best_by_top: dict[str, dict[str, Any]] = {}
    for td in sorted(set(top_dirs)):
        best_u = max((i for i in range(n) if top_dirs[i] == td), key=lambda x: (intra_height[x], -x))
        chain_names = [nodes[best_u][1]]
        cur = best_u
        while intra_height[cur] > 0:
            nxt = [v for v in adj_out[cur] if top_dirs[v] == td and intra_height[v] == intra_height[cur] - 1]
            nxt.sort(key=lambda x: (-intra_height[x], x))
            cur = nxt[0]
            chain_names.append(nodes[cur][1])
        intra_best_by_top[td] = {
            "max_intra_edges": intra_height[best_u],
            "start_module": nodes[best_u][1],
            "end_module": chain_names[-1],
            "chain_sample_head": chain_names[:5],
            "chain_sample_tail": chain_names[-5:],
        }

    return {
        "max_edges": max_h,
        "max_nodes": max_h + 1,
        "total_max_length_paths": crit_ways[main_idx],
        "subgraph_node_count": len(crit_nodes),
        "subgraph_edge_count": len(crit_edges),
        "mandatory_single_node_heights": mandatory_heights,
        "branching_heights": [
            {
                "height": h,
                "count": len(crit_by_h[h]),
                "modules": [nodes[u][1] for u in sorted(crit_by_h[h], key=lambda x: -crit_ways[x])],
            }
            for h in range(max_h, -1, -1)
            if len(crit_by_h[h]) > 1
        ],
        "canonical_chain_ids": canonical_chain,
        "subgraph_node_ids": crit_nodes,
        "subgraph_edges_indices": crit_edges,
        "crit_ways": crit_ways,
        "crit_by_h": crit_by_h,
        "intra_dir_longest": intra_best_by_top,
    }


def compute_paths_and_bridges(
    nodes: list[tuple[Any, ...]],
    adj_out: list[list[int]],
    adj_in: list[list[int]],
    main_idx: int,
    postorder: list[int],
    rpo: list[int],
    n_brandes_samples: int = 1200,
) -> dict[str, Any]:
    n = len(nodes)
    top_dirs = [r[4] for r in nodes]
    d2_dirs = [r[5] for r in nodes]

    # 1. Exact Main-to-leaf DAG path counts
    p_from_main = [0] * n
    p_from_main[main_idx] = 1
    for u in rpo:
        pu = p_from_main[u]
        for v in adj_out[u]:
            p_from_main[v] += pu

    p_to_leaf = [0] * n
    for u in postorder:
        nbrs = adj_out[u]
        if not nbrs:
            p_to_leaf[u] = 1
        else:
            p_to_leaf[u] = sum(p_to_leaf[v] for v in nbrs)

    total_m2l_paths = p_to_leaf[main_idx]
    path_stress = [p_from_main[i] * p_to_leaf[i] for i in range(n)]

    # 2. Exact direct cross-directory boundary degrees
    cross_top_in = [0] * n
    cross_top_out = [0] * n
    cross_d2_in = [0] * n
    cross_d2_out = [0] * n
    imp_top_sets: list[set[str]] = [set() for _ in range(n)]
    exp_top_sets: list[set[str]] = [set() for _ in range(n)]
    imp_d2_sets: list[set[str]] = [set() for _ in range(n)]
    exp_d2_sets: list[set[str]] = [set() for _ in range(n)]

    top_edge_matrix: Counter[tuple[str, str]] = Counter()
    for u in range(n):
        tu = top_dirs[u]
        d2u = d2_dirs[u]
        for v in adj_out[u]:
            tv = top_dirs[v]
            d2v = d2_dirs[v]
            top_edge_matrix[(tu, tv)] += 1
            if tu != tv:
                cross_top_out[u] += 1
                cross_top_in[v] += 1
                exp_top_sets[u].add(tv)
                imp_top_sets[v].add(tu)
            if d2u != d2v:
                cross_d2_out[u] += 1
                cross_d2_in[v] += 1
                exp_d2_sets[u].add(d2v)
                imp_d2_sets[v].add(d2u)

    # 3. Stratified Horvitz-Thompson weighted Brandes betweenness (shortest directed paths)
    by_top: dict[str, list[int]] = defaultdict(list)
    for i, td in enumerate(top_dirs):
        by_top[td].append(i)

    rng = random.Random(20261120)
    samples: list[tuple[int, float]] = []  # (node_idx, ht_weight)
    stratum_info: dict[str, dict[str, Any]] = {}
    for td, idxs in sorted(by_top.items()):
        # Ensure small directories are well-represented, but keep Horvitz-Thompson weights exact!
        target_k = max(min(len(idxs), 5), int(round(n_brandes_samples * len(idxs) / n)))
        k = min(len(idxs), target_k)
        chosen = idxs if k == len(idxs) else rng.sample(idxs, k)
        w_s = len(idxs) / k
        for s in chosen:
            samples.append((s, w_s))
        stratum_info[td] = {"total": len(idxs), "sampled": k, "weight": round(w_s, 4)}

    bc_all = [0.0] * n
    bc_cross_top = [0.0] * n
    bc_strict_transit = [0.0] * n

    sigma = [0.0] * n
    dist = [-1] * n
    delta_all = [0.0] * n
    delta_cross = [0.0] * n
    preds: list[list[int]] = [[] for _ in range(n)]

    for s, w_s in samples:
        ts = top_dirs[s]
        order: list[int] = []
        q: deque[int] = deque([s])
        dist[s] = 0
        sigma[s] = 1.0
        while q:
            v = q.popleft()
            order.append(v)
            dv = dist[v]
            sv = sigma[v]
            for w in adj_out[v]:
                dw = dist[w]
                if dw == -1:
                    dist[w] = dv + 1
                    q.append(w)
                    sigma[w] = sv
                    preds[w].append(v)
                elif dw == dv + 1:
                    sigma[w] += sv
                    preds[w].append(v)

        for w in reversed(order):
            if w == s:
                continue
            sw = sigma[w]
            dw_all = delta_all[w]
            dw_cross = delta_cross[w]
            is_cross_target = 1.0 if top_dirs[w] != ts else 0.0
            coeff_all = (1.0 + dw_all) / sw
            coeff_cross = (is_cross_target + dw_cross) / sw
            for v in preds[w]:
                sv = sigma[v]
                delta_all[v] += sv * coeff_all
                delta_cross[v] += sv * coeff_cross
            bc_all[w] += w_s * dw_all
            bc_cross_top[w] += w_s * dw_cross
            if top_dirs[w] != ts:
                bc_strict_transit[w] += w_s * dw_cross

        for u in order:
            dist[u] = -1
            sigma[u] = 0.0
            delta_all[u] = 0.0
            delta_cross[u] = 0.0
            preds[u].clear()

    return {
        "total_m2l_paths": total_m2l_paths,
        "p_from_main": p_from_main,
        "p_to_leaf": p_to_leaf,
        "path_stress": path_stress,
        "cross_top_in": cross_top_in,
        "cross_top_out": cross_top_out,
        "cross_d2_in": cross_d2_in,
        "cross_d2_out": cross_d2_out,
        "imp_top_cnt": [len(s) for s in imp_top_sets],
        "exp_top_cnt": [len(s) for s in exp_top_sets],
        "imp_d2_cnt": [len(s) for s in imp_d2_sets],
        "exp_d2_cnt": [len(s) for s in exp_d2_sets],
        "top_edge_matrix": top_edge_matrix,
        "brandes_sample_count": len(samples),
        "brandes_strata": stratum_info,
        "bc_all": bc_all,
        "bc_cross_top": bc_cross_top,
        "bc_strict_transit": bc_strict_transit,
    }


def node_record(
    idx: int,
    nodes: list[tuple[Any, ...]],
    decls_map: dict[int, list[dict[str, Any]]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    r = nodes[idx]
    rec: dict[str, Any] = {
        "id": r[0],
        "name": r[1],
        "rel_path": r[2],
        "top_dir": r[4],
        "depth2_dir": r[5],
        "lines": r[7],
        "bytes": r[8],
        "n_theorems": r[9],
        "n_lemmas": r[10],
        "n_defs": r[11],
        "n_structures": r[12],
        "n_other_decls": r[13],
        "external_imports": json.loads(r[14]),
        "dist_from_main": r[16],
        "height_from_leaves": r[17],
        "in_degree": r[18],
        "out_degree": r[20],
    }
    if decls_map is not None:
        dlist = decls_map.get(r[0], [])
        rec["decl_count"] = len(dlist)
        rec["sample_decls"] = dlist[:15]
    if extra:
        rec.update(extra)
    return rec


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = json.loads(META_PATH.read_text())

    nodes, adj_out, adj_in, main_idx = load_graph()
    n = len(nodes)
    edge_count = sum(len(x) for x in adj_out)
    assert n == meta["total_files"] == 175187
    assert edge_count == meta["total_internal_edges"] == 753261

    # 1. Reachability, RPO, DAG & Height verification
    dist, height, postorder, rpo, rpo_num = verify_bfs_and_rpo(nodes, adj_out, main_idx)
    zero_in = [nodes[i][1] for i in range(n) if nodes[i][18] == 0]
    leaves = [i for i in range(n) if nodes[i][20] == 0]

    # 2. Stratigraphic Layering
    top_dirs_all = sorted({r[4] for r in nodes})
    max_dist = max(dist)
    max_height = max(height)

    dist_hist: list[dict[str, Any]] = []
    for d in range(max_dist + 1):
        idxs = [i for i in range(n) if dist[i] == d]
        by_td = Counter(nodes[i][4] for i in idxs)
        dist_hist.append(
            {
                "dist": d,
                "files": len(idxs),
                "lines": sum(nodes[i][7] for i in idxs),
                "theorems": sum(nodes[i][9] for i in idxs),
                "defs": sum(nodes[i][11] for i in idxs),
                "by_top_dir": {td: by_td[td] for td in top_dirs_all if by_td[td] > 0},
            }
        )

    height_hist: list[dict[str, Any]] = []
    for h in range(max_height + 1):
        idxs = [i for i in range(n) if height[i] == h]
        by_td = Counter(nodes[i][4] for i in idxs)
        height_hist.append(
            {
                "height": h,
                "files": len(idxs),
                "lines": sum(nodes[i][7] for i in idxs),
                "theorems": sum(nodes[i][9] for i in idxs),
                "defs": sum(nodes[i][11] for i in idxs),
                "by_top_dir": {td: by_td[td] for td in top_dirs_all if by_td[td] > 0},
            }
        )

    top_dir_profiles: list[dict[str, Any]] = []
    for td in top_dirs_all:
        idxs = [i for i in range(n) if nodes[i][4] == td]
        ds = sorted(dist[i] for i in idxs)
        hs = sorted(height[i] for i in idxs)
        leaf_cnt = sum(1 for i in idxs if nodes[i][20] == 0)
        top_dir_profiles.append(
            {
                "top_dir": td,
                "files": len(idxs),
                "lines": sum(nodes[i][7] for i in idxs),
                "bytes": sum(nodes[i][8] for i in idxs),
                "theorems": sum(nodes[i][9] for i in idxs),
                "lemmas": sum(nodes[i][10] for i in idxs),
                "defs": sum(nodes[i][11] for i in idxs),
                "structures": sum(nodes[i][12] for i in idxs),
                "leaf_files": leaf_cnt,
                "leaf_pct": round(100.0 * leaf_cnt / len(idxs), 2),
                "dist_min": ds[0],
                "dist_p10": round(percentile_sorted(ds, 0.10), 2),
                "dist_median": round(percentile_sorted(ds, 0.50), 2),
                "dist_mean": round(sum(ds) / len(ds), 2),
                "dist_p90": round(percentile_sorted(ds, 0.90), 2),
                "dist_max": ds[-1],
                "height_min": hs[0],
                "height_p10": round(percentile_sorted(hs, 0.10), 2),
                "height_median": round(percentile_sorted(hs, 0.50), 2),
                "height_mean": round(sum(hs) / len(hs), 2),
                "height_p90": round(percentile_sorted(hs, 0.90), 2),
                "height_max": hs[-1],
            }
        )
    top_dir_profiles.sort(key=lambda x: (x["dist_min"], -x["files"]))

    # 3. Critical Path
    crit = compute_critical_paths(nodes, adj_out, main_idx, height, postorder)

    # 4. Dominator Tree
    idom, dom_depth, dom_size, dom_lines, dom_theorems, verified_top40, chk_passes = compute_dominators(
        nodes, adj_out, adj_in, main_idx, postorder, rpo, rpo_num
    )

    # 5. Hubs, Path Stress & Cross-Directory Bridges
    br = compute_paths_and_bridges(nodes, adj_out, adj_in, main_idx, postorder, rpo, n_brandes_samples=1200)

    # Leaf Audit details
    leaf_by_top = Counter(nodes[i][4] for i in leaves)
    leaf_by_d2 = Counter(nodes[i][5] for i in leaves)
    leaf_ext_counts = Counter()
    leaf_no_ext = 0
    leaf_one_line = 0
    leaf_zero_decl = 0
    for i in leaves:
        exts = json.loads(nodes[i][14])
        if not exts:
            leaf_no_ext += 1
        for ex in exts:
            leaf_ext_counts[ex] += 1
        if nodes[i][7] <= 1:
            leaf_one_line += 1
        if sum(nodes[i][9:14]) == 0:
            leaf_zero_decl += 1

    top_leaf_importers = sorted(leaves, key=lambda i: (-nodes[i][18], -nodes[i][7], i))[:20]
    top_leaf_lines = sorted(leaves, key=lambda i: (-nodes[i][7], -nodes[i][18], i))[:15]

    # Rankings for Dominators, Hubs, Bridges
    top_dom_idxs = sorted(range(n), key=lambda i: (-dom_size[i], i))[:100]
    top_dom_non_trivial_counts = {
        "gt_1": sum(1 for s in dom_size if s > 1),
        "ge_10": sum(1 for s in dom_size if s >= 10),
        "ge_100": sum(1 for s in dom_size if s >= 100),
        "ge_500": sum(1 for s in dom_size if s >= 500),
        "ge_1000": sum(1 for s in dom_size if s >= 1000),
        "ge_5000": sum(1 for s in dom_size if s >= 5000),
    }

    # Dominator skeleton: all nodes with dom_size >= 300 (so we capture clean multi-level spine)
    skeleton_idxs = sorted([i for i in range(n) if dom_size[i] >= 300], key=lambda i: (dom_depth[i], -dom_size[i], i))

    top_in_idxs = sorted(range(n), key=lambda i: (-nodes[i][18], -nodes[i][7], i))[:30]
    top_out_idxs = sorted(range(n), key=lambda i: (-nodes[i][20], -nodes[i][18], i))[:30]

    top_cross_brandes_idxs = sorted(range(n), key=lambda i: (-br["bc_cross_top"][i], i))[:30]
    top_cross_prod_idxs = sorted(
        range(n),
        key=lambda i: (
            -(br["cross_top_in"][i] * br["cross_top_out"][i]),
            -(br["imp_top_cnt"][i] * br["exp_top_cnt"][i]),
            i,
        ),
    )[:30]
    top_d2_prod_idxs = sorted(
        range(n),
        key=lambda i: (
            -(br["cross_d2_in"][i] * br["cross_d2_out"][i]),
            -(br["imp_d2_cnt"][i] * br["exp_d2_cnt"][i]),
            i,
        ),
    )[:30]
    top_stress_idxs = sorted(
        [i for i in range(n) if i != main_idx],
        key=lambda i: (-br["path_stress"][i], i),
    )[:30]

    # Collect declarations for all featured nodes
    featured_ids: set[int] = set()
    for grp in [
        top_dom_idxs[:50],
        crit["canonical_chain_ids"],
        crit["subgraph_node_ids"],
        top_in_idxs,
        top_out_idxs,
        top_cross_brandes_idxs,
        top_cross_prod_idxs,
        top_d2_prod_idxs,
        top_stress_idxs,
        top_leaf_importers,
        top_leaf_lines,
        [i for i in range(n) if nodes[i][4] in ("(root)", "Supplements", "BuildAid")],
    ]:
        for idx in grp:
            featured_ids.add(nodes[idx][0])
    decls_map = fetch_declarations_for(featured_ids)

    def dom_lineage(idx: int) -> list[str]:
        chain = [nodes[idx][1]]
        cur = idx
        while cur != main_idx:
            cur = idom[cur]
            chain.append(nodes[cur][1])
        chain.reverse()
        return chain

    # Build entry layer records (dist <= 3)
    entry_layer = [
        node_record(
            i,
            nodes,
            decls_map,
            {
                "idom_name": nodes[idom[i]][1],
                "dom_subtree_size": dom_size[i],
                "imports": [nodes[v][1] for v in adj_out[i]],
            },
        )
        for i in sorted([x for x in range(n) if dist[x] <= 3], key=lambda x: (dist[x], -dom_size[x], x))
    ]

    build_aid_records = [
        node_record(
            i,
            nodes,
            decls_map,
            {
                "importers": [nodes[u][1] for u in adj_in[i]],
                "dom_subtree_size": dom_size[i],
            },
        )
        for i in sorted([x for x in range(n) if nodes[x][4] == "BuildAid"], key=lambda x: nodes[x][1])
    ]

    dom_records = [
        node_record(
            i,
            nodes,
            decls_map,
            {
                "rank": rank,
                "idom_id": nodes[idom[i]][0],
                "idom_name": nodes[idom[i]][1],
                "dom_depth": dom_depth[i],
                "dom_subtree_size": dom_size[i],
                "dom_strict_subtree_size": dom_size[i] - 1,
                "dom_subtree_pct": round(100.0 * dom_size[i] / n, 3),
                "dom_subtree_lines": dom_lines[i],
                "dom_subtree_theorems": dom_theorems[i],
                "dom_lineage": dom_lineage(i),
                "direct_imports": [nodes[v][1] for v in adj_out[i]],
                "direct_importers_sample": [nodes[u][1] for u in adj_in[i][:10]],
            },
        )
        for rank, i in enumerate(top_dom_idxs, 1)
    ]

    skeleton_records = [
        {
            "id": nodes[i][0],
            "name": nodes[i][1],
            "rel_path": nodes[i][2],
            "top_dir": nodes[i][4],
            "idom_id": nodes[idom[i]][0],
            "idom_name": nodes[idom[i]][1],
            "dom_depth": dom_depth[i],
            "dom_subtree_size": dom_size[i],
            "dom_subtree_lines": dom_lines[i],
            "dist_from_main": dist[i],
            "height_from_leaves": height[i],
            "in_degree": nodes[i][18],
            "out_degree": nodes[i][20],
        }
        for i in skeleton_idxs
    ]

    crit_chain_records = [
        node_record(
            i,
            nodes,
            decls_map,
            {
                "step": step,
                "crit_ways_to_leaf": crit["crit_ways"][i],
                "height_width_in_crit_subgraph": len(crit["crit_by_h"][height[i]]),
                "dom_subtree_size": dom_size[i],
            },
        )
        for step, i in enumerate(crit["canonical_chain_ids"])
    ]

    crit_subgraph_nodes = [
        {
            "id": nodes[i][0],
            "name": nodes[i][1],
            "rel_path": nodes[i][2],
            "top_dir": nodes[i][4],
            "dist_from_main": dist[i],
            "height_from_leaves": height[i],
            "in_degree": nodes[i][18],
            "out_degree": nodes[i][20],
            "crit_ways": crit["crit_ways"][i],
            "dom_subtree_size": dom_size[i],
        }
        for i in sorted(crit["subgraph_node_ids"], key=lambda x: (-height[x], x))
    ]
    crit_subgraph_edges = [
        {"src": nodes[u][1], "dst": nodes[v][1], "src_h": height[u], "dst_h": height[v]}
        for u, v in crit["subgraph_edges_indices"]
    ]

    def hub_extra(i: int) -> dict[str, Any]:
        tot_p = br["total_m2l_paths"]
        ps = br["path_stress"][i]
        return {
            "cross_top_in": br["cross_top_in"][i],
            "cross_top_out": br["cross_top_out"][i],
            "cross_top_prod": br["cross_top_in"][i] * br["cross_top_out"][i],
            "distinct_importer_top_dirs": br["imp_top_cnt"][i],
            "distinct_imported_top_dirs": br["exp_top_cnt"][i],
            "cross_d2_in": br["cross_d2_in"][i],
            "cross_d2_out": br["cross_d2_out"][i],
            "cross_d2_prod": br["cross_d2_in"][i] * br["cross_d2_out"][i],
            "distinct_importer_d2_dirs": br["imp_d2_cnt"][i],
            "distinct_imported_d2_dirs": br["exp_d2_cnt"][i],
            "brandes_weighted_all": round(br["bc_all"][i], 2),
            "brandes_weighted_cross_top": round(br["bc_cross_top"][i], 2),
            "brandes_weighted_strict_transit": round(br["bc_strict_transit"][i], 2),
            "path_stress_fraction": round(ps / tot_p, 6) if tot_p else 0.0,
            "path_stress_log10": round(math.log10(ps), 3) if ps > 0 else 0.0,
            "path_stress_exact": str(ps),
            "dom_subtree_size": dom_size[i],
        }

    top_in_records = [node_record(i, nodes, decls_map, {"rank": r, **hub_extra(i)}) for r, i in enumerate(top_in_idxs, 1)]
    top_out_records = [node_record(i, nodes, decls_map, {"rank": r, **hub_extra(i)}) for r, i in enumerate(top_out_idxs, 1)]
    top_cross_brandes_records = [
        node_record(i, nodes, decls_map, {"rank": r, **hub_extra(i)}) for r, i in enumerate(top_cross_brandes_idxs, 1)
    ]
    top_cross_prod_records = [
        node_record(i, nodes, decls_map, {"rank": r, **hub_extra(i)}) for r, i in enumerate(top_cross_prod_idxs, 1)
    ]
    top_d2_prod_records = [
        node_record(i, nodes, decls_map, {"rank": r, **hub_extra(i)}) for r, i in enumerate(top_d2_prod_idxs, 1)
    ]
    top_stress_records = [
        node_record(i, nodes, decls_map, {"rank": r, **hub_extra(i)}) for r, i in enumerate(top_stress_idxs, 1)
    ]

    # Top-dir transition matrix
    top_edge_matrix_list = [
        {"src_top_dir": s_td, "dst_top_dir": d_td, "edges": cnt}
        for (s_td, d_td), cnt in sorted(br["top_edge_matrix"].items(), key=lambda x: (-x[1], x[0]))
    ]

    metrics = {
        "audit": {
            "total_files": n,
            "reachable_from_main": n,
            "unreachable_from_main": 0,
            "total_internal_edges": edge_count,
            "is_dag": True,
            "zero_in_degree_sources": zero_in,
            "leaf_count": len(leaves),
            "max_dist_from_main": max_dist,
            "max_height_from_leaves": max_height,
            "chk_passes": chk_passes,
            "verified_cut_dominators": len(verified_top40),
            "total_main_to_leaf_paths_exact": str(br["total_m2l_paths"]),
            "total_main_to_leaf_paths_log10": round(math.log10(br["total_m2l_paths"]), 3),
            "elapsed_seconds": round(time.time() - t0, 2),
        },
        "leaf_and_entry_audit": {
            "leaf_count": len(leaves),
            "leaf_lines": sum(nodes[i][7] for i in leaves),
            "leaf_theorems": sum(nodes[i][9] for i in leaves),
            "leaf_lemmas": sum(nodes[i][10] for i in leaves),
            "leaf_defs": sum(nodes[i][11] for i in leaves),
            "leaf_structures": sum(nodes[i][12] for i in leaves),
            "leaf_no_external_imports": leaf_no_ext,
            "leaf_le_1_line": leaf_one_line,
            "leaf_zero_decls": leaf_zero_decl,
            "leaves_by_top_dir": dict(leaf_by_top.most_common()),
            "top_20_leaf_depth2_dirs": [{"depth2_dir": k, "count": v} for k, v in leaf_by_d2.most_common(20)],
            "top_20_leaf_external_imports": [{"import": k, "count": v} for k, v in leaf_ext_counts.most_common(20)],
            "top_20_most_imported_leaves": [node_record(i, nodes, decls_map) for i in top_leaf_importers],
            "top_15_largest_leaves": [node_record(i, nodes, decls_map) for i in top_leaf_lines],
            "entry_layers_dist_le_3": entry_layer,
            "build_aid_modules": build_aid_records,
        },
        "stratigraphy": {
            "top_dir_profiles": top_dir_profiles,
            "dist_histogram": dist_hist,
            "height_histogram": height_hist,
            "top_dir_edge_matrix": top_edge_matrix_list,
        },
        "critical_path": {
            "max_edges": crit["max_edges"],
            "max_nodes": crit["max_nodes"],
            "total_max_length_paths": crit["total_max_length_paths"],
            "subgraph_node_count": crit["subgraph_node_count"],
            "subgraph_edge_count": crit["subgraph_edge_count"],
            "mandatory_single_node_heights": crit["mandatory_single_node_heights"],
            "branching_heights": crit["branching_heights"],
            "canonical_chain": crit_chain_records,
            "subgraph_nodes": crit_subgraph_nodes,
            "subgraph_edges": crit_subgraph_edges,
            "intra_dir_longest": crit["intra_dir_longest"],
        },
        "dominators": {
            "subtree_size_counts": top_dom_non_trivial_counts,
            "top_100_bottlenecks": dom_records,
            "skeleton_ge_300": skeleton_records,
        },
        "hubs_and_bridges": {
            "brandes_config": {
                "sample_count": br["brandes_sample_count"],
                "weighting": "Horvitz-Thompson inverse stratum probability (N_top_dir / k_top_dir)",
                "seed": 20261120,
                "strata": br["brandes_strata"],
            },
            "top_30_in_degree": top_in_records,
            "top_30_out_degree": top_out_records,
            "top_30_cross_dir_brandes": top_cross_brandes_records,
            "top_30_cross_top_dir_fan_bridges": top_cross_prod_records,
            "top_30_cross_depth2_fan_bridges": top_d2_prod_records,
            "top_30_main_to_leaf_path_stress": top_stress_records,
        },
    }

    METRICS_PATH.write_text(json.dumps(metrics, indent=2))
    print(f"Wrote {METRICS_PATH} in {time.time() - t0:.2f}s ({METRICS_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
