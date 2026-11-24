#!/usr/bin/env python3
"""Build structural Lean 4 histograms from lean/src and analysis/data/graph.sqlite."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import multiprocessing as mp
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "lean" / "src"
DB_PATH = ROOT / "analysis" / "data" / "graph.sqlite"
OUT_DIR = Path(__file__).resolve().parent
JSON_PATH = OUT_DIR / "histograms_data.json"
JS_PATH = OUT_DIR / "histograms_data.js"
INDEX_SCRIPT = ROOT / "analysis" / "build_index.py"

DECL_START_RE = re.compile(
    r"^(?:@\[[^\]]*\]\s*)*"
    r"(?:set_option\s+[^\n]*?\s+in\s+)?"
    r"(?:(?:public|meta)\s+)*"
    r"(?:(private|protected)\s+)?"
    r"(?:(?:noncomputable|partial|unsafe|scoped|local|public|meta)\s+)*"
    r"(theorem|lemma|def|structure|class|inductive|abbrev|axiom|opaque|instance)\b\s*([^\s:(\[{]*)"
)
DECL_KIND_RE = re.compile(
    r"\b(?:(?:public|meta)\s+)*(?:(private|protected)\s+)?(?:(?:noncomputable|partial|unsafe|scoped|local|public|meta)\s+)*"
    r"(theorem|lemma|def|structure|class|inductive|abbrev|axiom|opaque|instance)\b"
)
VAR_START_RE = re.compile(r"^variable\b")
ATTR_LINE_RE = re.compile(r"^@\[([^\]]+)\]\s*$")
ATTR_CMD_RE = re.compile(r"^attribute\s+\[([^\]]+)\]\s*(.*)$")
SET_OPTION_RE = re.compile(r"^set_option\s+([A-Za-z0-9_.]+)")
TC_BRACKET_RE = re.compile(
    r"(?:^|[\s({])\[(?:\s*[A-Za-z0-9_.']+\s*:\s*)?([A-Z][A-Za-z0-9_.']+)(?=[\s\]])"
)
EQUIV_RE = re.compile(r"≃ₗᵢ|≃\+\*|≃ₗ|≃L|≃ₐ|≃ₜ|≃ᵢ|≃ᵐ|≃o|≃\+|≃\*|≃|≅|↔")
TOP_STOP_RE = re.compile(
    r"^(?:@\[|end(?:\s|$)|namespace\s|public\s+(?:section|namespace|import|meta)|meta\s+import|import\s|module(?:\s|$)|section(?:\s|$)|attribute\s|open\s|set_option\s|variable\s|universe\s|omit\s|include\s)"
)
TOKEN_SPLIT_RE = re.compile(r"[\s;(<\[{]+")

CANONICAL_ATTR_TAGS = [
    "simp",
    "reducible",
    "reassoc",
    "ext",
    "instance_reducible",
    "simps",
    "to_additive",
    "fun_prop",
    "irreducible",
    "elab_as_elim",
    "nolint",
    "coe",
    "refl",
    "symm",
    "trans",
    "gcongr",
    "norm_cast",
    "aesop",
]

MODULAR_NOTATIONS = {"MOD", "ZMOD", "PMOD", "SMOD"}

BASELINE_TYPECLASSES = {
    "Field",
    "CommRing",
    "Ring",
    "Algebra",
    "AddCommGroup",
    "AddCommMonoid",
    "Module",
    "Group",
    "CommGroup",
    "Monoid",
    "Fintype",
    "Finite",
    "DecidableEq",
    "Fact",
    "TopologicalSpace",
    "NeZero",
    "CharZero",
    "Nontrivial",
    "Nonempty",
    "Inhabited",
    "LinearOrder",
}

TIER_META = [
    ("core_algebra", "Core Algebra"),
    ("number_local_fields", "Number & Local Fields"),
    ("comm_alg_geom", "Commutative & Algebraic Geometry"),
    ("analysis_topology_measure", "Analysis, Topology & Measure"),
    ("finiteness_logic", "Finiteness & Type-Level"),
    ("other", "Other Domain-Specific"),
]

PROOF_SHAPE_SPECS = [
    ("wrapper_forwarding", "Wrapper (first | exact …)"),
    ("oneliner_mech", "1-line mechanical (simp/rfl/rw/exact/…)"),
    ("oneliner_solver", "1-line solver (ring/omega/linarith/…)"),
    ("oneliner_other", "1-line other tactic"),
    ("term_mode", "Term-mode (no by)"),
    ("short_2_5", "Short tactic (2–5 lines)"),
    ("medium_6_20", "Medium tactic (6–20 lines)"),
    ("long_21_50", "Long tactic (21–50 lines)"),
    ("deep_51_plus", "Deep tactic (51+ lines)"),
]

ONELINER_MECH_TOKS = {
    "simp",
    "simpa",
    "simp_all",
    "dsimp",
    "rfl",
    "rw",
    "rwa",
    "exact",
    "ext",
    "funext",
    "unfold",
    "subst",
    "assumption",
    "trivial",
    "congr",
    "apply",
    "refine",
    "intro",
    "intros",
    "rintro",
}
ONELINER_SOLVER_TOKS = {
    "ring",
    "noncomm_ring",
    "omega",
    "linarith",
    "nlinarith",
    "positivity",
    "norm_num",
    "exact_mod_cast",
    "push_cast",
    "norm_cast",
    "field_simp",
    "abel",
    "group",
    "module",
    "linear_combination",
    "gcongr",
    "fun_prop",
    "continuity",
    "measurability",
    "decide",
    "tauto",
    "aesop",
    "fin_cases",
    "grind",
}

STRATEGY_SPECS = [
    ("have", "have (intermediate claim/object)", "conceptual", re.compile(r"\bhave\b")),
    ("obtain_rcases", "obtain / rcases / cases", "conceptual", re.compile(r"\b(?:obtain|rcases|cases)\b")),
    ("let_set", "let / set (local binding)", "conceptual", re.compile(r"\b(?:let|set)\b")),
    ("by_cases", "by_cases (case split)", "conceptual", re.compile(r"\bby_cases\b")),
    ("induction", "induction", "conceptual", re.compile(r"\binduction\b")),
    ("choose", "choose (choice extraction)", "conceptual", re.compile(r"\bchoose\b")),
    ("classical", "classical", "conceptual", re.compile(r"\bclassical\b")),
    ("calc", "calc (calculational chain)", "conceptual", re.compile(r"\bcalc\b")),
    ("by_contra", "by_contra / contrapose / exfalso", "conceptual", re.compile(r"\b(?:by_contra|contrapose|exfalso)\b")),
    ("suffices", "suffices", "conceptual", re.compile(r"\bsuffices\b")),
    ("filter_upwards", "filter_upwards", "conceptual", re.compile(r"\bfilter_upwards\b")),
    ("wlog", "wlog", "conceptual", re.compile(r"\bwlog\b")),
    ("simp_family", "simp / simpa / simp_all / dsimp", "solver", re.compile(r"\b(?:simp|simpa|simp_all|dsimp)\b")),
    ("omega", "omega", "solver", re.compile(r"\bomega\b")),
    ("ring", "ring / noncomm_ring", "solver", re.compile(r"\b(?:ring|noncomm_ring)\b")),
    ("linarith", "linarith / nlinarith", "solver", re.compile(r"\b(?:linarith|nlinarith)\b")),
    ("cast_tactics", "exact_mod_cast / push_cast / norm_cast", "solver", re.compile(r"\b(?:exact_mod_cast|push_cast|norm_cast)\b")),
    ("positivity", "positivity", "solver", re.compile(r"\bpositivity\b")),
    ("norm_num", "norm_num", "solver", re.compile(r"\bnorm_num\b")),
    ("linear_combination", "linear_combination", "solver", re.compile(r"\blinear_combination\b")),
    ("field_simp", "field_simp", "solver", re.compile(r"\bfield_simp\b")),
    ("abel_group_module", "abel / group / module", "solver", re.compile(r"\b(?:abel|group|module)\b")),
    ("gcongr", "gcongr", "solver", re.compile(r"\bgcongr\b")),
    ("fun_prop_cont_meas", "fun_prop / continuity / measurability", "solver", re.compile(r"\b(?:fun_prop|continuity|measurability)\b")),
    ("fin_cases_decide_tauto_aesop", "fin_cases / decide / tauto / aesop", "solver", re.compile(r"\b(?:fin_cases|decide|tauto|aesop)\b")),
    ("rw_rwa", "rw / rwa", "plumbing", re.compile(r"\b(?:rw|rwa)\b")),
    ("exact", "exact", "plumbing", re.compile(r"\bexact\b")),
    ("refine", "refine", "plumbing", re.compile(r"\brefine\b")),
    ("intro_family", "intro / intros / rintro", "plumbing", re.compile(r"\b(?:intro|intros|rintro)\b")),
    ("rfl", "rfl", "plumbing", re.compile(r"\brfl\b")),
    ("ext_funext", "ext / funext", "plumbing", re.compile(r"\b(?:ext|funext)\b")),
    ("apply", "apply", "plumbing", re.compile(r"\bapply\b")),
    ("trans", "trans", "plumbing", re.compile(r"\btrans\b")),
    ("congr", "congr", "plumbing", re.compile(r"\bcongr\b")),
    ("subst", "subst", "plumbing", re.compile(r"\bsubst\b")),
    ("change_convert", "change / convert", "plumbing", re.compile(r"\b(?:change|convert)\b")),
    ("constructor", "constructor", "plumbing", re.compile(r"\bconstructor\b")),
]

EQUIV_SPECS = [
    ("↔", "Logical iff (↔)"),
    ("≃", "Type equivalence (≃)"),
    ("≃ₗ", "Linear equiv (≃ₗ)"),
    ("≃+", "Additive equiv (≃+)"),
    ("≃+*", "Ring equiv (≃+*)"),
    ("≃ₐ", "Algebra equiv (≃ₐ)"),
    ("≅", "Categorical iso (≅)"),
    ("≃*", "Multiplicative equiv (≃*)"),
    ("≃ₜ", "Homeomorphism (≃ₜ)"),
    ("≃ₗᵢ", "Linear isometric equiv (≃ₗᵢ)"),
    ("≃L", "Continuous linear equiv (≃L)"),
    ("≃ᵐ", "Measurable equiv (≃ᵐ)"),
    ("≃ᵢ", "Isometry equiv (≃ᵢ)"),
    ("≃o", "Order iso (≃o)"),
]
EQUIV_LABEL_MAP = dict(EQUIV_SPECS)

QUINTILE_LABELS = ["Q1 (0–20%)", "Q2 (20–40%)", "Q3 (40–60%)", "Q4 (60–80%)", "Q5 (80–100%)"]
QUINTILE_GROUPS = ["public_theorem", "def_abbrev", "private_thm_lem", "public_lemma", "struct_class_ind"]

OPEN_BUCKETS = ["0", "1", "2", "3-4", "5-7", "8-10", "11+"]
FANIN_BUCKETS = ["0", "1", "2", "3-5", "6-10", "11-25", "26-100", "101-500", "500+"]
CROSS_FANIN_BUCKETS = ["0", "1", "2", "3-5", "6-10", "11-20", "21+"]
CROSS_OUT_SUB_BUCKETS = ["0 (leaf)", "1", "2", "3-5", "6-10", "11+"]
CROSS_OUT_DOM_BUCKETS = ["0 (leaf)", "1", "2", "3", "4", "5+"]
DECLS_PER_FILE_BUCKETS = ["0", "1", "2", "3-5", "6-10", "11-25", "26-50", "51+"]


def classify_typeclass(name: str) -> str:
    if name in {
        "Fintype",
        "Finite",
        "DecidableEq",
        "Fact",
        "Countable",
        "Nonempty",
        "Inhabited",
        "LinearOrder",
        "Subsingleton",
        "Encodable",
        "Decidable",
        "Preorder",
        "PartialOrder",
    }:
        return "finiteness_logic"
    if (
        name in {"NumberField", "IsCMField", "IsTotallyReal", "IsTotallyComplex", "IsAlgClosed", "IsAlgClosure", "IsFractionRing", "IsDedekindDomain", "ValuativeRel", "IsDiscreteValuationRing", "IsGalois", "IsCyclotomicExtension", "IsSeparable"}
        or "Nonarchimedean" in name
        or "LocalField" in name
        or "NumberField" in name
        or "CMField" in name
        or "Valuative" in name
        or "DiscreteValuation" in name
        or "Dedekind" in name
        or "TotallyReal" in name
        or "TotallyComplex" in name
        or "AlgClos" in name
        or "FractionRing" in name
    ):
        return "number_local_fields"
    if (
        name in {"TopologicalSpace", "NormedAddCommGroup", "NormedSpace", "InnerProductSpace", "MeasurableSpace", "BorelSpace", "CompleteSpace", "T2Space", "LocallyCompactSpace", "SecondCountableTopology", "CompactSpace", "IsUltrametricDist", "NormedField", "NontriviallyNormedField", "NormedAlgebra", "IsTopologicalGroup", "IsTopologicalAddGroup", "IsTopologicalRing", "SFinite", "DiscreteTopology", "ProperSpace", "SigmaFinite", "IsHaarMeasure", "ChartedSpace", "SmoothManifoldWithCorners"}
        or "Normed" in name
        or "InnerProduct" in name
        or "Measurable" in name
        or "Borel" in name
        or "Topolog" in name
        or "Compact" in name
        or "CompleteSpace" in name
        or "Ultrametric" in name
        or "ProperSpace" in name
    ):
        return "analysis_topology_measure"
    if (
        name in {"IsLocalRing", "IsNoetherianRing", "GrpObj", "IsCommMonObj", "IsIntegral", "IsAdicComplete", "IsIntegrallyClosed", "Smooth", "IsOpenImmersion", "IsClosedImmersion", "IsSeparated", "IsReduced", "QuasiCompact", "LocallyOfFiniteType", "IsLocallyNoetherian", "IsMonHom", "IsLocalHom", "Module.Projective", "HasFiniteLimits", "Abelian", "MonoidalCategory", "CartesianMonoidalCategory", "IsField", "IsRegular", "FormallySmooth", "FormallyUnramified", "Etale", "Flat"}
        or "LocalRing" in name
        or "Noetherian" in name
        or "GrpObj" in name
        or "MonObj" in name
        or "Immersion" in name
        or "AdicComplete" in name
        or "LocallyOfFinite" in name
        or "Scheme" in name
    ):
        return "comm_alg_geom"
    if (
        name in {"Field", "CommRing", "Ring", "Algebra", "Module", "Module.Finite", "Module.Free", "AddCommGroup", "AddCommMonoid", "Group", "CommGroup", "Monoid", "CommMonoid", "IsDomain", "CharZero", "CharP", "NeZero", "StarRing", "IsScalarTower", "FiniteDimensional", "Nontrivial", "Valued", "Semiring", "CommSemiring", "DivisionRing", "SMul", "MulAction"}
        or name.startswith("Module.")
    ):
        return "core_algebra"
    return "other"


def split_top_commas(text: str) -> list[str]:
    parts: list[str] = []
    cur: list[str] = []
    depth = 0
    for ch in text:
        if ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth = max(0, depth - 1)
            cur.append(ch)
        elif ch == "," and depth == 0:
            s = "".join(cur).strip()
            if s:
                parts.append(s)
            cur = []
        else:
            cur.append(ch)
    s = "".join(cur).strip()
    if s:
        parts.append(s)
    return parts


def parse_attr_tags(bracket_inner: str) -> list[str]:
    tags: list[str] = []
    for item in split_top_commas(bracket_inner):
        # Handle patterns like: reassoc (attr := simp) or to_additive (attr := simp)
        m_sub = re.search(r"\(\s*attr\s*:=\s*([^)]+)\)", item)
        if m_sub:
            tags.extend(parse_attr_tags(m_sub.group(1)))
            item = re.sub(r"\(\s*attr\s*:=\s*[^)]+\)", "", item).strip()
        # Strip leading visibility/scope modifiers
        while item.startswith(("local ", "scoped ")):
            item = item.split(None, 1)[1].strip() if " " in item else ""
        if not item:
            continue
        head = item.split()[0]
        if head.startswith("simps"):
            head = "simps"
        elif head.startswith("to_additive"):
            head = "to_additive"
        elif head.startswith("nolint"):
            head = "nolint"
        elif head.startswith("ext"):
            head = "ext"
        elif head.startswith("simp"):
            head = "simp"
        tags.append(head)
    return tags


def normalize_file_directive(bracket_inner: str) -> tuple[str, bool]:
    s = " ".join(bracket_inner.strip().split())
    if s.startswith("local instance"):
        return "local instance", True
    if s.startswith("instance "):
        return "instance", False
    if s.startswith("to_additive"):
        return "to_additive", False
    return s, False


def position_group(vis: str, kind: str) -> str:
    if kind == "theorem" and vis == "public":
        return "public_theorem"
    if kind in ("def", "abbrev"):
        return "def_abbrev"
    if kind in ("theorem", "lemma") and vis == "private":
        return "private_thm_lem"
    if kind == "lemma":
        return "public_lemma"
    return "struct_class_ind"


def empty_domain_acc() -> dict:
    return {
        "modules": 0,
        "declarations": 0,
        "theorems_lemmas": 0,
        "tactic_proofs": 0,
        "term_proofs": 0,
        "attr_tagged_decls": 0,
        "attr_occurrences": 0,
        "file_directives_total": 0,
        "doc_module_files": 0,
        "doc_decl_count": 0,
        "blueprint_tags": 0,
        "line_comments": 0,
        "block_comments": 0,
        "aux_named_decls": 0,
        "simp_modules": 0,
        "multi_decl_3plus_files": 0,
        "multi_decl_2plus_files": 0,
        "proof_shapes": Counter(),
        "decl_attrs": Counter(),
        "file_directives": Counter(),
        "local_instance_targets": Counter(),
        "set_options": Counter(),
        "typeclasses": Counter(),
        "strategy_proof_cnt": Counter(),
        "strategy_total_cnt": Counter(),
        "equiv_decl_cnt": Counter(),
        "equiv_total_cnt": Counter(),
        "open_buckets": Counter(),
        "open_roots": Counter(),
        "quintiles": [Counter() for _ in range(5)],
        "first_decl": Counter(),
        "last_decl": Counter(),
        "decl_vis_kind": Counter(),
        "decls_per_file": Counter(),
    }


def merge_acc(dst: dict, src: dict) -> None:
    for k in (
        "modules",
        "declarations",
        "theorems_lemmas",
        "tactic_proofs",
        "term_proofs",
        "attr_tagged_decls",
        "attr_occurrences",
        "file_directives_total",
        "doc_module_files",
        "doc_decl_count",
        "blueprint_tags",
        "line_comments",
        "block_comments",
        "aux_named_decls",
        "simp_modules",
        "multi_decl_3plus_files",
        "multi_decl_2plus_files",
    ):
        dst[k] += src[k]
    for k in (
        "proof_shapes",
        "decl_attrs",
        "file_directives",
        "local_instance_targets",
        "set_options",
        "typeclasses",
        "strategy_proof_cnt",
        "strategy_total_cnt",
        "equiv_decl_cnt",
        "equiv_total_cnt",
        "open_buckets",
        "open_roots",
        "first_decl",
        "last_decl",
        "decl_vis_kind",
        "decls_per_file",
    ):
        dst[k].update(src[k])
    for qi in range(5):
        dst["quintiles"][qi].update(src["quintiles"][qi])


def bucket_open(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 4:
        return "3-4"
    if n <= 7:
        return "5-7"
    if n <= 10:
        return "8-10"
    return "11+"


def bucket_decls_per_file(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    if n <= 25:
        return "11-25"
    if n <= 50:
        return "26-50"
    return "51+"


def bucket_fanin(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    if n <= 25:
        return "11-25"
    if n <= 100:
        return "26-100"
    if n <= 500:
        return "101-500"
    return "500+"


def bucket_cross_fanin(n: int) -> str:
    if n == 0:
        return "0"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    if n <= 20:
        return "11-20"
    return "21+"


def bucket_cross_out_sub(n: int) -> str:
    if n == 0:
        return "0 (leaf)"
    if n == 1:
        return "1"
    if n == 2:
        return "2"
    if n <= 5:
        return "3-5"
    if n <= 10:
        return "6-10"
    return "11+"


def bucket_cross_out_dom(n: int) -> str:
    if n == 0:
        return "0 (leaf)"
    if n <= 4:
        return str(n)
    return "5+"


def scan_chunk(task: tuple[list[tuple[int, str, str]], str]) -> tuple[dict[str, dict], list[int]]:
    """Scan a chunk of (mod_id, rel_path, top_dir) tuples."""
    chunk, src_str = task
    by_dom: dict[str, dict] = {}
    simp_mod_ids: list[int] = []

    for mod_id, rel_path, top_dir in chunk:
        acc = by_dom.get(top_dir)
        if acc is None:
            acc = empty_domain_acc()
            by_dom[top_dir] = acc

        full_path = os.path.join(src_str, rel_path)
        with open(full_path, encoding="utf-8", errors="replace") as f:
            txt = f.read()

        acc["modules"] += 1
        if "/-!" in txt:
            acc["doc_module_files"] += 1
        if "/--" in txt:
            acc["doc_decl_count"] += txt.count("/--")
        if "@[blueprint" in txt:
            acc["blueprint_tags"] += txt.count("@[blueprint")

        lines = txt.splitlines()
        n_lines = len(lines)
        has_simp_attr = False
        open_roots_set: set[str] = set()
        decls_in_file: list[str] = []
        pending_attrs: list[str] = []
        in_comment = 0
        i = 0

        while i < n_lines:
            ln = lines[i]
            stripped = ln.strip()

            # Simple block-comment tracking so comment prose doesn't pollute counts
            if in_comment > 0:
                if "/-" in stripped:
                    in_comment += stripped.count("/-")
                if "-/" in stripped:
                    in_comment = max(0, in_comment - stripped.count("-/"))
                i += 1
                continue

            if stripped.startswith("/-"):
                acc["block_comments"] += 1
                opens = stripped.count("/-")
                closes = stripped.count("-/")
                if opens > closes:
                    in_comment = opens - closes
                i += 1
                continue

            if stripped.startswith("--"):
                acc["line_comments"] += 1
                i += 1
                continue

            if not stripped:
                pending_attrs.clear()
                i += 1
                continue

            if stripped.startswith("open "):
                rest = stripped[5:].strip()
                if rest.startswith("scoped "):
                    rest = rest[7:].strip()
                for tok in rest.split():
                    if tok == "in" or tok.startswith("("):
                        break
                    open_roots_set.add(tok.split(".")[0])
                pending_attrs.clear()
                i += 1
                continue

            m_opt = SET_OPTION_RE.match(ln)
            if m_opt:
                acc["set_options"][m_opt.group(1)] += 1
                # Keep pending_attrs if `set_option ... in` sits between @[...] and theorem
                if not DECL_START_RE.match(ln):
                    if not stripped.endswith(" in"):
                        pending_attrs.clear()
                    i += 1
                    continue

            m_acmd = ATTR_CMD_RE.match(ln)
            if m_acmd:
                acc["file_directives_total"] += 1
                norm_dir, is_loc_inst = normalize_file_directive(m_acmd.group(1))
                acc["file_directives"][norm_dir] += 1
                if "simp" in m_acmd.group(1):
                    has_simp_attr = True
                if is_loc_inst:
                    tail = m_acmd.group(2).strip()
                    if tail.endswith(" in"):
                        tail = tail[:-3].strip()
                    for tgt in tail.split():
                        if tgt == "in":
                            break
                        acc["local_instance_targets"][tgt] += 1
                if not stripped.endswith(" in"):
                    pending_attrs.clear()
                i += 1
                continue

            m_attr_line = ATTR_LINE_RE.match(stripped)
            if m_attr_line:
                pending_attrs.extend(parse_attr_tags(m_attr_line.group(1)))
                i += 1
                continue

            if VAR_START_RE.match(ln):
                for m_tc in TC_BRACKET_RE.finditer(ln):
                    cname = m_tc.group(1)
                    if cname not in MODULAR_NOTATIONS:
                        acc["typeclasses"][cname] += 1
                pending_attrs.clear()
                i += 1
                continue

            if DECL_START_RE.match(ln):
                # Extract any inline @[...] before the declaration keywords
                inline_attrs: list[str] = []
                pos = 0
                s_ln = ln.lstrip()
                while s_ln[pos:].startswith("@["):
                    end_idx = s_ln.find("]", pos + 2)
                    if end_idx == -1:
                        break
                    inline_attrs.extend(parse_attr_tags(s_ln[pos + 2 : end_idx]))
                    pos = end_idx + 1
                    while pos < len(s_ln) and s_ln[pos].isspace():
                        pos += 1
                all_decl_attrs = pending_attrs + inline_attrs
                pending_attrs = []

                if all_decl_attrs:
                    acc["attr_tagged_decls"] += 1
                    for t in all_decl_attrs:
                        acc["decl_attrs"][t] += 1
                        acc["attr_occurrences"] += 1
                        if t == "simp":
                            has_simp_attr = True

                # Collect full signature before ':=' or trailing 'where'
                sig_parts: list[str] = []
                start_i = i
                has_by = False
                one_line_by: str | None = None
                while i < n_lines:
                    cur = lines[i]
                    if i > start_i and DECL_START_RE.match(cur):
                        break
                    if ":=" in cur:
                        before, after = cur.split(":=", 1)
                        sig_parts.append(before)
                        a = after.strip()
                        if a == "by":
                            has_by = True
                        elif a.startswith("by "):
                            has_by = True
                            one_line_by = a[3:].strip()
                        elif a == "by" or a.startswith("by\t"):
                            has_by = True
                        i += 1
                        break
                    if re.search(r"\bwhere\s*$", cur):
                        sig_parts.append(cur)
                        i += 1
                        break
                    sig_parts.append(cur)
                    i += 1

                sig = " ".join(sig_parts)
                m_dk = DECL_KIND_RE.search(sig)
                if not m_dk:
                    continue
                vis = (m_dk.group(1) or "public").strip()
                kind = m_dk.group(2)

                # Extract declaration name
                after_kind = sig[m_dk.end() :].lstrip()
                dname = after_kind.split()[0] if after_kind else ""
                dname = re.split(r"[:(\[{]", dname, maxsplit=1)[0]

                acc["declarations"] += 1
                acc["decl_vis_kind"][(vis, kind)] += 1
                decls_in_file.append(position_group(vis, kind))

                if dname and ("_aux" in dname.lower() or dname.endswith(("aux", "Aux"))):
                    acc["aux_named_decls"] += 1

                # Signature-only typeclasses
                for m_tc in TC_BRACKET_RE.finditer(sig):
                    cname = m_tc.group(1)
                    if cname not in MODULAR_NOTATIONS:
                        acc["typeclasses"][cname] += 1

                # Signature-only equivalence / bridge constructors
                eq_matches = EQUIV_RE.findall(sig)
                if eq_matches:
                    seen_eq: set[str] = set()
                    for sym in eq_matches:
                        acc["equiv_total_cnt"][sym] += 1
                        if sym not in seen_eq:
                            seen_eq.add(sym)
                            acc["equiv_decl_cnt"][sym] += 1

                # Proof body analysis for theorem & lemma
                if kind in ("theorem", "lemma"):
                    acc["theorems_lemmas"] += 1
                    body_lines: list[str] = []
                    if one_line_by is not None and one_line_by:
                        body_lines.append(one_line_by)
                    while i < n_lines:
                        cur = lines[i]
                        if cur and not cur[0].isspace() and (DECL_START_RE.match(cur) or TOP_STOP_RE.match(cur)):
                            break
                        cs = cur.strip()
                        if cs and not cs.startswith("--"):
                            body_lines.append(cs)
                        i += 1

                    if not has_by:
                        acc["term_proofs"] += 1
                        acc["proof_shapes"]["term_mode"] += 1
                    else:
                        acc["tactic_proofs"] += 1
                        n_body = len(body_lines)
                        first_ln = body_lines[0] if body_lines else ""
                        if first_ln.startswith("first |") or first_ln.startswith("first|"):
                            acc["proof_shapes"]["wrapper_forwarding"] += 1
                        elif n_body <= 1:
                            first_tok = TOKEN_SPLIT_RE.split(first_ln, maxsplit=1)[0] if first_ln else ""
                            if first_tok in ONELINER_MECH_TOKS:
                                acc["proof_shapes"]["oneliner_mech"] += 1
                            elif first_tok in ONELINER_SOLVER_TOKS:
                                acc["proof_shapes"]["oneliner_solver"] += 1
                            else:
                                acc["proof_shapes"]["oneliner_other"] += 1
                        elif n_body <= 5:
                            acc["proof_shapes"]["short_2_5"] += 1
                        elif n_body <= 20:
                            acc["proof_shapes"]["medium_6_20"] += 1
                        elif n_body <= 50:
                            acc["proof_shapes"]["long_21_50"] += 1
                        else:
                            acc["proof_shapes"]["deep_51_plus"] += 1

                        if body_lines:
                            body_text = "\n".join(body_lines)
                            for key, _, _, pat in STRATEGY_SPECS:
                                hits = pat.findall(body_text)
                                if hits:
                                    acc["strategy_proof_cnt"][key] += 1
                                    acc["strategy_total_cnt"][key] += len(hits)
                continue

            if stripped.startswith(("module", "import ", "public import", "meta import", "public section", "public meta", "namespace ", "section", "end ", "universe ")):
                pending_attrs.clear()
                if stripped in ("module", "public section") or stripped.startswith(("module ", "import ", "public import", "meta import", "public section ")):
                    i += 1
                    continue
            elif not stripped.endswith(" in"):
                pending_attrs.clear()
            i += 1

        if has_simp_attr:
            acc["simp_modules"] += 1
            simp_mod_ids.append(mod_id)

        acc["open_buckets"][bucket_open(len(open_roots_set))] += 1
        for r in open_roots_set:
            acc["open_roots"][r] += 1

        m_decls = len(decls_in_file)
        acc["decls_per_file"][bucket_decls_per_file(m_decls)] += 1
        if m_decls >= 2:
            acc["multi_decl_2plus_files"] += 1
            acc["first_decl"][decls_in_file[0]] += 1
            acc["last_decl"][decls_in_file[-1]] += 1
        if m_decls >= 3:
            acc["multi_decl_3plus_files"] += 1
            for idx_d, grp in enumerate(decls_in_file):
                q = min(4, (idx_d * 5) // m_decls)
                acc["quintiles"][q][grp] += 1

    return by_dom, simp_mod_ids


def serialize_domain(
    acc: dict,
    fanin_deg_non: Counter,
    fanin_deg_simp: Counter,
    cross_in_non: Counter,
    cross_in_simp: Counter,
    cross_out_sub: Counter,
    cross_out_dom: Counter,
    top_hubs: list[dict],
) -> dict:
    # Declaration attributes: nonzero sorted (-count, tag), plus canonical zero tags
    attr_items: list[dict] = []
    seen_tags: set[str] = set()
    for tag, cnt in sorted(acc["decl_attrs"].items(), key=lambda x: (-x[1], x[0])):
        attr_items.append({"tag": tag, "count": cnt})
        seen_tags.add(tag)
    for tag in CANONICAL_ATTR_TAGS:
        if tag not in seen_tags:
            attr_items.append({"tag": tag, "count": 0})

    # Typeclass tiers & top lists
    tier_totals = Counter()
    tc_rows: list[tuple[str, int, str]] = []
    for cname, cnt in sorted(acc["typeclasses"].items(), key=lambda x: (-x[1], x[0])):
        tier = classify_typeclass(cname)
        tier_totals[tier] += cnt
        tc_rows.append((cname, cnt, tier))

    top_all = [{"name": n, "count": c, "tier": t} for n, c, t in tc_rows[:25]]
    top_strong = [
        {"name": n, "count": c, "tier": t}
        for n, c, t in tc_rows
        if n not in BASELINE_TYPECLASSES
    ][:25]

    # Declaration kinds & visibility
    kind_totals: Counter[str] = Counter()
    by_kind: dict[str, dict[str, int]] = defaultdict(lambda: {"public": 0, "private": 0, "protected": 0})
    for (vis, kind), cnt in acc["decl_vis_kind"].items():
        kind_totals[kind] += cnt
        by_kind[kind][vis] += cnt
    kinds_list = [
        {
            "kind": k,
            "public": by_kind[k]["public"],
            "private": by_kind[k]["private"],
            "protected": by_kind[k]["protected"],
            "total": tot,
        }
        for k, tot in sorted(kind_totals.items(), key=lambda x: (-x[1], x[0]))
    ]

    # Equivalences
    all_eq_syms = set(acc["equiv_decl_cnt"].keys()) | {s for s, _ in EQUIV_SPECS}
    equiv_rows = [
        {
            "symbol": sym,
            "label": EQUIV_LABEL_MAP.get(sym, sym),
            "decl_count": acc["equiv_decl_cnt"][sym],
            "total_count": acc["equiv_total_cnt"][sym],
        }
        for sym in all_eq_syms
        if acc["equiv_decl_cnt"][sym] > 0 or sym in {"↔", "≃", "≃ₗ", "≃+", "≃+*", "≃ₐ", "≅", "≃*", "≃ₜ", "≃ₗᵢ", "≃L"}
    ]
    equiv_rows.sort(key=lambda r: (-r["decl_count"], r["symbol"]))

    return {
        "summary": {
            "modules": acc["modules"],
            "declarations": acc["declarations"],
            "theorems_lemmas": acc["theorems_lemmas"],
            "tactic_proofs": acc["tactic_proofs"],
            "term_proofs": acc["term_proofs"],
            "attr_tagged_decls": acc["attr_tagged_decls"],
            "attr_occurrences": acc["attr_occurrences"],
            "file_directives": acc["file_directives_total"],
            "doc_module_files": acc["doc_module_files"],
            "doc_decl_count": acc["doc_decl_count"],
            "blueprint_tags": acc["blueprint_tags"],
            "line_comments": acc["line_comments"],
            "block_comments": acc["block_comments"],
            "aux_named_decls": acc["aux_named_decls"],
            "simp_modules": acc["simp_modules"],
            "non_simp_modules": acc["modules"] - acc["simp_modules"],
        },
        "proof_shapes": [
            {"key": k, "label": lbl, "count": acc["proof_shapes"][k]}
            for k, lbl in PROOF_SHAPE_SPECS
        ],
        "decl_attrs": attr_items[:20],
        "file_directives": [
            {"directive": k, "count": v}
            for k, v in sorted(acc["file_directives"].items(), key=lambda x: (-x[1], x[0]))[:15]
        ],
        "local_instance_targets": [
            {"target": k, "count": v}
            for k, v in sorted(acc["local_instance_targets"].items(), key=lambda x: (-x[1], x[0]))[:15]
        ],
        "set_options": [
            {"option": k, "count": v}
            for k, v in sorted(acc["set_options"].items(), key=lambda x: (-x[1], x[0]))[:10]
        ],
        "typeclasses": {
            "top_all": top_all,
            "top_strong": top_strong,
            "tier_totals": [
                {"tier": tk, "label": tlbl, "count": tier_totals[tk]}
                for tk, tlbl in TIER_META
            ],
        },
        "proof_strategies": [
            {
                "key": key,
                "label": lbl,
                "group": grp,
                "proof_count": acc["strategy_proof_cnt"][key],
                "total_count": acc["strategy_total_cnt"][key],
            }
            for key, lbl, grp, _ in STRATEGY_SPECS
        ],
        "equivalences": equiv_rows,
        "cross_subtheory_imports": [
            {"bucket": b, "count": cross_out_sub[b]} for b in CROSS_OUT_SUB_BUCKETS
        ],
        "cross_domain_imports": [
            {"bucket": b, "count": cross_out_dom[b]} for b in CROSS_OUT_DOM_BUCKETS
        ],
        "open_namespaces": {
            "buckets": [{"bucket": b, "count": acc["open_buckets"][b]} for b in OPEN_BUCKETS],
            "top_roots": [
                {"namespace": k, "count": v}
                for k, v in sorted(acc["open_roots"].items(), key=lambda x: (-x[1], x[0]))[:15]
            ],
        },
        "fan_in": {
            "in_degree": [
                {
                    "bucket": b,
                    "non_simp": fanin_deg_non[b],
                    "simp": fanin_deg_simp[b],
                    "total": fanin_deg_non[b] + fanin_deg_simp[b],
                }
                for b in FANIN_BUCKETS
            ],
            "cross_subtheory": [
                {
                    "bucket": b,
                    "non_simp": cross_in_non[b],
                    "simp": cross_in_simp[b],
                    "total": cross_in_non[b] + cross_in_simp[b],
                }
                for b in CROSS_FANIN_BUCKETS
            ],
            "top_non_simp_hubs": top_hubs,
        },
        "file_order": {
            "multi_decl_3plus_files": acc["multi_decl_3plus_files"],
            "multi_decl_2plus_files": acc["multi_decl_2plus_files"],
            "groups": QUINTILE_GROUPS,
            "quintiles": [
                {
                    "label": QUINTILE_LABELS[qi],
                    "counts": {g: acc["quintiles"][qi][g] for g in QUINTILE_GROUPS},
                    "total": sum(acc["quintiles"][qi][g] for g in QUINTILE_GROUPS),
                }
                for qi in range(5)
            ],
            "first_decl": {
                "counts": {g: acc["first_decl"][g] for g in QUINTILE_GROUPS},
                "total": sum(acc["first_decl"][g] for g in QUINTILE_GROUPS),
            },
            "last_decl": {
                "counts": {g: acc["last_decl"][g] for g in QUINTILE_GROUPS},
                "total": sum(acc["last_decl"][g] for g in QUINTILE_GROUPS),
            },
        },
        "decl_taxonomy": {
            "kinds": kinds_list,
            "decls_per_file": [
                {"bucket": b, "count": acc["decls_per_file"][b]} for b in DECLS_PER_FILE_BUCKETS
            ],
        },
    }


def esc_cell(s: Any) -> str:
    """Escape pipe characters so Markdown table cells stay single-column."""
    return str(s).replace("|", "\\|")


def render_histograms_md(
    payload: dict,
    meta_json: dict | None = None,
    version_label: str = "",
    rel_src_label: str = "src/",
) -> str:
    """Render CODEBASE_HISTOGRAMS.md with full empirical findings & methodology."""
    m = payload["meta"]
    all_dom = payload["by_domain"]["ALL"]
    s = all_dom["summary"]
    fo = all_dom["file_order"]
    tc = all_dom["typeclasses"]
    fi = all_dom["fan_in"]
    tax = all_dom["decl_taxonomy"]

    tot_mod = max(1, s["modules"])
    tot_decl = max(1, s["declarations"])
    tot_tl = max(1, s["theorems_lemmas"])
    tot_tac = max(1, s["tactic_proofs"])

    shape_by_key = {r["key"]: r for r in all_dom["proof_shapes"]}
    attr_by_tag = {r["tag"]: r["count"] for r in all_dom["decl_attrs"]}
    dir_by_name = {r["directive"]: r["count"] for r in all_dom["file_directives"]}
    strat_by_key = {r["key"]: r for r in all_dom["proof_strategies"]}
    eq_by_sym = {r["symbol"]: r for r in all_dom["equivalences"]}
    kind_by_name = {r["kind"]: r for r in tax["kinds"]}
    dpf_by_bkt = {r["bucket"]: r["count"] for r in tax["decls_per_file"]}

    ver_note = f" (`{version_label}`)" if version_label else ""
    vid_cmd = version_label or "<version-id>"

    lines: list[str] = []
    a = lines.append
    a(f"# Codebase Structural Histograms & Lean 4 Comprehension Heuristics{ver_note}")
    a("")
    a(
        f"This report quantitatively tests standard Lean 4 comprehension heuristics against the empirical structure of the **{m['total_modules']:,}** reachable modules and **{m['total_declarations']:,}** declarations in `{rel_src_label}`:"
    )
    a("")
    a("- **Interactive Histogram Explorer:** [histograms.html](histograms.html) (offline SVG explorer with domain filtering across all discovered top-level directories)")
    a("- **Repeatable Generator:** [build_histograms.py](build_histograms.py)")
    a("- **Structured Dataset:** [histograms_data.json](histograms_data.json)")
    a("- **Module & Import Indexer:** [build_index.py](../build_index.py)")
    a("")
    a("---")
    a("")
    a("## 1. Standard Lean 4 Heuristics vs. Empirical Reality in This Codebase")
    a("")
    a("Standard advice for reading Mathlib-style Lean 4 codebases assumes heavy `@[simp]` tagging, `/-! ... -/` module docstrings, `/-- ... -/` docstrings, and `private lemma` / `_aux` conventions. Across this proof codebase, some heuristics hold strongly while others invert completely:")
    a("")

    m2 = max(1, fo["multi_decl_2plus_files"])
    m3 = max(1, fo["multi_decl_3plus_files"])
    first_pub_thm = fo["first_decl"]["counts"].get("public_theorem", 0)
    last_pub_thm = fo["last_decl"]["counts"].get("public_theorem", 0)

    if s["doc_module_files"] == 0 and s["doc_decl_count"] == 0 and s["line_comments"] == 0:
        doc_finding = (
            f"**0** files contain `/-!` module docstrings and **0** declarations have `/--` docstrings (`{s['blueprint_tags']}` `@[blueprint]` tags, `0` line comments). "
            f"However, across **{fo['multi_decl_2plus_files']:,}** multi-declaration files, the **final declaration** is a public `theorem` **{100.0 * last_pub_thm / m2:.2f}%** of the time (**{last_pub_thm:,}** files), vs. **{100.0 * first_pub_thm / m2:.2f}%** for the first declaration (**{first_pub_thm:,}** files)."
        )
        doc_impl = "Skip docstring search; bottom-of-file reading works strongly because definitions and helper lemmas sit earlier and public payoff theorems sit at the end."
    else:
        doc_finding = (
            f"**{s['doc_module_files']:,}** files contain `/-!` module docstrings and **{s['doc_decl_count']:,}** declarations carry `/--` docstrings (`{s['line_comments']:,}` line comments). "
            f"Across **{fo['multi_decl_2plus_files']:,}** multi-declaration files, the **final declaration** is a public `theorem` **{100.0 * last_pub_thm / m2:.2f}%** of the time (**{last_pub_thm:,}** files), vs. **{100.0 * first_pub_thm / m2:.2f}%** for the first declaration (**{first_pub_thm:,}** files)."
        )
        doc_impl = "Docstrings remain sparse outside focal files, while bottom-of-file reading holds strongly because definitions and helpers precede public payoff theorems."

    wrap_cnt = shape_by_key.get("wrapper_forwarding", {}).get("count", 0)
    mech_cnt = shape_by_key.get("oneliner_mech", {}).get("count", 0)
    solv_cnt = shape_by_key.get("oneliner_solver", {}).get("count", 0)
    oth1_cnt = shape_by_key.get("oneliner_other", {}).get("count", 0)
    one_line_tot = wrap_cnt + mech_cnt + solv_cnt + oth1_cnt
    glue_finding = (
        f"Only **{s['attr_tagged_decls']:,}** declarations (**{100.0 * s['attr_tagged_decls'] / tot_decl:.2f}%**) carry any `@[…]` tag (`{attr_by_tag.get('simp', 0):,}` `@[simp]`, `{attr_by_tag.get('ext', 0):,}` `@[ext]`, `{attr_by_tag.get('fun_prop', 0):,}` `@[fun_prop]`). "
        f"Instead, **{s['file_directives']:,}** file-scoped `attribute […]` directives manage local typeclasses (`{dir_by_name.get('local instance', 0):,}` `local instance`), and **{one_line_tot:,}** proofs (**{100.0 * one_line_tot / tot_tl:.2f}%** of theorems/lemmas) are 1-line tactics or `first \\| exact …` forwarding wrappers (**{wrap_cnt:,}**)."
    )
    glue_impl = f"Filtering out forwarding wrappers (`first \\| exact …`), 1-line mechanical tactics (`{mech_cnt:,}`), and `attribute [local instance]` boilerplate removes true glue better than scanning `@[…]` tags."

    tot_tc_occ = max(1, sum(t["count"] for t in tc["tier_totals"]))
    core_tc = tc["tier_totals"][0] if tc["tier_totals"] else {"label": "Core Algebra", "count": 0}
    top_base_str = ", ".join(f"`{t['name']}` `{t['count']:,}`" for t in tc["top_all"][:3])
    top_strong_str = ", ".join(f"`{t['name']}` (`{t['count']:,}`)" for t in tc["top_strong"][:7])
    tc_finding = (
        f"Out of **{tot_tc_occ:,}** signature binder occurrences, **{100.0 * core_tc['count'] / tot_tc_occ:.2f}%** are baseline `{core_tc['label']}` ({top_base_str}). "
        f"Filtering out baseline classes surfaces domain-specific hypotheses: {top_strong_str}."
    )
    tc_impl = "Excluding baseline algebraic/finiteness/topological classes isolates which mathematical theory layer a module operates in."

    iff_row = eq_by_sym.get("↔", {"decl_count": 0})
    bundled_decl_tot = sum(e["decl_count"] for e in all_dom["equivalences"] if e["symbol"] != "↔")
    eq_tot_decls = iff_row["decl_count"] + bundled_decl_tot
    top_bundled_str = ", ".join(
        [
            f"`{e['symbol']}` `{e['decl_count']:,}`"
            for e in all_dom["equivalences"]
            if e["symbol"] != "↔"
        ][:5]
    )
    multi_sub2 = sum(b["count"] for b in all_dom["cross_subtheory_imports"] if b["bucket"] not in ("0 (leaf)", "1"))
    eq_finding = (
        f"Signature-only longest-match scanning detects **{eq_tot_decls:,}** equivalence-bearing declarations (`{iff_row['decl_count']:,}` logical `↔` plus **{bundled_decl_tot:,}** bundled mathematical equivalences such as {top_bundled_str}). "
        f"Meanwhile, **{multi_sub2:,}** modules (**{100.0 * multi_sub2 / tot_mod:.2f}%**) import from 2+ distinct `depth-2` sub-theories."
    )
    eq_impl = "Bundled equivalence symbols (`≃ₗ`, `≃+*`, `≃ₐ`, `≅`, `≃ₜ`, `≃L`) and multi-subtheory import modules directly pinpoint abstraction boundaries."

    deg_bkt = {r["bucket"]: r for r in fi["in_degree"]}
    deg1_tot = deg_bkt.get("1", {}).get("total", 0)
    nonsimp_26p = sum(deg_bkt.get(k, {}).get("non_simp", 0) for k in ("26-100", "101-500", "500+"))
    nonsimp_500p = deg_bkt.get("500+", {}).get("non_simp", 0)
    top3_hubs = ", ".join(f"`{h['name'].rsplit('.', 1)[-1]}`" for h in fi["top_non_simp_hubs"][:3])
    fanin_finding = (
        f"Out of **{tot_mod:,}** modules, **{s['non_simp_modules']:,}** (**{100.0 * s['non_simp_modules'] / tot_mod:.2f}%**) have zero `@[simp]` declarations (`{s['simp_modules']:,}` contain `@[simp]`). "
        f"Exactly **{deg1_tot:,}** modules (**{100.0 * deg1_tot / tot_mod:.2f}%**) have `in_degree = 1`, while only **{nonsimp_26p:,}** non-`@[simp]` modules (**{100.0 * nonsimp_26p / tot_mod:.2f}%**) reach `in_degree >= 26` and **{nonsimp_500p}** reach `in_degree >= 500`."
    )
    fanin_impl = f"Module import fan-in cleanly separates single-consumer proof steps from shared specification hubs ({top3_hubs})."

    rw_r = strat_by_key.get("rw", {"proof_count": 0})
    ex_r = strat_by_key.get("exact", {"proof_count": 0})
    hv_r = strat_by_key.get("have", {"proof_count": 0})
    sp_r = strat_by_key.get("simp", {"proof_count": 0})
    ind_r = strat_by_key.get("induction", {"proof_count": 0})
    cls_r = strat_by_key.get("classical", {"proof_count": 0})
    chs_r = strat_by_key.get("choose", {"proof_count": 0})
    bc_r = strat_by_key.get("by_contra", {"proof_count": 0})
    moves_finding = (
        f"Across **{tot_tac:,}** tactic proofs, direct rewriting (`rw`/`rwa` in **{100.0 * rw_r['proof_count'] / tot_tac:.2f}%**, `exact` in **{100.0 * ex_r['proof_count'] / tot_tac:.2f}%**) and `have` (**{100.0 * hv_r['proof_count'] / tot_tac:.2f}%**) dominate, "
        f"while `simp`/`simpa`/`simp_all`/`dsimp` appears in **{100.0 * sp_r['proof_count'] / tot_tac:.2f}%**. Genuine structural moves are selective: "
        f"`induction` (**{100.0 * ind_r['proof_count'] / tot_tac:.2f}%**, `{ind_r['proof_count']:,}`), `classical` (**{100.0 * cls_r['proof_count'] / tot_tac:.2f}%**), `choose` (**{100.0 * chs_r['proof_count'] / tot_tac:.2f}%**), `by_contra`/`contrapose` (**{100.0 * bc_r['proof_count'] / tot_tac:.2f}%**)."
    )
    moves_impl = "Checking for `induction`, `by_contra`, `choose`, `classical`, `calc`, and multi-`obtain`/`have` blocks distinguishes conceptual steps from long `rw`/`ring` bookkeeping."

    thm_k = kind_by_name.get("theorem", {"total": 0, "private": 0})
    lem_k = kind_by_name.get("lemma", {"total": 0, "private": 0})
    q1_priv = fo["quintiles"][0]["counts"].get("private_thm_lem", 0) / max(1, fo["quintiles"][0]["total"])
    q5_priv = fo["quintiles"][4]["counts"].get("private_thm_lem", 0) / max(1, fo["quintiles"][4]["total"])
    last_priv = fo["last_decl"]["counts"].get("private_thm_lem", 0) / m2
    kind_finding = (
        f"`theorem` accounts for **{100.0 * thm_k['total'] / tot_decl:.2f}%** of declarations (`{thm_k['total']:,}`) vs. **{100.0 * lem_k['total'] / tot_decl:.2f}%** for `lemma` (`{lem_k['total']:,}`). "
        f"Only **{100.0 * thm_k['private'] / max(1, thm_k['total']):.2f}%** of `theorem`s are `private` (`{thm_k['private']:,}`), vs. **{100.0 * lem_k['private'] / max(1, lem_k['total']):.2f}%** of `lemma`s (`{lem_k['private']:,}`), and `{s['aux_named_decls']:,}` declarations have `aux`-suffixed names."
    )
    kind_impl = f"`private` visibility is a much sharper helper signal than `lemma` or `_aux` naming (`private` drops from `{100.0 * q1_priv:.2f}%` in Q1 and `{100.0 * q5_priv:.2f}%` in Q5 to `{100.0 * last_priv:.2f}%` on final declarations)."

    a("| Heuristic | Empirical Finding in `" + rel_src_label + "` | Practical Reading Implication |")
    a("|---|---|---|")
    a(f"| **Read module `/-!` docstrings and bottom-of-file declarations first** | {esc_cell(doc_finding)} | {esc_cell(doc_impl)} |")
    a(f"| **Filter out `@[simp]` / `@[ext]` / `@[norm_cast]` glue and 1-line proofs** | {esc_cell(glue_finding)} | {esc_cell(glue_impl)} |")
    a(f"| **Watch where stronger typeclasses enter** | {esc_cell(tc_finding)} | {esc_cell(tc_impl)} |")
    a(f"| **Look for cross-namespace equivalence bridges** | {esc_cell(eq_finding)} | {esc_cell(eq_impl)} |")
    a(f"| **Check non-`@[simp]` reference fan-in** | {esc_cell(fanin_finding)} | {esc_cell(fanin_impl)} |")
    a(f"| **Scan proof bodies for conceptual moves, not line count** | {esc_cell(moves_finding)} | {esc_cell(moves_impl)} |")
    a(f"| **Check `theorem` vs. `lemma` and `private` / `_aux`** | {esc_cell(kind_finding)} | {esc_cell(kind_impl)} |")
    a("")
    a("---")
    a("")
    a("## 2. Automation Attributes & Proof Glue")
    a("")
    a(
        f"Out of **{s['theorems_lemmas']:,}** `theorem` and `lemma` declarations (**{s['tactic_proofs']:,}** tactic proofs and **{s['term_proofs']:,}** term-mode proofs), mutually exclusive proof-shape classification breaks down as follows:"
    )
    a("")
    a("| Proof Shape Bucket | Count | Share of Theorems & Lemmas |")
    a("|---|---:|---:|")
    for ps in all_dom["proof_shapes"]:
        a(f"| {esc_cell(ps['label'])} | {ps['count']:,} | {100.0 * ps['count'] / tot_tl:.2f}% |")
    a("")
    a("### Declaration Attributes vs. File-Scoped `attribute […]` Directives")
    a("")
    a(
        f"Declaration-level `@[…]` attributes appear on **{s['attr_tagged_decls']:,}** declarations (**{100.0 * s['attr_tagged_decls'] / tot_decl:.2f}%** of `{s['declarations']:,}`, totaling **{s['attr_occurrences']:,}** tag occurrences), whereas file-scoped `attribute […]` directives appear **{s['file_directives']:,}** times—overwhelmingly activating local typeclass instances rather than rewriting rules:"
    )
    a("")
    a("| Top `@[…]` Declaration Tags | Count | Top File `attribute […]` Directives | Count |")
    a("|---|---:|---|---:|")
    attrs_top = all_dom["decl_attrs"][:8]
    dirs_top = all_dom["file_directives"][:8]
    for idx in range(max(len(attrs_top), len(dirs_top))):
        at_s = f"`@[{attrs_top[idx]['tag']}]` | {attrs_top[idx]['count']:,}" if idx < len(attrs_top) else " | "
        dr_s = f"`attribute [{dirs_top[idx]['directive']}]` | {dirs_top[idx]['count']:,}" if idx < len(dirs_top) else " | "
        a(f"| {at_s} | {dr_s} |")
    a("")
    loc_targets_str = ", ".join(f"`{t['target']}` (`{t['count']:,}`)" for t in all_dom["local_instance_targets"][:7])
    set_opts_str = ", ".join(f"`set_option {o['option']}` (`{o['count']:,}`)" for o in all_dom["set_options"][:4])
    a(f"The most frequent `attribute [local instance]` targets include {loc_targets_str}. Top compiler tuning options: {set_opts_str}.")
    a("")
    a("---")
    a("")
    a("## 3. Typeclass Usage & Mathematical Hypotheses")
    a("")
    tier_examples = {
        "core_algebra": "`Field`, `CommRing`, `Algebra`, `Module`, `AddCommGroup`, …",
        "number_local_fields": "`NumberField`, `IsCMField`, `ValuativeRel`, …",
        "finiteness_logic": "`Fintype`, `Fact`, `DecidableEq`, …",
        "analysis_topology_measure": "`TopologicalSpace`, `NormedAddCommGroup`, …",
        "comm_alg_geom": "`GrpObj`, `IsLocalRing`, `IsCommMonObj`, …",
        "other": "Project- and theory-specific predicates",
    }
    a(f"Restricting `[…]` extraction strictly to declaration signatures and `variable` headers yields **{tot_tc_occ:,}** typeclass binder occurrences across six mathematical tiers:")
    a("")
    a("| Mathematical Tier | Binder Occurrences | Share |")
    a("|---|---:|---:|")
    for tr in tc["tier_totals"]:
        ex = tier_examples.get(tr["tier"], "")
        lbl = f"{tr['label']} ({ex})" if ex else tr["label"]
        a(f"| {esc_cell(lbl)} | {tr['count']:,} | {100.0 * tr['count'] / tot_tc_occ:.2f}% |")
    a("")
    top_strong_12 = ", ".join(f"`{t['name']}` (`{t['count']:,}`)" for t in tc["top_strong"][:12])
    a(f"Filtering out the **{len(m['baseline_typeclasses'])}** baseline classes exposes the specialized mathematical hypotheses driving each top-level domain:")
    a("")
    a(f"- **Overall top stronger typeclasses:** {top_strong_12}.")
    dom_strat_parts: list[str] = []
    for dm in payload["domains"]:
        if dm["key"] in ("ALL", "(root)") or dm["modules"] < 200:
            continue
        if len(dom_strat_parts) >= 5:
            break
        d_strong = payload["by_domain"][dm["key"]]["typeclasses"]["top_strong"][:4]
        d_s_str = ", ".join(f"`{t['name']}` (`{t['count']:,}`)" for t in d_strong)
        dom_strat_parts.append(f"`{dm['key']}` (`{dm['modules']:,}` modules: {d_s_str})")
    if dom_strat_parts:
        a("- **Domain stratification:** " + "; ".join(dom_strat_parts) + ".")
    a("")
    a("---")
    a("")
    a("## 4. Proof Strategies: Conceptual Moves vs. Automated Solvers")
    a("")
    a(f"Scanning tactic bodies across all **{s['tactic_proofs']:,}** tactic-mode proofs separates ubiquitous rewriting mechanics from targeted automated solvers and conceptual proof moves:")
    a("")
    a("| Group | Tactic / Move | Tactic Proofs Using | Share of Tactic Proofs | Total Invocations |")
    a("|---|---|---:|---:|---:|")
    grp_order = [("plumbing", "Direct plumbing", 5), ("conceptual", "Conceptual", 10), ("solver", "Solver", 9)]
    for gkey, gname, glim in grp_order:
        rows_g = [r for r in all_dom["proof_strategies"] if r["group"] == gkey and r["total_count"] > 0]
        rows_g.sort(key=lambda r: (-r["proof_count"], -r["total_count"], r["key"]))
        for r in rows_g[:glim]:
            a(
                f"| {gname} | {esc_cell(r['label'])} | {r['proof_count']:,} | {100.0 * r['proof_count'] / tot_tac:.2f}% | {r['total_count']:,} |"
            )
    a("")
    a("---")
    a("")
    a("## 5. Cross-Namespace & Equivalence \"Bridge\" Signatures")
    a("")
    a(f"Longest-match tokenization over declaration signatures identifies **{eq_tot_decls:,}** declarations containing explicit equivalence/isomorphism constructors:")
    a("")
    a("| Constructor | Declarations | Total Occurrences |")
    a("|---|---:|---:|")
    for eq in all_dom["equivalences"]:
        if eq["decl_count"] <= 0:
            continue
        a(f"| {esc_cell(eq['label'])} | {eq['decl_count']:,} | {eq['total_count']:,} |")
    a("")
    multi_dom2 = sum(b["count"] for b in all_dom["cross_domain_imports"] if b["bucket"] not in ("0 (leaf)", "1"))
    open_bkt = {b["bucket"]: b["count"] for b in all_dom["open_namespaces"]["buckets"]}
    open5p = open_bkt.get("5-7", 0) + open_bkt.get("8-10", 0) + open_bkt.get("11+", 0)
    top_open_str = ", ".join(f"`{r['namespace']}` in `{r['count']:,}` files" for r in all_dom["open_namespaces"]["top_roots"][:4])
    a(
        f"Cross-module synthesis is also visible in import breadth and `open` headers: **{multi_sub2:,}** modules (**{100.0 * multi_sub2 / tot_mod:.2f}%**) import from 2+ distinct `depth-2` sub-theories, **{multi_dom2:,}** modules (**{100.0 * multi_dom2 / tot_mod:.2f}%**) import from 2+ distinct top-level domains, and **{open5p:,}** modules (**{100.0 * open5p / tot_mod:.2f}%**) open **5+** distinct root namespaces simultaneously (led by {top_open_str})."
    )
    a("")
    a("---")
    a("")
    a("## 6. Non-`@[simp]` Reference Fan-In & Reuse")
    a("")
    a("Joining file-level `@[simp]` detection with the SQLite import graph (`graph.sqlite`) shows a steep heavy-tailed reuse distribution:")
    a("")
    a("| Module `in_degree` | Non-`@[simp]` Modules | `@[simp]` Modules | Total Modules | Share |")
    a("|---|---:|---:|---:|---:|")
    for row in fi["in_degree"]:
        a(
            f"| `{row['bucket']}` | {row['non_simp']:,} | {row['simp']:,} | {row['total']:,} | {100.0 * row['total'] / tot_mod:.2f}% |"
        )
    a("")
    hub_str = ", ".join(
        f"`{h['name'].rsplit('.', 1)[-1]}` (`in_degree = {h['in_degree']:,}`)" for h in fi["top_non_simp_hubs"][:7]
    )
    a(f"The top non-`@[simp]` hub modules are foundational definition contracts and shared theory interfaces, led by {hub_str}.")
    a("")
    a("---")
    a("")
    a("## 7. Declaration Taxonomy & Top-to-Bottom File Order")
    a("")
    a(f"Across all **{s['declarations']:,}** declarations:")
    a("")
    a("| Kind | Public | Private | Protected | Total | Share |")
    a("|---|---:|---:|---:|---:|---:|")
    for kr in tax["kinds"]:
        a(
            f"| `{kr['kind']}` | {kr['public']:,} | {kr['private']:,} | {kr['protected']:,} | {kr['total']:,} | {100.0 * kr['total'] / tot_decl:.2f}% |"
        )
    a("")
    q1, q5 = fo["quintiles"][0], fo["quintiles"][4]
    q1_tot, q5_tot = max(1, q1["total"]), max(1, q5["total"])
    q1_def = q1["counts"].get("def_abbrev", 0)
    q5_def = q5["counts"].get("def_abbrev", 0)
    last_def = fo["last_decl"]["counts"].get("def_abbrev", 0)
    q1_pub_thm = q1["counts"].get("public_theorem", 0)
    q5_pub_thm = q5["counts"].get("public_theorem", 0)
    last_priv_cnt = fo["last_decl"]["counts"].get("private_thm_lem", 0)
    d1 = dpf_by_bkt.get("1", 0)
    d2 = dpf_by_bkt.get("2", 0)
    d35 = dpf_by_bkt.get("3-5", 0)
    d6p = dpf_by_bkt.get("6-10", 0) + dpf_by_bkt.get("11-25", 0) + dpf_by_bkt.get("26-50", 0) + dpf_by_bkt.get("51+", 0)
    a(f"Within the **{fo['multi_decl_3plus_files']:,}** files containing 3+ declarations (`Q1`–`Q5`) and the **{fo['multi_decl_2plus_files']:,}** files containing 2+ declarations (`First Decl` vs. `Last Decl`), top-down build order is strongly polarized:")
    a("")
    a(f"- **Definitions front-loaded:** `def` / `abbrev` makes up **{100.0 * q1_def / q1_tot:.2f}%** of `Q1` (`{q1_def:,}`) vs. **{100.0 * q5_def / q5_tot:.2f}%** in `Q5` (`{q5_def:,}`), dropping to **{100.0 * last_def / m2:.2f}%** on the final declaration.")
    a(f"- **Public theorems back-loaded:** Public `theorem` rises from **{100.0 * q1_pub_thm / q1_tot:.2f}%** in `Q1` (`{q1_pub_thm:,}`) to **{100.0 * q5_pub_thm / q5_tot:.2f}%** in `Q5` (`{q5_pub_thm:,}`), reaching **{100.0 * last_pub_thm / m2:.2f}%** (`{last_pub_thm:,}`) on the final declaration.")
    a(f"- **Private helpers excluded from payoff slot:** `private theorem`/`private lemma` comprises **{100.0 * q1_priv:.2f}%** in `Q1`, falls to **{100.0 * q5_priv:.2f}%** in `Q5`, and drops to **{100.0 * last_priv_cnt / m2:.2f}%** (`{last_priv_cnt:,}` files) on the final declaration.")
    a(f"- **File granularity:** **{d1:,}** modules (**{100.0 * d1 / tot_mod:.2f}%**) hold 1 declaration, **{d2:,}** (**{100.0 * d2 / tot_mod:.2f}%**) hold 2, **{d35:,}** (**{100.0 * d35 / tot_mod:.2f}%**) hold 3–5, and **{d6p:,}** (**{100.0 * d6p / tot_mod:.2f}%**) hold 6+.")
    a("")
    a("### Domain Breakdown")
    a("")
    a("| Domain | Modules | Declarations |")
    a("|---|---:|---:|")
    for dm in payload["domains"]:
        if dm["key"] == "ALL":
            continue
        a(f"| `{dm['key']}` | {dm['modules']:,} | {dm['declarations']:,} |")
    a("")
    a("---")
    a("")
    a("## 8. Repeatable Extraction Methodology & Caveats")
    a("")
    a("1. **Deterministic Pipeline (`build_histograms.py`):** Loads the sorted reachable module and edge tables from `graph.sqlite`, discovers all top-level domains dynamically sorted by `(-module_count, top_dir)`, and scans all `.lean` files in deterministic sorted chunks using multiprocessing.")
    a("2. **Signature-Only vs. Proof-Body Separation:** Typeclasses (`[…]`) and equivalence constructors (`≃ₗᵢ|≃+*|≃ₗ|…|↔`) are extracted strictly from declaration headers (before `:=` or trailing `where`) and `variable` lines so tactic arguments such as `rw [Finset.sum_comm]` never contaminate typeclass counts, and longest-match alternation prevents `≃+*` or `≃ₗᵢ` from double-counting as `≃`.")
    if meta_json:
        meta_decls = sum(meta_json.get("reachable_decl_counts", meta_json.get("decl_counts", {})).values())
        diff_pct = (100.0 * (s["declarations"] - meta_decls) / max(1, meta_decls))
        caveat_diff = f" (totaling `{s['declarations']:,}` declarations vs. `{meta_decls:,}` in `meta.json`—a `{diff_pct:+.2f}%` difference attributable to anonymous `instance` declarations and `set_option ... in` headers)"
    else:
        caveat_diff = f" (totaling `{s['declarations']:,}` syntactic declarations)"
    a(f"3. **Syntactic Scope Caveat:** Because the scanner parses Lean source text rather than elaborated `.olean` environments, implicit typeclass synthesis, tactic-generated sub-calls inside `simp`/`aesop`, and macro expansions are not unrolled. All counts are exact syntactic counts over `{rel_src_label}`{caveat_diff}.")
    a("4. **Regeneration:** To rebuild after a codebase change:")
    a("")
    a("```bash")
    a(f"python3 analysis/build_all.py --version {vid_cmd} --steps index,histograms")
    a("# Or standalone:")
    a(f"python3 analysis/codebase_histograms/build_histograms.py --db-path analysis/versions/{vid_cmd}/data/graph.sqlite --out-dir analysis/versions/{vid_cmd}/codebase_histograms --version-label {vid_cmd}")
    a("node analysis/render_reports.js")
    a("```")
    a("")
    return "\n".join(lines)


def main() -> None:
    global SRC_DIR, DB_PATH, OUT_DIR, JSON_PATH, JS_PATH
    parser = argparse.ArgumentParser(description="Build Lean 4 structural histograms.")
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="Re-run analysis/build_index.py before extracting histograms.",
    )
    parser.add_argument("--src-dir", type=Path, default=SRC_DIR)
    parser.add_argument("--db-path", type=Path, default=DB_PATH)
    parser.add_argument("--meta-path", type=Path, default=None)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--version-label", type=str, default="")
    parser.add_argument("--rel-src-label", type=str, default="src/")
    parser.add_argument("--render-md-only", action="store_true", help="Regenerate CODEBASE_HISTOGRAMS.md from existing histograms_data.json and meta.json.")
    parser.add_argument(
        "--workers",
        type=int,
        default=min(16, os.cpu_count() or 4),
        help="Number of worker processes.",
    )
    args = parser.parse_args()
    SRC_DIR = args.src_dir.resolve()
    DB_PATH = args.db_path.resolve()
    OUT_DIR = args.out_dir.resolve()
    JSON_PATH = OUT_DIR / "histograms_data.json"
    JS_PATH = OUT_DIR / "histograms_data.js"
    meta_path = (args.meta_path or (DB_PATH.parent / "meta.json")).resolve()
    meta_json = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else None

    if args.render_md_only:
        payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        md_path = OUT_DIR / "CODEBASE_HISTOGRAMS.md"
        md_path.write_text(
            render_histograms_md(
                payload,
                meta_json=meta_json,
                version_label=args.version_label,
                rel_src_label=args.rel_src_label,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {md_path} ({md_path.stat().st_size:,} bytes) via --render-md-only")
        return

    t0 = time.time()
    if args.rebuild_index or not DB_PATH.exists():
        print("Running analysis/build_index.py...")
        subprocess.run([sys.executable, str(INDEX_SCRIPT)], check=True)

    # Load reachable modules & edges from SQLite
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    mod_rows = conn.execute(
        """
        SELECT id, name, rel_path, top_dir, depth2_dir, in_degree_main, out_degree,
               n_theorems, n_lemmas, n_defs, n_structures, n_other_decls
        FROM modules
        WHERE reachable_from_main = 1
        ORDER BY rel_path, id
        """
    ).fetchall()

    mod_by_id: dict[int, tuple] = {}
    mod_items: list[tuple[int, str, str]] = []
    dom_counts: Counter[str] = Counter()
    for row in mod_rows:
        mod_id, name, rel_path, top_dir, depth2_dir, in_deg, out_deg, n_thm, n_lem, n_def, n_str, n_oth = row
        mod_by_id[mod_id] = row
        mod_items.append((mod_id, rel_path, top_dir))
        dom_counts[top_dir] += 1

    # Compute cross-subtheory / cross-domain edge sets
    in_subtheories: dict[int, set[str]] = defaultdict(set)
    out_subtheories: dict[int, set[str]] = defaultdict(set)
    out_domains: dict[int, set[str]] = defaultdict(set)
    for src_id, dst_id in conn.execute("SELECT src_id, dst_id FROM edges"):
        src_row = mod_by_id.get(src_id)
        dst_row = mod_by_id.get(dst_id)
        if src_row is None or dst_row is None:
            continue
        in_subtheories[dst_id].add(src_row[4])
        out_subtheories[src_id].add(dst_row[4])
        out_domains[src_id].add(dst_row[3])
    conn.close()

    print(f"Loaded {len(mod_items)} reachable modules from SQLite in {time.time() - t0:.2f}s")

    # Discover domains dynamically sorted by (-module_count, top_dir)
    ordered_domains = [d for d, _ in sorted(dom_counts.items(), key=lambda x: (-x[1], x[0]))]

    # Scan Lean source files in parallel
    t1 = time.time()
    chunk_size = 1000
    src_str = str(SRC_DIR)
    chunks = [(mod_items[i : i + chunk_size], src_str) for i in range(0, len(mod_items), chunk_size)]
    acc_by_dom: dict[str, dict] = {d: empty_domain_acc() for d in ordered_domains}
    all_acc = empty_domain_acc()
    simp_mod_ids: set[int] = set()

    workers = max(1, args.workers)
    if workers == 1:
        results = [scan_chunk(c) for c in chunks]
    else:
        with mp.Pool(processes=workers) as pool:
            results = pool.map(scan_chunk, chunks)

    for dom_map, chunk_simp_ids in results:
        simp_mod_ids.update(chunk_simp_ids)
        for d, d_acc in dom_map.items():
            merge_acc(acc_by_dom[d], d_acc)
            merge_acc(all_acc, d_acc)

    print(f"Scanned {all_acc['modules']} files in {time.time() - t1:.2f}s")

    # Join graph metrics (fan-in, cross-subtheory breadth, top hubs)
    fanin_non: dict[str, Counter] = defaultdict(Counter)
    fanin_simp: dict[str, Counter] = defaultdict(Counter)
    cross_in_non: dict[str, Counter] = defaultdict(Counter)
    cross_in_simp: dict[str, Counter] = defaultdict(Counter)
    cross_out_sub: dict[str, Counter] = defaultdict(Counter)
    cross_out_dom: dict[str, Counter] = defaultdict(Counter)
    hub_candidates: dict[str, list[dict]] = defaultdict(list)

    for row in mod_rows:
        mod_id, name, _, top_dir, depth2_dir, in_deg, _, n_thm, n_lem, n_def, n_str, _ = row
        is_simp = mod_id in simp_mod_ids
        b_in = bucket_fanin(in_deg)
        c_in_sub = len(in_subtheories.get(mod_id, ()))
        b_cin = bucket_cross_fanin(c_in_sub)
        b_osub = bucket_cross_out_sub(len(out_subtheories.get(mod_id, ())))
        b_odom = bucket_cross_out_dom(len(out_domains.get(mod_id, ())))

        for key in ("ALL", top_dir):
            if is_simp:
                fanin_simp[key][b_in] += 1
                cross_in_simp[key][b_cin] += 1
            else:
                fanin_non[key][b_in] += 1
                cross_in_non[key][b_cin] += 1
            cross_out_sub[key][b_osub] += 1
            cross_out_dom[key][b_odom] += 1

        if not is_simp:
            hub_rec = {
                "name": name,
                "top_dir": top_dir,
                "depth2_dir": depth2_dir,
                "in_degree": in_deg,
                "cross_subtheory_importers": c_in_sub,
                "n_theorems_lemmas": n_thm + n_lem,
                "n_defs_structs": n_def + n_str,
            }
            hub_candidates["ALL"].append(hub_rec)
            hub_candidates[top_dir].append(hub_rec)

    for key in hub_candidates:
        hub_candidates[key].sort(key=lambda r: (-r["in_degree"], r["name"]))
        hub_candidates[key] = hub_candidates[key][:15]

    by_domain_out: dict[str, dict] = {
        "ALL": serialize_domain(
            all_acc,
            fanin_non["ALL"],
            fanin_simp["ALL"],
            cross_in_non["ALL"],
            cross_in_simp["ALL"],
            cross_out_sub["ALL"],
            cross_out_dom["ALL"],
            hub_candidates["ALL"],
        )
    }
    for d in ordered_domains:
        by_domain_out[d] = serialize_domain(
            acc_by_dom[d],
            fanin_non[d],
            fanin_simp[d],
            cross_in_non[d],
            cross_in_simp[d],
            cross_out_sub[d],
            cross_out_dom[d],
            hub_candidates[d],
        )

    domains_meta = [
        {
            "key": "ALL",
            "label": "All domains",
            "modules": all_acc["modules"],
            "declarations": all_acc["declarations"],
        }
    ] + [
        {
            "key": d,
            "label": d,
            "modules": acc_by_dom[d]["modules"],
            "declarations": acc_by_dom[d]["declarations"],
        }
        for d in ordered_domains
    ]

    payload = {
        "meta": {
            "total_modules": all_acc["modules"],
            "total_declarations": all_acc["declarations"],
            "total_theorems_lemmas": all_acc["theorems_lemmas"],
            "tier_meta": [{"key": k, "label": l} for k, l in TIER_META],
            "baseline_typeclasses": sorted(BASELINE_TYPECLASSES),
            "quintile_groups": [
                {"key": "public_theorem", "label": "Public theorem"},
                {"key": "def_abbrev", "label": "def / abbrev"},
                {"key": "private_thm_lem", "label": "Private thm/lem"},
                {"key": "public_lemma", "label": "Public lemma"},
                {"key": "struct_class_ind", "label": "Struct / class / inst"},
            ],
            "strategy_groups": [
                {"key": "conceptual", "label": "Conceptual moves"},
                {"key": "solver", "label": "Automated solvers"},
                {"key": "plumbing", "label": "Direct rewriting / plumbing"},
            ],
            "elapsed_seconds": round(time.time() - t0, 2),
        },
        "domains": domains_meta,
        "by_domain": by_domain_out,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    JS_PATH.write_text(
        "window.__HISTOGRAMS_DATA__ = " + json.dumps(payload, separators=(",", ":"), ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    MD_PATH = OUT_DIR / "CODEBASE_HISTOGRAMS.md"
    MD_PATH.write_text(
        render_histograms_md(payload, meta_json=meta_json, version_label=args.version_label, rel_src_label=args.rel_src_label),
        encoding="utf-8",
    )

    # Validation summary
    all_out = by_domain_out["ALL"]
    shape_sum = sum(r["count"] for r in all_out["proof_shapes"])
    fanin_sum = sum(r["total"] for r in all_out["fan_in"]["in_degree"])
    dpf_sum = sum(r["count"] for r in all_out["decl_taxonomy"]["decls_per_file"])
    assert shape_sum == all_out["summary"]["theorems_lemmas"], (shape_sum, all_out["summary"]["theorems_lemmas"])
    assert fanin_sum == all_out["summary"]["modules"], (fanin_sum, all_out["summary"]["modules"])
    assert dpf_sum == all_out["summary"]["modules"], (dpf_sum, all_out["summary"]["modules"])

    print(
        f"Wrote {JSON_PATH.relative_to(ROOT)} and {JS_PATH.relative_to(ROOT)} "
        f"in {payload['meta']['elapsed_seconds']}s"
    )
    print(
        f"Totals: {all_out['summary']['modules']} modules, "
        f"{all_out['summary']['declarations']} decls, "
        f"{all_out['summary']['theorems_lemmas']} thm/lem, "
        f"attr_decls={all_out['summary']['attr_tagged_decls']}"
    )
    print("Top 5 attrs:", all_out["decl_attrs"][:8])
    print("Top 8 typeclasses:", all_out["typeclasses"]["top_all"][:8])
    print("Top 8 strong typeclasses:", all_out["typeclasses"]["top_strong"][:8])
    print("Proof shapes:", all_out["proof_shapes"])
    print("Equivalences:", all_out["equivalences"][:8])


if __name__ == "__main__":
    main()
