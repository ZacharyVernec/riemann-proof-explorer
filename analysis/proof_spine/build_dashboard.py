#!/usr/bin/env python3
"""Generate self-contained spine_dashboard.html from spine_metrics.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIR = Path(__file__).resolve().parent
METRICS_PATH = DIR / "spine_metrics.json"
HTML_PATH = DIR / "spine_dashboard.html"

# Verified mathematical notes from reading the top .lean files directly
VERIFIED_NOTES = {
    "Main": "Final root export proving riemannHypothesis, riemannZeta_eq_zero_re, LFunction_ne_zero_of_half_lt_re, LFunction_eq_zero_re, and LFunction_eq_zero_re_of_isPrimitive.",
    "Supplements.Kernels.MainTheoremsAll": "Apex junction merging MainTheoremsCritical and SmallClassNumbers.CorGKOf; dominates the entire proof tree below Main.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.RowSrc": "Bridges theta-kernel Parseval input (tLiftK) into galoisLocalGlobalStrong_recParameter (Row0b recT); shared by MainConclusion and CorGKOf.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GaloisRepresentationsOfThetaLift": "Bridges geometric realization (geoOne_holds) and TLiftK into Galois representations of theta lifts.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.WeightOneGeometricRealization": "Discharges HolomorphicLefschetzFormula from lefschetz_fixedPoint_finite_etale_correspondence to prove GeoOne.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.GeometricRealizationOfWeightOne": "Synthesizes crystalline towers, p-adic Witt lattices, finite-etale Kodaira-Spencer (ksGood_holds), and Hodge Lefschetz sums into GeoOne.",
    "Development.AutomorphicArithmetic.CharacterBoxes.RiemannHypothesisOfEveryCharacter": "Assembles operator, interpolation, and covolume inputs and proves riemannHypothesis_of_everyCharacter via completedRiemannZeta_one_sub and Gamma_R zeros.",
    "Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.TopMainZj": "Constructs LitLocAlt, LiteratureAutomorphyHypothesis, and LiteratureCMHypothesis from OpenImageCondition to build VWin.",
    "Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.WindowBoundOfLiteratureLevel": "Reduces VWin to LiteratureRankNHypothesis via descent-vanishing patching and Kato bounds.",
    "Development.WeilBound.CoreStatements.AutomorphicKernels.MoriwakiBigness.HilbertSamuelApplications.TopCovolSlim2Use": "Bridges Moriwaki bigness, Fargues exactness, Zarhin, Nef RR, Scholze-Weinstein, and Fubini-Study Chow heights to CovolX.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfSlimAndHyp": "Proves covolX_of_slim2 from Slim + HypothesesXH via exists_ch2Const_of_prints.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfHeightPrintsStatement": "Statement wrapper exposing GlobalTheory.T.covolume_of_height.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfHeightHyp": "Bridges hypotheses3_of_slim, second_jets_moret_bailly, and known_of_published_inputs into covolume_from_height_theorems.",
    "Supplements.Kernels.MainTheoremsCritical": "Assembles MainTheorems with SmallClassNumbers (ClassNumberThree, LenEqZeroIff, OnePoint).",
    "Supplements.Kernels.MainTheorems": "Exposes allChi, rhOfAll, critAll, and claimAll from CritLine, ClaimStrip, and MainConclusion.",
    "Development.AutomorphicArithmetic.CharacterBoxes.MainConclusion": "Proves UpperTheory.FinalTheorems.everyCharacter and riemannHypothesis from RowSrc + EveryCharacterOfLiteratureOfVWin + VwinOfRow.",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.EveryCharacterOfLiteratureOfVWin": "Synthesis binding OpenLiteratureStatements, published_results_arithmetic, and topCovolSlim2_use_alt_alt into EveryCharacter.",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.SiegelEisensteinSecondTermHypotheses": "Bridges Fock-model evaluation grids, Howe unramifiedness, and Siegel-Weil convergence to nonempty_hyps_definite_side_of_closed_bound.",
    "Development.AutomorphicSpectrum.Proofs.GeometryProofs.GoodTowerVolumeTheoremAlt": "Combines Arakelov intersection system, Moriwaki HS/bigness, ResK, Fargues Hodge-Tate, Zarhin, and thetaUnifAV_closed into GoodTowerExistsX and VolumeTheoremX.",
    "Development.AutomorphicSpectrum.Proofs.GeometryProofs.FinalTheoremOfInputsRightStatement": "Statement wrapper for final_theorem_of_inputs_right.",
    "Development.AutomorphicSpectrum.Proofs.GeometryProofs.FinalTheoremOfInputsRight": "Combines OrdinaryCurveStatement, family_pos_of_hodge_tate_inputs, comparison_of_inputs_avoidance, and CmpPair.",
    "Development.AutomorphicSpectrum.Proofs.DivisibilityProofs.GoodTowerVolumeTheoremStatement": "Statement wrapper for good_tower_volume_theorem.",
    "Development.AutomorphicSpectrum.Proofs.DivisibilityProofs.GoodTowerVolumeTheorem": "Discharges GoodTowerExistsX (exists_good_root_tower) and VolumeTheoremX (volume_theorem_of_inputs).",
    "Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.KatoQuadraticCharacters.UnramifiedZeta.ZetaUr": "Proves GlobalTheory.Ord2.ZetaUr via Kato Euler-system integrality and smoothed zeta-class Hodge-Tate law.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.ToroidalCompactificationFanLogKodairaSpencerIso": "Bridges rigid boundary charts for unitary data to ToroidalForFanKS.",
    "ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.BirationalGeometry.ToroidalCompactification.UniformisationConclusion": "Defines PELUnif and UniformisationConclusion (PsiUnitOn + TorsionIso) for PEL Shimura toroidal compactifications.",
    "ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.SemiabelianSchemes.SplitTori.SplitTorusAff": "Critical-path leaf (height 0): defines splitTorusAff, splitTorus, Gm, characters, and n-torsion schemes over Base Spec.",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.CohomologicalCsdTempered": "Anchor leaf module in ThirdPlaceSeries.",
    "Formalism.SharpRestriction.ParConsts": "Packs FamCore parameter constants (parConsts, NoGain, FamP) used across the analytic and geometric bridges.",
}


def compact_node(d: dict) -> dict:
    out = {
        "n": d["name"],
        "p": d["rel_path"],
        "t": d["top_dir"],
        "l": d["lines"],
        "th": d["n_theorems"],
        "df": d["n_defs"],
        "dm": d["dist_from_main"],
        "h": d["height_from_leaves"],
        "in": d["in_degree"],
        "out": d["out_degree"],
        "ds": d.get("dom_subtree_size", 1),
        "dl": d.get("dom_subtree_lines", d["lines"]),
    }
    if "rank" in d:
        out["rk"] = d["rank"]
    if "idom_name" in d:
        out["id"] = d["idom_name"]
    if "dom_depth" in d:
        out["dd"] = d["dom_depth"]
    if "dom_lineage" in d:
        out["lin"] = d["dom_lineage"]
    if "crit_ways_to_leaf" in d:
        out["cw"] = d["crit_ways_to_leaf"]
    if "height_width_in_crit_subgraph" in d:
        out["w"] = d["height_width_in_crit_subgraph"]
    if "brandes_weighted_cross_top" in d:
        out["bc"] = d["brandes_weighted_cross_top"]
        out["bs"] = d["brandes_weighted_strict_transit"]
        out["ci"] = d["cross_top_in"]
        out["co"] = d["cross_top_out"]
        out["cp"] = d["cross_top_prod"]
        out["itd"] = d["distinct_importer_top_dirs"]
        out["otd"] = d["distinct_imported_top_dirs"]
        out["pf"] = d["path_stress_fraction"]
        out["pl"] = d["path_stress_log10"]
    decls = d.get("sample_decls", [])[:6]
    if decls:
        out["dcl"] = [f"{x['kind']} {x['name']} (L{x['line_no']})" for x in decls]
    if d["name"] in VERIFIED_NOTES:
        out["note"] = VERIFIED_NOTES[d["name"]]
    return out


def render_spine_report_md(m: dict, source_blob_base: str = "", version_label: str = "") -> str:
    """Render PROOF_SPINE_REPORT.md dynamically from spine_metrics.json."""
    audit = m["audit"]
    la = m["leaf_and_entry_audit"]
    profiles = sorted(m["stratigraphy"]["top_dir_profiles"], key=lambda p: (-p["files"], p["top_dir"]))
    doms = m["dominators"]["top_100_bottlenecks"]
    skeleton = m["dominators"]["skeleton_ge_300"]
    skel_thresh = m["dominators"].get("skeleton_threshold", 300)
    crit = m["critical_path"]
    hubs = m["hubs_and_bridges"]
    edge_mat = m["stratigraphy"]["top_dir_edge_matrix"]

    def mlink(rel_path: str, label: str | None = None) -> str:
        text = label or Path(rel_path).name
        if source_blob_base:
            return f"[{text}]({source_blob_base.rstrip('/')}/{rel_path})"
        return f"`{rel_path}`"

    ver_suffix = f" ({version_label})" if version_label else ""
    lines: list[str] = []
    lines.append(f"# Proof Spine, Bottlenecks & Critical Dependency Chain{ver_suffix}")
    lines.append("")
    lines.append(
        f"This report analyzes the logical dependency DAG of the proof—tracing its mandatory mathematical bottlenecks (dominator tree rooted at {mlink('Main.lean')}), its deepest critical dependency chain from the final RH/GRH theorems down to foundational leaves, and the key bridge modules connecting the major theories (interactive explorer in [spine_dashboard.html](spine_dashboard.html))."
    )
    lines.append("")
    lines.append(
        "> **Edge Orientation Convention:** Throughout this report, a directed edge `(u, v)` means module `u` **depends on** `v` (`u` imports `v`). Hence `Main.lean` is the unique root/source at the apex of the proof, and foundational leaf modules sit at the base (`height = 0`)."
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## Executive Audit Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total Lean modules in codebase | {audit['total_files']:,} |")
    lines.append(f"| Modules reachable from `Main.lean` | {audit['reachable_from_main']:,} |")
    lines.append(f"| Unreachable / standalone modules excluded | {audit['unreachable_from_main']:,} |")
    lines.append(f"| Internal dependency edges (reachable DAG) | {audit['total_internal_edges']:,} |")
    lines.append(f"| Strict DAG verified (`is_dag`) | {'Yes' if audit['is_dag'] else 'No'} |")
    lines.append(f"| Shortest distance span from `Main.lean` | 0 – {audit['max_dist_from_main']} |")
    lines.append(f"| Critical dependency chain length | {crit['max_edges']} edges / {crit['max_nodes']} modules |")
    lines.append(f"| Critical max-length paths | {crit['total_max_length_paths']:,} |")
    lines.append(f"| Foundational leaf modules (`out_degree = 0`) | {la['leaf_count']:,} ({la['leaf_lines']:,} lines) |")
    lines.append(f"| Log10 total `Main → Leaf` dependency paths | {audit['total_main_to_leaf_paths_log10']} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Entry Funnel & Foundational Base")
    lines.append("")
    lines.append("### 1.1 Entry Funnel Near `Main.lean` (`dist ≤ 3`)")
    lines.append("")
    lines.append("| Dist | Module | Dom Subtree | Out-Deg | Mathematical Role |")
    lines.append("|---:|---|---:|---:|---|")
    for e in la["entry_layers_dist_le_3"][:25]:
        role = VERIFIED_NOTES.get(e["name"], "")
        if not role and e.get("sample_decls"):
            role = ", ".join(f"`{d['name'].rsplit('.', 1)[-1]}`" for d in e["sample_decls"][:4])
        lines.append(
            f"| {e['dist_from_main']} | {mlink(e['rel_path'], e['name'])} | {e['dom_subtree_size']:,} | {e['out_degree']} | {role} |"
        )
    lines.append("")
    lines.append("### 1.2 Top Foundational Leaves (`out_degree = 0`)")
    lines.append("")
    lines.append(
        f"There are **{la['leaf_count']:,}** foundational leaf modules (`{la['leaf_lines']:,}` lines, `{la['leaf_theorems']:,}` theorems, `{la['leaf_defs']:,}` definitions). Modules with zero external imports: `{la['leaf_no_external_imports']}`."
    )
    lines.append("")
    lines.append("| In-Deg | Lines | Top Directory | Module |")
    lines.append("|---:|---:|---|---|")
    for x in la["top_20_most_imported_leaves"][:15]:
        lines.append(f"| {x['in_degree']:,} | {x['lines']:,} | `{x['top_dir']}` | {mlink(x['rel_path'], x['name'])} |")
    if la["build_aid_modules"]:
        lines.append("")
        lines.append(f"### 1.3 `BuildAid` Modules ({len(la['build_aid_modules'])})")
        lines.append("")
        for b in la["build_aid_modules"]:
            lines.append(f"- {mlink(b['rel_path'], b['name'])} (dist {b['dist_from_main']}, in-degree {b['in_degree']})")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Stratigraphic Layering Across Top-Level Theories")
    lines.append("")
    lines.append("| Top Directory | Files | Lines | Leaves | Dist (min/med/max) | Height (med/max) |")
    lines.append("|---|---:|---:|---:|---|---|")
    for p in profiles:
        lines.append(
            f"| `{p['top_dir']}` | {p['files']:,} | {p['lines']:,} | {p['leaf_files']:,} | "
            f"{p['dist_min']} / {p['dist_median']} / {p['dist_max']} | {p['height_median']} / {p['height_max']} |"
        )
    lines.append("")
    lines.append("### Major Cross-Theory Edge Flows")
    lines.append("")
    lines.append("| Dependent (`src`) | Dependency (`dst`) | Edges |")
    lines.append("|---|---|---:|")
    for e in edge_mat[:15]:
        lines.append(f"| `{e['src_top_dir']}` | `{e['dst_top_dir']}` | {e['edges']:,} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. Dominator Bottleneck Spine (Cooper–Harvey–Kennedy)")
    lines.append("")
    lines.append(
        f"Every dependency path from `Main.lean` to a module passes through its dominators (`{len(skeleton)}` skeleton nodes with dominated subtree size `≥ {skel_thresh}`). Top mandatory bottlenecks:"
    )
    lines.append("")
    lines.append("| Rank | Dom Subtree | Depth | Dist / H | Top Dir | Module |")
    lines.append("|---:|---:|---:|---:|---|---|")
    for d in doms[:30]:
        lines.append(
            f"| {d['rank']} | {d['dom_subtree_size']:,} ({d['dom_subtree_pct']}%) | {d['dom_depth']} | "
            f"{d['dist_from_main']} / {d['height_from_leaves']} | `{d['top_dir']}` | {mlink(d['rel_path'], d['name'])} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. Critical Dependency Chain & Longest Intra-Directory Chains")
    lines.append("")
    lines.append(
        f"The longest dependency chain spans **{crit['max_edges']} edges ({crit['max_nodes']} modules)** across **{crit['total_max_length_paths']:,}** total max-length paths, with **{crit['mandatory_single_node_heights']}** single-node chokes and **{len(crit['branching_heights'])}** branching heights."
    )
    lines.append("")
    lines.append("| Top Directory | Max Intra-Dir Edges | Start → End |")
    lines.append("|---|---:|---|")
    for td, info in sorted(crit["intra_dir_longest"].items(), key=lambda x: -x[1]["max_intra_edges"]):
        lines.append(
            f"| `{td}` | {info['max_intra_edges']} | `{info['start_module'].rsplit('.', 1)[-1]}` → `{info['end_module'].rsplit('.', 1)[-1]}` |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Top Cross-Theory Bridges & Path-Stress Hubs")
    lines.append("")
    lines.append("| Rank | Brandes Cross-Dir | Cross Fan (In×Out) | In / Out | Top Dir | Module |")
    lines.append("|---:|---:|---:|---:|---|---|")
    for x in hubs["top_30_cross_dir_brandes"][:15]:
        lines.append(
            f"| {x['rank']} | {x['brandes_weighted_cross_top']:,.1f} | {x['cross_top_prod']:,} | "
            f"{x['in_degree']:,} / {x['out_degree']:,} | `{x['top_dir']}` | {mlink(x['rel_path'], x['name'])} |"
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build proof spine JS data, report, and HTML explorer")
    parser.add_argument("--metrics-path", type=Path, default=METRICS_PATH)
    parser.add_argument("--out-dir", type=Path, default=DIR)
    parser.add_argument("--write-html", action="store_true", help="Write canonical spine_dashboard.html")
    parser.add_argument("--version-label", type=str, default="")
    parser.add_argument("--source-blob-base", type=str, default="")
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    m = json.loads(args.metrics_path.read_text())

    # Build compact data payload for UI
    payload = {
        "audit": m["audit"],
        "leaf_audit": {
            "leaf_count": m["leaf_and_entry_audit"]["leaf_count"],
            "leaf_lines": m["leaf_and_entry_audit"]["leaf_lines"],
            "leaf_theorems": m["leaf_and_entry_audit"]["leaf_theorems"],
            "leaf_defs": m["leaf_and_entry_audit"]["leaf_defs"],
            "leaf_no_ext": m["leaf_and_entry_audit"]["leaf_no_external_imports"],
            "leaf_zero_decls": m["leaf_and_entry_audit"]["leaf_zero_decls"],
            "by_top": m["leaf_and_entry_audit"]["leaves_by_top_dir"],
            "top_ext": m["leaf_and_entry_audit"]["top_20_leaf_external_imports"][:10],
            "build_aid": [
                {
                    "n": b["name"],
                    "p": b["rel_path"],
                    "dm": b["dist_from_main"],
                    "in": b["in_degree"],
                    "imp": b["importers"][:5],
                }
                for b in m["leaf_and_entry_audit"]["build_aid_modules"]
            ],
            "top_leaves_imp": [compact_node(x) for x in m["leaf_and_entry_audit"]["top_20_most_imported_leaves"][:10]],
        },
        "profiles": m["stratigraphy"]["top_dir_profiles"],
        "dist_hist": m["stratigraphy"]["dist_histogram"],
        "height_hist": m["stratigraphy"]["height_histogram"],
        "edge_matrix": m["stratigraphy"]["top_dir_edge_matrix"],
        "dom_counts": m["dominators"]["subtree_size_counts"],
        "dom_top100": [compact_node(x) for x in m["dominators"]["top_100_bottlenecks"]],
        "skeleton": [
            {
                "n": s["name"],
                "p": s["rel_path"],
                "t": s["top_dir"],
                "id": s["idom_name"],
                "dd": s["dom_depth"],
                "ds": s["dom_subtree_size"],
                "dl": s["dom_subtree_lines"],
                "dm": s["dist_from_main"],
                "h": s["height_from_leaves"],
                "in": s["in_degree"],
                "out": s["out_degree"],
                "note": VERIFIED_NOTES.get(s["name"], ""),
            }
            for s in m["dominators"]["skeleton_ge_300"]
        ],
        "crit": {
            "max_edges": m["critical_path"]["max_edges"],
            "max_nodes": m["critical_path"]["max_nodes"],
            "total_paths": m["critical_path"]["total_max_length_paths"],
            "sub_nodes": m["critical_path"]["subgraph_node_count"],
            "sub_edges": m["critical_path"]["subgraph_edge_count"],
            "mandatory": m["critical_path"]["mandatory_single_node_heights"],
            "branches": m["critical_path"]["branching_heights"],
            "chain": [compact_node(x) for x in m["critical_path"]["canonical_chain"]],
            "intra": m["critical_path"]["intra_dir_longest"],
        },
        "hubs": {
            "brandes_n": m["hubs_and_bridges"]["brandes_config"]["sample_count"],
            "in_deg": [compact_node(x) for x in m["hubs_and_bridges"]["top_30_in_degree"]],
            "out_deg": [compact_node(x) for x in m["hubs_and_bridges"]["top_30_out_degree"]],
            "bc_cross": [compact_node(x) for x in m["hubs_and_bridges"]["top_30_cross_dir_brandes"]],
            "fan_cross": [compact_node(x) for x in m["hubs_and_bridges"]["top_30_cross_top_dir_fan_bridges"]],
            "stress": [compact_node(x) for x in m["hubs_and_bridges"]["top_30_main_to_leaf_path_stress"]],
        },
    }

    safe_json = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    data_js_path = args.out_dir / "spine_dashboard_data.js"
    data_js_path.write_text(f"window.__SPINE_DATA__ = {safe_json};\n", encoding="utf-8")
    print(f"Wrote {data_js_path} ({data_js_path.stat().st_size:,} bytes)")

    report_md = render_spine_report_md(m, source_blob_base=args.source_blob_base, version_label=args.version_label)
    report_md_path = args.out_dir / "PROOF_SPINE_REPORT.md"
    report_md_path.write_text(report_md, encoding="utf-8")
    print(f"Wrote {report_md_path} ({report_md_path.stat().st_size:,} bytes)")

    if not args.write_html:
        return

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Proof Spine &amp; Structural DAG Explorer — Riemann Hypothesis Lean 4 Formalization</title>
<style>
  :root {{
    --bg: #ffffff;
    --bg2: #f7f7f7;
    --panel: #ffffff;
    --panel2: #f0f0f0;
    --border: #cccccc;
    --text: #111111;
    --muted: #555555;
    --accent: #0056b3;
    --accent2: #0056b3;
    --good: #15803d;
    --warn: #b45309;
    --danger: #b91c1c;
    --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    line-height: 1.5;
  }}
  header {{
    background: #ffffff;
    border-bottom: 1px solid var(--border);
    padding: 16px 20px;
  }}
  .title-row {{
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }}
  h1 {{
    margin: 0;
    font-size: 1.4rem;
    font-weight: 700;
  }}
  .subtitle {{
    color: var(--muted);
    font-size: 0.9rem;
    margin-top: 4px;
  }}
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    font-size: 0.75rem;
    font-weight: 600;
    background: #f0f0f0;
    color: var(--text);
    border: 1px solid var(--border);
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(165px, 1fr));
    gap: 8px;
    margin-top: 12px;
  }}
  .kpi {{
    background: var(--bg2);
    border: 1px solid var(--border);
    padding: 8px 12px;
  }}
  .kpi-label {{
    font-size: 0.74rem;
    color: var(--muted);
  }}
  .kpi-val {{
    font-size: 1.15rem;
    font-weight: 700;
    margin-top: 2px;
    font-family: var(--mono);
  }}
  .kpi-sub {{
    font-size: 0.75rem;
    color: var(--muted);
    margin-top: 2px;
  }}
  nav {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 20px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
  }}
  .tab-btn {{
    background: #ffffff;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 6px 12px;
    font-size: 0.86rem;
    cursor: pointer;
  }}
  .tab-btn:hover {{
    background: #eeeeee;
  }}
  .tab-btn.active {{
    background: #222222;
    color: #ffffff;
    border-color: #222222;
  }}
  main {{
    padding: 16px 20px 40px;
    max-width: 1360px;
    margin: 0 auto;
  }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 14px 16px;
    margin-bottom: 16px;
  }}
  .card-head {{
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
  }}
  .card h2 {{
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
  }}
  .card p.desc {{
    margin: 4px 0 0;
    font-size: 0.84rem;
    color: var(--muted);
  }}
  .controls {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }}
  button.ctrl, select.ctrl, input.ctrl {{
    background: #ffffff;
    color: var(--text);
    border: 1px solid var(--border);
    padding: 5px 9px;
    font-size: 0.82rem;
    font-family: inherit;
  }}
  button.ctrl {{ cursor: pointer; }}
  button.ctrl:hover {{ background: #eeeeee; }}
  button.ctrl.active {{
    background: #222222;
    border-color: #222222;
    color: #ffffff;
  }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 8px 0 10px;
  }}
  .legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 2px 8px;
    background: var(--bg2);
    border: 1px solid var(--border);
    font-size: 0.78rem;
    cursor: pointer;
    user-select: none;
  }}
  .legend-item.dim {{ opacity: 0.38; }}
  .swatch {{
    width: 10px;
    height: 10px;
    display: inline-block;
  }}
  .svg-wrap {{
    position: relative;
    width: 100%;
    overflow-x: auto;
    background: #ffffff;
    border: 1px solid var(--border);
    padding: 8px;
  }}
  .tooltip {{
    position: fixed;
    pointer-events: none;
    background: #ffffff;
    border: 1px solid #666666;
    padding: 8px 10px;
    font-size: 0.78rem;
    color: var(--text);
    z-index: 100;
    max-width: 340px;
    display: none;
  }}
  .grid-2 {{
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 14px;
  }}
  @media (max-width: 1020px) {{
    .grid-2 {{ grid-template-columns: 1fr; }}
  }}
  .table-wrap {{
    overflow-x: auto;
    max-height: 500px;
    border: 1px solid var(--border);
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.81rem;
  }}
  th, td {{
    padding: 6px 8px;
    border: 1px solid #dddddd;
    text-align: left;
    vertical-align: top;
  }}
  th {{
    position: sticky;
    top: 0;
    background: var(--panel2);
    color: var(--text);
    font-weight: 600;
    font-size: 0.76rem;
    cursor: pointer;
    z-index: 2;
  }}
  tr:hover td {{
    background: #f5f5f5;
  }}
  tr.selected td {{
    background: #e6f0fa;
  }}
  .num {{
    text-align: right;
    font-family: var(--mono);
    white-space: nowrap;
  }}
  .mod-name {{
    font-family: var(--mono);
    font-size: 0.78rem;
    word-break: break-all;
  }}
  .dir-pill {{
    display: inline-block;
    padding: 1px 6px;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
  }}
  .detail-box {{
    background: var(--bg2);
    border: 1px solid var(--border);
    padding: 12px;
  }}
  .detail-box h3 {{
    margin: 0 0 6px;
    font-size: 0.95rem;
    font-family: var(--mono);
    word-break: break-all;
    color: var(--accent);
  }}
  .meta-kv {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(115px, 1fr));
    gap: 6px;
    margin: 8px 0;
  }}
  .kv-item {{
    background: #ffffff;
    border: 1px solid var(--border);
    padding: 5px 8px;
  }}
  .kv-k {{ font-size: 0.7rem; color: var(--muted); }}
  .kv-v {{ font-size: 0.86rem; font-family: var(--mono); font-weight: 700; }}
  .note-box {{
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    padding: 8px 10px;
    font-size: 0.82rem;
    margin: 8px 0;
  }}
  .decl-list {{
    font-family: var(--mono);
    font-size: 0.75rem;
    color: var(--muted);
    margin: 6px 0 0;
    padding-left: 18px;
  }}
  .minimap {{
    display: flex;
    flex-wrap: nowrap;
    gap: 2px;
    overflow-x: auto;
    padding: 6px 4px;
    background: var(--bg2);
    border: 1px solid var(--border);
    margin-bottom: 10px;
  }}
  .mm-cell {{
    min-width: 6px;
    height: 24px;
    cursor: pointer;
    opacity: 0.85;
    position: relative;
  }}
  .mm-cell.branch {{
    height: 32px;
    outline: 1px solid #000;
  }}
  .mm-cell.active {{
    opacity: 1;
    outline: 2px solid #000;
    z-index: 2;
  }}
  .tree-node {{
    margin-left: 14px;
    border-left: 1px solid var(--border);
    padding-left: 8px;
  }}
  .tree-row {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 6px;
    cursor: pointer;
    font-size: 0.8rem;
  }}
  .tree-row:hover {{ background: #eeeeee; }}
  .tree-row.selected {{ background: #e6f0fa; }}
  .bar-bg {{
    width: 100px;
    height: 8px;
    background: #e0e0e0;
    display: inline-block;
    vertical-align: middle;
  }}
  .bar-fill {{
    height: 100%;
    background: var(--accent);
  }}
</style>
</head>
<body>
<div style="padding:8px 20px;border-bottom:1px solid #ccc;font-size:13px;background:#fafafa;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">
  <div>
    <a href="../index.html" style="color:#0056b3;text-decoration:none;">&larr; Back to Analysis Portal</a> &middot;
    <a href="PROOF_SPINE_REPORT.html" style="color:#0056b3;text-decoration:none;">PROOF_SPINE_REPORT.html</a> &middot;
    <a href="PROOF_SPINE_REPORT.md" data-version-href="proof_spine/PROOF_SPINE_REPORT.md" style="color:#0056b3;text-decoration:none;">PROOF_SPINE_REPORT.md</a>
  </div>
  <span data-version-picker></span>
</div>
<script src="../version_picker.js"></script>
<header>
  <div class="title-row">
    <div>
      <h1>Proof Spine &amp; Structural DAG Explorer</h1>
      <div class="subtitle" id="page-subtitle">Lean 4 Riemann Hypothesis Formalization — Exact Reachability, Stratigraphy, Dominator Tree, Critical Spine &amp; Cross-Directory Bridges</div>
    </div>
    <span class="badge" id="version-badge">Multi-Version Offline Dashboard</span>
  </div>
  <div class="kpi-grid" id="kpi-grid"></div>
</header>

<nav>
  <button class="tab-btn active" data-tab="dom">1. Dominator Bottlenecks</button>
  <button class="tab-btn" data-tab="crit">2. Critical Dependency Chain</button>
  <button class="tab-btn" data-tab="hubs">3. Hubs &amp; Cross-Theory Bridges</button>
  <button class="tab-btn" data-tab="strat">4. Stratigraphic Layering</button>
</nav>

<main>
  <!-- TAB 1: STRATIGRAPHY -->
  <section class="tab-panel" id="tab-strat">
    <div class="card">
      <div class="card-head">
        <div>
          <h2>Stratigraphic Distribution by Top-Level Theory</h2>
          <p class="desc">Toggle between shortest distance from <code>Main</code> and height from foundational leaves. Click legend pills to isolate theories.</p>
        </div>
        <div class="controls">
          <button class="ctrl active" id="btn-axis-dist">Distance from Main</button>
          <button class="ctrl" id="btn-axis-height">Height from Leaves</button>
        </div>
      </div>
      <div class="legend" id="strat-legend"></div>
      <div class="svg-wrap"><svg id="strat-svg" width="1240" height="360"></svg></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-head">
          <div>
            <h2>Top-Level Theory Stratigraphic Profiles</h2>
            <p class="desc" id="strat-profile-desc">Click column headers to sort by distance from Main or height from leaves.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table id="profile-table">
            <thead>
              <tr>
                <th data-sort="top_dir">Theory</th>
                <th class="num" data-sort="dist_min">Dist from Main (min/med/max)</th>
                <th class="num" data-sort="height_median">Height from Base (med/max)</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <div>
            <h2>Cross-Theory Dependency Flows</h2>
            <p class="desc">Directed dependency relationships <code>src → dst</code> between top-level theories.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table id="matrix-table">
            <thead>
              <tr>
                <th>Dependent (<code>src</code>)</th>
                <th>Dependency (<code>dst</code>)</th>
                <th>Flow</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 2: DOMINATORS -->
  <section class="tab-panel active" id="tab-dom">
    <div class="card">
      <div class="card-head">
        <div>
          <h2>Dominator Bottleneck Explorer (Cooper-Harvey-Kennedy Tree from <code>Main</code>)</h2>
          <p class="desc">Every dependency path from <code>Main</code> to any theorem in a node's dominated subtree passes through that node.</p>
        </div>
        <div class="controls">
          <input class="ctrl" id="dom-search" type="search" placeholder="Filter module name...">
          <select class="ctrl" id="dom-dir-filter"><option value="">All theories</option></select>
        </div>
      </div>
      <div class="grid-2">
        <div>
          <h3 style="margin:0 0 8px;font-size:0.9rem;color:var(--muted);">Interactive Dominator Tree Skeleton</h3>
          <div id="dom-tree-box" style="max-height:460px;overflow:auto;background:var(--bg2);border:1px solid var(--border);border-radius:9px;padding:10px;"></div>
        </div>
        <div class="detail-box" id="dom-detail">
          <p style="color:var(--muted);margin:0;">Select any node in the dominator tree or table below to inspect its mathematical bridge role, lineage, and declarations.</p>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-head">
        <div>
          <h2>Top Dominator Bottlenecks</h2>
          <p class="desc">Click any row to inspect full details above.</p>
        </div>
      </div>
      <div class="table-wrap">
        <table id="dom-table">
          <thead>
            <tr>
              <th class="num">Rank</th>
              <th class="num">Dom Depth</th>
              <th class="num">Dist / H</th>
              <th>Theory</th>
              <th>Module</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- TAB 3: CRITICAL PATH -->
  <section class="tab-panel" id="tab-crit">
    <div class="card">
      <div class="card-head">
        <div>
          <h2 id="crit-card-title">Exact Critical Path Stepper</h2>
          <p class="desc" id="crit-card-desc">White-outlined bars on the minimap denote branching diamonds along longest paths; single-node levels are mandatory chokes.</p>
        </div>
        <div class="controls">
          <button class="ctrl" id="crit-prev">&larr; Prev</button>
          <button class="ctrl" id="crit-next">Next &rarr;</button>
          <button class="ctrl" id="crit-jump-trans">Next Dir Transition</button>
          <select class="ctrl" id="crit-jump-sel"></select>
        </div>
      </div>
      <div class="minimap" id="crit-minimap"></div>
      <div class="grid-2">
        <div class="detail-box" id="crit-detail"></div>
        <div class="detail-box">
          <h3 style="color:var(--text);">Longest Intra-Directory Chains</h3>
          <p style="font-size:0.8rem;color:var(--muted);margin:0 0 8px;">Maximum chain length staying strictly inside a single <code>top_dir</code>:</p>
          <div class="table-wrap" style="max-height:300px;">
            <table id="intra-table">
              <thead>
                <tr><th>Directory</th><th class="num">Max Edges</th><th>Start &rarr; End</th></tr>
              </thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 4: HUBS & BRIDGES -->
  <section class="tab-panel" id="tab-hubs">
    <div class="card">
      <div class="card-head">
        <div>
          <h2>Hubs &amp; Cross-Directory Bridge Nodes</h2>
          <p class="desc">Compare foundational import hubs (<code>in_degree</code>), assembly aggregators (<code>out_degree</code>), stratified cross-directory Brandes bridges, boundary fan-in&times;fan-out bridges, and <code>Main&rarr;Leaf</code> path-stress hubs.</p>
        </div>
        <div class="controls">
          <button class="ctrl active hub-mode" data-mode="bc_cross">Cross-Dir Brandes (Top 30)</button>
          <button class="ctrl hub-mode" data-mode="fan_cross">Cross-Dir Fan Bridges (Top 30)</button>
          <button class="ctrl hub-mode" data-mode="stress">Path Stress Hubs (Top 30)</button>
          <button class="ctrl hub-mode" data-mode="in_deg">Top In-Degree (30)</button>
          <button class="ctrl hub-mode" data-mode="out_deg">Top Out-Degree (30)</button>
          <input class="ctrl" id="hub-search" type="search" placeholder="Filter module...">
        </div>
      </div>
      <div class="grid-2">
        <div class="table-wrap">
          <table id="hub-table">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>
        <div class="detail-box" id="hub-detail">
          <p style="color:var(--muted);margin:0;">Select any hub or bridge row to view cross-directory fan metrics, path stress, and declarations.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- TAB 5: LEAVES & BUILD AID -->
  <section class="tab-panel" id="tab-leaves">
    <div class="grid-2">
      <div class="card">
        <div class="card-head">
          <div>
            <h2>Leaf Module Audit (<code>out_degree = 0</code>)</h2>
            <p class="desc" id="leaf-card-desc">Foundational leaf modules with no internal project imports.</p>
          </div>
        </div>
        <div id="leaf-bars"></div>
        <h3 style="margin:14px 0 8px;font-size:0.9rem;">Most Heavily Imported Leaves</h3>
        <div class="table-wrap" style="max-height:290px;">
          <table id="leaf-top-table">
            <thead><tr><th class="num">In-Deg</th><th class="num">Lines</th><th class="num">Decls</th><th>Dir</th><th>Module</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div id="buildaid-section">
          <div class="card-head">
            <div>
              <h2><code>BuildAid</code> Library-Suggestion Denylist Leaves</h2>
              <p class="desc" id="buildaid-desc">Meta-programming modules registering namespaces into <code>Lean.LibrarySuggestions.nameDenyListExt</code>.</p>
            </div>
          </div>
          <div class="table-wrap" style="max-height:220px;margin-bottom:14px;">
            <table id="buildaid-table">
              <thead><tr><th>Module</th><th class="num">Dist</th><th class="num">In-Deg</th><th>Sample Importers</th></tr></thead>
              <tbody></tbody>
            </table>
          </div>
        </div>
        <h3 style="margin:10px 0 8px;font-size:0.9rem;">Top Leaf External Imports</h3>
        <div class="table-wrap" style="max-height:220px;">
          <table id="leaf-ext-table">
            <thead><tr><th>External Import</th><th class="num">Leaf Files</th></tr></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </div>
  </section>
</main>

<div class="tooltip" id="tooltip"></div>

<script>
let DATA = null;

const DIR_COLORS = {{
  "(root)": "#f43f5e",
  "Supplements": "#fb923c",
  "Development": "#38bdf8",
  "Formalism": "#a78bfa",
  "GroundTheory": "#34d399",
  "CompanionTheory": "#fbbf24",
  "ReciprocityTheory": "#ec4899",
  "PositivityTheory": "#2dd4bf",
  "Lemmata": "#818cf8",
  "BuildAid": "#94a3b8"
}};

const fmt = (n) => Number(n).toLocaleString("en-US");
const esc = (s) => String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const shortName = (n) => {{
  const parts = n.split(".");
  return parts.length > 3 ? parts.slice(-3).join(".") : n;
}};
const dirColor = (td) => DIR_COLORS[td] || "#64748b";
const dirPill = (td) => `<span class="dir-pill" style="background:${{dirColor(td)}}22;color:${{DIR_COLORS[td]||'#334155'}};border:1px solid ${{dirColor(td)}}55">${{esc(td)}}</span>`;

const tip = document.getElementById("tooltip");
function showTip(evt, html) {{
  tip.innerHTML = html;
  tip.style.display = "block";
  const x = Math.min(window.innerWidth - 375, evt.clientX + 14);
  const y = Math.min(window.innerHeight - 160, evt.clientY + 14);
  tip.style.left = Math.max(8, x) + "px";
  tip.style.top = Math.max(8, y) + "px";
}}
function hideTip() {{ tip.style.display = "none"; }}

function renderKPIs() {{
  const topDoms = DATA.dom_top100 || [];
  const apex = topDoms[1] ? topDoms[1].n.split(".").pop() : "Main";
  const hasNode = (s) => topDoms.some(x => x.n.endsWith("." + s) || x.n === s) || (DATA.skeleton || []).some(x => x.n.endsWith("." + s) || x.n === s);
  const kpis = [
    ["Root Theorem", "Main.lean", `${{fmt(DATA.audit.reachable_from_main)}} modules · ${{fmt(DATA.audit.total_internal_edges)}} edges`],
    ["Apex Bottleneck", apex, topDoms[1] ? `Dominates ${{fmt(topDoms[1].ds)}} modules` : "Root dominator"],
    ["Galois Spine", hasNode("RowSrc") ? "RowSrc" : "MainConclusion", "Strong local-global compatibility Row0b"],
    ["Modularity Spine", hasNode("TopMainZj") ? "TopMainZj → VWin" : "ClaimStrip", "Patching, Kato Euler system & Selmer bounds"],
    ["Critical Chain", `${{DATA.crit.max_edges}} edges`, `${{fmt(DATA.crit.total_paths)}} max-length paths · ${{fmt(DATA.leaf_audit.leaf_count)}} leaves`]
  ];
  document.getElementById("kpi-grid").innerHTML = kpis.map(([k,v,s]) =>
    `<div class="kpi"><div class="kpi-label">${{k}}</div><div class="kpi-val">${{esc(v)}}</div><div class="kpi-sub">${{esc(s)}}</div></div>`
  ).join("");
}}

// Tab switching
document.querySelectorAll(".tab-btn").forEach(btn => {{
  btn.addEventListener("click", () => {{
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
  }});
}});

// ================= TAB 1: STRATIGRAPHY =================
let stratAxis = "dist";
let stratVal = "files";
const activeDirs = new Set();

function renderStratLegend() {{
  const dirs = DATA.profiles.map(p => p.top_dir);
  const el = document.getElementById("strat-legend");
  el.innerHTML = dirs.map(td => {{
    const dim = activeDirs.has(td) ? "" : "dim";
    return `<span class="legend-item ${{dim}}" data-dir="${{esc(td)}}"><span class="swatch" style="background:${{dirColor(td)}}"></span>${{esc(td)}}</span>`;
  }}).join("") + `<span class="legend-item" id="legend-reset" style="color:var(--accent)">Show All</span>`;

  el.querySelectorAll("[data-dir]").forEach(item => {{
    item.addEventListener("click", () => {{
      const d = item.dataset.dir;
      if (activeDirs.size === dirs.length) {{
        activeDirs.clear();
        activeDirs.add(d);
      }} else if (activeDirs.has(d)) {{
        activeDirs.delete(d);
        if (activeDirs.size === 0) dirs.forEach(x => activeDirs.add(x));
      }} else {{
        activeDirs.add(d);
      }}
      renderStratLegend();
      renderStratChart();
    }});
  }});
  document.getElementById("legend-reset").addEventListener("click", () => {{
    dirs.forEach(x => activeDirs.add(x));
    renderStratLegend();
    renderStratChart();
  }});
}}

function renderStratChart() {{
  const svg = document.getElementById("strat-svg");
  const W = 1240, H = 360, pad = {{l: 68, r: 24, t: 20, b: 42}};
  const plotW = W - pad.l - pad.r;
  const plotH = H - pad.t - pad.b;

  let rows = stratAxis === "dist" ? DATA.dist_hist : DATA.height_hist;
  const dirs = DATA.profiles.map(p => p.top_dir);

  // When showing lines across height or dist, scale proportionally if only top_dir file counts exist per bin
  const totals = rows.map(r => {{
    let s = 0;
    const totalFilesInBin = Math.max(1, r.files);
    for (const d of dirs) {{
      if (!activeDirs.has(d)) continue;
      const c = r.by_top_dir[d] || 0;
      s += stratVal === "files" ? c : (r.lines * (c / totalFilesInBin));
    }}
    return s;
  }});
  const maxY = Math.max(1, ...totals);
  const barW = plotW / rows.length;

  let out = `<rect x="0" y="0" width="${{W}}" height="${{H}}" fill="transparent"/>`;
  // Y gridlines
  for (let g = 0; g <= 4; g++) {{
    const val = (maxY * g) / 4;
    const y = pad.t + plotH - (plotH * g) / 4;
    out += `<line x1="${{pad.l}}" y1="${{y}}" x2="${{W - pad.r}}" y2="${{y}}" stroke="#dddddd" stroke-dasharray="3,3"/>`;
    out += `<text x="${{pad.l - 8}}" y="${{y + 4}}" text-anchor="end" fill="#555555" font-size="11" font-family="var(--mono)">${{fmt(Math.round(val))}}</text>`;
  }}

  rows.forEach((r, idx) => {{
    const x = pad.l + idx * barW;
    const bw = Math.max(1.5, barW - (rows.length > 60 ? 0.6 : 2.5));
    let yAcc = pad.t + plotH;
    const totalFilesInBin = Math.max(1, r.files);
    dirs.forEach(d => {{
      if (!activeDirs.has(d)) return;
      const c = r.by_top_dir[d] || 0;
      if (!c) return;
      const val = stratVal === "files" ? c : (r.lines * (c / totalFilesInBin));
      const bh = (val / maxY) * plotH;
      yAcc -= bh;
      out += `<rect x="${{x.toFixed(1)}}" y="${{yAcc.toFixed(1)}}" width="${{bw.toFixed(1)}}" height="${{Math.max(0.6, bh).toFixed(1)}}" fill="${{dirColor(d)}}"/>`;
    }});
    // Hover target rect
    out += `<rect class="bin-hit" data-idx="${{idx}}" x="${{x.toFixed(1)}}" y="${{pad.t}}" width="${{barW.toFixed(1)}}" height="${{plotH}}" fill="transparent"/>`;
    const labelStep = rows.length > 60 ? 20 : 5;
    const axisNum = stratAxis === "dist" ? r.dist : r.height;
    if (axisNum % labelStep === 0 || idx === rows.length - 1) {{
      out += `<text x="${{(x + barW/2).toFixed(1)}}" y="${{H - 16}}" text-anchor="middle" fill="#555555" font-size="11" font-family="var(--mono)">${{axisNum}}</text>`;
    }}
  }});
  out += `<text x="${{pad.l + plotW/2}}" y="${{H - 2}}" text-anchor="middle" fill="#555555" font-size="11">${{stratAxis === "dist" ? "Shortest Path Distance from Main.lean" : "Longest Height from Leaf Modules (out_degree = 0)"}}</text>`;
  svg.innerHTML = out;

  svg.querySelectorAll(".bin-hit").forEach(el => {{
    el.addEventListener("mousemove", (e) => {{
      const r = rows[Number(el.dataset.idx)];
      const k = stratAxis === "dist" ? `Distance d = ${{r.dist}}` : `Height h = ${{r.height}}`;
      const topList = Object.entries(r.by_top_dir).sort((a,b) => b[1]-a[1]).slice(0,5)
        .map(([d,c]) => `<div>${{esc(d)}}: <b>${{fmt(c)}}</b></div>`).join("");
      showTip(e, `<b>${{k}}</b><br>Total files: <b>${{fmt(r.files)}}</b> &middot; Lines: <b>${{fmt(r.lines)}}</b><br>Theorems: ${{fmt(r.theorems)}} &middot; Defs: ${{fmt(r.defs)}}<hr style="border-color:#2a3a59">${{topList}}`);
    }});
    el.addEventListener("mouseleave", hideTip);
  }});
}}

document.getElementById("btn-axis-dist").addEventListener("click", (e) => {{
  stratAxis = "dist";
  e.target.classList.add("active");
  document.getElementById("btn-axis-height").classList.remove("active");
  renderStratChart();
}});
document.getElementById("btn-axis-height").addEventListener("click", (e) => {{
  stratAxis = "height";
  e.target.classList.add("active");
  document.getElementById("btn-axis-dist").classList.remove("active");
  renderStratChart();
}});

let profSortKey = "dist_min", profSortAsc = true;
function renderProfiles() {{
  const rows = [...DATA.profiles].sort((a,b) => {{
    const va = a[profSortKey], vb = b[profSortKey];
    if (typeof va === "string") return profSortAsc ? va.localeCompare(vb) : vb.localeCompare(va);
    return profSortAsc ? va - vb : vb - va;
  }});
  document.querySelector("#profile-table tbody").innerHTML = rows.map(p => `
    <tr>
      <td>${{dirPill(p.top_dir)}}</td>
      <td class="num">${{p.dist_min}} / ${{p.dist_median}} / ${{p.dist_max}}</td>
      <td class="num">${{p.height_median}} / ${{p.height_max}}</td>
    </tr>
  `).join("");
}}
document.querySelectorAll("#profile-table th[data-sort]").forEach(th => {{
  th.addEventListener("click", () => {{
    const k = th.dataset.sort;
    if (profSortKey === k) profSortAsc = !profSortAsc;
    else {{ profSortKey = k; profSortAsc = (k === "top_dir" || k === "dist_min"); }}
    renderProfiles();
  }});
}});

function renderEdgeMatrix() {{
  const topEdges = DATA.edge_matrix.slice(0, 18);
  const maxE = Math.max(1, ...topEdges.map(x => x.edges));
  document.querySelector("#matrix-table tbody").innerHTML = topEdges.map(e => `
    <tr>
      <td>${{dirPill(e.src_top_dir)}}</td>
      <td>${{dirPill(e.dst_top_dir)}}</td>
      <td><span class="bar-bg"><span class="bar-fill" style="width:${{Math.max(2, 100 * Math.log10(e.edges + 1) / Math.log10(maxE + 1)).toFixed(1)}}%"></span></span></td>
    </tr>
  `).join("");
}}

// ================= TAB 2: DOMINATORS =================
function showModuleDetail(boxId, node) {{
  const box = document.getElementById(boxId);
  const declHtml = (node.dcl && node.dcl.length)
    ? `<div style="margin-top:8px;font-size:0.78rem;color:var(--muted)">Key declarations:</div><ul class="decl-list">${{node.dcl.map(x => `<li>${{esc(x)}}</li>`).join("")}}</ul>`
    : `<div style="margin-top:8px;font-size:0.78rem;color:var(--muted)">Pure import barrel / directive.</div>`;
  const noteHtml = node.note ? `<div class="note-box"><b>Mathematical Role:</b> ${{esc(node.note)}}</div>` : "";
  const lineageHtml = node.lin
    ? `<div style="margin-top:8px;font-size:0.76rem;color:var(--muted)"><b>Dominator lineage:</b> <span style="font-family:var(--mono)">${{node.lin.map(esc).join(" &rarr; ")}}</span></div>`
    : (node.id ? `<div style="margin-top:8px;font-size:0.76rem;color:var(--muted)"><b>Immediate dominator:</b> <span style="font-family:var(--mono)">${{esc(node.id)}}</span> (depth ${{node.dd}})</div>` : "");
  const srcUrl = (window.RHVersion && RHVersion.sourceUrl) ? RHVersion.sourceUrl(node.p) : "";
  const pathHtml = srcUrl
    ? `<a href="${{esc(srcUrl)}}" target="_blank" rel="noopener" style="color:var(--accent);text-decoration:none;">${{esc(node.p)}}</a>`
    : esc(node.p);
  box.innerHTML = `
    <h3>${{esc(node.n)}}</h3>
    <div style="font-size:0.78rem;color:var(--muted);font-family:var(--mono);">${{pathHtml}} ${{dirPill(node.t)}}</div>
    <div class="meta-kv">
      <div class="kv-item"><div class="kv-k">Dist / Height</div><div class="kv-v">${{node.dm}} / ${{node.h}}</div></div>
      <div class="kv-item"><div class="kv-k">Dom Subtree</div><div class="kv-v">${{fmt(node.ds)}}</div></div>
      <div class="kv-item"><div class="kv-k">In / Out Deg</div><div class="kv-v">${{fmt(node.in)}} / ${{fmt(node.out)}}</div></div>
    </div>
    ${{noteHtml}}
    ${{lineageHtml}}
    ${{declHtml}}
  `;
}}

function renderDomTree() {{
  const box = document.getElementById("dom-tree-box");
  const byName = new Map();
  const children = new Map();
  DATA.skeleton.forEach(s => {{
    byName.set(s.n, s);
    children.set(s.n, []);
  }});
  DATA.skeleton.forEach(s => {{
    if (s.n !== "Main" && children.has(s.id)) children.get(s.id).push(s);
  }});
  const topMap = new Map(DATA.dom_top100.map(d => [d.n, d]));

  function buildHTML(name, depth) {{
    const s = byName.get(name);
    if (!s) return "";
    const ch = (children.get(name) || []).sort((a,b) => b.ds - a.ds);
    const showChildren = depth < 3 || ch.length <= 8;
    const row = `<div class="tree-row" data-name="${{esc(s.n)}}">${{dirPill(s.t)}} <span class="mod-name">${{esc(shortName(s.n))}}</span></div>`;
    if (!ch.length) return row;
    const visibleCh = ch.slice(0, showChildren ? ch.length : 12);
    const more = ch.length > visibleCh.length ? `<div style="font-size:0.74rem;color:var(--muted);padding-left:18px;">+ ${{ch.length - visibleCh.length}} additional branches...</div>` : "";
    return row + `<div class="tree-node">${{visibleCh.map(c => buildHTML(c.n, depth + 1)).join("")}}${{more}}</div>`;
  }}

  box.innerHTML = buildHTML("Main", 0);
  box.querySelectorAll(".tree-row").forEach(r => {{
    r.addEventListener("click", () => {{
      box.querySelectorAll(".tree-row").forEach(x => x.classList.remove("selected"));
      r.classList.add("selected");
      const n = r.dataset.name;
      const obj = topMap.get(n) || byName.get(n);
      if (obj) showModuleDetail("dom-detail", obj);
    }});
  }});
  if (DATA.dom_top100.length > 2) showModuleDetail("dom-detail", DATA.dom_top100[2]);
}}

function renderDomTable() {{
  const dirs = [...new Set(DATA.dom_top100.map(x => x.t))].sort();
  const sel = document.getElementById("dom-dir-filter");
  dirs.forEach(d => sel.insertAdjacentHTML("beforeend", `<option value="${{esc(d)}}">${{esc(d)}}</option>`));

  function update() {{
    const q = document.getElementById("dom-search").value.trim().toLowerCase();
    const df = sel.value;
    const rows = DATA.dom_top100.filter(x => (!df || x.t === df) && (!q || x.n.toLowerCase().includes(q)));
    document.querySelector("#dom-table tbody").innerHTML = rows.map(d => `
      <tr data-rk="${{d.rk}}">
        <td class="num">${{d.rk}}</td>
        <td class="num">${{d.dd}}</td>
        <td class="num">${{d.dm}} / ${{d.h}}</td>
        <td>${{dirPill(d.t)}}</td>
        <td class="mod-name">${{esc(d.n)}}</td>
      </tr>
    `).join("");
    document.querySelectorAll("#dom-table tbody tr").forEach(tr => {{
      tr.addEventListener("click", () => {{
        document.querySelectorAll("#dom-table tbody tr").forEach(x => x.classList.remove("selected"));
        tr.classList.add("selected");
        const rk = Number(tr.dataset.rk);
        const obj = DATA.dom_top100.find(x => x.rk === rk);
        if (obj) showModuleDetail("dom-detail", obj);
      }});
    }});
  }}
  document.getElementById("dom-search").addEventListener("input", update);
  sel.addEventListener("change", update);
  update();
}}

// ================= TAB 3: CRITICAL PATH =================
let critStep = 0;
function renderCriticalPath() {{
  const chain = DATA.crit.chain;
  const mm = document.getElementById("crit-minimap");
  const sel = document.getElementById("crit-jump-sel");
  mm.innerHTML = chain.map((n, idx) => {{
    const br = n.w > 1 ? "branch" : "";
    return `<div class="mm-cell ${{br}}" data-step="${{idx}}" style="background:${{DIR_COLORS[n.t]||'#64748b'}}"></div>`;
  }}).join("");

  // Populate transitions into jump select
  sel.innerHTML = chain.map((n, idx) => {{
    const prev = idx > 0 ? chain[idx-1].t : null;
    if (idx === 0 || idx === chain.length - 1 || n.t !== prev || idx % 20 === 0) {{
      return `<option value="${{idx}}">Step ${{idx}} (h=${{n.h}}) [${{n.t}}] ${{shortName(n.n)}}</option>`;
    }}
    return "";
  }}).join("");

  function selectStep(idx) {{
    critStep = Math.max(0, Math.min(chain.length - 1, idx));
    mm.querySelectorAll(".mm-cell").forEach((c, i) => c.classList.toggle("active", i === critStep));
    const n = chain[critStep];
    const brInfo = DATA.crit.branches.find(b => b.height === n.h);
    const brHtml = brInfo
      ? `<div class="note-box" style="background:rgba(251,191,36,0.1);border-color:rgba(251,191,36,0.45)"><b>Branching Diamond at h=${{n.h}} (width ${{brInfo.count}}):</b> ${{brInfo.modules.map(m => `<code>${{esc(m)}}</code>`).join(", ")}}</div>`
      : `<div style="font-size:0.78rem;color:var(--good);margin-top:6px;">Mandatory single-node choke at h=${{n.h}} (100% of ${{fmt(DATA.crit.total_paths)}} critical paths pass here)</div>`;
    showModuleDetail("crit-detail", n);
    document.getElementById("crit-detail").insertAdjacentHTML("beforeend",
      `<div style="margin-top:8px;font-size:0.8rem;color:var(--muted)"><b>Step ${{critStep}} / ${{chain.length - 1}}</b> &middot; Remaining longest paths to leaf: <b>${{fmt(n.cw)}}</b></div>${{brHtml}}`
    );
    const activeCell = mm.querySelector(".mm-cell.active");
    if (activeCell) activeCell.scrollIntoView({{inline: "nearest", block: "nearest"}});
  }}

  mm.querySelectorAll(".mm-cell").forEach(c => {{
    c.addEventListener("click", () => selectStep(Number(c.dataset.step)));
    c.addEventListener("mousemove", (e) => {{
      const idx = Number(c.dataset.step);
      const n = chain[idx];
      showTip(e, `<b>Step ${{idx}} (h=${{n.h}}, dist=${{n.dm}})</b><br>${{esc(n.n)}}<br>Width: ${{n.w}} &middot; In=${{n.in}} Out=${{n.out}}`);
    }});
    c.addEventListener("mouseleave", hideTip);
  }});
  document.getElementById("crit-prev").addEventListener("click", () => selectStep(critStep - 1));
  document.getElementById("crit-next").addEventListener("click", () => selectStep(critStep + 1));
  document.getElementById("crit-jump-trans").addEventListener("click", () => {{
    const curDir = chain[critStep].t;
    for (let i = critStep + 1; i < chain.length; i++) {{
      if (chain[i].t !== curDir) {{ selectStep(i); return; }}
    }}
    selectStep(0);
  }});
  sel.addEventListener("change", () => selectStep(Number(sel.value)));

  // Intra-dir table
  const intraRows = Object.entries(DATA.crit.intra).sort((a,b) => b[1].max_intra_edges - a[1].max_intra_edges);
  document.querySelector("#intra-table tbody").innerHTML = intraRows.map(([td, info]) => `
    <tr>
      <td>${{dirPill(td)}}</td>
      <td class="num"><b>${{info.max_intra_edges}}</b></td>
      <td class="mod-name">${{esc(shortName(info.start_module))}} &rarr; ${{esc(shortName(info.end_module))}}</td>
    </tr>
  `).join("");

  selectStep(0);
}}

// ================= TAB 4: HUBS & BRIDGES =================
let hubMode = "bc_cross";
function renderHubs() {{
  const list = DATA.hubs[hubMode] || [];
  const q = document.getElementById("hub-search").value.trim().toLowerCase();
  const filtered = list.filter(x => !q || x.n.toLowerCase().includes(q));
  const thead = document.querySelector("#hub-table thead");
  const tbody = document.querySelector("#hub-table tbody");

  let metricHdr = "Score";
  if (hubMode === "bc_cross") metricHdr = "Cross Brandes (Strict)";
  else if (hubMode === "fan_cross") metricHdr = "Cross In × Out";
  else if (hubMode === "stress") metricHdr = "Path Stress %";
  else if (hubMode === "in_deg") metricHdr = "In-Degree";
  else if (hubMode === "out_deg") metricHdr = "Out-Degree";

  thead.innerHTML = `<tr><th class="num">#</th><th class="num">${{metricHdr}}</th><th class="num">In / Out</th><th class="num">Dist / H</th><th>Dir</th><th>Module</th></tr>`;
  tbody.innerHTML = filtered.map(x => {{
    let metricCell = "";
    if (hubMode === "bc_cross") metricCell = `${{fmt(Math.round(x.bc))}} <span style="color:var(--muted)">(${{fmt(Math.round(x.bs))}})</span>`;
    else if (hubMode === "fan_cross") metricCell = `<b>${{fmt(x.cp)}}</b> <span style="color:var(--muted)">(${{x.ci}}&times;${{x.co}})</span>`;
    else if (hubMode === "stress") metricCell = `<b>${{(x.pf*100).toFixed(2)}}%</b>`;
    else if (hubMode === "in_deg") metricCell = `<b>${{fmt(x.in)}}</b>`;
    else if (hubMode === "out_deg") metricCell = `<b>${{fmt(x.out)}}</b>`;
    return `<tr data-rk="${{x.rk}}">
      <td class="num">${{x.rk}}</td>
      <td class="num">${{metricCell}}</td>
      <td class="num">${{fmt(x.in)}} / ${{fmt(x.out)}}</td>
      <td class="num">${{x.dm}} / ${{x.h}}</td>
      <td>${{dirPill(x.t)}}</td>
      <td class="mod-name">${{esc(x.n)}}</td>
    </tr>`;
  }}).join("");

  tbody.querySelectorAll("tr").forEach(tr => {{
    tr.addEventListener("click", () => {{
      tbody.querySelectorAll("tr").forEach(r => r.classList.remove("selected"));
      tr.classList.add("selected");
      const rk = Number(tr.dataset.rk);
      const obj = list.find(x => x.rk === rk);
      if (obj) showModuleDetail("hub-detail", obj);
    }});
  }});
  if (filtered.length) showModuleDetail("hub-detail", filtered[0]);
}}

document.querySelectorAll(".hub-mode").forEach(btn => {{
  btn.addEventListener("click", () => {{
    document.querySelectorAll(".hub-mode").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    hubMode = btn.dataset.mode;
    renderHubs();
  }});
}});
document.getElementById("hub-search").addEventListener("input", renderHubs);

// ================= TAB 5: LEAVES & BUILDAID =================
function renderLeavesTab() {{
  const la = DATA.leaf_audit;
  document.getElementById("leaf-card-desc").textContent =
    `${{fmt(la.leaf_count)}} foundational leaf modules (${{fmt(la.leaf_lines)}} lines; ${{fmt(la.leaf_theorems)}} theorems; ${{fmt(la.leaf_defs)}} defs). Modules without external imports: ${{fmt(la.leaf_no_ext)}}.`;
  const baSec = document.getElementById("buildaid-section");
  if (la.build_aid && la.build_aid.length) {{
    baSec.style.display = "";
    document.getElementById("buildaid-desc").textContent =
      `${{la.build_aid.length}} meta-programming modules registering namespaces into Lean.LibrarySuggestions.nameDenyListExt.`;
    document.querySelector("#buildaid-table tbody").innerHTML = la.build_aid.map(b => `
      <tr>
        <td class="mod-name"><b>${{esc(b.n)}}</b></td>
        <td class="num">${{b.dm}}</td>
        <td class="num">${{b.in}}</td>
        <td class="mod-name" style="color:var(--muted)">${{esc(b.imp.slice(0,2).map(shortName).join(", "))}}</td>
      </tr>
    `).join("");
  }} else {{
    baSec.style.display = "none";
  }}

  const entries = Object.entries(la.by_top).sort((a,b) => b[1]-a[1]);
  const maxL = Math.max(1, ...entries.map(e => e[1]));
  document.getElementById("leaf-bars").innerHTML = entries.map(([td, cnt]) => `
    <div style="display:flex;align-items:center;gap:10px;margin:5px 0;font-size:0.82rem;">
      <div style="width:155px">${{dirPill(td)}}</div>
      <div style="flex:1;background:var(--bg2);height:12px;border-radius:6px;overflow:hidden;">
        <div style="width:${{(100*cnt/maxL).toFixed(1)}}%;height:100%;background:${{dirColor(td)}}"></div>
      </div>
      <div class="num" style="width:70px">${{fmt(cnt)}}</div>
    </div>
  `).join("");

  document.querySelector("#leaf-top-table tbody").innerHTML = la.top_leaves_imp.map(x => `
    <tr>
      <td class="num"><b>${{fmt(x.in)}}</b></td>
      <td class="num">${{fmt(x.l)}}</td>
      <td class="num">${{x.th + x.df}}</td>
      <td>${{dirPill(x.t)}}</td>
      <td class="mod-name">${{esc(x.n)}}</td>
    </tr>
  `).join("");

  document.querySelector("#leaf-ext-table tbody").innerHTML = la.top_ext.map(x => `
    <tr><td class="mod-name">${{esc(x.import)}}</td><td class="num">${{fmt(x.count)}}</td></tr>
  `).join("");
}}

function initSpine(data) {{
  DATA = data;
  DATA.profiles.forEach(p => activeDirs.add(p.top_dir));
  if (window.RHVersion && RHVersion.current) {{
    document.getElementById("version-badge").textContent = RHVersion.current.short_label || RHVersion.current.label || RHVersion.current.id;
    document.getElementById("page-subtitle").textContent =
      `Lean 4 Riemann Hypothesis (${{RHVersion.current.label}}) — Exact Reachability, Stratigraphy, Dominator Tree, Critical Spine & Cross-Directory Bridges`;
  }}
  document.getElementById("crit-card-title").textContent =
    `Exact Critical Path Stepper (${{DATA.crit.max_edges}} Edges / ${{DATA.crit.max_nodes}} Modules)`;
  document.getElementById("crit-card-desc").textContent =
    `White-outlined bars on the minimap denote the ${{DATA.crit.branches.length}} heights with branching diamonds (${{fmt(DATA.crit.total_paths)}} total max-length paths); all other ${{DATA.crit.mandatory}} levels are single-module chokes.`;
  const pos = DATA.profiles.find(p => p.top_dir === "PositivityTheory");
  const sortedH = [...DATA.profiles].sort((a,b) => b.height_median - a.height_median);
  if (sortedH.length >= 2) {{
    const topP = pos || sortedH[0];
    const botP = sortedH[sortedH.length - 1];
    document.getElementById("strat-profile-desc").textContent =
      `Click column headers to sort. ${{topP.top_dir}} sits high (med h=${{topP.height_median}}) while ${{botP.top_dir}} sits near the base (med h=${{botP.height_median}}).`;
  }}

  renderKPIs();
  renderStratLegend();
  renderStratChart();
  renderProfiles();
  renderEdgeMatrix();
  renderDomTree();
  renderDomTable();
  renderCriticalPath();
  renderHubs();
  renderLeavesTab();
}}

RHVersion.loadDataScript("proof_spine/spine_dashboard_data.js", "__SPINE_DATA__", initSpine);
</script>
</body>
</html>
"""

    HTML_PATH.write_text(html)
    print(f"Wrote {HTML_PATH} ({HTML_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
