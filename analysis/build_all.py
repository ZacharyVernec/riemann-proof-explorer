#!/usr/bin/env python3
"""
Incremental multi-version orchestrator for the Riemann Hypothesis Lean proof analysis portal.

Usage:
  python3 analysis/build_all.py                      # Build default version only + sync portal
  python3 analysis/build_all.py --version <id>       # Build a single version + sync portal
  python3 analysis/build_all.py --all                # Rebuild every version in versions.json + sync portal
  python3 analysis/build_all.py --only-sync          # Skip heavy builds; sync meta summaries, manifest, canonicals & HTML
  python3 analysis/build_all.py --version <id> --steps spine,blueprint --skip-existing

Adding a new Lean repo version:
  1. Append an entry to analysis/versions.json (set is_default: true on the newest one).
  2. Run `python3 analysis/build_all.py --version <new_id>` — older versions do not need to be rerun.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
ANALYSIS_DIR = Path(__file__).resolve().parent
VERSIONS_JSON = ANALYSIS_DIR / "versions.json"
VERSIONS_DIR = ANALYSIS_DIR / "versions"
PICKER_JS = ANALYSIS_DIR / "version_picker.js"
RENDER_REPORTS_JS = ANALYSIS_DIR / "render_reports.js"

ALL_STEPS = [
    "download",
    "index",
    "inventory",
    "spine",
    "blueprint",
    "interfaces",
    "dep_graphs",
    "full_dag",
    "histograms",
    "treemap",
]

PUBLIC_MANIFEST_KEYS = (
    "id",
    "label",
    "short_label",
    "date",
    "repo_name",
    "repo_url",
    "commit",
    "source_blob_base",
    "source_tree_base",
    "is_default",
)

CANONICAL_DEFAULT_FILES = [
    "data/meta.json",
    "blueprint/BLUEPRINT.md",
    "dependency_graph/README.md",
    "dependency_graph/top_level_graph.svg",
    "dependency_graph/depth2_major_graph.svg",
    "interfaces/INTERFACES_REPORT.md",
    "proof_spine/PROOF_SPINE_REPORT.md",
    "size_treemap/SIZE_ANALYSIS.md",
    "published_theorems/PUBLISHED_THEOREMS_INVENTORY.md",
    "full_dag/FULL_DAG.md",
    "codebase_histograms/CODEBASE_HISTOGRAMS.md",
]


def load_versions() -> list[dict[str, Any]]:
    data = json.loads(VERSIONS_JSON.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"Expected non-empty JSON list in {VERSIONS_JSON}")
    return data


def get_default_version(versions: list[dict[str, Any]]) -> dict[str, Any]:
    for v in versions:
        if v.get("is_default"):
            return v
    return versions[0]


def write_if_changed(path: Path, text: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def run_cmd(cmd: list[str], cwd: Path = ROOT) -> None:
    pretty = " ".join(str(c) for c in cmd)
    print(f"  $ {pretty}")
    subprocess.run(cmd, cwd=cwd, check=True)


def download_version_source(ver: dict[str, Any], skip_existing: bool) -> None:
    src_dir = ROOT / ver["local_src_dir"]
    if src_dir.is_dir() and any(src_dir.glob("*.lean")):
        if skip_existing or not ver.get("tarball_url"):
            print(f"[download] Using existing Lean source at {src_dir.relative_to(ROOT)}")
            return
        print(f"[download] Lean source already present at {src_dir.relative_to(ROOT)}; skipping re-download.")
        return

    tar_url = ver.get("tarball_url")
    if not tar_url:
        raise FileNotFoundError(
            f"Source directory {src_dir} does not exist and no tarball_url is configured for version '{ver['id']}'."
        )

    repo_dir = ROOT / ver["local_repo_dir"]
    repo_dir.parent.mkdir(parents=True, exist_ok=True)
    tmp_tgz = repo_dir.parent / f".tmp_{ver['id']}.tar.gz"
    tmp_extract = repo_dir.parent / f".tmp_extract_{ver['id']}"
    if tmp_extract.exists():
        shutil.rmtree(tmp_extract)
    tmp_extract.mkdir(parents=True, exist_ok=True)

    print(f"[download] Fetching {tar_url} ...")
    req = urllib.request.Request(tar_url, headers={"User-Agent": "riemann-proof-explorer-build/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=180) as resp, open(tmp_tgz, "wb") as out_f:
            shutil.copyfileobj(resp, out_f)

        resolved_base = tmp_extract.resolve()
        with tarfile.open(tmp_tgz, "r:gz") as tf:
            for member in tf.getmembers():
                raw_parts = [p for p in Path(member.name).parts if p not in ("", ".")]
                if not raw_parts or len(raw_parts) < 2:
                    continue
                if raw_parts[0].startswith("/") or ".." in raw_parts:
                    raise RuntimeError(f"Unsafe tar member path: {member.name}")
                rel = Path(*raw_parts[1:])  # strip top-level GitHub repo-sha/ directory
                target = (tmp_extract / rel).resolve()
                if not target.is_relative_to(resolved_base):
                    raise RuntimeError(f"Tar path traversal blocked: {member.name}")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    src_f = tf.extractfile(member)
                    if src_f is not None:
                        with src_f, open(target, "wb") as dst_f:
                            shutil.copyfileobj(src_f, dst_f)

        if not (tmp_extract / "src").is_dir():
            raise RuntimeError(f"Extracted archive for '{ver['id']}' missing expected 'src/' directory")
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        tmp_extract.rename(repo_dir)
        print(f"[download] Extracted Lean source into {repo_dir.relative_to(ROOT)}")
    finally:
        if tmp_tgz.exists():
            tmp_tgz.unlink()
        if tmp_extract.exists():
            shutil.rmtree(tmp_extract, ignore_errors=True)


def step_outputs_exist(ver_dir: Path, step: str, ver: dict[str, Any]) -> bool:
    if step == "download":
        src_dir = ROOT / ver["local_src_dir"]
        return src_dir.is_dir() and any(src_dir.glob("*.lean"))
    required_map: dict[str, list[Path]] = {
        "index": [ver_dir / "data" / "graph.sqlite", ver_dir / "data" / "meta.json"],
        "inventory": [ver_dir / "published_theorems" / "PUBLISHED_THEOREMS_INVENTORY.md"],
        "spine": [
            ver_dir / "proof_spine" / "spine_metrics.json",
            ver_dir / "proof_spine" / "spine_dashboard_data.js",
            ver_dir / "proof_spine" / "PROOF_SPINE_REPORT.md",
        ],
        "blueprint": [
            ver_dir / "blueprint" / "blueprint_data.json",
            ver_dir / "blueprint" / "blueprint_data.js",
            ver_dir / "blueprint" / "BLUEPRINT.md",
        ],
        "interfaces": [
            ver_dir / "interfaces" / "interfaces.json",
            ver_dir / "interfaces" / "interface_browser_data.js",
            ver_dir / "interfaces" / "INTERFACES_REPORT.md",
        ],
        "dep_graphs": [
            ver_dir / "dependency_graph" / "dir_graph.json",
            ver_dir / "dependency_graph" / "dir_graph_data.js",
            ver_dir / "dependency_graph" / "top_level_graph.svg",
            ver_dir / "dependency_graph" / "depth2_major_graph.svg",
            ver_dir / "dependency_graph" / "README.md",
        ],
        "full_dag": [
            ver_dir / "full_dag" / "full_dag_data.js",
            ver_dir / "full_dag" / "layout_summary.json",
            ver_dir / "full_dag" / "FULL_DAG.md",
        ],
        "histograms": [
            ver_dir / "codebase_histograms" / "histograms_data.json",
            ver_dir / "codebase_histograms" / "histograms_data.js",
            ver_dir / "codebase_histograms" / "CODEBASE_HISTOGRAMS.md",
        ],
        "treemap": [
            ver_dir / "size_treemap" / "hierarchy_sizes.json",
            ver_dir / "size_treemap" / "hierarchy_data.js",
            ver_dir / "size_treemap" / "SIZE_ANALYSIS.md",
        ],
    }
    paths = required_map.get(step, [])
    return bool(paths) and all(p.exists() and p.stat().st_size > 0 for p in paths)


def build_version(ver: dict[str, Any], steps: list[str], skip_existing: bool, write_html: bool) -> None:
    vid = ver["id"]
    ver_dir = VERSIONS_DIR / vid
    src_dir = ROOT / ver["local_src_dir"]
    rel_src_label = "lean/src/" if ver["local_src_dir"] == "lean/src" else "src/"
    blob_base = ver["source_blob_base"]

    data_dir = ver_dir / "data"
    db_path = data_dir / "graph.sqlite"
    meta_path = data_dir / "meta.json"
    inv_md = ver_dir / "published_theorems" / "PUBLISHED_THEOREMS_INVENTORY.md"
    spine_metrics = ver_dir / "proof_spine" / "spine_metrics.json"

    print(f"\n=== Building version: {vid} ({ver['label']}) ===")
    py = sys.executable

    for step in steps:
        if skip_existing and step_outputs_exist(ver_dir, step, ver):
            print(f"[{vid}] Skipping '{step}' (--skip-existing)")
            continue

        t0 = time.time()
        print(f"[{vid}] Running step: {step}")

        if step == "download":
            download_version_source(ver, skip_existing)
        elif step == "index":
            run_cmd([py, str(ANALYSIS_DIR / "build_index.py"), "--src-dir", str(src_dir), "--out-dir", str(data_dir)])
        elif step == "inventory":
            run_cmd([
                py,
                str(ANALYSIS_DIR / "published_theorems" / "build_inventory.py"),
                "--src-dir", str(src_dir),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--out-dir", str(ver_dir / "published_theorems"),
                "--version-label", vid,
                "--rel-src-label", rel_src_label,
            ])
        elif step == "spine":
            run_cmd([
                py,
                str(ANALYSIS_DIR / "proof_spine" / "analyze_spine.py"),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--out-dir", str(ver_dir / "proof_spine"),
            ])
            cmd = [
                py,
                str(ANALYSIS_DIR / "proof_spine" / "build_dashboard.py"),
                "--metrics-path", str(spine_metrics),
                "--out-dir", str(ver_dir / "proof_spine"),
                "--version-label", vid,
                "--source-blob-base", blob_base,
            ]
            if write_html:
                cmd.append("--write-html")
            run_cmd(cmd)
        elif step == "blueprint":
            run_cmd([
                py,
                str(ANALYSIS_DIR / "blueprint" / "build_blueprint.py"),
                "--src-dir", str(src_dir),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--spine-metrics", str(spine_metrics),
                "--out-dir", str(ver_dir / "blueprint"),
                "--version-label", vid,
                "--source-blob-base", blob_base,
                "--rel-src-label", rel_src_label,
            ])
        elif step == "interfaces":
            cmd = [
                py,
                str(ANALYSIS_DIR / "interfaces" / "extract_interfaces.py"),
                "--src-dir", str(src_dir),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--out-dir", str(ver_dir / "interfaces"),
                "--github-blob-base", blob_base,
                "--version-label", vid,
                "--rel-src-label", rel_src_label,
            ]
            if write_html:
                cmd.append("--write-html")
            run_cmd(cmd)
        elif step == "dep_graphs":
            cmd = [
                py,
                str(ANALYSIS_DIR / "dependency_graph" / "build_dep_graphs.py"),
                "--src-dir", str(src_dir),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--out-dir", str(ver_dir / "dependency_graph"),
                "--version-label", vid,
                "--source-blob-base", blob_base,
                "--rel-src-label", rel_src_label,
            ]
            if write_html:
                cmd.append("--write-html")
            run_cmd(cmd)
        elif step == "full_dag":
            run_cmd([
                py,
                str(ANALYSIS_DIR / "full_dag" / "build_full_dag.py"),
                "--src-dir", str(src_dir),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--out-dir", str(ver_dir / "full_dag"),
                "--inventory-path", str(inv_md),
                "--version-label", vid,
                "--rel-src-label", rel_src_label,
            ])
        elif step == "histograms":
            run_cmd([
                py,
                str(ANALYSIS_DIR / "codebase_histograms" / "build_histograms.py"),
                "--src-dir", str(src_dir),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--out-dir", str(ver_dir / "codebase_histograms"),
                "--version-label", vid,
                "--rel-src-label", rel_src_label,
            ])
        elif step == "treemap":
            run_cmd([
                py,
                str(ANALYSIS_DIR / "size_treemap" / "build_hierarchy.py"),
                "--db-path", str(db_path),
                "--meta-path", str(meta_path),
                "--out-dir", str(ver_dir / "size_treemap"),
                "--version-label", vid,
                "--rel-src-label", rel_src_label,
            ])
        else:
            raise ValueError(f"Unknown build step: {step}")

        print(f"[{vid}] Finished '{step}' in {time.time() - t0:.2f}s")


def write_meta_summary_js(ver: dict[str, Any]) -> None:
    vid = ver["id"]
    ver_dir = VERSIONS_DIR / vid
    meta_path = ver_dir / "data" / "meta.json"
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    bp_nodes = None
    bp_path = ver_dir / "blueprint" / "blueprint_data.json"
    if bp_path.exists():
        bp = json.loads(bp_path.read_text(encoding="utf-8"))
        bp_nodes = bp.get("meta", {}).get("node_count") or len(bp.get("nodes", []))

    summary = {
        "version": vid,
        "reachable_files": meta.get("reachable_files", meta.get("total_files", 0)),
        "unreachable_files": meta.get("unreachable_files", 0),
        "total_files": meta.get("total_files", 0),
        "reachable_internal_edges": meta.get("reachable_internal_edges", meta.get("internal_edges", 0)),
        "total_internal_edges": meta.get("total_internal_edges", meta.get("internal_edges", 0)),
        "reachable_decl_counts": meta.get("reachable_decl_counts", meta.get("decl_counts", {})),
        "decl_counts": meta.get("decl_counts", {}),
        "max_reachable_height_from_leaves": meta.get("max_reachable_height_from_leaves", meta.get("max_height_from_leaves", 0)),
        "max_height_from_leaves": meta.get("max_height_from_leaves", 0),
        "max_dist_from_main": meta.get("max_dist_from_main", 0),
        "is_dag": bool(meta.get("is_dag", True)),
        "blueprint_nodes": bp_nodes,
    }
    js_path = ver_dir / "data" / "meta_summary.js"
    js_text = "window.__META_SUMMARY__ = " + json.dumps(summary, separators=(",", ":"), ensure_ascii=False) + ";\n"
    if write_if_changed(js_path, js_text):
        print(f"[sync] Wrote {js_path.relative_to(ROOT)}")


def sync_version_picker_manifest(versions: list[dict[str, Any]]) -> None:
    text = PICKER_JS.read_text(encoding="utf-8")
    start_marker = "/*VERSIONS_MANIFEST_START*/"
    end_marker = "/*VERSIONS_MANIFEST_END*/"
    if start_marker not in text or end_marker not in text:
        raise RuntimeError(f"Missing manifest markers in {PICKER_JS}")

    public_entries = [{k: v[k] for k in PUBLIC_MANIFEST_KEYS if k in v} for v in versions]
    manifest_json = json.dumps(public_entries, indent=2, ensure_ascii=False)
    indented = "\n".join("  " + line if line else "" for line in f"const MANIFEST = {manifest_json};".splitlines())
    replacement = f"  {start_marker}\n{indented}\n  {end_marker}"

    pattern = re.compile(r"[ \t]*" + re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    new_text, count = pattern.subn(replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Failed substituting manifest block in {PICKER_JS}")
    if write_if_changed(PICKER_JS, new_text):
        print(f"[sync] Updated manifest in {PICKER_JS.relative_to(ROOT)}")


def sync_default_canonicals(default_ver: dict[str, Any]) -> None:
    vid = default_ver["id"]
    ver_dir = VERSIONS_DIR / vid
    if not ver_dir.is_dir():
        raise FileNotFoundError(f"Default version directory does not exist: {ver_dir}")

    for rel in CANONICAL_DEFAULT_FILES:
        src = ver_dir / rel
        dst = ANALYSIS_DIR / rel
        if not src.exists():
            print(f"[sync] WARNING: Missing default asset {src.relative_to(ROOT)}; skipping canonical sync")
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        src_bytes = src.read_bytes()
        if not dst.exists() or dst.read_bytes() != src_bytes:
            dst.write_bytes(src_bytes)
            print(f"[sync] Synced {dst.relative_to(ROOT)} <- versions/{vid}/{rel}")


def sync_portal(versions: list[dict[str, Any]]) -> None:
    print("\n=== Syncing portal assets ===")
    for ver in versions:
        write_meta_summary_js(ver)
    sync_version_picker_manifest(versions)
    sync_default_canonicals(get_default_version(versions))
    run_cmd(["node", str(RENDER_REPORTS_JS)])


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Incremental orchestrator for rebuilding one (or all) Lean repo versions and syncing the analysis portal."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--version", type=str, help="Build only the specified version ID from analysis/versions.json.")
    group.add_argument("--all", action="store_true", help="Rebuild every version listed in analysis/versions.json.")
    group.add_argument("--only-sync", action="store_true", help="Skip analysis steps; only sync metadata/manifest/canonicals/HTML.")
    parser.add_argument(
        "--steps",
        type=str,
        default=",".join(ALL_STEPS),
        help=f"Comma-separated subset of steps to run (default: all). Choices: {','.join(ALL_STEPS)}",
    )
    parser.add_argument("--skip-existing", action="store_true", help="Skip steps whose outputs already exist for the target version.")
    parser.add_argument("--write-html", action="store_true", help="Also regenerate explorer HTML shells from builder templates where supported.")
    args = parser.parse_args()

    versions = load_versions()
    by_id = {v["id"]: v for v in versions}

    steps = [s.strip() for s in args.steps.split(",") if s.strip()]
    invalid = [s for s in steps if s not in ALL_STEPS]
    if invalid:
        raise SystemExit(f"Invalid --steps: {', '.join(invalid)}. Valid: {', '.join(ALL_STEPS)}")

    if not args.only_sync:
        if args.all:
            targets = versions
        elif args.version:
            if args.version not in by_id:
                raise SystemExit(f"Unknown version '{args.version}'. Available: {', '.join(by_id)}")
            targets = [by_id[args.version]]
        else:
            targets = [get_default_version(versions)]
            print(f"No --version or --all specified; targeting default version '{targets[0]['id']}' only.")

        for ver in targets:
            build_version(ver, steps, skip_existing=args.skip_existing, write_html=args.write_html)

    sync_portal(versions)
    print("\nAll requested tasks completed cleanly.")


if __name__ == "__main__":
    main()
