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
import statistics
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
FORMAT_VERSION = 3

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

PALETTE_NAMES = {
    "#2563eb": "Blue",
    "#ea580c": "Orange",
    "#ca8a04": "Gold / Amber",
    "#0d9488": "Teal",
    "#059669": "Emerald green",
    "#c026d3": "Fuchsia / Magenta",
    "#7c3aed": "Violet / Purple",
    "#64748b": "Slate gray",
    "#4f46e5": "Indigo",
    "#111827": "Charcoal / Near-black",
}

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
        "SELECT id, name, rel_path, dir_path, top_dir FROM modules WHERE reachable_from_main = 1 ORDER BY rel_path ASC, id ASC"
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

    mod_rows = cur.execute(
        "SELECT id, rel_path FROM modules WHERE reachable_from_main = 1 ORDER BY rel_path ASC, id ASC"
    ).fetchall()
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
            r"^[ \t]*(?:@\[.*?\]\s*)*(?:set_option\s+[^\n]*?\s+in\s+)*(?:(?:public|meta|private|protected|noncomputable|local|scoped)\s+)*(theorem|lemma)\s+([^\s:(\[{]+)",
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
    import_re = re.compile(r"^(?:(?:public|meta)\s+)?import\s+")
    imports = [l for l in lines if import_re.match(l)]
    body_lines = [l for l in lines if not import_re.match(l) and l.strip()]
    body_text = "\n".join(body_lines)

    if len(imports) < 50 or len(body_lines) > 40 or "theorem " not in body_text:
        return dead_edges

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    mod_decls: dict[int, list[str]] = defaultdict(list)
    db_mods = cur.execute("SELECT id, name FROM modules WHERE reachable_from_main = 1").fetchall()
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
        "c_sort_keys": c_sort_keys,
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
        "c_adj_out": c_adj_out,
        "c_weights_out": c_weights_out,
        "c_adj_in": c_adj_in,
        "c_weights_in": c_weights_in,
        "effective_dead_edges": effective_dead_edges,
        "peeled_barrels": peeled_barrels,
    }


def compute_transitive_reduction(
    n_nodes: int,
    adj_out: list[list[int]],
    adj_in: list[list[int]],
) -> tuple[list[list[int]], list[list[int]]]:
    """Compute exact transitive reduction (Hasse diagram) via striped Python int bitsets."""
    in_rem = [len(adj_in[i]) for i in range(n_nodes)]
    q: deque[int] = deque(i for i in range(n_nodes) if in_rem[i] == 0)
    topo: list[int] = []
    while q:
        u = q.popleft()
        topo.append(u)
        for v in adj_out[u]:
            in_rem[v] -= 1
            if in_rem[v] == 0:
                q.append(v)
    if len(topo) != n_nodes:
        raise RuntimeError(f"Transitive reduction failed: processed {len(topo)} of {n_nodes} nodes")

    topo_pos = [0] * n_nodes
    for idx, u in enumerate(topo):
        topo_pos[u] = idx

    stripe_size = 16384
    tr_out: list[list[int]] = [[] for _ in range(n_nodes)]
    for start in range(0, n_nodes, stripe_size):
        end = min(n_nodes, start + stripe_size)
        reach1 = [0] * n_nodes
        for pos in range(end - 1, -1, -1):
            u = topo[pos]
            outs = adj_out[u]
            if not outs:
                continue
            r2 = 0
            r1 = 0
            for v in outs:
                rv = reach1[v]
                if rv:
                    r2 |= rv
                    r1 |= rv
                pv = topo_pos[v]
                if start <= pv < end:
                    r1 |= 1 << (pv - start)
            reach1[u] = r1
            for v in outs:
                pv = topo_pos[v]
                if start <= pv < end and not ((r2 >> (pv - start)) & 1):
                    tr_out[u].append(v)

    tr_in: list[list[int]] = [[] for _ in range(n_nodes)]
    for u in range(n_nodes):
        tr_out[u].sort()
        for v in tr_out[u]:
            tr_in[v].append(u)
    return tr_out, tr_in


def pack_edge_bitmask(bits: list[bool]) -> bytes:
    """Pack boolean list little-endian (bit i at byte i>>3, mask 1<<(i&7))."""
    out = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        if b:
            out[i >> 3] |= 1 << (i & 7)
    return bytes(out)


def simplify_chains_and_leaves(
    n_nodes: int,
    adj_out: list[list[int]],
    adj_in: list[list[int]],
    init_node_weights: list[int],
    init_edge_mults: list[dict[int, int]] | None,
    protected_nodes: set[int],
    node_full_ids: list[int],
) -> dict[str, Any]:
    """2-phase fixed-point collapse: simple leaves fold into parent nw; (1,1) chains contract onto edges."""
    edge_m: list[dict[int, int]] = [
        {v: (init_edge_mults[u][v] if init_edge_mults is not None else 1) for v in adj_out[u]}
        for u in range(n_nodes)
    ]
    edge_c: list[dict[int, int]] = [{v: 0 for v in adj_out[u]} for u in range(n_nodes)]
    edge_c_leaves: list[dict[int, int]] = [{v: 0 for v in adj_out[u]} for u in range(n_nodes)]
    edge_c_chains: list[dict[int, int]] = [{v: 0 for v in adj_out[u]} for u in range(n_nodes)]
    adj_i: list[set[int]] = [set(adj_in[u]) for u in range(n_nodes)]

    nw = list(init_node_weights)
    abs_leaves = [0] * n_nodes
    abs_chains = [0] * n_nodes
    rep_full_id = [-1] * n_nodes
    rep_weight = [0] * n_nodes
    alive = [True] * n_nodes

    leaves_removed = 0
    chains_removed = 0
    init_total_weight = sum(init_node_weights)

    changed = True
    while changed:
        changed = False
        # Phase 1: Peel all unprotected simple leaves (in=1, out=0) iteratively
        lq: deque[int] = deque(
            u
            for u in range(n_nodes)
            if alive[u] and u not in protected_nodes and len(adj_i[u]) == 1 and len(edge_m[u]) == 0
        )
        while lq:
            u = lq.popleft()
            if not alive[u] or u in protected_nodes or len(adj_i[u]) != 1 or len(edge_m[u]) != 0:
                continue
            p = next(iter(adj_i[u]))
            alive[u] = False
            adj_i[u].clear()
            leaves_removed += 1
            changed = True

            edge_m[p].pop(u)
            c_pu = edge_c[p].pop(u)
            cl_pu = edge_c_leaves[p].pop(u)
            cc_pu = edge_c_chains[p].pop(u)

            cand_w = nw[u] + c_pu
            nw[p] += cand_w
            abs_leaves[p] += 1 + abs_leaves[u] + cl_pu
            abs_chains[p] += abs_chains[u] + cc_pu

            cand_fid = node_full_ids[u] if rep_full_id[u] == -1 else rep_full_id[u]
            if cand_w > rep_weight[p] or (
                cand_w == rep_weight[p] and (rep_full_id[p] == -1 or cand_fid < rep_full_id[p])
            ):
                rep_full_id[p] = cand_fid
                rep_weight[p] = cand_w

            if alive[p] and p not in protected_nodes and len(adj_i[p]) == 1 and len(edge_m[p]) == 0:
                lq.append(p)

        # Phase 2: Contract all unprotected pass-through (1,1) nodes deterministically
        cq: deque[int] = deque(
            u
            for u in range(n_nodes)
            if alive[u] and u not in protected_nodes and len(adj_i[u]) == 1 and len(edge_m[u]) == 1
        )
        while cq:
            u = cq.popleft()
            if not alive[u] or u in protected_nodes or len(adj_i[u]) != 1 or len(edge_m[u]) != 1:
                continue
            p = next(iter(adj_i[u]))
            c = next(iter(edge_m[u]))
            if p == c:
                raise RuntimeError(f"Self-loop encountered during chain contraction at node {u}")
            alive[u] = False
            adj_i[u].clear()
            chains_removed += 1
            changed = True

            m_pu = edge_m[p].pop(u)
            m_uc = edge_m[u].pop(c)
            c_pu = edge_c[p].pop(u)
            c_uc = edge_c[u].pop(c)
            cl_pu = edge_c_leaves[p].pop(u)
            cl_uc = edge_c_leaves[u].pop(c)
            cc_pu = edge_c_chains[p].pop(u)
            cc_uc = edge_c_chains[u].pop(c)
            adj_i[c].discard(u)

            path_mult = max(m_pu, m_uc)
            added_c = c_pu + c_uc + nw[u]
            added_cl = cl_pu + cl_uc + abs_leaves[u]
            added_cc = cc_pu + cc_uc + 1 + abs_chains[u]

            if c in edge_m[p]:
                edge_m[p][c] += path_mult
                edge_c[p][c] += added_c
                edge_c_leaves[p][c] += added_cl
                edge_c_chains[p][c] += added_cc
            else:
                edge_m[p][c] = path_mult
                edge_c[p][c] = added_c
                edge_c_leaves[p][c] = added_cl
                edge_c_chains[p][c] = added_cc
                adj_i[c].add(p)

            if alive[p] and p not in protected_nodes and len(adj_i[p]) == 1 and len(edge_m[p]) == 1:
                cq.append(p)
            if alive[c] and c not in protected_nodes and len(adj_i[c]) == 1 and len(edge_m[c]) == 1:
                cq.append(c)

    surviving = [u for u in range(n_nodes) if alive[u]]
    total_nw = sum(nw[u] for u in surviving)
    total_ec = sum(c_val for u in surviving for c_val in edge_c[u].values())
    if total_nw + total_ec != init_total_weight:
        raise RuntimeError(
            f"Module conservation violated: node_w({total_nw}) + edge_chain({total_ec}) != {init_total_weight}"
        )

    for u in surviving:
        if u not in protected_nodes:
            if 1 + abs_leaves[u] + abs_chains[u] != nw[u]:
                raise RuntimeError(f"Weight decomposition mismatch at node {u}: 1+{abs_leaves[u]}+{abs_chains[u]} != {nw[u]}")
            if len(adj_i[u]) == 1 and len(edge_m[u]) <= 1:
                raise RuntimeError(f"Uncollapsed simple node remained: {u} (in={len(adj_i[u])}, out={len(edge_m[u])})")
        for v in edge_m[u]:
            if edge_c_leaves[u][v] + edge_c_chains[u][v] != edge_c[u][v]:
                raise RuntimeError(f"Edge chain split mismatch on {u}->{v}")

    return {
        "surviving": surviving,
        "nw": nw,
        "abs_leaves": abs_leaves,
        "abs_chains": abs_chains,
        "rep_full_id": rep_full_id,
        "edge_m": edge_m,
        "edge_c": edge_c,
        "leaves_removed": leaves_removed,
        "chains_removed": chains_removed,
        "total_nw": total_nw,
        "total_ec": total_ec,
    }


