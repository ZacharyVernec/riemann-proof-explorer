#!/usr/bin/env python3
"""Extract cross-boundary directory interfaces, compression metrics, and self-contained browser."""

from __future__ import annotations

import argparse
import html
import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = ROOT / "analysis" / "data" / "graph.sqlite"
META_PATH = ROOT / "analysis" / "data" / "meta.json"
LEAN_SRC = ROOT / "lean" / "src"
OUT_DIR = SCRIPT_DIR
CURATED_PATH = SCRIPT_DIR / "curated_summaries.json"
JSON_OUT = OUT_DIR / "interfaces.json"
REPORT_OUT = OUT_DIR / "INTERFACES_REPORT.md"
HTML_OUT = SCRIPT_DIR / "interface_browser.html"


def compute_level_interfaces(
    conn: sqlite3.Connection,
    level: int,
    col_name: str,
    analyzed_set: set[str],
) -> tuple[list[dict], list[dict]]:
    """Compute cross-boundary interface statistics and ranked interface files for all dirs at level."""
    dir_rows = conn.execute(
        """
        SELECT dir_key, parent_key, files, reachable_files, lines, reachable_lines,
               bytes, theorems, lemmas, defs, structures,
               min_dist_from_main, avg_dist_from_main, max_height
        FROM dir_stats
        WHERE level = ? AND reachable_files > 0
        ORDER BY reachable_files DESC, dir_key ASC
        """,
        (level,),
    ).fetchall()

    # Cross-boundary incoming edges: dst inside D, src outside D (reachable subgraph only)
    in_edge_rows = conn.execute(
        f"""
        SELECT dst.{col_name} AS dst_dir,
               dst.id AS dst_id,
               dst.rel_path,
               dst.name,
               dst.top_dir,
               dst.depth2_dir,
               dst.lines,
               dst.n_theorems,
               dst.n_lemmas,
               dst.n_defs,
               dst.n_structures,
               dst.in_degree_main,
               dst.dist_from_main,
               dst.height_from_leaves,
               src.{col_name} AS src_dir,
               COUNT(*) AS edge_cnt,
               COUNT(DISTINCT src.id) AS src_file_cnt
        FROM edges e
        JOIN modules src ON e.src_id = src.id
        JOIN modules dst ON e.dst_id = dst.id
        WHERE src.reachable_from_main = 1 AND dst.reachable_from_main = 1
          AND src.{col_name} != dst.{col_name}
        GROUP BY dst.id, src.{col_name}
        """
    ).fetchall()

    # Aggregate unique external importers per directory & per file
    dir_ext_importers: dict[str, int] = dict(
        conn.execute(
            f"""
            SELECT dst.{col_name}, COUNT(DISTINCT src.id)
            FROM edges e
            JOIN modules src ON e.src_id = src.id
            JOIN modules dst ON e.dst_id = dst.id
            WHERE src.reachable_from_main = 1 AND dst.reachable_from_main = 1
              AND src.{col_name} != dst.{col_name}
            GROUP BY dst.{col_name}
            """
        ).fetchall()
    )

    # Dir-to-dir flow matrix (src_dir -> dst_dir)
    matrix_rows = conn.execute(
        f"""
        SELECT src.{col_name} AS src_dir,
               dst.{col_name} AS dst_dir,
               COUNT(*) AS edges,
               COUNT(DISTINCT src.id) AS src_files,
               COUNT(DISTINCT dst.id) AS dst_files
        FROM edges e
        JOIN modules src ON e.src_id = src.id
        JOIN modules dst ON e.dst_id = dst.id
        WHERE src.reachable_from_main = 1 AND dst.reachable_from_main = 1
          AND src.{col_name} != dst.{col_name}
        GROUP BY src.{col_name}, dst.{col_name}
        ORDER BY edges DESC, src_dir ASC, dst_dir ASC
        """
    ).fetchall()

    incoming_by_dir: dict[str, list[dict]] = defaultdict(list)
    outgoing_by_dir: dict[str, list[dict]] = defaultdict(list)
    matrix_list: list[dict] = []
    for src_d, dst_d, edges, src_files, dst_files in matrix_rows:
        rec = {
            "src_dir": src_d,
            "dst_dir": dst_d,
            "edges": edges,
            "src_files": src_files,
            "dst_files": dst_files,
        }
        matrix_list.append(rec)
        incoming_by_dir[dst_d].append(
            {"dir": src_d, "edges": edges, "src_files": src_files, "dst_files": dst_files}
        )
        outgoing_by_dir[src_d].append(
            {"dir": dst_d, "edges": edges, "src_files": src_files, "dst_files": dst_files}
        )

    # Group file records per directory
    files_by_dir: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in in_edge_rows:
        (
            dst_dir,
            dst_id,
            rel_path,
            mod_name,
            top_dir,
            depth2_dir,
            lines,
            n_thm,
            n_lem,
            n_def,
            n_str,
            in_deg,
            dist_main,
            height,
            src_dir,
            edge_cnt,
            _src_file_cnt,
        ) = row
        fmap = files_by_dir[dst_dir]
        frec = fmap.get(dst_id)
        if frec is None:
            frec = {
                "rel_path": rel_path,
                "module_name": mod_name,
                "top_dir": top_dir,
                "depth2_dir": depth2_dir,
                "lines": lines,
                "n_theorems": n_thm,
                "n_lemmas": n_lem,
                "n_defs": n_def,
                "n_structures": n_str,
                "tot_in_degree": in_deg,
                "ext_fan_in": 0,
                "dist_from_main": dist_main,
                "height_from_leaves": height,
                "analyzed": rel_path in analyzed_set,
                "ext_dirs": {},
            }
            fmap[dst_id] = frec
        frec["ext_fan_in"] += edge_cnt
        frec["ext_dirs"][src_dir] = edge_cnt

    dirs_out: list[dict] = []
    for (
        dkey,
        pkey,
        files,
        r_files,
        lines,
        r_lines,
        nbytes,
        thm,
        lem,
        df,
        st,
        min_d,
        avg_d,
        max_h,
    ) in dir_rows:
        iface_list = list(files_by_dir.get(dkey, {}).values())
        for item in iface_list:
            item["ext_dirs"] = dict(
                sorted(item["ext_dirs"].items(), key=lambda kv: (-kv[1], kv[0]))
            )
        iface_list.sort(
            key=lambda x: (-x["ext_fan_in"], -x["tot_in_degree"], x["rel_path"])
        )

        iface_count = len(iface_list)
        iface_lines = sum(x["lines"] for x in iface_list)
        ext_edges = sum(x["ext_fan_in"] for x in iface_list)
        eff_files = r_files or files
        eff_lines = r_lines or lines
        comp_ratio = round(iface_count / eff_files, 6) if eff_files > 0 else 0.0
        line_comp_ratio = round(iface_lines / eff_lines, 6) if eff_lines > 0 else 0.0
        comp_factor = round(eff_files / iface_count, 2) if iface_count > 0 else None

        inc = sorted(
            incoming_by_dir.get(dkey, []), key=lambda x: (-x["edges"], x["dir"])
        )
        outg = sorted(
            outgoing_by_dir.get(dkey, []), key=lambda x: (-x["edges"], x["dir"])
        )
        ext_out_edges = sum(x["edges"] for x in outg)

        dirs_out.append(
            {
                "dir_key": dkey,
                "level": level,
                "parent_key": pkey,
                "total_files": files,
                "reachable_files": r_files,
                "total_lines": lines,
                "total_bytes": nbytes,
                "theorems": thm,
                "lemmas": lem,
                "defs": df,
                "structures": st,
                "min_dist_from_main": min_d,
                "avg_dist_from_main": round(avg_d, 2) if avg_d is not None else None,
                "max_height": max_h,
                "interface_files_count": iface_count,
                "interface_lines": iface_lines,
                "compression_ratio": comp_ratio,
                "line_compression_ratio": line_comp_ratio,
                "compression_factor": comp_factor,
                "total_ext_imports": ext_edges,
                "unique_ext_importers": dir_ext_importers.get(dkey, 0),
                "ext_dir_importers_count": len(inc),
                "importing_dirs": inc,
                "outgoing_ext_imports": ext_out_edges,
                "imported_external_dirs": outg,
                "interface_files": iface_list,
            }
        )

    return dirs_out, matrix_list


def resolve_curated_entries(
    conn: sqlite3.Connection, curated: dict[str, dict]
) -> tuple[dict[str, dict], list[str]]:
    """Resolve curated interface paths against reachable modules and declarations."""
    reach_mods = {
        r[0]: r
        for r in conn.execute(
            """
            SELECT rel_path, id, name, top_dir, depth2_dir, lines, bytes,
                   n_theorems, n_lemmas, n_defs, n_structures, n_other_decls,
                   dist_from_main, height_from_leaves, in_degree_main, out_degree
            FROM modules WHERE reachable_from_main = 1
            """
        ).fetchall()
    }
    sym_full: dict[str, list[tuple[str, str, str, int, int]]] = defaultdict(list)
    sym_short: dict[str, list[tuple[str, str, str, int, int]]] = defaultdict(list)
    for full, kind, rel, ln, ind in conn.execute(
        """
        SELECT d.name, d.kind, m.rel_path, d.line_no, m.in_degree_main
        FROM declarations d
        JOIN modules m ON m.id = d.module_id
        WHERE m.reachable_from_main = 1
        ORDER BY m.in_degree_main DESC, d.line_no ASC
        """
    ):
        sym_full[full].append((full, kind, rel, ln, ind))
        sym_short[full.rsplit(".", 1)[-1]].append((full, kind, rel, ln, ind))

    resolved: dict[str, dict] = {}
    skipped: list[str] = []

    def copy_entry(info: dict, orig_rel: str, actual_rel: str) -> dict:
        out = dict(info)
        out["key_exports"] = [dict(ke) for ke in info.get("key_exports", [])]
        if actual_rel != orig_rel:
            out["role"] = f"{info['role']} (relocated from {Path(orig_rel).name})"
        return out

    # First pass: keep exact path matches so canonical files own their slots before clumped merges
    unmatched: list[tuple[str, dict]] = []
    for rel_path, info in curated.items():
        if rel_path in reach_mods:
            resolved[rel_path] = copy_entry(info, rel_path, rel_path)
        else:
            unmatched.append((rel_path, info))

    # Second pass: relocate moved/clumped files by exported symbol lookup
    for orig_rel, info in unmatched:
        target_rel: str | None = None
        for ke in info.get("key_exports", []):
            cands = sym_full.get(ke["name"], []) or sym_short.get(ke["name"].rsplit(".", 1)[-1], [])
            if cands:
                # Prefer non-Definitions module with highest in_degree_main
                best = min(cands, key=lambda c: (1 if "/Definitions/" in c[2] else 0, -c[4], c[3]))
                target_rel = best[2]
                break
        if target_rel is None:
            skipped.append(orig_rel)
            continue
        if target_rel in resolved:
            # Merge unique key_exports onto existing clumped module
            existing = resolved[target_rel]
            have_names = {k["name"] for k in existing["key_exports"]}
            for ke in info.get("key_exports", []):
                if ke["name"] not in have_names:
                    existing["key_exports"].append(dict(ke))
                    have_names.add(ke["name"])
            existing["plain_english_summary"] = (
                f"{existing['plain_english_summary']} [Also incorporates relocated exports from {Path(orig_rel).name}: {info['role']}.]"
            )
        else:
            resolved[target_rel] = copy_entry(info, orig_rel, target_rel)

    return resolved, skipped


def extract_analyzed_interfaces(
    conn: sqlite3.Connection,
    curated: dict[str, dict],
    top_dirs_map: dict[str, dict],
    d2_dirs_map: dict[str, dict],
    github_blob_base: str = "",
) -> list[dict]:
    """Build verified declaration + plain-English records for all resolved interface files."""
    # Pre-index per-file fan-in from top_dirs_map and d2_dirs_map
    top_file_lookup: dict[str, dict] = {}
    for d in top_dirs_map.values():
        for f in d["interface_files"]:
            top_file_lookup[f["rel_path"]] = f

    d2_file_lookup: dict[str, dict] = {}
    for d in d2_dirs_map.values():
        for f in d["interface_files"]:
            d2_file_lookup[f["rel_path"]] = f

    mod_records: list[tuple[str, dict, tuple]] = []
    for rel_path, info in curated.items():
        mod = conn.execute(
            """
            SELECT id, name, top_dir, depth2_dir, lines, bytes,
                   n_theorems, n_lemmas, n_defs, n_structures, n_other_decls,
                   dist_from_main, height_from_leaves, in_degree_main, out_degree
            FROM modules
            WHERE rel_path = ? AND reachable_from_main = 1
            """,
            (rel_path,),
        ).fetchone()
        if mod is None:
            raise ValueError(f"Resolved curated file missing from reachable modules: {rel_path}")
        mod_records.append((rel_path, info, mod))

    curated_ids = [rec[2][0] for rec in mod_records]
    if not curated_ids:
        return []
    id_to_rel = {rec[2][0]: rec[0] for rec in mod_records}
    id_ph = ",".join("?" * len(curated_ids))

    # Outgoing cross-boundary external theory imports for curated interfaces
    out_top_map: dict[str, dict[str, int]] = defaultdict(dict)
    for src_rel, dst_top, cnt in conn.execute(
        f"""
        SELECT src.rel_path, dst.top_dir, COUNT(*)
        FROM edges e
        JOIN modules src ON e.src_id = src.id
        JOIN modules dst ON e.dst_id = dst.id
        WHERE src.id IN ({id_ph}) AND src.reachable_from_main = 1 AND dst.reachable_from_main = 1
          AND src.top_dir != dst.top_dir
        GROUP BY src.id, dst.top_dir
        ORDER BY COUNT(*) DESC, dst.top_dir ASC
        """,
        curated_ids,
    ).fetchall():
        out_top_map[src_rel][dst_top] = cnt

    out_d2_map: dict[str, dict[str, int]] = defaultdict(dict)
    for src_rel, dst_d2, cnt in conn.execute(
        f"""
        SELECT src.rel_path, dst.depth2_dir, COUNT(*)
        FROM edges e
        JOIN modules src ON e.src_id = src.id
        JOIN modules dst ON e.dst_id = dst.id
        WHERE src.id IN ({id_ph}) AND src.reachable_from_main = 1 AND dst.reachable_from_main = 1
          AND src.depth2_dir != dst.depth2_dir
        GROUP BY src.id, dst.depth2_dir
        ORDER BY COUNT(*) DESC, dst.depth2_dir ASC
        """,
        curated_ids,
    ).fetchall():
        out_d2_map[src_rel][dst_d2] = cnt

    # Direct 1-hop edges among the curated interfaces
    direct_deps_map: dict[str, list[str]] = defaultdict(list)
    direct_dependents_map: dict[str, list[str]] = defaultdict(list)
    for src_id, dst_id in conn.execute(
        f"SELECT src_id, dst_id FROM edges WHERE src_id IN ({id_ph}) AND dst_id IN ({id_ph})",
        curated_ids + curated_ids,
    ).fetchall():
        s_rel = id_to_rel[src_id]
        d_rel = id_to_rel[dst_id]
        direct_deps_map[s_rel].append(d_rel)
        direct_dependents_map[d_rel].append(s_rel)

    # Exact transitive reduction DAG among curated interfaces via topological bitmask propagation
    mod_order = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM modules WHERE reachable_from_main = 1 ORDER BY height_from_leaves ASC"
        ).fetchall()
    ]
    reach_id_set = set(mod_order)
    adj: dict[int, list[int]] = defaultdict(list)
    for src_id, dst_id in conn.execute("SELECT src_id, dst_id FROM edges").fetchall():
        if src_id in reach_id_set and dst_id in reach_id_set:
            adj[src_id].append(dst_id)

    idx_mask = {mid: (1 << idx) for idx, mid in enumerate(curated_ids)}
    max_mod_id = max(mod_order) if mod_order else 0
    reach = [0] * (max_mod_id + 1)
    for u in mod_order:
        m = 0
        for v in adj.get(u, ()):
            m |= reach[v]
            vm = idx_mask.get(v)
            if vm:
                m |= vm
        reach[u] = m

    tr_deps_map: dict[str, list[str]] = defaultdict(list)
    tr_dependents_map: dict[str, list[str]] = defaultdict(list)
    n_curated = len(curated_ids)
    for i, mid_i in enumerate(curated_ids):
        r_i = reach[mid_i]
        indirect = 0
        for k in range(n_curated):
            if (r_i >> k) & 1:
                indirect |= reach[curated_ids[k]]
        direct_tr = r_i & ~indirect
        rel_i = id_to_rel[mid_i]
        for j in range(n_curated):
            if (direct_tr >> j) & 1:
                rel_j = id_to_rel[curated_ids[j]]
                tr_deps_map[rel_i].append(rel_j)
                tr_dependents_map[rel_j].append(rel_i)

    blob_prefix = github_blob_base.rstrip("/")
    results: list[dict] = []
    for rel_path, info, mod in mod_records:
        (
            mod_id,
            mod_name,
            top_dir,
            d2_dir,
            lines,
            nbytes,
            n_thm,
            n_lem,
            n_def,
            n_str,
            n_oth,
            dist_main,
            height,
            in_deg,
            out_deg,
        ) = mod

        decls = conn.execute(
            """
            SELECT kind, name, line_no
            FROM declarations
            WHERE module_id = ?
            ORDER BY line_no ASC
            """,
            (mod_id,),
        ).fetchall()
        decl_list = [{"kind": k, "name": n, "line_no": ln} for k, n, ln in decls]
        by_name = {}
        by_short = {}
        for k, n, ln in decls:
            by_name.setdefault(n, (k, n, ln))
            by_short.setdefault(n.rsplit(".", 1)[-1], (k, n, ln))

        resolved_exports: list[dict] = []
        for ke in info.get("key_exports", []):
            ke_copy = dict(ke)
            hit = by_name.get(ke["name"]) or by_short.get(ke["name"].rsplit(".", 1)[-1])
            if hit:
                ke_copy["kind"] = hit[0]
                ke_copy["name"] = hit[1]
                ke_copy["line_no"] = hit[2]
                resolved_exports.append(ke_copy)

        t_info = top_file_lookup.get(rel_path)
        d2_info = d2_file_lookup.get(rel_path)
        f_url = f"{blob_prefix}/{rel_path}" if blob_prefix else rel_path

        results.append(
            {
                "rel_path": rel_path,
                "module_name": mod_name,
                "file_url": f_url,
                "top_dir": top_dir,
                "depth2_dir": d2_dir,
                "role": info["role"],
                "lines": lines,
                "bytes": nbytes,
                "n_theorems": n_thm,
                "n_lemmas": n_lem,
                "n_defs": n_def,
                "n_structures": n_str,
                "n_other_decls": n_oth,
                "dist_from_main": dist_main,
                "height_from_leaves": height,
                "tot_in_degree": in_deg,
                "out_degree": out_deg,
                "top_ext_fan_in": t_info["ext_fan_in"] if t_info else 0,
                "importing_top_dirs": t_info["ext_dirs"] if t_info else {},
                "imported_top_dirs": out_top_map.get(rel_path, {}),
                "d2_ext_fan_in": d2_info["ext_fan_in"] if d2_info else 0,
                "importing_d2_dirs": d2_info["ext_dirs"] if d2_info else {},
                "imported_d2_dirs": out_d2_map.get(rel_path, {}),
                "direct_analyzed_deps": sorted(direct_deps_map.get(rel_path, [])),
                "direct_analyzed_dependents": sorted(direct_dependents_map.get(rel_path, [])),
                "tr_analyzed_deps": sorted(tr_deps_map.get(rel_path, [])),
                "tr_analyzed_dependents": sorted(tr_dependents_map.get(rel_path, [])),
                "plain_english_summary": info["plain_english_summary"],
                "key_exports": resolved_exports,
                "all_declarations": decl_list,
            }
        )

    results.sort(
        key=lambda x: (-x["top_ext_fan_in"], -x["d2_ext_fan_in"], -x["tot_in_degree"], x["rel_path"])
    )
    return results


