#!/usr/bin/env python3
"""Aggregate directory-level dependency graphs from graph.sqlite and generate static + interactive visualizations."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT / "lean" / "src"
DB_PATH = ROOT / "analysis" / "data" / "graph.sqlite"
META_PATH = ROOT / "analysis" / "data" / "meta.json"
OUT_DIR = SCRIPT_DIR

TOP_ORDER = [
    "(root)",
    "Supplements",
    "Development",
    "CompanionTheory",
    "PositivityTheory",
    "Formalism",
    "ReciprocityTheory",
    "GroundTheory",
    "Lemmata",
    "BuildAid",
]

TOP_COLORS = {
    "(root)": {"fill": "#1e293b", "border": "#94a3b8", "dot": "#334155", "font": "#f8fafc"},
    "Supplements": {"fill": "#312e81", "border": "#818cf8", "dot": "#3730a3", "font": "#f8fafc"},
    "Development": {"fill": "#1e3a8a", "border": "#60a5fa", "dot": "#1d4ed8", "font": "#f8fafc"},
    "CompanionTheory": {"fill": "#064e3b", "border": "#34d399", "dot": "#047857", "font": "#f8fafc"},
    "PositivityTheory": {"fill": "#701a75", "border": "#e879f9", "dot": "#86198f", "font": "#f8fafc"},
    "Formalism": {"fill": "#7c2d12", "border": "#fb923c", "dot": "#c2410c", "font": "#f8fafc"},
    "ReciprocityTheory": {"fill": "#134e4a", "border": "#2dd4bf", "dot": "#0f766e", "font": "#f8fafc"},
    "GroundTheory": {"fill": "#713f12", "border": "#facc15", "dot": "#a16207", "font": "#f8fafc"},
    "Lemmata": {"fill": "#3b0764", "border": "#c084fc", "dot": "#6b21a8", "font": "#f8fafc"},
    "BuildAid": {"fill": "#374151", "border": "#9ca3af", "dot": "#4b5563", "font": "#f8fafc"},
}

MAJOR_FORMALISM_HUBS = {
    "Formalism/LocalToGlobal",
    "Formalism/SharpRestriction",
    "Formalism/LocalRingCardinality",
    "Formalism/PeriodIntegrals",
    "Formalism/HermitianCurvature",
    "Formalism/RealPlaceAnalysis",
    "Formalism/SatakeDualWeyl",
    "Formalism/PairingDivisors",
    "Formalism/GammaFactorNonvanishing",
}

MAJOR_GROUND_KEEP = {
    "GroundTheory/HeightsAndTheta",
    "GroundTheory/AutomorphicForms",
    "GroundTheory/ProfiniteCohomology",
    "GroundTheory/GlobalFields",
    "GroundTheory/PAdicHodge",
    "GroundTheory/ArithmeticGeometry",
    "GroundTheory/LocalFields",
}

MAJOR_RECIPROCITY_KEEP = {
    "ReciprocityTheory/ReductiveGroups",
    "ReciprocityTheory/L2DbarEstimates",
    "ReciprocityTheory/AnalyticForms",
    "ReciprocityTheory/DualLattices",
    "ReciprocityTheory/SemistableReduction",
    "ReciprocityTheory/ClassFieldTheory",
    "ReciprocityTheory/GroupCohomology",
    "ReciprocityTheory/Chebotarev",
    "ReciprocityTheory/GeometryOfNumbers",
}


def tarjan_scc(nodes: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """Compute strongly connected components using iterative Tarjan's algorithm."""
    adj: dict[str, list[str]] = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)

    index_counter = 0
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    sccs: list[list[str]] = []

    for start in nodes:
        if start in indices:
            continue
        call_stack: list[tuple[str, int]] = [(start, 0)]
        indices[start] = lowlink[start] = index_counter
        index_counter += 1
        stack.append(start)
        on_stack.add(start)

        while call_stack:
            v, ni = call_stack[-1]
            neighbors = adj[v]
            if ni < len(neighbors):
                call_stack[-1] = (v, ni + 1)
                w = neighbors[ni]
                if w not in indices:
                    indices[w] = lowlink[w] = index_counter
                    index_counter += 1
                    stack.append(w)
                    on_stack.add(w)
                    call_stack.append((w, 0))
                elif w in on_stack:
                    if indices[w] < lowlink[v]:
                        lowlink[v] = indices[w]
            else:
                call_stack.pop()
                if call_stack:
                    parent = call_stack[-1][0]
                    if lowlink[v] < lowlink[parent]:
                        lowlink[parent] = lowlink[v]
                if lowlink[v] == indices[v]:
                    comp: list[str] = []
                    while True:
                        w = stack.pop()
                        on_stack.remove(w)
                        comp.append(w)
                        if w == v:
                            break
                    sccs.append(sorted(comp))

    sccs.sort(key=lambda c: (-len(c), c[0]))
    return sccs


def format_num(n: int) -> str:
    """Format integer with comma separators."""
    return f"{n:,}"


def sanitize_id(name: str) -> str:
    """Convert directory key into safe Mermaid / DOT identifier."""
    out = []
    for ch in name:
        if ch.isalnum() or ch == "_":
            out.append(ch)
        else:
            out.append("_")
    res = "".join(out)
    if res and res[0].isdigit():
        res = "n_" + res
    return res


