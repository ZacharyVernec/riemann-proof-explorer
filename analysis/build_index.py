#!/usr/bin/env python3
"""Build canonical SQLite graph index and meta.json for lean/src."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

ROOT = Path("/home/ubuntu/riemann_proof")
SRC_DIR = ROOT / "lean" / "src"
OUT_DIR = ROOT / "analysis" / "data"
DB_PATH = OUT_DIR / "graph.sqlite"
META_PATH = OUT_DIR / "meta.json"

EXTERNAL_PREFIXES = {"Mathlib", "Batteries", "Lean"}

DECL_RE = re.compile(
    rb'^(?:@\[.*?\]\s*)?(?:(?:private|protected|noncomputable|partial|unsafe|scoped|local)\s+)*'
    rb'(theorem|lemma|def|structure|class|inductive|abbrev|axiom|opaque|instance)\s+([^\s:(\[{]+)'
)


def dir_levels(dir_path: str) -> tuple[str, str, str]:
    if not dir_path:
        return "(root)", "(root)", "(root)"
    parts = dir_path.split("/")
    top = parts[0]
    d2 = "/".join(parts[:2]) if len(parts) >= 2 else dir_path
    d3 = "/".join(parts[:3]) if len(parts) >= 3 else dir_path
    return top, d2, d3


def main() -> None:
    t0 = time.time()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    # Phase 1: Discover all .lean files deterministically
    rel_paths: list[str] = []
    src_str = str(SRC_DIR)
    for dirpath, _, filenames in os.walk(src_str):
        for fn in filenames:
            if fn.endswith(".lean"):
                full = os.path.join(dirpath, fn)
                rel = os.path.relpath(full, src_str).replace(os.sep, "/")
                rel_paths.append(rel)
    rel_paths.sort()

    n_mod = len(rel_paths)
    name_to_id: dict[str, int] = {}
    mod_names: list[str] = [""] * n_mod
    mod_dirs: list[tuple[str, str, str, str]] = []

    for idx, rel in enumerate(rel_paths):
        mod_id = idx + 1
        mod_name = rel[:-5].replace("/", ".")
        name_to_id[mod_name] = mod_id
        mod_names[idx] = mod_name
        dpath = os.path.dirname(rel)
        top, d2, d3 = dir_levels(dpath)
        mod_dirs.append((dpath, top, d2, d3))

    print(f"Discovered {n_mod} .lean files in {time.time() - t0:.2f}s")

    # Phase 2: Parse imports, line/byte counts, and declarations
    t1 = time.time()
    raw_imports: list[list[str]] = [[] for _ in range(n_mod)]
    ext_imports: list[list[str]] = [[] for _ in range(n_mod)]
    unresolved_imports: list[dict[str, str]] = []
    ext_counts: Counter[str] = Counter()
    decl_counts: Counter[str] = Counter()

    lines_arr = [0] * n_mod
    bytes_arr = [0] * n_mod
    n_thm = [0] * n_mod
    n_lem = [0] * n_mod
    n_def = [0] * n_mod
    n_str = [0] * n_mod
    n_oth = [0] * n_mod

    decl_rows: list[tuple[int, str, str, int]] = []
    adj_out: list[list[int]] = [[] for _ in range(n_mod)]
    adj_in: list[list[int]] = [[] for _ in range(n_mod)]
    edges_list: list[tuple[int, int]] = []

    for idx, rel in enumerate(rel_paths):
        mod_id = idx + 1
        full_path = os.path.join(src_str, rel)
        with open(full_path, "rb") as f:
            data = f.read()
        bytes_arr[idx] = len(data)
        split_lines = data.splitlines()
        lines_arr[idx] = len(split_lines)

        seen_dst: set[int] = set()
        exts: list[str] = []
        for lineno, line in enumerate(split_lines, 1):
            if line.startswith(b"import "):
                parts = line.decode("utf-8", errors="replace").strip().split()
                if len(parts) >= 2:
                    imp_name = parts[1]
                    dst_id = name_to_id.get(imp_name)
                    if dst_id is not None:
                        if dst_id not in seen_dst:
                            seen_dst.add(dst_id)
                            edges_list.append((mod_id, dst_id))
                            adj_out[idx].append(dst_id - 1)
                            adj_in[dst_id - 1].append(idx)
                    else:
                        top_prefix = imp_name.split(".")[0]
                        if top_prefix in EXTERNAL_PREFIXES:
                            exts.append(imp_name)
                            ext_counts[imp_name] += 1
                        else:
                            unresolved_imports.append({"module": mod_names[idx], "import": imp_name})
            else:
                m = DECL_RE.match(line)
                if m:
                    kind = m.group(1).decode("utf-8", errors="replace")
                    dname = m.group(2).decode("utf-8", errors="replace")
                    decl_counts[kind] += 1
                    decl_rows.append((mod_id, kind, dname, lineno))
                    if kind == "theorem":
                        n_thm[idx] += 1
                    elif kind == "lemma":
                        n_lem[idx] += 1
                    elif kind == "def":
                        n_def[idx] += 1
                    elif kind == "structure":
                        n_str[idx] += 1
                    else:
                        n_oth[idx] += 1

        ext_imports[idx] = exts

    print(
        f"Parsed files in {time.time() - t1:.2f}s: "
        f"{len(edges_list)} internal edges, {len(decl_rows)} decls, "
        f"{len(unresolved_imports)} unresolved imports"
    )

    # Phase 3: Graph computations (BFS from Main, Kahn height from leaves)
    t2 = time.time()
    reachable = [0] * n_mod
    dist_main: list[int | None] = [None] * n_mod

    main_id = name_to_id.get("Main")
    if main_id is not None:
        m_idx = main_id - 1
        reachable[m_idx] = 1
        dist_main[m_idx] = 0
        q: deque[int] = deque([m_idx])
        while q:
            u = q.popleft()
            du = dist_main[u]
            assert du is not None
            for v in adj_out[u]:
                if not reachable[v]:
                    reachable[v] = 1
                    dist_main[v] = du + 1
                    q.append(v)

    in_deg = [len(adj_in[i]) for i in range(n_mod)]
    out_deg = [len(adj_out[i]) for i in range(n_mod)]
    in_deg_main = [sum(1 for u in adj_in[i] if reachable[u]) for i in range(n_mod)]

    # Height from leaves using Kahn's topological algorithm on reversed edges (dst -> src)
    rem_out = list(out_deg)
    height = [0] * n_mod
    kq: deque[int] = deque(i for i in range(n_mod) if rem_out[i] == 0)
    processed = 0
    while kq:
        v = kq.popleft()
        processed += 1
        hv_plus_1 = height[v] + 1
        for u in adj_in[v]:
            if hv_plus_1 > height[u]:
                height[u] = hv_plus_1
            rem_out[u] -= 1
            if rem_out[u] == 0:
                kq.append(u)

    is_dag = processed == n_mod
    print(f"Graph metrics computed in {time.time() - t2:.2f}s (is_dag={is_dag})")

    # Phase 4: Aggregate dir_stats
    # level -> dir_key -> stats accumulator
    # stats: [parent_key, files, r_files, lines, r_lines, bytes, thm, lem, df, st, min_dist, sum_dist, cnt_dist, max_h]
    dir_acc: dict[tuple[int, str], list] = {}

    def add_dir(level: int, key: str, parent: str, idx: int) -> None:
        rec = dir_acc.get((level, key))
        if rec is None:
            rec = [parent, 0, 0, 0, 0, 0, 0, 0, 0, 0, None, 0, 0, 0]
            dir_acc[(level, key)] = rec
        rec[1] += 1
        r = reachable[idx]
        ln = lines_arr[idx]
        rec[2] += r
        rec[3] += ln
        if r:
            rec[4] += ln
        rec[5] += bytes_arr[idx]
        rec[6] += n_thm[idx]
        rec[7] += n_lem[idx]
        rec[8] += n_def[idx]
        rec[9] += n_str[idx]
        dm = dist_main[idx]
        if dm is not None:
            if rec[10] is None or dm < rec[10]:
                rec[10] = dm
            rec[11] += dm
            rec[12] += 1
        h = height[idx]
        if h > rec[13]:
            rec[13] = h

    for idx in range(n_mod):
        dpath, top, d2, d3 = mod_dirs[idx]
        add_dir(1, top, "", idx)
        add_dir(2, d2, "" if top == d2 else top, idx)
        add_dir(3, d3, "" if d2 == d3 else d2, idx)
        leaf_key = dpath if dpath else "(root)"
        leaf_parent = os.path.dirname(dpath) if "/" in dpath else ("" if not dpath else "")
        if "/" in dpath:
            leaf_parent = os.path.dirname(dpath)
        elif dpath:
            leaf_parent = "(root)"
        else:
            leaf_parent = ""
        add_dir(0, leaf_key, leaf_parent, idx)

    # Phase 5: Write SQLite database
    t3 = time.time()
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA synchronous = OFF")
    conn.execute("PRAGMA journal_mode = MEMORY")
    conn.execute("PRAGMA temp_store = MEMORY")

    conn.executescript(
        """
        CREATE TABLE modules (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            rel_path TEXT UNIQUE,
            dir_path TEXT,
            top_dir TEXT,
            depth2_dir TEXT,
            depth3_dir TEXT,
            lines INTEGER,
            bytes INTEGER,
            n_theorems INTEGER,
            n_lemmas INTEGER,
            n_defs INTEGER,
            n_structures INTEGER,
            n_other_decls INTEGER,
            external_imports TEXT,
            reachable_from_main INTEGER,
            dist_from_main INTEGER,
            height_from_leaves INTEGER,
            in_degree INTEGER,
            in_degree_main INTEGER,
            out_degree INTEGER
        );
        CREATE TABLE edges (
            src_id INTEGER,
            dst_id INTEGER
        );
        CREATE TABLE declarations (
            module_id INTEGER,
            kind TEXT,
            name TEXT,
            line_no INTEGER
        );
        CREATE TABLE dir_stats (
            level INTEGER,
            dir_key TEXT,
            parent_key TEXT,
            files INTEGER,
            reachable_files INTEGER,
            lines INTEGER,
            reachable_lines INTEGER,
            bytes INTEGER,
            theorems INTEGER,
            lemmas INTEGER,
            defs INTEGER,
            structures INTEGER,
            min_dist_from_main INTEGER,
            avg_dist_from_main REAL,
            max_height INTEGER
        );
        """
    )

    with conn:
        conn.executemany(
            """
            INSERT INTO modules VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                (
                    idx + 1,
                    mod_names[idx],
                    rel_paths[idx],
                    mod_dirs[idx][0],
                    mod_dirs[idx][1],
                    mod_dirs[idx][2],
                    mod_dirs[idx][3],
                    lines_arr[idx],
                    bytes_arr[idx],
                    n_thm[idx],
                    n_lem[idx],
                    n_def[idx],
                    n_str[idx],
                    n_oth[idx],
                    json.dumps(ext_imports[idx]),
                    reachable[idx],
                    dist_main[idx],
                    height[idx],
                    in_deg[idx],
                    in_deg_main[idx],
                    out_deg[idx],
                )
                for idx in range(n_mod)
            ),
        )
        conn.executemany("INSERT INTO edges VALUES (?,?)", edges_list)
        conn.executemany("INSERT INTO declarations VALUES (?,?,?,?)", decl_rows)
        conn.executemany(
            "INSERT INTO dir_stats VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                (
                    lvl,
                    key,
                    rec[0],
                    rec[1],
                    rec[2],
                    rec[3],
                    rec[4],
                    rec[5],
                    rec[6],
                    rec[7],
                    rec[8],
                    rec[9],
                    rec[10],
                    (rec[11] / rec[12]) if rec[12] > 0 else None,
                    rec[13],
                )
                for (lvl, key), rec in sorted(dir_acc.items())
            ),
        )

    conn.executescript(
        """
        CREATE INDEX idx_edges_src ON edges(src_id);
        CREATE INDEX idx_edges_dst ON edges(dst_id);
        CREATE INDEX idx_decls_mod ON declarations(module_id);
        CREATE INDEX idx_decls_kind ON declarations(kind);
        CREATE INDEX idx_dirstats_level ON dir_stats(level, dir_key);
        CREATE INDEX idx_modules_top ON modules(top_dir);
        CREATE INDEX idx_modules_d2 ON modules(depth2_dir);
        CREATE INDEX idx_modules_reach ON modules(reachable_from_main);
        """
    )
    conn.close()
    print(f"Wrote SQLite DB in {time.time() - t3:.2f}s")

    # Phase 6: Write meta.json
    reachable_files = sum(reachable)
    unreachable_files = n_mod - reachable_files
    total_lines = sum(lines_arr)
    reachable_lines = sum(lines_arr[i] for i in range(n_mod) if reachable[i])
    total_bytes = sum(bytes_arr)
    reachable_edges = sum(1 for u_id, _ in edges_list if reachable[u_id - 1])
    max_dist = max((d for d in dist_main if d is not None), default=0)
    max_height = max(height, default=0)

    meta = {
        "total_files": n_mod,
        "reachable_files": reachable_files,
        "unreachable_files": unreachable_files,
        "total_lines": total_lines,
        "reachable_lines": reachable_lines,
        "total_bytes": total_bytes,
        "total_internal_edges": len(edges_list),
        "reachable_internal_edges": reachable_edges,
        "max_dist_from_main": max_dist,
        "max_height_from_leaves": max_height,
        "is_dag": is_dag,
        "unresolved_imports": unresolved_imports,
        "external_import_counts": dict(ext_counts.most_common()),
        "decl_counts": dict(decl_counts.most_common()),
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    META_PATH.write_text(json.dumps(meta, indent=2))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