def build_simplified_view(
    simp: dict[str, Any],
    sort_keys: list[str],
    node_full_ids: list[int],
    full_rel_path: list[str],
    full_order: list[int],
    c_super_titles: list[str],
    y_iters: int,
    x_sweeps: int,
) -> dict[str, Any]:
    """Compute weighted Sugiyama layout and binary sections for a simplified DAG view."""
    surviving = simp["surviving"]
    n_s = len(surviving)
    old_to_dense = {old_u: i for i, old_u in enumerate(surviving)}

    s_sort_keys = [sort_keys[u] for u in surviving]
    s_adj_out: list[list[int]] = [[] for _ in range(n_s)]
    s_adj_in: list[list[int]] = [[] for _ in range(n_s)]
    s_w_out: list[list[int]] = [[] for _ in range(n_s)]
    s_w_in: list[list[int]] = [[] for _ in range(n_s)]

    edge_m = simp["edge_m"]
    edge_c = simp["edge_c"]
    for i, old_u in enumerate(surviving):
        targets = sorted(old_to_dense[old_v] for old_v in edge_m[old_u].keys())
        s_adj_out[i] = targets
        for j in targets:
            old_v = surviving[j]
            w_tot = edge_m[old_u][old_v] + edge_c[old_u][old_v]
            s_w_out[i].append(w_tot)
            s_adj_in[j].append(i)
            s_w_in[j].append(w_tot)

    s_y, s_x, s_layer_dy, s_metrics = compute_layout(
        s_sort_keys,
        s_adj_out,
        s_adj_in,
        y_iters,
        x_sweeps,
        edge_weights_out=s_w_out,
        edge_weights_in=s_w_in,
    )
    s_num_layers = (max(s_y) + 1) if n_s else 0

    s_order = sorted(range(n_s), key=lambda u: (s_y[u], s_x[u], s_sort_keys[u]))
    s_dense_to_canon = [0] * n_s
    for new_sid, dense_id in enumerate(s_order):
        s_dense_to_canon[dense_id] = new_sid

    s_layer_offsets = [0] * (s_num_layers + 1)
    prev_layer = -1
    prev_x = 0.0
    s_min_gap = float("inf")
    for new_sid, dense_id in enumerate(s_order):
        ly = s_y[dense_id]
        xv = s_x[dense_id]
        if ly != prev_layer:
            for fill_l in range(prev_layer + 1, ly + 1):
                s_layer_offsets[fill_l] = new_sid
            prev_layer = ly
        else:
            gap = xv - prev_x
            if gap < s_min_gap:
                s_min_gap = gap
            if gap < 1.0 - 1e-4:
                raise RuntimeError(f"Simplified layer {ly} spacing violation at node {new_sid}: gap={gap}")
        prev_x = xv
    for fill_l in range(prev_layer + 1, s_num_layers + 1):
        s_layer_offsets[fill_l] = n_s

    s_node_x_f32 = [struct.unpack("<f", struct.pack("<f", s_x[dense_id]))[0] for dense_id in s_order]
    s_node_full_id = [node_full_ids[surviving[dense_id]] for dense_id in s_order]

    nw = simp["nw"]
    abs_leaves = simp["abs_leaves"]
    abs_chains = simp["abs_chains"]
    rep_full_id = simp["rep_full_id"]

    weighted_node_records: list[tuple[int, int, int, int, int]] = []
    max_node_weight = 1
    for new_sid, dense_id in enumerate(s_order):
        old_u = surviving[dense_id]
        fid = s_node_full_id[new_sid]
        if fid >= 0 and nw[old_u] > 1:
            w_val = nw[old_u]
            if w_val > max_node_weight:
                max_node_weight = w_val
            weighted_node_records.append(
                (new_sid, w_val, abs_leaves[old_u], abs_chains[old_u], rep_full_id[old_u])
            )

    # Canonical edges and 1-bit-flagged LEB128 edge stream
    canon_edges: list[list[tuple[int, int, int]]] = [[] for _ in range(n_s)]
    edge_count = 0
    weighted_edge_count = 0
    chain_edge_count = 0
    max_edge_weight = 1
    max_edge_mult = 1
    max_edge_chain = 0

    for dense_u, old_u in enumerate(surviving):
        nu = s_dense_to_canon[dense_u]
        pairs: list[tuple[int, int, int]] = []
        for old_v, mult in edge_m[old_u].items():
            nv = s_dense_to_canon[old_to_dense[old_v]]
            if nu >= nv:
                raise RuntimeError(f"Simplified canonical ID invariant violated: {nu} -> {nv}")
            ch = edge_c[old_u][old_v]
            pairs.append((nv, mult, ch))
            edge_count += 1
            wtot = mult + ch
            if wtot >= 2:
                weighted_edge_count += 1
            if ch > 0:
                chain_edge_count += 1
            if wtot > max_edge_weight:
                max_edge_weight = wtot
            if mult > max_edge_mult:
                max_edge_mult = mult
            if ch > max_edge_chain:
                max_edge_chain = ch
        pairs.sort()
        canon_edges[nu] = pairs

    edge_buf = bytearray()
    for nu in range(n_s):
        pairs = canon_edges[nu]
        encode_varint(edge_buf, len(pairs))
        prev_v = 0
        for nv, mult, ch in pairs:
            is_w = 1 if (mult != 1 or ch != 0) else 0
            encode_varint(edge_buf, ((nv - prev_v) << 1) | is_w)
            if is_w:
                encode_varint(edge_buf, mult)
                encode_varint(edge_buf, ch)
            prev_v = nv

    xmin = min(s_node_x_f32, default=0.0)
    xmax = max(s_node_x_f32, default=0.0)
    ymin = 0.0
    ymax = round(max(0, s_num_layers - 1) * s_layer_dy, 4)

    def _label_for_fid(fid: int) -> str:
        if fid >= 0:
            return full_rel_path[full_order[fid]]
        return f"[Literature] {c_super_titles[-(fid + 1)]}"

    top_weighted_nodes = [
        {
            "rel_path": full_rel_path[full_order[s_node_full_id[rec[0]]]],
            "weight": rec[1],
            "absorbed_leaves": rec[2],
            "absorbed_chains": rec[3],
            "rep_rel_path": full_rel_path[full_order[rec[4]]] if rec[4] >= 0 else None,
        }
        for rec in sorted(weighted_node_records, key=lambda r: (-r[1], r[0]))[:10]
    ]

    top_edges_raw: list[tuple[int, int, int, int, int]] = []
    for nu in range(n_s):
        for nv, mult, ch in canon_edges[nu]:
            if mult + ch >= 2:
                top_edges_raw.append((mult + ch, ch, mult, nu, nv))
    top_edges_raw.sort(key=lambda t: (-t[0], -t[1], -t[2], t[3], t[4]))
    top_weighted_edges = [
        {
            "src": _label_for_fid(s_node_full_id[nu]),
            "dst": _label_for_fid(s_node_full_id[nv]),
            "weight": wtot,
            "mult": mult,
            "chain": ch,
        }
        for wtot, ch, mult, nu, nv in top_edges_raw[:10]
    ]

    summary_meta = {
        "node_count": n_s,
        "edge_count": edge_count,
        "num_layers": s_num_layers,
        "layer_dy": s_layer_dy,
        "min_intra_layer_gap": round(s_min_gap, 4) if math.isfinite(s_min_gap) else None,
        "bounds": {"xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax},
        "aspect_ratio": round((xmax - xmin) / max(1e-6, ymax - ymin), 3),
        "leaves_removed": simp["leaves_removed"],
        "chains_removed": simp["chains_removed"],
        "weighted_node_count": len(weighted_node_records),
        "max_node_weight": max_node_weight,
        "weighted_edge_count": weighted_edge_count,
        "chain_edge_count": chain_edge_count,
        "max_edge_weight": max_edge_weight,
        "max_edge_mult": max_edge_mult,
        "max_edge_chain": max_edge_chain,
        "total_node_weight": simp["total_nw"],
        "total_edge_chain_weight": simp["total_ec"],
        "layout_metrics": s_metrics,
        "top_weighted_nodes": top_weighted_nodes,
        "top_weighted_edges": top_weighted_edges,
    }

    return {
        "layer_offsets": s_layer_offsets,
        "node_x_f32": s_node_x_f32,
        "node_full_id": s_node_full_id,
        "weighted_node_records": weighted_node_records,
        "edge_buf": edge_buf,
        "summary": summary_meta,
    }


def compute_decl_stats(db_path: Path) -> dict[str, Any]:
    """Compute reachable declaration totals, median/mean per module, and sample dist=1 entry module from SQLite."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    rows = conn.execute(
        """
        SELECT rel_path,
               n_theorems + n_lemmas + n_defs + n_structures + n_other_decls AS n_decls,
               dist_from_main
        FROM modules
        WHERE reachable_from_main = 1
        ORDER BY dist_from_main ASC, rel_path ASC
        """
    ).fetchall()
    conn.close()
    decls = [int(r[1]) for r in rows]
    n = len(decls)
    total_decls = sum(decls)
    single_decls = sum(1 for d in decls if d == 1)
    ex_mod = None
    for rel, _, dist_m in rows:
        if dist_m == 1 and rel != "Statements.lean":
            ex_mod = rel
            break
    if ex_mod is None:
        ex_mod = rows[1][0] if len(rows) > 1 else (rows[0][0] if rows else "Main.lean")
    med_raw = statistics.median(decls) if n else 0
    med_val: int | float = int(med_raw) if float(med_raw).is_integer() else round(float(med_raw), 1)
    return {
        "total_decls": total_decls,
        "median_decls": med_val,
        "mean_decls": round(total_decls / n, 2) if n else 0.0,
        "single_decl_modules": single_decls,
        "single_decl_pct": round(100.0 * single_decls / n, 1) if n else 0.0,
        "example_second_module": ex_mod,
    }


def _short_mod_name(rel_path: str) -> str:
    p = rel_path[:-5] if rel_path.endswith(".lean") else rel_path
    parts = p.split("/")
    return "/".join(parts[-2:]) if len(parts) >= 2 else p


def _stem_name(rel_path: str) -> str:
    return Path(rel_path).stem


def render_full_dag_md(
    summary: dict[str, Any],
    meta: dict[str, Any],
    decl_stats: dict[str, Any] | None = None,
    version_label: str = "",
    rel_src_label: str = "src/",
) -> str:
    """Render FULL_DAG.md with full methodology, derivations, and live metrics."""
    meta_decls = sum(meta.get("reachable_decl_counts", meta.get("decl_counts", {})).values())
    ds = decl_stats or {}
    decl_total = ds.get("total_decls") or meta_decls
    n_mod = summary["node_count"]
    n_edges = summary["edge_count"]
    n_layers = summary["num_layers"]
    h_max = max(0, n_layers - 1)
    lm = summary["layout_metrics"]
    lw = lm["layer_widths"]

    col = summary["collapsed"]
    clm = col["layout_metrics"]
    clw = clm["layer_widths"]
    fh = summary["full_hasse"]
    eh = summary["existing_hasse"]
    simp = summary["simplified"]
    payload = summary["payload"]

    med_decls = ds.get("median_decls", "—")
    mean_decls = ds.get("mean_decls", round(decl_total / max(1, n_mod), 2))
    single_mods = ds.get("single_decl_modules", 0)
    single_pct = ds.get("single_decl_pct", 0.0)
    ex_second = ds.get("example_second_module", "Statements.lean")
    ex_second_mod = ex_second[:-5].replace("/", ".") if ex_second.endswith(".lean") else ex_second.replace("/", ".")
    decl_ratio = round(decl_total / max(1, n_mod), 1)

    fh_red_pct = 100.0 * fh["redundant_edge_count"] / max(1, n_edges)
    eh_red_pct = 100.0 * eh["redundant_edge_count"] / max(1, col["edge_count"])

    fs_sm = simp.get("full_simp", {})
    fhs_sm = simp.get("full_hasse_simp", {})
    top_sup = col["top_supernodes"][0] if col.get("top_supernodes") else None
    top_fhs_node = fhs_sm.get("top_weighted_nodes", [None])[0]

    ver_note = f" (`{version_label}`)" if version_label else ""
    vid_cmd = version_label or "<version-id>"
    src_no_slash = rel_src_label.rstrip("/")

    lines: list[str] = []
    a = lines.append
    a(f"# Full Lean Module Dependency DAG{ver_note}")
    a("")
    a("This document describes the repeatable layout pipeline, binary data packaging, graph-simplification modes, and WebGL visualization behind the interactive full-graph viewer:")
    a("")
    a("- **Interactive Viewer:** [full_dag.html](full_dag.html) (pan and zoom across all modules and import edges, with three composable simplification switches: **Collapse existing theory** `C`, **Hide redundant imports** `H`, and **Collapse chains & leaves** `L`, plus the **Max depth** BFS filter `[` / `]`)")
    a("- **Layout Generator:** [build_full_dag.py](build_full_dag.py)")
    a("- **Layout Summary:** [layout_summary.json](layout_summary.json)")
    a("- **SQLite Indexer:** [build_index.py](../build_index.py)")
    a("- **Existing-Theory Inventory & Methodology:** [PUBLISHED_THEOREMS_INVENTORY.html](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.html) ([Markdown](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md))")
    a("")
    a(
        f"> **Direction Convention:** Every node represents a `.lean` module under `{src_no_slash}`. A directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Top-level theorem modules sit at the top (`layer 0`), and foundational definitions and leaf modules sit below (`layer 1..{h_max}`)."
    )
    a("")
    a("---")
    a("")
    a("## 1. Why Modules Rather Than Individual Statements?")
    a("")
    a(
        f"In Lean 4, a **module** corresponds 1-to-1 with a single `.lean` source file under `{rel_src_label}` (the compilation unit that produces one `.olean` binary). For instance, `{rel_src_label}Main.lean` is module `Main`, and `{rel_src_label}{ex_second}` is module `{ex_second_mod}`. Each module begins with explicit `import` headers declaring its dependencies, and because Lean forbids circular imports, the module import graph is guaranteed to be a strict DAG."
    )
    a("")
    a("Inside those modules live individual **declarations** (`theorem`, `lemma`, `def`, `structure`, `class`, `inductive`, `abbrev`, `instance`). A finer-grained **declaration-level DAG**—linking every declaration to the exact constants referenced in its type and proof term—is not tracked here for three reasons:")
    a("")
    a(
        f"1. **Accurate extraction requires full compilation:** Lean 4 proofs rely heavily on tactics (`simp`, `linarith`, `ring`, `aesop`, etc.), typeclass synthesis, coercions, and `open`ed namespaces, so many dependencies never appear explicitly by name in raw `.lean` source text. Recovering true declaration-level edges requires compiling the entire codebase to `.olean` files and inspecting Lean's elaborated `Environment` (for example, `Expr.getUsedConstants` on each `ConstantInfo`). By contrast, module `import` statements are explicit syntax at the top of every file, allowing [build_index.py](../build_index.py) to extract the exact module DAG deterministically from `{rel_src_label}` using only Python."
    )
    a(
        f"2. **Scale and architectural clarity:** Across reachable modules, the codebase contains **{decl_total:,}** declarations ({decl_ratio}× the **{n_mod:,}** modules). Including tactic-elaborated and typeclass-synthesized edges would expand the graph to millions of edges, dramatically increasing layout and browser rendering cost while obscuring macro-level mathematical structure under low-level algebraic and tactic plumbing."
    )
    a(
        f"3. **Modules here are fine-grained:** Across the **{n_mod:,}** reachable modules in `{rel_src_label}`, the median module contains **{med_decls}** declarations (mean `{mean_decls:.2f}`), and **{single_mods:,} modules ({single_pct:.1f}%)** contain a single declaration. The module DAG therefore closely tracks theorem-level architecture while grouping small local helper lemmas together."
    )
    a("")
    a("---")
    a("")
    a("## 2. End-to-End Repeatable Pipeline")
    a("")
    a("The visualization is generated deterministically from the Lean source tree with zero hardcoded module paths, directory names, layer counts, or fixed directory-to-color mappings. Rebuilding this version runs a single orchestrator command:")
    a("")
    a("```bash")
    a(f"python3 analysis/build_all.py --version {vid_cmd} --steps full_dag")
    a("```")
    a("")
    a("Or directly via `build_full_dag.py` against SQLite:")
    a("")
    a("```bash")
    a(f"python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/{vid_cmd}/data/graph.sqlite --out-dir analysis/versions/{vid_cmd}/full_dag")
    a("```")
    a("")
    a("The pipeline executes five stages:")
    a("")
    a(f"1. **Source Indexing (`analysis/build_index.py`):** Walks `{rel_src_label}` in sorted relative-path order, parses `import` statements, builds the deduplicated internal module import graph, and writes `graph.sqlite` and `meta.json`.")
    a("2. **Acyclicity Verification (`load_graph` + Kahn's topological sort):** Loads all reachable modules ordered deterministically by `(rel_path, id)` and runs Kahn's topological algorithm from roots ($\\text{in\\_degree} = 0$). If any import cycle exists, the pipeline aborts immediately with an error.")
    a("3. **Deterministic 3-Stage Sugiyama Layout (`compute_layout`):** Assigns integer layer coordinates $y(u)$ and continuous non-overlapping horizontal coordinates $x(u)$, then scales vertical spacing dynamically to preserve a readable widescreen aspect ratio.")
    a("4. **Graph Simplification & Multi-View Weighted Layouts (`build_collapsed_dag`, `compute_transitive_reduction`, `simplify_chains_and_leaves`):**")
    a(f"   - Applies the inventory-driven proof-frontier cut to contract peer-reviewed background proofs into **{col['supernode_count']} Literature Supernodes** (`existing`).")
    a("   - Computes exact transitive reduction (Hasse diagrams) on both the full DAG (`full_hasse`) and existing-theory DAG (`existing_hasse`), packing 1-bit-per-edge masks for zero-jump in-place toggling.")
    a("   - Runs a 2-phase fixed-point chain/leaf collapse (`simplify_chains_and_leaves`) across all four `(existing, hasse)` combinations (`full_simp`, `full_hasse_simp`, `existing_simp`, `existing_hasse_simp`), computing weighted Sugiyama layouts using edge weights $w_E = \\text{mult} + \\text{chain}$.")
    a(
        f"5. **Canonical Re-Indexing & `LDAG` v{payload['format_version']} Packaging:** Re-indexes every node-bearing layout in `(y, x, sort_key)` order, packs typed arrays, LEB128 delta-varint CSR adjacency lists, 1-bit Hasse masks, sparse weighted-anchor records, and 1-bit-flagged weighted edge streams into a 4-byte-aligned `LDAG` v{payload['format_version']} binary buffer, compresses deterministically (`gzip` with `mtime=0`), and emits [full_dag_data.js](full_dag_data.js) alongside [layout_summary.json](layout_summary.json)."
    )
    a("")
    a("---")
    a("")
    a("## 3. Layout Algorithm")
    a("")
    a(f"Drawing the complete import graph of **{n_mod:,}** modules and **{n_edges:,}** edges requires strict topological orientation (every edge pointing downward) while minimizing vertical edge spans and horizontal edge crossings.")
    a("")
    a("### Stage 1: Bottom-Aligned Longest-Path Layering")
    a("")
    a("First, module heights $h(u)$ from leaf modules ($\\text{out\\_degree} = 0$) are computed in reverse topological order:")
    a("")
    a("$$h(u) = \\begin{cases} 0 & \\text{if } \\text{out}(u) = \\emptyset, \\\\ 1 + \\max_{(u, v) \\in E} h(v) & \\text{otherwise.} \\end{cases}$$")
    a("")
    a(f"Setting initial vertical rank $y_0(u) = H_{{\\max}} - h(u)$ places the root entry module (`Main`, $h = {h_max}$) at $y = 0$ and guarantees $y_0(v) \\ge y_0(u) + 1$ for every edge $(u, v) \\in E$.")
    a("")
    a("### Stage 2: Feasible $L_1$ Vertical Rank Tightening")
    a("")
    a("Bottom-aligned layering leaves intermediate modules with fewer outgoing than incoming dependencies sitting deeper than necessary. To reduce total vertical edge length $\\sum_{(u,v)\\in E} (y(v) - y(u))$ while strictly preserving the DAG invariant $y(v) \\ge y(u) + 1$, the generator runs up to 25 alternating topological and reverse-topological coordinate-descent sweeps.")
    a("")
    a("At each node $u$, the feasible integer interval imposed by its neighbors is:")
    a("")
    a("$$\\ell(u) = \\begin{cases} 0 & \\text{if } \\text{in}(u) = \\emptyset, \\\\ \\max_{(p, u) \\in E} y(p) + 1 & \\text{otherwise,} \\end{cases} \\qquad r(u) = \\begin{cases} H_{\\max} & \\text{if } \\text{out}(u) = \\emptyset, \\\\ \\min_{(u, c) \\in E} y(c) - 1 & \\text{otherwise.} \\end{cases}$$")
    a("")
    a("Since the local derivative of total edge span with respect to $y(u)$ is $|\\text{in}(u)| - |\\text{out}(u)|$:")
    a("- If $|\\text{in}(u)| > |\\text{out}(u)|$, $u$ moves to $\\ell(u)$ (pulled upward toward its importers).")
    a("- If $|\\text{out}(u)| > |\\text{in}(u)|$, $u$ moves to $r(u)$ (pulled downward toward its dependencies).")
    a("- If $|\\text{in}(u)| = |\\text{out}(u)|$, $u$ moves to the rounded mean of its neighbors clamped to $[\\ell(u), r(u)]$.")
    a("")
    a(
        f"Across the full graph, these sweeps reduce mean vertical edge span from **{lm['init_avg_y_span']:.3f}** layers to **{lm['final_avg_y_span']:.3f}** layers, placing **{lm['span_eq_1_edges']:,}** edges on adjacent layers ($\\Delta y = 1$) and **{lm['span_le_5_edges']:,}** edges within $\\Delta y \\le 5$."
    )
    a("")
    a("### Stage 3: Weighted Barycenter Ordering & Isotonic $L_2$ Placement")
    a("")
    a(f"Nodes are grouped into layers $L_0, \\dots, L_{{{h_max}}}$, initially sorted by `rel_path` and centered with unit spacing. The generator then executes {lm['x_sweeps_run']} alternating top-down and bottom-up sweeps:")
    a("")
    a("1. **Inverse-Span Weighted Barycenter:** For every node $u \\in L_k$, its target horizontal position $\\bar{x}(u)$ averages both incoming and outgoing neighbors weighted by $w(u, v) = |y(u) - y(v)|^{-1}$ so short-span edges pull more strongly than long-span cross-layer edges:")
    a("")
    a("$$\\bar{x}(u) = \\frac{\\sum_{v \\in \\text{in}(u) \\cup \\text{out}(u)} \\frac{x(v)}{|y(u) - y(v)|}}{\\sum_{v \\in \\text{in}(u) \\cup \\text{out}(u)} \\frac{1}{|y(u) - y(v)|}}.$$")
    a("")
    a("2. **Permutation & Relaxation:** During the first 10 sweeps, each layer is re-sorted by $(\\bar{x}(u), \\text{rel\\_path}(u))$ to eliminate crossings; during the final sweeps, the layer ordering is held fixed while coordinates relax smoothly.")
    a("3. **Pool-Adjacent-Violators (PAV) Isotonic Projection:** Within each ordered layer $u_0, \\dots, u_{m-1}$, coordinates are projected onto the non-overlap polytope $x(u_{i+1}) - x(u_i) \\ge 1.0$ by solving the exact $O(m)$ isotonic $L_2$ regression problem $\\min \\sum_{i=0}^{m-1} (x_i - \\bar{x}(u_i))^2$ via the Pool-Adjacent-Violators algorithm on $z_i = x_i - i$ with target $t_i = \\bar{x}(u_i) - i$.")
    a("")
    a(
        f"This stage reduces mean horizontal edge span $|\\Delta x|$ from **{lm['init_avg_x_span']:.3f}** units to **{lm['final_avg_x_span']:.3f}** units, while enforcing a strict minimum horizontal gap of **{summary['min_intra_layer_gap'] or 1.0:.1f}** world unit between adjacent nodes in every layer."
    )
    a("")
    a(
        f"Finally, layer vertical spacing $\\Delta y$ is computed dynamically from total horizontal span $W_x = x_{{\\max}} - x_{{\\min}}$ and layer count $K$ as $\\Delta y = \\text{{clamp}}\\!\\left(\\frac{{W_x}}{{1.85 \\cdot (K - 1)}},\\, 4.0,\\, 12.0\\right)$, yielding $\\Delta y = {summary['layer_dy']:.4f}$ and an overall aspect ratio of **{summary['aspect_ratio']:.2f} : 1**."
    )
    a("")
    a("---")
    a("")
    a("## 4. Refactor-Resilience Guarantees")
    a("")
    a("- **Zero Hardcoded Names or Counts:** Every top-level directory (`top_dir`) is discovered dynamically from `graph.sqlite`, sorted deterministically by `(-module_count, top_dir)`, and colored from a fixed high-contrast light-theme categorical palette (with a deterministic golden-angle HSL fallback beyond 10 directories).")
    a("- **Deterministic Tie-Breaking & Bit-Exact Output:** Node ordering ties break on `rel_path`, canonical IDs are sorted by `(layer, x, rel_path)`, and gzip compression uses `mtime=0`, ensuring repeated runs on unchanged sources emit byte-identical outputs.")
    a(
        f"- **Invariant Checks:** Across all 8 composable views, the generator verifies zero self-loops, exact topological completeness (`len(topo) == N`), strict downward edge monotonicity ($y(u) < y(v)$ and $\\text{{id}}(u) < \\text{{id}}(v)$), intra-layer non-overlap ($\\Delta x \\ge 1.0$), exact Hasse bitmask counts (`{fh['edge_count']:,}` for `full_hasse`, `{eh['edge_count']:,}` for `existing_hasse`), zero remaining unprotected simple leaves or `(1,1)` pass-through nodes after fixed-point simplification, and exact module conservation ($\\sum_{{v \\in V}} w(v) + \\sum_{{e \\in E}} \\text{{chain}}(e) = {n_mod:,}$) before writing output."
    )
    a("")
    a("---")
    a("")
    a("## 5. Simplification Modes, Weights & `LDAG` v3 Architecture")
    a("")
    a("The viewer provides three orthogonal, composable toggles that switch smoothly between **8 pre-verified graph views**:")
    a("")
    a(f"1. **Collapse existing theory (`C`):** Contracts established peer-reviewed mathematical proofs into **{col['supernode_count']} Literature Supernodes**.")
    a("2. **Hide redundant imports (`H`):** Applies exact transitive reduction (the Hasse diagram), hiding shortcut import edges that are already implied by longer dependency paths.")
    a("3. **Collapse chains & leaves (`L`):** Folds private simple-leaf subtrees upward into weighted parent anchor nodes (`Anchor [w]`) and contracts pass-through `(1,1)` chains onto weighted dependency edges.")
    a("")
    a("### 5.1 Existing-Theory Proof-Frontier Cut (\"Collapse existing theory\")")
    a("")
    a("The **\"Collapse existing theory\"** toggle in [full_dag.html](full_dag.html) (keyboard shortcut `C`) lets readers hide subtrees of the Lean codebase proving already-established peer-reviewed mathematics while preserving every novel theorem, shared interface specification, and statement contract.")
    a("")
    a("Following the identification methodology in [PUBLISHED_THEOREMS_INVENTORY.md](../published_theorems/PUBLISHED_THEOREMS_INVENTORY.md#methodology-identifying-collapsible-existing-theory-proof-subtrees), `build_full_dag.py`:")
    a("")
    a("1. Parses audited peer-reviewed `Prop` identifiers and bold canonical literature titles from Sections 1–11 of the active inventory (excluding Section 12 project-specific statements and internal scaffolding).")
    a("2. Enforces the SQLite defining-module ancestor guard and scans final conclusion heads of `theorem`/`lemma` declarations while excluding `*/Definitions/*`, assumed hypothesis-bundle projections/dispatchers (`OpenImageCondition`, `OpenLiteratureStatements`, etc.), novel headline modules, and multi-topic re-export barrels.")
    if col["dead_edges_pruned"] > 0:
        a(
            f"3. Performs reachability from `Main` without crossing outgoing edges of detected proof roots while pruning **{col['dead_edges_pruned']}** provably dead bridge imports whose targets lie strictly below the baseline published-theorem frontier."
        )
    else:
        a("3. Performs reachability from `Main` without crossing outgoing edges of detected proof roots so proof-only interiors are isolated without disconnecting active mathematical interfaces.")
    a("")
    a(
        f"Modules unreachable from `Main` past the proof-frontier cut form the **proof-only interior** $C$ (`{col['interior_module_count']:,}` modules), while reached proof-root modules form the **frontier** $F$ (`{col['frontier_module_count']:,}` modules). Grouping frontier roots into **{col['supernode_count']} Literature Supernodes** $S_T$ rendered as **diamond axiom sinks** ($\\text{{out\\_degree}} = 0$) and assigning every $v \\in C$ via deterministic multi-source BFS yields a complete disjoint partition:"
    )
    a("")
    a(f"$$|A| + \\sum_{{T}} |S_T| = {col['active_node_count']:,} + {col['collapsed_module_count']:,} = {n_mod:,}.$$")
    a("")
    ex_sup_str = f" (for example, `{top_sup['title']} [{top_sup['owned_modules']:,}]`)" if top_sup else ""
    a(
        f"Each supernode displays its canonical literature title and collapsed module count in brackets{ex_sup_str}. Contracting parallel frontier imports from an active module $u \\in A$ to $S_T$ induces edge multiplicity weights (**{col['super_edge_count']:,}** contracted supernode edges from **{col['raw_super_edge_count']:,}** raw frontier imports, with **{col['weighted_edges_ge_2']:,}** edges having $w \\ge 2$, up to $w_{{\\max}} = {col['max_edge_weight']}$)."
    )
    a("")
    a("### 5.2 Transitive Reduction (\"Hide redundant imports\" / Hasse Diagram)")
    a("")
    a("Lean modules frequently `import` both a downstream module $B$ and an ancestor $C$ that $B$ already imports (`A -> B -> C` alongside shortcut `A -> C`).")
    a("")
    a("The **\"Hide redundant imports\"** toggle (`H` hotkey) displays the DAG's **exact transitive reduction** (its Hasse diagram), keeping an edge $(u, v)$ if and only if no indirect directed path $u \\to \\dots \\to v$ of length $\\ge 2$ exists:")
    a("")
    a("- **Algorithm (`compute_transitive_reduction`):** Processes nodes in topological order using striped arbitrary-precision integer bitsets (stripe width $B = 16{,}384$) to compute 1-step reachability $R_1(u)$ and $\\ge 2$-step reachability $R_2(u) = \\bigvee_{(u, v) \\in E} R_1(v)$; edge $(u, v)$ is redundant iff $v \\in R_2(u)$.")
    a(f"- **Edge Reduction (Full DAG):** Removes **{fh['redundant_edge_count']:,}** redundant edges (`{fh_red_pct:.2f}%`), leaving **{fh['edge_count']:,}** covering edges (`full_hasse`).")
    a(f"- **Edge Reduction (Existing-Theory DAG):** Removes **{eh['redundant_edge_count']:,}** redundant edges (`{eh_red_pct:.2f}%`), leaving **{eh['edge_count']:,}** covering edges (`existing_hasse`).")
    a(f"- **In-Place Zero-Jump Filtering:** When *Collapse chains & leaves* is off, toggling `H` keeps node coordinates fixed and swaps CSR edges using compact 1-bit masks (`full_hasse_mask` = `{payload['full_hasse_mask_bytes']:,}` B; `existing_hasse_mask` = `{payload['existing_hasse_mask_bytes']:,}` B).")
    a("")
    a("### 5.3 Chain & Simple-Leaf Collapse (\"Collapse chains & leaves\")")
    a("")
    a(
        f"The **\"Collapse chains & leaves\"** toggle (`L` hotkey) runs `simplify_chains_and_leaves`, a deterministic 2-phase fixed-point contraction loop (on the base DAG removing **{fs_sm.get('leaves_removed', 0):,}** leaves and **{fs_sm.get('chains_removed', 0):,}** chain nodes; after transitive reduction removing **{fhs_sm.get('leaves_removed', 0):,}** leaves and **{fhs_sm.get('chains_removed', 0):,}** chain nodes):"
    )
    a("")
    a("1. **Phase 1 — Simple-Leaf Folding into Node Weight (`in = 1, out = 0`):** Iteratively peels every unprotected node $u$ with a single importer $p$ and zero internal dependencies upward into $p$, transferring node weight and any edge chain weight:")
    a("")
    a("$$w(p) \\leftarrow w(p) + w(u) + \\text{chain}(p, u).$$")
    a("")
    ex_anchor_txt = (
        f" (for instance, `{_stem_name(top_fhs_node['rel_path'])}` absorbs `{top_fhs_node['absorbed_leaves']}` leaves and `{top_fhs_node['absorbed_chains']}` chain modules to reach weight `{top_fhs_node['weight']}`)"
        if top_fhs_node
        else ""
    )
    a(f"Private leaf-trees collapse into weighted anchor nodes{ex_anchor_txt}. When *Collapse existing theory* is also active, all **{col['supernode_count']} Literature Supernodes** are protected from absorption so diamond landmarks remain visible.")
    a("2. **Phase 2 — Pass-Through `(1,1)` Chain Contraction into Edge Weight:** Iteratively contracts every unprotected `(1, 1)` node $u$ along $p \\to u \\to c$ into a direct edge $(p, c)$, merging parallel paths:")
    a("")
    a("$$\\text{mult}(p, c) \\mathrel{+}= \\max\\!\\big(\\text{mult}(p, u),\\, \\text{mult}(u, c)\\big), \\qquad \\text{chain}(p, c) \\mathrel{+}= \\text{chain}(p, u) + \\text{chain}(u, c) + w(u).$$")
    a("")
    a("The combined edge weight used for layout attraction and stroke rendering is $w_E(e) = \\text{mult}(e) + \\text{chain}(e)$.")
    a("3. **Fixed-Point Iteration & Module Conservation:** Phases 1 and 2 repeat until convergence (running *after* Hasse reduction when both `H` and `L` are active), preserving exact module conservation across every surviving view:")
    a("")
    a(f"$$\\sum_{{v \\in V}} w(v) + \\sum_{{e \\in E}} \\text{{chain}}(e) = {n_mod:,}.$$")
    a("")
    a("### 5.4 Node Labeling & Weight Encoding (Option A)")
    a("")
    a("- **Weighted Anchor Nodes (`Anchor [w]`):** Any active module with weight $w > 1$ renders with increased disc diameter ($w_{\\text{base}} + 0.55 \\ln(w)$) and an **inner white halo ring** (`alphaByte = 128`), labeled with its bold domain-colored `[w]` suffix.")
    a("- **Deep-Zoom Breakdown Subtitles (`zoom >= 55`):** Single-leaf absorption ($k = 1$) names the absorbed module directly; multi-module absorption summarizes `+k collapsed (L leaves, C chain)` alongside its directory path.")
    a("- **Weighted Edges & Badges:** Contracted edges scale in WebGL opacity, 2D stroke width ($\\log_2 w_E$), deep-zoom arrowheads, and collision-free `×m` / `+c` / `×m +c` badges at `zoom >= 6`.")
    a("")
    a("### 5.5 Compact Offline Payload (`LDAG` v3 in `full_dag_data.js`)")
    a("")
    a("Because browser `fetch()` fails under `file://` CORS restrictions, `build_full_dag.py` embeds the gzipped 4-byte-aligned little-endian `LDAG` binary container as `window.__FULL_DAG_GZ_B64__` in `full_dag_data.js` and decompresses it client-side via `DecompressionStream(\"gzip\")`:")
    a("")
    a(f"- **Container Sizes:** `{payload['raw_binary_bytes']:,}` raw bytes → `{payload['gzip_bytes']:,}` B gzipped (`mtime=0`) → `{payload['js_file_bytes']:,}` B JS payload (`format_version = {payload['format_version']}`).")
    a(f"- **Base & Collapsed Sections (`v1 + v2`):** Header JSON, full-graph typed arrays & delta-varint CSR `edge_buf` (`{payload['edge_varint_bytes']:,}` B), collapsed supernode metadata (`c_super_edges_buf` = `{payload['c_super_edges_bytes']:,}` B), and `{col['dead_edges_pruned']}` pruned dead-edge pairs.")
    a(f"- **Hasse Bitmasks & 4 Simplified Views (`v3`):** `full_hasse_mask` (`{payload['full_hasse_mask_bytes']:,}` B), `existing_hasse_mask` (`{payload['existing_hasse_mask_bytes']:,}` B), and 1-bit-flagged LEB128 CSR edge streams (`{payload['simplified_edge_varint_bytes']:,}` B across all 4 simplified views).")
    a("")
    a("---")
    a("")
    a("## 6. Viewer Legend and Visual Encoding")
    a("")
    a("The interactive viewer ([full_dag.html](full_dag.html)) displays a collapsible corner legend populated dynamically from `header.groups` (sorted by descending module count) and a **Max depth** BFS filter bar:")
    a("")
    a("| Top-Level Directory | Modules | Hex | Color |")
    a("| :--- | ---: | :--- | :--- |")
    for dom in summary["domains"]:
        cname = PALETTE_NAMES.get(dom["color"], "Golden-angle HSL")
        a(f"| `{dom['name']}` | {dom['modules']:,} | `{dom['color']}` | {cname} |")
    a("")
    a("- **Future Refactor Fallback:** Beyond 10 top-level directories, `group_color()` assigns deterministic golden-angle HSL colors.")
    a("- **Top-Right Toggle Bar & Controls:** **Collapse existing theory (`C`)**, **Hide redundant imports (`H`)**, **Collapse chains & leaves (`L`)**, plus the **Max depth** shortest-path BFS depth control (`[` / `]` hotkeys and `All` toggle) filtering nodes and edges by distance from `Main` without altering coordinates.")
    a("")
    a("---")
    a("")
    a("## 7. Current Graph & Layout Summary")
    a("")
    a("### 8-View Summary Matrix")
    a("")
    a("| View (`Existing`, `Hasse`, `Chains/Leaves`) | Nodes | Edges | Layers | Layer Spacing | Avg $\\Delta y$ | Avg $\\lvert\\Delta x\\rvert$ | Weighted Anchors ($w > 1$) | Weighted Edges ($w_E \\ge 2$) | Module Conservation |")
    a("| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    a(
        f"| **Full DAG** (`F, F, F`) | {n_mod:,} | {n_edges:,} | {n_layers} | {summary['layer_dy']:.4f} | {lm['final_avg_y_span']:.3f} | {lm['final_avg_x_span']:.3f} | — | — | `{n_mod:,} + 0 = {n_mod:,}` |"
    )
    a(
        f"| **Full + Hide redundant imports** (`F, T, F`) | {n_mod:,} | {fh['edge_count']:,} | {n_layers} | {summary['layer_dy']:.4f} | *(in-place)* | *(in-place)* | — | — | `{n_mod:,} + 0 = {n_mod:,}` |"
    )
    a(
        f"| **Existing Theory** (`T, F, F`) | {col['node_count']:,} | {col['edge_count']:,} | {col['num_layers']} | {col['layer_dy']:.4f} | {clm['final_avg_y_span']:.3f} | {clm['final_avg_x_span']:.3f} | {col['supernode_count']} supernodes | {col['weighted_edges_ge_2']:,} | `{n_mod:,} + 0 = {n_mod:,}` |"
    )
    a(
        f"| **Existing + Hide redundant imports** (`T, T, F`) | {col['node_count']:,} | {eh['edge_count']:,} | {col['num_layers']} | {col['layer_dy']:.4f} | *(in-place)* | *(in-place)* | {col['supernode_count']} supernodes | *(in-place)* | `{n_mod:,} + 0 = {n_mod:,}` |"
    )
    simp_labels = [
        ("full_simp", "**Full + Chains & Leaves** (`F, F, T`)", False),
        ("full_hasse_simp", "**Full + Hasse + Chains & Leaves** (`F, T, T`)", False),
        ("existing_simp", "**Existing + Chains & Leaves** (`T, F, T`)", True),
        ("existing_hasse_simp", "**Existing + Hasse + Chains & Leaves** (`T, T, T`)", True),
    ]
    for skey, slabel, has_super in simp_labels:
        sm = simp[skey]
        slm = sm["layout_metrics"]
        w_node_str = (
            f"{sm['weighted_node_count']:,} + {col['supernode_count']} super"
            if has_super
            else f"{sm['weighted_node_count']:,} (`max w={sm['max_node_weight']}`)"
        )
        cons_str = f"`{sm['total_node_weight']:,} + {sm['total_edge_chain_weight']:,} = {n_mod:,}`"
        a(
            f"| {slabel} | {sm['node_count']:,} | {sm['edge_count']:,} | {sm['num_layers']} | {sm['layer_dy']:.4f} | {slm['final_avg_y_span']:.3f} | {slm['final_avg_x_span']:.3f} | {w_node_str} | {sm['weighted_edge_count']:,} (`max={sm['max_edge_weight']}`) | {cons_str} |"
        )
    a("")
    if fhs_sm.get("top_weighted_nodes") or fhs_sm.get("top_weighted_edges"):
        a("### Top Weighted Anchor Nodes & Contracted Edges (`full_hasse_simp`)")
        a("")
        if fhs_sm.get("top_weighted_nodes"):
            a("| Top Weighted Anchor Node (`Anchor [w]`) | Weight $w$ | Breakdown (`leaves` / `chains`) | Representative Absorbed Leaf |")
            a("| :--- | ---: | :---: | :--- |")
            for wn in fhs_sm["top_weighted_nodes"][:5]:
                a(
                    f"| `{_short_mod_name(wn['rel_path'])}` | {wn['weight']} | {wn['absorbed_leaves']} / {wn['absorbed_chains']} | `{_stem_name(wn['rep_rel_path'])}` |"
                )
            a("")
        if fhs_sm.get("top_weighted_edges"):
            a("| Top Contracted Edge (`src → dst`) | Combined Weight $w_E$ | Multiplicity (`×mult`) | Contracted Chain (`+chain`) |")
            a("| :--- | ---: | ---: | ---: |")
            for we in fhs_sm["top_weighted_edges"][:5]:
                a(
                    f"| `{_stem_name(we['src'])} → {_stem_name(we['dst'])}` | {we['weight']} | ×{we['mult']} | +{we['chain']} |"
                )
            a("")

    a("### Full DAG Summary")
    a("")
    a("| Metric | Value |")
    a("| :--- | ---: |")
    a(f"| Total Lean Modules (Nodes) | {n_mod:,} |")
    a(f"| Total Internal Import Edges | {n_edges:,} |")
    a(f"| Declarations Indexed (Reachable) | {decl_total:,} |")
    a(f"| Acyclic DAG Verified (`is_dag`) | `{str(lm['is_dag']).lower()}` |")
    a(f"| Topological Layers | {n_layers} (`layer 0`..`{h_max}`) |")
    a(f"| Layer Width (min / median / p95 / max) | {lw['min']:,} / {lw['median']:,} / {lw['p95']:,} / {lw['max']:,} |")
    a(f"| Vertical Layer Spacing (`layer_dy`) | {summary['layer_dy']:.4f} |")
    a(f"| Mean Vertical Span ($\\Delta y$ before $\\to$ after) | {lm['init_avg_y_span']:.3f} $\\to$ {lm['final_avg_y_span']:.3f} |")
    a(f"| Mean Horizontal Span ($\\lvert\\Delta x\\rvert$ before $\\to$ after) | {lm['init_avg_x_span']:.3f} $\\to$ {lm['final_avg_x_span']:.3f} |")
    a(f"| Adjacent / Short-Span Edges ($\\Delta y = 1$ / $\\Delta y \\le 5$) | {lm['span_eq_1_edges']:,} / {lm['span_le_5_edges']:,} |")
    a(f"| World Aspect Ratio | {summary['aspect_ratio']:.2f} : 1 |")
    a(f"| `LDAG` v{payload['format_version']} Payload (`full_dag_data.js`) | {payload['js_file_bytes']:,} bytes (`{payload['gzip_bytes']:,}` B gzip / `{payload['raw_binary_bytes']:,}` B raw) |")
    a("")
    a("### Collapsed DAG Summary (\"Collapse Existing Theory\")")
    a("")
    a("| Metric | Value |")
    a("| :--- | ---: |")
    a(f"| Collapsed View Nodes (`active + supernodes`) | {col['node_count']:,} (`{col['active_node_count']:,}` active + `{col['supernode_count']}` literature supernodes) |")
    a(f"| Collapsed Modules Total (`frontier + interior`) | {col['collapsed_module_count']:,} (`{col['collapsed_pct']:.2f}%`: `{col['frontier_module_count']:,}` frontier + `{col['interior_module_count']:,}` interior) |")
    a(f"| Collapsed View Edges (`active + supernode`) | {col['edge_count']:,} (`{col['active_edge_count']:,}` active + `{col['super_edge_count']:,}` supernode edges) |")
    a(f"| Raw Frontier Imports Contracted / Max Weight | {col['raw_super_edge_count']:,} raw imports / $w_{{\\max}} = {col['max_edge_weight']}$ (`{col['weighted_edges_ge_2']:,}` edges with $w \\ge 2$) |")
    a(f"| Targeted Dead Bridge Imports Pruned | {col['dead_edges_pruned']:,} |")
    a(f"| Acyclic DAG Verified (`is_dag`) | `{str(clm['is_dag']).lower()}` |")
    a(f"| Topological Layers (`c_num_layers`) | {col['num_layers']} (`layer 0`..`{max(0, col['num_layers'] - 1)}`) |")
    a(f"| Collapsed Layer Width (min / median / p95 / max) | {clw['min']:,} / {clw['median']:,} / {clw['p95']:,} / {clw['max']:,} |")
    a(f"| Vertical Layer Spacing (`c_layer_dy`) | {col['layer_dy']:.4f} |")
    a(f"| Mean Vertical Span ($\\Delta y$ before $\\to$ after) | {clm['init_avg_y_span']:.3f} $\\to$ {clm['final_avg_y_span']:.3f} (`{clm['span_eq_1_edges']:,}` at $\\Delta y = 1$) |")
    a(f"| Mean Horizontal Span ($\\lvert\\Delta x\\rvert$ before $\\to$ after) | {clm['init_avg_x_span']:.3f} $\\to$ {clm['final_avg_x_span']:.3f} |")
    a(f"| Min Intra-Layer Gap / World Aspect Ratio | {col['min_intra_layer_gap'] or 1.0} / {col['aspect_ratio']:.2f} : 1 |")
    a("")
    a("### Discovered Top-Level Domains & Collapse Breakdown")
    a("")
    dom_col_map = {d["name"]: d for d in col.get("domain_breakdown", [])}
    a("| Top-Level Directory | Total Modules | Active | Collapsed | Collapsed % | Palette Color | Layer Range (min / med / max) | Mean $x$ |")
    a("| :--- | ---: | ---: | ---: | ---: | :---: | :---: | ---: |")
    for dom in summary["domains"]:
        cd = dom_col_map.get(dom["name"], {})
        a(
            f"| `{dom['name']}` | {dom['modules']:,} | {cd.get('active_modules', dom['modules']):,} | {cd.get('collapsed_modules', 0):,} | {cd.get('collapsed_pct', 0.0):.1f}% | `{dom['color']}` | {dom['min_layer']} / {dom['median_layer']} / {dom['max_layer']} | {dom['mean_x']:.2f} |"
        )
    a("")
    a(f"### Top {min(20, len(col.get('top_supernodes', [])))} Collapsed Literature Supernodes")
    a("")
    a("| Literature Supernode Title | Owned Collapsed Modules | Full Cone Modules | Frontier Roots | Contracted In-Edges | Raw Imports |")
    a("| :--- | ---: | ---: | ---: | ---: | ---: |")
    for ts in col.get("top_supernodes", [])[:20]:
        a(
            f"| {ts['title']} | {ts['owned_modules']:,} | {ts['cone_modules']:,} | {ts['frontier_modules']} | {ts['in_edges']:,} | {ts['raw_in_edges']:,} |"
        )
    a("")
    a("### Top 15 Most Imported Hub Modules")
    a("")
    a("| Top Imported Hub Module | In-Degree | Out-Degree | Layer |")
    a("|---|---:|---:|---:|")
    for hub in summary["top_in_degree_hubs"][:15]:
        a(f"| `{hub['rel_path']}` | {hub['in_degree']:,} | {hub['out_degree']:,} | {hub['layer']} |")
    a("")
    a("---")
    a("")
    a("## 8. Regenerating After a Lean Refactor")
    a("")
    a("```bash")
    a(f"# 1. Rebuild only this version's full DAG payload & sync portal reports")
    a(f"python3 analysis/build_all.py --version {vid_cmd} --steps index,inventory,full_dag")
    a("")
    a(f"# 2. Or re-run build_full_dag.py standalone and regenerate HTML reports")
    a(f"python3 analysis/full_dag/build_full_dag.py --db-path analysis/versions/{vid_cmd}/data/graph.sqlite --out-dir analysis/versions/{vid_cmd}/full_dag --version-label {vid_cmd}")
    a("node analysis/render_reports.js")
    a("")
    a("# 3. Open the local analysis portal or viewer")
    a("python3 -m http.server 8000 --directory analysis")
    a("```")
    a("")
    return "\n".join(lines)


def main() -> None:
    global SRC_DIR
    parser = argparse.ArgumentParser(
        description="Build deterministic Sugiyama layout and binary payload for the full Lean DAG."
    )
    parser.add_argument("--rebuild-index", action="store_true", help="Re-run analysis/build_index.py first")
    parser.add_argument("--src-dir", type=Path, default=SRC_DIR, help="Path to Lean src root")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to graph.sqlite")
    parser.add_argument("--meta-path", type=Path, default=None, help="Path to meta.json (defaults alongside db-path)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Output directory")
    parser.add_argument("--inventory-path", type=Path, default=DEFAULT_INVENTORY_PATH, help="Path to PUBLISHED_THEOREMS_INVENTORY.md")
    parser.add_argument("--version-label", type=str, default="")
    parser.add_argument("--rel-src-label", type=str, default="src/")
    parser.add_argument("--y-iters", type=int, default=25, help="Max L1 vertical rank-tightening sweeps")
    parser.add_argument("--x-sweeps", type=int, default=16, help="Horizontal barycenter + PAV sweeps")
    parser.add_argument("--render-md-only", action="store_true", help="Regenerate FULL_DAG.md from existing layout_summary.json, meta.json, and graph.sqlite")
    args = parser.parse_args()
    SRC_DIR = args.src_dir
    meta_path = args.meta_path or (args.db_path.parent / "meta.json")
    meta_json = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    if args.render_md_only:
        summary_path = args.out_dir / "layout_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        decl_stats = compute_decl_stats(args.db_path) if args.db_path.exists() else None
        md_path = args.out_dir / "FULL_DAG.md"
        md_path.write_text(
            render_full_dag_md(
                summary,
                meta_json,
                decl_stats=decl_stats,
                version_label=args.version_label,
                rel_src_label=args.rel_src_label,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {md_path} ({md_path.stat().st_size:,} bytes) via --render-md-only")
        return

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
    new_adj_in: list[list[int]] = [[] for _ in range(n_mod)]
    for old_u in range(n_mod):
        nu = old_to_new[old_u]
        targets = sorted(old_to_new[old_v] for old_v in adj_out[old_u])
        for nv in targets:
            if nu >= nv:
                raise RuntimeError(f"Canonical ID ordering invariant violated: {nu} -> {nv}")
            new_adj_in[nv].append(nu)
        new_adj_out[nu] = targets
    for nu in range(n_mod):
        new_adj_in[nu].sort()

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

    # Stage C: Transitive reduction (Hasse bitmasks) & 4 chain/leaf-simplified views
    t_v3 = time.time()
    full_tr_out, full_tr_in = compute_transitive_reduction(n_mod, new_adj_out, new_adj_in)
    full_tr_sets = [set(nbrs) for nbrs in full_tr_out]
    full_hasse_bits = [nv in full_tr_sets[nu] for nu in range(n_mod) for nv in new_adj_out[nu]]
    full_hasse_edge_count = sum(len(nbrs) for nbrs in full_tr_out)
    if len(full_hasse_bits) != n_edges or sum(1 for b in full_hasse_bits if b) != full_hasse_edge_count:
        raise RuntimeError("Full Hasse bitmask count mismatch")
    full_hasse_mask = pack_edge_bitmask(full_hasse_bits)

    # Canonical existing-theory adjacency in exact JS CSR emission order
    full_to_c = [-1] * n_mod
    for cu, fid in enumerate(c_node_full_id):
        if fid >= 0:
            full_to_c[fid] = cu
    dead_set = set(dead_edges_canonical)
    c_can_out: list[list[int]] = [[] for _ in range(n_c)]
    c_can_in: list[list[int]] = [[] for _ in range(n_c)]
    c_can_em: list[dict[int, int]] = [{} for _ in range(n_c)]
    c_can_edge_seq: list[list[int]] = [[] for _ in range(n_c)]
    for cu in range(n_c):
        fid = c_node_full_id[cu]
        if fid >= 0:
            for fv in new_adj_out[fid]:
                cv = full_to_c[fv]
                if cv >= 0 and (fid, fv) not in dead_set:
                    c_can_edge_seq[cu].append(cv)
                    c_can_em[cu][cv] = 1
            for cv, w in col_res["c_super_adj_out"][cu]:
                c_can_edge_seq[cu].append(cv)
                c_can_em[cu][cv] = w
        c_can_out[cu] = sorted(c_can_em[cu].keys())
        for cv in c_can_out[cu]:
            c_can_in[cv].append(cu)
    for cv in range(n_c):
        c_can_in[cv].sort()

    c_tr_out, c_tr_in = compute_transitive_reduction(n_c, c_can_out, c_can_in)
    c_tr_sets = [set(nbrs) for nbrs in c_tr_out]
    existing_edge_count = col_res["active_edge_cnt"] + col_res["super_edge_cnt"]
    existing_hasse_bits = [cv in c_tr_sets[cu] for cu in range(n_c) for cv in c_can_edge_seq[cu]]
    existing_hasse_edge_count = sum(len(nbrs) for nbrs in c_tr_out)
    if (
        len(existing_hasse_bits) != existing_edge_count
        or sum(1 for b in existing_hasse_bits if b) != existing_hasse_edge_count
    ):
        raise RuntimeError("Existing-theory Hasse bitmask count mismatch")
    existing_hasse_mask = pack_edge_bitmask(existing_hasse_bits)

    full_sort_keys = [rel_path[old_id] for old_id in order]
    full_node_ids = list(range(n_mod))
    full_init_nw = [1] * n_mod

    c_can_sort_keys = [col_res["c_sort_keys"][old_cid] for old_cid in col_res["c_order"]]
    c_can_nw = [1 if fid >= 0 else col_res["c_super_counts"][-(fid + 1)] for fid in c_node_full_id]
    c_protected = {cu for cu, fid in enumerate(c_node_full_id) if fid < 0}
    c_tr_em = [{cv: c_can_em[cu][cv] for cv in c_tr_out[cu]} for cu in range(n_c)]
    c_super_titles = col_res["c_super_titles"]

    simp_specs = [
        ("full_simp", n_mod, new_adj_out, new_adj_in, full_init_nw, None, set(), full_node_ids, full_sort_keys),
        ("full_hasse_simp", n_mod, full_tr_out, full_tr_in, full_init_nw, None, set(), full_node_ids, full_sort_keys),
        ("existing_simp", n_c, c_can_out, c_can_in, c_can_nw, c_can_em, c_protected, c_node_full_id, c_can_sort_keys),
        (
            "existing_hasse_simp",
            n_c,
            c_tr_out,
            c_tr_in,
            c_can_nw,
            c_tr_em,
            c_protected,
            c_node_full_id,
            c_can_sort_keys,
        ),
    ]

    simplified_views: dict[str, dict[str, Any]] = {}
    for skey, s_n, s_out, s_in, s_nw, s_em, s_prot, s_fids, s_keys in simp_specs:
        simp_raw = simplify_chains_and_leaves(s_n, s_out, s_in, s_nw, s_em, s_prot, s_fids)
        view_pack = build_simplified_view(
            simp_raw,
            s_keys,
            s_fids,
            rel_path,
            order,
            c_super_titles,
            args.y_iters,
            args.x_sweeps,
        )
        simplified_views[skey] = view_pack
        sm = view_pack["summary"]
        print(
            f"  [{skey}] {sm['node_count']:,} nodes, {sm['edge_count']:,} edges, {sm['num_layers']} layers "
            f"(−{sm['leaves_removed']:,} leaves, −{sm['chains_removed']:,} chains; "
            f"weighted nodes={sm['weighted_node_count']:,}, weighted edges={sm['weighted_edge_count']:,})"
        )
    print(f"Computed Hasse masks & 4 simplified views in {time.time() - t_v3:.2f}s")

    simp_header_meta: dict[str, Any] = {}
    for skey, _, _, _, _, _, _, _, _ in simp_specs:
        sm = simplified_views[skey]["summary"]
        simp_header_meta[skey] = {
            "node_count": sm["node_count"],
            "edge_count": sm["edge_count"],
            "num_layers": sm["num_layers"],
            "layer_dy": sm["layer_dy"],
            "bounds": sm["bounds"],
            "weighted_node_count": sm["weighted_node_count"],
            "weighted_edge_count": sm["weighted_edge_count"],
            "leaves_removed": sm["leaves_removed"],
            "chains_removed": sm["chains_removed"],
            "max_node_weight": sm["max_node_weight"],
            "max_edge_weight": sm["max_edge_weight"],
            "layout_metrics": sm["layout_metrics"],
        }

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
            "edge_count": existing_edge_count,
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
        "full_hasse": {
            "edge_count": full_hasse_edge_count,
            "redundant_edge_count": n_edges - full_hasse_edge_count,
            "bitmask_bytes": len(full_hasse_mask),
        },
        "existing_hasse": {
            "edge_count": existing_hasse_edge_count,
            "redundant_edge_count": existing_edge_count - existing_hasse_edge_count,
            "bitmask_bytes": len(existing_hasse_mask),
        },
        "simplified": simp_header_meta,
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

    # Assemble 4-byte-aligned little-endian LDAG v3 binary payload
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

    # v3 Hasse bitmasks
    raw_buf.extend(struct.pack("<I", len(full_hasse_mask)))
    raw_buf.extend(full_hasse_mask)
    pad4(raw_buf)

    raw_buf.extend(struct.pack("<I", len(existing_hasse_mask)))
    raw_buf.extend(existing_hasse_mask)
    pad4(raw_buf)

    # v3 Simplified view sections
    simp_edge_bytes_total = 0
    for skey, _, _, _, _, _, _, _, _ in simp_specs:
        vp = simplified_views[skey]
        sm = vp["summary"]
        s_n = sm["node_count"]
        s_layers = sm["num_layers"]
        recs = vp["weighted_node_records"]
        s_ebuf = vp["edge_buf"]
        simp_edge_bytes_total += len(s_ebuf)

        raw_buf.extend(struct.pack(f"<{s_layers + 1}I", *vp["layer_offsets"]))
        raw_buf.extend(struct.pack(f"<{s_n}f", *vp["node_x_f32"]))
        raw_buf.extend(struct.pack(f"<{s_n}i", *vp["node_full_id"]))
        raw_buf.extend(struct.pack("<I", len(recs)))
        for nid_w, w_val, a_l, a_c, r_fid in recs:
            raw_buf.extend(struct.pack("<IIHHi", nid_w, w_val, min(65535, a_l), min(65535, a_c), r_fid))
        raw_buf.extend(struct.pack("<I", len(s_ebuf)))
        raw_buf.extend(s_ebuf)
        pad4(raw_buf)

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
        "full_hasse": header_obj["full_hasse"],
        "existing_hasse": header_obj["existing_hasse"],
        "simplified": {
            skey: simplified_views[skey]["summary"]
            for skey, _, _, _, _, _, _, _, _ in simp_specs
        },
        "payload": {
            "format_version": FORMAT_VERSION,
            "raw_binary_bytes": len(raw_buf),
            "gzip_bytes": len(gz_bytes),
            "js_file_bytes": data_js_path.stat().st_size,
            "edge_varint_bytes": len(edge_buf),
            "c_super_edges_bytes": len(c_super_edges_buf),
            "full_hasse_mask_bytes": len(full_hasse_mask),
            "existing_hasse_mask_bytes": len(existing_hasse_mask),
            "simplified_edge_varint_bytes": simp_edge_bytes_total,
            "name_blob_bytes": len(name_blob),
            "dir_blob_bytes": len(dir_blob),
        },
        "elapsed_seconds": round(time.time() - t0, 2),
    }
    summary_path = args.out_dir / "layout_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    md_path = args.out_dir / "FULL_DAG.md"
    decl_stats = compute_decl_stats(args.db_path)
    md_path.write_text(
        render_full_dag_md(
            summary,
            meta_json,
            decl_stats=decl_stats,
            version_label=args.version_label,
            rel_src_label=args.rel_src_label,
        ),
        encoding="utf-8",
    )

    print(
        f"Wrote {data_js_path} ({data_js_path.stat().st_size:,} bytes; "
        f"gz={len(gz_bytes):,}, raw={len(raw_buf):,}), {summary_path}, and {md_path} in {time.time() - t0:.2f}s"
    )


if __name__ == "__main__":
    main()