def load_graph_data() -> dict[str, Any]:
    """Load modules, edges, and dir_stats from graph.sqlite and build aggregated structures."""
    t0 = time.time()
    meta = json.loads(META_PATH.read_text())
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    cur = conn.cursor()

    # Load modules into compact parallel structures indexed by module_id (1..N)
    n_max = cur.execute("SELECT MAX(id) FROM modules").fetchone()[0]
    mod_rel: list[str] = [""] * (n_max + 1)
    mod_top: list[str] = [""] * (n_max + 1)
    mod_d2: list[str] = [""] * (n_max + 1)
    mod_d3: list[str] = [""] * (n_max + 1)
    mod_lines = [0] * (n_max + 1)
    mod_bytes = [0] * (n_max + 1)
    mod_thm = [0] * (n_max + 1)
    mod_lem = [0] * (n_max + 1)
    mod_def = [0] * (n_max + 1)
    mod_str = [0] * (n_max + 1)
    mod_dist = [0] * (n_max + 1)
    mod_height = [0] * (n_max + 1)

    all_ids: list[int] = []
    reach_set: set[int] = set()
    for row in cur.execute(
        """
        SELECT id, rel_path, top_dir, depth2_dir, depth3_dir,
               lines, bytes, n_theorems, n_lemmas, n_defs, n_structures,
               COALESCE(dist_from_main, 0), height_from_leaves
        FROM modules
        WHERE reachable_from_main = 1
        """
    ):
        mid = row[0]
        all_ids.append(mid)
        reach_set.add(mid)
        mod_rel[mid] = row[1]
        mod_top[mid] = row[2]
        mod_d2[mid] = row[3]
        mod_d3[mid] = row[4]
        mod_lines[mid] = row[5]
        mod_bytes[mid] = row[6]
        mod_thm[mid] = row[7]
        mod_lem[mid] = row[8]
        mod_def[mid] = row[9]
        mod_str[mid] = row[10]
        mod_dist[mid] = row[11]
        mod_height[mid] = row[12]

    # Identify mixed directories (having both direct files and subdirectories)
    l1_direct: dict[str, int] = defaultdict(int)
    l1_subdirs: dict[str, set[str]] = defaultdict(set)
    l2_direct: dict[str, int] = defaultdict(int)
    l2_subdirs: dict[str, set[str]] = defaultdict(set)

    for mid in all_ids:
        t, d2, d3 = mod_top[mid], mod_d2[mid], mod_d3[mid]
        if d2 == t:
            l1_direct[t] += 1
        else:
            l1_subdirs[t].add(d2)
        if d3 == d2:
            l2_direct[d2] += 1
        else:
            l2_subdirs[d2].add(d3)

    mixed_l1 = {t for t in l1_direct if l1_direct[t] > 0 and len(l1_subdirs[t]) > 0}
    mixed_l2 = {d2 for d2 in l2_direct if l2_direct[d2] > 0 and len(l2_subdirs[d2]) > 0}

    # Assign hierarchical node IDs per module at L1, L2, L3
    # Node ID format: "L1:<key>", "L2:<key>", "L3:<key>"
    mod_tree_l1: list[str] = [""] * (n_max + 1)
    mod_tree_l2: list[str] = [""] * (n_max + 1)
    mod_tree_l3: list[str] = [""] * (n_max + 1)

    tree_nodes: dict[str, dict[str, Any]] = {}
    node_modules: dict[str, list[int]] = defaultdict(list)

    def ensure_node(
        nid: str,
        dir_key: str,
        label: str,
        level: int,
        top_dir: str,
        parent_id: str | None,
    ) -> None:
        if nid not in tree_nodes:
            tree_nodes[nid] = {
                "id": nid,
                "dir_key": dir_key,
                "label": label,
                "level": level,
                "top_dir": top_dir,
                "parent_id": parent_id,
                "children_ids": [],
                "is_leaf": True,
                "files": 0,
                "lines": 0,
                "bytes": 0,
                "theorems": 0,
                "lemmas": 0,
                "defs": 0,
                "structures": 0,
                "min_dist": None,
                "sum_dist": 0,
                "max_height": 0,
            }
            if parent_id is not None and parent_id in tree_nodes:
                pnode = tree_nodes[parent_id]
                pnode["children_ids"].append(nid)
                pnode["is_leaf"] = False

    for mid in all_ids:
        t, d2, d3 = mod_top[mid], mod_d2[mid], mod_d3[mid]
        n1 = f"L1:{t}"
        ensure_node(n1, t, t, 1, t, None)
        mod_tree_l1[mid] = n1

        # Determine L2 tree node (if L1 has subdirs)
        if len(l1_subdirs[t]) == 0:
            # L1 itself is a leaf (e.g. (root), BuildAid)
            n2 = n1
            n3 = n1
        else:
            if d2 == t:
                assert t in mixed_l1
                d2_tree_key = f"{t}/(direct)"
                n2 = f"L2:{d2_tree_key}"
                ensure_node(n2, t, "(direct files)", 2, t, n1)
                n3 = n2
            else:
                n2 = f"L2:{d2}"
                short2 = d2.split("/", 1)[1] if "/" in d2 else d2
                ensure_node(n2, d2, short2, 2, t, n1)
                if len(l2_subdirs[d2]) == 0:
                    n3 = n2
                else:
                    if d3 == d2:
                        assert d2 in mixed_l2
                        d3_tree_key = f"{d2}/(direct)"
                        n3 = f"L3:{d3_tree_key}"
                        ensure_node(n3, d2, "(direct files)", 3, t, n2)
                    else:
                        n3 = f"L3:{d3}"
                        short3 = d3.split("/", 2)[2] if d3.count("/") >= 2 else d3
                        ensure_node(n3, d3, short3, 3, t, n2)

        mod_tree_l2[mid] = n2
        mod_tree_l3[mid] = n3

        # Accumulate stats into every distinct ancestor node of this module
        seen_anc = []
        for anc in (n1, n2, n3):
            if anc not in seen_anc:
                seen_anc.append(anc)
                nd = tree_nodes[anc]
                nd["files"] += 1
                nd["lines"] += mod_lines[mid]
                nd["bytes"] += mod_bytes[mid]
                nd["theorems"] += mod_thm[mid]
                nd["lemmas"] += mod_lem[mid]
                nd["defs"] += mod_def[mid]
                nd["structures"] += mod_str[mid]
                dm = mod_dist[mid]
                if nd["min_dist"] is None or dm < nd["min_dist"]:
                    nd["min_dist"] = dm
                nd["sum_dist"] += dm
                if mod_height[mid] > nd["max_height"]:
                    nd["max_height"] = mod_height[mid]
                node_modules[anc].append(mid)

    for nd in tree_nodes.values():
        f = nd["files"]
        nd["avg_dist"] = round(nd["sum_dist"] / f, 2) if f else 0.0
        del nd["sum_dist"]
        nd["children_ids"].sort(
            key=lambda cid: (-tree_nodes[cid]["files"], tree_nodes[cid]["label"])
        )

    # Single linear pass over all 753,261 edges to aggregate:
    # - Canonical flat level 1 (top_dir), level 2 (depth2_dir), level 3 (depth3_dir) edges
    # - Leaf-to-leaf tree edges (using n3)
    # - Per-module cross-boundary out/in counts at L1, L2, L3
    e_l1_w: dict[tuple[str, str], int] = defaultdict(int)
    e_l1_s: dict[tuple[str, str], set[int]] = defaultdict(set)
    e_l1_d: dict[tuple[str, str], set[int]] = defaultdict(set)

    e_l2_w: dict[tuple[str, str], int] = defaultdict(int)
    e_l2_s: dict[tuple[str, str], set[int]] = defaultdict(set)
    e_l2_d: dict[tuple[str, str], set[int]] = defaultdict(set)

    e_l3_w: dict[tuple[str, str], int] = defaultdict(int)
    e_l3_s: dict[tuple[str, str], set[int]] = defaultdict(set)
    e_l3_d: dict[tuple[str, str], set[int]] = defaultdict(set)

    leaf_e_w: dict[tuple[str, str], int] = defaultdict(int)
    leaf_e_s: dict[tuple[str, str], set[int]] = defaultdict(set)
    leaf_e_d: dict[tuple[str, str], set[int]] = defaultdict(set)

    cross_out_l1 = [0] * (n_max + 1)
    cross_in_l1 = [0] * (n_max + 1)
    cross_out_l2 = [0] * (n_max + 1)
    cross_in_l2 = [0] * (n_max + 1)
    cross_out_l3 = [0] * (n_max + 1)
    cross_in_l3 = [0] * (n_max + 1)

    total_edges_read = 0
    reach_edges: list[tuple[int, int]] = []
    for s_id, d_id in cur.execute("SELECT src_id, dst_id FROM edges"):
        if s_id not in reach_set or d_id not in reach_set:
            continue
        reach_edges.append((s_id, d_id))
        total_edges_read += 1
        st, dt = mod_top[s_id], mod_top[d_id]
        if st != dt:
            k1 = (st, dt)
            e_l1_w[k1] += 1
            e_l1_s[k1].add(s_id)
            e_l1_d[k1].add(d_id)
            cross_out_l1[s_id] += 1
            cross_in_l1[d_id] += 1

        sd2, dd2 = mod_d2[s_id], mod_d2[d_id]
        if sd2 != dd2:
            k2 = (sd2, dd2)
            e_l2_w[k2] += 1
            e_l2_s[k2].add(s_id)
            e_l2_d[k2].add(d_id)
            cross_out_l2[s_id] += 1
            cross_in_l2[d_id] += 1

        sd3, dd3 = mod_d3[s_id], mod_d3[d_id]
        if sd3 != dd3:
            k3 = (sd3, dd3)
            e_l3_w[k3] += 1
            e_l3_s[k3].add(s_id)
            e_l3_d[k3].add(d_id)
            cross_out_l3[s_id] += 1
            cross_in_l3[d_id] += 1

        nl_s, nl_d = mod_tree_l3[s_id], mod_tree_l3[d_id]
        if nl_s != nl_d:
            kl = (nl_s, nl_d)
            leaf_e_w[kl] += 1
            leaf_e_s[kl].add(s_id)
            leaf_e_d[kl].add(d_id)

    conn.close()

    assert total_edges_read == meta["reachable_internal_edges"], (
        f"Edge mismatch: {total_edges_read} vs {meta['reachable_internal_edges']}"
    )

    # Compute top cross-boundary files for every tree node
    for nid, nd in tree_nodes.items():
        lvl = nd["level"]
        mids = node_modules[nid]
        if lvl == 1:
            cout, cin = cross_out_l1, cross_in_l1
        elif lvl == 2:
            cout, cin = cross_out_l2, cross_in_l2
        else:
            cout, cin = cross_out_l3, cross_in_l3

        out_ranked = sorted(
            (mid for mid in mids if cout[mid] > 0),
            key=lambda m: (-cout[m], -mod_lines[m], mod_rel[m]),
        )[:5]
        in_ranked = sorted(
            (mid for mid in mids if cin[mid] > 0),
            key=lambda m: (-cin[m], -mod_lines[m], mod_rel[m]),
        )[:5]

        nd["top_out_files"] = [
            {
                "rel_path": mod_rel[m],
                "cross_out": cout[m],
                "lines": mod_lines[m],
                "dist": mod_dist[m],
                "height": mod_height[m],
            }
            for m in out_ranked
        ]
        nd["top_in_files"] = [
            {
                "rel_path": mod_rel[m],
                "cross_in": cin[m],
                "lines": mod_lines[m],
                "dist": mod_dist[m],
                "height": mod_height[m],
            }
            for m in in_ranked
        ]

    def build_level_summary(
        nodes_set: set[str],
        w_map: dict[tuple[str, str], int],
        s_map: dict[tuple[str, str], set[int]],
        d_map: dict[tuple[str, str], set[int]],
    ) -> dict[str, Any]:
        edges_out = []
        dir_pairs = list(w_map.keys())
        for s, d in sorted(dir_pairs, key=lambda k: (-w_map[k], k[0], k[1])):
            rev_w = w_map.get((d, s), 0)
            edges_out.append(
                {
                    "src": s,
                    "dst": d,
                    "weight": w_map[(s, d)],
                    "src_files": len(s_map[(s, d)]),
                    "dst_files": len(d_map[(s, d)]),
                    "has_reverse": rev_w > 0,
                    "reverse_weight": rev_w,
                }
            )
        mutual_pairs = sum(1 for (s, d) in dir_pairs if s < d and (d, s) in w_map)
        sccs = tarjan_scc(sorted(nodes_set), dir_pairs)
        nontrivial_sccs = [c for c in sccs if len(c) > 1]
        return {
            "node_count": len(nodes_set),
            "edge_count": len(edges_out),
            "total_cross_edges": sum(w_map.values()),
            "mutual_pairs": mutual_pairs,
            "nontrivial_scc_count": len(nontrivial_sccs),
            "sccs": nontrivial_sccs,
            "edges": edges_out,
        }

    l1_keys = {mod_top[m] for m in all_ids}
    l2_keys = {mod_d2[m] for m in all_ids}
    l3_keys = {mod_d3[m] for m in all_ids}

    levels_data = {
        "1": build_level_summary(l1_keys, e_l1_w, e_l1_s, e_l1_d),
        "2": build_level_summary(l2_keys, e_l2_w, e_l2_s, e_l2_d),
        "3": build_level_summary(l3_keys, e_l3_w, e_l3_s, e_l3_d),
    }

    leaf_edges = [
        [s, d, w, len(leaf_e_s[(s, d)]), len(leaf_e_d[(s, d)])]
        for (s, d), w in sorted(leaf_e_w.items(), key=lambda kv: (-kv[1], kv[0][0], kv[0][1]))
    ]

    # Validate leaf partition
    leaf_nodes = [nd for nd in tree_nodes.values() if nd["is_leaf"]]
    assert sum(nd["files"] for nd in leaf_nodes) == meta["reachable_files"]
    assert len(leaf_nodes) == len(l3_keys)
    assert len(leaf_edges) == levels_data["3"]["edge_count"]

    present_top = {mod_top[mid] for mid in all_ids}
    active_top_order = [t for t in TOP_ORDER if t in present_top] + sorted(present_top - set(TOP_ORDER))
    root_ids = [f"L1:{t}" for t in active_top_order if f"L1:{t}" in tree_nodes]

    # Count minor subdirs per top dir dynamically for major_bucket labels
    minor_counts: dict[str, set[str]] = defaultdict(set)
    for mid in all_ids:
        t, d2 = mod_top[mid], mod_d2[mid]
        if t == "Formalism" and d2 not in MAJOR_FORMALISM_HUBS:
            minor_counts[t].add(d2)
        elif t == "PositivityTheory" and d2 != "PositivityTheory/AutomorphicForms":
            minor_counts[t].add(d2)
        elif t == "GroundTheory" and d2 not in MAJOR_GROUND_KEEP:
            minor_counts[t].add(d2)
        elif t == "ReciprocityTheory" and d2 not in MAJOR_RECIPROCITY_KEEP:
            minor_counts[t].add(d2)

    # Build projected Depth-2 major architectural dataset
    def major_bucket(mid: int) -> str:
        t, d2 = mod_top[mid], mod_d2[mid]
        if t in ("(root)", "BuildAid", "Development", "CompanionTheory", "Supplements"):
            return d2
        if t == "Lemmata":
            return "Lemmata/*"
        if t == "Formalism":
            return d2 if d2 in MAJOR_FORMALISM_HUBS else f"Formalism/(other {len(minor_counts['Formalism'])})"
        if t == "PositivityTheory":
            return d2 if d2 == "PositivityTheory/AutomorphicForms" else f"PositivityTheory/(other {len(minor_counts['PositivityTheory'])})"
        if t == "GroundTheory":
            return d2 if d2 in MAJOR_GROUND_KEEP else f"GroundTheory/(minor {len(minor_counts['GroundTheory'])})"
        if t == "ReciprocityTheory":
            return d2 if d2 in MAJOR_RECIPROCITY_KEEP else f"ReciprocityTheory/(minor {len(minor_counts['ReciprocityTheory'])})"
        return d2

    major_nodes: dict[str, dict[str, Any]] = {}
    mod_major: list[str] = [""] * (n_max + 1)
    for mid in all_ids:
        b = major_bucket(mid)
        mod_major[mid] = b
        if b not in major_nodes:
            major_nodes[b] = {
                "key": b,
                "top_dir": mod_top[mid],
                "files": 0,
                "lines": 0,
                "max_height": 0,
                "min_dist": None,
            }
        mn = major_nodes[b]
        mn["files"] += 1
        mn["lines"] += mod_lines[mid]
        if mod_height[mid] > mn["max_height"]:
            mn["max_height"] = mod_height[mid]
        dm = mod_dist[mid]
        if mn["min_dist"] is None or dm < mn["min_dist"]:
            mn["min_dist"] = dm

    major_edge_w: dict[tuple[str, str], int] = defaultdict(int)
    for s_id, d_id in reach_edges:
        bs, bd = mod_major[s_id], mod_major[d_id]
        if bs != bd:
            major_edge_w[(bs, bd)] += 1

    print(
        f"Loaded & aggregated {len(all_ids):,} reachable modules and {total_edges_read:,} edges "
        f"into {len(tree_nodes)} tree nodes in {time.time() - t0:.2f}s"
    )

    return {
        "top_order": active_top_order,
        "meta": {
            "repo_root": str(SRC_DIR),
            "total_files": meta["total_files"],
            "reachable_files": meta["reachable_files"],
            "unreachable_files": meta.get("unreachable_files", 0),
            "total_lines": meta.get("reachable_lines", meta["total_lines"]),
            "total_bytes": meta["total_bytes"],
            "total_internal_edges": meta["reachable_internal_edges"],
            "is_dag": meta["is_dag"],
            "max_dist_from_main": meta["max_dist_from_main"],
            "max_height_from_leaves": meta["max_height_from_leaves"],
            "edge_semantics": "Directed edge (src -> dst) means src imports dst (src depends on dst).",
        },
        "levels": levels_data,
        "tree": {
            "root_ids": root_ids,
            "nodes": tree_nodes,
            "leaf_edges": leaf_edges,
        },
        "_major_projection": {
            "nodes": major_nodes,
            "edges": dict(major_edge_w),
        },
    }


def write_top_level_mermaid(data: dict[str, Any], out_path: Path) -> None:
    """Write top_level_graph.mmd (Mermaid flowchart TD)."""
    tree_nodes = data["tree"]["nodes"]
    l1_edges = data["levels"]["1"]["edges"]
    active_tops = data.get("top_order") or [t for t in TOP_ORDER if f"L1:{t}" in tree_nodes]

    lines: list[str] = [
        "%%{init: {'theme': 'base', 'themeVariables': {'fontFamily': 'Inter, system-ui, sans-serif'}}}%%",
        "flowchart TD",
        "  %% Directed edge A --> B means A imports B (A depends on B)",
        "  %% Heavy (>=1000): bold ==> | Medium (50..999): --> | Light (<50): -.->",
        "",
        "  subgraph LEGEND[\"Legend: Edge A → B means A imports B (depends on B)\"]",
        "    direction LR",
        "    L_src[\"Importer\"] ==>|\"≥ 1,000 imports\"| L_dst[\"Imported\"]",
        "    L_src2[\"Importer\"] -->|\"50–999 imports\"| L_dst2[\"Imported\"]",
        "    L_src3[\"Importer\"] -.->|\"< 50 / weaker reverse\"| L_dst3[\"Imported\"]",
        "  end",
        "",
    ]

    for top in active_tops:
        nid = f"L1:{top}"
        nd = tree_nodes[nid]
        sid = sanitize_id(top)
        label = (
            f"{top}<br/>"
            f"min dist {nd['min_dist']} · max height {nd['max_height']}"
        )
        lines.append(f'  {sid}["{label}"]')

    lines.append("")
    for e in l1_edges:
        s_id = sanitize_id(e["src"])
        d_id = sanitize_id(e["dst"])
        w = e["weight"]
        is_entry = e["src"] in ("(root)", "Supplements")
        is_weaker_rev = e["has_reverse"] and w < e["reverse_weight"]
        tag = f"{format_num(w)} (rev of {format_num(e['reverse_weight'])})" if is_weaker_rev else format_num(w)
        if w >= 1000:
            arrow = "==>"
        elif w >= 50 or is_entry:
            arrow = "-->"
        else:
            arrow = "-.->"
        lines.append(f'  {s_id} {arrow}|"{tag}"| {d_id}')

    lines.append("")
    for top in active_tops:
        sid = sanitize_id(top)
        c = TOP_COLORS.get(top, TOP_COLORS["BuildAid"])
        lines.append(
            f"  style {sid} fill:{c['dot']},stroke:{c['border']},stroke-width:2px,color:#ffffff"
        )
    lines.append("  style LEGEND fill:#0f172a,stroke:#475569,color:#e2e8f0")
    lines.append("  style L_src fill:#1e293b,stroke:#64748b,color:#f8fafc")
    lines.append("  style L_dst fill:#1e293b,stroke:#64748b,color:#f8fafc")
    lines.append("  style L_src2 fill:#1e293b,stroke:#64748b,color:#f8fafc")
    lines.append("  style L_dst2 fill:#1e293b,stroke:#64748b,color:#f8fafc")
    lines.append("  style L_src3 fill:#1e293b,stroke:#64748b,color:#f8fafc")
    lines.append("  style L_dst3 fill:#1e293b,stroke:#64748b,color:#f8fafc")

    out_path.write_text("\n".join(lines) + "\n")