def build_browser_payload(full_data: dict, max_files_per_d2: int = 120, max_files_per_top: int = 250) -> dict:
    """Create compact embedded JSON payload for interface_browser.html."""
    analyzed_paths = {x["rel_path"] for x in full_data["analyzed_interfaces"]}

    def trim_dir(d: dict, limit: int) -> dict:
        ifaces = d["interface_files"]
        kept = ifaces[:limit]
        kept_paths = {f["rel_path"] for f in kept}
        for f in ifaces[limit:]:
            if f["rel_path"] in analyzed_paths and f["rel_path"] not in kept_paths:
                kept.append(f)
        compact_ifaces = [
            {
                "p": f["rel_path"],
                "d2": f["depth2_dir"],
                "e": f["ext_fan_in"],
                "t": f["tot_in_degree"],
                "l": f["lines"],
                "th": f["n_theorems"],
                "le": f["n_lemmas"],
                "df": f["n_defs"],
                "st": f["n_structures"],
                "dm": f["dist_from_main"],
                "ht": f["height_from_leaves"],
                "a": 1 if f["analyzed"] else 0,
                "ed": f["ext_dirs"],
            }
            for f in kept
        ]
        return {
            "dir_key": d["dir_key"],
            "level": d["level"],
            "parent_key": d["parent_key"],
            "total_files": d["total_files"],
            "total_lines": d["total_lines"],
            "theorems": d["theorems"],
            "lemmas": d["lemmas"],
            "defs": d["defs"],
            "structures": d["structures"],
            "min_dist_from_main": d["min_dist_from_main"],
            "max_height": d["max_height"],
            "interface_files_count": d["interface_files_count"],
            "interface_lines": d["interface_lines"],
            "compression_ratio": d["compression_ratio"],
            "line_compression_ratio": d["line_compression_ratio"],
            "compression_factor": d["compression_factor"],
            "total_ext_imports": d["total_ext_imports"],
            "unique_ext_importers": d["unique_ext_importers"],
            "importing_dirs": d["importing_dirs"],
            "imported_external_dirs": d["imported_external_dirs"],
            "shown_files_count": len(compact_ifaces),
            "interface_files": compact_ifaces,
        }

    return {
        "meta": full_data["meta"],
        "top_dir_matrix": full_data["top_dir_matrix"],
        "top_dirs": [trim_dir(d, max_files_per_top) for d in full_data["top_dirs"]],
        "depth2_dirs": [trim_dir(d, max_files_per_d2) for d in full_data["depth2_dirs"]],
        "analyzed_interfaces": full_data["analyzed_interfaces"],
    }


def render_report(
    full_export: dict,
    version_label: str = "",
    rel_src_label: str = "src/",
    skipped_curated: list[str] | None = None,
) -> str:
    """Render structured Markdown report focusing on mathematical interfaces and plain-English API summaries."""
    analyzed = full_export["analyzed_interfaces"]
    meta = full_export["meta"]
    active_tops = {d["dir_key"] for d in full_export["top_dirs"]}

    lines: list[str] = []
    a = lines.append

    ver_note = f" (`{version_label}`)" if version_label else ""
    a(f"# Cross-Boundary Mathematical Interfaces & Contracts{ver_note}")
    a("")
    a(
        f"This report translates the cross-boundary public mathematical interfaces of the proof across `{rel_src_label}` (**{meta['reachable_files']:,} reachable modules**, **{meta['top_dir_count']} top-level theories**, **{meta['depth2_dir_count']} depth-2 sub-theories**), focusing on the mathematical specifications, theorem contracts, and bridges that link the major sub-theories (interactive browser in [interface_browser.html](interface_browser.html))."
    )
    a("")
    a("## 1. Architectural Overview of Mathematical Boundaries")
    a("")
    sup_note = (
        " Its final outputs funnel into `Supplements/Kernels/` (`MainTheoremsAll.lean`) and from there into `Main.lean`,"
        if "Supplements" in active_tops
        else " Its final outputs (`ClaimStrip.lean`, `MainConclusion.lean`) funnel directly into `Main.lean`,"
    )
    a(
        f"- **`Development` as the Central Synthesis Engine:** `Development` develops the core proofs across abelian varieties, automorphic arithmetic, automorphic spectrum, the Weil bound, étale cohomology, discrete groups, and resolution of singularities.{sup_note} while also supplying local-global compatibility, representation-algebra, and literature-bundle contracts (`SumIoPr`, `Brauer`, `Langlands`, `LocIsotypic`, `RealTransport`) to `CompanionTheory` and `PositivityTheory`."
    )
    a(
        "- **`Formalism` & `ReciprocityTheory` as Specification Contract Hubs:** `Formalism` and `ReciprocityTheory` export the foundational **mathematical specification packages (`Prop` predicates and `structure` contracts)**—such as `UniformisationConclusion`, `PELUnif`, `UnifUniqSt`, `HeckeKer`, `Laws`, `Laws2`, `LocCoh`, `D7`, and `LocalTateDualityK`—that decouple the upper analytic, Galois, and Arakelov engines from the underlying algebraic-geometric and harmonic-analytic constructions."
    )
    a(
        "- **`GroundTheory`, `CompanionTheory` & `PositivityTheory` as Specialized Pillars:** `GroundTheory` supplies Arakelov Hermitian lattices (`KernelsLattice`), Whittaker multiplicity one (`Injective`), Poitou-Tate nine-term duality (`PoitouTateNineTermGs`), and idelic norm product formulas (`IdeleNorms`). `CompanionTheory` supplies adelic Siegel-Weil Euler-product measures (`IsEulerProd`), Harish-Chandra discrete series Capelli characters (`DiscreteSeriesInfinitesimalCharacter`), and discrete-series characters. `PositivityTheory` supplies $\\mathrm{GL}(3)\\times\\mathrm{GL}(2)$ and $\\mathrm{GL}(2)\\times\\mathrm{GL}(2)$ Rankin-Selberg zeta integrals and weight-one Hilbert Eisenstein series."
    )
    a("")
    a(f"## 2. Sub-Theory Public APIs in Plain Mathematical English ({len(analyzed)} Verified Interfaces)")
    a("")
    a("Every interface below was resolved directly against the active reachable declaration index (`graph.sqlite`) for this codebase version.")
    a("")

    order_top = [
        "(root)",
        "Supplements",
        "Development",
        "Formalism",
        "ReciprocityTheory",
        "GroundTheory",
        "CompanionTheory",
        "PositivityTheory",
        "Lemmata",
        "BuildAid",
    ]
    by_top: dict[str, list[dict]] = defaultdict(list)
    for item in analyzed:
        by_top[item["top_dir"]].append(item)
    ordered_active = [td for td in order_top if by_top.get(td)] + sorted(set(by_top.keys()) - set(order_top))

    for sec_idx, td in enumerate(ordered_active, 1):
        items = by_top[td]
        a(f"### 2.{sec_idx} `{td}`")
        a("")
        if td in ("(root)", "Supplements"):
            items_sorted = sorted(items, key=lambda x: (x["dist_from_main"], x["rel_path"]))
        else:
            items_sorted = sorted(items, key=lambda x: (-x["top_ext_fan_in"], -x["d2_ext_fan_in"], -x["tot_in_degree"], x["rel_path"]))

        for it in items_sorted:
            top_imps = ", ".join(f"`{k}`" for k in list(it["importing_top_dirs"].keys())[:5]) or "None (apex)"
            d2_imps = ", ".join(f"`{k}`" for k in list(it["importing_d2_dirs"].keys())[:4]) or "None"
            a(f"#### [`{it['rel_path']}`]({it['file_url']})")
            a(f"- **Role:** {it['role']} | **Sub-Theory:** `{it['depth2_dir']}` | **Used by:** Top-level: {top_imps} · Sub-theories: {d2_imps}")
            a(f"- **Plain-English Mathematical Summary:** {it['plain_english_summary']}")
            if it["key_exports"]:
                a("- **Key Exported Declarations:**")
                for ke in it["key_exports"]:
                    link = f"{it['file_url']}#L{ke['line_no']}"
                    a(f"  - `{ke['kind']}` [`{ke['name']}`]({link}) (L{ke['line_no']}): {ke['summary']}")
            else:
                a("- **Key Exported Declarations:** Pure import barrel / namespace directive.")
            a("")

    if skipped_curated:
        a("---")
        a("")
        a(f"## 3. Baseline Interface Files Not Present in `{rel_src_label}` ({len(skipped_curated)})")
        a("")
        for sp in skipped_curated:
            a(f"- `{sp}`")
        a("")

    return "\n".join(lines) + "\n"


def render_html(payload: dict) -> str:
    """Render graphical HTML/CSS/SVG/JS interface browser shell loading interface_browser_data.js."""
    return r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Riemann Proof Lean Codebase — Cross-Boundary Interface Browser</title>
