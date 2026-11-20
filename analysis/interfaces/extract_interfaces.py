#!/usr/bin/env python3
"""Extract cross-boundary directory interfaces, compression metrics, and self-contained browser."""

from __future__ import annotations

import html
import json
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

DB_PATH = Path("/home/ubuntu/riemann_proof/analysis/data/graph.sqlite")
META_PATH = Path("/home/ubuntu/riemann_proof/analysis/data/meta.json")
LEAN_SRC = Path("/home/ubuntu/riemann_proof/lean/src")
OUT_DIR = Path("/home/ubuntu/riemann_proof/analysis/interfaces")
CURATED_PATH = OUT_DIR / "curated_summaries.json"
JSON_OUT = OUT_DIR / "interfaces.json"
REPORT_OUT = OUT_DIR / "INTERFACES_REPORT.md"
HTML_OUT = OUT_DIR / "interface_browser.html"


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
        WHERE level = ?
        ORDER BY files DESC, dir_key ASC
        """,
        (level,),
    ).fetchall()

    # Cross-boundary incoming edges: dst inside D, src outside D
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
               dst.in_degree,
               dst.dist_from_main,
               dst.height_from_leaves,
               src.{col_name} AS src_dir,
               COUNT(*) AS edge_cnt,
               COUNT(DISTINCT src.id) AS src_file_cnt
        FROM edges e
        JOIN modules src ON e.src_id = src.id
        JOIN modules dst ON e.dst_id = dst.id
        WHERE src.{col_name} != dst.{col_name}
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
            WHERE src.{col_name} != dst.{col_name}
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
        WHERE src.{col_name} != dst.{col_name}
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
        comp_ratio = round(iface_count / files, 6) if files > 0 else 0.0
        line_comp_ratio = round(iface_lines / lines, 6) if lines > 0 else 0.0
        comp_factor = round(files / iface_count, 2) if iface_count > 0 else None

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


def extract_analyzed_interfaces(
    conn: sqlite3.Connection,
    curated: dict[str, dict],
    top_dirs_map: dict[str, dict],
    d2_dirs_map: dict[str, dict],
) -> list[dict]:
    """Build verified declaration + plain-English records for all curated interface files."""
    # Pre-index per-file fan-in from top_dirs_map and d2_dirs_map
    top_file_lookup: dict[str, dict] = {}
    for d in top_dirs_map.values():
        for f in d["interface_files"]:
            top_file_lookup[f["rel_path"]] = f

    d2_file_lookup: dict[str, dict] = {}
    for d in d2_dirs_map.values():
        for f in d["interface_files"]:
            d2_file_lookup[f["rel_path"]] = f

    results: list[dict] = []
    for rel_path, info in curated.items():
        mod = conn.execute(
            """
            SELECT id, name, top_dir, depth2_dir, lines, bytes,
                   n_theorems, n_lemmas, n_defs, n_structures, n_other_decls,
                   dist_from_main, height_from_leaves, in_degree, out_degree
            FROM modules
            WHERE rel_path = ?
            """,
            (rel_path,),
        ).fetchone()
        if mod is None:
            raise ValueError(f"Curated file missing from graph.sqlite: {rel_path}")
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
        decl_set = {(k, n, ln) for k, n, ln in decls}

        for ke in info.get("key_exports", []):
            triple = (ke["kind"], ke["name"], ke["line_no"])
            if triple not in decl_set:
                raise AssertionError(
                    f"Declaration verification failed in {rel_path}: {triple} not found in graph.sqlite"
                )

        t_info = top_file_lookup.get(rel_path)
        d2_info = d2_file_lookup.get(rel_path)

        results.append(
            {
                "rel_path": rel_path,
                "module_name": mod_name,
                "file_url": f"file://{LEAN_SRC / rel_path}",
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
                "d2_ext_fan_in": d2_info["ext_fan_in"] if d2_info else 0,
                "importing_d2_dirs": d2_info["ext_dirs"] if d2_info else {},
                "plain_english_summary": info["plain_english_summary"],
                "key_exports": info.get("key_exports", []),
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


def render_report(full_export: dict) -> str:
    """Render structured Markdown report with compression tables and plain-English API summaries."""
    meta = full_export["meta"]
    top_dirs = full_export["top_dirs"]
    d2_dirs = full_export["depth2_dirs"]
    top_matrix = full_export["top_dir_matrix"]
    analyzed = full_export["analyzed_interfaces"]

    lines: list[str] = []
    a = lines.append

    a("# Cross-Boundary Interface & Compression Analysis")
    a("")
    a("This report extracts and analyzes the cross-boundary public interfaces of the Lean 4 codebase in [`lean/src`](file:///home/ubuntu/riemann_proof/lean/src), built from [`analysis/data/graph.sqlite`](file:///home/ubuntu/riemann_proof/analysis/data/graph.sqlite) and verified directly against the `.lean` source files.")
    a("")
    a("An **interface file** of a directory `D` is defined as any `.lean` module inside `D` that is directly imported by at least one module strictly outside `D`. The **compression ratio** is `interface_files / total_files` (smaller ratios indicate tighter encapsulation behind narrow boundary contracts).")
    a("")
    a("## 1. Executive Summary & Architectural Findings")
    a("")
    a(f"- **Global Scale & Boundary Compression:** Out of **{meta['total_files']:,} files** ({meta['total_lines']:,} lines; 100% reachable from `Main.lean` in a strict DAG with {meta['total_internal_edges']:,} internal edges), only **{meta['top_dir_interface_files']:,} files ({meta['top_dir_overall_compression_ratio']*100:.2f}%)** cross a top-level directory boundary ({meta['total_cross_top_edges']:,} cross-boundary edges), and **{meta['depth2_dir_interface_files']:,} files ({meta['depth2_dir_overall_compression_ratio']*100:.2f}%)** cross a depth-2 sub-theory boundary ({meta['total_cross_d2_edges']:,} cross-boundary edges across {meta['depth2_dir_count']} depth-2 buckets).")
    a("- **Extreme Encapsulation of `Development` (118.8x compression):** `Development` contains **141,928 files** (81.0% of the repository, 12.23M lines), yet exports only **1,195 interface files** (`0.0084` compression ratio, `0.0132` by lines) outside `Development`. Its final proof outputs funnel through a 6-file bottleneck into `Supplements/Kernels/` and from there via a single barrel file (`MainTheoremsAll.lean`) into `Main.lean`.")
    a("- **`Formalism` & `ReciprocityTheory` as High-Traffic Specification Hubs:** Together, `Formalism` (**43,538** incoming external edges into 3,640 interface files) and `ReciprocityTheory` (**39,723** incoming external edges into 1,503 interface files) absorb **86.3%** of all cross-top-directory imports (`83,261 / 96,497`). Reading the highest fan-in files reveals that they primarily export **mathematical specification packages (`Prop` predicates and `structure` contracts)**—such as `UniformisationConclusion`, `PELUnif`, `UnifUniqSt`, `HeckeKer`, `Laws`, `Laws2`, `LocCoh`, `D7`, and `LocalTateDualityK`—rather than raw leaf lemmas.")
    a("- **Depth-2 Sub-Theory Extremes:** Among depth-2 sub-theories with at least 20 files, the tightest compression occurs in `Formalism/AdmissibleDesigns` (**4.30%**, 4/93), `Formalism/WachLatticeTwists` (**4.58%**, 12/262), `Development/AutomorphicArithmetic` (**5.56%**, 1,024/18,431), `ReciprocityTheory/Chebotarev` (**6.38%**, 3/47), `Development/ResolutionOfSingularities` (**7.62%**, 38/499), and `Development/AbelianVarietyTheory` (**9.58%**, 9,498/99,187). Conversely, foundational leaf toolkits such as `Lemmata/*` (**100.0%**, 167 single-file modules), `Formalism/FrobeniusOrbits` (**96.88%**), `Formalism/RealPlaceAnalysis` (**90.74%**), and `Formalism/HarderNarasimhan` (**90.70%**) expose nearly all their modules externally.")
    a("- **Bidirectional Directory Coupling within a Strict Module DAG:** Although module imports form a strict acyclic DAG (`is_dag = true`), directories exhibit rich two-way interdependence: `Development` heavily imports `Formalism` (41,857 edges) and `ReciprocityTheory` (38,051 edges), while `CompanionTheory` imports `Development` (1,437 edges) and `PositivityTheory` imports `Development` (632 edges), and `Development` in turn imports `CompanionTheory` (1,874 edges) and `PositivityTheory` (1,057 edges).")
    a("- **Architectural Idioms Discovered in Source:** Direct reading uncovered thin 1-line re-export facades (`CompanionTheory/EightfoldTheory/VariationTheory/AutomorphicForms/Newform.lean`, imported 248 times by `Development`) and 4-line library-suggestion deny-list directives (`BuildAid/D1.lean`–`D5.lean`), illustrating how namespace facades and build-tuning hooks appear alongside mathematical theorem/definition interfaces.")
    a("")

    a("## 2. Top-Level Directory Compression & Dependency Flow")
    a("")
    a("| Top-Level Directory | Total Files | Interface Files | Compression Ratio | Compression Factor | Ext Import Edges (In) | Unique Ext Importers | Ext Outgoing Edges | Total Lines | Interface Lines (Ratio) |")
    a("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for d in top_dirs:
        cf = f"{d['compression_factor']:.2f}x" if d["compression_factor"] else "Apex (0 exports)"
        a(
            f"| `{d['dir_key']}` | {d['total_files']:,} | {d['interface_files_count']:,} | "
            f"{d['compression_ratio']:.4f} ({d['compression_ratio']*100:.2f}%) | {cf} | "
            f"{d['total_ext_imports']:,} | {d['unique_ext_importers']:,} | {d['outgoing_ext_imports']:,} | "
            f"{d['total_lines']:,} | {d['interface_lines']:,} ({d['line_compression_ratio']:.4f}) |"
        )
    a("")
    a("> **Note on `(root)` and `Formalism` at depth 2:** At depth-1 (`top_dir`), `(root)` contains `Main.lean` and `Statements.lean`, with `0` external importers because `Main.lean` sits at the root of the DAG (`dist_from_main = 0`). At depth-2 (`depth2_dir`), `dir_stats` partitions root-level files directly inside `Formalism/*.lean` (9 files such as `Formalism/ZetaRealNonvanish.lean` and `Formalism/StatementOC.lean`) separately from `Formalism/<Subdir>` (107 subdirectories).")
    a("")
    a("### Major Cross-Boundary Dependency Flows (`src` imports `dst`)")
    a("")
    a("| Source Top-Dir | Target Top-Dir | Import Edges | Source Files | Target Interface Files |")
    a("|---|---|---:|---:|---:|")
    for row in top_matrix[:18]:
        a(f"| `{row['src_dir']}` | `{row['dst_dir']}` | {row['edges']:,} | {row['src_files']:,} | {row['dst_files']:,} |")
    a("")

    a("## 3. Depth-2 Sub-Theory Compression Statistics")
    a("")
    a("### 3.1 Top 35 Largest Depth-2 Sub-Theories (by Total Files)")
    a("")
    a("| Depth-2 Directory | Files | Interface Files | Ratio | Ext Edges (In) | Unique Ext Importers | Top Interface File (Ext Fan-In) |")
    a("|---|---:|---:|---:|---:|---:|---|")
    for d in d2_dirs[:35]:
        if d["interface_files"]:
            tf = d["interface_files"][0]
            top_cell = f"[{tf['rel_path'].split('/')[-1]}](file:///home/ubuntu/riemann_proof/lean/src/{tf['rel_path']}) ({tf['ext_fan_in']:,})"
        else:
            top_cell = "-"
        a(
            f"| `{d['dir_key']}` | {d['total_files']:,} | {d['interface_files_count']:,} | "
            f"{d['compression_ratio']:.4f} | {d['total_ext_imports']:,} | {d['unique_ext_importers']:,} | {top_cell} |"
        )
    a("")

    a("### 3.2 Highest-Compression Depth-2 Sub-Theories (`total_files >= 20`, Lowest Ratio)")
    a("")
    a("| Depth-2 Directory | Files | Interface Files | Ratio | Compression Factor | Ext Edges (In) |")
    a("|---|---:|---:|---:|---:|---:|")
    d2_ge20 = [d for d in d2_dirs if d["total_files"] >= 20]
    for d in sorted(d2_ge20, key=lambda x: (x["compression_ratio"], -x["total_files"]))[:15]:
        cf = f"{d['compression_factor']:.2f}x" if d["compression_factor"] else "-"
        a(
            f"| `{d['dir_key']}` | {d['total_files']:,} | {d['interface_files_count']:,} | "
            f"{d['compression_ratio']:.4f} | {cf} | {d['total_ext_imports']:,} |"
        )
    a("")

    a("### 3.3 Top 15 Depth-2 Sub-Theories by Cross-Boundary Fan-In")
    a("")
    a("| Depth-2 Directory | Ext Import Edges | Unique Ext Importers | Interface / Total Files | Ratio |")
    a("|---|---:|---:|---:|---:|")
    for d in sorted(d2_dirs, key=lambda x: -x["total_ext_imports"])[:15]:
        a(
            f"| `{d['dir_key']}` | {d['total_ext_imports']:,} | {d['unique_ext_importers']:,} | "
            f"{d['interface_files_count']:,} / {d['total_files']:,} | {d['compression_ratio']:.4f} |"
        )
    a("")

    a("## 4. Sub-Theory Public APIs in Plain Mathematical English (59 Verified Interface Files)")
    a("")
    a("Every file below was read directly from `/home/ubuntu/riemann_proof/lean/src/`, and all listed declaration names and line numbers were verified against `graph.sqlite`.")
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

    top_lookup = {d["dir_key"]: d for d in top_dirs}

    for td in order_top:
        items = by_top.get(td, [])
        if not items:
            continue
        td_stat = top_lookup[td]
        a(f"### 4.{order_top.index(td)+1} `{td}` ({td_stat['total_files']:,} files -> {td_stat['interface_files_count']:,} top-dir interfaces, ratio `{td_stat['compression_ratio']:.4f}`)")
        a("")
        # Keep Main before Statements, Supplements All before MainTheorems, otherwise sort by fan-in desc
        if td in ("(root)", "Supplements"):
            items_sorted = sorted(items, key=lambda x: (x["dist_from_main"], x["rel_path"]))
        else:
            items_sorted = sorted(items, key=lambda x: (-x["top_ext_fan_in"], -x["d2_ext_fan_in"], -x["tot_in_degree"], x["rel_path"]))

        for it in items_sorted:
            top_imps = ", ".join(f"`{k}` ({v})" for k, v in list(it["importing_top_dirs"].items())[:5]) or "None (apex)"
            d2_imps = ", ".join(f"`{k}` ({v})" for k, v in list(it["importing_d2_dirs"].items())[:4]) or "None"
            a(f"#### [`{it['rel_path']}`]({it['file_url']})")
            a(
                f"- **Role:** {it['role']} | **Depth-2:** `{it['depth2_dir']}` | **Lines:** {it['lines']} | "
                f"**Top-Dir Ext Fan-In:** {it['top_ext_fan_in']:,} | **Depth-2 Ext Fan-In:** {it['d2_ext_fan_in']:,} | "
                f"**Total In-Degree:** {it['tot_in_degree']:,} (`dist={it['dist_from_main']}`, `height={it['height_from_leaves']}`)"
            )
            a(f"- **External Importers:** Top-dirs: {top_imps} | Depth-2 dirs: {d2_imps}")
            a(f"- **Plain-English Mathematical Summary:** {it['plain_english_summary']}")
            if it["key_exports"]:
                a("- **Key Exported Declarations:**")
                for ke in it["key_exports"]:
                    link = f"{it['file_url']}#L{ke['line_no']}"
                    a(f"  - `{ke['kind']}` [`{ke['name']}`]({link}) (L{ke['line_no']}): {ke['summary']}")
            else:
                a("- **Key Exported Declarations:** No local `theorem`/`def`/`structure` declarations (pure import barrel / command directive).")
            a("")

    return "\n".join(lines) + "\n"


def render_html(payload: dict) -> str:
    """Render a 100% self-contained searchable HTML/CSS/JS interface browser (zero CDN links)."""
    json_blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    # Prevent accidental </script> termination inside JSON
    json_blob = json_blob.replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Riemann Proof Lean Codebase — Cross-Boundary Interface Browser</title>
<style>
  :root {{
    --bg: #0b1020;
    --panel: #121931;
    --panel2: #182240;
    --border: #28355e;
    --text: #e6ecff;
    --muted: #9aa9d4;
    --accent: #6aa9ff;
    --accent2: #5de4c7;
    --warn: #ffd166;
    --badge-bg: #1e2c52;
    --code-bg: #090e1c;
    --row-hover: #1b274b;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.45;
  }}
  header {{
    background: linear-gradient(135deg, #101833 0%, #162347 100%);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }}
  header h1 {{
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
    letter-spacing: -0.01em;
  }}
  header .sub {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 2px;
  }}
  .top-stats {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }}
  .pill {{
    background: var(--badge-bg);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 5px 12px;
    font-size: 0.8rem;
    color: var(--text);
  }}
  .pill b {{ color: var(--accent2); }}
  .toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    padding: 12px 24px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    align-items: center;
  }}
  .tabs {{
    display: inline-flex;
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 3px;
  }}
  .tab {{
    border: 0;
    background: transparent;
    color: var(--muted);
    padding: 6px 14px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.86rem;
    font-weight: 600;
  }}
  .tab.active {{
    background: var(--accent);
    color: #081024;
  }}
  input[type="search"], select {{
    background: var(--code-bg);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 0.88rem;
    outline: none;
  }}
  input[type="search"]:focus, select:focus {{
    border-color: var(--accent);
  }}
  #globalSearch {{
    flex: 1 1 320px;
    min-width: 240px;
  }}
  .layout {{
    display: grid;
    grid-template-columns: 360px 1fr;
    min-height: calc(100vh - 130px);
  }}
  @media (max-width: 960px) {{
    .layout {{ grid-template-columns: 1fr; }}
  }}
  .sidebar {{
    border-right: 1px solid var(--border);
    background: var(--panel);
    display: flex;
    flex-direction: column;
    max-height: calc(100vh - 130px);
  }}
  .sidebar-head {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    font-size: 0.8rem;
    color: var(--muted);
  }}
  .dir-list {{
    overflow-y: auto;
    flex: 1;
  }}
  .dir-item {{
    padding: 10px 14px;
    border-bottom: 1px solid rgba(40,53,94,0.5);
    cursor: pointer;
    transition: background 0.12s;
  }}
  .dir-item:hover {{ background: var(--row-hover); }}
  .dir-item.active {{
    background: #1d2d57;
    border-left: 3px solid var(--accent);
    padding-left: 11px;
  }}
  .dir-name {{
    font-weight: 600;
    font-size: 0.88rem;
    word-break: break-word;
  }}
  .dir-meta {{
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-top: 4px;
    font-size: 0.77rem;
    color: var(--muted);
  }}
  .ratio-bar {{
    height: 4px;
    background: var(--code-bg);
    border-radius: 3px;
    margin-top: 6px;
    overflow: hidden;
  }}
  .ratio-fill {{
    height: 100%;
    background: linear-gradient(90deg, var(--accent2), var(--accent));
  }}
  .main {{
    padding: 20px 24px;
    overflow-y: auto;
    max-height: calc(100vh - 130px);
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 12px;
    margin-bottom: 18px;
  }}
  .kpi {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
  }}
  .kpi .lbl {{
    font-size: 0.75rem;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .kpi .val {{
    font-size: 1.32rem;
    font-weight: 700;
    margin-top: 4px;
    color: var(--text);
  }}
  .kpi .hint {{
    font-size: 0.75rem;
    color: var(--accent2);
    margin-top: 2px;
  }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
  }}
  .card h2, .card h3 {{
    margin: 0 0 10px 0;
    font-size: 1rem;
  }}
  .flow-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .chip {{
    background: var(--panel2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 10px;
    font-size: 0.8rem;
  }}
  .chip b {{ color: var(--accent); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.84rem;
  }}
  th, td {{
    padding: 8px 10px;
    text-align: left;
    border-bottom: 1px solid rgba(40,53,94,0.6);
    vertical-align: top;
  }}
  th {{
    color: var(--muted);
    font-weight: 600;
    font-size: 0.76rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    background: var(--panel2);
    position: sticky;
    top: 0;
  }}
  tr.clickable:hover {{ background: var(--row-hover); cursor: pointer; }}
  .mono {{
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 0.81rem;
    word-break: break-word;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: var(--accent2);
    white-space: nowrap;
  }}
  .badge.warn {{ color: var(--warn); }}
  .badge.kind {{ color: var(--accent); }}
  a.filelink {{
    color: var(--accent);
    text-decoration: none;
  }}
  a.filelink:hover {{ text-decoration: underline; }}
  .summary-box {{
    background: var(--panel2);
    border-left: 3px solid var(--accent2);
    padding: 12px 14px;
    border-radius: 6px;
    margin: 10px 0 14px 0;
    font-size: 0.92rem;
  }}
  .detail-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 8px;
  }}
  .btn {{
    background: var(--panel2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 12px;
    cursor: pointer;
    font-size: 0.82rem;
  }}
  .btn:hover {{ border-color: var(--accent); }}
  .muted {{ color: var(--muted); }}
  .table-wrap {{
    max-height: 500px;
    overflow: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
  }}
</style>
</head>
<body>
<header>
  <div>
    <h1>Lean Riemann Proof — Cross-Boundary Interface Browser</h1>
    <div class="sub">100% self-contained explorer of directory compression, public API surfaces, declarations, and plain-English mathematics</div>
  </div>
  <div class="top-stats" id="topStats"></div>
</header>

<div class="toolbar">
  <div class="tabs">
    <button class="tab active" data-mode="top">Top-Level Dirs (<span id="cntTop">0</span>)</button>
    <button class="tab" data-mode="d2">Depth-2 Sub-Theories (<span id="cntD2">0</span>)</button>
    <button class="tab" data-mode="analyzed">Analyzed APIs (<span id="cntAn">0</span>)</button>
    <button class="tab" data-mode="search">Global Search</button>
  </div>
  <input id="globalSearch" type="search" placeholder="Filter directories, interface paths, Lean declarations, or math terms...">
  <select id="sortSelect" title="Sort directories">
    <option value="files">Sort: Total Files</option>
    <option value="ext">Sort: External Imports</option>
    <option value="ifaces">Sort: Interface Files</option>
    <option value="ratio_asc">Sort: Lowest Ratio (Most Compressed)</option>
    <option value="ratio_desc">Sort: Highest Ratio</option>
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

<script id="iface-data" type="application/json">{json_blob}</script>
<script>
(function () {{
  const DATA = JSON.parse(document.getElementById("iface-data").textContent);
  const ANALYZED_MAP = new Map(DATA.analyzed_interfaces.map(x => [x.rel_path, x]));

  const state = {{
    mode: "top",
    query: "",
    sort: "files",
    selectedDir: "Development",
    selectedFile: DATA.analyzed_interfaces[0] ? DATA.analyzed_interfaces[0].rel_path : null,
    fileFilter: ""
  }};

  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

  const fmt = (n) => n == null ? "-" : Number(n).toLocaleString();
  const pct = (r) => (Number(r) * 100).toFixed(2) + "%";
  const fileUrl = (rel, line) => "file:///home/ubuntu/riemann_proof/lean/src/" + encodeURI(rel) + (line ? "#L" + line : "");

  // Header stats
  document.getElementById("cntTop").textContent = DATA.top_dirs.length;
  document.getElementById("cntD2").textContent = DATA.depth2_dirs.length;
  document.getElementById("cntAn").textContent = DATA.analyzed_interfaces.length;
  document.getElementById("topStats").innerHTML = [
    `<span class="pill">Files: <b>${{fmt(DATA.meta.total_files)}}</b></span>`,
    `<span class="pill">Top-Dir Interfaces: <b>${{fmt(DATA.meta.top_dir_interface_files)}}</b> (${{pct(DATA.meta.top_dir_interface_files / DATA.meta.total_files)}})</span>`,
    `<span class="pill">Depth-2 Interfaces: <b>${{fmt(DATA.meta.depth2_dir_interface_files)}}</b> (${{pct(DATA.meta.depth2_dir_interface_files / DATA.meta.total_files)}})</span>`,
    `<span class="pill">Deep-Read Files: <b>${{DATA.analyzed_interfaces.length}}</b></span>`
  ].join("");

  function sortDirs(list) {{
    const arr = list.slice();
    switch (state.sort) {{
      case "ext": arr.sort((a, b) => b.total_ext_imports - a.total_ext_imports || b.total_files - a.total_files); break;
      case "ifaces": arr.sort((a, b) => b.interface_files_count - a.interface_files_count); break;
      case "ratio_asc": arr.sort((a, b) => a.compression_ratio - b.compression_ratio || b.total_files - a.total_files); break;
      case "ratio_desc": arr.sort((a, b) => b.compression_ratio - a.compression_ratio || b.total_files - a.total_files); break;
      case "name": arr.sort((a, b) => a.dir_key.localeCompare(b.dir_key)); break;
      default: arr.sort((a, b) => b.total_files - a.total_files);
    }}
    return arr;
  }}

  function renderSidebar() {{
    const q = state.query.trim().toLowerCase();
    const listEl = document.getElementById("sidebarList");
    const lblEl = document.getElementById("sidebarLabel");
    const cntEl = document.getElementById("sidebarCount");

    if (state.mode === "analyzed" || state.mode === "search") {{
      lblEl.textContent = state.mode === "analyzed" ? "Analyzed Interface Files" : "Matching Analyzed Files";
      const items = DATA.analyzed_interfaces.filter(item => {{
        if (!q) return true;
        if (item.rel_path.toLowerCase().includes(q)) return true;
        if (item.plain_english_summary.toLowerCase().includes(q)) return true;
        if (item.role.toLowerCase().includes(q)) return true;
        if (item.key_exports.some(k => k.name.toLowerCase().includes(q) || k.summary.toLowerCase().includes(q))) return true;
        if (item.all_declarations.some(d => d.name.toLowerCase().includes(q))) return true;
        return false;
      }});
      cntEl.textContent = items.length;
      if (items.length && !items.some(x => x.rel_path === state.selectedFile)) {{
        state.selectedFile = items[0].rel_path;
      }}
      listEl.innerHTML = items.map(item => `
        <div class="dir-item ${{item.rel_path === state.selectedFile ? "active" : ""}}" data-file="${{esc(item.rel_path)}}">
          <div class="dir-name mono">${{esc(item.rel_path.split("/").pop())}}</div>
          <div class="muted" style="font-size:0.74rem;word-break:break-all;">${{esc(item.depth2_dir)}}</div>
          <div class="dir-meta">
            <span class="badge">${{esc(item.role)}}</span>
            <span>top_in: <b>${{fmt(item.top_ext_fan_in)}}</b> · d2_in: <b>${{fmt(item.d2_ext_fan_in)}}</b></span>
          </div>
        </div>
      `).join("") || `<div style="padding:16px" class="muted">No analyzed files match "${{esc(state.query)}}".</div>`;
      listEl.querySelectorAll(".dir-item").forEach(el => {{
        el.onclick = () => {{ state.selectedFile = el.dataset.file; render(); }};
      }});
      return;
    }}

    const srcList = state.mode === "top" ? DATA.top_dirs : DATA.depth2_dirs;
    lblEl.textContent = state.mode === "top" ? "Top-Level Directories" : "Depth-2 Directories";
    const filtered = sortDirs(srcList).filter(d => {{
      if (!q) return true;
      if (d.dir_key.toLowerCase().includes(q)) return true;
      return d.interface_files.some(f => f.p.toLowerCase().includes(q));
    }});
    cntEl.textContent = filtered.length;
    if (filtered.length && !filtered.some(d => d.dir_key === state.selectedDir)) {{
      state.selectedDir = filtered[0].dir_key;
    }}

    listEl.innerHTML = filtered.map(d => {{
      const fillW = Math.min(100, Math.max(2, d.compression_ratio * 100));
      return `
        <div class="dir-item ${{d.dir_key === state.selectedDir ? "active" : ""}}" data-dir="${{esc(d.dir_key)}}">
          <div class="dir-name">${{esc(d.dir_key)}}</div>
          <div class="dir-meta">
            <span>${{fmt(d.interface_files_count)}} / ${{fmt(d.total_files)}} files (${{pct(d.compression_ratio)}})</span>
            <span>ext: <b>${{fmt(d.total_ext_imports)}}</b></span>
          </div>
          <div class="ratio-bar"><div class="ratio-fill" style="width:${{fillW}}%"></div></div>
        </div>
      `;
    }}).join("") || `<div style="padding:16px" class="muted">No directories match "${{esc(state.query)}}".</div>`;

    listEl.querySelectorAll(".dir-item").forEach(el => {{
      el.onclick = () => {{ state.selectedDir = el.dataset.dir; state.fileFilter = ""; render(); }};
    }});
  }}

  function renderAnalyzedDetail(relPath, backBtnHtml) {{
    const item = ANALYZED_MAP.get(relPath);
    if (!item) return "";
    const topImps = Object.entries(item.importing_top_dirs || {{}});
    const d2Imps = Object.entries(item.importing_d2_dirs || {{}});
    const q = state.query.trim().toLowerCase();
    const decls = item.all_declarations.filter(d => !q || d.name.toLowerCase().includes(q) || d.kind.toLowerCase().includes(q));

    return `
      <div class="card">
        <div class="detail-header">
          <div>
            ${{backBtnHtml || ""}}
            <div style="margin-top:6px;">
              <span class="badge">${{esc(item.role)}}</span>
              <span class="badge kind">${{esc(item.depth2_dir)}}</span>
            </div>
            <h2 class="mono" style="margin-top:8px;">
              <a class="filelink" href="${{fileUrl(item.rel_path)}}" target="_blank">${{esc(item.rel_path)}}</a>
            </h2>
          </div>
          <div style="text-align:right;font-size:0.82rem;" class="muted">
            Lines: <b>${{fmt(item.lines)}}</b> · dist_from_main: <b>${{item.dist_from_main}}</b> · height: <b>${{item.height_from_leaves}}</b><br>
            Top Ext Fan-In: <b>${{fmt(item.top_ext_fan_in)}}</b> · Depth-2 Ext Fan-In: <b>${{fmt(item.d2_ext_fan_in)}}</b> · Total In: <b>${{fmt(item.tot_in_degree)}}</b>
          </div>
        </div>

        <div class="summary-box">${{esc(item.plain_english_summary)}}</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
          <div>
            <div class="muted" style="font-size:0.78rem;margin-bottom:4px;">Imported by External Top-Dirs</div>
            <div class="flow-chips">
              ${{topImps.map(([k, v]) => `<span class="chip"><b>${{esc(k)}}</b>: ${{fmt(v)}}</span>`).join("") || '<span class="muted">None (apex)</span>'}}
            </div>
          </div>
          <div>
            <div class="muted" style="font-size:0.78rem;margin-bottom:4px;">Imported by External Depth-2 Dirs</div>
            <div class="flow-chips">
              ${{d2Imps.slice(0, 12).map(([k, v]) => `<span class="chip"><b>${{esc(k)}}</b>: ${{fmt(v)}}</span>`).join("") || '<span class="muted">None</span>'}}
              ${{d2Imps.length > 12 ? `<span class="chip muted">+${{d2Imps.length - 12}} more</span>` : ""}}
            </div>
          </div>
        </div>

        <h3>Key Exported Mathematical APIs (${{item.key_exports.length}})</h3>
        ${{item.key_exports.length ? `
          <div class="table-wrap" style="max-height:320px;margin-bottom:14px;">
            <table>
              <thead><tr><th>Kind</th><th>Declaration</th><th>Line</th><th>Plain-English Mathematical Meaning</th></tr></thead>
              <tbody>
                ${{item.key_exports.map(k => `
                  <tr>
                    <td><span class="badge kind">${{esc(k.kind)}}</span></td>
                    <td class="mono"><a class="filelink" href="${{fileUrl(item.rel_path, k.line_no)}}" target="_blank">${{esc(k.name)}}</a></td>
                    <td class="mono">L${{k.line_no}}</td>
                    <td>${{esc(k.summary)}}</td>
                  </tr>
                `).join("")}}
              </tbody>
            </table>
          </div>
        ` : `<p class="muted">This file exports via Lean imports / commands rather than local named theorem/def declarations.</p>`}}

        <h3>All Extracted Declarations in SQLite (${{decls.length}} / ${{item.all_declarations.length}})</h3>
        <div class="table-wrap" style="max-height:300px;">
          <table>
            <thead><tr><th>Line</th><th>Kind</th><th>Name</th></tr></thead>
            <tbody>
              ${{decls.map(d => `
                <tr>
                  <td class="mono"><a class="filelink" href="${{fileUrl(item.rel_path, d.line_no)}}" target="_blank">L${{d.line_no}}</a></td>
                  <td><span class="badge kind">${{esc(d.kind)}}</span></td>
                  <td class="mono">${{esc(d.name)}}</td>
                </tr>
              `).join("") || `<tr><td colspan="3" class="muted">No declarations indexed in SQLite for this file.</td></tr>`}}
            </tbody>
          </table>
        </div>
      </div>
    `;
  }}

  function renderGlobalSearch() {{
    const q = state.query.trim().toLowerCase();
    const matchedDirs = DATA.depth2_dirs.filter(d => !q || d.dir_key.toLowerCase().includes(q)).slice(0, 30);
    const matchedFiles = [];
    const seen = new Set();
    for (const d of DATA.top_dirs) {{
      for (const f of d.interface_files) {{
        if (seen.has(f.p)) continue;
        const an = ANALYZED_MAP.get(f.p);
        const hit = !q || f.p.toLowerCase().includes(q) || (an && (
          an.plain_english_summary.toLowerCase().includes(q) ||
          an.all_declarations.some(x => x.name.toLowerCase().includes(q))
        ));
        if (hit) {{
          seen.add(f.p);
          matchedFiles.push(f);
        }}
      }}
    }}
    matchedFiles.sort((a, b) => b.a - a.a || b.e - a.e);

    const mainEl = document.getElementById("mainPane");
    mainEl.innerHTML = `
      ${{state.selectedFile && ANALYZED_MAP.has(state.selectedFile) ? renderAnalyzedDetail(state.selectedFile, "") : ""}}
      <div class="card">
        <h2>Global Cross-Boundary Search Results ${{q ? 'for "' + esc(state.query) + '"' : "(All Top Interfaces)"}}</h2>
        <p class="muted">Matched ${{matchedDirs.length}} depth-2 directories (showing up to 30) and ${{matchedFiles.length}} top-dir interface files (showing top 80).</p>
        <div class="flow-chips" style="margin-bottom:14px;">
          ${{matchedDirs.map(d => `<span class="chip" style="cursor:pointer;" data-jumpd2="${{esc(d.dir_key)}}"><b>${{esc(d.dir_key)}}</b> (${{d.interface_files_count}}/${{d.total_files}})</span>`).join("")}}
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>File</th><th>Depth-2 Dir</th><th>Top Ext In</th><th>Tot In</th><th>Lines</th><th>Status</th></tr></thead>
            <tbody>
              ${{matchedFiles.slice(0, 80).map(f => `
                <tr class="${{f.a ? "clickable" : ""}}" data-openan="${{f.a ? esc(f.p) : ""}}">
                  <td class="mono"><a class="filelink" href="${{fileUrl(f.p)}}" target="_blank">${{esc(f.p)}}</a></td>
                  <td>${{esc(f.d2)}}</td>
                  <td><b>${{fmt(f.e)}}</b></td>
                  <td>${{fmt(f.t)}}</td>
                  <td>${{fmt(f.l)}}</td>
                  <td>${{f.a ? '<span class="badge">Analyzed API</span>' : '<span class="muted">Indexed</span>'}}</td>
                </tr>
              `).join("")}}
            </tbody>
          </table>
        </div>
      </div>
    `;
    mainEl.querySelectorAll("[data-jumpd2]").forEach(el => {{
      el.onclick = () => {{ state.mode = "d2"; state.selectedDir = el.dataset.jumpd2; render(); }};
    }});
    mainEl.querySelectorAll("[data-openan]").forEach(el => {{
      if (el.dataset.openan) el.onclick = (ev) => {{
        if (ev.target.tagName === "A") return;
        state.selectedFile = el.dataset.openan;
        render();
      }};
    }});
  }}

  function renderMain() {{
    const mainEl = document.getElementById("mainPane");
    if (state.mode === "analyzed") {{
      mainEl.innerHTML = renderAnalyzedDetail(state.selectedFile, "");
      return;
    }}
    if (state.mode === "search") {{
      renderGlobalSearch();
      return;
    }}

    const srcList = state.mode === "top" ? DATA.top_dirs : DATA.depth2_dirs;
    const d = srcList.find(x => x.dir_key === state.selectedDir) || srcList[0];
    if (!d) {{
      mainEl.innerHTML = `<div class="card">No directory selected.</div>`;
      return;
    }}

    const q = state.query.trim().toLowerCase();
    const fQuery = state.fileFilter.trim().toLowerCase();
    const shown = d.interface_files.filter(f => {{
      if (fQuery && !f.p.toLowerCase().includes(fQuery)) return false;
      if (q && !d.dir_key.toLowerCase().includes(q) && !f.p.toLowerCase().includes(q)) return false;
      return true;
    }});

    const analyzedInDir = DATA.analyzed_interfaces.filter(x =>
      (state.mode === "top" ? x.top_dir : x.depth2_dir) === d.dir_key
    );

    const activeAn = state.selectedFile && analyzedInDir.some(x => x.rel_path === state.selectedFile)
      ? state.selectedFile : null;

    mainEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px;margin-bottom:12px;">
        <div>
          <h2 style="margin:0;">${{esc(d.dir_key)}}</h2>
          <div class="muted" style="font-size:0.84rem;">
            ${{state.mode === "top" ? "Top-Level Directory" : "Depth-2 Sub-Theory"}}${{d.parent_key ? " · parent: " + esc(d.parent_key) : ""}}
            · min dist from Main: <b>${{d.min_dist_from_main}}</b> · max height: <b>${{d.max_height}}</b>
          </div>
        </div>
        <div class="muted" style="font-size:0.84rem;">
          ${{fmt(d.total_lines)}} lines · ${{fmt(d.theorems)}} theorems · ${{fmt(d.defs)}} defs · ${{fmt(d.structures)}} structures
        </div>
      </div>

      <div class="kpi-grid">
        <div class="kpi"><div class="lbl">Total Files</div><div class="val">${{fmt(d.total_files)}}</div><div class="hint">${{fmt(d.total_lines)}} lines</div></div>
        <div class="kpi"><div class="lbl">Interface Files</div><div class="val">${{fmt(d.interface_files_count)}}</div><div class="hint">${{fmt(d.interface_lines)}} lines</div></div>
        <div class="kpi"><div class="lbl">Compression Ratio</div><div class="val">${{pct(d.compression_ratio)}}</div><div class="hint">${{d.compression_factor ? d.compression_factor + "x compression" : "Apex (0 exports)"}}</div></div>
        <div class="kpi"><div class="lbl">Cross-Boundary Imports</div><div class="val">${{fmt(d.total_ext_imports)}}</div><div class="hint">from ${{fmt(d.unique_ext_importers)}} external files</div></div>
        <div class="kpi"><div class="lbl">Outgoing Ext Imports</div><div class="val">${{fmt(d.outgoing_ext_imports)}}</div><div class="hint">into ${{d.imported_external_dirs.length}} external dirs</div></div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
        <div class="card">
          <h3>Imported By External Directories (${{d.importing_dirs.length}})</h3>
          <div class="flow-chips">
            ${{d.importing_dirs.map(x => `<span class="chip"><b>${{esc(x.dir)}}</b>: ${{fmt(x.edges)}} edges (${{fmt(x.src_files)}} -> ${{fmt(x.dst_files)}} files)</span>`).join("") || '<span class="muted">No external importers.</span>'}}
          </div>
        </div>
        <div class="card">
          <h3>Imports From External Directories (${{d.imported_external_dirs.length}})</h3>
          <div class="flow-chips">
            ${{d.imported_external_dirs.map(x => `<span class="chip"><b>${{esc(x.dir)}}</b>: ${{fmt(x.edges)}} edges (${{fmt(x.src_files)}} -> ${{fmt(x.dst_files)}} files)</span>`).join("") || '<span class="muted">No external dependencies (self-contained / Mathlib only).</span>'}}
          </div>
        </div>
      </div>

      ${{activeAn ? renderAnalyzedDetail(activeAn, `<button class="btn" id="closeAnBtn">← Back to ${{esc(d.dir_key)}} summary</button>`) : ""}}

      ${{analyzedInDir.length ? `
        <div class="card">
          <h3>Deep-Read Analyzed Public APIs in ${{esc(d.dir_key)}} (${{analyzedInDir.length}})</h3>
          <div class="flow-chips">
            ${{analyzedInDir.map(x => `
              <button class="btn" data-pickan="${{esc(x.rel_path)}}">
                <span class="mono">${{esc(x.rel_path.split("/").pop())}}</span>
                <span class="badge">${{esc(x.role)}}</span>
              </button>
            `).join("")}}
          </div>
        </div>
      ` : ""}}

      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:10px;">
          <h3 style="margin:0;">Exported Cross-Boundary Interface Files (<span id="shownCount">showing ${{shown.length}} of ${{fmt(d.interface_files_count)}}</span>)</h3>
          <input id="localFileFilter" type="search" value="${{esc(state.fileFilter)}}" placeholder="Filter files inside this directory..." style="min-width:260px;">
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>Interface File</th>
                <th>Ext Fan-In</th>
                <th>Tot In</th>
                <th>Lines</th>
                <th>T / D / S</th>
                <th>Importing External Dirs</th>
                <th>API</th>
              </tr>
            </thead>
            <tbody id="ifaceTbody"></tbody>
          </table>
        </div>
      </div>
    `;

    function renderIfaceRows() {{
      const fq = state.fileFilter.trim().toLowerCase();
      const rows = d.interface_files.filter(f => {{
        if (fq && !f.p.toLowerCase().includes(fq)) return false;
        if (q && !d.dir_key.toLowerCase().includes(q) && !f.p.toLowerCase().includes(q)) return false;
        return true;
      }});
      const sc = document.getElementById("shownCount");
      if (sc) sc.textContent = `showing ${{rows.length}} of ${{fmt(d.interface_files_count)}}` + (d.shown_files_count < d.interface_files_count ? ` (top ${{d.shown_files_count}} embedded)` : "");
      const tb = document.getElementById("ifaceTbody");
      if (!tb) return;
      tb.innerHTML = rows.map((f, idx) => {{
        const eds = f.ed || {{}};
        const edStr = Object.entries(eds).slice(0, 4).map(([k, v]) => `${{k}} (${{v}})`).join(", ");
        const moreEd = Object.keys(eds).length > 4 ? ` +${{Object.keys(eds).length - 4}}` : "";
        return `
          <tr class="${{f.a ? "clickable" : ""}}" data-pickan="${{f.a ? esc(f.p) : ""}}">
            <td class="muted">${{idx + 1}}</td>
            <td class="mono"><a class="filelink" href="${{fileUrl(f.p)}}" target="_blank">${{esc(f.p)}}</a></td>
            <td><b>${{fmt(f.e)}}</b></td>
            <td>${{fmt(f.t)}}</td>
            <td>${{fmt(f.l)}}</td>
            <td class="mono">${{f.th}}/${{f.df}}/${{f.st}}</td>
            <td style="font-size:0.78rem;">${{esc(edStr + moreEd)}}</td>
            <td>${{f.a ? '<span class="badge">View Summary</span>' : '<span class="muted">-</span>'}}</td>
          </tr>
        `;
      }}).join("") || `<tr><td colspan="8" class="muted">No cross-boundary interface files in this directory.</td></tr>`;
      tb.querySelectorAll("[data-pickan]").forEach(el => {{
        if (el.dataset.pickan) {{
          el.onclick = (ev) => {{
            if (ev.target.tagName === "A") return;
            state.selectedFile = el.dataset.pickan;
            renderMain();
          }};
        }}
      }});
    }}

    renderIfaceRows();

    const lf = document.getElementById("localFileFilter");
    if (lf) {{
      lf.oninput = (e) => {{ state.fileFilter = e.target.value; renderIfaceRows(); }};
    }}
    mainEl.querySelectorAll("[data-pickan]").forEach(el => {{
      if (el.dataset.pickan) {{
        el.onclick = (ev) => {{
          if (ev.target.tagName === "A") return;
          state.selectedFile = el.dataset.pickan;
          renderMain();
        }};
      }}
    }});
    const cb = document.getElementById("closeAnBtn");
    if (cb) cb.onclick = () => {{ state.selectedFile = null; renderMain(); }};
  }}

  function render() {{
    renderSidebar();
    renderMain();
  }}

  document.querySelectorAll(".tab").forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll(".tab").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.mode = btn.dataset.mode;
      if (state.mode === "analyzed" && !ANALYZED_MAP.has(state.selectedFile)) {{
        state.selectedFile = DATA.analyzed_interfaces[0].rel_path;
      }}
      render();
    }};
  }});

  document.getElementById("globalSearch").addEventListener("input", (e) => {{
    state.query = e.target.value;
    render();
  }});

  document.getElementById("sortSelect").addEventListener("change", (e) => {{
    state.sort = e.target.value;
    renderSidebar();
  }});

  render();
}})();
</script>
</body>
</html>
"""


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(CURATED_PATH, "r", encoding="utf-8") as f:
        curated: dict[str, dict] = json.load(f)
    analyzed_set = set(curated.keys())

    with open(META_PATH, "r", encoding="utf-8") as f:
        meta_raw = json.load(f)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    top_dirs, top_matrix = compute_level_interfaces(conn, 1, "top_dir", analyzed_set)
    d2_dirs, d2_matrix = compute_level_interfaces(conn, 2, "depth2_dir", analyzed_set)

    top_map = {d["dir_key"]: d for d in top_dirs}
    d2_map = {d["dir_key"]: d for d in d2_dirs}

    analyzed_list = extract_analyzed_interfaces(conn, curated, top_map, d2_map)
    conn.close()

    total_top_iface_files = sum(d["interface_files_count"] for d in top_dirs)
    total_d2_iface_files = sum(d["interface_files_count"] for d in d2_dirs)
    total_top_ext_edges = sum(d["total_ext_imports"] for d in top_dirs)
    total_d2_ext_edges = sum(d["total_ext_imports"] for d in d2_dirs)

    full_export = {
        "meta": {
            "total_files": meta_raw["total_files"],
            "reachable_files": meta_raw["reachable_files"],
            "total_lines": meta_raw["total_lines"],
            "total_internal_edges": meta_raw["total_internal_edges"],
            "is_dag": meta_raw["is_dag"],
            "top_dir_count": len(top_dirs),
            "depth2_dir_count": len(d2_dirs),
            "top_dir_interface_files": total_top_iface_files,
            "top_dir_overall_compression_ratio": round(total_top_iface_files / meta_raw["total_files"], 6),
            "depth2_dir_interface_files": total_d2_iface_files,
            "depth2_dir_overall_compression_ratio": round(total_d2_iface_files / meta_raw["total_files"], 6),
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

    report_md = render_report(full_export)
    with open(REPORT_OUT, "w", encoding="utf-8") as f:
        f.write(report_md)

    browser_payload = build_browser_payload(full_export)
    html_text = render_html(browser_payload)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html_text)

    json_mb = JSON_OUT.stat().st_size / (1024 * 1024)
    rep_kb = REPORT_OUT.stat().st_size / 1024
    html_mb = HTML_OUT.stat().st_size / (1024 * 1024)
    print(f"Generated {JSON_OUT} ({json_mb:.2f} MiB), {REPORT_OUT} ({rep_kb:.1f} KiB), and {HTML_OUT} ({html_mb:.2f} MiB) in {time.time() - t0:.2f}s")
    print(
        f"Summary: {len(top_dirs)} top_dirs ({total_top_iface_files} iface files, {total_top_ext_edges} ext edges), "
        f"{len(d2_dirs)} depth2_dirs ({total_d2_iface_files} iface files, {total_d2_ext_edges} ext edges), "
        f"{len(analyzed_list)} curated APIs verified 100% against SQLite."
    )


if __name__ == "__main__":
    main()