def write_top_level_dot(data: dict[str, Any], out_path: Path) -> None:
    """Write top_level_graph.dot for Graphviz rendering."""
    tree_nodes = data["tree"]["nodes"]
    l1_edges = data["levels"]["1"]["edges"]
    active_tops = data.get("top_order") or [t for t in TOP_ORDER if f"L1:{t}" in tree_nodes]
    active_set = set(active_tops)

    lines: list[str] = [
        "digraph TopLevelDependencies {",
        "  graph [",
        (
            '    label="Riemann Proof — Top-Level Mathematical Domain Dependency Graph\\n'
            'Edge A -> B means A depends on B (A imports from B)\\n'
            'Blue: primary cross-theory dependency | Slate: secondary | Indigo: Main entry chain | Dashed Amber: reverse coupling"'
        ),
        "    labelloc=t",
        "    fontsize=15",
        '    fontname="Helvetica"',
        "    rankdir=TB",
        "    splines=true",
        "    nodesep=0.95",
        "    ranksep=0.95",
        '    bgcolor="#0f172a"',
        '    fontcolor="#f8fafc"',
        "    pad=0.45",
        "  ];",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=11, penwidth=2, margin="0.18,0.10"];',
        '  edge [fontname="Helvetica", fontsize=9];',
        "",
    ]

    for top in active_tops:
        nid = f"L1:{top}"
        nd = tree_nodes[nid]
        sid = sanitize_id(top)
        c = TOP_COLORS.get(top, TOP_COLORS["BuildAid"])
        label = (
            f"{top}\\n"
            f"dist>={nd['min_dist']} | maxH={nd['max_height']}"
        )
        lines.append(
            f'  {sid} [label="{label}", fillcolor="{c["dot"]}", color="{c["border"]}", fontcolor="#ffffff"];'
        )

    rank_groups = [
        ["(root)"],
        ["Supplements"],
        ["Development"],
        ["CompanionTheory", "PositivityTheory"],
        ["Formalism", "GroundTheory", "ReciprocityTheory"],
        ["Lemmata", "BuildAid"],
    ]
    lines.append("")
    for grp in rank_groups:
        present_grp = [sanitize_id(t) for t in grp if t in active_set]
        if present_grp:
            lines.append(f"  {{ rank=same; {'; '.join(present_grp)}; }}")
    lines.append("")

    rank_idx = {
        "(root)": 0,
        "Supplements": 1,
        "Development": 2,
        "CompanionTheory": 3,
        "PositivityTheory": 3,
        "Formalism": 4,
        "GroundTheory": 4,
        "ReciprocityTheory": 4,
        "Lemmata": 5,
        "BuildAid": 5,
    }

    for e in l1_edges:
        s_id = sanitize_id(e["src"])
        d_id = sanitize_id(e["dst"])
        w = e["weight"]
        pw = max(1.2, min(6.0, 1.0 + math.log10(max(1, w)) * 1.15))
        is_entry = e["src"] in ("(root)", "Supplements")
        is_back = e["has_reverse"] and w < e["reverse_weight"]
        goes_up = rank_idx.get(e["dst"], 4) < rank_idx.get(e["src"], 4)
        if is_entry:
            color = "#a5b4fc"
            style = "bold"
            fontcolor = "#c7d2fe"
            lbl = f"{format_num(w)} (entry)"
            constraint = "true"
            pw = 2.4
        elif is_back:
            color = "#f59e0b"
            style = "dashed"
            fontcolor = "#fbbf24"
            lbl = f"{format_num(w)} (rev)"
            constraint = "false" if goes_up else "true"
        elif w >= 1000:
            color = "#38bdf8"
            style = "solid"
            fontcolor = "#bae6fd"
            lbl = f"{format_num(w)}"
            constraint = "false" if goes_up else "true"
        elif w >= 50:
            color = "#94a3b8"
            style = "solid"
            fontcolor = "#cbd5e1"
            lbl = f"{format_num(w)}"
            constraint = "false" if goes_up else "true"
        else:
            color = "#64748b"
            style = "dotted"
            fontcolor = "#94a3b8"
            lbl = f"{format_num(w)}"
            constraint = "false" if goes_up else "true"

        lines.append(
            f'  {s_id} -> {d_id} [label=" {lbl} ", penwidth={pw:.2f}, color="{color}", '
            f'style={style}, fontcolor="{fontcolor}", constraint={constraint}];'
        )

    lines.append("}")
    out_path.write_text("\n".join(lines) + "\n")


def write_depth2_major_dot(data: dict[str, Any], out_path: Path) -> None:
    """Write depth2_major_graph.dot covering major depth-2 sub-theories and Formalism hubs."""
    proj = data["_major_projection"]
    nodes: dict[str, dict[str, Any]] = proj["nodes"]
    edges: dict[tuple[str, str], int] = proj["edges"]

    # Keep edges with weight >= 150, entry chain edges, and strongest incoming/outgoing per node
    keep_edges: set[tuple[str, str]] = set()
    for (s, d), w in edges.items():
        if w >= 150 or s in ("(root)", "Supplements/Kernels") or d in ("(root)", "Supplements/Kernels"):
            keep_edges.add((s, d))

    for n in nodes:
        ins = [((s, d), w) for (s, d), w in edges.items() if d == n]
        outs = [((s, d), w) for (s, d), w in edges.items() if s == n]
        if ins:
            keep_edges.add(max(ins, key=lambda x: x[1])[0])
        if outs:
            keep_edges.add(max(outs, key=lambda x: x[1])[0])

    lines: list[str] = [
        "digraph Depth2MajorArchitecture {",
        "  graph [",
        (
            f'    label="Riemann Proof — Major Depth-2 Sub-Theory Architecture\\n'
            f'Edge A -> B means A depends on B\\n'
            f'Colors: Blue=Development | Emerald=Companion | Magenta=Positivity | Orange=Formalism | Teal=Reciprocity | Gold=Ground | Purple=Lemmata | Slate=Root/BuildAid"'
        ),
        "    labelloc=t",
        "    fontsize=15",
        '    fontname="Helvetica"',
        "    rankdir=TB",
        "    splines=true",
        "    nodesep=0.38",
        "    ranksep=0.80",
        '    bgcolor="#0f172a"',
        '    fontcolor="#f8fafc"',
        "    pad=0.40",
        "  ];",
        '  node [shape=box, style="rounded,filled", fontname="Helvetica", fontsize=10, penwidth=1.8, margin="0.14,0.08"];',
        '  edge [fontname="Helvetica", fontsize=8];',
        "",
    ]

    active_tops = data.get("top_order") or TOP_ORDER
    for key in sorted(
        nodes.keys(),
        key=lambda k: (
            -nodes[k]["max_height"],
            active_tops.index(nodes[k]["top_dir"]) if nodes[k]["top_dir"] in active_tops else 99,
            -nodes[k]["files"],
        ),
    ):
        nd = nodes[key]
        c = TOP_COLORS.get(nd["top_dir"], TOP_COLORS["BuildAid"])
        sid = sanitize_id(key)
        lbl = f"{key}\\nH={nd['max_height']}"
        lines.append(
            f'  {sid} [label="{lbl}", fillcolor="{c["dot"]}", color="{c["border"]}", fontcolor="#ffffff"];'
        )

    lines.append("")

    for s, d in sorted(keep_edges, key=lambda k: (-edges[k], k[0], k[1])):
        w = edges[(s, d)]
        rev_w = edges.get((d, s), 0)
        is_back = rev_w > 0 and w < rev_w
        pw = max(0.9, min(5.5, 0.8 + math.log10(max(1, w)) * 1.05))
        if s in ("(root)", "Supplements/Kernels") or d == "Formalism/GammaFactorNonvanishing":
            color = "#a5b4fc"
            style = "bold"
            fontcolor = "#c7d2fe"
            constraint = "true"
            pw = 2.2
        elif is_back:
            color = "#f59e0b"
            style = "dashed"
            fontcolor = "#fbbf24"
            constraint = "false"
        elif w >= 1000:
            color = "#38bdf8"
            style = "solid"
            fontcolor = "#bae6fd"
            constraint = "true"
        elif w >= 150:
            color = "#94a3b8"
            style = "solid"
            fontcolor = "#cbd5e1"
            constraint = "true"
        else:
            color = "#64748b"
            style = "dotted"
            fontcolor = "#94a3b8"
            constraint = "true"

        lbl = f" {format_num(w)} " if (w >= 300 or s in ("(root)", "Supplements/Kernels") or d == "BuildAid" or w < 150) else ""
        lines.append(
            f'  {sanitize_id(s)} -> {sanitize_id(d)} [label="{lbl}", penwidth={pw:.2f}, '
            f'color="{color}", style={style}, fontcolor="{fontcolor}", constraint={constraint}];'
        )

    lines.append("}")
    out_path.write_text("\n".join(lines) + "\n")


def render_svg_with_dot(dot_path: Path, svg_path: Path) -> None:
    """Invoke /usr/bin/dot -Tsvg to render DOT file to SVG."""
    subprocess.run(
        ["/usr/bin/dot", "-Tsvg", str(dot_path), "-o", str(svg_path)],
        check=True,
    )


