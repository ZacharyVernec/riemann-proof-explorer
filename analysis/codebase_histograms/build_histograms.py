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


def render_histograms_md(
    payload: dict,
    version_label: str = "",
    rel_src_label: str = "src/",
) -> str:
    """Render CODEBASE_HISTOGRAMS.md dynamically from computed histogram distributions."""
    m = payload["meta"]
    all_dom = payload["by_domain"]["ALL"]
    s = all_dom["summary"]
    ver_note = f" (`{version_label}`)" if version_label else ""
    lines: list[str] = []
    a = lines.append
    a(f"# Codebase Structural Histograms{ver_note}")
    a("")
    a(
        f"Empirical structural analysis across `{rel_src_label}` (**{m['total_modules']:,} reachable modules**, **{m['total_declarations']:,} declarations**, **{m['total_theorems_lemmas']:,} theorems & lemmas**) paired with the interactive explorer in [histograms.html](histograms.html)."
    )
    a("")
    a("---")
    a("")
    a("## 1. Corpus Totals & Proof Glue")
    a("")
    a("| Metric | Count / Share |")
    a("|---|---:|")
    a(f"| Reachable Lean modules | {s['modules']:,} |")
    a(f"| Total declarations | {s['declarations']:,} |")
    a(f"| Theorems & lemmas | {s['theorems_lemmas']:,} |")
    a(f"| Tactic proofs (`by ...`) | {s['tactic_proofs']:,} |")
    a(f"| Term-mode proofs | {s['term_proofs']:,} |")
    a(f"| Attribute-tagged declarations | {s['attr_tagged_decls']:,} |")
    a(f"| Modules defining `@[simp]` | {s['simp_modules']:,} |")
    a("")
    a("### Proof Shape Distribution")
    a("")
    a("| Proof Shape | Count | Share of Thm/Lem |")
    a("|---|---:|---:|")
    tot_tl = max(1, s["theorems_lemmas"])
    for ps in all_dom["proof_shapes"]:
        a(f"| {ps['label']} (`{ps['key']}`) | {ps['count']:,} | {100.0 * ps['count'] / tot_tl:.1f}% |")
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
    a("### Top Attributes & Typeclasses")
    a("")
    a("| Attribute | Count | Typeclass Binder | Signature Occurrences |")
    a("|---|---:|---|---:|")
    attrs = all_dom["decl_attrs"][:10]
    tcs = all_dom["typeclasses"]["top_all"][:10]
    for idx in range(max(len(attrs), len(tcs))):
        at_s = f"`@[{attrs[idx]['tag']}]` | {attrs[idx]['count']:,}" if idx < len(attrs) else " | "
        tc_s = f"`[{tcs[idx]['name']}]` | {tcs[idx]['count']:,}" if idx < len(tcs) else " | "
        a(f"| {at_s} | {tc_s} |")
    a("")
    return "\n".join(lines) + "\n"


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
        render_histograms_md(payload, version_label=args.version_label, rel_src_label=args.rel_src_label),
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