<style>
  :root {
    --bg: #ffffff;
    --panel: #fafafa;
    --panel2: #f2f2f2;
    --border: #cccccc;
    --text: #111111;
    --muted: #555555;
    --accent: #0056b3;
    --warn: #b45309;
    --up: #b45309;
    --up-bg: #fef3c7;
    --down: #0284c7;
    --down-bg: #e0f2fe;
    --badge-bg: #eeeeee;
    --code-bg: #ffffff;
    --row-hover: #f5f5f5;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }
  header {
    background: #ffffff;
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
  }
  header h1 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
  }
  header .sub {
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 2px;
  }
  .top-stats {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .pill {
    background: var(--badge-bg);
    border: 1px solid var(--border);
    padding: 3px 8px;
    font-size: 0.8rem;
    color: var(--text);
  }
  .pill b { color: var(--text); }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 20px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    align-items: center;
  }
  .tabs {
    display: inline-flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  .tab {
    border: 1px solid var(--border);
    background: #ffffff;
    color: var(--text);
    padding: 5px 10px;
    cursor: pointer;
    font-size: 0.84rem;
  }
  .tab:hover { background: #eeeeee; }
  .tab.active {
    background: #222222;
    color: #ffffff;
    border-color: #222222;
  }
  input[type="search"], select {
    background: var(--code-bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 5px 10px;
    font-size: 0.85rem;
  }
  #globalSearch {
    flex: 1 1 280px;
    min-width: 220px;
  }
  .layout {
    display: grid;
    grid-template-columns: 320px 1fr;
    min-height: calc(100vh - 140px);
  }
  @media (max-width: 980px) {
    .layout { grid-template-columns: 1fr; }
    .sidebar { max-height: 280px !important; border-right: none; border-bottom: 1px solid var(--border); }
    .main { max-height: none !important; }
  }
  .sidebar {
    border-right: 1px solid var(--border);
    background: var(--panel);
    display: flex;
    flex-direction: column;
    max-height: calc(100vh - 140px);
  }
  .sidebar-head {
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
  }
  .dir-list {
    overflow-y: auto;
    flex: 1;
  }
  .dir-item {
    padding: 8px 12px;
    border-bottom: 1px solid #e5e5e5;
    border-left: 3px solid transparent;
    cursor: pointer;
  }
  .dir-item:hover { background: #eeeeee; }
  .dir-item.active {
    background: #e6f0fa;
  }
  .dir-row-top {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .theory-dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
    display: inline-block;
  }
  .dir-name {
    font-weight: 600;
    font-size: 0.85rem;
    word-break: break-word;
    flex: 1;
  }
  .dir-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 4px;
    font-size: 0.74rem;
    color: var(--muted);
  }
  .conn-bar {
    height: 3px;
    background: #e5e7eb;
    margin-top: 5px;
    overflow: hidden;
  }
  .conn-fill {
    height: 100%;
    transition: width 0.15s ease;
  }
  .main {
    padding: 16px 20px;
    overflow-y: auto;
    max-height: calc(100vh - 140px);
  }
  .card {
    background: #ffffff;
    border: 1px solid var(--border);
    padding: 14px;
    margin-bottom: 14px;
  }
  .card h2, .card h3 {
    margin: 0 0 8px 0;
    font-size: 1rem;
  }
  .flow-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .chip {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 3px 8px;
    font-size: 0.78rem;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .chip.clickable { cursor: pointer; }
  .chip.clickable:hover { background: #eeeeee; border-color: #999999; }
  .chip.active-filter { background: #e0f2fe; border-color: #0284c7; color: #075985; font-weight: 600; }
  .chip.up { background: var(--up-bg); border-color: var(--up); color: #78350f; }
  .chip.down { background: var(--down-bg); border-color: var(--down); color: #075985; }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.84rem;
  }
  th, td {
    padding: 6px 8px;
    text-align: left;
    border: 1px solid #dddddd;
    vertical-align: top;
  }
  th {
    color: var(--text);
    font-weight: 600;
    font-size: 0.78rem;
    background: var(--panel2);
    position: sticky;
    top: 0;
    z-index: 2;
  }
  tr.clickable:hover { background: var(--row-hover); cursor: pointer; }
  .mono {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.81rem;
    word-break: break-word;
  }
  .badge {
    display: inline-block;
    padding: 1px 6px;
    font-size: 0.72rem;
    font-weight: 600;
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: var(--text);
    white-space: nowrap;
  }
  .badge.warn { color: var(--warn); }
  .badge.kind { color: var(--accent); }
  a.filelink {
    color: var(--accent);
    text-decoration: none;
  }
  a.filelink:hover { text-decoration: underline; }
  .summary-box {
    background: #fafafa;
    border-left: 3px solid #888888;
    padding: 10px 12px;
    margin: 8px 0 12px 0;
    font-size: 0.92rem;
  }
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 8px;
  }
  .btn {
    background: #ffffff;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 4px 10px;
    cursor: pointer;
    font-size: 0.8rem;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .btn:hover { background: #eeeeee; }
  .btn.active { background: #222222; color: #ffffff; border-color: #222222; }
  .btn.sm { padding: 2px 7px; font-size: 0.75rem; }
  .muted { color: var(--muted); }
  .table-wrap {
    max-height: 460px;
    overflow: auto;
    border: 1px solid var(--border);
  }

  /* Graphical Explorer Panels */
  .graph-panel {
    background: #ffffff;
    border: 1px solid var(--border);
    margin-bottom: 14px;
  }
  .graph-head {
    padding: 9px 12px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
  }
  .graph-title-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }
  .graph-title-group h2 {
    margin: 0;
    font-size: 0.96rem;
    font-weight: 700;
  }
  .graph-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }
  .seg-group {
    display: inline-flex;
    gap: 2px;
  }
  .legend-strip {
    padding: 6px 12px;
    background: #ffffff;
    border-bottom: 1px solid #e5e5e5;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    font-size: 0.76rem;
    color: var(--muted);
  }
  .legend-items {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }
  .swatch {
    width: 11px;
    height: 11px;
    border: 1px solid #666666;
    display: inline-block;
  }
  .swatch.sel { background: #eff6ff; border: 2px solid #111111; }
  .swatch.up { background: var(--up-bg); border-color: var(--up); }
  .swatch.down { background: var(--down-bg); border-color: var(--down); }
  .dag-scroll {
    position: relative;
    width: 100%;
    height: 520px;
    overflow: auto;
    background: #ffffff;
    cursor: grab;
  }
  .dag-scroll.grabbing { cursor: grabbing; }
  .dag-stage {
    transform-origin: 0 0;
    display: inline-block;
  }
  .svg-box {
    width: 100%;
    overflow-x: auto;
    background: #ffffff;
    padding: 8px;
  }
  .svg-box svg, .dag-stage svg {
    display: block;
    user-select: none;
  }
  .sel-banner {
    padding: 8px 12px;
    background: #f8fafc;
    border-top: 1px solid #e5e5e5;
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
  }
  .matrix-grid-wrap {
    display: grid;
    grid-template-columns: 1.05fr 1fr;
    gap: 14px;
    padding: 12px;
  }
  @media (max-width: 1180px) {
    .matrix-grid-wrap { grid-template-columns: 1fr; }
  }
  .matrix-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.72rem;
    table-layout: fixed;
  }
  .matrix-table th, .matrix-table td {
    border: 1px solid #e2e8f0;
    padding: 4px 3px;
    text-align: center;
    vertical-align: middle;
  }
  .matrix-table th.row-hd {
    text-align: left;
    padding: 4px 6px;
    width: 122px;
    background: #fafafa;
    font-weight: 600;
    position: static;
  }
  .matrix-table th.col-hd {
    writing-mode: vertical-rl;
    transform: rotate(180deg);
    height: 104px;
    background: #fafafa;
    font-weight: 600;
    position: static;
    padding: 6px 3px;
  }
  .matrix-cell {
    cursor: pointer;
    font-weight: 600;
    font-size: 0.7rem;
  }
  .matrix-cell:hover {
    outline: 2px solid #111111;
    outline-offset: -2px;
  }
  .matrix-diag {
    background: #f1f5f9;
    color: #94a3b8;
  }
  .matrix-zero {
    background: #ffffff;
    color: #cbd5e1;
  }

  /* Declaration composition bar */
  .decl-bar-wrap {
    margin: 8px 0 10px 0;
  }
  .decl-stacked-bar {
    height: 11px;
    width: 100%;
    display: flex;
    border: 1px solid #cbd5e1;
    overflow: hidden;
    background: #f8fafc;
    margin-bottom: 8px;
  }
  .decl-seg {
    height: 100%;
    cursor: pointer;
    transition: opacity 0.12s;
  }
  .decl-seg:hover { opacity: 0.8; }

  /* Filter banner in theory mode */
  .filter-banner {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 7px 10px;
    margin-bottom: 10px;
    background: #eff6ff;
    border: 1px solid #93c5fd;
    font-size: 0.82rem;
  }

  /* Reach bar inside module table */
  .reach-bar {
    height: 4px;
    background: #e2e8f0;
    margin-top: 4px;
    max-width: 220px;
  }
  .reach-fill {
    height: 100%;
    background: #0284c7;
  }

  /* Floating SVG Tooltip */
  .svg-tooltip {
    position: fixed;
    z-index: 999;
    pointer-events: none;
    background: #ffffff;
    border: 1px solid #475569;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    padding: 7px 10px;
    font-size: 0.77rem;
    line-height: 1.4;
    color: var(--text);
    max-width: 340px;
    display: none;
  }
  .svg-tooltip .tt-title { font-weight: 700; margin-bottom: 2px; word-break: break-word; }
  .svg-tooltip .tt-sub { color: var(--muted); font-size: 0.72rem; margin-bottom: 3px; word-break: break-word; }
  .svg-tooltip .tt-body { font-size: 0.74rem; }

  .svg-node { cursor: pointer; }
  .svg-node:hover .svg-node-box { stroke: #111111 !important; stroke-width: 2px !important; }
</style>
</head>
<body>
<nav style="padding:8px 20px;border-bottom:1px solid #ccc;font-size:13px;background:#fafafa;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
  <div>
    <a href="../index.html" style="color:#0056b3;text-decoration:none;">&larr; Back to Analysis Portal</a> &middot;
    <a href="INTERFACES_REPORT.html" style="color:#0056b3;text-decoration:none;">INTERFACES_REPORT.html</a> &middot;
    <a href="INTERFACES_REPORT.md" data-version-href="interfaces/INTERFACES_REPORT.md" style="color:#0056b3;text-decoration:none;">INTERFACES_REPORT.md</a>
  </div>
  <span data-version-picker></span>
</nav>
<script src="../version_picker.js"></script>
<header>
  <div>
    <h1>Riemann Proof — Cross-Boundary Mathematical Interface Browser</h1>
    <div class="sub" id="ifaceSubtitle">Interactive graphical explorer of cross-theory contract architecture, boundary flows, and plain-English Lean 4 APIs</div>
  </div>
  <div class="top-stats" id="topStats"></div>
</header>

<div class="toolbar">
  <div class="tabs">
    <button class="tab active" data-mode="analyzed">Analyzed APIs (<span id="cntAn">0</span>)</button>
    <button class="tab" data-mode="top">Top-Level Theories (<span id="cntTop">0</span>)</button>
    <button class="tab" data-mode="d2">Depth-2 Sub-Theories (<span id="cntD2">0</span>)</button>
    <button class="tab" data-mode="search">Global Search</button>
  </div>
  <input id="globalSearch" type="search" placeholder="Filter theories, interface paths, Lean declarations, or math terms...">
  <select id="sortSelect" title="Sort directories">
    <option value="ext">Sort: Cross-Theory Connections</option>
    <option value="name">Sort: Name A-Z</option>
  </select>
</div>

<div class="layout">
  <aside class="sidebar">
    <div class="sidebar-head">
      <span id="sidebarLabel">Directories</span>
      <span id="sidebarCount">0</span>
    </div>
    <div class="dir-list" id="sidebarList"></div>
  </aside>
  <main class="main" id="mainPane"></main>
</div>
<div class="svg-tooltip" id="svgTooltip"></div>

<script>
(function () {
  "use strict";

  let DATA = null;
  let ANALYZED_MAP = new Map();
  let TOP_DIR_MAP = new Map();
  let D2_DIR_MAP = new Map();
  let THEORY_ORDER = [];

  const CANONICAL_THEORY_ORDER = [
    "(root)", "Supplements",
    "Development", "CompanionTheory", "PositivityTheory",
    "Formalism", "ReciprocityTheory",
    "GroundTheory", "Lemmata", "BuildAid"
  ];
  const THEORY_META = {
    "(root)":            { color: "#334155", bg: "#f1f5f9", border: "#94a3b8", tier: 0, label: "(root)" },
    "Supplements":       { color: "#3730a3", bg: "#eef2ff", border: "#818cf8", tier: 0, label: "Supplements" },
    "Development":       { color: "#1d4ed8", bg: "#eff6ff", border: "#60a5fa", tier: 1, label: "Development" },
    "CompanionTheory":   { color: "#047857", bg: "#ecfdf5", border: "#34d399", tier: 1, label: "CompanionTheory" },
    "PositivityTheory":  { color: "#86198f", bg: "#fdf4ff", border: "#e879f9", tier: 1, label: "PositivityTheory" },
    "Formalism":         { color: "#c2410c", bg: "#fff7ed", border: "#fb923c", tier: 2, label: "Formalism" },
    "ReciprocityTheory": { color: "#0f766e", bg: "#f0fdfa", border: "#2dd4bf", tier: 2, label: "ReciprocityTheory" },
    "GroundTheory":      { color: "#a16207", bg: "#fefce8", border: "#facc15", tier: 3, label: "GroundTheory" },
    "Lemmata":           { color: "#6b21a8", bg: "#faf5ff", border: "#c084fc", tier: 3, label: "Lemmata" },
    "BuildAid":          { color: "#4b5563", bg: "#f3f4f6", border: "#9ca3af", tier: 3, label: "BuildAid" }
  };

  const DECL_COLORS = {
    theorem: "#1d4ed8",
    lemma: "#6b21a8",
    def: "#0f766e",
    structure: "#c2410c",
    abbrev: "#0284c7",
    class: "#86198f",
    instance: "#a16207",
    inductive: "#047857",
    other: "#64748b"
  };

  const state = {
    mode: "analyzed",
    graphView: "dag",    // "dag" | "ego" | "matrix"
    hopMode: "tr",       // "tr" | "direct"
    coneOnly: false,
    showDiagram: true,
    dagZoom: 1.0,
    query: "",
    sort: "ext",
    selectedDir: "Development",
    selectedFile: null,
    fileFilter: "",
    importerFilter: "",
    declKindFilter: "all",
    showAllLeftBf: false,
    showAllRightBf: false
  };

  let activeDagDrag = null;

  function getTheoryMeta(key) {
    if (THEORY_META[key]) return THEORY_META[key];
    const top = String(key || "").split("/")[0];
    return THEORY_META[top] || { color: "#475569", bg: "#f8fafc", border: "#94a3b8", tier: 3, label: top || "(root)" };
  }

  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  const shortMod = (rel) => String(rel || "").split("/").pop().replace(/\.lean$/, "");
  const shortLabel = (s, maxLen) => {
    const str = String(s || "");
    return str.length <= maxLen ? str : str.slice(0, maxLen - 1) + "\u2026";
  };
  const fileUrl = (rel, line) => (window.RHVersion && RHVersion.sourceUrl)
    ? RHVersion.sourceUrl(rel, line)
    : (rel + (line ? "#L" + line : ""));

  // Tooltip helpers
  const tooltipEl = document.getElementById("svgTooltip");
  function hideTooltip() {
    tooltipEl.style.display = "none";
  }
  function bindTooltips(rootEl) {
    rootEl.querySelectorAll("[data-tip-title]").forEach(el => {
      el.addEventListener("mouseenter", (ev) => {
        const title = el.getAttribute("data-tip-title") || "";
        const sub = el.getAttribute("data-tip-sub") || "";
        const body = el.getAttribute("data-tip-body") || "";
        tooltipEl.innerHTML =
          `<div class="tt-title">${esc(title)}</div>` +
          (sub ? `<div class="tt-sub">${esc(sub)}</div>` : "") +
          (body ? `<div class="tt-body">${esc(body)}</div>` : "");
        tooltipEl.style.display = "block";
        positionTooltip(ev);
      });
      el.addEventListener("mousemove", positionTooltip);
      el.addEventListener("mouseleave", hideTooltip);
    });
  }
  function positionTooltip(ev) {
    const pad = 12;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let x = ev.clientX + pad;
    let y = ev.clientY + pad;
    const rect = tooltipEl.getBoundingClientRect();
    if (x + rect.width + 10 > vw) x = Math.max(8, ev.clientX - rect.width - pad);
    if (y + rect.height + 10 > vh) y = Math.max(8, ev.clientY - rect.height - pad);
    tooltipEl.style.left = x + "px";
    tooltipEl.style.top = y + "px";
  }

  function syncTabs() {
    document.querySelectorAll(".tab").forEach(btn => {
      btn.classList.toggle("active", btn.dataset.mode === state.mode);
    });
  }

  function selectContract(relPath) {
    if (!ANALYZED_MAP.has(relPath)) return;
    state.selectedFile = relPath;
    state.declKindFilter = "all";
    render();
  }

  function jumpToTheory(mode, dirKey, importerFilter) {
    state.mode = mode;
    state.selectedDir = dirKey;
    state.importerFilter = importerFilter || "";
    state.fileFilter = "";
    state.showAllLeftBf = false;
    state.showAllRightBf = false;
    render();
  }

  function buildArrowMarkers(prefix) {
    return `
      <defs>
        <marker id="${prefix}-arr-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#94a3b8"/>
        </marker>
        <marker id="${prefix}-arr-up" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#b45309"/>
        </marker>
        <marker id="${prefix}-arr-down" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#0284c7"/>
        </marker>
        <marker id="${prefix}-arr-slate" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1.5 L 10 5 L 0 8.5 z" fill="#475569"/>
        </marker>
      </defs>
    `;
  }

  function getContractCones(relPath, hopMode) {
    const item = ANALYZED_MAP.get(relPath);
    const directUp = new Set();
    const directDown = new Set();
    const allUp = new Set();
    const allDown = new Set();
    if (!item) return { directUp, directDown, allUp, allDown };

    const upField = hopMode === "direct" ? "direct_analyzed_deps" : "tr_analyzed_deps";
    const downField = hopMode === "direct" ? "direct_analyzed_dependents" : "tr_analyzed_dependents";

    (item[upField] || []).forEach(p => directUp.add(p));
    (item[downField] || []).forEach(p => directDown.add(p));

    if (hopMode === "direct") {
      directUp.forEach(p => allUp.add(p));
      directDown.forEach(p => allDown.add(p));
      return { directUp, directDown, allUp, allDown };
    }

    const qUp = Array.from(directUp);
    while (qUp.length) {
      const cur = qUp.shift();
      if (allUp.has(cur)) continue;
      allUp.add(cur);
      const node = ANALYZED_MAP.get(cur);
      if (node) {
        (node.tr_analyzed_deps || []).forEach(nxt => {
          if (!allUp.has(nxt)) qUp.push(nxt);
        });
      }
    }

    const qDown = Array.from(directDown);
    while (qDown.length) {
      const cur = qDown.shift();
      if (allDown.has(cur)) continue;
      allDown.add(cur);
      const node = ANALYZED_MAP.get(cur);
      if (node) {
        (node.tr_analyzed_dependents || []).forEach(nxt => {
          if (!allDown.has(nxt)) qDown.push(nxt);
        });
      }
    }
    return { directUp, directDown, allUp, allDown };
  }

  function sortDirs(list) {
    const arr = list.slice();
    switch (state.sort) {
      case "name": arr.sort((a, b) => a.dir_key.localeCompare(b.dir_key)); break;
      default: arr.sort((a, b) => b.total_ext_imports - a.total_ext_imports || a.dir_key.localeCompare(b.dir_key));
    }
    return arr;
  }

  function matchesAnalyzedQuery(item, q) {
    if (!q) return true;
    if (item.rel_path.toLowerCase().includes(q)) return true;
    if (item.plain_english_summary.toLowerCase().includes(q)) return true;
    if (item.role.toLowerCase().includes(q)) return true;
    if (item.key_exports.some(k => k.name.toLowerCase().includes(q) || k.summary.toLowerCase().includes(q))) return true;
    if (item.all_declarations.some(d => d.name.toLowerCase().includes(q))) return true;
    return false;
  }

  function renderSidebar() {
    const q = state.query.trim().toLowerCase();
    const listEl = document.getElementById("sidebarList");
    const lblEl = document.getElementById("sidebarLabel");
    const cntEl = document.getElementById("sidebarCount");

    if (state.mode === "analyzed" || state.mode === "search") {
      lblEl.textContent = state.mode === "analyzed" ? "Analyzed Interface Files" : "Matching Analyzed Files";
      const items = DATA.analyzed_interfaces.filter(item => matchesAnalyzedQuery(item, q));
      cntEl.textContent = items.length;
      if (items.length && !items.some(x => x.rel_path === state.selectedFile)) {
        state.selectedFile = items[0].rel_path;
      }
      const maxConns = Math.max(1, ...DATA.analyzed_interfaces.map(x =>
        Object.keys(x.importing_top_dirs || {}).length +
        Object.keys(x.imported_top_dirs || {}).length +
        (x.tr_analyzed_deps || []).length +
        (x.tr_analyzed_dependents || []).length
      ));
      listEl.innerHTML = items.map(item => {
        const tm = getTheoryMeta(item.top_dir);
        const connScore =
          Object.keys(item.importing_top_dirs || {}).length +
          Object.keys(item.imported_top_dirs || {}).length +
          (item.tr_analyzed_deps || []).length +
          (item.tr_analyzed_dependents || []).length;
        const pct = Math.max(8, Math.round((connScore / maxConns) * 100));
        const active = item.rel_path === state.selectedFile;
        return `
          <div class="dir-item ${active ? "active" : ""}" style="border-left-color:${active ? tm.color : tm.border};" data-file="${esc(item.rel_path)}">
            <div class="dir-row-top">
              <span class="theory-dot" style="background:${tm.color};" title="${esc(item.top_dir)}"></span>
              <div class="dir-name mono">${esc(item.rel_path.split("/").pop())}</div>
            </div>
            <div class="muted" style="font-size:0.73rem;word-break:break-all;margin-left:15px;">${esc(item.depth2_dir)}</div>
            <div class="dir-meta" style="margin-left:15px;">
              <span class="badge">${esc(item.role)}</span>
              <span>${item.key_exports.length} key &middot; ${item.all_declarations.length} decls</span>
            </div>
            <div class="conn-bar" style="margin-left:15px;"><div class="conn-fill" style="width:${pct}%;background:${tm.color};"></div></div>
          </div>
        `;
      }).join("") || `<div style="padding:16px" class="muted">No analyzed files match "${esc(state.query)}".</div>`;
      listEl.querySelectorAll(".dir-item").forEach(el => {
        el.onclick = () => selectContract(el.dataset.file);
      });
      return;
    }

    const srcList = state.mode === "top" ? DATA.top_dirs : DATA.depth2_dirs;
    lblEl.textContent = state.mode === "top" ? "Top-Level Theories" : "Depth-2 Sub-Theories";
    const filtered = sortDirs(srcList).filter(d => {
      if (!q) return true;
      if (d.dir_key.toLowerCase().includes(q)) return true;
      return d.interface_files.some(f => f.p.toLowerCase().includes(q));
    });
    cntEl.textContent = filtered.length;
    if (filtered.length && !filtered.some(d => d.dir_key === state.selectedDir)) {
      state.selectedDir = filtered[0].dir_key;
    }

    const analyzedByDir = new Map();
    for (const a of DATA.analyzed_interfaces) {
      const k = state.mode === "top" ? a.top_dir : a.depth2_dir;
      analyzedByDir.set(k, (analyzedByDir.get(k) || 0) + 1);
    }
    const maxLinks = Math.max(1, ...srcList.map(d => d.importing_dirs.length + d.imported_external_dirs.length));

    listEl.innerHTML = filtered.map(d => {
      const tm = getTheoryMeta(d.dir_key);
      const anCnt = analyzedByDir.get(d.dir_key) || 0;
      const links = d.importing_dirs.length + d.imported_external_dirs.length;
      const pct = Math.max(6, Math.round((links / maxLinks) * 100));
      const active = d.dir_key === state.selectedDir;
      return `
        <div class="dir-item ${active ? "active" : ""}" style="border-left-color:${active ? tm.color : tm.border};" data-dir="${esc(d.dir_key)}">
          <div class="dir-row-top">
            <span class="theory-dot" style="background:${tm.color};"></span>
            <div class="dir-name">${esc(d.dir_key)}</div>
          </div>
          <div class="dir-meta" style="margin-left:15px;">
            <span>Parent: ${esc(d.parent_key || "(root)")}</span>
            <span>${d.importing_dirs.length}&darr; ${d.imported_external_dirs.length}&uarr;${anCnt ? ` &middot; <b>${anCnt} API${anCnt > 1 ? "s" : ""}</b>` : ""}</span>
          </div>
          <div class="conn-bar" style="margin-left:15px;"><div class="conn-fill" style="width:${pct}%;background:${tm.color};"></div></div>
        </div>
      `;
    }).join("") || `<div style="padding:16px" class="muted">No theories match "${esc(state.query)}".</div>`;

    listEl.querySelectorAll(".dir-item").forEach(el => {
      el.onclick = () => jumpToTheory(state.mode, el.dataset.dir, "");
    });
  }

  // =========================================================================
  // VIEW 1: Stratified 59-Interface Contract Architecture DAG (SVG)
  // =========================================================================
  function buildContractDagHtml() {
    const W = 1420;
    const NW = 152, NH = 38, NGX = 10, NGY = 12, PADX = 12, HEADH = 28, PADB = 12;

    const byTop = new Map();
    THEORY_ORDER.forEach(t => byTop.set(t, []));
    for (const item of DATA.analyzed_interfaces) {
      if (!byTop.has(item.top_dir)) byTop.set(item.top_dir, []);
      byTop.get(item.top_dir).push(item);
    }
    byTop.forEach(arr => {
      arr.sort((a, b) =>
        (b.height_from_leaves - a.height_from_leaves) ||
        (a.dist_from_main - b.dist_from_main) ||
        a.rel_path.localeCompare(b.rel_path)
      );
    });

    const tierConfigs = [
      { label: "Tier 0: Apex & Entrypoints", items: [
        { key: "(root)", cols: 2 },
        { key: "Supplements", cols: 2 }
      ]},
      { label: "Tier 1: Core Synthesis & Automorphic/Positivity Pillars", items: [
        { key: "Development", cols: 4 },
        { key: "CompanionTheory", cols: 2 },
        { key: "PositivityTheory", cols: 2 }
      ]},
      { label: "Tier 2: Specification & Contract Hubs", items: [
        { key: "Formalism", cols: 5 },
        { key: "ReciprocityTheory", cols: 3 }
      ]},
      { label: "Tier 3: Foundational & Support Machinery", items: [
        { key: "GroundTheory", cols: 3 },
        { key: "Lemmata", cols: 1 },
        { key: "BuildAid", cols: 1 }
      ]}
    ];

    const boxes = [];
    const nodePos = new Map();
    let curY = 20;

    for (const tier of tierConfigs) {
      const presentItems = tier.items.filter(cfg => (byTop.get(cfg.key) || []).length > 0 || TOP_DIR_MAP.has(cfg.key));
      if (!presentItems.length) continue;
      const gap = presentItems.length === 3 && presentItems[0].key === "Development" ? 20 : 28;
      const boxMeta = presentItems.map(cfg => {
        const nodes = byTop.get(cfg.key) || [];
        const rows = Math.max(1, Math.ceil(nodes.length / cfg.cols));
        const w = cfg.cols * NW + (cfg.cols - 1) * NGX + 2 * PADX;
        const h = HEADH + rows * NH + (rows - 1) * NGY + PADB;
        return { key: cfg.key, cols: cfg.cols, nodes, w, h };
      });
      const tierMaxH = Math.max(...boxMeta.map(b => b.h));
      const totalW = boxMeta.reduce((s, b) => s + b.w, 0) + gap * (boxMeta.length - 1);
      let curX = Math.round((W - totalW) / 2);

      for (const b of boxMeta) {
        boxes.push({ key: b.key, x: curX, y: curY, w: b.w, h: tierMaxH, count: b.nodes.length });
        b.nodes.forEach((item, idx) => {
          const r = Math.floor(idx / b.cols);
          const c = idx % b.cols;
          const nx = curX + PADX + c * (NW + NGX);
          const ny = curY + HEADH + r * (NH + NGY);
          nodePos.set(item.rel_path, {
            x: nx, y: ny, cx: nx + NW / 2, cy: ny + NH / 2,
            w: NW, h: NH, tier: getTheoryMeta(item.top_dir).tier, item
          });
        });
        curX += b.w + gap;
      }
      curY += tierMaxH + 54;
    }
    const H = curY - 34;

    const sel = state.selectedFile;
    const cones = getContractCones(sel, state.hopMode);
    const q = state.query.trim().toLowerCase();

    // Edges
    const edgeField = state.hopMode === "direct" ? "direct_analyzed_deps" : "tr_analyzed_deps";
    const bgEdges = [];
    const fgEdges = [];

    for (const srcItem of DATA.analyzed_interfaces) {
      const s = srcItem.rel_path;
      const sp = nodePos.get(s);
      if (!sp) continue;
      for (const d of (srcItem[edgeField] || [])) {
        const dp = nodePos.get(d);
        if (!dp) continue;

        let relType = "bg";
        if (s === sel) relType = "up-direct";
        else if (d === sel) relType = "down-direct";
        else if (cones.allUp.has(s) && cones.allUp.has(d)) relType = "up-cone";
        else if (cones.allDown.has(s) && cones.allDown.has(d)) relType = "down-cone";

        if (state.coneOnly && relType === "bg") continue;

        let pathD = "";
        if (sp.y + sp.h < dp.y - 6) {
          const x1 = sp.cx, y1 = sp.y + sp.h;
          const x2 = dp.cx, y2 = dp.y;
          const dy = Math.max(22, (y2 - y1) * 0.45);
          pathD = `M ${x1} ${y1} C ${x1} ${y1 + dy}, ${x2} ${y2 - dy}, ${x2} ${y2}`;
        } else if (dp.y + dp.h < sp.y - 6) {
          const x1 = sp.cx, y1 = sp.y;
          const x2 = dp.cx, y2 = dp.y + dp.h;
          const dy = Math.max(22, (y1 - y2) * 0.45);
          pathD = `M ${x1} ${y1} C ${x1 - 24} ${y1 - dy}, ${x2 - 24} ${y2 + dy}, ${x2} ${y2}`;
        } else {
          // Same row / adjacent inside same tier
          const x1 = sp.cx, y1 = sp.y;
          const x2 = dp.cx, y2 = dp.y;
          const arcY = Math.min(y1, y2) - 24;
          pathD = `M ${x1} ${y1} C ${x1} ${arcY}, ${x2} ${arcY}, ${x2} ${y2}`;
        }

        let stroke = "#94a3b8", sw = 1.0, op = 0.2, marker = "dag-arr-muted";
        if (relType === "up-direct") { stroke = "#b45309"; sw = 2.2; op = 0.95; marker = "dag-arr-up"; }
        else if (relType === "up-cone") { stroke = "#d97706"; sw = 1.5; op = 0.65; marker = "dag-arr-up"; }
        else if (relType === "down-direct") { stroke = "#0284c7"; sw = 2.2; op = 0.95; marker = "dag-arr-down"; }
        else if (relType === "down-cone") { stroke = "#0284c7"; sw = 1.5; op = 0.65; marker = "dag-arr-down"; }

        const svgPath = `<path d="${pathD}" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-opacity="${op}" marker-end="url(#${marker})" pointer-events="none"/>`;
        if (relType === "bg") bgEdges.push(svgPath);
        else fgEdges.push(svgPath);
      }
    }

    const boxesSvg = boxes.map(b => {
      const tm = getTheoryMeta(b.key);
      return `
        <g>
          <rect x="${b.x}" y="${b.y}" width="${b.w}" height="${b.h}" rx="6" fill="${tm.bg}" fill-opacity="0.55" stroke="${tm.border}" stroke-width="1.3"/>
          <rect x="${b.x}" y="${b.y}" width="${b.w}" height="22" rx="6" fill="${tm.color}" fill-opacity="0.1"/>
          <text x="${b.x + 10}" y="${b.y + 15}" font-size="11" font-weight="700" fill="${tm.color}" style="cursor:pointer;" data-jump-top="${esc(b.key)}">${esc(b.key)} (${b.count})</text>
        </g>
      `;
    }).join("");

    const nodesSvg = Array.from(nodePos.values()).map(np => {
      const item = np.item;
      const p = item.rel_path;
      const tm = getTheoryMeta(item.top_dir);
      const isSel = p === sel;
      const isDirectUp = cones.directUp.has(p);
      const isAllUp = cones.allUp.has(p);
      const isDirectDown = cones.directDown.has(p);
      const isAllDown = cones.allDown.has(p);
      const inCone = isSel || isAllUp || isAllDown;
      const queryHit = q && matchesAnalyzedQuery(item, q);

      let fill = "#ffffff";
      let stroke = tm.border;
      let sw = 1.2;
      let op = state.coneOnly && !inCone ? 0.25 : 1.0;

      if (isSel) {
        fill = "#eff6ff"; stroke = "#111111"; sw = 2.5; op = 1.0;
      } else if (isAllUp) {
        fill = "#fef3c7"; stroke = "#b45309"; sw = isDirectUp ? 2.1 : 1.3; op = 1.0;
      } else if (isAllDown) {
        fill = "#e0f2fe"; stroke = "#0284c7"; sw = isDirectDown ? 2.1 : 1.3; op = 1.0;
      }
      if (queryHit && !isSel) {
        stroke = "#111111"; sw = 2.0;
      }

      const title = shortLabel(shortMod(p), 20);
      const sub = item.key_exports.length
        ? `${item.key_exports.length} key · ${item.all_declarations.length} decls`
        : `Re-export · ${item.all_declarations.length} decls`;
      const tipBody = `${item.role} | Used by ${Object.keys(item.importing_top_dirs || {}).length} ext theories · Depends on ${Object.keys(item.imported_top_dirs || {}).length} ext theories`;

      return `
        <g class="svg-node" opacity="${op}" data-select-file="${esc(p)}"
           data-tip-title="${esc(p)}"
           data-tip-sub="${esc(item.top_dir + ' · ' + item.depth2_dir)}"
           data-tip-body="${esc(tipBody)}">
          <rect class="svg-node-box" x="${np.x}" y="${np.y}" width="${np.w}" height="${np.h}" rx="4" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>
          <rect x="${np.x}" y="${np.y}" width="4" height="${np.h}" rx="2" fill="${tm.color}"/>
          <text x="${np.x + 10}" y="${np.y + 15}" font-size="10.5" font-weight="700" fill="#111111" font-family="ui-monospace, SFMono-Regular, Menlo, monospace">${esc(title)}</text>
          <text x="${np.x + 10}" y="${np.y + 29}" font-size="9" fill="#555555">${esc(sub)}</text>
        </g>
      `;
    }).join("");

    const scaledW = Math.round(W * state.dagZoom);
    const scaledH = Math.round(H * state.dagZoom);

    return `
      <div class="dag-scroll" id="dagScroll">
        <div class="dag-stage" id="dagStage">
          <svg width="${scaledW}" height="${scaledH}" viewBox="0 0 ${W} ${H}">
            ${buildArrowMarkers("dag")}
            ${boxesSvg}
            <g>${bgEdges.join("")}</g>
            <g>${fgEdges.join("")}</g>
            <g>${nodesSvg}</g>
          </svg>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // VIEW 2 & EMBEDDED DETAIL: Focused Contract Boundary Ego-Graph (SVG)
  // =========================================================================
  function buildContractEgoHtml(item, prefix) {
    if (!item) return "";
    const hopMode = state.hopMode;
    const downContracts = (hopMode === "direct" ? item.direct_analyzed_dependents : item.tr_analyzed_dependents) || [];
    const upContracts = (hopMode === "direct" ? item.direct_analyzed_deps : item.tr_analyzed_deps) || [];

    const impTop = Object.keys(item.importing_top_dirs || {});
    const impD2 = Object.keys(item.importing_d2_dirs || {});
    const outTop = Object.keys(item.imported_top_dirs || {});
    const outD2 = Object.keys(item.imported_d2_dirs || {});

    const leftItems = [];
    if (impTop.length) {
      leftItems.push({ type: "hdr", label: `Used By Top-Level Theories (${impTop.length})` });
      impTop.forEach(d => leftItems.push({ type: "top", label: d, jumpTop: d, edges: item.importing_top_dirs[d] }));
    }
    if (impD2.length) {
      leftItems.push({ type: "hdr", label: `Used By Sub-Theories (${impD2.length})` });
      impD2.slice(0, 7).forEach(d => leftItems.push({ type: "d2", label: d, jumpD2: d, edges: item.importing_d2_dirs[d] }));
      if (impD2.length > 7) leftItems.push({ type: "note", label: `+ ${impD2.length - 7} more sub-theories` });
    }
    if (downContracts.length) {
      leftItems.push({ type: "hdr", label: `Downstream Analyzed Contracts (${downContracts.length})` });
      downContracts.slice(0, 9).forEach(p => leftItems.push({ type: "file", label: shortMod(p), path: p }));
      if (downContracts.length > 9) leftItems.push({ type: "note", label: `+ ${downContracts.length - 9} more contracts` });
    }
    if (!leftItems.length) {
      leftItems.push({ type: "note", label: "Apex entrypoint (no external dependents)" });
    }

    const rightItems = [];
    if (upContracts.length) {
      rightItems.push({ type: "hdr", label: `Upstream Analyzed Contracts (${upContracts.length})` });
      upContracts.slice(0, 10).forEach(p => rightItems.push({ type: "file", label: shortMod(p), path: p }));
      if (upContracts.length > 10) rightItems.push({ type: "note", label: `+ ${upContracts.length - 10} more contracts` });
    }
    if (outTop.length) {
      rightItems.push({ type: "hdr", label: `Imports Top-Level Theories (${outTop.length})` });
      outTop.forEach(d => rightItems.push({ type: "top", label: d, jumpTop: d, edges: item.imported_top_dirs[d] }));
    }
    if (outD2.length) {
      rightItems.push({ type: "hdr", label: `Imports Sub-Theories (${outD2.length})` });
      outD2.slice(0, 7).forEach(d => rightItems.push({ type: "d2", label: d, jumpD2: d, edges: item.imported_d2_dirs[d] }));
      if (outD2.length > 7) rightItems.push({ type: "note", label: `+ ${outD2.length - 7} more sub-theories` });
    }
    if (!rightItems.length) {
      rightItems.push({ type: "note", label: "No external theory imports (internal / Mathlib only)" });
    }

    const rowHeight = (it) => it.type === "hdr" ? 20 : (it.type === "note" ? 18 : 26);
    const colGap = 5;
    const calcColH = (arr) => arr.reduce((s, it) => s + rowHeight(it) + colGap, 0);

    const exportsShown = item.key_exports.slice(0, 9);
    const extraExports = Math.max(0, item.key_exports.length - exportsShown.length);
    const centerH = 74 + Math.max(1, exportsShown.length) * 28 + (extraExports ? 20 : 0) + 14;

    const leftH = calcColH(leftItems);
    const rightH = calcColH(rightItems);
    const H = Math.max(210, leftH + 36, rightH + 36, centerH + 40);
    const W = 1080;

    const centerX = 385, centerW = 310;
    const centerY = Math.round((H - centerH) / 2);
    const tm = getTheoryMeta(item.top_dir);

    let leftY = Math.round((H - leftH) / 2);
    const leftNodesSvg = [];
    const leftEdgesSvg = [];
    const lx = 16, lw = 290;

    leftItems.forEach((it) => {
      const rh = rowHeight(it);
      if (it.type === "hdr") {
        leftNodesSvg.push(`<text x="${lx}" y="${leftY + 14}" font-size="10.5" font-weight="700" fill="#075985">${esc(it.label)}</text>`);
      } else if (it.type === "note") {
        leftNodesSvg.push(`<text x="${lx + 6}" y="${leftY + 12}" font-size="10" fill="#64748b" font-style="italic">${esc(it.label)}</text>`);
      } else {
        const cy = leftY + rh / 2;
        const ctm = it.type === "file" ? getTheoryMeta(ANALYZED_MAP.get(it.path)?.top_dir) : getTheoryMeta(it.label);
        const attr = it.type === "file"
          ? `data-select-file="${esc(it.path)}"`
          : (it.type === "top" ? `data-jump-top="${esc(it.jumpTop)}"` : `data-jump-d2="${esc(it.jumpD2)}"`);
        const tipTitle = it.type === "file" ? it.path : it.label;
        const tipSub = it.type === "file" ? (ANALYZED_MAP.get(it.path)?.role || "Analyzed Contract") : (it.type === "top" ? "Top-Level Theory (click to open)" : "Depth-2 Sub-Theory (click to open)");
        const dx = centerX - (lx + lw);
        const targetY = centerY + Math.min(centerH - 20, Math.max(20, cy - centerY));
        leftEdgesSvg.push(
          `<path d="M ${lx + lw} ${cy} C ${lx + lw + dx * 0.5} ${cy}, ${centerX - dx * 0.5} ${targetY}, ${centerX - 2} ${targetY}" fill="none" stroke="#0284c7" stroke-width="1.5" stroke-opacity="0.7" marker-end="url(#${prefix}-arr-down)"/>`
        );
        leftNodesSvg.push(`
          <g class="svg-node" ${attr} data-tip-title="${esc(tipTitle)}" data-tip-sub="${esc(tipSub)}">
            <rect class="svg-node-box" x="${lx}" y="${leftY}" width="${lw}" height="${rh}" rx="4" fill="#e0f2fe" stroke="#0284c7" stroke-width="1.1"/>
            <rect x="${lx}" y="${leftY}" width="4" height="${rh}" rx="2" fill="${ctm.color}"/>
            <text x="${lx + 10}" y="${leftY + 17}" font-size="10.5" font-weight="600" fill="#0c4a6e" font-family="${it.type === "file" ? "ui-monospace,monospace" : "inherit"}">${esc(shortLabel(it.label, 35))}</text>
          </g>
        `);
      }
      leftY += rh + colGap;
    });

    let rightY = Math.round((H - rightH) / 2);
    const rightNodesSvg = [];
    const rightEdgesSvg = [];
    const rx = 774, rw = 290;

    rightItems.forEach((it) => {
      const rh = rowHeight(it);
      if (it.type === "hdr") {
        rightNodesSvg.push(`<text x="${rx}" y="${rightY + 14}" font-size="10.5" font-weight="700" fill="#92400e">${esc(it.label)}</text>`);
      } else if (it.type === "note") {
        rightNodesSvg.push(`<text x="${rx + 6}" y="${rightY + 12}" font-size="10" fill="#64748b" font-style="italic">${esc(it.label)}</text>`);
      } else {
        const cy = rightY + rh / 2;
        const ctm = it.type === "file" ? getTheoryMeta(ANALYZED_MAP.get(it.path)?.top_dir) : getTheoryMeta(it.label);
        const attr = it.type === "file"
          ? `data-select-file="${esc(it.path)}"`
          : (it.type === "top" ? `data-jump-top="${esc(it.jumpTop)}"` : `data-jump-d2="${esc(it.jumpD2)}"`);
        const tipTitle = it.type === "file" ? it.path : it.label;
        const tipSub = it.type === "file" ? (ANALYZED_MAP.get(it.path)?.role || "Analyzed Contract") : (it.type === "top" ? "Top-Level Theory (click to open)" : "Depth-2 Sub-Theory (click to open)");
        const dx = rx - (centerX + centerW);
        const srcY = centerY + Math.min(centerH - 20, Math.max(20, cy - centerY));
        rightEdgesSvg.push(
          `<path d="M ${centerX + centerW} ${srcY} C ${centerX + centerW + dx * 0.5} ${srcY}, ${rx - dx * 0.5} ${cy}, ${rx - 2} ${cy}" fill="none" stroke="#b45309" stroke-width="1.5" stroke-opacity="0.7" marker-end="url(#${prefix}-arr-up)"/>`
        );
        rightNodesSvg.push(`
          <g class="svg-node" ${attr} data-tip-title="${esc(tipTitle)}" data-tip-sub="${esc(tipSub)}">
            <rect class="svg-node-box" x="${rx}" y="${rightY}" width="${rw}" height="${rh}" rx="4" fill="#fef3c7" stroke="#b45309" stroke-width="1.1"/>
            <rect x="${rx}" y="${rightY}" width="4" height="${rh}" rx="2" fill="${ctm.color}"/>
            <text x="${rx + 10}" y="${rightY + 17}" font-size="10.5" font-weight="600" fill="#78350f" font-family="${it.type === "file" ? "ui-monospace,monospace" : "inherit"}">${esc(shortLabel(it.label, 35))}</text>
          </g>
        `);
      }
      rightY += rh + colGap;
    });

    // Center Contract Card
    let expY = centerY + 66;
    const exportNodesSvg = exportsShown.length
      ? exportsShown.map(ke => {
          const kc = DECL_COLORS[ke.kind] || DECL_COLORS.other;
          const row = `
            <g class="svg-node" data-open-url="${esc(fileUrl(item.rel_path, ke.line_no))}"
               data-tip-title="${esc(ke.kind + ' ' + ke.name + ' (L' + ke.line_no + ')')}"
               data-tip-body="${esc(ke.summary)}">
              <rect class="svg-node-box" x="${centerX + 12}" y="${expY}" width="${centerW - 24}" height="23" rx="3" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
              <rect x="${centerX + 12}" y="${expY}" width="4" height="23" rx="1" fill="${kc}"/>
              <text x="${centerX + 21}" y="${expY + 15}" font-size="10" font-weight="600" fill="#111111" font-family="ui-monospace,monospace">${esc(ke.kind)} ${esc(shortLabel(ke.name, 27))}</text>
            </g>
          `;
          expY += 28;
          return row;
        }).join("")
      : `<rect x="${centerX + 12}" y="${expY}" width="${centerW - 24}" height="24" rx="3" fill="#ffffff" stroke="#cbd5e1"/>
         <text x="${centerX + 20}" y="${expY + 16}" font-size="10" fill="#64748b">Pure import barrel / namespace facade</text>`;

    const extraExpSvg = extraExports
      ? `<text x="${centerX + 14}" y="${expY + 14}" font-size="9.5" fill="#64748b">+ ${extraExports} more key exports in table below</text>`
      : "";

    const centerSvg = `
      <g>
        <rect x="${centerX}" y="${centerY}" width="${centerW}" height="${centerH}" rx="6" fill="${tm.bg}" stroke="${tm.color}" stroke-width="2"/>
        <rect x="${centerX}" y="${centerY}" width="${centerW}" height="56" rx="6" fill="${tm.color}" fill-opacity="0.1"/>
        <text x="${centerX + 12}" y="${centerY + 20}" font-size="12.5" font-weight="700" fill="#111111" font-family="ui-monospace,monospace">${esc(shortLabel(shortMod(item.rel_path), 31))}</text>
        <text x="${centerX + 12}" y="${centerY + 35}" font-size="10" font-weight="600" fill="${tm.color}">${esc(shortLabel(item.depth2_dir, 40))}</text>
        <text x="${centerX + 12}" y="${centerY + 49}" font-size="9.5" fill="#475569">${esc(shortLabel(item.role, 42))}</text>
        ${exportNodesSvg}
        ${extraExpSvg}
      </g>
    `;

    return `
      <div class="svg-box">
        <svg viewBox="0 0 ${W} ${H}" width="100%" style="min-width:740px;">
          ${buildArrowMarkers(prefix)}
          ${leftEdgesSvg.join("")}
          ${rightEdgesSvg.join("")}
          ${leftNodesSvg.join("")}
          ${rightNodesSvg.join("")}
          ${centerSvg}
        </svg>
      </div>
    `;
  }

  // =========================================================================
  // VIEW 3: Cross-Theory Flow Network & 10x10 Coupling Heatmap
  // =========================================================================
  function buildMatrixViewHtml() {
    const W = 620, H = 430;
    const tierBoxes = [[], [], [], []];
    THEORY_ORDER.forEach(t => {
      const tr = Math.max(0, Math.min(3, getTheoryMeta(t).tier ?? 3));
      tierBoxes[tr].push(t);
    });
    const nodes = {};
    const tierY = [20, 120, 234, 348];
    tierBoxes.forEach((arr, tr) => {
      if (!arr.length) return;
      const boxH = tr === 0 ? 42 : 46;
      const gapX = 24;
      const maxW = Math.min(170, Math.floor((W - 40 - gapX * Math.max(0, arr.length - 1)) / arr.length));
      const totalW = arr.length * maxW + Math.max(0, arr.length - 1) * gapX;
      let cx = Math.round((W - totalW) / 2);
      for (const t of arr) {
        nodes[t] = { x: cx, y: tierY[tr], w: maxW, h: boxH };
        cx += maxW + gapX;
      }
    });

    const edgeLookup = new Map();
    let maxEdges = 1;
    for (const r of DATA.top_dir_matrix) {
      edgeLookup.set(`${r.src_dir}::${r.dst_dir}`, r);
      if (r.edges > maxEdges) maxEdges = r.edges;
    }

    const anCounts = new Map();
    DATA.analyzed_interfaces.forEach(a => anCounts.set(a.top_dir, (anCounts.get(a.top_dir) || 0) + 1));

    const edgesSvg = DATA.top_dir_matrix.map(r => {
      const sp = nodes[r.src_dir], dp = nodes[r.dst_dir];
      if (!sp || !dp) return "";
      const rev = edgeLookup.get(`${r.dst_dir}::${r.src_dir}`);
      const sTier = getTheoryMeta(r.src_dir).tier;
      const dTier = getTheoryMeta(r.dst_dir).tier;
      const isRev = (sTier > dTier) || (rev && r.edges < rev.edges && sTier >= dTier);

      const x1 = sp.x + sp.w / 2, y1 = sp.y + sp.h / 2;
      const x2 = dp.x + dp.w / 2, y2 = dp.y + dp.h / 2;
      const mx = (x1 + x2) / 2, my = (y1 + y2) / 2;
      const dx = x2 - x1, dy = y2 - y1;
      const len = Math.max(1, Math.hypot(dx, dy));
      const curveOffset = rev ? (isRev ? 26 : -22) : 0;
      const cx = mx - (dy / len) * curveOffset;
      const cy = my + (dx / len) * curveOffset;

      // Trim endpoints cleanly near rectangle borders
      const sx = x1 + (dx / len) * 28;
      const sy = y1 + (dy / len) * 20;
      const ex = x2 - (dx / len) * 32;
      const ey = y2 - (dy / len) * 24;

      const sw = 1.0 + (Math.log10(1 + r.edges) / Math.log10(1 + maxEdges)) * 3.8;
      const stroke = isRev ? "#d97706" : (r.edges >= 1000 ? "#0284c7" : "#475569");
      const dash = isRev ? `stroke-dasharray="5,3"` : "";
      const op = isRev ? 0.55 : (r.edges >= 1000 ? 0.8 : 0.45);
      const marker = isRev ? "mat-arr-up" : (r.edges >= 1000 ? "mat-arr-down" : "mat-arr-slate");

      return `<path d="M ${sx} ${sy} Q ${cx} ${cy} ${ex} ${ey}" fill="none" stroke="${stroke}" stroke-width="${sw.toFixed(2)}" stroke-opacity="${op}" ${dash} marker-end="url(#${marker})"/>`;
    }).join("");

    const nodesSvg = THEORY_ORDER.map(t => {
      const p = nodes[t];
      const tm = getTheoryMeta(t);
      const td = TOP_DIR_MAP.get(t);
      const anCnt = anCounts.get(t) || 0;
      const inC = td ? td.importing_dirs.length : 0;
      const outC = td ? td.imported_external_dirs.length : 0;
      return `
        <g class="svg-node" data-jump-top="${esc(t)}"
           data-tip-title="${esc(t)}"
           data-tip-sub="${anCnt} analyzed interface contracts"
           data-tip-body="Used by ${inC} external theories · Depends on ${outC} external theories. Click to inspect.">
          <rect class="svg-node-box" x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="5" fill="${tm.bg}" stroke="${tm.color}" stroke-width="1.8"/>
          <text x="${p.x + p.w / 2}" y="${p.y + 18}" text-anchor="middle" font-size="11.5" font-weight="700" fill="#111111">${esc(t)}</text>
          <text x="${p.x + p.w / 2}" y="${p.y + 33}" text-anchor="middle" font-size="9.5" fill="${tm.color}">${anCnt} analyzed API${anCnt === 1 ? "" : "s"}</text>
        </g>
      `;
    }).join("");

    // 10x10 Coupling Matrix
    const logMax = Math.log10(1 + maxEdges);
    const matrixHtml = `
      <table class="matrix-table">
        <thead>
          <tr>
            <th class="row-hd">Importer &darr; / Exported &rarr;</th>
            ${THEORY_ORDER.map(dst => `<th class="col-hd"><span style="color:${getTheoryMeta(dst).color};">${esc(dst)}</span></th>`).join("")}
          </tr>
        </thead>
        <tbody>
          ${THEORY_ORDER.map(src => `
            <tr>
              <th class="row-hd"><span class="theory-dot" style="background:${getTheoryMeta(src).color};margin-right:4px;"></span>${esc(src)}</th>
              ${THEORY_ORDER.map(dst => {
                if (src === dst) return `<td class="matrix-diag">&mdash;</td>`;
                const rec = edgeLookup.get(`${src}::${dst}`);
                if (!rec) return `<td class="matrix-zero">&middot;</td>`;
                const ratio = Math.log10(1 + rec.edges) / logMax;
                const alpha = (0.12 + ratio * 0.78).toFixed(2);
                const textColor = ratio > 0.55 ? "#ffffff" : "#0c4a6e";
                const tierLabel = rec.edges >= 1000 ? "Primary" : (rec.edges >= 50 ? "Medium" : "Light");
                return `
                  <td class="matrix-cell"
                      style="background:rgba(2, 132, 199, ${alpha});color:${textColor};"
                      data-matrix-src="${esc(src)}" data-matrix-dst="${esc(dst)}"
                      data-tip-title="${esc(src)} \u2192 ${esc(dst)}"
                      data-tip-sub="${tierLabel} cross-theory coupling"
                      data-tip-body="${rec.src_files} modules import ${rec.dst_files} interface modules. Click to filter ${dst} interfaces used by ${src}.">
                    ${rec.dst_files}
                  </td>
                `;
              }).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
      <div class="muted" style="font-size:0.75rem;margin-top:8px;">
        Cell numbers indicate how many cross-boundary interface modules in the column theory are imported by the row theory; shading reflects log-scaled coupling strength. Click any cell to inspect those modules.
      </div>
    `;

    return `
      <div class="matrix-grid-wrap">
        <div>
          <div style="font-size:0.84rem;font-weight:700;margin-bottom:6px;">Top-Level Cross-Theory Flow Network (A &rarr; B means A imports B)</div>
          <div class="svg-box" style="border:1px solid #e2e8f0;">
            <svg viewBox="0 0 ${W} ${H}" width="100%">
              ${buildArrowMarkers("mat")}
              ${edgesSvg}
              ${nodesSvg}
            </svg>
          </div>
          <div class="muted" style="font-size:0.75rem;margin-top:6px;">
            Solid blue/slate arrows indicate primary downward dependencies; dashed amber arrows indicate reverse feedback links. Click any theory box to browse its interfaces.
          </div>
        </div>
        <div>
          <div style="font-size:0.84rem;font-weight:700;margin-bottom:6px;">${THEORY_ORDER.length}&times;${THEORY_ORDER.length} Cross-Theory Coupling Matrix</div>
          ${matrixHtml}
        </div>
      </div>
    `;
  }

  // =========================================================================
  // ANALYZED EXPLORER TOP GRAPHICAL PANEL
  // =========================================================================
  function renderAnalyzedGraphPanel() {
    const item = ANALYZED_MAP.get(state.selectedFile);
    const cones = getContractCones(state.selectedFile, state.hopMode);
    const tm = item ? getTheoryMeta(item.top_dir) : THEORY_META["(root)"];

    const viewTitle = state.graphView === "dag"
      ? `Contract Architecture DAG (${DATA.analyzed_interfaces.length} Analyzed Mathematical Interfaces)`
      : (state.graphView === "ego"
        ? "Focused Contract Boundary Ego-Graph"
        : "Cross-Theory Flow Network & Coupling Matrix");

    let bodyHtml = "";
    if (state.showDiagram) {
      if (state.graphView === "dag") bodyHtml = buildContractDagHtml();
      else if (state.graphView === "ego") bodyHtml = buildContractEgoHtml(item, "ego");
      else bodyHtml = buildMatrixViewHtml();
    }

    const selBannerHtml = item ? `
      <div class="sel-banner">
        <span class="theory-dot" style="background:${tm.color};"></span>
        <strong class="mono">${esc(shortMod(item.rel_path))}</strong>
        <span class="badge">${esc(item.role)}</span>
        <span class="chip down">${cones.allDown.size} downstream consumer${cones.allDown.size === 1 ? "" : "s"}</span>
        <span class="chip up">${cones.allUp.size} upstream dependenc${cones.allUp.size === 1 ? "y" : "ies"}</span>
        ${state.hopMode === "tr" && (cones.directUp.size || cones.directDown.size) ? `
          <span class="muted" style="font-size:0.75rem;">
            (${cones.directDown.size} direct TR &darr; · ${cones.directUp.size} direct TR &uarr;)
          </span>
        ` : ""}
        <div style="margin-left:auto;display:flex;gap:6px;flex-wrap:wrap;">
          <button class="btn sm" data-jump-top="${esc(item.top_dir)}">Open ${esc(item.top_dir)} Theory</button>
          <button class="btn sm" data-jump-d2="${esc(item.depth2_dir)}">Open ${esc(shortLabel(item.depth2_dir, 28))}</button>
        </div>
      </div>
    ` : "";

    return `
      <div class="graph-panel">
        <div class="graph-head">
          <div class="graph-title-group">
            <h2>${esc(viewTitle)}</h2>
            <div class="seg-group">
              <button class="btn sm ${state.graphView === "dag" ? "active" : ""}" data-gview="dag">1. Contract DAG</button>
              <button class="btn sm ${state.graphView === "ego" ? "active" : ""}" data-gview="ego">2. Boundary Ego-Graph</button>
              <button class="btn sm ${state.graphView === "matrix" ? "active" : ""}" data-gview="matrix">3. Theory Flow &amp; Matrix</button>
            </div>
          </div>
          <div class="graph-controls">
            ${state.graphView !== "matrix" ? `
              <div class="seg-group">
                <button class="btn sm ${state.hopMode === "tr" ? "active" : ""}" data-hop="tr" title="Transitive reduction contract DAG (164 minimal edges)">Transitive DAG</button>
                <button class="btn sm ${state.hopMode === "direct" ? "active" : ""}" data-hop="direct" title="Direct 1-hop module imports only (9 edges)">Direct 1-Hop</button>
              </div>
            ` : ""}
            ${state.graphView === "dag" && state.showDiagram ? `
              <label style="display:inline-flex;align-items:center;gap:4px;font-size:0.77rem;cursor:pointer;">
                <input type="checkbox" id="chkConeOnly" ${state.coneOnly ? "checked" : ""}> Selected cone only
              </label>
              <div class="seg-group">
                <button class="btn sm" id="btnDagZoomOut" title="Zoom Out">&minus;</button>
                <button class="btn sm" id="btnDagZoomReset" title="Reset Zoom">${Math.round(state.dagZoom * 100)}%</button>
                <button class="btn sm" id="btnDagZoomIn" title="Zoom In">+</button>
              </div>
            ` : ""}
            <button class="btn sm" id="btnToggleDiagram">${state.showDiagram ? "Hide Diagram" : "Show Diagram"}</button>
          </div>
        </div>
        ${state.showDiagram ? `
          <div class="legend-strip">
            <div class="legend-items">
              ${state.graphView === "matrix" ? `
                <span class="legend-item"><span class="swatch" style="background:#0284c7;border-color:#0284c7;"></span> Primary dependency flow (A &rarr; B means A imports B)</span>
                <span class="legend-item"><span class="swatch" style="background:#d97706;border-color:#d97706;"></span> Reverse feedback flow</span>
              ` : `
                <span class="legend-item"><span class="swatch sel"></span> Selected Contract</span>
                <span class="legend-item"><span class="swatch down"></span> Downstream Consumers (Import Selected)</span>
                <span class="legend-item"><span class="swatch up"></span> Upstream Dependencies (Imported by Selected)</span>
                <span class="muted">Arrow <code>A &rarr; B</code> means <code>A</code> depends on <code>B</code> · Click any node to inspect</span>
              `}
            </div>
          </div>
          ${bodyHtml}
        ` : ""}
        ${selBannerHtml}
      </div>
    `;
  }

  // =========================================================================
  // THEORY BOUNDARY BUTTERFLY DIAGRAM (Top-Level & Depth-2 Modes)
  // =========================================================================
  function buildButterflySvgHtml(d, mode, analyzedInDir) {
    const leftAll = d.importing_dirs || [];
    const rightAll = d.imported_external_dirs || [];
    const leftLimit = state.showAllLeftBf ? leftAll.length : Math.min(14, leftAll.length);
    const rightLimit = state.showAllRightBf ? rightAll.length : Math.min(14, rightAll.length);
    const leftList = leftAll.slice(0, leftLimit);
    const rightList = rightAll.slice(0, rightLimit);

    const W = 1100;
    const rowH = 26, rowGap = 6;
    const leftH = Math.max(40, leftList.length * (rowH + rowGap) + (leftAll.length > leftList.length ? 22 : 0));
    const rightH = Math.max(40, rightList.length * (rowH + rowGap) + (rightAll.length > rightList.length ? 22 : 0));
    const centerH = 120;
    const H = Math.max(190, leftH + 46, rightH + 46, centerH + 46);

    const maxLeftE = Math.max(1, ...leftList.map(x => x.edges || 1));
    const maxRightE = Math.max(1, ...rightList.map(x => x.edges || 1));

    const lx = 16, lw = 290;
    const cx = 405, cw = 290;
    const rx = 794, rw = 290;
    const cyCenter = Math.round((H - centerH) / 2);

    const ctm = getTheoryMeta(d.dir_key);
    const activeImp = state.importerFilter;

    let leftY = Math.round((H - leftH) / 2) + 12;
    const leftSvg = [];
    const leftRibbons = [];

    if (!leftList.length) {
      leftSvg.push(`<text x="${lx}" y="${Math.round(H / 2)}" font-size="11" fill="#64748b" font-style="italic">No external dependents (apex)</text>`);
    } else {
      leftList.forEach(x => {
        const tm = getTheoryMeta(x.dir);
        const yMid = leftY + rowH / 2;
        const barW = Math.max(6, Math.round(((x.edges || 1) / maxLeftE) * (lw - 16)));
        const sw = 1.4 + (Math.log10(1 + (x.edges || 1)) / Math.log10(1 + maxLeftE)) * 4.5;
        const isSelImp = activeImp === x.dir;
        const dimmed = activeImp && !isSelImp;
        const targetY = cyCenter + 16 + Math.min(centerH - 32, Math.max(0, yMid - cyCenter));
        const dx = cx - (lx + lw);

        leftRibbons.push(
          `<path d="M ${lx + lw} ${yMid} C ${lx + lw + dx * 0.5} ${yMid}, ${cx - dx * 0.5} ${targetY}, ${cx - 2} ${targetY}" fill="none" stroke="#0284c7" stroke-width="${sw.toFixed(2)}" stroke-opacity="${dimmed ? 0.14 : (isSelImp ? 0.95 : 0.58)}" marker-end="url(#bf-arr-down)"/>`
        );
        leftSvg.push(`
          <g class="svg-node" opacity="${dimmed ? 0.45 : 1}" data-bf-imp="${esc(x.dir)}"
             data-tip-title="${esc(x.dir)} \u2192 ${esc(d.dir_key)}"
             data-tip-sub="External consumer theory"
             data-tip-body="Imports ${x.dst_files} interface module${x.dst_files === 1 ? "" : "s"} in ${d.dir_key}. Click to filter module table below.">
            <rect class="svg-node-box" x="${lx}" y="${leftY}" width="${lw}" height="${rowH}" rx="4" fill="${isSelImp ? "#bae6fd" : "#e0f2fe"}" stroke="${isSelImp ? "#0369a1" : "#38bdf8"}" stroke-width="${isSelImp ? 2 : 1.1}"/>
            <rect x="${lx}" y="${leftY}" width="4" height="${rowH}" rx="2" fill="${tm.color}"/>
            <rect x="${lx + 8}" y="${leftY + rowH - 5}" width="${barW}" height="3" rx="1" fill="#0284c7" fill-opacity="0.6"/>
            <text x="${lx + 10}" y="${leftY + 16}" font-size="10.5" font-weight="${isSelImp ? 700 : 600}" fill="#0c4a6e">${esc(shortLabel(x.dir, 34))}</text>
          </g>
        `);
        leftY += rowH + rowGap;
      });
    }

    let rightY = Math.round((H - rightH) / 2) + 12;
    const rightSvg = [];
    const rightRibbons = [];

    if (!rightList.length) {
      rightSvg.push(`<text x="${rx}" y="${Math.round(H / 2)}" font-size="11" fill="#64748b" font-style="italic">No external theory dependencies</text>`);
    } else {
      rightList.forEach(x => {
        const tm = getTheoryMeta(x.dir);
        const yMid = rightY + rowH / 2;
        const barW = Math.max(6, Math.round(((x.edges || 1) / maxRightE) * (rw - 16)));
        const sw = 1.4 + (Math.log10(1 + (x.edges || 1)) / Math.log10(1 + maxRightE)) * 4.5;
        const srcY = cyCenter + 16 + Math.min(centerH - 32, Math.max(0, yMid - cyCenter));
        const dx = rx - (cx + cw);

        rightRibbons.push(
          `<path d="M ${cx + cw} ${srcY} C ${cx + cw + dx * 0.5} ${srcY}, ${rx - dx * 0.5} ${yMid}, ${rx - 2} ${yMid}" fill="none" stroke="#b45309" stroke-width="${sw.toFixed(2)}" stroke-opacity="0.58" marker-end="url(#bf-arr-up)"/>`
        );
        rightSvg.push(`
          <g class="svg-node" data-bf-dep="${esc(x.dir)}"
             data-tip-title="${esc(d.dir_key)} \u2192 ${esc(x.dir)}"
             data-tip-sub="External dependency theory"
             data-tip-body="${d.dir_key} imports ${x.dst_files} interface module${x.dst_files === 1 ? "" : "s"} from ${x.dir}. Click to open ${x.dir}.">
            <rect class="svg-node-box" x="${rx}" y="${rightY}" width="${rw}" height="${rowH}" rx="4" fill="#fef3c7" stroke="#d97706" stroke-width="1.1"/>
            <rect x="${rx}" y="${rightY}" width="4" height="${rowH}" rx="2" fill="${tm.color}"/>
            <rect x="${rx + 8}" y="${rightY + rowH - 5}" width="${barW}" height="3" rx="1" fill="#b45309" fill-opacity="0.6"/>
            <text x="${rx + 10}" y="${rightY + 16}" font-size="10.5" font-weight="600" fill="#78350f">${esc(shortLabel(x.dir, 34))}</text>
          </g>
        `);
        rightY += rowH + rowGap;
      });
    }

    const centerSvg = `
      <g>
        <rect x="${cx}" y="${cyCenter}" width="${cw}" height="${centerH}" rx="6" fill="${ctm.bg}" stroke="${ctm.color}" stroke-width="2.2"/>
        <rect x="${cx}" y="${cyCenter}" width="${cw}" height="34" rx="6" fill="${ctm.color}" fill-opacity="0.12"/>
        <text x="${cx + cw / 2}" y="${cyCenter + 22}" text-anchor="middle" font-size="12.5" font-weight="700" fill="#111111">${esc(shortLabel(d.dir_key, 34))}</text>
        <text x="${cx + cw / 2}" y="${cyCenter + 50}" text-anchor="middle" font-size="10.5" fill="${ctm.color}" font-weight="600">${mode === "top" ? "Top-Level Theory" : "Depth-2 Sub-Theory"}${d.parent_key ? " · " + esc(d.parent_key) : ""}</text>
        <text x="${cx + cw / 2}" y="${cyCenter + 72}" text-anchor="middle" font-size="10.5" fill="#111111">Used by ${leftAll.length} external theor${leftAll.length === 1 ? "y" : "ies"}</text>
        <text x="${cx + cw / 2}" y="${cyCenter + 90}" text-anchor="middle" font-size="10.5" fill="#111111">Depends on ${rightAll.length} external theor${rightAll.length === 1 ? "y" : "ies"}</text>
        <text x="${cx + cw / 2}" y="${cyCenter + 108}" text-anchor="middle" font-size="10" fill="#475569">${analyzedInDir.length} analyzed interface contract${analyzedInDir.length === 1 ? "" : "s"}</text>
      </g>
    `;

    return `
      <div class="graph-panel">
        <div class="graph-head">
          <div class="graph-title-group">
            <h2>Cross-Boundary Theory Flow Butterfly</h2>
            <span class="muted" style="font-size:0.78rem;">Click a left consumer to filter interface modules below; click a right dependency to open that theory.</span>
          </div>
          <div class="graph-controls">
            ${leftAll.length > 14 ? `<button class="btn sm" id="btnToggleLeftBf">${state.showAllLeftBf ? "Show Top 14 Consumers" : `Show All ${leftAll.length} Consumers`}</button>` : ""}
            ${rightAll.length > 14 ? `<button class="btn sm" id="btnToggleRightBf">${state.showAllRightBf ? "Show Top 14 Dependencies" : `Show All ${rightAll.length} Dependencies`}</button>` : ""}
          </div>
        </div>
        <div class="legend-strip">
          <div class="legend-items">
            <span class="legend-item"><span class="swatch down"></span> Used By External Theories (${leftAll.length})</span>
            <span class="legend-item"><span class="swatch up"></span> Depends On External Theories (${rightAll.length})</span>
            <span class="muted">Ribbon thickness &amp; bars indicate relative cross-boundary coupling strength</span>
          </div>
        </div>
        <div class="svg-box">
          <svg viewBox="0 0 ${W} ${H}" width="100%" style="min-width:740px;">
            ${buildArrowMarkers("bf")}
            <text x="${lx}" y="16" font-size="11" font-weight="700" fill="#075985">Used By External Theories (${leftAll.length})</text>
            <text x="${rx}" y="16" font-size="11" font-weight="700" fill="#92400e">Depends On External Theories (${rightAll.length})</text>
            ${leftRibbons.join("")}
            ${rightRibbons.join("")}
            ${leftSvg.join("")}
            ${rightSvg.join("")}
            ${centerSvg}
          </svg>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // ANALYZED DETAIL INSPECTOR (With Ego-Graph + Declaration Composition Bar)
  // =========================================================================
  function renderAnalyzedDetail(relPath, backBtnHtml) {
    const item = ANALYZED_MAP.get(relPath);
    if (!item) return "";
    const tm = getTheoryMeta(item.top_dir);
    const topImps = Object.keys(item.importing_top_dirs || {});
    const d2Imps = Object.keys(item.importing_d2_dirs || {});
    const topDeps = Object.keys(item.imported_top_dirs || {});
    const q = state.query.trim().toLowerCase();

    // Declaration kind histogram
    const kindOrder = ["theorem", "lemma", "def", "structure", "abbrev", "class", "instance", "inductive"];
    const kindCounts = new Map();
    item.all_declarations.forEach(d => {
      kindCounts.set(d.kind, (kindCounts.get(d.kind) || 0) + 1);
    });
    const sortedKinds = Array.from(kindCounts.entries()).sort((a, b) => {
      const ia = kindOrder.indexOf(a[0]);
      const ib = kindOrder.indexOf(b[0]);
      if (ia !== -1 && ib !== -1) return ia - ib;
      if (ia !== -1) return -1;
      if (ib !== -1) return 1;
      return b[1] - a[1] || a[0].localeCompare(b[0]);
    });

    const totalDecls = Math.max(1, item.all_declarations.length);
    const declBarSegs = item.all_declarations.length
      ? sortedKinds.map(([k, cnt]) => {
          const pct = (cnt / totalDecls) * 100;
          const color = DECL_COLORS[k] || DECL_COLORS.other;
          return `<div class="decl-seg" data-decl-kind="${esc(k)}" style="width:${pct.toFixed(2)}%;background:${color};" title="${esc(k)}: ${cnt}"></div>`;
        }).join("")
      : `<div style="width:100%;background:#e2e8f0;"></div>`;

    const declKindPills = `
      <div class="flow-chips" style="margin-bottom:8px;">
        <span class="chip clickable ${state.declKindFilter === "all" ? "active-filter" : ""}" data-decl-kind="all">
          All (${item.all_declarations.length})
        </span>
        ${sortedKinds.map(([k, cnt]) => {
          const color = DECL_COLORS[k] || DECL_COLORS.other;
          const act = state.declKindFilter === k;
          return `
            <span class="chip clickable ${act ? "active-filter" : ""}" data-decl-kind="${esc(k)}">
              <span class="theory-dot" style="background:${color};"></span>${esc(k)} (${cnt})
            </span>
          `;
        }).join("")}
      </div>
    `;

    const decls = item.all_declarations.filter(d => {
      if (state.declKindFilter !== "all" && d.kind !== state.declKindFilter) return false;
      if (q && !d.name.toLowerCase().includes(q) && !d.kind.toLowerCase().includes(q)) return false;
      return true;
    });

    const showInlineEgo = !(state.mode === "analyzed" && state.showDiagram && state.graphView === "ego");

    return `
      <div class="card" style="border-top:3px solid ${tm.color};">
        <div class="detail-header">
          <div>
            ${backBtnHtml || ""}
            <div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
              <span class="badge">${esc(item.role)}</span>
              <span class="badge kind" style="border-color:${tm.border};color:${tm.color};background:${tm.bg};cursor:pointer;" data-jump-d2="${esc(item.depth2_dir)}">${esc(item.depth2_dir)}</span>
              <span class="badge" style="cursor:pointer;" data-jump-top="${esc(item.top_dir)}">${esc(item.top_dir)}</span>
            </div>
            <h2 class="mono" style="margin-top:8px;">
              <a class="filelink" href="${fileUrl(item.rel_path)}" target="_blank">${esc(item.rel_path)}</a>
            </h2>
          </div>
          <div style="text-align:right;font-size:0.82rem;" class="muted">
            Sub-Theory: <b>${esc(item.depth2_dir)}</b>
          </div>
        </div>

        <div class="summary-box">${esc(item.plain_english_summary)}</div>

        ${showInlineEgo ? `
          <div style="border:1px solid #e2e8f0;margin-bottom:14px;">
            <div style="padding:6px 10px;background:#fafafa;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
              <strong style="font-size:0.84rem;">Cross-Boundary Contract Ego-Graph</strong>
              <span class="muted" style="font-size:0.75rem;">Click any connected contract or theory node to navigate</span>
            </div>
            ${buildContractEgoHtml(item, "det")}
          </div>
        ` : ""}

        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(220px, 1fr));gap:12px;margin-bottom:14px;">
          <div>
            <div class="muted" style="font-size:0.78rem;margin-bottom:4px;">Used by Top-Level Theories (${topImps.length})</div>
            <div class="flow-chips">
              ${topImps.map(k => `<span class="chip clickable" data-jump-top="${esc(k)}"><span class="theory-dot" style="background:${getTheoryMeta(k).color};"></span><b>${esc(k)}</b></span>`).join("") || '<span class="muted">None (apex)</span>'}
            </div>
          </div>
          <div>
            <div class="muted" style="font-size:0.78rem;margin-bottom:4px;">Depends on Top-Level Theories (${topDeps.length})</div>
            <div class="flow-chips">
              ${topDeps.map(k => `<span class="chip clickable" data-jump-top="${esc(k)}"><span class="theory-dot" style="background:${getTheoryMeta(k).color};"></span><b>${esc(k)}</b></span>`).join("") || '<span class="muted">None (internal / Mathlib only)</span>'}
            </div>
          </div>
          <div>
            <div class="muted" style="font-size:0.78rem;margin-bottom:4px;">Used by Depth-2 Sub-Theories (${d2Imps.length})</div>
            <div class="flow-chips">
              ${d2Imps.slice(0, 10).map(k => `<span class="chip clickable" data-jump-d2="${esc(k)}"><b>${esc(k)}</b></span>`).join("") || '<span class="muted">None</span>'}
              ${d2Imps.length > 10 ? `<span class="chip muted">+${d2Imps.length - 10} more</span>` : ""}
            </div>
          </div>
        </div>

        <h3>Key Exported Mathematical APIs (${item.key_exports.length})</h3>
        ${item.key_exports.length ? `
          <div class="table-wrap" style="max-height:320px;margin-bottom:14px;">
            <table>
              <thead><tr><th>Kind</th><th>Declaration</th><th>Line</th><th>Plain-English Mathematical Meaning</th></tr></thead>
              <tbody>
                ${item.key_exports.map(k => `
                  <tr>
                    <td><span class="badge kind" style="color:${DECL_COLORS[k.kind] || DECL_COLORS.other};">${esc(k.kind)}</span></td>
                    <td class="mono"><a class="filelink" href="${fileUrl(item.rel_path, k.line_no)}" target="_blank">${esc(k.name)}</a></td>
                    <td class="mono">L${k.line_no}</td>
                    <td>${esc(k.summary)}</td>
                  </tr>
                `).join("")}
              </tbody>
            </table>
          </div>
        ` : `<p class="muted">This file exports via Lean imports / commands rather than local named theorem/def declarations.</p>`}

        <h3>Declaration Breakdown &amp; Index (${decls.length} / ${item.all_declarations.length})</h3>
        <div class="decl-bar-wrap">
          <div class="decl-stacked-bar">${declBarSegs}</div>
          ${declKindPills}
        </div>
        <div class="table-wrap" style="max-height:300px;">
          <table>
            <thead><tr><th>Line</th><th>Kind</th><th>Name</th></tr></thead>
            <tbody>
              ${decls.map(d => `
                <tr>
                  <td class="mono"><a class="filelink" href="${fileUrl(item.rel_path, d.line_no)}" target="_blank">L${d.line_no}</a></td>
                  <td><span class="badge kind" style="color:${DECL_COLORS[d.kind] || DECL_COLORS.other};">${esc(d.kind)}</span></td>
                  <td class="mono">${esc(d.name)}</td>
                </tr>
              `).join("") || `<tr><td colspan="3" class="muted">No declarations match the current filter.</td></tr>`}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  function renderGlobalSearch() {
    const q = state.query.trim().toLowerCase();
    const matchedDirs = DATA.depth2_dirs.filter(d => !q || d.dir_key.toLowerCase().includes(q)).slice(0, 30);
    const matchedFiles = [];
    const seen = new Set();
    for (const d of DATA.top_dirs) {
      for (const f of d.interface_files) {
        if (seen.has(f.p)) continue;
        const an = ANALYZED_MAP.get(f.p);
        const hit = !q || f.p.toLowerCase().includes(q) || (an && (
          an.plain_english_summary.toLowerCase().includes(q) ||
          an.all_declarations.some(x => x.name.toLowerCase().includes(q))
        ));
        if (hit) {
          seen.add(f.p);
          matchedFiles.push(f);
        }
      }
    }
    matchedFiles.sort((a, b) => b.a - a.a || b.e - a.e);

    const mainEl = document.getElementById("mainPane");
    mainEl.innerHTML = `
      ${state.selectedFile && ANALYZED_MAP.has(state.selectedFile) ? renderAnalyzedDetail(state.selectedFile, "") : ""}
      <div class="card">
        <h2>Global Cross-Boundary Search Results ${q ? 'for "' + esc(state.query) + '"' : "(All Top Interfaces)"}</h2>
        <p class="muted">Matched ${matchedDirs.length} depth-2 sub-theories (showing up to 30) and ${matchedFiles.length} cross-boundary interface modules (showing top 80).</p>
        <div class="flow-chips" style="margin-bottom:14px;">
          ${matchedDirs.map(d => `<span class="chip clickable" data-jump-d2="${esc(d.dir_key)}"><span class="theory-dot" style="background:${getTheoryMeta(d.dir_key).color};"></span><b>${esc(d.dir_key)}</b></span>`).join("")}
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Interface Module</th><th>Sub-Theory</th><th>Used By</th><th>Status</th></tr></thead>
            <tbody>
              ${matchedFiles.slice(0, 80).map(f => {
                const eds = Object.keys(f.ed || {});
                return `
                  <tr class="${f.a ? "clickable" : ""}" data-openan="${f.a ? esc(f.p) : ""}">
                    <td class="mono"><a class="filelink" href="${fileUrl(f.p)}" target="_blank">${esc(f.p)}</a></td>
                    <td><span class="chip clickable" data-jump-d2="${esc(f.d2)}"><span class="theory-dot" style="background:${getTheoryMeta(f.d2).color};"></span>${esc(f.d2)}</span></td>
                    <td>${eds.slice(0, 3).map(k => `<span class="badge" style="margin-right:3px;">${esc(k)}</span>`).join("")}${eds.length > 3 ? ` +${eds.length - 3}` : ""}</td>
                    <td>${f.a ? '<span class="badge">Analyzed API</span>' : '<span class="muted">Indexed</span>'}</td>
                  </tr>
                `;
              }).join("")}
            </tbody>
          </table>
        </div>
      </div>
    `;
    bindMainInteractions(mainEl);
  }

  function bindMainInteractions(container) {
    bindTooltips(container);

    container.querySelectorAll("[data-select-file]").forEach(el => {
      el.addEventListener("click", (ev) => {
        if (window._dagJustDragged) return;
        ev.stopPropagation();
        selectContract(el.getAttribute("data-select-file"));
      });
    });

    container.querySelectorAll("[data-open-url]").forEach(el => {
      el.addEventListener("click", (ev) => {
        ev.stopPropagation();
        window.open(el.getAttribute("data-open-url"), "_blank");
      });
    });

    container.querySelectorAll("[data-jump-top]").forEach(el => {
      el.addEventListener("click", (ev) => {
        if (window._dagJustDragged) return;
        ev.stopPropagation();
        jumpToTheory("top", el.getAttribute("data-jump-top"), "");
      });
    });

    container.querySelectorAll("[data-jump-d2]").forEach(el => {
      el.addEventListener("click", (ev) => {
        if (window._dagJustDragged) return;
        ev.stopPropagation();
        jumpToTheory("d2", el.getAttribute("data-jump-d2"), "");
      });
    });

    container.querySelectorAll("[data-matrix-src]").forEach(el => {
      el.addEventListener("click", () => {
        const src = el.getAttribute("data-matrix-src");
        const dst = el.getAttribute("data-matrix-dst");
        jumpToTheory("top", dst, src);
      });
    });

    container.querySelectorAll("[data-openan]").forEach(el => {
      const p = el.getAttribute("data-openan");
      if (p) {
        el.addEventListener("click", (ev) => {
          if (ev.target.tagName === "A" || ev.target.closest("[data-jump-d2]")) return;
          selectContract(p);
        });
      }
    });

    container.querySelectorAll("[data-decl-kind]").forEach(el => {
      el.addEventListener("click", () => {
        const k = el.getAttribute("data-decl-kind");
        state.declKindFilter = (state.declKindFilter === k && k !== "all") ? "all" : k;
        renderMain();
      });
    });

    // Graph Panel Controls
    container.querySelectorAll("[data-gview]").forEach(el => {
      el.onclick = () => { state.graphView = el.getAttribute("data-gview"); state.showDiagram = true; renderMain(); };
    });
    container.querySelectorAll("[data-hop]").forEach(el => {
      el.onclick = () => { state.hopMode = el.getAttribute("data-hop"); renderMain(); };
    });
    const chkCone = document.getElementById("chkConeOnly");
    if (chkCone) {
      chkCone.onchange = (e) => { state.coneOnly = e.target.checked; renderMain(); };
    }
    const btnToggle = document.getElementById("btnToggleDiagram");
    if (btnToggle) {
      btnToggle.onclick = () => { state.showDiagram = !state.showDiagram; renderMain(); };
    }
    const btnZIn = document.getElementById("btnDagZoomIn");
    const btnZOut = document.getElementById("btnDagZoomOut");
    const btnZReset = document.getElementById("btnDagZoomReset");
    if (btnZIn) btnZIn.onclick = () => { state.dagZoom = Math.min(2.2, +(state.dagZoom + 0.15).toFixed(2)); renderMain(); };
    if (btnZOut) btnZOut.onclick = () => { state.dagZoom = Math.max(0.55, +(state.dagZoom - 0.15).toFixed(2)); renderMain(); };
    if (btnZReset) btnZReset.onclick = () => { state.dagZoom = 1.0; renderMain(); };

    // Drag-to-pan on DAG viewport
    const dagScroll = document.getElementById("dagScroll");
    if (dagScroll) {
      dagScroll.addEventListener("mousedown", (e) => {
        if (e.button !== 0) return;
        window._dagJustDragged = false;
        activeDagDrag = {
          scrollEl: dagScroll,
          startX: e.clientX,
          startY: e.clientY,
          scrollL: dagScroll.scrollLeft,
          scrollT: dagScroll.scrollTop
        };
        dagScroll.classList.add("grabbing");
      });
    }
  }

  function renderMain() {
    hideTooltip();
    const mainEl = document.getElementById("mainPane");
    if (state.mode === "analyzed") {
      mainEl.innerHTML = renderAnalyzedGraphPanel() + renderAnalyzedDetail(state.selectedFile, "");
      bindMainInteractions(mainEl);
      return;
    }
    if (state.mode === "search") {
      renderGlobalSearch();
      return;
    }

    const srcList = state.mode === "top" ? DATA.top_dirs : DATA.depth2_dirs;
    const d = srcList.find(x => x.dir_key === state.selectedDir) || srcList[0];
    if (!d) {
      mainEl.innerHTML = `<div class="card">No directory selected.</div>`;
      return;
    }

    const q = state.query.trim().toLowerCase();
    const analyzedInDir = DATA.analyzed_interfaces.filter(x =>
      (state.mode === "top" ? x.top_dir : x.depth2_dir) === d.dir_key
    );
    const activeAn = state.selectedFile && analyzedInDir.some(x => x.rel_path === state.selectedFile)
      ? state.selectedFile : null;

    const tm = getTheoryMeta(d.dir_key);
    const maxModuleConsumers = Math.max(1, ...d.interface_files.map(f => Object.keys(f.ed || {}).length));

    mainEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
        <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
          <span class="theory-dot" style="background:${tm.color};width:12px;height:12px;"></span>
          <h2 style="margin:0;">${esc(d.dir_key)}</h2>
          <span class="badge">${state.mode === "top" ? "Top-Level Theory" : "Depth-2 Sub-Theory"}${d.parent_key ? " · parent: " + esc(d.parent_key) : ""}</span>
        </div>
      </div>

      ${buildButterflySvgHtml(d, state.mode, analyzedInDir)}

      ${activeAn ? renderAnalyzedDetail(activeAn, `<button class="btn" id="closeAnBtn">&larr; Back to ${esc(d.dir_key)} summary</button>`) : ""}

      ${analyzedInDir.length ? `
        <div class="card">
          <h3>Analyzed Mathematical Interfaces in ${esc(d.dir_key)} (${analyzedInDir.length})</h3>
          <div class="flow-chips">
            ${analyzedInDir.map(x => `
              <button class="btn ${activeAn === x.rel_path ? "active" : ""}" data-pickan="${esc(x.rel_path)}">
                <span class="mono">${esc(x.rel_path.split("/").pop())}</span>
                <span class="badge">${esc(x.role)}</span>
              </button>
            `).join("")}
          </div>
        </div>
      ` : ""}

      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
          <h3 style="margin:0;">Cross-Boundary Interface Modules (<span id="shownCount">showing 0</span>)</h3>
          <input id="localFileFilter" type="search" value="${esc(state.fileFilter)}" placeholder="Filter modules inside this theory..." style="min-width:260px;">
        </div>
        ${state.importerFilter ? `
          <div class="filter-banner">
            <span>Showing modules in <b>${esc(d.dir_key)}</b> imported by external consumer <b>${esc(state.importerFilter)}</b></span>
            <div style="display:flex;gap:6px;">
              <button class="btn sm" id="btnOpenImporter">&nearr; Open ${esc(shortLabel(state.importerFilter, 26))}</button>
              <button class="btn sm" id="btnClearImporter">Clear Consumer Filter</button>
            </div>
          </div>
        ` : ""}
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Interface Module</th>
                <th>Used By External Theories</th>
                <th>API</th>
              </tr>
            </thead>
            <tbody id="ifaceTbody"></tbody>
          </table>
        </div>
      </div>
    `;

    function renderIfaceRows() {
      const fq = state.fileFilter.trim().toLowerCase();
      const impF = state.importerFilter;
      const rows = d.interface_files.filter(f => {
        if (impF && !(f.ed && Object.prototype.hasOwnProperty.call(f.ed, impF))) return false;
        if (fq && !f.p.toLowerCase().includes(fq)) return false;
        if (q && !d.dir_key.toLowerCase().includes(q) && !f.p.toLowerCase().includes(q)) return false;
        return true;
      });
      const sc = document.getElementById("shownCount");
      if (sc) sc.textContent = `showing ${rows.length}`;
      const tb = document.getElementById("ifaceTbody");
      if (!tb) return;
      tb.innerHTML = rows.map((f, idx) => {
        const eds = f.ed || {};
        const edKeys = Object.keys(eds);
        const reachPct = Math.max(5, Math.round((edKeys.length / maxModuleConsumers) * 100));
        const pills = edKeys.slice(0, 4).map(k => {
          const ktm = getTheoryMeta(k);
          const isAct = state.importerFilter === k;
          return `<span class="chip clickable ${isAct ? "active-filter" : ""}" style="padding:1px 6px;font-size:0.73rem;" data-row-imp="${esc(k)}"><span class="theory-dot" style="background:${ktm.color};width:7px;height:7px;"></span>${esc(k)}</span>`;
        }).join(" ");
        const moreEd = edKeys.length > 4 ? ` <span class="muted" style="font-size:0.74rem;">+${edKeys.length - 4}</span>` : "";
        return `
          <tr class="${f.a ? "clickable" : ""}" data-pickan="${f.a ? esc(f.p) : ""}">
            <td class="muted">${idx + 1}</td>
            <td class="mono"><a class="filelink" href="${fileUrl(f.p)}" target="_blank">${esc(f.p)}</a></td>
            <td>
              <div style="display:flex;flex-wrap:wrap;gap:4px;align-items:center;">${pills}${moreEd}</div>
              <div class="reach-bar" title="Used by ${edKeys.length} external theor${edKeys.length === 1 ? "y" : "ies"}"><div class="reach-fill" style="width:${reachPct}%;"></div></div>
            </td>
            <td>${f.a ? '<span class="badge">View Summary</span>' : '<span class="muted">-</span>'}</td>
          </tr>
        `;
      }).join("") || `<tr><td colspan="4" class="muted">No cross-boundary interface modules match the active filters.</td></tr>`;

      tb.querySelectorAll("[data-pickan]").forEach(el => {
        if (el.dataset.pickan) {
          el.onclick = (ev) => {
            if (ev.target.tagName === "A" || ev.target.closest("[data-row-imp]")) return;
            state.selectedFile = el.dataset.pickan;
            state.declKindFilter = "all";
            renderMain();
          };
        }
      });
      tb.querySelectorAll("[data-row-imp]").forEach(el => {
        el.onclick = (ev) => {
          ev.stopPropagation();
          const imp = el.getAttribute("data-row-imp");
          state.importerFilter = (state.importerFilter === imp) ? "" : imp;
          renderMain();
        };
      });
    }

    renderIfaceRows();
    bindMainInteractions(mainEl);

    const lf = document.getElementById("localFileFilter");
    if (lf) {
      lf.oninput = (e) => { state.fileFilter = e.target.value; renderIfaceRows(); };
    }
    mainEl.querySelectorAll("[data-bf-imp]").forEach(el => {
      el.addEventListener("click", () => {
        const imp = el.getAttribute("data-bf-imp");
        state.importerFilter = (state.importerFilter === imp) ? "" : imp;
        renderMain();
      });
    });
    mainEl.querySelectorAll("[data-bf-dep]").forEach(el => {
      el.addEventListener("click", () => {
        jumpToTheory(state.mode, el.getAttribute("data-bf-dep"), "");
      });
    });
    const btnToggleLeft = document.getElementById("btnToggleLeftBf");
    if (btnToggleLeft) btnToggleLeft.onclick = () => { state.showAllLeftBf = !state.showAllLeftBf; renderMain(); };
    const btnToggleRight = document.getElementById("btnToggleRightBf");
    if (btnToggleRight) btnToggleRight.onclick = () => { state.showAllRightBf = !state.showAllRightBf; renderMain(); };

    const btnOpenImp = document.getElementById("btnOpenImporter");
    if (btnOpenImp) btnOpenImp.onclick = () => jumpToTheory(state.mode, state.importerFilter, "");
    const btnClrImp = document.getElementById("btnClearImporter");
    if (btnClrImp) btnClrImp.onclick = () => { state.importerFilter = ""; renderMain(); };

    mainEl.querySelectorAll("[data-pickan]").forEach(el => {
      if (el.dataset.pickan) {
        el.onclick = (ev) => {
          if (ev.target.tagName === "A") return;
          state.selectedFile = el.dataset.pickan;
          state.declKindFilter = "all";
          renderMain();
        };
      }
    });
    const cb = document.getElementById("closeAnBtn");
    if (cb) cb.onclick = () => { state.selectedFile = null; renderMain(); };
  }

  function render() {
    syncTabs();
    renderSidebar();
    renderMain();
  }

  function setupStaticListeners() {
    document.querySelectorAll(".tab").forEach(btn => {
      btn.onclick = () => {
        state.mode = btn.dataset.mode;
        state.importerFilter = "";
        state.fileFilter = "";
        if (DATA && state.mode === "analyzed" && !ANALYZED_MAP.has(state.selectedFile)) {
          state.selectedFile = DATA.analyzed_interfaces[0] ? DATA.analyzed_interfaces[0].rel_path : null;
        }
        if (DATA) render();
      };
    });

    document.getElementById("globalSearch").addEventListener("input", (e) => {
      state.query = e.target.value;
      if (DATA) render();
    });

    document.getElementById("sortSelect").addEventListener("change", (e) => {
      state.sort = e.target.value;
      if (DATA) renderSidebar();
    });

    window.addEventListener("mousemove", (e) => {
      if (!activeDagDrag) return;
      const dx = e.clientX - activeDagDrag.startX;
      const dy = e.clientY - activeDagDrag.startY;
      if (Math.hypot(dx, dy) > 4) window._dagJustDragged = true;
      activeDagDrag.scrollEl.scrollLeft = activeDagDrag.scrollL - dx;
      activeDagDrag.scrollEl.scrollTop = activeDagDrag.scrollT - dy;
    });

    window.addEventListener("mouseup", () => {
      if (!activeDagDrag) return;
      activeDagDrag.scrollEl.classList.remove("grabbing");
      activeDagDrag = null;
      setTimeout(() => { window._dagJustDragged = false; }, 50);
    });
  }

  function prepareInterfaces(data) {
    const analyzedMap = new Map(data.analyzed_interfaces.map(x => [x.rel_path, x]));
    const topDirMap = new Map(data.top_dirs.map(x => [x.dir_key, x]));
    const d2DirMap = new Map(data.depth2_dirs.map(x => [x.dir_key, x]));
    const theoryOrder = [
      ...CANONICAL_THEORY_ORDER.filter(t => topDirMap.has(t)),
      ...data.top_dirs.map(d => d.dir_key).filter(t => !CANONICAL_THEORY_ORDER.includes(t))
    ];
    return { data, analyzedMap, topDirMap, d2DirMap, theoryOrder };
  }

  function applyInterfaces(prepared, ver) {
    hideTooltip();
    activeDagDrag = null;
    DATA = prepared.data;
    ANALYZED_MAP = prepared.analyzedMap;
    TOP_DIR_MAP = prepared.topDirMap;
    D2_DIR_MAP = prepared.d2DirMap;
    THEORY_ORDER = prepared.theoryOrder;

    const curVer = ver || (window.RHVersion && RHVersion.current);
    if (curVer) {
      document.getElementById("ifaceSubtitle").textContent =
        `Lean 4 (${curVer.label}) — Cross-theory contract architecture, boundary flows & Lean APIs`;
    }

    document.getElementById("cntTop").textContent = DATA.top_dirs.length;
    document.getElementById("cntD2").textContent = DATA.depth2_dirs.length;
    document.getElementById("cntAn").textContent = DATA.analyzed_interfaces.length;
    document.getElementById("topStats").innerHTML = [
      `<span class="pill">Top-Level Theories: <b>${DATA.top_dirs.length}</b></span>`,
      `<span class="pill">Sub-Theories: <b>${DATA.depth2_dirs.length}</b></span>`,
      `<span class="pill">Analyzed Mathematical Interfaces: <b>${DATA.analyzed_interfaces.length}</b></span>`
    ].join("");

    if (state.mode === "top" && !TOP_DIR_MAP.has(state.selectedDir)) {
      state.selectedDir = TOP_DIR_MAP.has("Development") ? "Development" : (DATA.top_dirs[0] ? DATA.top_dirs[0].dir_key : "");
    } else if (state.mode === "d2" && !D2_DIR_MAP.has(state.selectedDir)) {
      state.selectedDir = DATA.depth2_dirs[0] ? DATA.depth2_dirs[0].dir_key : "";
    } else if (!TOP_DIR_MAP.has(state.selectedDir) && !D2_DIR_MAP.has(state.selectedDir)) {
      state.selectedDir = TOP_DIR_MAP.has("Development") ? "Development" : (DATA.top_dirs[0] ? DATA.top_dirs[0].dir_key : "");
    }

    if (!state.selectedFile || !ANALYZED_MAP.has(state.selectedFile)) {
      state.selectedFile = DATA.analyzed_interfaces[0] ? DATA.analyzed_interfaces[0].rel_path : null;
    }

    state.importerFilter = "";
    state.fileFilter = "";
    state.declKindFilter = "all";
    render();
  }

  setupStaticListeners();
  RHVersion.loadDataScript("interfaces/interface_browser_data.js", "__INTERFACES_DATA__", applyInterfaces, {
    prepare: prepareInterfaces
  });
})();
</script>
</body>
</html>
"""


def main() -> None:
    global DB_PATH, META_PATH, LEAN_SRC, OUT_DIR, CURATED_PATH, JSON_OUT, REPORT_OUT, HTML_OUT
    parser = argparse.ArgumentParser(description="Extract cross-boundary directory interfaces")
    parser.add_argument("--src-dir", type=Path, default=LEAN_SRC)
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--meta-path", type=Path, default=META_PATH)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--curated-path", type=Path, default=CURATED_PATH)
    parser.add_argument("--github-blob-base", type=str, default="")
    parser.add_argument("--version-label", type=str, default="")
    parser.add_argument("--rel-src-label", type=str, default="src/")
    parser.add_argument("--write-html", action="store_true", help="Write canonical interface_browser.html")
    args = parser.parse_args()

    LEAN_SRC = args.src_dir
    DB_PATH = args.db_path
    META_PATH = args.meta_path
    OUT_DIR = args.out_dir
    CURATED_PATH = args.curated_path
    JSON_OUT = OUT_DIR / "interfaces.json"
    REPORT_OUT = OUT_DIR / "INTERFACES_REPORT.md"

    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(CURATED_PATH, "r", encoding="utf-8") as f:
        curated_raw: dict[str, dict] = json.load(f)

    with open(META_PATH, "r", encoding="utf-8") as f:
        meta_raw = json.load(f)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    curated, skipped_curated = resolve_curated_entries(conn, curated_raw)
    analyzed_set = set(curated.keys())

    top_dirs, top_matrix = compute_level_interfaces(conn, 1, "top_dir", analyzed_set)
    d2_dirs, d2_matrix = compute_level_interfaces(conn, 2, "depth2_dir", analyzed_set)

    top_map = {d["dir_key"]: d for d in top_dirs}
    d2_map = {d["dir_key"]: d for d in d2_dirs}

    analyzed_list = extract_analyzed_interfaces(
        conn, curated, top_map, d2_map, github_blob_base=args.github_blob_base
    )
    conn.close()

    total_top_iface_files = sum(d["interface_files_count"] for d in top_dirs)
    total_d2_iface_files = sum(d["interface_files_count"] for d in d2_dirs)
    total_top_ext_edges = sum(d["total_ext_imports"] for d in top_dirs)
    total_d2_ext_edges = sum(d["total_ext_imports"] for d in d2_dirs)
    reach_total = int(meta_raw.get("reachable_files", meta_raw["total_files"]))
    reach_edges = int(meta_raw.get("reachable_internal_edges", meta_raw["total_internal_edges"]))
    reach_lines = int(meta_raw.get("reachable_lines", meta_raw["total_lines"]))

    full_export = {
        "meta": {
            "version_label": args.version_label,
            "total_files": meta_raw["total_files"],
            "reachable_files": reach_total,
            "total_lines": reach_lines,
            "total_internal_edges": reach_edges,
            "is_dag": meta_raw["is_dag"],
            "top_dir_count": len(top_dirs),
            "depth2_dir_count": len(d2_dirs),
            "top_dir_interface_files": total_top_iface_files,
            "top_dir_overall_compression_ratio": round(total_top_iface_files / reach_total, 6) if reach_total else 0.0,
            "depth2_dir_interface_files": total_d2_iface_files,
            "depth2_dir_overall_compression_ratio": round(total_d2_iface_files / reach_total, 6) if reach_total else 0.0,
            "total_cross_top_edges": total_top_ext_edges,
            "total_cross_d2_edges": total_d2_ext_edges,
            "analyzed_interfaces_count": len(analyzed_list),
        },
        "top_dir_matrix": top_matrix,
        "depth2_dir_matrix": d2_matrix,
        "top_dirs": top_dirs,
        "depth2_dirs": d2_dirs,
        "analyzed_interfaces": analyzed_list,
    }

    with open(JSON_OUT, "w", encoding="utf-8") as f:
        json.dump(full_export, f, indent=2, ensure_ascii=False)

    report_md = render_report(
        full_export,
        version_label=args.version_label,
        rel_src_label=args.rel_src_label,
        skipped_curated=skipped_curated,
    )
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.write(report_md)

    browser_payload = build_browser_payload(full_export)
    js_blob = json.dumps(browser_payload, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    data_js_out = OUT_DIR / "interface_browser_data.js"
    data_js_out.write_text(f"window.__INTERFACES_DATA__ = {js_blob};\n", encoding="utf-8")

    if args.write_html:
        html_text = render_html(browser_payload)
        with open(HTML_OUT, "w", encoding="utf-8") as f:
            f.write(html_text)
        print(f"Wrote canonical HTML {HTML_OUT} ({HTML_OUT.stat().st_size:,} bytes)")

    json_mb = JSON_OUT.stat().st_size / (1024 * 1024)
    rep_kb = REPORT_OUT.stat().st_size / 1024
    js_mb = data_js_out.stat().st_size / (1024 * 1024)
    print(
        f"Generated {JSON_OUT} ({json_mb:.2f} MiB), {data_js_out} ({js_mb:.2f} MiB), "
        f"{REPORT_OUT} ({rep_kb:.1f} KiB) in {time.time() - t0:.2f}s"
    )
    print(
        f"Summary: {len(top_dirs)} top_dirs ({total_top_iface_files} iface files), "
        f"{len(d2_dirs)} depth2_dirs ({total_d2_iface_files} iface files), "
        f"{len(analyzed_list)} analyzed APIs ({len(skipped_curated)} baseline curated absent)."
    )


if __name__ == "__main__":
    main()