def write_readme_md(
    data: dict[str, Any],
    out_path: Path,
    source_blob_base: str = "",
    version_label: str = "",
    rel_src_label: str = "src/",
) -> None:
    """Write version-aware README.md for dependency_graph."""
    meta = data["meta"]
    tree_nodes = data["tree"]["nodes"]
    l2_edges = data["levels"]["2"]["edges"]
    active_tops = data.get("top_order") or []
    n_major = len(data["_major_projection"]["nodes"])

    def mlink(rel_path: str, label: str | None = None) -> str:
        t = label or Path(rel_path).name
        if source_blob_base:
            return f"[{t}]({source_blob_base.rstrip('/')}/{rel_path})"
        return f"`{rel_path}`"

    roles = {
        "(root)": f"Top-level theorem statements and entry point ({mlink('Main.lean')}, {mlink('Statements.lean')})",
        "Supplements": "Theorem-assembly kernel (`Supplements/Kernels/*`) bridging `Main.lean` into the main proof tracks",
        "Development": "Primary proof synthesis engine: abelian varieties, automorphic arithmetic, automorphic spectrum, Weil bound, étale cohomology, discrete groups, and resolution of singularities",
        "CompanionTheory": "Spectral geometry, real reductive groups, Harish-Chandra modules, and automorphic companion results",
        "PositivityTheory": "Automorphic positivity estimates, Rankin-Selberg integrals, and weight-1 Hilbert Eisenstein series",
        "Formalism": "Foundational analytic and algebraic specification contracts: local-to-global theta lifts, sharp restriction, period integrals, Hermitian curvature, and local Bloch-Kato cohomology",
        "ReciprocityTheory": "Reductive groups, PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, $L^2$ $\\bar\\partial$-estimates, and reciprocity laws",
        "GroundTheory": "Arakelov heights, theta functions, global/local fields, Whittaker multiplicity one, profinite Poitou-Tate cohomology, and $p$-adic Hodge theory",
        "Lemmata": "Standalone linear-algebraic and matrix-determinant lemma units",
        "BuildAid": "Library-suggestion namespace configuration leaves",
    }

    ver_note = f" ({version_label})" if version_label else ""
    lines: list[str] = []
    a = lines.append
    a(f"# Theory-Level Dependency Graph Analysis{ver_note}")
    a("")
    a(
        f"This directory contains aggregated dependency graphs, static diagrams, and an interactive explorer mapping the logical relationships across the mathematical domains and sub-theories of `{rel_src_label}` (**{meta['reachable_files']:,} reachable modules**, **{meta['total_internal_edges']:,} edges**)."
    )
    a("")
    a(
        "> **Direction Convention:** Throughout all data files, diagrams, and tools in this directory, a directed edge **`A -> B`** means **`A` depends on `B`** (`A` imports mathematical definitions or theorems from `B`). Conversely, `B` supplies results to `A`."
    )
    a("")
    a("---")
    a("")
    a("## 1. Deliverables & Quick Links")
    a("")
    a("| Artifact | Description |")
    a("| :--- | :--- |")
    a("| `dir_graph_data.js` / `dir_graph.json` | Aggregated dependency graph across Depth 1 (top-level theories), Depth 2 (sub-theories), Depth 3 (topic modules), and the hierarchical tree. |")
    a("| `top_level_graph.mmd` / `top_level_graph.dot` / [top_level_graph.svg](top_level_graph.svg) | Mermaid and Graphviz diagrams of the top-level mathematical domains and cross-domain flows. |")
    a(f"| `depth2_major_graph.dot` / [depth2_major_graph.svg](depth2_major_graph.svg) | Readable {n_major}-node Depth-2 architectural projection across sub-theories and major hubs. |")
    a("| [dependency_explorer.html](dependency_explorer.html) | Self-contained offline interactive explorer with Depth 1→2→3 expand/collapse, height-stratified pan/zoom layout, upstream/downstream/mutual highlighting, and search. |")
    a("")
    a("---")
    a("")
    a("## 2. Macro-Dependency Structure (Top-Level Theories)")
    a("")
    a(
        f"All **{meta['reachable_files']:,}** modules reachable from {mlink('Main.lean')} form a **strict acyclic DAG** (`is_dag = {meta['is_dag']}`), organized across **{len(active_tops)}** active top-level directories:"
    )
    a("")
    a("| Top-Level Domain | Files | Lines | Dist Min | Max Height | Mathematical & Architectural Role |")
    a("| :--- |---:|---:|---:|---:|:---|")
    for td in active_tops:
        nd = tree_nodes[f"L1:{td}"]
        a(
            f"| `{td}` | {nd['files']:,} | {nd['lines']:,} | {nd['min_dist']} | {nd['max_height']} | {roles.get(td, td)} |"
        )
    a("")
    a("### Key Structural Observations")
    if "Supplements" in active_tops:
        a(
            f"1. **The Entry Chain:** {mlink('Main.lean')} depends on {mlink('Statements.lean')} and `Supplements/Kernels/MainTheoremsAll.lean`. From there, `Supplements/Kernels` draws on the main proof synthesis in `Development/AutomorphicArithmetic` and the functional-equation reflection theorem in `Formalism/GammaFactorNonvanishing`."
        )
    else:
        a(
            f"1. **The Entry Chain:** {mlink('Main.lean')} imports {mlink('Statements.lean')} and `Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean` (alongside `ClaimStrip.lean`), feeding directly into the main character-box proof synthesis and its functional-equation reflection dependencies."
        )
    a(
        "2. **Synthesis vs. Foundation Split:** `Development` serves as the central consumer and synthesis engine, drawing heavily on the specification contracts and foundational theorems in `Formalism`, `ReciprocityTheory`, and `GroundTheory`, while co-evolving with `CompanionTheory` and `PositivityTheory`."
    )
    a("")
    a("---")
    a("")
    a("## 3. Topical Directory Cycles vs. Strict Module-Level DAG")
    a("")
    l1_meta = data["levels"]["1"]
    l2_meta = data["levels"]["2"]
    l1_sccs = [s for s in l1_meta.get("sccs", []) if len(s) > 1]
    l2_sccs = [s for s in l2_meta.get("sccs", []) if len(s) > 1]
    l1_desc = (
        f"**{len(l1_sccs)}** top-level SCC (spanning {len(l1_sccs[0])} domains)"
        if l1_sccs
        else "**0** nontrivial top-level SCCs"
    )
    n_l2_mutual = l2_meta.get("mutual_pairs", 0)
    if isinstance(n_l2_mutual, list):
        n_l2_mutual = len(n_l2_mutual)
    l2_desc = (
        f"**{len(l2_sccs)}** nontrivial sub-theory SCCs (largest spanning **{len(l2_sccs[0])}** sub-theories; **{n_l2_mutual}** mutual bidirectional pairs)"
        if l2_sccs
        else "**0** nontrivial sub-theory SCCs"
    )
    a(
        f"Even though the underlying module-level dependency graph has **zero cycles** (`is_dag = {meta['is_dag']}`), aggregating dependencies by topical folder produces bidirectional couplings (strongly connected components) between directories: Depth 1 contains {l1_desc}, and Depth 2 contains {l2_desc}."
    )
    a("")
    a("### Why Directory Cycles Coexist with a Module-Level DAG")
    a(
        "Directories organize the proof by **mathematical topic** rather than strict topological build height. Low-height specification or definition modules inside a high-level directory are referenced by higher-height proof modules in a foundational directory, while high-height synthesis modules in the first directory depend on the foundational directory:"
    )
    a("")
    a(
        "- **Specification-to-Realization Back-Flows:** `Development` depends heavily on `Formalism` and `ReciprocityTheory`, while a small number of modules in `Formalism` reference low-height parameter/character helpers inside `Development`."
    )
    l2_edge_pairs = {(e["src"], e["dst"]) for e in l2_edges}
    if ("Development/WeilBound", "Development/AutomorphicSpectrum") in l2_edge_pairs and (
        "Development/AutomorphicSpectrum",
        "Development/WeilBound",
    ) in l2_edge_pairs:
        mutual_note = (
            "At Depth 1, `Development <-> CompanionTheory` and `Development <-> PositivityTheory` exhibit two-way interplay; "
            "at Depth 2, **`Development/WeilBound <-> Development/AutomorphicSpectrum`** are tightly coupled, as spectral decomposition and Weil-bound / Moriwaki-bigness arguments alternate across inductive stages."
        )
    else:
        mutual_note = (
            "At Depth 1 and Depth 2, co-evolving proof synthesis tracks alternate across inductive stages while remaining strictly acyclic at individual `.lean` file granularity."
        )
    a(f"- **Co-Evolving Mathematical Pillars:** {mutual_note}")
    a("")
    a("---")
    a("")
    a("## 4. Major Cross-Theory Mathematical Flows (Depth 2)")
    a("")
    flow_notes = {
        ("Development/AutomorphicArithmetic", "Development/AbelianVarietyTheory"): "Covolume bounds, literature packages (`LitN`), local Langlands axioms, and CM period comparisons",
        ("Development/AbelianVarietyTheory", "ReciprocityTheory/ReductiveGroups"): "PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, and polarized abelian scheme laws",
        ("Development/AbelianVarietyTheory", "Formalism/LocalToGlobal"): "Indefinite/definite unitary theta-lift stages, Siegel lattice theory, and seesaw/doubling identities",
        ("Development/WeilBound", "Development/AbelianVarietyTheory"): "De Rham/crystalline comparisons, Nef Riemann–Roch, and Nadel vanishing pairs",
        ("Development/AbelianVarietyTheory", "Formalism/SharpRestriction"): "Formal differential theta-expression chart independence, local Bloch–Kato cohomology (`LocCoh`), and Schur norm bounds",
        ("Development/AutomorphicSpectrum", "Development/AbelianVarietyTheory"): "Polarized abelian scheme realizations, divisor proofs, and discrete series branching",
        ("Development/WeilBound", "Development/AutomorphicSpectrum"): "Mutual interplay between spectral geometry / good root towers and Moriwaki arithmetic bigness / regularized Siegel–Weil",
        ("Development/AutomorphicSpectrum", "Development/WeilBound"): "Regularized Siegel–Weil inputs feeding back into automorphic spectral & geometric tower stages",
        ("Development/AutomorphicArithmetic", "Formalism/LocalToGlobal"): "Local-to-global theta-kernel stages and definite/indefinite lift contracts",
        ("Development/AutomorphicSpectrum", "ReciprocityTheory/ReductiveGroups"): "Boundary charts on toroidal compactifications and semiabelian scheme models",
        ("Development/AutomorphicArithmetic", "Development/WeilBound"): "Moriwaki bigness, étale finiteness, and resolution inputs feeding automorphic-arithmetic thresholds",
        ("Development/AutomorphicSpectrum", "GroundTheory/HeightsAndTheta"): "Arakelov Hermitian vector bundles, Bost–Zhang slope inequalities, and DVR pairing flag independence",
        ("Development/AbelianVarietyTheory", "Formalism/LocalRingCardinality"): "Master CM host and self-dual Hermitian lattice package (`D7`) and Fontaine period-ring identifications (`LocTied`)",
    }
    a("| Source Sub-Theory (`depends on →`) | Target Sub-Theory (`← supplies`) | Import Edges | Source → Target Files | Mathematical Connection |")
    a("|:---|:---|---:|---|:---|")
    for e in sorted(l2_edges, key=lambda x: (-x["weight"], x["src"], x["dst"]))[:15]:
        conn_desc = flow_notes.get((e["src"], e["dst"]), "Cross-theory module dependency flow")
        a(f"| `{e['src']}` | `{e['dst']}` | {e['weight']:,} | {e['src_files']:,} → {e['dst_files']:,} | {conn_desc} |")
    a("")
    a("---")
    a("")
    a("## 5. Regenerating & Validating")
    a("")
    a("```bash")
    vid_arg = version_label or "<version-id>"
    a(f"# Rebuild dependency graphs for this Lean version via the orchestrator")
    a(f"python3 analysis/build_all.py --version {vid_arg} --steps dep_graphs")
    a("")
    a("# Or run standalone against specific SQLite/source paths:")
    a("python3 analysis/dependency_graph/build_dep_graphs.py --help")
    a("```")
    a("")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_explorer_html(data: dict[str, Any], out_path: Path) -> None:
    """Write self-contained dependency_explorer.html shell loading versioned dir_graph_data.js."""
    html_doc = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Riemann Proof — Lean 4 Directory Dependency Explorer</title>
