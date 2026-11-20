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
    """Render structured Markdown report focusing on mathematical interfaces and plain-English API summaries."""
    analyzed = full_export["analyzed_interfaces"]

    lines: list[str] = []
    a = lines.append

    a("# Cross-Boundary Mathematical Interfaces & Contracts")
    a("")
    a("This report translates the cross-boundary public mathematical interfaces of the proof in [`lean/src`](file:///home/ubuntu/riemann_proof/lean/src), focusing on the mathematical specifications, theorem contracts, and bridges that link the major sub-theories.")
    a("")
    a("## 1. Architectural Overview of Mathematical Boundaries")
    a("")
    a("- **`Development` as the Central Synthesis Engine:** `Development` develops the core proofs across abelian varieties, automorphic arithmetic, automorphic spectrum, the Weil bound, étale cohomology, discrete groups, and resolution of singularities. Its final outputs funnel into `Supplements/Kernels/` (`MainTheoremsAll.lean`) and from there into `Main.lean`, while also supplying local-global compatibility, representation-algebra, and literature-bundle contracts (`SumIoPr`, `Brauer`, `Langlands`, `LocIsotypic`, `RealTransport`) to `CompanionTheory` and `PositivityTheory`.")
    a("- **`Formalism` & `ReciprocityTheory` as Specification Contract Hubs:** `Formalism` and `ReciprocityTheory` export the foundational **mathematical specification packages (`Prop` predicates and `structure` contracts)**—such as `UniformisationConclusion`, `PELUnif`, `UnifUniqSt`, `HeckeKer`, `Laws`, `Laws2`, `LocCoh`, `D7`, and `LocalTateDualityK`—that decouple the upper analytic, Galois, and Arakelov engines from the underlying algebraic-geometric and harmonic-analytic constructions.")
    a("- **`GroundTheory`, `CompanionTheory` & `PositivityTheory` as Specialized Pillars:** `GroundTheory` supplies Arakelov Hermitian lattices (`KernelsLattice`), Whittaker multiplicity one (`Injective`), Poitou-Tate nine-term duality (`PoitouTateNineTermGs`), and idelic norm product formulas (`IdeleNorms`). `CompanionTheory` supplies adelic Siegel-Weil Euler-product measures (`IsEulerProd`), Harish-Chandra discrete series Capelli characters (`DiscreteSeriesInfinitesimalCharacter`), and Flath factorization. `PositivityTheory` supplies $\\mathrm{GL}(3)\\times\\mathrm{GL}(2)$ and $\\mathrm{GL}(2)\\times\\mathrm{GL}(2)$ Rankin-Selberg zeta integrals and weight-one Hilbert Eisenstein series.")
    a("")
    a("## 2. Sub-Theory Public APIs in Plain Mathematical English (59 Verified Interfaces)")
    a("")
    a("Every interface below was read directly from `/home/ubuntu/riemann_proof/lean/src/`, and all listed declaration names and line numbers were verified against the declaration index.")
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

    for td in order_top:
        items = by_top.get(td, [])
        if not items:
            continue
        a(f"### 2.{order_top.index(td)+1} `{td}`")
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
    --bg: #ffffff;
    --panel: #fafafa;
    --panel2: #f2f2f2;
    --border: #cccccc;
    --text: #111111;
    --muted: #555555;
    --accent: #0056b3;
    --accent2: #0056b3;
    --warn: #b45309;
    --badge-bg: #eeeeee;
    --code-bg: #ffffff;
    --row-hover: #f5f5f5;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
  }}
  header {{
    background: #ffffff;
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
  }}
  header h1 {{
    margin: 0;
    font-size: 1.25rem;
    font-weight: 700;
  }}
  header .sub {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 2px;
  }}
  .top-stats {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .pill {{
    background: var(--badge-bg);
    border: 1px solid var(--border);
    padding: 3px 8px;
    font-size: 0.8rem;
    color: var(--text);
  }}
  .pill b {{ color: var(--text); }}
  .toolbar {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding: 8px 20px;
    background: var(--panel);
    border-bottom: 1px solid var(--border);
    align-items: center;
  }}
  .tabs {{
    display: inline-flex;
    gap: 4px;
  }}
  .tab {{
    border: 1px solid var(--border);
    background: #ffffff;
    color: var(--text);
    padding: 5px 10px;
    cursor: pointer;
    font-size: 0.84rem;
  }}
  .tab:hover {{
    background: #eeeeee;
  }}
  .tab.active {{
    background: #222222;
    color: #ffffff;
    border-color: #222222;
  }}
  input[type="search"], select {{
    background: var(--code-bg);
    color: var(--text);
    border: 1px solid var(--border);
    padding: 5px 10px;
    font-size: 0.85rem;
  }}
  #globalSearch {{
    flex: 1 1 300px;
    min-width: 220px;
  }}
  .layout {{
    display: grid;
    grid-template-columns: 320px 1fr;
    min-height: calc(100vh - 110px);
  }}
  @media (max-width: 960px) {{
    .layout {{ grid-template-columns: 1fr; }}
  }}
  .sidebar {{
    border-right: 1px solid var(--border);
    background: var(--panel);
    display: flex;
    flex-direction: column;
    max-height: calc(100vh - 110px);
  }}
  .sidebar-head {{
    padding: 8px 12px;
    border-bottom: 1px solid var(--border);
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--muted);
  }}
  .dir-list {{
    overflow-y: auto;
    flex: 1;
  }}
  .dir-item {{
    padding: 8px 12px;
    border-bottom: 1px solid #e5e5e5;
    cursor: pointer;
  }}
  .dir-item:hover {{ background: #eeeeee; }}
  .dir-item.active {{
    background: #e6f0fa;
    border-left: 3px solid var(--accent);
    padding-left: 9px;
  }}
  .dir-name {{
    font-weight: 600;
    font-size: 0.86rem;
    word-break: break-word;
  }}
  .dir-meta {{
    display: flex;
    justify-content: space-between;
    gap: 8px;
    margin-top: 3px;
    font-size: 0.76rem;
    color: var(--muted);
  }}
  .ratio-bar {{
    height: 3px;
    background: #e0e0e0;
    margin-top: 4px;
  }}
  .ratio-fill {{
    height: 100%;
    background: var(--accent);
  }}
  .main {{
    padding: 16px 20px;
    overflow-y: auto;
    max-height: calc(100vh - 110px);
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(145px, 1fr));
    gap: 10px;
    margin-bottom: 16px;
  }}
  .kpi {{
    background: #ffffff;
    border: 1px solid var(--border);
    padding: 10px 12px;
  }}
  .kpi .lbl {{
    font-size: 0.75rem;
    color: var(--muted);
  }}
  .kpi .val {{
    font-size: 1.2rem;
    font-weight: 700;
    margin-top: 2px;
    color: var(--text);
  }}
  .kpi .hint {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 2px;
  }}
  .card {{
    background: #ffffff;
    border: 1px solid var(--border);
    padding: 14px;
    margin-bottom: 14px;
  }}
  .card h2, .card h3 {{
    margin: 0 0 8px 0;
    font-size: 1rem;
  }}
  .flow-chips {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  .chip {{
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 4px 8px;
    font-size: 0.8rem;
  }}
  .chip b {{ color: var(--text); }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.84rem;
  }}
  th, td {{
    padding: 6px 8px;
    text-align: left;
    border: 1px solid #dddddd;
    vertical-align: top;
  }}
  th {{
    color: var(--text);
    font-weight: 600;
    font-size: 0.78rem;
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
    padding: 1px 6px;
    font-size: 0.72rem;
    font-weight: 600;
    background: var(--badge-bg);
    border: 1px solid var(--border);
    color: var(--text);
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
    background: #fafafa;
    border-left: 3px solid #888888;
    padding: 10px 12px;
    margin: 8px 0 12px 0;
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
    background: #ffffff;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 5px 10px;
    cursor: pointer;
    font-size: 0.82rem;
  }}
  .btn:hover {{ background: #eeeeee; }}
  .muted {{ color: var(--muted); }}
  .table-wrap {{
    max-height: 500px;
    overflow: auto;
    border: 1px solid var(--border);
  }}
</style>
</head>
<body>
<nav style="padding:8px 20px;border-bottom:1px solid #ccc;font-size:13px;background:#fafafa;">
  <a href="../index.html" style="color:#0056b3;text-decoration:none;">&larr; Back to Analysis Portal</a> &middot;
  <a href="INTERFACES_REPORT.html" style="color:#0056b3;text-decoration:none;">INTERFACES_REPORT.html</a> &middot;
  <a href="INTERFACES_REPORT.md" style="color:#0056b3;text-decoration:none;">INTERFACES_REPORT.md</a>
</nav>
<header>
  <div>
    <h1>Riemann Proof — Cross-Boundary Mathematical Interface Browser</h1>
    <div class="sub">Self-contained explorer of cross-theory public API surfaces, declarations, and plain-English mathematics</div>
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
  <input id="globalSearch" type="search" placeholder="Filter directories, interface paths, Lean declarations, or math terms...">
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

<script id="iface-data" type="application/json">{json_blob}</script>
<script>
(function () {{
  const DATA = JSON.parse(document.getElementById("iface-data").textContent);
  const ANALYZED_MAP = new Map(DATA.analyzed_interfaces.map(x => [x.rel_path, x]));

  const state = {{
    mode: "analyzed",
    query: "",
    sort: "ext",
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
  const fileUrl = (rel, line) => "file:///home/ubuntu/riemann_proof/lean/src/" + encodeURI(rel) + (line ? "#L" + line : "");

  // Header stats
  document.getElementById("cntTop").textContent = DATA.top_dirs.length;
  document.getElementById("cntD2").textContent = DATA.depth2_dirs.length;
  document.getElementById("cntAn").textContent = DATA.analyzed_interfaces.length;
  document.getElementById("topStats").innerHTML = [
    `<span class="pill">Top-Level Theories: <b>${{DATA.top_dirs.length}}</b></span>`,
    `<span class="pill">Sub-Theories: <b>${{DATA.depth2_dirs.length}}</b></span>`,
    `<span class="pill">Analyzed Mathematical Interfaces: <b>${{DATA.analyzed_interfaces.length}}</b></span>`
  ].join("");

  function sortDirs(list) {{
    const arr = list.slice();
    switch (state.sort) {{
      case "name": arr.sort((a, b) => a.dir_key.localeCompare(b.dir_key)); break;
      default: arr.sort((a, b) => b.total_ext_imports - a.total_ext_imports || a.dir_key.localeCompare(b.dir_key));
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
          </div>
        </div>
      `).join("") || `<div style="padding:16px" class="muted">No analyzed files match "${{esc(state.query)}}".</div>`;
      listEl.querySelectorAll(".dir-item").forEach(el => {{
        el.onclick = () => {{ state.selectedFile = el.dataset.file; render(); }};
      }});
      return;
    }}

    const srcList = state.mode === "top" ? DATA.top_dirs : DATA.depth2_dirs;
    lblEl.textContent = state.mode === "top" ? "Top-Level Theories" : "Depth-2 Sub-Theories";
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
      return `
        <div class="dir-item ${{d.dir_key === state.selectedDir ? "active" : ""}}" data-dir="${{esc(d.dir_key)}}">
          <div class="dir-name">${{esc(d.dir_key)}}</div>
          <div class="dir-meta">
            <span>Parent: ${{esc(d.parent_key || "(root)")}}</span>
          </div>
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
            Sub-Theory: <b>${{esc(item.depth2_dir)}}</b>
          </div>
        </div>

        <div class="summary-box">${{esc(item.plain_english_summary)}}</div>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px;">
          <div>
            <div class="muted" style="font-size:0.78rem;margin-bottom:4px;">Used by Top-Level Theories</div>
            <div class="flow-chips">
              ${{topImps.map(([k]) => `<span class="chip"><b>${{esc(k)}}</b></span>`).join("") || '<span class="muted">None (apex)</span>'}}
            </div>
          </div>
          <div>
            <div class="muted" style="font-size:0.78rem;margin-bottom:4px;">Used by Depth-2 Sub-Theories</div>
            <div class="flow-chips">
              ${{d2Imps.slice(0, 12).map(([k]) => `<span class="chip"><b>${{esc(k)}}</b></span>`).join("") || '<span class="muted">None</span>'}}
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
          ${{matchedDirs.map(d => `<span class="chip" style="cursor:pointer;" data-jumpd2="${{esc(d.dir_key)}}"><b>${{esc(d.dir_key)}}</b></span>`).join("")}}
        </div>
        <div class="table-wrap">
          <table>
            <thead><tr><th>Interface Module</th><th>Sub-Theory</th><th>Status</th></tr></thead>
            <tbody>
              ${{matchedFiles.slice(0, 80).map(f => `
                <tr class="${{f.a ? "clickable" : ""}}" data-openan="${{f.a ? esc(f.p) : ""}}">
                  <td class="mono"><a class="filelink" href="${{fileUrl(f.p)}}" target="_blank">${{esc(f.p)}}</a></td>
                  <td>${{esc(f.d2)}}</td>
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
            ${{state.mode === "top" ? "Top-Level Theory" : "Depth-2 Sub-Theory"}}${{d.parent_key ? " · parent: " + esc(d.parent_key) : ""}}
          </div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;">
        <div class="card">
          <h3>Used By External Theories (${{d.importing_dirs.length}})</h3>
          <div class="flow-chips">
            ${{d.importing_dirs.map(x => `<span class="chip"><b>${{esc(x.dir)}}</b></span>`).join("") || '<span class="muted">No external dependents.</span>'}}
          </div>
        </div>
        <div class="card">
          <h3>Depends On External Theories (${{d.imported_external_dirs.length}})</h3>
          <div class="flow-chips">
            ${{d.imported_external_dirs.map(x => `<span class="chip"><b>${{esc(x.dir)}}</b></span>`).join("") || '<span class="muted">No external dependencies (self-contained / Mathlib only).</span>'}}
          </div>
        </div>
      </div>

      ${{activeAn ? renderAnalyzedDetail(activeAn, `<button class="btn" id="closeAnBtn">← Back to ${{esc(d.dir_key)}} summary</button>`) : ""}}

      ${{analyzedInDir.length ? `
        <div class="card">
          <h3>Analyzed Mathematical Interfaces in ${{esc(d.dir_key)}} (${{analyzedInDir.length}})</h3>
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
          <h3 style="margin:0;">Cross-Boundary Interface Modules (<span id="shownCount">showing ${{shown.length}}</span>)</h3>
          <input id="localFileFilter" type="search" value="${{esc(state.fileFilter)}}" placeholder="Filter modules inside this theory..." style="min-width:260px;">
        </div>
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

    function renderIfaceRows() {{
      const fq = state.fileFilter.trim().toLowerCase();
      const rows = d.interface_files.filter(f => {{
        if (fq && !f.p.toLowerCase().includes(fq)) return false;
        if (q && !d.dir_key.toLowerCase().includes(q) && !f.p.toLowerCase().includes(q)) return false;
        return true;
      }});
      const sc = document.getElementById("shownCount");
      if (sc) sc.textContent = `showing ${{rows.length}}`;
      const tb = document.getElementById("ifaceTbody");
      if (!tb) return;
      tb.innerHTML = rows.map((f, idx) => {{
        const eds = f.ed || {{}};
        const edStr = Object.keys(eds).slice(0, 4).join(", ");
        const moreEd = Object.keys(eds).length > 4 ? ` +${{Object.keys(eds).length - 4}}` : "";
        return `
          <tr class="${{f.a ? "clickable" : ""}}" data-pickan="${{f.a ? esc(f.p) : ""}}">
            <td class="muted">${{idx + 1}}</td>
            <td class="mono"><a class="filelink" href="${{fileUrl(f.p)}}" target="_blank">${{esc(f.p)}}</a></td>
            <td style="font-size:0.78rem;">${{esc(edStr + moreEd)}}</td>
            <td>${{f.a ? '<span class="badge">View Summary</span>' : '<span class="muted">-</span>'}}</td>
          </tr>
        `;
      }}).join("") || `<tr><td colspan="4" class="muted">No cross-boundary interface modules in this directory.</td></tr>`;
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
