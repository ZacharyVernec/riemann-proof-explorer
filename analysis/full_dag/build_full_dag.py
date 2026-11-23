#!/usr/bin/env python3
"""Build a deterministic, refactor-resilient layout and binary dataset for the full Lean module DAG."""

from __future__ import annotations

import argparse
import base64
import colorsys
import gzip
import json
import math
import re
import shutil
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
DEFAULT_INVENTORY_PATH = ROOT / "analysis" / "published_theorems" / "PUBLISHED_THEOREMS_INVENTORY.md"
BUILD_INDEX_SCRIPT = ROOT / "analysis" / "build_index.py"
SRC_DIR = ROOT / "lean" / "src"

MAGIC = b"LDAG"
FORMAT_VERSION = 2

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

NOVEL_HEADS = {
    "RiemannHypothesis",
    "RiemannZetaZerosOnLine",
    "DirichletLNonvanishingRightOfHalf",
    "DirichletLZerosOnLine",
    "PrimitiveDirichletLZerosOnLine",
    "EveryCharacter",
    "VWin",
    "CorGK",
    "Bound",
    "CovolX",
    "CovolumeBoundOfX",
    "ZeroFreeAll",
    "HalfPlane",
    "Strip",
    "Zeta",
    "HypothesesH'",
    "DeepStR",
    "GoodTowerExistsX",
    "VolumeTheoremX",
}

BUNDLE_PARAM_RE = re.compile(
    r"\b(?:Hypotheses[A-Z0-9₂']*|"
    r"LitN|LitLoc\w*|LitAut|LitCoh|LitCM|"
    r"PublishedHodgeBundleTheorems|ThetaLocalInputs|"
    r"LiteratureRankNHypothesis|LiteratureAutomorphyHypothesis|"
    r"LiteratureCMHypothesis|UnitaryGroupThirdPlaceHypotheses|"
    r"OpenImageCondition|OpenLiteratureStatements)\b"
)

SECTION12_EXTRA_EXCLUDED = {
    "SelfTw",
    "adSys",
    "IsNormChar",
    "WeakBC",
    "IsFL",
    "IsGalRepOfR",
    "IsoTwist",
    "IsQuadCharOf",
    "IsBC",
    "IsSel",
    "IsLat",
    "Clauses",
    "Compat",
    "Reading",
    "LeviBlockCentreFinite",
    "LeviCentreFiniteUnitary",
    "LeviCentreInducedUnitary",
    "CentreFiniteUnitary",
    "PrimesInProgressionsRelative",
    "TZRat",
    "QuadraticHeckeZeroEstimates",
    "BesselXiIntegrable",
    "MatrixLemma",
    "ArithRiemannRochAbelian",
    "ThetaRationalInvariance",
    "exists_unit_kills_of_idempotent",
    "exists_unit_kills",
}

RHEC_MODULE_NAME = "Development.AutomorphicArithmetic.CharacterBoxes.RiemannHypothesisOfEveryCharacter"
RHEC_KEEP_IMPORT = "Development.AutomorphicArithmetic.CharacterBoxes.EveryCharacter"


def hex_to_rgb(hex_color: str) -> list[int]:
    """Convert '#rrggbb' hex string to [r, g, b] ints."""
    h = hex_color.lstrip("#")
    return [int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)]


def group_color(idx: int) -> str:
    """Return a crisp light-theme categorical color for group index idx."""
    if idx < len(BASE_PALETTE):
        return BASE_PALETTE[idx]
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
    edge_weights_out: list[list[int]] | None = None,
    edge_weights_in: list[list[int]] | None = None,
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
            if not ins and not outs:
                continue
            lo = max(y[p] for p in ins) + 1 if ins else 0
            hi = min(y[c] for c in outs) - 1 if outs else max_h
            if edge_weights_in is None:
                ni = len(ins)
                no = len(outs)
                if ni > no:
                    ny = lo
                elif no > ni:
                    ny = hi
                else:
                    avg = (sum(y[p] for p in ins) + sum(y[c] for c in outs)) / (ni + no)
                    ny = max(lo, min(hi, int(round(avg))))
            else:
                wins = edge_weights_in[u]
                wouts = edge_weights_out[u]  # type: ignore[index]
                wi = sum(wins)
                wo = sum(wouts)
                if wi > wo:
                    ny = lo
                elif wo > wi:
                    ny = hi
                else:
                    wsum = sum(w * y[p] for p, w in zip(ins, wins)) + sum(w * y[c] for c, w in zip(outs, wouts))
                    avg = wsum / (wi + wo)
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
                if edge_weights_in is None:
                    for v in adj_in[u]:
                        w = 1.0 / (yu - y[v])
                        num += w * x[v]
                        den += w
                    for v in adj_out[u]:
                        w = 1.0 / (y[v] - yu)
                        num += w * x[v]
                        den += w
                else:
                    for v, ew in zip(adj_in[u], edge_weights_in[u]):
                        w = (1.0 + math.log2(ew)) / (yu - y[v])
                        num += w * x[v]
                        den += w
                    for v, ew in zip(adj_out[u], edge_weights_out[u]):  # type: ignore[index]
                        w = (1.0 + math.log2(ew)) / (y[v] - yu)
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
                if edge_weights_in is None:
                    for v in adj_in[u]:
                        w = 1.0 / (yu - y[v])
                        num += w * x[v]
                        den += w
                    for v in adj_out[u]:
                        w = 1.0 / (y[v] - yu)
                        num += w * x[v]
                        den += w
                else:
                    for v, ew in zip(adj_in[u], edge_weights_in[u]):
                        w = (1.0 + math.log2(ew)) / (yu - y[v])
                        num += w * x[v]
                        den += w
                    for v, ew in zip(adj_out[u], edge_weights_out[u]):  # type: ignore[index]
                        w = (1.0 + math.log2(ew)) / (y[v] - yu)
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


