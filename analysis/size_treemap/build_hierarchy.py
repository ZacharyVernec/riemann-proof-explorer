#!/usr/bin/env python3
"""Build directory size hierarchy JSON and architectural diagnostics from graph.sqlite."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path("/home/ubuntu/riemann_proof")
DB_PATH = ROOT / "analysis" / "data" / "graph.sqlite"
META_PATH = ROOT / "analysis" / "data" / "meta.json"
OUT_DIR = ROOT / "analysis" / "size_treemap"
OUT_JSON = OUT_DIR / "hierarchy_sizes.json"

MAX_TOP_FILES_LINES = 10
MAX_TOP_FILES_DECLS = 5


def compute_quantiles(values: list[int]) -> dict[str, float | int]:
    """Compute min, p10, p25, median, mean, p75, p90, p95, p99, max, sum."""
    n = len(values)
    if n == 0:
        return {
            "count": 0,
            "sum": 0,
            "min": 0,
            "p10": 0,
            "p25": 0,
            "median": 0,
            "mean": 0.0,
            "p75": 0,
            "p90": 0,
            "p95": 0,
            "p99": 0,
            "max": 0,
        }
    s = sorted(values)

    def pct(p: float) -> int | float:
        idx = (p / 100.0) * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        if frac == 0:
            return s[lo]
        val = s[lo] * (1.0 - frac) + s[hi] * frac
        return round(val, 2)

    median: int | float
    if n % 2 == 1:
        median = s[n // 2]
    else:
        mid = (s[n // 2 - 1] + s[n // 2]) / 2.0
        median = int(mid) if mid.is_integer() else round(mid, 2)

    return {
        "count": n,
        "sum": sum(s),
        "min": s[0],
        "p10": pct(10),
        "p25": pct(25),
        "median": median,
        "mean": round(sum(s) / n, 2),
        "p75": pct(75),
        "p90": pct(90),
        "p95": pct(95),
        "p99": pct(99),
        "max": s[-1],
    }


def make_empty_acc() -> dict[str, Any]:
    return {
        "files": 0,
        "lines": 0,
        "bytes": 0,
        "theorems": 0,
        "lemmas": 0,
        "defs": 0,
        "structures": 0,
        "other_decls": 0,
        "dist_sum": 0,
        "dist_cnt": 0,
        "min_dist": None,
        "max_height": 0,
    }


def add_mod_to_acc(acc: dict[str, Any], row: tuple[Any, ...]) -> None:
    # row: (rel_path, dir_path, top_dir, depth2_dir, depth3_dir, lines, bytes, n_thm, n_lem, n_def, n_str, n_oth, dist, height)
    _, _, _, _, _, lines, b, thm, lem, df, st, oth, dist, height = row
    acc["files"] += 1
    acc["lines"] += lines
    acc["bytes"] += b
    acc["theorems"] += thm
    acc["lemmas"] += lem
    acc["defs"] += df
    acc["structures"] += st
    acc["other_decls"] += oth
    if dist is not None:
        acc["dist_sum"] += dist
        acc["dist_cnt"] += 1
        if acc["min_dist"] is None or dist < acc["min_dist"]:
            acc["min_dist"] = dist
    if height is not None and height > acc["max_height"]:
        acc["max_height"] = height


def merge_acc(dst: dict[str, Any], src: dict[str, Any]) -> None:
    dst["files"] += src["files"]
    dst["lines"] += src["lines"]
    dst["bytes"] += src["bytes"]
    dst["theorems"] += src["theorems"]
    dst["lemmas"] += src["lemmas"]
    dst["defs"] += src["defs"]
    dst["structures"] += src["structures"]
    dst["other_decls"] += src["other_decls"]
    dst["dist_sum"] += src["dist_sum"]
    dst["dist_cnt"] += src["dist_cnt"]
    if src["min_dist"] is not None:
        if dst["min_dist"] is None or src["min_dist"] < dst["min_dist"]:
            dst["min_dist"] = src["min_dist"]
    if src["max_height"] > dst["max_height"]:
        dst["max_height"] = src["max_height"]


def finalize_metrics(acc: dict[str, Any]) -> dict[str, Any]:
    tl = acc["theorems"] + acc["lemmas"]
    ds = acc["defs"] + acc["structures"]
    od = acc["other_decls"]
    return {
        "files": acc["files"],
        "lines": acc["lines"],
        "bytes": acc["bytes"],
        "theorems_lemmas": tl,
        "defs_structures": ds,
        "other_decls": od,
        "all_decls": tl + ds + od,
        "avg_dist_from_main": round(acc["dist_sum"] / acc["dist_cnt"], 2) if acc["dist_cnt"] > 0 else None,
        "min_dist_from_main": acc["min_dist"],
        "max_height": acc["max_height"],
    }


def select_top_files(direct_mods: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    """Select compact union of top direct files by lines, thm+lem, and def+str."""
    if not direct_mods:
        return []
    # item: (rel_path, lines, bytes, tl, ds, od, dist, height)
    by_lines = sorted(direct_mods, key=lambda x: (-x[1], -x[2], x[0]))[:MAX_TOP_FILES_LINES]
    chosen: dict[str, tuple[Any, ...]] = {x[0]: x for x in by_lines}
    if len(direct_mods) > MAX_TOP_FILES_LINES:
        by_tl = sorted(direct_mods, key=lambda x: (-x[3], -x[1], x[0]))[:MAX_TOP_FILES_DECLS]
        by_ds = sorted(direct_mods, key=lambda x: (-x[4], -x[1], x[0]))[:MAX_TOP_FILES_DECLS]
        for x in by_tl + by_ds:
            if x[0] not in chosen:
                chosen[x[0]] = x
    ordered = sorted(chosen.values(), key=lambda x: (-x[1], -x[2], x[0]))
    return [
        {
            "name": Path(x[0]).name,
            "lines": x[1],
            "bytes": x[2],
            "theorems_lemmas": x[3],
            "defs_structures": x[4],
            "other_decls": x[5],
            "dist": x[6],
            "height": x[7],
        }
        for x in ordered
    ]


def bucket_decls(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    buckets = [
        ("0", lambda d: d == 0),
        ("1", lambda d: d == 1),
        ("2", lambda d: d == 2),
        ("3-5", lambda d: 3 <= d <= 5),
        ("6-10", lambda d: 6 <= d <= 10),
        ("11-25", lambda d: 11 <= d <= 25),
        ("26-100", lambda d: 26 <= d <= 100),
        ("101+", lambda d: d >= 101),
    ]
    total = len(rows)
    counts = [0] * len(buckets)
    lines_sums = [0] * len(buckets)
    for r in rows:
        d = r[7] + r[8] + r[9] + r[10] + r[11]
        for i, (_, pred) in enumerate(buckets):
            if pred(d):
                counts[i] += 1
                lines_sums[i] += r[5]
                break
    return [
        {
            "bucket": label,
            "files": counts[i],
            "pct_files": round(100.0 * counts[i] / total, 2),
            "lines": lines_sums[i],
        }
        for i, (label, _) in enumerate(buckets)
    ]


def bucket_lines(rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
    buckets = [
        ("1-20", lambda l: l <= 20),
        ("21-50", lambda l: 21 <= l <= 50),
        ("51-100", lambda l: 51 <= l <= 100),
        ("101-200", lambda l: 101 <= l <= 200),
        ("201-500", lambda l: 201 <= l <= 500),
        ("501-1000", lambda l: 501 <= l <= 1000),
        ("1001+", lambda l: l >= 1001),
    ]
    total = len(rows)
    counts = [0] * len(buckets)
    lines_sums = [0] * len(buckets)
    for r in rows:
        l = r[5]
        for i, (_, pred) in enumerate(buckets):
            if pred(l):
                counts[i] += 1
                lines_sums[i] += l
                break
    return [
        {
            "bucket": label,
            "files": counts[i],
            "pct_files": round(100.0 * counts[i] / total, 2),
            "lines": lines_sums[i],
        }
        for i, (label, _) in enumerate(buckets)
    ]


def build_data() -> dict[str, Any]:
    t0 = time.time()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    rows = conn.execute(
        """
        SELECT rel_path, dir_path, top_dir, depth2_dir, depth3_dir,
               lines, bytes, n_theorems, n_lemmas, n_defs, n_structures, n_other_decls,
               dist_from_main, height_from_leaves
        FROM modules
        ORDER BY rel_path
        """
    ).fetchall()

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))

    # Group direct files by dir_path and build full directory set
    direct_acc: dict[str, dict[str, Any]] = defaultdict(make_empty_acc)
    direct_files_map: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    all_dirs: set[str] = {""}
    children_map: dict[str, set[str]] = defaultdict(set)

    # Groupings for diagnostics
    top_groups: dict[str, list[tuple[Any, ...]]] = defaultdict(list)
    d2_acc: dict[str, dict[str, Any]] = defaultdict(make_empty_acc)
    d2_parent: dict[str, str] = {}
    d3_acc: dict[str, dict[str, Any]] = defaultdict(make_empty_acc)
    d3_parent: dict[str, str] = {}

    for row in rows:
        rel_path, dir_path, top_dir, d2_dir, d3_dir, lines, b, thm, lem, df, st, oth, dist, height = row
        add_mod_to_acc(direct_acc[dir_path], row)
        direct_files_map[dir_path].append(
            (rel_path, lines, b, thm + lem, df + st, oth, dist, height)
        )

        top_groups[top_dir].append(row)
        add_mod_to_acc(d2_acc[d2_dir], row)
        d2_parent[d2_dir] = top_dir
        add_mod_to_acc(d3_acc[d3_dir], row)
        d3_parent[d3_dir] = d2_dir

        if dir_path:
            parts = dir_path.split("/")
            prev = ""
            for i in range(1, len(parts) + 1):
                cur = "/".join(parts[:i])
                all_dirs.add(cur)
                children_map[prev].add(cur)
                prev = cur

    # Compute subtree accumulators bottom-up (longest path first)
    subtree_acc: dict[str, dict[str, Any]] = {d: make_empty_acc() for d in all_dirs}
    for d in sorted(all_dirs, key=lambda s: (0 if not s else s.count("/") + 1, s), reverse=True):
        acc = subtree_acc[d]
        if d in direct_acc:
            merge_acc(acc, direct_acc[d])
        for ch in children_map.get(d, ()):
            merge_acc(acc, subtree_acc[ch])

    def build_node(d: str) -> dict[str, Any]:
        depth = 0 if not d else d.count("/") + 1
        name = "lean/src" if not d else d.rsplit("/", 1)[-1]
        top_dir = "(root)" if not d else d.split("/", 1)[0]
        node: dict[str, Any] = {
            "name": name,
            "path": d,
            "top_dir": top_dir,
            "depth": depth,
        }
        node.update(finalize_metrics(subtree_acc[d]))

        child_paths = sorted(
            children_map.get(d, ()),
            key=lambda c: (-subtree_acc[c]["lines"], -subtree_acc[c]["files"], c),
        )
        has_direct = d in direct_acc and direct_acc[d]["files"] > 0
        if has_direct and child_paths:
            node["direct"] = finalize_metrics(direct_acc[d])
        if has_direct:
            node["top_files"] = select_top_files(direct_files_map[d])
        if child_paths:
            node["children"] = [build_node(c) for c in child_paths]
        return node

    tree = build_node("")

    # Sanity check against meta.json
    assert tree["files"] == meta["total_files"], (tree["files"], meta["total_files"])
    assert tree["lines"] == meta["total_lines"], (tree["lines"], meta["total_lines"])
    assert tree["bytes"] == meta["total_bytes"], (tree["bytes"], meta["total_bytes"])

    # Verify dir_stats level=1, 2, 3 consistency
    ds_lvl1 = {
        r[0]: r[1:]
        for r in conn.execute(
            "SELECT dir_key, files, lines, bytes, theorems+lemmas, defs+structures FROM dir_stats WHERE level=1"
        )
    }
    assert len(ds_lvl1) == len(top_groups)

    total_files = meta["total_files"]
    total_lines = meta["total_lines"]
    total_bytes = meta["total_bytes"]
    total_tl = tree["theorems_lemmas"]
    total_ds = tree["defs_structures"]

    # Complete top_dir breakdown
    top_dirs_summary: list[dict[str, Any]] = []
    by_top_dist: dict[str, Any] = {}
    stmt_by_top: dict[str, dict[str, int]] = {}
    for td, td_rows in sorted(top_groups.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        acc = make_empty_acc()
        one_decl = 0
        le2_decl = 0
        le20_lines = 0
        stmt_cnt = 0
        stmt_lines = 0
        for r in td_rows:
            add_mod_to_acc(acc, r)
            d_cnt = r[7] + r[8] + r[9] + r[10] + r[11]
            if d_cnt == 1:
                one_decl += 1
            if d_cnt <= 2:
                le2_decl += 1
            if r[5] <= 20:
                le20_lines += 1
            if r[0].endswith("Statement.lean"):
                stmt_cnt += 1
                stmt_lines += r[5]
        m = finalize_metrics(acc)
        q_lines = compute_quantiles([r[5] for r in td_rows])
        q_bytes = compute_quantiles([r[6] for r in td_rows])
        q_decls = compute_quantiles([r[7] + r[8] + r[9] + r[10] + r[11] for r in td_rows])
        q_tl = compute_quantiles([r[7] + r[8] for r in td_rows])
        q_ds = compute_quantiles([r[9] + r[10] for r in td_rows])

        by_top_dist[td] = {
            "lines": q_lines,
            "bytes": q_bytes,
            "all_decls": q_decls,
            "theorems_lemmas": q_tl,
            "defs_structures": q_ds,
        }
        stmt_by_top[td] = {"files": stmt_cnt, "lines": stmt_lines}

        n_td = len(td_rows)
        top_dirs_summary.append(
            {
                "top_dir": td,
                **m,
                "pct_files": round(100.0 * m["files"] / total_files, 2),
                "pct_lines": round(100.0 * m["lines"] / total_lines, 2),
                "pct_bytes": round(100.0 * m["bytes"] / total_bytes, 2),
                "pct_theorems_lemmas": round(100.0 * m["theorems_lemmas"] / total_tl, 2),
                "pct_defs_structures": round(100.0 * m["defs_structures"] / total_ds, 2),
                "mean_lines_per_file": q_lines["mean"],
                "median_lines_per_file": q_lines["median"],
                "mean_decls_per_file": q_decls["mean"],
                "median_decls_per_file": q_decls["median"],
                "one_decl_files": one_decl,
                "pct_one_decl": round(100.0 * one_decl / n_td, 2),
                "le2_decl_files": le2_decl,
                "le20_line_files": le20_lines,
                "statement_files": stmt_cnt,
                "statement_lines": stmt_lines,
            }
        )

    # Complete depth2_dir breakdown (all 330)
    depth2_summary = []
    for d2_key, acc in d2_acc.items():
        m = finalize_metrics(acc)
        depth2_summary.append(
            {
                "depth2_dir": d2_key,
                "top_dir": d2_parent[d2_key],
                **m,
                "pct_files": round(100.0 * m["files"] / total_files, 3),
                "pct_lines": round(100.0 * m["lines"] / total_lines, 3),
                "mean_lines_per_file": round(m["lines"] / m["files"], 2),
            }
        )
    depth2_summary.sort(key=lambda x: (-x["lines"], -x["files"], x["depth2_dir"]))

    # depth3_dir breakdown (top 30 by lines & top 30 by files)
    depth3_all = []
    for d3_key, acc in d3_acc.items():
        m = finalize_metrics(acc)
        depth3_all.append(
            {
                "depth3_dir": d3_key,
                "depth2_dir": d3_parent[d3_key],
                **m,
                "pct_files": round(100.0 * m["files"] / total_files, 3),
                "pct_lines": round(100.0 * m["lines"] / total_lines, 3),
                "mean_lines_per_file": round(m["lines"] / m["files"], 2),
            }
        )
    top30_d3_lines = sorted(depth3_all, key=lambda x: (-x["lines"], -x["files"], x["depth3_dir"]))[:30]
    top30_d3_files = sorted(depth3_all, key=lambda x: (-x["files"], -x["lines"], x["depth3_dir"]))[:30]

    # Direct folder (dir_stats level=0) vs pure leaf folders (no subdirectories)
    dir_path_all = []
    pure_leaf_all = []
    for d_key, acc in direct_acc.items():
        m = finalize_metrics(acc)
        rec = {
            "dir_path": d_key if d_key else "(root)",
            "has_subdirs": bool(children_map.get(d_key)),
            **m,
            "pct_files": round(100.0 * m["files"] / total_files, 3),
            "pct_lines": round(100.0 * m["lines"] / total_lines, 3),
            "mean_lines_per_file": round(m["lines"] / m["files"], 2),
        }
        dir_path_all.append(rec)
        if not children_map.get(d_key):
            pure_leaf_all.append(rec)

    top25_dir_paths_lines = sorted(dir_path_all, key=lambda x: (-x["lines"], -x["files"], x["dir_path"]))[:25]
    top25_dir_paths_files = sorted(dir_path_all, key=lambda x: (-x["files"], -x["lines"], x["dir_path"]))[:25]
    top25_pure_leaf_lines = sorted(pure_leaf_all, key=lambda x: (-x["lines"], -x["files"], x["dir_path"]))[:25]
    top25_pure_leaf_files = sorted(pure_leaf_all, key=lambda x: (-x["files"], -x["lines"], x["dir_path"]))[:25]

    top25_d2_lines = depth2_summary[:25]
    top25_d2_files = sorted(depth2_summary, key=lambda x: (-x["files"], -x["lines"], x["depth2_dir"]))[:25]
    top25_d3_lines = top30_d3_lines[:25]
    top25_d3_files = top30_d3_files[:25]

    # Top 25 individual files by lines and by bytes
    def format_file_row(r: tuple[Any, ...]) -> dict[str, Any]:
        tl = r[7] + r[8]
        ds = r[9] + r[10]
        od = r[11]
        return {
            "rel_path": r[0],
            "top_dir": r[2],
            "lines": r[5],
            "bytes": r[6],
            "theorems_lemmas": tl,
            "defs_structures": ds,
            "other_decls": od,
            "all_decls": tl + ds + od,
            "dist_from_main": r[12],
            "height_from_leaves": r[13],
        }

    top25_files_lines = [format_file_row(r) for r in sorted(rows, key=lambda r: (-r[5], -r[6], r[0]))[:25]]
    top25_files_bytes = [format_file_row(r) for r in sorted(rows, key=lambda r: (-r[6], -r[5], r[0]))[:25]]

    # Overall file distribution stats
    all_lines = [r[5] for r in rows]
    all_bytes = [r[6] for r in rows]
    all_tl = [r[7] + r[8] for r in rows]
    all_ds = [r[9] + r[10] for r in rows]
    all_decls = [r[7] + r[8] + r[9] + r[10] + r[11] for r in rows]

    exact_1_decl = sum(1 for d in all_decls if d == 1)
    exact_0_decl = sum(1 for d in all_decls if d == 0)
    le1_tl = sum(1 for x in all_tl if x <= 1)
    le2_decl = sum(1 for d in all_decls if d <= 2)
    stmt_total_files = sum(v["files"] for v in stmt_by_top.values())
    stmt_total_lines = sum(v["lines"] for v in stmt_by_top.values())

    conn.close()

    result = {
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_db": str(DB_PATH),
        "src_root": str(ROOT / "lean" / "src"),
        "build_seconds": round(time.time() - t0, 2),
        "meta": meta,
        "tree_stats": {
            "total_dir_nodes": len(all_dirs),
            "dirs_with_direct_files": len(direct_acc),
            "pure_leaf_dirs": len(pure_leaf_all),
            "intermediate_dirs_with_direct_files": len(direct_acc) - len(pure_leaf_all),
            "max_dir_depth": max(0 if not d else d.count("/") + 1 for d in all_dirs),
        },
        "summary": {
            "top_dirs": top_dirs_summary,
            "depth2_dirs": depth2_summary,
            "top30_depth3_dirs_by_lines": top30_d3_lines,
            "top30_depth3_dirs_by_files": top30_d3_files,
            "top25_depth2_dirs_by_lines": top25_d2_lines,
            "top25_depth2_dirs_by_files": top25_d2_files,
            "top25_depth3_dirs_by_lines": top25_d3_lines,
            "top25_depth3_dirs_by_files": top25_d3_files,
            "top25_dir_paths_direct_by_lines": top25_dir_paths_lines,
            "top25_dir_paths_direct_by_files": top25_dir_paths_files,
            "top25_pure_leaf_dirs_by_lines": top25_pure_leaf_lines,
            "top25_pure_leaf_dirs_by_files": top25_pure_leaf_files,
            "top25_files_by_lines": top25_files_lines,
            "top25_files_by_bytes": top25_files_bytes,
            "file_distributions": {
                "overall": {
                    "lines": compute_quantiles(all_lines),
                    "bytes": compute_quantiles(all_bytes),
                    "all_decls": compute_quantiles(all_decls),
                    "theorems_lemmas": compute_quantiles(all_tl),
                    "defs_structures": compute_quantiles(all_ds),
                },
                "by_top_dir": by_top_dist,
                "micro_module_markers": {
                    "files_with_0_decls": exact_0_decl,
                    "files_with_1_decl": exact_1_decl,
                    "pct_1_decl": round(100.0 * exact_1_decl / total_files, 2),
                    "files_with_le_2_decls": le2_decl,
                    "pct_le_2_decls": round(100.0 * le2_decl / total_files, 2),
                    "files_with_le_1_thm_lem": le1_tl,
                    "pct_le_1_thm_lem": round(100.0 * le1_tl / total_files, 2),
                    "statement_wrapper_files": stmt_total_files,
                    "pct_statement_wrappers": round(100.0 * stmt_total_files / total_files, 2),
                    "statement_wrapper_lines": stmt_total_lines,
                    "statement_wrappers_by_top_dir": stmt_by_top,
                },
                "decl_count_buckets": bucket_decls(rows),
                "line_count_buckets": bucket_lines(rows),
            },
        },
        "tree": tree,
    }
    return result


HTML_PATH = OUT_DIR / "treemap_sunburst.html"
DATA_START_MARKER = "/*DATA_START*/"
DATA_END_MARKER = "/*DATA_END*/"


def embed_into_html(data: dict[str, Any], html_path: Path = HTML_PATH) -> None:
    """Embed compact hierarchy payload into self-contained treemap_sunburst.html."""
    html = html_path.read_text(encoding="utf-8")
    i0 = html.find(DATA_START_MARKER)
    i1 = html.find(DATA_END_MARKER)
    if i0 == -1 or i1 == -1 or i1 < i0:
        raise RuntimeError(f"Could not find data markers in {html_path}")

    payload = {
        "generated_at": data["generated_at"],
        "src_root": data["src_root"],
        "meta": {
            "total_files": data["meta"]["total_files"],
            "total_lines": data["meta"]["total_lines"],
            "total_bytes": data["meta"]["total_bytes"],
            "reachable_files": data["meta"]["reachable_files"],
            "max_dist_from_main": data["meta"]["max_dist_from_main"],
            "max_height_from_leaves": data["meta"]["max_height_from_leaves"],
        },
        "tree_stats": data["tree_stats"],
        "summary": {
            "top_dirs": data["summary"]["top_dirs"],
        },
        "tree": data["tree"],
    }
    raw_js = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    new_html = (
        html[: i0 + len(DATA_START_MARKER)]
        + raw_js
        + html[i1:]
    )
    html_path.write_text(new_html, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON with indent=2")
    parser.add_argument("--embed-html", action="store_true", help="Embed hierarchy payload into treemap_sunburst.html")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = build_data()
    if args.pretty:
        OUT_JSON.write_text(json.dumps(data, indent=2), encoding="utf-8")
    else:
        OUT_JSON.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    size_mb = OUT_JSON.stat().st_size / (1024 * 1024)
    print(f"Wrote {OUT_JSON} ({size_mb:.2f} MB) in {data['build_seconds']}s")
    if args.embed_html:
        embed_into_html(data)
        html_mb = HTML_PATH.stat().st_size / (1024 * 1024)
        print(f"Embedded data into {HTML_PATH} ({html_mb:.2f} MB)")
    print(f"Tree nodes: {data['tree_stats']}")
    print("Top dirs:")
    for td in data["summary"]["top_dirs"]:
        print(
            f"  {td['top_dir']:20s} files={td['files']:6d} ({td['pct_files']:5.2f}%) "
            f"lines={td['lines']:8d} ({td['pct_lines']:5.2f}%) "
            f"tl={td['theorems_lemmas']:6d} ds={td['defs_structures']:6d} "
            f"1decl={td['pct_one_decl']:5.1f}%"
        )


if __name__ == "__main__":
    main()