<style>
  :root {
    --bg: #ffffff;
    --panel: #fafafa;
    --panel-alt: #f0f0f0;
    --border: #cccccc;
    --text: #111111;
    --muted: #555555;
    --accent: #0056b3;
    --out-color: #0284c7;
    --in-color: #d97706;
    --mutual-color: #7c3aed;
    --selected-color: #111111;
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0;
    padding: 0;
    height: 100%;
    width: 100%;
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 13px;
    overflow: hidden;
  }
  .app {
    display: grid;
    grid-template-rows: auto auto auto 1fr;
    height: 100vh;
    width: 100vw;
  }
  header {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    padding: 8px 14px;
    background: #ffffff;
    border-bottom: 1px solid var(--border);
  }
  .title-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
  }
  h1 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--text);
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 7px;
    font-size: 11px;
    background: var(--panel-alt);
    border: 1px solid var(--border);
    color: var(--muted);
  }
  .pill strong { color: var(--text); }
  .dir-banner {
    font-size: 11px;
    color: var(--text);
    background: #f5f5f5;
    border: 1px solid var(--border);
    padding: 3px 8px;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
    padding: 6px 14px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
  }
  .tool-group {
    display: flex;
    align-items: center;
    gap: 6px;
    padding-right: 10px;
    border-right: 1px solid var(--border);
  }
  .tool-group:last-child { border-right: none; }
  .tool-label {
    font-size: 11px;
    color: var(--muted);
    font-weight: 600;
  }
  button {
    background: #ffffff;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 3px 8px;
    font-size: 12px;
    cursor: pointer;
  }
  button:hover {
    background: #eeeeee;
  }
  button.active {
    background: #222222;
    border-color: #222222;
    color: #ffffff;
  }
  button.sm {
    padding: 2px 6px;
    font-size: 11px;
  }
  .search-wrap {
    position: relative;
    width: 240px;
  }
  .search-wrap input {
    width: 100%;
    background: #ffffff;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 4px 8px;
    font-size: 12px;
  }
  .search-results {
    position: absolute;
    top: calc(100% + 2px);
    left: 0;
    right: 0;
    max-height: 280px;
    overflow-y: auto;
    background: #ffffff;
    border: 1px solid var(--border);
    z-index: 40;
    display: none;
  }
  .search-item {
    padding: 5px 8px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid #eeeeee;
  }
  .search-item:hover { background: #eeeeee; }
  .search-item .sname {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px;
  }
  .search-item .smeta {
    font-size: 10px;
    color: var(--muted);
    flex-shrink: 0;
  }
  .main-grid {
    display: grid;
    grid-template-columns: 260px 1fr 350px;
    min-height: 0;
    height: 100%;
  }
  .sidebar {
    background: var(--panel);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .inspector {
    background: var(--panel);
    border-left: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .pane-head {
    padding: 7px 10px;
    border-bottom: 1px solid var(--border);
    font-weight: 700;
    font-size: 12px;
    color: var(--text);
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--panel-alt);
  }
  .pane-body {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }
  .tree-row {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 3px 5px;
    cursor: pointer;
    user-select: none;
  }
  .tree-row:hover { background: #eeeeee; }
  .tree-row.selected { background: #e6f0fa; outline: 1px solid #99c2ff; }
  .tree-toggle {
    width: 15px;
    height: 15px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    color: var(--muted);
    flex-shrink: 0;
  }
  .tree-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .tree-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 12px;
  }
  .tree-count {
    font-size: 10px;
    color: var(--muted);
    font-family: ui-monospace, monospace;
  }
  .canvas-wrap {
    position: relative;
    overflow: hidden;
    background: #ffffff;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
    cursor: grab;
  }
  canvas.dragging { cursor: grabbing; }
  .hud-top-left {
    position: absolute;
    top: 8px;
    left: 8px;
    display: flex;
    gap: 6px;
    align-items: center;
    pointer-events: none;
  }
  .hud-badge {
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid var(--border);
    padding: 3px 8px;
    font-size: 11px;
    color: var(--text);
    pointer-events: auto;
  }
  .hud-bottom-left {
    position: absolute;
    bottom: 8px;
    left: 8px;
    background: rgba(255, 255, 255, 0.94);
    border: 1px solid var(--border);
    padding: 6px 10px;
    font-size: 11px;
    line-height: 1.5;
    max-width: 340px;
    pointer-events: none;
  }
  .legend-row {
    display: flex;
    align-items: center;
    gap: 7px;
  }
  .swatch {
    width: 12px;
    height: 3px;
    display: inline-block;
  }
  .hud-bottom-right {
    position: absolute;
    bottom: 8px;
    right: 8px;
    display: flex;
    gap: 4px;
  }
  .tooltip {
    position: absolute;
    pointer-events: none;
    background: #ffffff;
    border: 1px solid #666666;
    padding: 6px 9px;
    font-size: 11px;
    color: var(--text);
    display: none;
    z-index: 30;
    max-width: 300px;
  }
  .stat-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 6px;
    margin-bottom: 10px;
  }
  .stat-card {
    background: #ffffff;
    border: 1px solid var(--border);
    padding: 5px 7px;
  }
  .stat-card .k { font-size: 10px; color: var(--muted); }
  .stat-card .v { font-size: 13px; font-weight: 700; color: var(--text); margin-top: 1px; }
  .sec-title {
    font-size: 11px;
    font-weight: 700;
    color: var(--text);
    margin: 10px 0 5px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .edge-list {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .edge-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 6px;
    padding: 4px 6px;
    background: #ffffff;
    border: 1px solid var(--border);
    cursor: pointer;
  }
  .edge-row:hover { background: #eeeeee; }
  .edge-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    font-size: 11px;
    font-family: ui-monospace, monospace;
  }
  .edge-meta {
    display: flex;
    align-items: center;
    gap: 5px;
    flex-shrink: 0;
    font-size: 11px;
    font-family: ui-monospace, monospace;
  }
  .tag-mutual {
    font-size: 10px;
    padding: 0 4px;
    background: #f3e8ff;
    color: #6b21a8;
    border: 1px solid #d8b4fe;
  }
  .file-link {
    display: block;
    padding: 4px 6px;
    margin-bottom: 3px;
    background: #ffffff;
    border: 1px solid var(--border);
    color: var(--accent);
    text-decoration: none;
    font-family: ui-monospace, monospace;
    font-size: 11px;
    word-break: break-all;
  }
  .file-link:hover {
    background: #eeeeee;
  }
  .file-sub {
    color: var(--muted);
    font-size: 10px;
    margin-top: 2px;
    font-family: -apple-system, sans-serif;
  }
  .empty-hint {
    color: var(--muted);
    font-size: 12px;
    padding: 8px 4px;
  }
  input[type="range"] {
    cursor: pointer;
  }
  @media (max-width: 1100px) {
    .main-grid { grid-template-columns: 220px 1fr 310px; }
  }
</style>
</head>
<body>
<div class="app">
  <div style="padding:6px 14px;border-bottom:1px solid #ccc;font-size:12.5px;background:#fafafa;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
    <div>
      <a href="../index.html" style="color:#0056b3;text-decoration:none;">&larr; Back to Analysis Portal</a> &middot;
      <a href="README.html" style="color:#0056b3;text-decoration:none;">README.html</a> &middot;
      <a href="README.md" data-version-href="dependency_graph/README.md" style="color:#0056b3;text-decoration:none;">README.md</a>
    </div>
    <span data-version-picker></span>
  </div>
  <script src="../version_picker.js"></script>
  <header>
    <div class="title-wrap">
      <h1>Riemann Proof — Theory Dependency Explorer</h1>
      <span class="pill" id="ver-pill"><strong>Strict Module DAG</strong></span>
    </div>
    <div class="dir-banner">
      <strong>Edge Direction:</strong> Arrow <code>A → B</code> means <code>A</code> <strong>depends on</strong> <code>B</code>
    </div>
  </header>

  <div class="toolbar">
    <div class="tool-group">
      <span class="tool-label">Preset</span>
      <button id="btn-l1" class="active">Level 1</button>
      <button id="btn-l2-major">Level 2 Major</button>
      <button id="btn-l2-all">Level 2 All</button>
    </div>
    <div class="tool-group">
      <span class="tool-label">Layout</span>
      <button id="btn-layout-height" class="active">Height Strata</button>
      <button id="btn-layout-dist">Dist from Main</button>
    </div>
    <div class="tool-group">
      <span class="tool-label">Highlight</span>
      <button id="btn-hop-1" class="active">Direct (1-hop)</button>
      <button id="btn-hop-all">Transitive</button>
    </div>
    <div class="tool-group">
      <span class="tool-label">Min Weight</span>
      <input id="weight-slider" type="range" min="0" max="100" value="0" style="width:110px" />
      <span id="weight-val" style="min-width:46px;font-family:ui-monospace,monospace;">≥ 1</span>
      <button class="sm preset-w" data-w="1">1</button>
      <button class="sm preset-w" data-w="25">25</button>
      <button class="sm preset-w" data-w="100">100</button>
      <button class="sm preset-w" data-w="500">500</button>
      <label style="display:inline-flex;align-items:center;gap:4px;font-size:11px;color:var(--text);cursor:pointer;">
        <input id="chk-keep-sel" type="checkbox" checked /> Keep selected edges
      </label>
    </div>
    <div class="tool-group">
      <div class="search-wrap">
        <input id="search-input" type="text" placeholder="Search directory (L1 / L2 / L3)..." autocomplete="off" />
        <div id="search-results" class="search-results"></div>
      </div>
    </div>
  </div>

  <div class="main-grid">
    <aside class="sidebar">
      <div class="pane-head">
        <span>Directory Hierarchy</span>
        <span id="tree-summary" style="font-weight:400;color:var(--muted);">877 nodes</span>
      </div>
      <div id="dir-tree" class="pane-body"></div>
    </aside>

    <main class="canvas-wrap" id="canvas-wrap">
      <canvas id="graph-canvas"></canvas>
      <div class="hud-top-left">
        <div class="hud-badge" id="hud-counts">Visible: 10 nodes · 33 edges</div>
        <div class="hud-badge" id="hud-tip">Double-click a node to expand/collapse · Drag to pan · Scroll to zoom</div>
      </div>
      <div class="hud-bottom-left">
        <div style="font-weight:700;margin-bottom:3px;color:var(--text);">Highlight Legend (for Selected Node X)</div>
        <div class="legend-row"><span class="swatch" style="background:var(--out-color)"></span><span><strong>Blue →</strong>: Upstream dependencies (X imports target)</span></div>
        <div class="legend-row"><span class="swatch" style="background:var(--in-color)"></span><span><strong>Orange ←</strong>: Downstream dependents (source imports X)</span></div>
        <div class="legend-row"><span class="swatch" style="background:var(--mutual-color)"></span><span><strong>Purple ⇄</strong>: Mutual directory dependency (both ways)</span></div>
      </div>
      <div class="hud-bottom-right">
        <button id="btn-zoom-in" title="Zoom In">+</button>
        <button id="btn-zoom-out" title="Zoom Out">−</button>
        <button id="btn-fit" title="Fit to Screen">Fit View</button>
        <button id="btn-clear-sel" title="Clear Selection">Clear Sel</button>
      </div>
      <div class="tooltip" id="tooltip"></div>
    </main>

    <aside class="inspector">
      <div class="pane-head">
        <span>Directory Inspector</span>
        <span id="insp-level" style="font-weight:400;color:var(--muted);">—</span>
      </div>
      <div id="inspector-body" class="pane-body">
        <div class="empty-hint">Click any node in the graph or directory tree to inspect its metrics, incoming/outgoing dependencies, and top cross-boundary Lean files.</div>
      </div>
    </aside>
  </div>
</div>

<script>
function initDepExplorer(GRAPH_DATA) {
  "use strict";

  const nodesById = GRAPH_DATA.tree.nodes;
  const leafEdges = GRAPH_DATA.tree.leaf_edges;
  const rootIds = GRAPH_DATA.tree.root_ids;
  const colors = GRAPH_DATA.colors;
  const repoRoot = GRAPH_DATA.meta.repo_root;

  document.getElementById("btn-l1").textContent = `Level 1 (${rootIds.length})`;
  if (window.RHVersion && RHVersion.current) {
    document.getElementById("ver-pill").innerHTML = `<strong>${RHVersion.current.short_label || RHVersion.current.label}</strong> &middot; Strict Module DAG`;
  }

  // Build quick exact lookup maps for L1, L2, L3 edge metrics (src_files / dst_files)
  const exactL1 = new Map();
  for (const e of GRAPH_DATA.levels["1"].edges) {
    exactL1.set(e.src + "|" + e.dst, e);
  }
  const exactL2 = new Map();
  for (const e of GRAPH_DATA.levels["2"].edges) {
    exactL2.set(e.src + "|" + e.dst, e);
  }
  const exactL3 = new Map();
  for (const e of leafEdges) {
    exactL3.set(e[0] + "|" + e[1], e);
  }

  // Precompute leaf -> ancestor chain [L1, L2?, L3?]
  const leafIds = [];
  const leafChain = new Map();
  for (const nid of Object.keys(nodesById)) {
    const nd = nodesById[nid];
    if (nd.is_leaf) {
      leafIds.push(nid);
      const chain = [];
      let cur = nid;
      while (cur) {
        chain.push(cur);
        cur = nodesById[cur].parent_id;
      }
      chain.reverse();
      leafChain.set(nid, chain);
    }
  }

  // Precompute SCC membership at L1 and L2
  const sccInfoByKey = new Map();
  for (const lvl of ["1", "2", "3"]) {
    for (const comp of GRAPH_DATA.levels[lvl].sccs) {
      for (const k of comp) {
        sccInfoByKey.set(lvl + ":" + k, comp.length);
      }
    }
  }

  // Application state
  const state = {
    expandedIds: new Set(),
    treeOpenIds: new Set(),
    selectedId: nodesById["L1:Development"] ? "L1:Development" : (rootIds[0] || null),
    hoveredNodeId: null,
    hoveredEdge: null,
    minWeight: 1,
    keepSelectedEdges: true,
    layoutMode: "height", // "height" | "dist"
    hopMode: "direct", // "direct" | "transitive"
    visibleNodes: [],
    visibleNodeMap: new Map(),
    visibleEdges: [],
    edgeLookup: new Map(),
    positions: new Map(), // nid -> {x, y, w, h}
    cam: { x: 0, y: 0, scale: 1 },
    dragging: false,
    dragMoved: false,
    dragStart: { x: 0, y: 0, camX: 0, camY: 0 },
  };

  // DOM refs
  const canvas = document.getElementById("graph-canvas");
  const wrap = document.getElementById("canvas-wrap");
  const ctx = canvas.getContext("2d");
  const tooltip = document.getElementById("tooltip");
  const hudCounts = document.getElementById("hud-counts");
  const dirTreeEl = document.getElementById("dir-tree");
  const inspBody = document.getElementById("inspector-body");
  const inspLevel = document.getElementById("insp-level");
  const weightSlider = document.getElementById("weight-slider");
  const weightVal = document.getElementById("weight-val");
  const chkKeepSel = document.getElementById("chk-keep-sel");
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");

  function fmt(n) {
    return Number(n).toLocaleString("en-US");
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // Log-scale slider mapping: 0..100 -> 1..42000
  function sliderToWeight(v) {
    const t = Number(v) / 100;
    if (t <= 0) return 1;
    return Math.round(Math.pow(42000, t));
  }
  function weightToSlider(w) {
    if (w <= 1) return 0;
    return Math.min(100, Math.round((Math.log(w) / Math.log(42000)) * 100));
  }

  function visibleAncestor(leafId) {
    const chain = leafChain.get(leafId);
    for (let i = 0; i < chain.length - 1; i++) {
      if (!state.expandedIds.has(chain[i])) {
        return chain[i];
      }
    }
    return chain[chain.length - 1];
  }

  function recomputeVisibleGraph() {
    const visSet = new Set();
    const leafToVis = new Map();
    for (const lid of leafIds) {
      const v = visibleAncestor(lid);
      visSet.add(v);
      leafToVis.set(lid, v);
    }

    state.visibleNodes = Array.from(visSet).map((id) => nodesById[id]);
    state.visibleNodeMap = new Map(state.visibleNodes.map((n) => [n.id, n]));

    // Aggregate leaf edges across visible partition
    const rawAgg = new Map();
    for (let i = 0; i < leafEdges.length; i++) {
      const e = leafEdges[i];
      const vs = leafToVis.get(e[0]);
      const vd = leafToVis.get(e[1]);
      if (vs !== vd) {
        const key = vs + "|" + vd;
        rawAgg.set(key, (rawAgg.get(key) || 0) + e[2]);
      }
    }

    const edges = [];
    const lookup = new Map();
    for (const [key, w] of rawAgg.entries()) {
      const sep = key.indexOf("|");
      const src = key.slice(0, sep);
      const dst = key.slice(sep + 1);
      const revKey = dst + "|" + src;
      const revW = rawAgg.get(revKey) || 0;
      let srcFiles = null;
      let dstFiles = null;
      const srcNd = nodesById[src];
      const dstNd = nodesById[dst];
      const dKey = srcNd.dir_key + "|" + dstNd.dir_key;
      if (srcNd.level === 1 && dstNd.level === 1) {
        const ex = exactL1.get(dKey);
        if (ex) { srcFiles = ex.src_files; dstFiles = ex.dst_files; }
      } else if ((srcNd.level === 2 || (srcNd.level === 1 && srcNd.is_leaf)) && (dstNd.level === 2 || (dstNd.level === 1 && dstNd.is_leaf))) {
        const ex = exactL2.get(dKey);
        if (ex) { srcFiles = ex.src_files; dstFiles = ex.dst_files; }
      } else if (srcNd.is_leaf && dstNd.is_leaf) {
        const ex = exactL3.get(key);
        if (ex) { srcFiles = ex[3]; dstFiles = ex[4]; }
      }
      const obj = {
        src,
        dst,
        weight: w,
        hasReverse: revW > 0,
        reverseWeight: revW,
        srcFiles,
        dstFiles,
      };
      edges.push(obj);
      lookup.set(key, obj);
    }

    edges.sort((a, b) => b.weight - a.weight);
    state.visibleEdges = edges;
    state.edgeLookup = lookup;

    // Ensure selectedId is visible (or lift to visible ancestor)
    if (state.selectedId && !state.visibleNodeMap.has(state.selectedId)) {
      let cur = state.selectedId;
      while (cur && !state.visibleNodeMap.has(cur)) {
        cur = nodesById[cur] ? nodesById[cur].parent_id : null;
      }
      state.selectedId = cur || (state.visibleNodes[0] ? state.visibleNodes[0].id : null);
    }

    layoutVisibleNodes();
    updateCountsBadge();
    renderTreeSidebar();
    renderInspector();
    renderCanvas();
  }

  function layoutVisibleNodes() {
    const nodes = state.visibleNodes;
    const nCount = nodes.length;
    if (nCount === 0) return;

    // Bucket nodes into clean layers
    // Height mode: group by quantized max_height descending (top = 202, bottom = 0)
    // Dist mode: group by min_dist ascending (top = 0, bottom = max)
    const buckets = new Map();
    for (const nd of nodes) {
      let layerKey;
      if (state.layoutMode === "height") {
        if (nd.max_height >= 195) layerKey = -nd.max_height; // keep Main/Supplements/Dev separated cleanly
        else if (nd.max_height === 0) layerKey = 1000;
        else layerKey = -Math.round(nd.max_height / 14) * 14;
      } else {
        layerKey = nd.min_dist;
      }
      if (!buckets.has(layerKey)) buckets.set(layerKey, []);
      buckets.get(layerKey).push(nd);
    }

    const sortedKeys = Array.from(buckets.keys()).sort((a, b) => a - b);

    // Build adjacency for barycenter ordering within each layer
    const neighbors = new Map();
    for (const nd of nodes) neighbors.set(nd.id, []);
    for (const e of state.visibleEdges) {
      if (e.weight >= Math.min(state.minWeight, 10)) {
        neighbors.get(e.src).push({ id: e.dst, w: e.weight });
        neighbors.get(e.dst).push({ id: e.src, w: e.weight });
      }
    }

    // Initial deterministic order inside each bucket by top_order & files
    const topRank = new Map(GRAPH_DATA.top_order.map((t, i) => [t, i]));
    for (const k of sortedKeys) {
      buckets.get(k).sort((a, b) => {
        const ta = topRank.get(a.top_dir) ?? 99;
        const tb = topRank.get(b.top_dir) ?? 99;
        if (ta !== tb) return ta - tb;
        return b.files - a.files;
      });
    }

    // Estimate initial x-coord and run 2 barycenter passes
    const tempX = new Map();
    for (const k of sortedKeys) {
      const row = buckets.get(k);
      row.forEach((nd, idx) => tempX.set(nd.id, idx - (row.length - 1) / 2));
    }
    for (let pass = 0; pass < 2; pass++) {
      for (const k of sortedKeys) {
        const row = buckets.get(k);
        if (row.length <= 2) continue;
        const score = new Map();
        for (const nd of row) {
          const nbs = neighbors.get(nd.id);
          let sw = 0, wx = 0;
          for (const nb of nbs) {
            const lw = Math.log10(nb.w + 1);
            wx += (tempX.get(nb.id) || 0) * lw;
            sw += lw;
          }
          score.set(nd.id, sw > 0 ? wx / sw : tempX.get(nd.id));
        }
        row.sort((a, b) => (score.get(a.id) - score.get(b.id)) || (b.files - a.files));
        row.forEach((nd, idx) => tempX.set(nd.id, idx - (row.length - 1) / 2));
      }
    }

    const boxW = nCount > 80 ? 156 : 182;
    const boxH = nCount > 80 ? 44 : 52;
    const gapX = nCount > 80 ? 22 : 34;
    const gapY = nCount > 80 ? 54 : 74;
    const maxPerRow = nCount > 150 ? 12 : 9;

    state.positions.clear();
    let curY = 0;
    for (const k of sortedKeys) {
      const rowNodes = buckets.get(k);
      const chunks = [];
      for (let i = 0; i < rowNodes.length; i += maxPerRow) {
        chunks.push(rowNodes.slice(i, i + maxPerRow));
      }
      for (const chunk of chunks) {
        const totalW = chunk.length * boxW + (chunk.length - 1) * gapX;
        let curX = -totalW / 2;
        for (const nd of chunk) {
          state.positions.set(nd.id, {
            x: curX,
            y: curY,
            w: boxW,
            h: boxH,
          });
          curX += boxW + gapX;
        }
        curY += boxH + (chunks.length > 1 ? 26 : 0);
      }
      curY += gapY;
    }
  }

  function fitToScreen() {
    if (state.positions.size === 0) return;
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    for (const p of state.positions.values()) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x + p.w);
      maxY = Math.max(maxY, p.y + p.h);
    }
    const rect = wrap.getBoundingClientRect();
    const pad = 64;
    const gw = Math.max(1, maxX - minX);
    const gh = Math.max(1, maxY - minY);
    const scale = Math.min(
      1.35,
      Math.max(0.08, Math.min((rect.width - pad * 2) / gw, (rect.height - pad * 2) / gh))
    );
    state.cam.scale = scale;
    state.cam.x = rect.width / 2 - ((minX + maxX) / 2) * scale;
    state.cam.y = rect.height / 2 - ((minY + maxY) / 2) * scale;
    renderCanvas();
  }

  function focusNode(nid) {
    const p = state.positions.get(nid);
    if (!p) return;
    const rect = wrap.getBoundingClientRect();
    const targetScale = Math.max(state.cam.scale, 0.85);
    state.cam.scale = Math.min(targetScale, 1.4);
    state.cam.x = rect.width / 2 - (p.x + p.w / 2) * state.cam.scale;
    state.cam.y = rect.height / 2 - (p.y + p.h / 2) * state.cam.scale;
  }

  function getFilteredEdges() {
    const sel = state.selectedId;
    const minW = state.minWeight;
    const keepSel = state.keepSelectedEdges;
    return state.visibleEdges.filter((e) => {
      if (e.weight >= minW) return true;
      if (keepSel && sel && (e.src === sel || e.dst === sel)) return true;
      return false;
    });
  }

  function computeHighlightSets(filteredEdges) {
    const sel = state.selectedId;
    const upstreamNodes = new Set(); // sel imports these
    const downstreamNodes = new Set(); // these import sel
    const mutualNodes = new Set();
    const edgeRoles = new Map(); // edge -> "out" | "in" | "mutual" | "dim" | "normal"

    if (!sel || !state.visibleNodeMap.has(sel)) {
      for (const e of filteredEdges) edgeRoles.set(e, "normal");
      return { upstreamNodes, downstreamNodes, mutualNodes, edgeRoles };
    }

    if (state.hopMode === "direct") {
      for (const e of filteredEdges) {
        if (e.src === sel) upstreamNodes.add(e.dst);
        if (e.dst === sel) downstreamNodes.add(e.src);
      }
      for (const id of upstreamNodes) {
        if (downstreamNodes.has(id)) mutualNodes.add(id);
      }
      for (const e of filteredEdges) {
        if (e.src === sel && e.dst !== sel) {
          edgeRoles.set(e, mutualNodes.has(e.dst) ? "mutual" : "out");
        } else if (e.dst === sel && e.src !== sel) {
          edgeRoles.set(e, mutualNodes.has(e.src) ? "mutual" : "in");
        } else {
          edgeRoles.set(e, "dim");
        }
      }
    } else {
      // Transitive BFS upstream (following src -> dst) and downstream (dst -> src)
      const outAdj = new Map();
      const inAdj = new Map();
      for (const e of filteredEdges) {
        if (!outAdj.has(e.src)) outAdj.set(e.src, []);
        outAdj.get(e.src).push(e.dst);
        if (!inAdj.has(e.dst)) inAdj.set(e.dst, []);
        inAdj.get(e.dst).push(e.src);
      }
      const q1 = [sel];
      const visUp = new Set([sel]);
      while (q1.length) {
        const u = q1.shift();
        for (const v of (outAdj.get(u) || [])) {
          if (!visUp.has(v)) { visUp.add(v); upstreamNodes.add(v); q1.push(v); }
        }
      }
      const q2 = [sel];
      const visDown = new Set([sel]);
      while (q2.length) {
        const u = q2.shift();
        for (const v of (inAdj.get(u) || [])) {
          if (!visDown.has(v)) { visDown.add(v); downstreamNodes.add(v); q2.push(v); }
        }
      }
      for (const id of upstreamNodes) {
        if (downstreamNodes.has(id)) mutualNodes.add(id);
      }
      for (const e of filteredEdges) {
        const inUp = (e.src === sel || upstreamNodes.has(e.src)) && (upstreamNodes.has(e.dst) || e.dst === sel);
        const inDn = (e.dst === sel || downstreamNodes.has(e.dst)) && (downstreamNodes.has(e.src) || e.src === sel);
        if (inUp && inDn) edgeRoles.set(e, "mutual");
        else if (inUp) edgeRoles.set(e, "out");
        else if (inDn) edgeRoles.set(e, "in");
        else edgeRoles.set(e, "dim");
      }
    }
    return { upstreamNodes, downstreamNodes, mutualNodes, edgeRoles };
  }

  function updateCountsBadge() {
    const filtered = getFilteredEdges();
    hudCounts.textContent = `Visible: ${state.visibleNodes.length} nodes · ${filtered.length}/${state.visibleEdges.length} edges`;
  }

  function edgeCurvePoints(e) {
    const ps = state.positions.get(e.src);
    const pd = state.positions.get(e.dst);
    if (!ps || !pd) return null;
    const sx = ps.x + ps.w / 2;
    const sy = ps.y + ps.h / 2;
    const dx = pd.x + pd.w / 2;
    const dy = pd.y + pd.h / 2;

    // Anchor closer to top/bottom or sides depending on relative geometry
    const vx = dx - sx;
    const vy = dy - sy;
    let x1 = sx, y1 = sy, x2 = dx, y2 = dy;
    if (Math.abs(vy) >= Math.abs(vx) * 0.45) {
      y1 = vy >= 0 ? ps.y + ps.h : ps.y;
      y2 = vy >= 0 ? pd.y : pd.y + pd.h;
    } else {
      x1 = vx >= 0 ? ps.x + ps.w : ps.x;
      x2 = vx >= 0 ? pd.x : pd.x + pd.w;
    }
    const mx = (x1 + x2) / 2;
    const my = (y1 + y2) / 2;
    const len = Math.hypot(x2 - x1, y2 - y1) || 1;
    const nx = -(y2 - y1) / len;
    const ny = (x2 - x1) / len;
    const curveOffset = e.hasReverse ? Math.min(44, Math.max(16, len * 0.14)) : Math.min(26, len * 0.07);
    const cx = mx + nx * curveOffset;
    const cy = my + ny * curveOffset;
    return { x1, y1, cx, cy, x2, y2 };
  }

  function drawRoundedRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + w - r, y);
    ctx.quadraticCurveTo(x + w, y, x + w, y + r);
    ctx.lineTo(x + w, y + h - r);
    ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    ctx.lineTo(x + r, y + h);
    ctx.quadraticCurveTo(x, y + h, x, y + h - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
  }

  function renderCanvas() {
    const rect = wrap.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(rect.width * dpr) || canvas.height !== Math.round(rect.height * dpr)) {
      canvas.width = Math.round(rect.width * dpr);
      canvas.height = Math.round(rect.height * dpr);
    }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, rect.width, rect.height);

    ctx.save();
    ctx.translate(state.cam.x, state.cam.y);
    ctx.scale(state.cam.scale, state.cam.scale);

    const filteredEdges = getFilteredEdges();
    const { upstreamNodes, downstreamNodes, mutualNodes, edgeRoles } = computeHighlightSets(filteredEdges);

    // Draw dimmed/normal edges first, then highlighted edges on top
    const orderedEdges = filteredEdges.slice().sort((a, b) => {
      const ra = edgeRoles.get(a);
      const rb = edgeRoles.get(b);
      const pa = (ra === "dim") ? 0 : (ra === "normal" ? 1 : 2);
      const pb = (rb === "dim") ? 0 : (rb === "normal" ? 1 : 2);
      return pa - pb;
    });

    for (const e of orderedEdges) {
      const pts = edgeCurvePoints(e);
      if (!pts) continue;
      const role = edgeRoles.get(e);
      const isHover = state.hoveredEdge === e;
      let stroke = "rgba(100, 116, 139, 0.4)";
      let alpha = 1;
      let lw = Math.max(0.8, Math.min(4.8, 0.7 + Math.log10(e.weight + 1) * 0.85));

      if (role === "dim") {
        stroke = "rgba(148, 163, 184, 0.18)";
        lw = Math.min(lw, 1.4);
      } else if (role === "out") {
        stroke = "#0284c7";
        lw = Math.max(lw, 2.1);
      } else if (role === "in") {
        stroke = "#d97706";
        lw = Math.max(lw, 2.1);
      } else if (role === "mutual") {
        stroke = "#7c3aed";
        lw = Math.max(lw, 2.2);
      } else {
        stroke = e.weight >= 1000 ? "rgba(2, 132, 199, 0.55)" : "rgba(100, 116, 139, 0.35)";
      }
      if (isHover) {
        stroke = "#111111";
        lw += 1.4;
      }

      ctx.strokeStyle = stroke;
      ctx.lineWidth = lw;
      ctx.beginPath();
      ctx.moveTo(pts.x1, pts.y1);
      ctx.quadraticCurveTo(pts.cx, pts.cy, pts.x2, pts.y2);
      ctx.stroke();

      // Arrowhead near target
      if (role !== "dim" || state.cam.scale > 0.55) {
        const t = 0.96;
        const tx = 2 * (1 - t) * (pts.cx - pts.x1) + 2 * t * (pts.x2 - pts.cx);
        const ty = 2 * (1 - t) * (pts.cy - pts.y1) + 2 * t * (pts.y2 - pts.cy);
        const ang = Math.atan2(ty, tx);
        const headLen = Math.min(11, Math.max(6, 5 + lw * 1.1));
        ctx.fillStyle = stroke;
        ctx.beginPath();
        ctx.moveTo(pts.x2, pts.y2);
        ctx.lineTo(pts.x2 - headLen * Math.cos(ang - 0.38), pts.y2 - headLen * Math.sin(ang - 0.38));
        ctx.lineTo(pts.x2 - headLen * Math.cos(ang + 0.38), pts.y2 - headLen * Math.sin(ang + 0.38));
        ctx.closePath();
        ctx.fill();
      }

      // Edge weight label for highlighted direct edges or very heavy edges
      if ((role === "out" || role === "in" || role === "mutual" || isHover) && state.cam.scale >= 0.4) {
        const lx = 0.25 * pts.x1 + 0.5 * pts.cx + 0.25 * pts.x2;
        const ly = 0.25 * pts.y1 + 0.5 * pts.cy + 0.25 * pts.y2;
        const txt = fmt(e.weight);
        ctx.font = "600 10px ui-monospace, monospace";
        const tw = ctx.measureText(txt).width + 8;
        ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
        drawRoundedRect(lx - tw / 2, ly - 8, tw, 16, 2);
        ctx.fill();
        ctx.strokeStyle = "#cccccc";
        ctx.lineWidth = 0.8;
        ctx.stroke();
        ctx.fillStyle = stroke;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(txt, lx, ly);
      }
    }

    // Draw nodes
    for (const nd of state.visibleNodes) {
      const p = state.positions.get(nd.id);
      if (!p) continue;
      const c = colors[nd.top_dir] || colors["BuildAid"];
      const isSel = nd.id === state.selectedId;
      const isHover = nd.id === state.hoveredNodeId;
      const isUp = upstreamNodes.has(nd.id);
      const isDn = downstreamNodes.has(nd.id);
      const isMut = mutualNodes.has(nd.id);
      const dimmed = state.selectedId && !isSel && !isUp && !isDn && !isHover;

      ctx.save();
      ctx.globalAlpha = dimmed ? 0.28 : 1.0;

      // Fill box
      ctx.fillStyle = isSel ? "#eef6ff" : "#ffffff";
      drawRoundedRect(p.x, p.y, p.w, p.h, 3);
      ctx.fill();

      // Left color stripe
      ctx.fillStyle = c.dot;
      ctx.fillRect(p.x, p.y, 5, p.h);

      // Border highlight
      let borderCol = "#999999";
      let bw = 1.2;
      if (isSel) { borderCol = "#111111"; bw = 2.6; }
      else if (isMut) { borderCol = "#7c3aed"; bw = 2.2; }
      else if (isUp) { borderCol = "#0284c7"; bw = 2.0; }
      else if (isDn) { borderCol = "#d97706"; bw = 2.0; }
      if (isHover && !isSel) { borderCol = "#111111"; bw = 2.0; }

      ctx.strokeStyle = borderCol;
      ctx.lineWidth = bw;
      drawRoundedRect(p.x, p.y, p.w, p.h, 3);
      ctx.stroke();

      // Text inside node
      if (state.cam.scale >= 0.22) {
        ctx.fillStyle = "#111111";
        ctx.font = "700 11px -apple-system, BlinkMacSystemFont, sans-serif";
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        const maxChars = Math.floor((p.w - 30) / 6.3);
        const title = nd.label.length > maxChars ? nd.label.slice(0, maxChars - 1) + "…" : nd.label;
        ctx.fillText(title, p.x + 10, p.y + 7);

        ctx.fillStyle = "#555555";
        ctx.font = "10px ui-monospace, monospace";
        ctx.fillText(`${fmt(nd.files)}f · H=${nd.max_height}`, p.x + 10, p.y + p.h - 17);

        // Expand/collapse badge
        if (!nd.is_leaf) {
          const isExp = state.expandedIds.has(nd.id);
          const badge = isExp ? "−" : `+${nd.children_ids.length}`;
          ctx.font = "700 9px ui-monospace, monospace";
          const bwTxt = ctx.measureText(badge).width + 8;
          ctx.fillStyle = "#eeeeee";
          drawRoundedRect(p.x + p.w - bwTxt - 6, p.y + 6, bwTxt, 15, 2);
          ctx.fill();
          ctx.fillStyle = "#222222";
          ctx.textAlign = "center";
          ctx.fillText(badge, p.x + p.w - bwTxt / 2 - 6, p.y + 8);
        }
      }
      ctx.restore();
    }

    ctx.restore();
  }

  function screenToWorld(sx, sy) {
    return {
      x: (sx - state.cam.x) / state.cam.scale,
      y: (sy - state.cam.y) / state.cam.scale,
    };
  }

  function hitTestNode(wx, wy) {
    for (let i = state.visibleNodes.length - 1; i >= 0; i--) {
      const nd = state.visibleNodes[i];
      const p = state.positions.get(nd.id);
      if (p && wx >= p.x && wx <= p.x + p.w && wy >= p.y && wy <= p.y + p.h) {
        return nd.id;
      }
    }
    return null;
  }

  function hitTestEdge(wx, wy) {
    const filtered = getFilteredEdges();
    let best = null;
    let bestDist = 9 / Math.max(0.4, state.cam.scale);
    for (const e of filtered) {
      const pts = edgeCurvePoints(e);
      if (!pts) continue;
      for (let t = 0.1; t <= 0.9; t += 0.1) {
        const omt = 1 - t;
        const bx = omt * omt * pts.x1 + 2 * omt * t * pts.cx + t * t * pts.x2;
        const by = omt * omt * pts.y1 + 2 * omt * t * pts.cy + t * t * pts.y2;
        const d = Math.hypot(wx - bx, wy - by);
        if (d < bestDist) {
          bestDist = d;
          best = e;
        }
      }
    }
    return best;
  }

  function toggleExpandNode(nid) {
    const nd = nodesById[nid];
    if (!nd || nd.is_leaf) return;
    if (state.expandedIds.has(nid)) {
      // Collapse nid and any expanded descendants
      const stack = [nid];
      while (stack.length) {
        const cur = stack.pop();
        state.expandedIds.delete(cur);
        for (const cid of nodesById[cur].children_ids) stack.push(cid);
      }
    } else {
      // Expand ancestors up to nid and expand nid itself
      let cur = nid;
      while (cur) {
        if (!nodesById[cur].is_leaf) state.expandedIds.add(cur);
        state.treeOpenIds.add(cur);
        cur = nodesById[cur].parent_id;
      }
    }
    recomputeVisibleGraph();
  }

  function selectAndFocus(nid, expandParentIfHidden = true) {
    const nd = nodesById[nid];
    if (!nd) return;
    if (expandParentIfHidden && !state.visibleNodeMap.has(nid)) {
      let cur = nd.parent_id;
      while (cur) {
        state.expandedIds.add(cur);
        state.treeOpenIds.add(cur);
        cur = nodesById[cur].parent_id;
      }
      recomputeVisibleGraph();
    }
    state.selectedId = nid;
    let cur = nd.parent_id;
    while (cur) { state.treeOpenIds.add(cur); cur = nodesById[cur].parent_id; }
    focusNode(nid);
    updateCountsBadge();
    renderTreeSidebar();
    renderInspector();
    renderCanvas();
  }

  function renderTreeSidebar() {
    const frag = document.createDocumentFragment();
    function buildRow(nid, depth) {
      const nd = nodesById[nid];
      const row = document.createElement("div");
      row.className = "tree-row" + (state.selectedId === nid ? " selected" : "");
      row.style.paddingLeft = (6 + depth * 13) + "px";

      const tog = document.createElement("span");
      tog.className = "tree-toggle";
      const hasKids = nd.children_ids.length > 0;
      const isOpen = state.treeOpenIds.has(nid);
      tog.textContent = hasKids ? (isOpen ? "▼" : "▶") : "•";
      tog.addEventListener("click", (ev) => {
        ev.stopPropagation();
        if (!hasKids) return;
        if (state.treeOpenIds.has(nid)) state.treeOpenIds.delete(nid);
        else state.treeOpenIds.add(nid);
        renderTreeSidebar();
      });

      const dot = document.createElement("span");
      dot.className = "tree-dot";
      dot.style.background = (colors[nd.top_dir] || colors["BuildAid"]).border;

      const lbl = document.createElement("span");
      lbl.className = "tree-label";
      lbl.textContent = nd.label;
      lbl.title = nd.id.replace(/^L\\d:/, "");

      const cnt = document.createElement("span");
      cnt.className = "tree-count";
      cnt.textContent = fmt(nd.files);

      row.append(tog, dot, lbl, cnt);
      row.addEventListener("click", () => selectAndFocus(nid, true));
      row.addEventListener("dblclick", () => toggleExpandNode(nid));
      frag.appendChild(row);

      if (hasKids && isOpen) {
        for (const cid of nd.children_ids) buildRow(cid, depth + 1);
      }
    }
    for (const rid of rootIds) buildRow(rid, 0);
    dirTreeEl.innerHTML = "";
    dirTreeEl.appendChild(frag);
  }

  function renderInspector() {
    const nid = state.selectedId;
    if (!nid || !nodesById[nid]) {
      inspLevel.textContent = "—";
      inspBody.innerHTML = '<div class="empty-hint">Click any directory node to inspect its stats, imports, dependents, and top cross-boundary files.</div>';
      return;
    }
    const nd = nodesById[nid];
    inspLevel.textContent = `Level ${nd.level} (${nd.top_dir})`;

    // Gather incoming and outgoing edges in the CURRENT visible graph
    const outEdges = state.visibleEdges.filter((e) => e.src === nid).sort((a, b) => b.weight - a.weight);
    const inEdges = state.visibleEdges.filter((e) => e.dst === nid).sort((a, b) => b.weight - a.weight);
    const totOut = outEdges.reduce((s, e) => s + e.weight, 0);
    const totIn = inEdges.reduce((s, e) => s + e.weight, 0);
    const sccSize = sccInfoByKey.get(nd.level + ":" + nd.dir_key) || 1;
    const isExp = state.expandedIds.has(nid);

    let html = `
      <div style="margin-bottom:10px;">
        <div style="font-size:14px;font-weight:700;color:var(--text);word-break:break-word;">${escHtml(nd.id.replace(/^L\\d:/, ""))}</div>
        <div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
          ${!nd.is_leaf ? `<button id="insp-toggle-exp" class="sm">${isExp ? "Collapse Subdirs" : `Expand (+${nd.children_ids.length} subdirs)`}</button>` : '<span class="pill">Leaf Directory</span>'}
          ${nd.parent_id ? `<button id="insp-up-parent" class="sm">Parent: ${escHtml(nodesById[nd.parent_id].label)}</button>` : ""}
          ${sccSize > 1 ? `<span class="pill" style="border-color:#7c3aed;color:#6b21a8;">In L${nd.level} SCC (size ${sccSize})</span>` : `<span class="pill">Acyclic at L${nd.level}</span>`}
        </div>
      </div>

      <div class="stat-grid">
        <div class="stat-card"><div class="k">Dist from Main</div><div class="v">min ${nd.min_dist} · avg ${nd.avg_dist}</div></div>
        <div class="stat-card"><div class="k">Max Leaf Height</div><div class="v">${nd.max_height}</div></div>
      </div>

      <div class="sec-title">
        <span style="color:var(--out-color);">Imports → (Dependencies of this dir)</span>
        <span>${fmt(totOut)} total</span>
      </div>
      <div class="edge-list">
    `;

    if (outEdges.length === 0) {
      html += '<div class="empty-hint">No cross-directory outgoing imports in current view.</div>';
    } else {
      for (const e of outEdges.slice(0, 15)) {
        const target = nodesById[e.dst];
        const pct = totOut > 0 ? ((e.weight / totOut) * 100).toFixed(1) : "0.0";
        const fileNote = e.srcFiles !== null ? ` · ${fmt(e.srcFiles)}→${fmt(e.dstFiles)}f` : "";
        html += `
          <div class="edge-row jump-node" data-nid="${escHtml(e.dst)}">
            <span class="edge-name" title="${escHtml(target.id.replace(/^L\\d:/, ""))}">${escHtml(target.id.replace(/^L\\d:/, ""))}</span>
            <span class="edge-meta">
              ${e.hasReverse ? `<span class="tag-mutual" title="Reverse edge weight: ${fmt(e.reverseWeight)}">⇄ ${fmt(e.reverseWeight)}</span>` : ""}
              <span style="color:var(--out-color);">${fmt(e.weight)}</span>
              <span style="color:var(--muted);">(${pct}%${fileNote})</span>
            </span>
          </div>`;
      }
    }
    html += `</div>`;

    html += `
      <div class="sec-title">
        <span style="color:var(--in-color);">Imported by ← (Dependents on this dir)</span>
        <span>${fmt(totIn)} total</span>
      </div>
      <div class="edge-list">
    `;
    if (inEdges.length === 0) {
      html += '<div class="empty-hint">No cross-directory incoming imports in current view.</div>';
    } else {
      for (const e of inEdges.slice(0, 15)) {
        const src = nodesById[e.src];
        const pct = totIn > 0 ? ((e.weight / totIn) * 100).toFixed(1) : "0.0";
        const fileNote = e.srcFiles !== null ? ` · ${fmt(e.srcFiles)}→${fmt(e.dstFiles)}f` : "";
        html += `
          <div class="edge-row jump-node" data-nid="${escHtml(e.src)}">
            <span class="edge-name" title="${escHtml(src.id.replace(/^L\\d:/, ""))}">${escHtml(src.id.replace(/^L\\d:/, ""))}</span>
            <span class="edge-meta">
              ${e.hasReverse ? `<span class="tag-mutual" title="Reverse edge weight: ${fmt(e.reverseWeight)}">⇄ ${fmt(e.reverseWeight)}</span>` : ""}
              <span style="color:var(--in-color);">${fmt(e.weight)}</span>
              <span style="color:var(--muted);">(${pct}%${fileNote})</span>
            </span>
          </div>`;
      }
    }
    html += `</div>`;

    html += `<div class="sec-title"><span>Top Cross-Boundary Outgoing Files (L${nd.level})</span></div>`;
    if (nd.top_out_files.length === 0) {
      html += '<div class="empty-hint">None at this level.</div>';
    } else {
      for (const f of nd.top_out_files) {
        const href = (window.RHVersion && RHVersion.sourceUrl) ? RHVersion.sourceUrl(f.rel_path) : f.rel_path;
        html += `
          <a class="file-link" href="${escHtml(href)}" target="_blank" rel="noopener">
            ${escHtml(f.rel_path)}
            <div class="file-sub">${fmt(f.cross_out)} cross-dir imports out · ${fmt(f.lines)} lines · dist ${f.dist} · H=${f.height}</div>
          </a>`;
      }
    }

    html += `<div class="sec-title"><span>Top Cross-Boundary Imported Files (L${nd.level})</span></div>`;
    if (nd.top_in_files.length === 0) {
      html += '<div class="empty-hint">None at this level.</div>';
    } else {
      for (const f of nd.top_in_files) {
        const href = (window.RHVersion && RHVersion.sourceUrl) ? RHVersion.sourceUrl(f.rel_path) : f.rel_path;
        html += `
          <a class="file-link" href="${escHtml(href)}" target="_blank" rel="noopener">
            ${escHtml(f.rel_path)}
            <div class="file-sub">${fmt(f.cross_in)} cross-dir imports in · ${fmt(f.lines)} lines · dist ${f.dist} · H=${f.height}</div>
          </a>`;
      }
    }

    inspBody.innerHTML = html;

    const btnExp = document.getElementById("insp-toggle-exp");
    if (btnExp) btnExp.addEventListener("click", () => toggleExpandNode(nid));
    const btnParent = document.getElementById("insp-up-parent");
    if (btnParent) btnParent.addEventListener("click", () => {
      const pid = nd.parent_id;
      if (pid) {
        state.expandedIds.delete(pid);
        state.selectedId = pid;
        recomputeVisibleGraph();
        fitToScreen();
      }
    });
    for (const row of inspBody.querySelectorAll(".jump-node")) {
      row.addEventListener("click", () => selectAndFocus(row.getAttribute("data-nid"), true));
    }
  }

  // Presets
  function setPreset(mode) {
    document.getElementById("btn-l1").classList.toggle("active", mode === "l1");
    document.getElementById("btn-l2-major").classList.toggle("active", mode === "l2-major");
    document.getElementById("btn-l2-all").classList.toggle("active", mode === "l2-all");

    state.expandedIds.clear();
    if (mode === "l2-major") {
      for (const rid of rootIds) {
        const t = rid.slice(3);
        if (["(root)", "Formalism", "Lemmata", "BuildAid"].includes(t)) continue;
        if (nodesById[rid] && !nodesById[rid].is_leaf) state.expandedIds.add(rid);
      }
    } else if (mode === "l2-all") {
      for (const rid of rootIds) {
        if (!nodesById[rid].is_leaf) state.expandedIds.add(rid);
      }
    }
    recomputeVisibleGraph();
    fitToScreen();
  }

  document.getElementById("btn-l1").addEventListener("click", () => setPreset("l1"));
  document.getElementById("btn-l2-major").addEventListener("click", () => setPreset("l2-major"));
  document.getElementById("btn-l2-all").addEventListener("click", () => setPreset("l2-all"));

  document.getElementById("btn-layout-height").addEventListener("click", (ev) => {
    state.layoutMode = "height";
    ev.target.classList.add("active");
    document.getElementById("btn-layout-dist").classList.remove("active");
    layoutVisibleNodes();
    fitToScreen();
  });
  document.getElementById("btn-layout-dist").addEventListener("click", (ev) => {
    state.layoutMode = "dist";
    ev.target.classList.add("active");
    document.getElementById("btn-layout-height").classList.remove("active");
    layoutVisibleNodes();
    fitToScreen();
  });

  document.getElementById("btn-hop-1").addEventListener("click", (ev) => {
    state.hopMode = "direct";
    ev.target.classList.add("active");
    document.getElementById("btn-hop-all").classList.remove("active");
    renderCanvas();
  });
  document.getElementById("btn-hop-all").addEventListener("click", (ev) => {
    state.hopMode = "transitive";
    ev.target.classList.add("active");
    document.getElementById("btn-hop-1").classList.remove("active");
    renderCanvas();
  });

  function applyWeightFilter(w) {
    state.minWeight = w;
    weightVal.textContent = "≥ " + fmt(w);
    weightSlider.value = weightToSlider(w);
    updateCountsBadge();
    renderCanvas();
  }
  weightSlider.addEventListener("input", () => applyWeightFilter(sliderToWeight(weightSlider.value)));
  for (const b of document.querySelectorAll(".preset-w")) {
    b.addEventListener("click", () => applyWeightFilter(Number(b.getAttribute("data-w"))));
  }
  chkKeepSel.addEventListener("change", () => {
    state.keepSelectedEdges = chkKeepSel.checked;
    updateCountsBadge();
    renderCanvas();
  });

  // Search box across all 877 nodes
  const allSearchNodes = Object.values(nodesById).sort((a, b) => b.files - a.files);
  searchInput.addEventListener("input", () => {
    const q = searchInput.value.trim().toLowerCase();
    if (!q) {
      searchResults.style.display = "none";
      return;
    }
    const matches = allSearchNodes
      .filter((n) => n.id.toLowerCase().includes(q) || n.dir_key.toLowerCase().includes(q))
      .slice(0, 25);
    if (matches.length === 0) {
      searchResults.innerHTML = '<div class="search-item"><span class="sname">No matching directories</span></div>';
    } else {
      searchResults.innerHTML = matches
        .map(
          (m) => `
          <div class="search-item" data-nid="${escHtml(m.id)}">
            <span class="sname">${escHtml(m.id.replace(/^L\\d:/, ""))}</span>
            <span class="smeta">L${m.level} · ${fmt(m.files)}f</span>
          </div>`
        )
        .join("");
      for (const el of searchResults.querySelectorAll(".search-item")) {
        el.addEventListener("click", () => {
          const nid = el.getAttribute("data-nid");
          searchResults.style.display = "none";
          selectAndFocus(nid, true);
        });
      }
    }
    searchResults.style.display = "block";
  });
  document.addEventListener("click", (ev) => {
    if (!searchResults.contains(ev.target) && ev.target !== searchInput) {
      searchResults.style.display = "none";
    }
  });

  // Canvas interactions (pan, zoom, click, double-click, hover)
  canvas.addEventListener("mousedown", (ev) => {
    state.dragging = true;
    state.dragMoved = false;
    state.dragStart = { x: ev.clientX, y: ev.clientY, camX: state.cam.x, camY: state.cam.y };
    canvas.classList.add("dragging");
  });
  window.addEventListener("mousemove", (ev) => {
    if (state.dragging) {
      const dx = ev.clientX - state.dragStart.x;
      const dy = ev.clientY - state.dragStart.y;
      if (Math.hypot(dx, dy) > 4) state.dragMoved = true;
      state.cam.x = state.dragStart.camX + dx;
      state.cam.y = state.dragStart.camY + dy;
      tooltip.style.display = "none";
      renderCanvas();
      return;
    }
    if (ev.target !== canvas) {
      tooltip.style.display = "none";
      return;
    }
    const rect = canvas.getBoundingClientRect();
    const sx = ev.clientX - rect.left;
    const sy = ev.clientY - rect.top;
    const wpt = screenToWorld(sx, sy);
    const nid = hitTestNode(wpt.x, wpt.y);
    const edge = nid ? null : hitTestEdge(wpt.x, wpt.y);
    if (nid !== state.hoveredNodeId || edge !== state.hoveredEdge) {
      state.hoveredNodeId = nid;
      state.hoveredEdge = edge;
      renderCanvas();
    }
    if (nid) {
      const nd = nodesById[nid];
      tooltip.innerHTML = `
        <div style="font-weight:700;margin-bottom:3px;">${escHtml(nd.id.replace(/^L\\d:/, ""))}</div>
        <div>Min dist: ${nd.min_dist} · Max height: ${nd.max_height}</div>
        ${!nd.is_leaf ? '<div style="color:#94a3b8;margin-top:3px;">Double-click to expand/collapse</div>' : ""}
      `;
      tooltip.style.left = Math.min(rect.width - 280, sx + 14) + "px";
      tooltip.style.top = Math.min(rect.height - 95, sy + 14) + "px";
      tooltip.style.display = "block";
      canvas.style.cursor = "pointer";
    } else if (edge) {
      const revTxt = edge.hasReverse ? `<br/>Reverse (${escHtml(edge.dst.replace(/^L\\d:/,""))} → ${escHtml(edge.src.replace(/^L\\d:/,""))}): <strong>${fmt(edge.reverseWeight)}</strong>` : "";
      tooltip.innerHTML = `
        <div><strong>${escHtml(edge.src.replace(/^L\\d:/, ""))}</strong></div>
        <div>imports → <strong>${escHtml(edge.dst.replace(/^L\\d:/, ""))}</strong></div>
        <div style="margin-top:3px;">Weight: <strong>${fmt(edge.weight)}</strong> file imports${revTxt}</div>
      `;
      tooltip.style.left = Math.min(rect.width - 310, sx + 14) + "px";
      tooltip.style.top = Math.min(rect.height - 95, sy + 14) + "px";
      tooltip.style.display = "block";
      canvas.style.cursor = "pointer";
    } else {
      tooltip.style.display = "none";
      canvas.style.cursor = "grab";
    }
  });
  window.addEventListener("mouseup", (ev) => {
    if (!state.dragging) return;
    state.dragging = false;
    canvas.classList.remove("dragging");
    if (!state.dragMoved && ev.target === canvas) {
      const rect = canvas.getBoundingClientRect();
      const wpt = screenToWorld(ev.clientX - rect.left, ev.clientY - rect.top);
      const nid = hitTestNode(wpt.x, wpt.y);
      if (nid) {
        state.selectedId = nid;
        let cur = nodesById[nid].parent_id;
        while (cur) { state.treeOpenIds.add(cur); cur = nodesById[cur].parent_id; }
        updateCountsBadge();
        renderTreeSidebar();
        renderInspector();
        renderCanvas();
      }
    }
  });
  canvas.addEventListener("dblclick", (ev) => {
    const rect = canvas.getBoundingClientRect();
    const wpt = screenToWorld(ev.clientX - rect.left, ev.clientY - rect.top);
    const nid = hitTestNode(wpt.x, wpt.y);
    if (nid) {
      toggleExpandNode(nid);
      fitToScreen();
    }
  });
  canvas.addEventListener(
    "wheel",
    (ev) => {
      ev.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const sx = ev.clientX - rect.left;
      const sy = ev.clientY - rect.top;
      const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
      const newScale = Math.min(2.8, Math.max(0.08, state.cam.scale * factor));
      const ratio = newScale / state.cam.scale;
      state.cam.x = sx - (sx - state.cam.x) * ratio;
      state.cam.y = sy - (sy - state.cam.y) * ratio;
      state.cam.scale = newScale;
      renderCanvas();
    },
    { passive: false }
  );

  document.getElementById("btn-zoom-in").addEventListener("click", () => {
    const rect = wrap.getBoundingClientRect();
    const cx = rect.width / 2, cy = rect.height / 2;
    const ns = Math.min(2.8, state.cam.scale * 1.25);
    const r = ns / state.cam.scale;
    state.cam.x = cx - (cx - state.cam.x) * r;
    state.cam.y = cy - (cy - state.cam.y) * r;
    state.cam.scale = ns;
    renderCanvas();
  });
  document.getElementById("btn-zoom-out").addEventListener("click", () => {
    const rect = wrap.getBoundingClientRect();
    const cx = rect.width / 2, cy = rect.height / 2;
    const ns = Math.max(0.08, state.cam.scale / 1.25);
    const r = ns / state.cam.scale;
    state.cam.x = cx - (cx - state.cam.x) * r;
    state.cam.y = cy - (cy - state.cam.y) * r;
    state.cam.scale = ns;
    renderCanvas();
  });
  document.getElementById("btn-fit").addEventListener("click", fitToScreen);
  document.getElementById("btn-clear-sel").addEventListener("click", () => {
    state.selectedId = null;
    updateCountsBadge();
    renderTreeSidebar();
    renderInspector();
    renderCanvas();
  });

  window.addEventListener("resize", renderCanvas);

  // Initialize view
  recomputeVisibleGraph();
  fitToScreen();
}
RHVersion.loadDataScript("dependency_graph/dir_graph_data.js", "__DEP_GRAPH_DATA__", initDepExplorer);
</script>
</body>
</html>
"""
    out_path.write_text(html_doc, encoding="utf-8")


def main() -> None:
    global SRC_DIR, DB_PATH, META_PATH, OUT_DIR
    parser = argparse.ArgumentParser(description="Build directory-level dependency graphs")
    parser.add_argument("--src-dir", type=Path, default=SRC_DIR)
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--meta-path", type=Path, default=META_PATH)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--version-label", type=str, default="")
    parser.add_argument("--source-blob-base", type=str, default="")
    parser.add_argument("--rel-src-label", type=str, default="src/")
    parser.add_argument("--write-html", action="store_true", help="Write canonical dependency_explorer.html")
    args = parser.parse_args()

    SRC_DIR = args.src_dir
    DB_PATH = args.db_path
    META_PATH = args.meta_path
    OUT_DIR = args.out_dir
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    data = load_graph_data()

    # Save dir_graph.json + dir_graph_data.js
    json_out = {k: v for k, v in data.items() if not k.startswith("_")}
    json_path = OUT_DIR / "dir_graph.json"
    json_path.write_text(json.dumps(json_out, indent=2), encoding="utf-8")

    embedded_payload = {
        "meta": data["meta"],
        "colors": TOP_COLORS,
        "top_order": data.get("top_order", TOP_ORDER),
        "levels": {
            "1": data["levels"]["1"],
            "2": data["levels"]["2"],
            "3": {
                "node_count": data["levels"]["3"]["node_count"],
                "edge_count": data["levels"]["3"]["edge_count"],
                "total_cross_edges": data["levels"]["3"]["total_cross_edges"],
                "mutual_pairs": data["levels"]["3"]["mutual_pairs"],
                "nontrivial_scc_count": data["levels"]["3"]["nontrivial_scc_count"],
                "sccs": data["levels"]["3"]["sccs"],
            },
        },
        "tree": data["tree"],
    }
    js_blob = json.dumps(embedded_payload, separators=(",", ":"), ensure_ascii=True).replace("<", "\\u003c")
    js_path = OUT_DIR / "dir_graph_data.js"
    js_path.write_text(f"window.__DEP_GRAPH_DATA__ = {js_blob};\n", encoding="utf-8")

    mmd_path = OUT_DIR / "top_level_graph.mmd"
    top_dot_path = OUT_DIR / "top_level_graph.dot"
    top_svg_path = OUT_DIR / "top_level_graph.svg"
    d2_dot_path = OUT_DIR / "depth2_major_graph.dot"
    d2_svg_path = OUT_DIR / "depth2_major_graph.svg"
    readme_path = OUT_DIR / "README.md"

    write_top_level_mermaid(data, mmd_path)
    write_top_level_dot(data, top_dot_path)
    write_depth2_major_dot(data, d2_dot_path)
    render_svg_with_dot(top_dot_path, top_svg_path)
    render_svg_with_dot(d2_dot_path, d2_svg_path)
    write_readme_md(
        data,
        readme_path,
        source_blob_base=args.source_blob_base,
        version_label=args.version_label,
        rel_src_label=args.rel_src_label,
    )

    outputs = [json_path, js_path, mmd_path, top_dot_path, top_svg_path, d2_dot_path, d2_svg_path, readme_path]
    if args.write_html:
        html_path = SCRIPT_DIR / "dependency_explorer.html"
        write_explorer_html(data, html_path)
        outputs.append(html_path)

    for p in outputs:
        print(f"Wrote {p} ({p.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