def clean_lit_title(raw_title: str) -> str:
    """Convert markdown/LaTeX inline title to crisp plain-text Unicode suitable for canvas labels."""
    s = raw_title.strip()
    replacements = [
        (r"\\mathrm\{GL\}", "GL"),
        (r"\\mathrm\{SL\}", "SL"),
        (r"\\mathbb\{Q\}", "ℚ"),
        (r"\\mathbb\{F\}", "𝔽"),
        (r"\\mathbb\{Z\}", "ℤ"),
        (r"\\mathbb\{C\}", "ℂ"),
        (r"\\mathbb\{R\}", "ℝ"),
        (r"\\mathcal\{O\}", "O"),
        (r"\\mathfrak\{g\}", "g"),
        (r"\\ell", "ℓ"),
        (r"\\varepsilon", "ε"),
        (r"\\gamma", "γ"),
        (r"\\to", "→"),
        (r"\\times", "×"),
    ]
    for pat, rep in replacements:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", s)
    s = s.replace("$", "").replace("`", "").replace("**", "")
    s = s.replace("_n", "ₙ").replace("_q", "_q").replace("^2", "²").replace("^1_f", "¹_f")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_published_inventory(
    inv_path: Path,
) -> tuple[dict[str, tuple[str, str, int]], dict[str, list[str]], set[str]]:
    """Parse PUBLISHED_THEOREMS_INVENTORY.md into symbol->(row_key, title, order), path hints, and exclusions."""
    if not inv_path.exists():
        raise RuntimeError(f"Inventory file not found: {inv_path}")
    text = inv_path.read_text(encoding="utf-8")

    sec_untraced_m = re.search(r"^###\s+12\.\s+Formalizations", text, re.M)
    if sec_untraced_m is None:
        sec_untraced_m = re.search(r"^###\s+11\.\s+Formalizations", text, re.M)
    if sec_untraced_m is None:
        raise RuntimeError(f"Could not locate untraced section heading in {inv_path}")

    meth_m = re.search(r"^##\s+Methodology:", text, re.M)
    traced_text = text[: sec_untraced_m.start()]
    untraced_text = text[sec_untraced_m.start() : (meth_m.start() if meth_m else len(text))]

    sym_to_lit: dict[str, tuple[str, str, int]] = {}
    sym_path_hints: dict[str, list[str]] = defaultdict(list)

    row_order = 0
    for line in traced_text.splitlines():
        if not line.startswith("| `"):
            continue
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) < 2:
            continue
        col1, col2 = cols[0], cols[1]
        # Only parse comparative literature tables (exclude overview directory tables whose col1 has paths)
        if "`/" in col1 or col1.startswith("`Development/"):
            continue
        row_order += 1
        row_key = f"lit_{row_order:03d}"
        m_bold = re.search(r"\*\*(.+?)\*\*", col2)
        raw_title = m_bold.group(1) if m_bold else col2.split(";")[0]
        title = clean_lit_title(raw_title)

        # Extract backticked symbol names and trailing parenthesized path hints
        for tok in re.findall(r"`([^`]+)`", col1):
            if "/" in tok or ".lean" in tok or " " in tok or "*" in tok or len(tok) < 3:
                continue
            sym_to_lit.setdefault(tok, (row_key, title, row_order))

        # Capture any explicit .lean path hints in col1 for this row's symbols
        row_syms = [
            tok
            for tok in re.findall(r"`([^`]+)`", col1)
            if "/" not in tok and ".lean" not in tok and " " not in tok and "*" not in tok and len(tok) >= 3
        ]
        hints = [p.lstrip("./") for p in re.findall(r"\(`([^`#]+\.lean)", col1)]
        for s in row_syms:
            for h in hints:
                sym_path_hints[s].append(h)

    excluded_syms = set(SECTION12_EXTRA_EXCLUDED)
    for line in untraced_text.splitlines():
        if not line.startswith("| `"):
            continue
        col1 = line.split("|")[1]
        for tok in re.findall(r"`([^`]+)`", col1):
            if "/" not in tok and ".lean" not in tok and " " not in tok and "*" not in tok and len(tok) >= 3:
                excluded_syms.add(tok)

    for s in excluded_syms:
        sym_to_lit.pop(s, None)

    return sym_to_lit, sym_path_hints, excluded_syms


