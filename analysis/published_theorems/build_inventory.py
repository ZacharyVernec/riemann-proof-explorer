#!/usr/bin/env python3
"""
Generate PUBLISHED_THEOREMS_INVENTORY.md deterministically for a Lean codebase version
using graph.sqlite, meta.json, and literature_catalog.json.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CATALOG = SCRIPT_DIR / "literature_catalog.json"

NUM_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
TOKEN_IGNORE = {"/", ".lean", " ", "*"}


def is_sym_token(tok: str) -> bool:
    if len(tok) < 3 or any(ch in tok for ch in TOKEN_IGNORE):
        return False
    return True


def compact_path(rel_path: str, orig_hint: str) -> str:
    """Format a repo-relative path preserving ellipsis style if the original hint used it."""
    if orig_hint.startswith(".../"):
        parts = rel_path.split("/")
        if len(parts) >= 2:
            return ".../" + "/".join(parts[-2:])
    return rel_path


def find_matching_files(
    hint: str, reach_by_base: dict[str, list[str]], reach_set: set[str]
) -> list[str]:
    clean = hint.removeprefix("./")
    if clean.startswith(".../"):
        segs = [s for s in clean[4:].split("/.../") if s]
        if not segs:
            return []
        cands = reach_by_base.get(Path(segs[-1]).name, [])
        return [f for f in cands if all(s in f for s in segs) and f.endswith(segs[-1])]
    if "/.../" in clean:
        segs = [s for s in clean.split("/.../") if s]
        if not segs:
            return []
        cands = reach_by_base.get(Path(segs[-1]).name, [])
        return [
            f
            for f in cands
            if f.startswith(segs[0]) and all(s in f for s in segs) and f.endswith(segs[-1])
        ]
    return [clean] if clean in reach_set else []


def split_top_level_clusters(col1: str) -> list[str]:
    """
    Split a col1 cell into clusters of `sym1`, `sym2` (...), keeping symbols together
    with their following parenthetical file/proof annotation.
    """
    # Split on commas outside parentheses and backticks
    parts: list[str] = []
    cur: list[str] = []
    paren_depth = 0
    in_bt = False
    for ch in col1:
        if ch == "`":
            in_bt = not in_bt
            cur.append(ch)
        elif not in_bt and ch == "(":
            paren_depth += 1
            cur.append(ch)
        elif not in_bt and ch == ")" and paren_depth > 0:
            paren_depth -= 1
            cur.append(ch)
        elif not in_bt and paren_depth == 0 and ch == ",":
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur).strip())

    # Group bare symbol items onto the next item that carries a parenthetical clause
    clusters: list[str] = []
    pending: list[str] = []
    for part in parts:
        if not part:
            continue
        pending.append(part)
        if "(" in part and ")" in part:
            clusters.append(", ".join(pending))
            pending = []
    if pending:
        clusters.append(", ".join(pending))
    return clusters


def parse_line_hint(hint: str) -> tuple[int, int] | None:
    if not hint:
        return None
    nums = [int(n) for n in re.findall(r"L(\d+)", hint)]
    if not nums:
        return None
    return min(nums), max(nums)


def pick_best_decl(
    sym: str,
    sym_to_defs: dict[str, list[tuple[str, str, str, int]]],
    prefer_file: str | None = None,
) -> tuple[str, str, str, int] | None:
    cands = sym_to_defs.get(sym)
    if not cands:
        return None
    if prefer_file:
        same_file = [c for c in cands if c[2] == prefer_file]
        if same_file:
            return same_file[0]
    # Prefer specification modules in PublishedTheorems / defining modules over proof modules
    for c in cands:
        if "/PublishedTheorems/" in c[2] and c[1] in ("def", "abbrev", "structure", "theorem"):
            return c
    for c in cands:
        if c[1] in ("def", "abbrev", "structure"):
            return c
    return cands[0]


def resolve_cluster(
    cluster: str,
    sym_to_defs: dict[str, list[tuple[str, str, str, int]]],
    reach_files: list[str],
    reach_set: set[str],
    reach_by_base: dict[str, list[str]],
) -> str | None:
    """Resolve symbols and file/line references in one cluster for the current codebase."""
    # Extract head (before paren) and optional paren clause(s)
    m_par = re.search(r"\(([^()]*)\)", cluster)
    head = cluster[: m_par.start()].strip() if m_par else cluster
    tail = cluster[m_par.start() :] if m_par else ""

    head_syms = [t for t in re.findall(r"`([^`]+)`", head) if is_sym_token(t)]
    alive_head_syms = [s for s in head_syms if s in sym_to_defs]

    # Check if tail mentions extra symbols (e.g. discharged by `foo` in `bar.lean`)
    tail_syms = [t for t in re.findall(r"`([^`]+)`", tail) if is_sym_token(t)]
    alive_tail_syms = [s for s in tail_syms if s in sym_to_defs]

    # Check if any file ref in cluster exists directly
    file_refs = re.findall(r"`([^`#]+\.lean)(#L[^`]*)?`", cluster)
    matched_files = [
        find_matching_files(path, reach_by_base, reach_set) for path, _ in file_refs
    ]
    any_file_matched = any(bool(m) for m in matched_files)

    if head_syms and not alive_head_syms:
        return None
    if not head_syms and not any_file_matched:
        return None

    # If a symbol list had some removed symbols and some alive ones, keep only alive ones
    new_head = head
    if head_syms and alive_head_syms and len(alive_head_syms) < len(head_syms):
        dead = set(head_syms) - set(alive_head_syms)
        # Re-join surviving symbol tokens cleanly if head is just backticked symbols
        if all(t.strip("` ,") in head_syms for t in head.split(",") if t.strip()):
            new_head = ", ".join(f"`{s}`" for s in alive_head_syms)
        else:
            for ds in dead:
                new_head = new_head.replace(f", `{ds}`", "").replace(f"`{ds}`, ", "")

    if not tail:
        return new_head if alive_head_syms else None

    # Rewrite file refs inside tail: (`spec.lean#L...`, proved in `proof.lean#L...`)
    # Split tail clauses cleanly around `; proved` or `, proved` or `, discharged`
    def replace_ref(match: re.Match[str]) -> str:
        full_tok = match.group(0)
        raw_path = match.group(1)
        line_hint = match.group(2) or ""
        is_proved_ctx = bool(
            re.search(
                r"(?:proved|discharged)[^`(]*$",
                tail[: match.start()],
            )
        )
        cands = find_matching_files(raw_path, reach_by_base, reach_set)
        target_syms = alive_tail_syms if (is_proved_ctx and alive_tail_syms) else alive_head_syms

        chosen_file: str | None = None
        if cands:
            # Prefer a candidate defining one of the target symbols
            for cf in cands:
                if any(c[2] == cf for s in target_syms for c in sym_to_defs.get(s, [])):
                    chosen_file = cf
                    break
            if not chosen_file:
                chosen_file = cands[0]
        elif not is_proved_ctx and target_syms:
            # Spec file moved / clumped: relocate via defining symbol
            for s in target_syms:
                decl = pick_best_decl(s, sym_to_defs)
                if decl:
                    chosen_file = decl[2]
                    break
        elif is_proved_ctx and alive_tail_syms:
            # Explicit proof symbol relocated (e.g. RowSrc.lean -> MainConclusion.lean)
            for s in alive_tail_syms:
                decl = pick_best_decl(s, sym_to_defs)
                if decl:
                    chosen_file = decl[2]
                    break
        elif not is_proved_ctx and raw_path.startswith(".../"):
            # Try basename match if directory path slightly refactored
            base = Path(raw_path).name
            bc = reach_by_base.get(base, [])
            if len(bc) == 1:
                chosen_file = bc[0]

        if not chosen_file:
            return "__DEAD_REF__" + full_tok

        # Resolve line numbers of target symbols inside chosen_file
        sym_lines = sorted(
            {
                c[3]
                for s in target_syms
                for c in sym_to_defs.get(s, [])
                if c[2] == chosen_file
            }
        )
        new_path_str = (
            compact_path(chosen_file, raw_path)
            if cands
            else chosen_file
        )
        if not line_hint:
            return f"`{new_path_str}`"
        orig_span = parse_line_hint(line_hint)
        if sym_lines and orig_span:
            lo, hi = orig_span
            if all((lo - 4) <= ln <= (hi + 4) for ln in sym_lines):
                return f"`{new_path_str}{line_hint}`"
            if len(sym_lines) == 1:
                return f"`{new_path_str}#L{sym_lines[0]}`"
            return f"`{new_path_str}#L{sym_lines[0]}-L{sym_lines[-1]}`"
        if sym_lines:
            if len(sym_lines) == 1:
                return f"`{new_path_str}#L{sym_lines[0]}`"
            return f"`{new_path_str}#L{sym_lines[0]}-L{sym_lines[-1]}`"
        return f"`{new_path_str}{line_hint}`" if chosen_file in cands else f"`{new_path_str}`"

    new_tail = re.sub(r"`([^`#]+\.lean)(#L[^`]*)?`", replace_ref, tail)
    # Clean up dead proof/file clauses cleanly
    new_tail = re.sub(r"\s*[;,]\s*(?:proved(?:\s+(?:conditionally|unconditionally))?\s+(?:from\s+`[^`]+`\s+)?in|discharged by\s+`[^`]+`\s+in)\s+__DEAD_REF__`[^`]+`(?:\s*&\s*__DEAD_REF__`[^`]+`)?", "", new_tail)
    new_tail = re.sub(r"\s*&\s*__DEAD_REF__`[^`]+`", "", new_tail)
    new_tail = re.sub(r",?\s*__DEAD_REF__`[^`]+`", "", new_tail)
    new_tail = re.sub(r"\(\s*[;,]\s*", "(", new_tail)
    new_tail = re.sub(r"\s*,\s*\)", ")", new_tail)
    new_tail = re.sub(r"\(\s*\)", "", new_tail).strip()

    if not alive_head_syms and "__DEAD_REF__" in new_tail:
        return None
    if new_head == "" and not new_tail:
        return None
    if new_tail and not new_head:
        return new_tail
    return f"{new_head} {new_tail}".strip() if new_tail else new_head


def resolve_col1(
    orig_col1: str,
    sym_to_defs: dict[str, list[tuple[str, str, str, int]]],
    reach_files: list[str],
    reach_set: set[str],
    reach_by_base: dict[str, list[str]],
) -> tuple[str | None, list[str]]:
    clusters = split_top_level_clusters(orig_col1)
    kept: list[str] = []
    for cl in clusters:
        resolved = resolve_cluster(cl, sym_to_defs, reach_files, reach_set, reach_by_base)
        if resolved:
            kept.append(resolved)
    if not kept:
        return None, []
    joined = ", ".join(kept)
    syms = [t for t in re.findall(r"`([^`]+)`", joined) if is_sym_token(t)]
    return joined, syms


def load_reachable_index(db_path: Path):
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    reach_rows = cur.execute(
        "SELECT id, rel_path FROM modules WHERE reachable_from_main = 1 ORDER BY rel_path"
    ).fetchall()
    reach_files = [r[1] for r in reach_rows]
    reach_set = set(reach_files)
    reach_by_base: dict[str, list[str]] = defaultdict(list)
    for rf in reach_files:
        reach_by_base[Path(rf).name].append(rf)

    sym_to_defs: dict[str, list[tuple[str, str, str, int]]] = defaultdict(list)
    for full_name, kind, rel_path, line_no in cur.execute(
        """
        SELECT d.name, d.kind, m.rel_path, d.line_no
        FROM declarations d
        JOIN modules m ON m.id = d.module_id
        WHERE m.reachable_from_main = 1
        ORDER BY d.line_no ASC
        """
    ):
        short = full_name.rsplit(".", 1)[-1]
        sym_to_defs[short].append((full_name, kind, rel_path, line_no))
    conn.close()
    return reach_files, reach_set, reach_by_base, sym_to_defs


def build_inventory(args: argparse.Namespace) -> None:
    catalog = json.loads(args.catalog_path.read_text(encoding="utf-8"))
    meta = json.loads(args.meta_path.read_text(encoding="utf-8"))
    reach_files, reach_set, reach_by_base, sym_to_defs = load_reachable_index(args.db_path)

    reach_total = int(meta.get("reachable_files", len(reach_files)))
    pt_reach_files = [f for f in reach_files if "/PublishedTheorems/" in f]
    pt_count = len(pt_reach_files)
    pt_pct = (100.0 * pt_count / reach_total) if reach_total else 0.0

    # Active PublishedTheorems directories
    active_pt_dirs = []
    for entry in catalog["published_theorems_dirs"]:
        prefix = entry["dir_prefix"].rstrip("/") + "/"
        n_mod = sum(1 for f in reach_files if f.startswith(prefix))
        if n_mod > 0:
            active_pt_dirs.append((entry, n_mod))

    n_pt_dirs = len(active_pt_dirs)
    pt_word = NUM_WORDS.get(n_pt_dirs, str(n_pt_dirs))
    src_label = args.rel_src_label or "src/"
    ver_note = f" (`{args.version_label}`)" if args.version_label else ""

    lines: list[str] = []
    lines.append(f"# Inventory of Existing Peer-Reviewed Theory Across `{src_label}`{ver_note}")
    lines.append("")
    lines.append(
        f"Across `{src_label}` ({reach_total:,} modules reachable from `Main.lean`), existing peer-reviewed mathematics is formalized in two complementary places:"
    )
    lines.append("")
    lines.append(
        f"1. **The {pt_word} `PublishedTheorems` directories** ({pt_count:,} modules, {pt_pct:.1f}% of reachable codebase), which declare the primary catalog of `Prop` specifications and bridges (`GlobalTheory.Published.*`, `UpperTheory.V.Published.*`, etc.)."
    )
    lines.append(
        "2. **Companion background-theory modules outside `PublishedTheorems`**, which formalize additional foundational peer-reviewed results (such as BLGGT/Caraiani local–global compatibility `Row0b`, Local Langlands with tame types `RecTExists`, unitary-to-$\\mathrm{GL}_n$ isobaric base change, local/global Tate duality and Greenberg–Wiles, Moriwaki arithmetic bigness, functorial resolution of singularities in characteristic $0$, étale cohomology finiteness, and the holomorphic Lefschetz fixed-point formula)."
    )
    lines.append("")
    lines.append(
        "This report compares these formalized mathematical statements against the peer-reviewed literature, catalogs where they specialize hypotheses, weaken equivalences, or introduce project-specific scaffolding, and documents the methodology used to identify and collapse their proof subtrees in the [Full Lean Module DAG](../full_dag/FULL_DAG.md)."
    )
    lines.append("")
    lines.append(f"## Overview of the {pt_word.capitalize()} `PublishedTheorems` Directories")
    lines.append("")
    lines.append("| Directory | Reachable Modules | Mathematical Role | Literature Traceability |")
    lines.append("|---|---:|---|---|")
    for entry, n_mod in active_pt_dirs:
        lines.append(
            f"| `{entry['dir_prefix']}/` | {n_mod:,} | {entry['role']} | {entry['traceability']} |"
        )
    lines.append("")
    lines.append("## Overview of Companion Collapsible Background Theory Outside `PublishedTheorems`")
    lines.append("")
    lines.append("| Directory / Statement Hub | Primary Proof Subtree(s) | Literature Domain |")
    lines.append("|---|---|---|")
    for entry in catalog["companion_overview"]:
        hub_paths = [p.removeprefix("./") for p in re.findall(r"`([^`#]+\.lean)", entry["hub"])]
        hub_syms = [t for t in re.findall(r"`([^`]+)`", entry["hub"]) if is_sym_token(t)]
        has_any = any(sym in sym_to_defs for sym in hub_syms) or any(
            bool(find_matching_files(hp, reach_by_base, reach_set)) for hp in hub_paths
        )
        if not has_any:
            continue
        subtree_text = entry["subtree"]
        # Update RowSrc.lean if clumped into MainConclusion.lean
        if "RowSrc.lean" in subtree_text and not any(f.endswith("RowSrc.lean") for f in reach_files):
            decl = pick_best_decl("galoisLocalGlobalStrong_recParameter", sym_to_defs)
            if decl:
                subtree_text = subtree_text.replace(
                    "`.../IntegralStructures/RowSrc.lean`",
                    f"`{decl[2]}#L{decl[3]}`",
                )
        lines.append(f"| {entry['hub']} | {subtree_text} | {entry['domain']} |")
    lines.append("")
    lines.append("## Cross-Cutting Ways the Lean Formalizations Differ from Published Literature")
    lines.append("")
    lines.extend(catalog["cross_cutting"])
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Comparative Tables: Published Literature vs. Lean Formalizations")

    total_catalog_rows = sum(len(s["rows"]) for s in catalog["sections"])
    rendered_rows = 0
    omitted_rows: list[tuple[int, str]] = []

    for sec in catalog["sections"]:
        resolved_sec_rows = []
        for row in sec["rows"]:
            col1_new, _ = resolve_col1(
                row["col1"], sym_to_defs, reach_files, reach_set, reach_by_base
            )
            if col1_new:
                resolved_sec_rows.append((col1_new, row["col2"], row["col3"]))
            else:
                omitted_rows.append((sec["num"], row["col2"]))
        if not resolved_sec_rows:
            continue
        rendered_rows += len(resolved_sec_rows)
        lines.append("")
        lines.append(f"### {sec['num']}. {sec['title']}")
        lines.append("")
        if sec.get("intro"):
            intro_txt = sec["intro"].replace("six `PublishedTheorems` folders", f"{pt_word} `PublishedTheorems` folders")
            intro_txt = intro_txt.replace("`lean/src/`", f"`{src_label}`")
            lines.append(intro_txt)
            lines.append("")
        lines.append("| Lean Symbol(s) & File(s) | Published, Peer-Reviewed Result | How the Lean Formalization Differs from the Literature |")
        lines.append("|---|---|---|")
        for c1, c2, c3 in resolved_sec_rows:
            lines.append(f"| {c1} | {c2} | {c3} |")
        lines.append("")
        lines.append("---")

    # Section 12: untraced formalizations (always emit heading so build_full_dag.py locates it cleanly)
    lines.append("")
    lines.append(f"### 12. {catalog['section12']['title']}")
    lines.append("")
    lines.append("| Lean Symbol(s) & File(s) | Category | Why It Cannot Be Traced to Existing Literature |")
    lines.append("|---|---|---|")
    for row in catalog["section12"]["rows"]:
        # Check if any file/dir/symbol referenced in this Sec 12 row is present in the version
        c1 = row["col1"]
        refs = re.findall(r"`([^`]+)`", c1)
        is_dir_row = any("/" in r or r.endswith(".lean") for r in refs)
        syms = [r for r in refs if is_sym_token(r)]
        if is_dir_row and not syms:
            # Pure path / folder rule
            has_match = any(
                any(r.removeprefix("./").rstrip("/") in rf for rf in reach_files)
                for r in refs
                if not r.startswith("_root_")
            )
            if not has_match:
                continue
        elif syms:
            has_sym = any(s in sym_to_defs for s in syms)
            has_file = any(
                bool(find_matching_files(p, reach_by_base, reach_set))
                for p, _ in re.findall(r"`([^`#]+\.lean)(#L[^`]*)?`", c1)
            )
            if not (has_sym or has_file) and "Internal proof-decomposition" not in row["category"]:
                # Resolve out removed standalone items if absent; keep internal Prop scaffolding rules if PublishedTheorems exists
                if not any(s.startswith(("A0", "L0", "Q1", "S1", "Ptfs")) for s in syms):
                    continue
        resolved_c1, _ = resolve_col1(c1, sym_to_defs, reach_files, reach_set, reach_by_base)
        final_c1 = resolved_c1 if (syms and resolved_c1 and "**" not in c1) else c1
        lines.append(f"| {final_c1} | {row['category']} | {row['reason']} |")

    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Methodology: Identifying Collapsible Existing-Theory Proof Subtrees")
    lines.append("")
    foundational_count = sum(
        1
        for f in reach_files
        if f.startswith("Formalism/") or f.startswith("ReciprocityTheory/") or "/Definitions/" in f
    )
    lines.append(
        f"A naive directory-based filter fails to isolate existing-theory proofs in this repository: the {pt_word} `PublishedTheorems` folders comprise only **{pt_count:,} modules ({pt_pct:.1f}%)** and consist almost entirely of `def ... : Prop` *specifications* rather than proofs, while the actual proofs live downstream across `Development/`, `GroundTheory/`, `CompanionTheory/`, and `PositivityTheory/` and are wired into the main argument at discharge hubs (`EveryCharacterOfLiteratureOfVWin.lean`, `TopMainZj.lean`, `PublishedHypothesesFromPatching.lean`, `TopCovolSlim2Use.lean`, `MainConclusion.lean`). Conversely, ~{foundational_count:,} foundational modules (`Formalism/`, `ReciprocityTheory/`, `Definitions/`) are needed merely to *state* the interfaces and must remain visible."
    )
    lines.append("")
    lines.append(
        f"To identify **only** the subtrees that exist to prove already-existing peer-reviewed theory, the DAG pipeline derives a deterministic **published-theorem proof-frontier cut** directly from Sections 1–12 of this inventory ({rendered_rows:,} active literature theorem groups matching reachable modules out of {total_catalog_rows:,} cataloged):"
    )
    lines.append("")
    lines.append(
        "1. **Inventory-Driven Target Set & Section 12 Exclusion:** Parse every backticked Lean `Prop` identifier from Sections 1–11 (and its bold canonical literature title in Column 2), while explicitly excluding all symbols cataloged in Section 12 (project-packaged analytic NT bounds, project-tailored constants, internal glue predicates, scaffolding `A0`..`KY`, and sanity checks). Restricting targets strictly to this audited inventory prevents generic Mathlib identifiers (such as `IsIntegral`) from matching unrelated algebraic lemmas."
    )
    lines.append(
        "2. **Defining-Module Ancestor Guard:** Using [graph.sqlite](../data/graph.sqlite), resolve each target symbol to its defining Lean module(s) in `PublishedTheorems` or the companion hubs in Section 11, and compute the set of transitive importers (ancestors). A `theorem`/`lemma` is only accepted as a proof of symbol `S` if its module transitively imports a defining module of `S`."
    )
    lines.append(
        "3. **Final-Conclusion Proof-Root Detection & Consumer/Bundle Guards:** Parse the signature of every `theorem` and `lemma` in candidate modules using balanced-delimiter scanning to extract the **final conclusion head(s)** after the last top-level `→` (splitting top-level `∧` conjuncts). This separates *provers* (`theorem foo : GlobalTheory.Published.Bar`) from *consumers* (`theorem baz (h : GlobalTheory.Published.Bar) : NovelResult`). To avoid false positives:"
    )
    lines.append("   - Exclude any module under `*/Definitions/*`.")
    lines.append(
        "   - Exclude any theorem whose premises take an assumed literature hypothesis bundle (`HypothesesU`, `Hypotheses2`, `HypothesesUE`, `LitN`, `LitLoc*`, `LitAut`, `LitCoh`, `LitCM`, `PublishedHodgeBundleTheorems`, `ThetaLocalInputs`, `LiteratureRankNHypothesis`, `OpenImageCondition`, `OpenLiteratureStatements`, etc.), which merely projects or dispatches fields out of an assumed bundle."
    )
    lines.append(
        "   - Exclude any module that also proves a novel headline theorem (`RiemannHypothesis`, `EveryCharacter`, `VWin`, `CorGK`, `Bound`, `CovolX`, `CovolumeBoundOfX`, `DeepStR`, `GoodTowerExistsX`, `VolumeTheoremX`, etc.)."
    )
    lines.append(
        "   - Iteratively peel **multi-topic re-export barrels**: any candidate proof root whose proven literature conclusions span $\\ge 2$ inventory rows and whose direct imports already include candidate proof roots spanning $\\ge 2$ inventory rows is removed from the cut set so each theorem subtree retains its own Literature Supernode rather than merging behind a forwarding hub."
    )
    has_rhec = "Development/AutomorphicArithmetic/CharacterBoxes/RiemannHypothesisOfEveryCharacter.lean" in reach_set
    if has_rhec:
        lines.append(
            "4. **Targeted Dead Transitive Import Pruning on Split Bridges:** `Development/AutomorphicArithmetic/CharacterBoxes/RiemannHypothesisOfEveryCharacter.lean` is a 23-line proof body referencing only `UpperTheory.EveryCharacter` and Mathlib, yet carries 207 unused transitive imports left over from automated module splitting that point directly into downstream subtrees. During collapse reachability (without modifying `.lean` source files or the full DAG), provably unreferenced imports on `RiemannHypothesisOfEveryCharacter` whose targets lie strictly inside existing-theory proof subtrees (below the baseline published-theorem frontier) are pruned, preventing interior proof leakage without collapsing unrelated non-published legacy modules."
        )
    else:
        lines.append(
            "4. **Targeted Dead Transitive Import Pruning on Split Bridges:** Checked automatically when standalone split-bridge modules (such as `RiemannHypothesisOfEveryCharacter.lean`) are present; no split-bridge dead-import pruning is needed in this clumped/simplified codebase."
        )
    lines.append(
        "5. **Frontier-Domination Cut & Literature-Supernode Contraction:** Run reachability from `Main` without traversing outgoing edges of the detected proof roots $B$. Every node still reached is either **active** (novel proof or shared definition/contract) or a **frontier proof root** $f \\in F \\subseteq B$; every unreachable module forms the **collapsed proof-only interior** $C$ (strictly dominated by $B$). Grouping $F$ by its inventory row in Sections 1–11 into axiom-sink **Literature Supernodes** $S_T$ (`out_degree = 0`) and partitioning $C$ via deterministic multi-source BFS assigns every collapsed module to a unique supernode while guaranteeing strict DAG acyclicity and exact conservation of module counts."
    )

    if omitted_rows:
        lines.append("")
        lines.append("### Catalog Rows Not Active in This Version")
        lines.append("")
        lines.append(
            f"The following **{len(omitted_rows)}** literature theorem groups from the baseline catalog have no reachable symbols or defining modules in `{src_label}` (removed, inlined, or unreachable from `Main.lean`):"
        )
        lines.append("")
        for sec_num, col2 in omitted_rows:
            title_short = col2.split("—")[0].strip()
            lines.append(f"- **§{sec_num}:** {title_short}")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_md = args.out_dir / "PUBLISHED_THEOREMS_INVENTORY.md"
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        f"Wrote {out_md}: {pt_count} PublishedTheorems modules, "
        f"{rendered_rows}/{total_catalog_rows} active inventory rows ({len(omitted_rows)} omitted)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build versioned PUBLISHED_THEOREMS_INVENTORY.md")
    parser.add_argument("--src-dir", type=Path, default=ROOT / "lean" / "src")
    parser.add_argument("--db-path", type=Path, default=ROOT / "analysis" / "data" / "graph.sqlite")
    parser.add_argument("--meta-path", type=Path, default=ROOT / "analysis" / "data" / "meta.json")
    parser.add_argument("--out-dir", type=Path, default=SCRIPT_DIR)
    parser.add_argument("--catalog-path", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--version-label", type=str, default="")
    parser.add_argument("--rel-src-label", type=str, default="src/")
    args = parser.parse_args()
    build_inventory(args)


if __name__ == "__main__":
    main()
