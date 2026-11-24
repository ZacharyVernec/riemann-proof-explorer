#!/usr/bin/env python3
"""
Generate versioned blueprint_data.json, blueprint_data.js, and BLUEPRINT.md
from graph.sqlite, meta.json, spine_metrics.json, and milestones_spec.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_SPEC = SCRIPT_DIR / "milestones_spec.json"


def load_dom_map(spine_path: Path | None) -> tuple[dict[str, int], dict[str, int]]:
    """Return (rel_path -> dom_subtree_size, rel_path -> dom_rank)."""
    if not spine_path or not spine_path.exists():
        return {}, {}
    m = json.loads(spine_path.read_text(encoding="utf-8"))
    dom_sz: dict[str, int] = {}
    dom_rk: dict[str, int] = {}
    for x in m.get("dominators", {}).get("skeleton_ge_300", []):
        dom_sz[x["rel_path"]] = int(x["dom_subtree_size"])
    for x in m.get("dominators", {}).get("top_100_bottlenecks", []):
        dom_sz[x["rel_path"]] = int(x["dom_subtree_size"])
        dom_rk[x["rel_path"]] = int(x["rank"])
    for x in m.get("leaf_and_entry_audit", {}).get("entry_layers_dist_le_3", []):
        dom_sz.setdefault(x["rel_path"], int(x.get("dom_subtree_size", 1)))
    return dom_sz, dom_rk


def resolve_milestone(
    spec_node: dict[str, Any],
    reach_mods: dict[str, tuple[int, str, int, int, int, int, int]],
    file_decls: dict[str, list[tuple[str, str, int]]],
    sym_full: dict[str, list[tuple[str, str, str, int]]],
    sym_short: dict[str, list[tuple[str, str, str, int]]],
    dom_sz: dict[str, int],
) -> tuple[str, str, int, bool] | None:
    """Resolve (lean_file, lean_symbol, line_no, was_relocated) or None if absent."""
    orig_file = spec_node.get("lean_file", "")
    cands = [c for c in spec_node.get("symbol_candidates", []) if c]

    # Step A: exact file match in reachable modules
    if orig_file in reach_mods:
        decls = file_decls.get(orig_file, [])
        for cand in cands:
            for fname, _kind, ln in decls:
                if fname == cand:
                    return orig_file, fname, ln, False
        for cand in cands:
            short = cand.rsplit(".", 1)[-1]
            for fname, _kind, ln in decls:
                if fname.rsplit(".", 1)[-1] == short:
                    return orig_file, fname, ln, False
        # File exists & reachable, symbol renamed internally
        if decls:
            for fname, kind, ln in decls:
                if kind in ("theorem", "def", "structure", "abbrev"):
                    return orig_file, fname, ln, False
            fname, _kind, ln = decls[0]
            return orig_file, fname, ln, False
        return orig_file, (cands[0] if cands else spec_node.get("lean_symbol", "")), 1, False

    # Step B: relocate via symbol_candidates across reachable declarations
    matches: list[tuple[str, str, str, int]] = []
    for cand in cands:
        if cand in sym_full:
            matches.extend(sym_full[cand])
    if not matches:
        for cand in cands:
            short = cand.rsplit(".", 1)[-1]
            if short in sym_short:
                matches.extend(sym_short[short])

    if not matches:
        return None

    def score_match(m: tuple[str, str, str, int]) -> tuple[int, int, int, int]:
        full, kind, rel, _ln = m
        in_defs = 1 if "/Definitions/" in rel else 0
        exact_name = 0 if full in cands else 1
        dsize = dom_sz.get(rel, 0)
        pref_kind = 0 if kind in ("theorem", "def", "abbrev", "structure") else 1
        return (exact_name, in_defs, pref_kind, -dsize)

    best = min(matches, key=score_match)
    return best[2], best[0], best[3], True


def rewire_dependencies(
    orig_order: list[str],
    orig_deps_map: dict[str, list[str]],
    kept_ids: set[str],
) -> dict[str, list[str]]:
    """Transitively rewire dependency edges through dropped intermediate nodes."""
    rewired: dict[str, list[str]] = {}
    for nid in orig_order:
        if nid not in kept_ids:
            continue
        direct_kept: list[str] = []
        seen_kept: set[str] = set()
        visited_dropped: set[str] = set()
        q: deque[str] = deque(orig_deps_map.get(nid, []))
        while q:
            dep = q.popleft()
            if dep == nid:
                continue
            if dep in kept_ids:
                if dep not in seen_kept:
                    seen_kept.add(dep)
                    direct_kept.append(dep)
            elif dep not in visited_dropped:
                visited_dropped.add(dep)
                for nxt in orig_deps_map.get(dep, []):
                    if nxt != nid:
                        q.append(nxt)
        rewired[nid] = direct_kept
    return rewired


def verify_acyclic(nodes: list[dict[str, Any]]) -> None:
    adj = {n["id"]: n["depends_on"] for n in nodes}
    color: dict[str, int] = {}

    def dfs(u: str) -> None:
        color[u] = 1
        for v in adj.get(u, []):
            st = color.get(v, 0)
            if st == 1:
                raise RuntimeError(f"Cycle detected in blueprint DAG at edge {u} -> {v}")
            if st == 0:
                dfs(v)
        color[u] = 2

    for nid in adj:
        if color.get(nid, 0) == 0:
            dfs(nid)


def refresh_notes(
    orig_notes: str,
    rel_path: str,
    orig_file: str,
    relocated: bool,
    out_deg: int,
    dist_main: int,
    height_leaves: int,
    dom_sz_val: int | None,
    dom_rk_val: int | None,
    clumped_into: str | None,
) -> str:
    note = orig_notes or ""
    # Replace dynamic tuple when present
    if dom_rk_val is not None and dom_sz_val is not None:
        note = re.sub(
            r"Rank \d+ dominator \(out_degree=\d+,\s*dist=\d+,\s*height=\d+\)\.",
            f"Rank {dom_rk_val} dominator (dom_subtree={dom_sz_val:,}, out_degree={out_deg}, dist={dist_main}, height={height_leaves}).",
            note,
        )
    if relocated and orig_file != rel_path:
        orig_base = Path(orig_file).name
        note = (f"{note} " if note else "") + f"[Relocated from {orig_base} to {rel_path}]"
    if clumped_into:
        note = (f"{note} " if note else "") + f"[Shares module {Path(clumped_into).name}]"
    return note.strip()


def render_blueprint_md(
    bp_data: dict[str, Any],
    dropped_titles: list[tuple[int, str, str]],
    source_blob_base: str = "",
    version_label: str = "",
) -> str:
    meta = bp_data["meta"]
    nodes = bp_data["nodes"]
    by_id = {n["id"]: n for n in nodes}
    edges_count = sum(len(n["depends_on"]) for n in nodes)

    def mlink(rel_path: str, line_no: int | None = None, label: str | None = None) -> str:
        text = label or f"{rel_path}" + (f"#L{line_no}" if line_no else "")
        if source_blob_base:
            frag = f"#L{line_no}" if line_no else ""
            return f"[{text}]({source_blob_base.rstrip('/')}/{rel_path}{frag})"
        return f"`{rel_path}`" + (f" (L{line_no})" if line_no else "")

    ver_note = f" (`{version_label}`)" if version_label else ""
    lines: list[str] = []
    lines.append(f"# Formalized Proof Blueprint: Riemann Hypothesis & Generalized Riemann Hypothesis{ver_note}")
    lines.append("")
    lines.append(
        f"This blueprint distills the Lean proof DAG (**{meta['total_modules']:,} reachable modules**, **{meta['total_lines']:,} lines**, **{meta['total_internal_edges']:,} internal dependency edges**) into **{meta['node_count']} mathematical milestones** across **5 architectural stages** (Stages 0–4) connected by **{edges_count} dependency links** (interactive DAG in [blueprint.html](blueprint.html))."
    )
    lines.append("")
    lines.append("> **Direction Convention:** Stage 0 sits at the apex (`Main.lean`); arrows `A → B` mean milestone `A` depends directly on prerequisite `B`.")
    lines.append("")

    for st in meta["stages"]:
        st_nodes = [n for n in nodes if n["stage"] == st["stage"]]
        if not st_nodes:
            continue
        lines.append("---")
        lines.append("")
        lines.append(f"## Stage {st['stage']}: {st['label']} ({len(st_nodes)} milestones)")
        lines.append("")
        lines.append(st["description"])
        lines.append("")
        for n in st_nodes:
            deps_str = ", ".join(f"`{by_id[d]['title']}`" for d in n["depends_on"] if d in by_id) or "None (foundation)"
            dom_str = f" · Dominates **{n['dom_subtree_size']:,}** modules" if n.get("dom_subtree_size") else ""
            lines.append(f"### {n['title']} (`{n['id']}`)")
            lines.append("")
            if n.get("hide_lean") and n.get("explanation"):
                short = n["explanation"]["short"]
                lines.append(f"- **Statement:** {short['statement']}")
                lines.append(f"- **Assumptions:** {short['assumptions']}")
                lines.append(f"- **Proof strategy:** {short['proof_strategy']}")
            else:
                lines.append(f"{n['plain_english']}")
                lines.append("")
                if n.get("math_statement"):
                    lines.append(f"- **Mathematical form:** `{n['math_statement']}`")
            lines.append(f"- **Lean anchor:** `{n['lean_symbol']}` in {mlink(n['lean_file'], n['line_no'])}{dom_str}")
            lines.append(f"- **Depends on:** {deps_str}")
            if n.get("notes"):
                lines.append(f"- **Notes:** {n['notes']}")
            lines.append("")

    if dropped_titles:
        lines.append("---")
        lines.append("")
        lines.append("## Baseline Milestones Merged or Removed in This Version")
        lines.append("")
        lines.append(
            f"The following **{len(dropped_titles)}** baseline milestones were merged, inlined, or eliminated in `{meta.get('codebase_root', 'src/')}` (prerequisite edges were transitively rewired across kept milestones):"
        )
        lines.append("")
        for st_num, nid, title in dropped_titles:
            lines.append(f"- **Stage {st_num}** (`{nid}`): {title}")
        lines.append("")

    return "\n".join(lines) + "\n"


def build_blueprint(args: argparse.Namespace) -> None:
    spec = json.loads(args.spec_path.read_text(encoding="utf-8"))
    meta = json.loads(args.meta_path.read_text(encoding="utf-8"))
    dom_sz, dom_rk = load_dom_map(args.spine_metrics)

    conn = sqlite3.connect(f"file:{args.db_path}?mode=ro", uri=True)
    cur = conn.cursor()

    reach_mods: dict[str, tuple[int, str, int, int, int, int, int]] = {}
    for mid, rel, lines_cnt, dist_m, height_l, in_deg_m, out_deg in cur.execute(
        """
        SELECT id, rel_path, lines, dist_from_main, height_from_leaves, in_degree_main, out_degree
        FROM modules WHERE reachable_from_main = 1
        """
    ):
        reach_mods[rel] = (mid, rel, lines_cnt, dist_m, height_l, in_deg_m, out_deg)

    # Filter out_degree to reachable targets if needed
    id_to_rel = {v[0]: rel for rel, v in reach_mods.items()}
    reach_out_deg: dict[str, int] = defaultdict(int)
    for src_id, dst_id in cur.execute("SELECT src_id, dst_id FROM edges"):
        if src_id in id_to_rel and dst_id in id_to_rel:
            reach_out_deg[id_to_rel[src_id]] += 1

    file_decls: dict[str, list[tuple[str, str, int]]] = defaultdict(list)
    sym_full: dict[str, list[tuple[str, str, str, int]]] = defaultdict(list)
    sym_short: dict[str, list[tuple[str, str, str, int]]] = defaultdict(list)
    for full_name, kind, rel, ln in cur.execute(
        """
        SELECT d.name, d.kind, m.rel_path, d.line_no
        FROM declarations d
        JOIN modules m ON m.id = d.module_id
        WHERE m.reachable_from_main = 1
        ORDER BY d.line_no ASC
        """
    ):
        file_decls[rel].append((full_name, kind, ln))
        sym_full[full_name].append((full_name, kind, rel, ln))
        sym_short[full_name.rsplit(".", 1)[-1]].append((full_name, kind, rel, ln))
    conn.close()

    orig_order = [n["id"] for n in spec["nodes"]]
    orig_deps_map = {n["id"]: list(n.get("depends_on", [])) for n in spec["nodes"]}

    resolved_map: dict[str, tuple[dict[str, Any], str, str, int, bool]] = {}
    dropped: list[tuple[int, str, str]] = []
    for sn in spec["nodes"]:
        res = resolve_milestone(sn, reach_mods, file_decls, sym_full, sym_short, dom_sz)
        if res is None:
            dropped.append((sn["stage"], sn["id"], sn["title"]))
        else:
            rel_path, actual_sym, line_no, relocated = res
            resolved_map[sn["id"]] = (sn, rel_path, actual_sym, line_no, relocated)

    kept_ids = set(resolved_map.keys())
    rewired_deps = rewire_dependencies(orig_order, orig_deps_map, kept_ids)

    # Track unique dominator badge ownership per lean_file
    seen_dom_files: dict[str, str] = {}
    out_nodes: list[dict[str, Any]] = []
    for nid in orig_order:
        if nid not in resolved_map:
            continue
        sn, rel_path, actual_sym, line_no, relocated = resolved_map[nid]
        mod_info = reach_mods[rel_path]
        dist_m, height_l = mod_info[3], mod_info[4]
        out_deg = reach_out_deg.get(rel_path, mod_info[6])
        raw_dom = dom_sz.get(rel_path)
        clumped_owner = seen_dom_files.get(rel_path)
        if clumped_owner is None:
            seen_dom_files[rel_path] = nid
            dom_val = raw_dom if (raw_dom is not None and raw_dom > 1) else None
            clumped_note = None
        else:
            dom_val = None
            clumped_note = rel_path if relocated else None

        node_obj = dict(sn)
        node_obj.pop("symbol_candidates", None)
        node_obj["lean_file"] = rel_path
        node_obj["lean_symbol"] = actual_sym
        node_obj["line_no"] = line_no
        node_obj["depends_on"] = rewired_deps[nid]
        node_obj["dom_subtree_size"] = dom_val
        node_obj["notes"] = refresh_notes(
            sn.get("notes", ""),
            rel_path,
            sn.get("lean_file", ""),
            relocated,
            out_deg,
            dist_m,
            height_l,
            dom_val,
            dom_rk.get(rel_path) if dom_val else None,
            clumped_note,
        )
        out_nodes.append(node_obj)

    verify_acyclic(out_nodes)

    bp_data = {
        "meta": {
            "title": "Formalized Proof Blueprint: Riemann Hypothesis & Generalized Riemann Hypothesis",
            "version_label": args.version_label or "",
            "codebase_root": args.rel_src_label or str(args.src_dir),
            "total_modules": int(meta.get("reachable_files", len(reach_mods))),
            "total_lines": int(meta.get("reachable_lines", meta.get("total_lines", 0))),
            "total_internal_edges": int(meta.get("reachable_internal_edges", meta.get("total_internal_edges", 0))),
            "is_dag": bool(meta.get("is_dag", True)),
            "node_count": len(out_nodes),
            "stages": spec["stages"],
            "theory_groups": spec["theory_groups"],
        },
        "nodes": out_nodes,
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.out_dir / "blueprint_data.json"
    js_path = args.out_dir / "blueprint_data.js"
    md_path = args.out_dir / "BLUEPRINT.md"

    json_str = json.dumps(bp_data, indent=2, ensure_ascii=False)
    json_path.write_text(json_str + "\n", encoding="utf-8")
    compact_js = json.dumps(bp_data, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
    js_path.write_text(f"window.__BLUEPRINT_DATA__ = {compact_js};\n", encoding="utf-8")
    md_path.write_text(
        render_blueprint_md(bp_data, dropped, source_blob_base=args.source_blob_base, version_label=args.version_label),
        encoding="utf-8",
    )
    print(
        f"Wrote {args.out_dir}/blueprint_data.{{json,js}} & BLUEPRINT.md: "
        f"{len(out_nodes)}/{len(orig_order)} milestones ({len(dropped)} dropped, "
        f"{sum(len(n['depends_on']) for n in out_nodes)} edges)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build versioned Proof Blueprint JSON/JS/MD")
    parser.add_argument("--src-dir", type=Path, default=ROOT / "lean" / "src")
    parser.add_argument("--db-path", type=Path, default=ROOT / "analysis" / "data" / "graph.sqlite")
    parser.add_argument("--meta-path", type=Path, default=ROOT / "analysis" / "data" / "meta.json")
    parser.add_argument("--spine-metrics", type=Path, default=ROOT / "analysis" / "proof_spine" / "spine_metrics.json")
    parser.add_argument("--out-dir", type=Path, default=SCRIPT_DIR)
    parser.add_argument("--spec-path", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--version-label", type=str, default="")
    parser.add_argument("--source-blob-base", type=str, default="")
    parser.add_argument("--rel-src-label", type=str, default="src/")
    args = parser.parse_args()
    build_blueprint(args)


if __name__ == "__main__":
    main()