def resolve_symbol_allowed_ancestors(
    db_path: Path,
    sym_to_lit: dict[str, tuple[str, str, int]],
    sym_path_hints: dict[str, list[str]],
    rel_path: list[str],
    adj_in: list[list[int]],
) -> dict[str, set[int]]:
    """Map each inventory symbol to the set of modules that transitively import its defining statement module."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()

    mod_rows = cur.execute("SELECT id, rel_path FROM modules ORDER BY rel_path ASC, id ASC").fetchall()
    db_to_idx = {db_id: idx for idx, (db_id, _) in enumerate(mod_rows)}

    target_syms = set(sym_to_lit.keys())
    def_candidates: dict[str, list[tuple[int, str, str]]] = defaultdict(list)

    for db_mod_id, kind, decl_name in cur.execute(
        "SELECT module_id, kind, name FROM declarations WHERE kind IN ('def', 'abbrev', 'structure', 'theorem')"
    ):
        short = decl_name.rsplit(".", 1)[-1]
        if short not in target_syms:
            continue
        idx = db_to_idx.get(db_mod_id)
        if idx is not None:
            def_candidates[short].append((idx, rel_path[idx], kind))
    conn.close()

    stmt_prefixes = (
        "Development/AbelianVarietyTheory/PublishedTheorems/",
        "Development/AutomorphicSpectrum/PublishedTheorems/",
        "Development/AutomorphicArithmetic/AutomorphicVarieties/PublishedTheorems/",
        "PositivityTheory/PublishedTheorems/",
        "ReciprocityTheory/",
        "Formalism/",
        "Development/ResolutionOfSingularities/Statements.lean",
        "Development/EtaleCohomology/EtaleSheaves/EtaleChapterEFour.lean",
        "Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/TypeConditions/WeightsConjBis.lean",
        "Development/AutomorphicArithmetic/Foundations/LocalLanglands/IsRecTOfIsRec.lean",
        "Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/RecTExists.lean",
        "Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/GaloisSideTwistedSelmerAuxiliaryPrimes.lean",
        "Development/WeilBound/RepresentationTheoryGL/ArchimedeanBaseChange/ArchimedeanBaseChangeProof/BaseChangeIsobaricNOf.lean",
        "Development/AutomorphicArithmetic/Foundations/BaseChangeIdentities/Narrow.lean",
        "Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/LocalTypeDictionary/DiscreteSpectrumResidualClassification.lean",
        "Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/LefschetzSigmaSums/HodgeTraceFromLefschetzAndGroupSide.lean",
        "Development/WeilBound/ThetaLifts/LatticeBasics/HypothesesS.lean",
        "Development/WeilBound/ThetaLifts/LatticeBasics/HypothesesE.lean",
        "Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/SmallGeneratedCountUpperOfUse.lean",
        "Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/MoriwakiBigTheorem/HSChain.lean",
    )

    sym_def_mods: dict[str, set[int]] = {}
    for sym in target_syms:
        cands = def_candidates.get(sym, [])
        hints = [h.lstrip("./") for h in sym_path_hints.get(sym, [])]

        # Priority 1: non-theorem (def/abbrev/structure) in statement directories or matching path hints
        p1 = {
            idx
            for idx, rp, kind in cands
            if kind != "theorem"
            and (
                rp.startswith(stmt_prefixes)
                or any(rp.endswith(h.split(".../")[-1]) for h in hints if not h.startswith(".../"))
                or any(rp.endswith(h[4:]) for h in hints if h.startswith(".../"))
            )
        }
        # Priority 2: any declaration in statement directories or matching path hints (handles in-place theorems)
        p2 = {
            idx
            for idx, rp, _ in cands
            if rp.startswith(stmt_prefixes)
            or any(rp.endswith(h[4:]) if h.startswith(".../") else rp.endswith(h) for h in hints)
        }
        # Priority 3: non-theorem definitions outside Proofs/
        p3 = {idx for idx, rp, kind in cands if kind != "theorem" and "/Proofs/" not in rp}
        chosen = p1 or p2 or p3 or {idx for idx, _, _ in cands}
        sym_def_mods[sym] = chosen

    # Cache reverse BFS ancestor sets per unique defining module
    unique_def_mods = {m for ms in sym_def_mods.values() for m in ms}
    anc_cache: dict[int, set[int]] = {}
    for dm in unique_def_mods:
        seen = {dm}
        q = deque([dm])
        while q:
            u = q.popleft()
            for p in adj_in[u]:
                if p not in seen:
                    seen.add(p)
                    q.append(p)
        anc_cache[dm] = seen

    sym_allowed: dict[str, set[int]] = {}
    for sym, ms in sym_def_mods.items():
        allowed: set[int] = set()
        for dm in ms:
            allowed |= anc_cache[dm]
        sym_allowed[sym] = allowed

    return sym_allowed


def split_top_level(s: str, sep: str) -> list[str]:
    """Split s by sep only at bracket nesting depth 0 (avoiding ':=' when sep is ':')."""
    parts: list[str] = []
    depth = 0
    cur_start = 0
    i = 0
    n = len(s)
    seplen = len(sep)
    while i < n:
        c = s[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth = max(0, depth - 1)
        elif depth == 0 and s[i : i + seplen] == sep:
            if sep == ":" and i + 1 < n and s[i + 1] == "=":
                i += 2
                continue
            parts.append(s[cur_start:i])
            cur_start = i + seplen
            i += seplen
            continue
        i += 1
    parts.append(s[cur_start:])
    return parts


def parse_module_published_proofs(
    file_path: Path,
    nid: int,
    sym_allowed: dict[str, set[int]],
    excluded_syms: set[str],
) -> list[str]:
    """Return inventory symbol names proved as final conclusions in file_path, or [] if none/novel/bundle."""
    txt = file_path.read_text(encoding="utf-8", errors="replace")
    if "theorem " not in txt and "lemma " not in txt:
        return []

    decl_starts = list(
        re.finditer(
            r"^[ \t]*(?:@\[.*?\]\s*)*(?:(?:private|protected|noncomputable|local|scoped)\s+)*(theorem|lemma)\s+([^\s:(\[{]+)",
            txt,
            re.M,
        )
    )
    if not decl_starts:
        return []

    hits: list[str] = []
    for idx, m in enumerate(decl_starts):
        end = decl_starts[idx + 1].start() if idx + 1 < len(decl_starts) else len(txt)
        chunk = txt[m.end() : end]
        depth = 0
        sig_end = len(chunk)
        i = 0
        while i < len(chunk):
            c = chunk[i]
            if c in "([{":
                depth += 1
            elif c in ")]}":
                depth = max(0, depth - 1)
            elif depth == 0:
                if chunk[i : i + 2] == ":=":
                    sig_end = i
                    break
                if (
                    chunk[i : i + 5] == "where"
                    and (i == 0 or not chunk[i - 1].isalnum())
                    and (i + 5 == len(chunk) or not chunk[i + 5].isalnum())
                ):
                    sig_end = i
                    break
            i += 1

        sig = " ".join(chunk[:sig_end].split())
        cp = split_top_level(sig, ":")
        if len(cp) < 2:
            continue
        params_part = cp[0]
        ret = ":".join(cp[1:]).strip()
        ap = split_top_level(ret, "→")
        hyp_part = params_part + " " + " ".join(ap[:-1])
        lp = ap[-1].strip()
        if "->" in lp:
            ap2 = split_top_level(lp, "->")
            hyp_part += " " + " ".join(ap2[:-1])
            lp = ap2[-1].strip()

        heads: list[str] = []
        for p in split_top_level(lp, "∧"):
            hm = re.match(r"^[\s(]*([A-Za-z_][A-Za-z0-9_.'₂]*)", p)
            if hm:
                heads.append(hm.group(1))

        for h in heads:
            short = h.rsplit(".", 1)[-1]
            if short in NOVEL_HEADS:
                return []
            if short in excluded_syms:
                continue
            allowed = sym_allowed.get(short)
            if allowed is not None and nid in allowed and not BUNDLE_PARAM_RE.search(hyp_part):
                hits.append(short)

    return hits


def detect_published_proof_roots(
    rel_path: list[str],
    sym_to_lit: dict[str, tuple[str, str, int]],
    sym_allowed: dict[str, set[int]],
    excluded_syms: set[str],
) -> dict[int, list[str]]:
    """Detect all Lean modules whose theorems prove audited existing-theory propositions."""
    path_to_nid = {rp: i for i, rp in enumerate(rel_path)}
    all_allowed_union: set[int] = set()
    for s_set in sym_allowed.values():
        all_allowed_union |= s_set

    prop_list = sorted(sym_to_lit.keys())
    cand_nids: set[int] = set()

    if shutil.which("rg"):
        chunk_size = 250
        for i in range(0, len(prop_list), chunk_size):
            pat = r"\b(?:" + "|".join(re.escape(p) for p in prop_list[i : i + chunk_size]) + r")\b"
            res = subprocess.run(["rg", "-l", pat, str(SRC_DIR)], capture_output=True, text=True)
            prefix = str(SRC_DIR) + "/"
            for line in res.stdout.splitlines():
                if line.startswith(prefix):
                    nid = path_to_nid.get(line[len(prefix) :])
                    if nid is not None and nid in all_allowed_union:
                        cand_nids.add(nid)
    else:
        cand_nids = all_allowed_union

    prover_syms: dict[int, list[str]] = {}
    for nid in sorted(cand_nids):
        rp = rel_path[nid]
        if "/Definitions/" in rp:
            continue
        hits = parse_module_published_proofs(SRC_DIR / rp, nid, sym_allowed, excluded_syms)
        if hits:
            prover_syms[nid] = hits

    return prover_syms


def find_dead_bridge_imports(
    db_path: Path,
    mod_name: list[str],
    rel_path: list[str],
    adj_out: list[list[int]],
) -> set[tuple[int, int]]:
    """Prune provably unused transitive imports on thin top-level proof bridges (e.g. RHEC)."""
    name_to_nid = {nm: i for i, nm in enumerate(mod_name)}
    dead_edges: set[tuple[int, int]] = set()

    rhec_nid = name_to_nid.get(RHEC_MODULE_NAME)
    if rhec_nid is None:
        return dead_edges

    rp = rel_path[rhec_nid]
    lines = (SRC_DIR / rp).read_text(encoding="utf-8", errors="replace").splitlines()
    imports = [l for l in lines if l.startswith("import ")]
    body_lines = [l for l in lines if not l.startswith("import ") and l.strip()]
    body_text = "\n".join(body_lines)

    if len(imports) < 50 or len(body_lines) > 40 or "theorem " not in body_text:
        return dead_edges

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    mod_decls: dict[int, list[str]] = defaultdict(list)
    db_mods = cur.execute("SELECT id, name FROM modules").fetchall()
    db_to_nid = {db_id: name_to_nid[nm] for db_id, nm in db_mods if nm in name_to_nid}
    for db_mid, dname in cur.execute("SELECT module_id, name FROM declarations"):
        nid = db_to_nid.get(db_mid)
        if nid is not None and nid in adj_out[rhec_nid]:
            mod_decls[nid].append(dname)
    conn.close()

    kept: list[str] = []
    for v in adj_out[rhec_nid]:
        decls = mod_decls.get(v, [])
        referenced = False
        for d in decls:
            short = d.rsplit(".", 1)[-1]
            if re.search(rf"\b{re.escape(short)}\b", body_text):
                referenced = True
                break
        if not referenced and decls:
            dead_edges.add((rhec_nid, v))
        else:
            kept.append(mod_name[v])

    if RHEC_KEEP_IMPORT not in kept:
        raise RuntimeError(f"Expected {RHEC_KEEP_IMPORT} to remain referenced in {RHEC_MODULE_NAME}; kept={kept}")
    return dead_edges


def build_collapsed_dag(
    mod_name: list[str],
    rel_path: list[str],
    top_dir: list[str],
    adj_out: list[list[int]],
    adj_in: list[list[int]],
    prover_syms: dict[int, list[str]],
    sym_to_lit: dict[str, tuple[str, str, int]],
    dead_edges: set[tuple[int, int]],
    y_iters: int,
    x_sweeps: int,
) -> dict[str, Any]:
    """Compute frontier-domination cut, literature supernode contraction, and compact weighted layout."""
    n_mod = len(mod_name)
    name_to_nid = {nm: i for i, nm in enumerate(mod_name)}
    main_nid = name_to_nid["Main"]

    # Distance from Main in full DAG (deterministic tie-breaking for ownership)
    dist_main = [10**9] * n_mod
    dist_main[main_nid] = 0
    dq = deque([main_nid])
    while dq:
        u = dq.popleft()
        du = dist_main[u] + 1
        for v in adj_out[u]:
            if dist_main[v] > du:
                dist_main[v] = du
                dq.append(v)

    cut_nodes = set(prover_syms.keys())
    peeled_barrels = 0
    changed = True
    while changed:
        changed = False
        for u in sorted(cut_nodes):
            u_rows = {sym_to_lit[s][0] for s in prover_syms[u]}
            if len(u_rows) < 2:
                continue
            child_rows = {
                sym_to_lit[s][0]
                for v in adj_out[u]
                if v in cut_nodes
                for s in prover_syms[v]
            }
            if len(child_rows) >= 2:
                cut_nodes.remove(u)
                peeled_barrels += 1
                changed = True

    # Baseline reachability without dead-edge pruning to identify interior of baseline frontier
    act0: set[int] = {main_nid}
    q0 = deque([main_nid])
    while q0:
        u = q0.popleft()
        if u in cut_nodes:
            continue
        for v in adj_out[u]:
            if v not in act0:
                act0.add(v)
                q0.append(v)
    front0 = act0 & cut_nodes

    below_front0: set[int] = set()
    bq = deque()
    for f in front0:
        for v in adj_out[f]:
            if v not in below_front0:
                below_front0.add(v)
                bq.append(v)
    while bq:
        u = bq.popleft()
        for v in adj_out[u]:
            if v not in below_front0:
                below_front0.add(v)
                bq.append(v)

    effective_dead_edges = {(u, v) for (u, v) in dead_edges if v in below_front0}

    while True:
        active_set = {main_nid}
        q = deque([main_nid])
        while q:
            u = q.popleft()
            if u in cut_nodes:
                continue
            for v in adj_out[u]:
                if (u, v) in effective_dead_edges:
                    continue
                if v not in active_set:
                    active_set.add(v)
                    q.append(v)
        frontier_set = active_set & cut_nodes
        collapsed_interior = set(range(n_mod)) - active_set

        # Verify every collapsed_interior node is reachable from frontier_set
        reach_front = set(frontier_set)
        rq = deque(frontier_set)
        while rq:
            u = rq.popleft()
            for v in adj_out[u]:
                if v in collapsed_interior and v not in reach_front:
                    reach_front.add(v)
                    rq.append(v)
        unowned = collapsed_interior - reach_front
        if not unowned or not effective_dead_edges:
            break
        # Restore any pruned dead edge whose target can reach an unowned node
        anc_unowned = set(unowned)
        aq = deque(unowned)
        while aq:
            u = aq.popleft()
            for p in adj_in[u]:
                if p not in anc_unowned:
                    anc_unowned.add(p)
                    aq.append(p)
        to_restore = {(u, v) for (u, v) in effective_dead_edges if v in anc_unowned}
        if not to_restore:
            break
        effective_dead_edges -= to_restore

    pure_active = sorted(active_set - frontier_set, key=lambda u: rel_path[u])

    # Map each frontier module to its primary literature entry (row_key, title, row_order)
    lit_groups: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    for f in sorted(frontier_set):
        syms = prover_syms[f]
        best_sym = min(syms, key=lambda s: (sym_to_lit[s][2], s))
        lit_entry = sym_to_lit[best_sym]
        lit_groups[lit_entry].append(f)

    # Full cone size per supernode (for summary metrics)
    super_cone_interior: dict[tuple[str, str, int], set[int]] = {}
    for gk, fnodes in lit_groups.items():
        seen_c: set[int] = set()
        cq = deque()
        for f in fnodes:
            for v in adj_out[f]:
                if v in collapsed_interior and v not in seen_c:
                    seen_c.add(v)
                    cq.append(v)
        while cq:
            u = cq.popleft()
            for v in adj_out[u]:
                if v in collapsed_interior and v not in seen_c:
                    seen_c.add(v)
                    cq.append(v)
        super_cone_interior[gk] = seen_c

    # Disjoint ownership partition of collapsed_interior via deterministic multi-source BFS
    node_owner: dict[int, tuple[str, str, int]] = {}
    ordered_frontiers: list[tuple[int, tuple[str, str, int]]] = []
    for gk, fnodes in lit_groups.items():
        for f in fnodes:
            node_owner[f] = gk
            ordered_frontiers.append((f, gk))
    ordered_frontiers.sort(key=lambda item: (dist_main[item[0]], -len(adj_in[item[0]]), rel_path[item[0]]))

    bfs_q: deque[tuple[int, tuple[str, str, int]]] = deque()
    for f, gk in ordered_frontiers:
        for v in adj_out[f]:
            if v in collapsed_interior and v not in node_owner:
                node_owner[v] = gk
                bfs_q.append((v, gk))
    while bfs_q:
        u, gk = bfs_q.popleft()
        for v in adj_out[u]:
            if v in collapsed_interior and v not in node_owner:
                node_owner[v] = gk
                bfs_q.append((v, gk))

    # Any unreachable residual (should be empty since full graph is Main-reachable, but guard anyway)
    if len(node_owner) != len(frontier_set) + len(collapsed_interior):
        unowned = (frontier_set | collapsed_interior) - set(node_owner.keys())
        raise RuntimeError(f"Unassigned collapsed nodes detected: {len(unowned)}")

    owned_members: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    for u, gk in node_owner.items():
        owned_members[gk].append(u)

    # Order supernodes deterministically by (-owned_count, row_order, title)
    sorted_super_keys = sorted(
        lit_groups.keys(),
        key=lambda gk: (-len(owned_members[gk]), gk[2], gk[1], gk[0]),
    )
    n_active = len(pure_active)
    n_super = len(sorted_super_keys)
    n_c = n_active + n_super

    active_to_idx = {u: i for i, u in enumerate(pure_active)}
    super_key_to_sidx = {gk: i for i, gk in enumerate(sorted_super_keys)}

    # Build contracted adjacency + weights for collapsed DAG (nodes 0..N_c-1)
    c_sort_keys: list[str] = [rel_path[u] for u in pure_active] + [
        f"~lit/{gk[0]}/{gk[1]}" for gk in sorted_super_keys
    ]
    c_adj_out: list[list[int]] = [[] for _ in range(n_c)]
    c_adj_in: list[list[int]] = [[] for _ in range(n_c)]
    c_weights_out: list[list[int]] = [[] for _ in range(n_c)]
    c_weights_in: list[list[int]] = [[] for _ in range(n_c)]

    active_edge_cnt = 0
    super_edge_cnt = 0
    raw_super_edge_cnt = 0
    max_edge_weight = 1
    weight_hist: Counter[int] = Counter()

    for idx_u, full_u in enumerate(pure_active):
        aa_targets: list[int] = []
        super_mult: Counter[int] = Counter()
        for full_v in adj_out[full_u]:
            if (full_u, full_v) in effective_dead_edges:
                continue
            if full_v in active_to_idx:
                aa_targets.append(active_to_idx[full_v])
            elif full_v in frontier_set:
                s_idx = super_key_to_sidx[node_owner[full_v]]
                super_mult[n_active + s_idx] += 1

        aa_targets.sort()
        for idx_v in aa_targets:
            c_adj_out[idx_u].append(idx_v)
            c_weights_out[idx_u].append(1)
            c_adj_in[idx_v].append(idx_u)
            c_weights_in[idx_v].append(1)
            active_edge_cnt += 1
            weight_hist[1] += 1

        for idx_v in sorted(super_mult.keys()):
            w = super_mult[idx_v]
            c_adj_out[idx_u].append(idx_v)
            c_weights_out[idx_u].append(w)
            c_adj_in[idx_v].append(idx_u)
            c_weights_in[idx_v].append(w)
            super_edge_cnt += 1
            raw_super_edge_cnt += w
            weight_hist[w] += 1
            if w > max_edge_weight:
                max_edge_weight = w

    # Run weighted Sugiyama layout on collapsed DAG
    c_y, c_x, c_layer_dy, c_metrics = compute_layout(
        c_sort_keys,
        c_adj_out,
        c_adj_in,
        y_iters,
        x_sweeps,
        edge_weights_out=c_weights_out,
        edge_weights_in=c_weights_in,
    )
    c_num_layers = (max(c_y) + 1) if n_c else 0

    # Canonical re-indexing of collapsed nodes by (c_y, c_x, c_sort_keys)
    c_order = sorted(range(n_c), key=lambda u: (c_y[u], c_x[u], c_sort_keys[u]))
    c_old_to_new = [0] * n_c
    for new_cid, old_cid in enumerate(c_order):
        c_old_to_new[old_cid] = new_cid

    c_layer_offsets = [0] * (c_num_layers + 1)
    prev_layer = -1
    prev_x = 0.0
    c_min_gap = float("inf")
    for new_cid, old_cid in enumerate(c_order):
        ly = c_y[old_cid]
        xv = c_x[old_cid]
        if ly != prev_layer:
            for fill_l in range(prev_layer + 1, ly + 1):
                c_layer_offsets[fill_l] = new_cid
            prev_layer = ly
        else:
            gap = xv - prev_x
            if gap < c_min_gap:
                c_min_gap = gap
            if gap < 1.0 - 1e-4:
                raise RuntimeError(f"Collapsed layer {ly} spacing violation at node {new_cid}: gap={gap}")
        prev_x = xv
    for fill_l in range(prev_layer + 1, c_num_layers + 1):
        c_layer_offsets[fill_l] = n_c

    c_node_x_f32 = [
        struct.unpack("<f", struct.pack("<f", c_x[old_cid]))[0] for old_cid in c_order
    ]

    # Map canonical collapsed node -> (is_supernode, old_full_idx or super_idx)
    c_super_counts = [len(owned_members[gk]) for gk in sorted_super_keys]
    c_super_frontier_counts = [len(lit_groups[gk]) for gk in sorted_super_keys]
    c_super_titles = [gk[1] for gk in sorted_super_keys]
    c_super_dom_top_dir = [
        Counter(top_dir[m] for m in owned_members[gk]).most_common(1)[0][0]
        for gk in sorted_super_keys
    ]

    # Build canonical collapsed supernode outgoing adjacency list: cu -> sorted [(cv, w)]
    c_super_adj_out: list[list[tuple[int, int]]] = [[] for _ in range(n_c)]
    for old_u in range(n_active):
        nu = c_old_to_new[old_u]
        pairs: list[tuple[int, int]] = []
        for old_v, w in zip(c_adj_out[old_u], c_weights_out[old_u]):
            nv = c_old_to_new[old_v]
            if nu >= nv:
                raise RuntimeError(f"Collapsed canonical ID invariant violated: {nu} -> {nv}")
            if old_v >= n_active:
                pairs.append((nv, w))
        pairs.sort()
        c_super_adj_out[nu] = pairs

    return {
        "pure_active": pure_active,
        "frontier_set": frontier_set,
        "collapsed_interior": collapsed_interior,
        "sorted_super_keys": sorted_super_keys,
        "owned_members": owned_members,
        "lit_groups": lit_groups,
        "super_cone_interior": super_cone_interior,
        "node_owner": node_owner,
        "n_c": n_c,
        "n_active": n_active,
        "n_super": n_super,
        "active_edge_cnt": active_edge_cnt,
        "super_edge_cnt": super_edge_cnt,
        "raw_super_edge_cnt": raw_super_edge_cnt,
        "max_edge_weight": max_edge_weight,
        "weight_hist": weight_hist,
        "c_y": c_y,
        "c_x": c_x,
        "c_layer_dy": c_layer_dy,
        "c_num_layers": c_num_layers,
        "c_min_gap": c_min_gap,
        "c_metrics": c_metrics,
        "c_order": c_order,
        "c_old_to_new": c_old_to_new,
        "c_layer_offsets": c_layer_offsets,
        "c_node_x_f32": c_node_x_f32,
        "c_super_counts": c_super_counts,
        "c_super_frontier_counts": c_super_frontier_counts,
        "c_super_titles": c_super_titles,
        "c_super_dom_top_dir": c_super_dom_top_dir,
        "c_super_adj_out": c_super_adj_out,
        "c_adj_in": c_adj_in,
        "c_weights_in": c_weights_in,
        "effective_dead_edges": effective_dead_edges,
        "peeled_barrels": peeled_barrels,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic Sugiyama layout and binary payload for the full Lean DAG."
    )
    parser.add_argument("--rebuild-index", action="store_true", help="Re-run analysis/build_index.py first")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to graph.sqlite")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory")
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY_PATH, help="Path to PUBLISHED_THEOREMS_INVENTORY.md")
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

    # Stage A: Full DAG layout
    t_lay = time.time()
    y, x, layer_dy, layout_metrics = compute_layout(rel_path, adj_out, adj_in, args.y_iters, args.x_sweeps)
    num_layers = (max(y) + 1) if n_mod else 0
    print(
        f"Computed full layout ({num_layers} layers, layer_dy={layer_dy}) in {time.time() - t_lay:.2f}s | "
        f"avg_y_span {layout_metrics['init_avg_y_span']:.2f} -> {layout_metrics['final_avg_y_span']:.2f} | "
        f"avg_x_span {layout_metrics['init_avg_x_span']:.2f} -> {layout_metrics['final_avg_x_span']:.2f}"
    )

    order = sorted(range(n_mod), key=lambda u: (y[u], x[u], rel_path[u]))
    old_to_new = [0] * n_mod
    for new_id, old_id in enumerate(order):
        old_to_new[old_id] = new_id

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

    # Stage B: Existing-theory identification & collapsed DAG layout
    t_col = time.time()
    sym_to_lit, sym_path_hints, excluded_syms = parse_published_inventory(args.inventory_path)
    sym_allowed = resolve_symbol_allowed_ancestors(args.db_path, sym_to_lit, sym_path_hints, rel_path, adj_in)
    prover_syms = detect_published_proof_roots(rel_path, sym_to_lit, sym_allowed, excluded_syms)
    dead_edges = find_dead_bridge_imports(args.db_path, mod_name, rel_path, adj_out)
    col_res = build_collapsed_dag(
        mod_name,
        rel_path,
        top_dir,
        adj_out,
        adj_in,
        prover_syms,
        sym_to_lit,
        dead_edges,
        args.y_iters,
        args.x_sweeps,
    )

    n_c = col_res["n_c"]
    n_active = col_res["n_active"]
    n_super = col_res["n_super"]
    c_num_layers = col_res["c_num_layers"]
    c_layer_dy = col_res["c_layer_dy"]
    collapsed_mod_count = len(col_res["frontier_set"]) + len(col_res["collapsed_interior"])
    assert sum(col_res["c_super_counts"]) == collapsed_mod_count
    assert n_active + collapsed_mod_count == n_mod

    print(
        f"Computed collapsed layout in {time.time() - t_col:.2f}s: "
        f"{n_active:,} active + {n_super:,} literature supernodes = {n_c:,} nodes "
        f"(collapsed {collapsed_mod_count:,} modules = {100.0 * collapsed_mod_count / n_mod:.1f}%), "
        f"{c_num_layers} layers, max_edge_weight={col_res['max_edge_weight']}"
    )

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

    unique_dirs = sorted(set(dir_path))
    dir_to_id = {dp: idx for idx, dp in enumerate(unique_dirs)}

    # Dense arrays for full DAG in canonical order
    node_x_f32 = [0.0] * n_mod
    node_group = bytearray(n_mod)
    node_in_deg_list = [0] * n_mod
    node_out_deg_list = [0] * n_mod
    node_dir_id = [0] * n_mod
    short_names: list[str] = [""] * n_mod

    group_x_acc: dict[str, list[float]] = defaultdict(list)
    group_y_acc: dict[str, list[int]] = defaultdict(list)

    for new_id, old_id in enumerate(order):
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

    c_node_x_f32 = col_res["c_node_x_f32"]
    c_xmin = min(c_node_x_f32, default=0.0)
    c_xmax = max(c_node_x_f32, default=0.0)
    c_ymin = 0.0
    c_ymax = round(max(0, c_num_layers - 1) * c_layer_dy, 4)

    # Collapsed canonical node mapping: >= 0 full canonical ID; < 0 -> supernode index -(val + 1)
    pure_active = col_res["pure_active"]
    c_node_full_id = [0] * n_c
    for new_cid, old_cid in enumerate(col_res["c_order"]):
        if old_cid < n_active:
            c_node_full_id[new_cid] = old_to_new[pure_active[old_cid]]
        else:
            s_idx = old_cid - n_active
            c_node_full_id[new_cid] = -(s_idx + 1)

    c_super_group = bytearray(top_to_gid[td] for td in col_res["c_super_dom_top_dir"])
    c_super_titles_blob = "\n".join(col_res["c_super_titles"]).encode("utf-8")

    # Encode supernode edges via LEB128 delta-varint pairs (target_delta, weight)
    c_super_edges_buf = bytearray()
    for nu in range(n_c):
        pairs = col_res["c_super_adj_out"][nu]
        encode_varint(c_super_edges_buf, len(pairs))
        prev_v = 0
        for nv, w in pairs:
            encode_varint(c_super_edges_buf, nv - prev_v)
            encode_varint(c_super_edges_buf, w)
            prev_v = nv

    dead_edges_canonical = sorted(
        (old_to_new[u], old_to_new[v]) for u, v in col_res["effective_dead_edges"]
    )

    header_obj = {
        "node_count": n_mod,
        "edge_count": n_edges,
        "num_layers": num_layers,
        "layer_dy": layer_dy,
        "bounds": {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax},
        "groups": groups_meta,
        "dir_count": len(unique_dirs),
        "layout_metrics": layout_metrics,
        "collapsed": {
            "node_count": n_c,
            "active_node_count": n_active,
            "supernode_count": n_super,
            "collapsed_module_count": collapsed_mod_count,
            "frontier_module_count": len(col_res["frontier_set"]),
            "interior_module_count": len(col_res["collapsed_interior"]),
            "edge_count": col_res["active_edge_cnt"] + col_res["super_edge_cnt"],
            "active_edge_count": col_res["active_edge_cnt"],
            "super_edge_count": col_res["super_edge_cnt"],
            "raw_super_edge_count": col_res["raw_super_edge_cnt"],
            "max_edge_weight": col_res["max_edge_weight"],
            "num_layers": c_num_layers,
            "layer_dy": c_layer_dy,
            "bounds": {"xmin": c_xmin, "xmax": c_xmax, "ymin": c_ymin, "ymax": c_ymax},
            "dead_edge_count": len(dead_edges_canonical),
            "layout_metrics": col_res["c_metrics"],
        },
    }
    header_bytes = json.dumps(header_obj, separators=(",", ":")).encode("utf-8")

    # Encode full-graph CSR edges via unsigned LEB128 delta-varints
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

    # Assemble 4-byte-aligned little-endian LDAG v2 binary payload
    raw_buf = bytearray()
    raw_buf.extend(MAGIC)
    raw_buf.extend(struct.pack("<II", FORMAT_VERSION, len(header_bytes)))
    raw_buf.extend(header_bytes)
    pad4(raw_buf)

    # Full DAG sections
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
    pad4(raw_buf)

    # Collapsed DAG v2 sections
    raw_buf.extend(struct.pack(f"<{c_num_layers + 1}I", *col_res["c_layer_offsets"]))
    raw_buf.extend(struct.pack(f"<{n_c}f", *c_node_x_f32))
    raw_buf.extend(struct.pack(f"<{n_c}i", *c_node_full_id))
    raw_buf.extend(struct.pack(f"<{n_super}I", *col_res["c_super_counts"]))

    raw_buf.extend(struct.pack(f"<{n_super}H", *(min(65535, d) for d in col_res["c_super_frontier_counts"])))
    pad4(raw_buf)

    raw_buf.extend(c_super_group)
    pad4(raw_buf)

    raw_buf.extend(struct.pack("<I", len(c_super_titles_blob)))
    raw_buf.extend(c_super_titles_blob)
    pad4(raw_buf)

    raw_buf.extend(struct.pack("<I", len(c_super_edges_buf)))
    raw_buf.extend(c_super_edges_buf)
    pad4(raw_buf)

    raw_buf.extend(struct.pack("<I", len(dead_edges_canonical)))
    for du, dv in dead_edges_canonical:
        raw_buf.extend(struct.pack("<II", du, dv))

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

    # Collapsed summary stats
    active_by_top = Counter(top_dir[u] for u in pure_active)
    collapsed_domain_breakdown = []
    for g in groups_meta:
        td = g["name"]
        tot_g = g["count"]
        act_g = active_by_top[td]
        col_g = tot_g - act_g
        collapsed_domain_breakdown.append(
            {
                "name": td,
                "total_modules": tot_g,
                "active_modules": act_g,
                "collapsed_modules": col_g,
                "collapsed_pct": round(100.0 * col_g / tot_g, 1) if tot_g else 0.0,
            }
        )

    top_supernodes_summary = []
    for s_idx, gk in enumerate(col_res["sorted_super_keys"][:30]):
        old_cid = n_active + s_idx
        in_e = len(col_res["c_adj_in"][old_cid])
        raw_in_e = sum(col_res["c_weights_in"][old_cid])
        cone_cnt = len(col_res["lit_groups"][gk]) + len(col_res["super_cone_interior"][gk])
        top_supernodes_summary.append(
            {
                "title": col_res["c_super_titles"][s_idx],
                "inventory_key": gk[0],
                "owned_modules": col_res["c_super_counts"][s_idx],
                "cone_modules": cone_cnt,
                "frontier_modules": col_res["c_super_frontier_counts"][s_idx],
                "in_edges": in_e,
                "raw_in_edges": raw_in_e,
                "dominant_domain": col_res["c_super_dom_top_dir"][s_idx],
                "layer": col_res["c_y"][old_cid],
            }
        )

    w_hist = col_res["weight_hist"]
    collapsed_summary = {
        "node_count": n_c,
        "active_node_count": n_active,
        "supernode_count": n_super,
        "collapsed_module_count": collapsed_mod_count,
        "collapsed_pct": round(100.0 * collapsed_mod_count / n_mod, 2) if n_mod else 0.0,
        "frontier_module_count": len(col_res["frontier_set"]),
        "interior_module_count": len(col_res["collapsed_interior"]),
        "edge_count": col_res["active_edge_cnt"] + col_res["super_edge_cnt"],
        "active_edge_count": col_res["active_edge_cnt"],
        "super_edge_count": col_res["super_edge_cnt"],
        "raw_super_edge_count": col_res["raw_super_edge_cnt"],
        "max_edge_weight": col_res["max_edge_weight"],
        "weighted_edges_ge_2": sum(cnt for w, cnt in w_hist.items() if w >= 2),
        "weight_histogram": {str(k): w_hist[k] for k in sorted(w_hist.keys())},
        "num_layers": c_num_layers,
        "layer_dy": c_layer_dy,
        "min_intra_layer_gap": round(col_res["c_min_gap"], 4) if math.isfinite(col_res["c_min_gap"]) else None,
        "bounds": header_obj["collapsed"]["bounds"],
        "aspect_ratio": round((c_xmax - c_xmin) / max(1e-6, c_ymax - c_ymin), 3),
        "dead_edges_pruned": len(dead_edges_canonical),
        "layout_metrics": col_res["c_metrics"],
        "domain_breakdown": collapsed_domain_breakdown,
        "top_supernodes": top_supernodes_summary,
    }

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
        "collapsed": collapsed_summary,
        "payload": {
            "format_version": FORMAT_VERSION,
            "raw_binary_bytes": len(raw_buf),
            "gzip_bytes": len(gz_bytes),
            "js_file_bytes": data_js_path.stat().st_size,
            "edge_varint_bytes": len(edge_buf),
            "c_super_edges_bytes": len(c_super_edges_buf),
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
