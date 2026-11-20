#!/usr/bin/env python3
"""Generate self-contained spine_dashboard.html from spine_metrics.json."""

from __future__ import annotations

import json
from pathlib import Path

DIR = Path("/home/ubuntu/riemann_proof/analysis/proof_spine")
METRICS_PATH = DIR / "spine_metrics.json"
HTML_PATH = DIR / "spine_dashboard.html"

# Verified mathematical notes from reading the top .lean files directly
VERIFIED_NOTES = {
    "Main": "Final root export proving riemannHypothesis, riemannZeta_eq_zero_re, LFunction_ne_zero_of_half_lt_re, LFunction_eq_zero_re, and LFunction_eq_zero_re_of_isPrimitive.",
    "Supplements.Kernels.MainTheoremsAll": "Apex junction merging MainTheoremsCritical and SmallClassNumbers.CorGKOf; dominates 175,185/175,187 modules.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.RowSrc": "Bridges theta-kernel Parseval input (tLiftK) into galoisLocalGlobalStrong_recParameter (Row0b recT); shared by MainConclusion and CorGKOf.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GaloisRepresentationsOfThetaLift": "Bridges geometric realization (geoOne_holds) and TLiftK into Galois representations of theta lifts.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.WeightOneGeometricRealization": "Discharges HolomorphicLefschetzFormula from lefschetz_fixedPoint_finite_etale_correspondence to prove GeoOne.",
    "Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.GeometricRealizationOfWeightOne": "Synthesizes crystalline towers, p-adic Witt lattices, finite-etale Kodaira-Spencer (ksGood_holds), and Hodge Lefschetz sums into GeoOne.",
    "Development.AutomorphicArithmetic.CharacterBoxes.RiemannHypothesisOfEveryCharacter": "Assembles 208 modules and proves riemannHypothesis_of_everyCharacter via completedRiemannZeta_one_sub and Gamma_R zeros.",
    "Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.TopMainZj": "Constructs LitLocAlt, LiteratureAutomorphyHypothesis, and LiteratureCMHypothesis from OpenImageCondition to build VWin.",
    "Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.WindowBoundOfLiteratureLevel": "Reduces VWin to LiteratureRankNHypothesis via descent-vanishing patching and Kato bounds.",
    "Development.WeilBound.CoreStatements.AutomorphicKernels.MoriwakiBigness.HilbertSamuelApplications.TopCovolSlim2Use": "Bridges Moriwaki bigness, Fargues exactness, Zarhin, Nef RR, Scholze-Weinstein, and Fubini-Study Chow heights to CovolX.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfSlimAndHyp": "Proves covolX_of_slim2 from Slim + HypothesesXH via exists_ch2Const_of_prints.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfHeightPrintsStatement": "Statement wrapper exposing GlobalTheory.T.covolume_of_height.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfHeightHyp": "Bridges hypotheses3_of_slim, second_jets_moret_bailly, and known_of_published_inputs into covolume_from_height_theorems.",
    "Supplements.Kernels.MainTheoremsCritical": "Assembles MainTheorems with SmallClassNumbers (ClassNumberThree, LenEqZeroIff, OnePoint).",
    "Supplements.Kernels.MainTheorems": "Exposes allChi, rhOfAll, critAll, and claimAll from CritLine, ClaimStrip, and MainConclusion.",
    "Development.AutomorphicArithmetic.CharacterBoxes.MainConclusion": "Proves UpperTheory.FinalTheorems.everyCharacter and riemannHypothesis from RowSrc + EveryCharacterOfLiteratureOfVWin + VwinOfRow.",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.EveryCharacterOfLiteratureOfVWin": "814-line synthesis binding OpenLiteratureStatements, published_results_arithmetic, and topCovolSlim2_use_alt_alt into EveryCharacter.",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.SiegelEisensteinSecondTermHypotheses": "Bridges Fock-model evaluation grids, Howe unramifiedness, and Siegel-Weil convergence to nonempty_hyps_definite_side_of_closed_bound.",
    "Development.AutomorphicSpectrum.Proofs.GeometryProofs.GoodTowerVolumeTheoremAlt": "Combines Arakelov intersection system, Moriwaki HS/bigness, ResK, Fargues Hodge-Tate, Zarhin, and thetaUnifAV_closed into GoodTowerExistsX and VolumeTheoremX.",
    "Development.AutomorphicSpectrum.Proofs.GeometryProofs.FinalTheoremOfInputsRightStatement": "Statement wrapper for final_theorem_of_inputs_right.",
    "Development.AutomorphicSpectrum.Proofs.GeometryProofs.FinalTheoremOfInputsRight": "Combines OrdinaryCurveStatement, family_pos_of_hodge_tate_inputs, comparison_of_inputs_avoidance, and CmpPair.",
    "Development.AutomorphicSpectrum.Proofs.DivisibilityProofs.GoodTowerVolumeTheoremStatement": "Statement wrapper for good_tower_volume_theorem.",
    "Development.AutomorphicSpectrum.Proofs.DivisibilityProofs.GoodTowerVolumeTheorem": "Discharges GoodTowerExistsX (exists_good_root_tower) and VolumeTheoremX (volume_theorem_of_inputs).",
    "Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.KatoQuadraticCharacters.UnramifiedZeta.ZetaUr": "Proves GlobalTheory.Ord2.ZetaUr via Kato Euler-system integrality and smoothed zeta-class Hodge-Tate law.",
    "Development.AbelianVarietyTheory.Proofs.DivisorProofs.ToroidalCompactificationFanLogKodairaSpencerIso": "Bridges rigid boundary charts for unitary data to ToroidalForFanKS.",
    "ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.BirationalGeometry.ToroidalCompactification.UniformisationConclusion": "Defines PELUnif and UniformisationConclusion (PsiUnitOn + TorsionIso); critical-path height 9 with 2,390 direct importers.",
    "ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.SemiabelianSchemes.SplitTori.SplitTorusAff": "Critical-path leaf (height 0): defines splitTorusAff, splitTorus, Gm, characters, and n-torsion schemes over Base Spec.",
    "Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.CohomologicalCsdTempered": "1-line anchor leaf (import Mathlib; 0 decls) imported by 2,242 files.",
    "Formalism.SharpRestriction.ParConsts": "Packs FamCore parameter constants (parConsts, NoGain, FamP); carries 89.94% of all Main-to-leaf paths.",
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


def main() -> None:
    m = json.loads(METRICS_PATH.read_text())

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

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Proof Spine &amp; Structural DAG Explorer — Riemann Hypothesis Lean 4 Formalization</title>
<style>
  :root {{
    --bg: #0b101b;
    --bg2: #121a2b;
    --panel: #162033;
    --panel2: #1c2840;
    --border: #2a3a59;
    --text: #e6edf7;
    --muted: #93a4c3;
    --accent: #38bdf8;
    --accent2: #a78bfa;
    --good: #34d399;
    --warn: #fbbf24;
    --danger: #fb7185;
    --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: var(--sans);
    line-height: 1.45;
  }}
  header {{
    background: linear-gradient(135deg, #0f172a 0%, #172554 55%, #1e1b4b 100%);
    border-bottom: 1px solid var(--border);
    padding: 20px 28px 16px;
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
    font-size: 1.45rem;
    letter-spacing: -0.02em;
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
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 600;
    background: rgba(56, 189, 248, 0.14);
    color: var(--accent);
    border: 1px solid rgba(56, 189, 248, 0.35);
  }}
  .kpi-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
    gap: 10px;
    margin-top: 16px;
  }}
  .kpi {{
    background: rgba(15, 23, 42, 0.72);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px 14px;
  }}
  .kpi-label {{
    font-size: 0.74rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted);
  }}
  .kpi-val {{
    font-size: 1.25rem;
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
    padding: 10px 28px;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    position: sticky;
    top: 0;
    z-index: 20;
  }}
  .tab-btn {{
    background: transparent;
    color: var(--muted);
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 7px 14px;
    font-size: 0.88rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .tab-btn:hover {{
    color: var(--text);
    background: var(--panel);
  }}
  .tab-btn.active {{
    background: rgba(56, 189, 248, 0.16);
    color: var(--accent);
    border-color: rgba(56, 189, 248, 0.45);
  }}
  main {{
    padding: 20px 28px 40px;
    max-width: 1520px;
    margin: 0 auto;
  }}
  .tab-panel {{ display: none; }}
  .tab-panel.active {{ display: block; }}
  .card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 18px;
  }}
  .card-head {{
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    margin-bottom: 12px;
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
    gap: 8px;
    align-items: center;
  }}
  button.ctrl, select.ctrl, input.ctrl {{
    background: var(--bg2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 6px 10px;
    font-size: 0.82rem;
    font-family: inherit;
  }}
  button.ctrl {{ cursor: pointer; font-weight: 600; }}
  button.ctrl:hover {{ border-color: var(--accent); }}
  button.ctrl.active {{
    background: rgba(56, 189, 248, 0.2);
    border-color: var(--accent);
    color: var(--accent);
  }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 8px 0 12px;
  }}
  .legend-item {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 9px;
    border-radius: 999px;
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
    border-radius: 3px;
    display: inline-block;
  }}
  .svg-wrap {{
    position: relative;
    width: 100%;
    overflow-x: auto;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 10px;
  }}
  .tooltip {{
    position: fixed;
    pointer-events: none;
    background: rgba(11, 16, 27, 0.96);
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 9px 12px;
    font-size: 0.78rem;
    color: var(--text);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.55);
    z-index: 100;
    max-width: 360px;
    display: none;
  }}
  .grid-2 {{
    display: grid;
    grid-template-columns: 1.25fr 1fr;
    gap: 16px;
  }}
  @media (max-width: 1020px) {{
    .grid-2 {{ grid-template-columns: 1fr; }}
  }}
  .table-wrap {{
    overflow-x: auto;
    max-height: 520px;
    border: 1px solid var(--border);
    border-radius: 9px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.81rem;
  }}
  th, td {{
    padding: 7px 10px;
    border-bottom: 1px solid rgba(42, 58, 89, 0.65);
    text-align: left;
    vertical-align: top;
  }}
  th {{
    position: sticky;
    top: 0;
    background: var(--panel2);
    color: var(--muted);
    font-weight: 700;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    cursor: pointer;
    z-index: 2;
  }}
  tr:hover td {{
    background: rgba(56, 189, 248, 0.06);
  }}
  tr.selected td {{
    background: rgba(56, 189, 248, 0.14);
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
    padding: 1px 7px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    white-space: nowrap;
  }}
  .detail-box {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
  }}
  .detail-box h3 {{
    margin: 0 0 6px;
    font-size: 0.96rem;
    font-family: var(--mono);
    word-break: break-all;
    color: var(--accent);
  }}
  .meta-kv {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 8px;
    margin: 10px 0;
  }}
  .kv-item {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 6px 8px;
  }}
  .kv-k {{ font-size: 0.7rem; color: var(--muted); text-transform: uppercase; }}
  .kv-v {{ font-size: 0.88rem; font-family: var(--mono); font-weight: 700; }}
  .note-box {{
    background: rgba(52, 211, 153, 0.08);
    border: 1px solid rgba(52, 211, 153, 0.35);
    border-radius: 8px;
    padding: 9px 11px;
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
    padding: 8px 4px;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 12px;
  }}
  .mm-cell {{
    min-width: 6px;
    height: 28px;
    border-radius: 2px;
    cursor: pointer;
    opacity: 0.82;
    position: relative;
  }}
  .mm-cell.branch {{
    height: 36px;
    outline: 1px solid #fff;
  }}
  .mm-cell.active {{
    opacity: 1;
    transform: scaleY(1.18);
    outline: 2px solid var(--accent);
    z-index: 2;
  }}
  .tree-node {{
    margin-left: 16px;
    border-left: 1px dashed var(--border);
    padding-left: 10px;
  }}
  .tree-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 7px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 0.8rem;
  }}
  .tree-row:hover {{ background: rgba(56, 189, 248, 0.09); }}
  .tree-row.selected {{ background: rgba(56, 189, 248, 0.18); }}
  .bar-bg {{
    width: 110px;
    height: 8px;
    background: var(--bg);
    border-radius: 4px;
    overflow: hidden;
    display: inline-block;
    vertical-align: middle;
  }}
  .bar-fill {{
    height: 100%;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
  }}
</style>
</head>
<body>
<header>
  <div class="title-row">
    <div>
      <h1>Proof Spine &amp; Structural DAG Explorer</h1>
      <div class="subtitle">Lean 4 Riemann Hypothesis Formalization — Exact Reachability, Stratigraphy, Dominator Tree, Critical Spine &amp; Cross-Directory Bridges</div>
    </div>
    <span class="badge">100% Self-Contained Offline Dashboard</span>
  </div>
  <div class="kpi-grid" id="kpi-grid"></div>
</header>

<nav>
  <button class="tab-btn active" data-tab="strat">1. Stratigraphic Layering</button>
  <button class="tab-btn" data-tab="dom">2. Dominator Bottlenecks</button>
  <button class="tab-btn" data-tab="crit">3. Critical Path Stepper (202 Edges)</button>
  <button class="tab-btn" data-tab="hubs">4. Hubs &amp; Cross-Dir Bridges</button>
  <button class="tab-btn" data-tab="leaves">5. Leaf &amp; Entry Audit</button>
</nav>

<main>
  <!-- TAB 1: STRATIGRAPHY -->
  <section class="tab-panel active" id="tab-strat">
    <div class="card">
      <div class="card-head">
        <div>
          <h2>Stratigraphic Distribution by Top-Level Directory</h2>
          <p class="desc">Toggle between shortest distance from <code>Main</code> (0..43) and longest height from leaves (0..202). Click legend pills to isolate directories.</p>
        </div>
        <div class="controls">
          <button class="ctrl active" id="btn-axis-dist">Distance from Main (0..43)</button>
          <button class="ctrl" id="btn-axis-height">Height from Leaves (0..202)</button>
          <button class="ctrl active" id="btn-val-files">Files</button>
          <button class="ctrl" id="btn-val-lines">Lines</button>
        </div>
      </div>
      <div class="legend" id="strat-legend"></div>
      <div class="svg-wrap"><svg id="strat-svg" width="1240" height="360"></svg></div>
    </div>

    <div class="grid-2">
      <div class="card">
        <div class="card-head">
          <div>
            <h2>Top-Level Directory Structural Profiles</h2>
            <p class="desc">Click column headers to sort. Note how <code>PositivityTheory</code> sits high (med h=97) while <code>GroundTheory</code> and <code>ReciprocityTheory</code> sit near the base.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table id="profile-table">
            <thead>
              <tr>
                <th data-sort="top_dir">Directory</th>
                <th class="num" data-sort="files">Files</th>
                <th class="num" data-sort="leaf_pct">Leaves %</th>
                <th class="num" data-sort="dist_min">Dist (min/med/max)</th>
                <th class="num" data-sort="height_median">Height (med/max)</th>
                <th class="num" data-sort="lines">Lines</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-head">
          <div>
            <h2>Cross-Directory Import Matrix (Edges)</h2>
            <p class="desc">Directed imports <code>src → dst</code> between top-level directories (showing top 18 transitions).</p>
          </div>
        </div>
        <div class="table-wrap">
          <table id="matrix-table">
            <thead>
              <tr>
                <th>Importer (<code>src</code>)</th>
                <th>Imported (<code>dst</code>)</th>
                <th class="num">Edges</th>
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
  <section class="tab-panel" id="tab-dom">
    <div class="card">
      <div class="card-head">
        <div>
          <h2>Dominator Bottleneck Explorer (Cooper-Harvey-Kennedy Tree from <code>Main</code>)</h2>
          <p class="desc">Every import path from <code>Main</code> to every file in a node's dominated subtree passes through that node. Verified against independent graph cuts on top 40 nodes.</p>
        </div>
        <div class="controls">
          <input class="ctrl" id="dom-search" type="search" placeholder="Filter module name...">
          <select class="ctrl" id="dom-dir-filter"><option value="">All top_dirs</option></select>
        </div>
      </div>
      <div class="grid-2">
        <div>
          <h3 style="margin:0 0 8px;font-size:0.9rem;color:var(--muted);">Interactive Dominator Tree Skeleton (subtrees &ge; 300 files)</h3>
          <div id="dom-tree-box" style="max-height:460px;overflow:auto;background:var(--bg2);border:1px solid var(--border);border-radius:9px;padding:10px;"></div>
        </div>
        <div class="detail-box" id="dom-detail">
          <p style="color:var(--muted);margin:0;">Select any node in the dominator tree or table below to inspect its lineage, dominated volume, and declarations.</p>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-head">
        <div>
          <h2>Top 100 Dominator Bottlenecks</h2>
          <p class="desc">Ranked by dominated subtree size (inclusive). Click any row to inspect full details above.</p>
        </div>
      </div>
      <div class="table-wrap">
        <table id="dom-table">
          <thead>
            <tr>
              <th class="num">Rank</th>
              <th class="num">Dominated Files</th>
              <th class="num">% Graph</th>
              <th class="num">Dom Lines</th>
              <th class="num">Depth</th>
              <th class="num">Dist / H</th>
              <th class="num">In / Out</th>
              <th>Dir</th>
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
          <h2>Exact Critical Path Stepper (202 Edges / 203 Modules)</h2>
          <p class="desc">White-outlined bars on the minimap denote the 21 heights with branching diamonds (width 2&ndash;3 across 1,008 total max-length paths); all other 182 levels are single-module chokes.</p>
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
            <p class="desc">5,927 foundational leaf modules (615,171 lines; 21,610 theorems; 13,624 defs). Every single leaf imports at least one external library.</p>
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
        <div class="card-head">
          <div>
            <h2><code>BuildAid</code> Library-Suggestion Denylist Leaves</h2>
            <p class="desc">5 meta-programming modules (4 lines each, 0 declarations) registering namespaces into <code>Lean.LibrarySuggestions.nameDenyListExt</code>.</p>
          </div>
        </div>
        <div class="table-wrap" style="max-height:220px;margin-bottom:14px;">
          <table id="buildaid-table">
            <thead><tr><th>Module</th><th class="num">Dist</th><th class="num">In-Deg</th><th>Sample Importers</th></tr></thead>
            <tbody></tbody>
          </table>
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
const DATA = {safe_json};

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
const dirPill = (td) => `<span class="dir-pill" style="background:${{DIR_COLORS[td]||'#64748b'}}22;color:${{DIR_COLORS[td]||'#cbd5e1'}};border:1px solid ${{DIR_COLORS[td]||'#64748b'}}55">${{esc(td)}}</span>`;

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

// Render KPIs
(function renderKPIs() {{
  const a = DATA.audit;
  const kpis = [
    ["Total Modules", fmt(a.total_files), `${{fmt(a.reachable_from_main)}} reachable (100%)`],
    ["Internal Edges", fmt(a.total_internal_edges), "Strict DAG (0 cycles)"],
    ["Leaf Modules", fmt(a.leaf_count), "out_degree = 0 (0 w/o ext imports)"],
    ["Max Dist from Main", a.max_dist_from_main, "Peak at d=10 (15,539 files)"],
    ["Critical Spine Height", `${{a.max_height_from_leaves}} edges`, `${{fmt(DATA.crit.total_paths)}} max paths; 182 chokes`],
    ["Main→Leaf Paths", "9.75 × 10²²", `Exact: ${{a.total_main_to_leaf_paths_exact.slice(0,9)}}... (23 digits)`],
    ["Top Bottleneck", "175,185 (99.999%)", "Supplements.Kernels.MainTheoremsAll"]
  ];
  document.getElementById("kpi-grid").innerHTML = kpis.map(([k,v,s]) =>
    `<div class="kpi"><div class="kpi-label">${{k}}</div><div class="kpi-val">${{v}}</div><div class="kpi-sub">${{s}}</div></div>`
  ).join("");
}})();

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
const activeDirs = new Set(Object.keys(DIR_COLORS));

function renderStratLegend() {{
  const dirs = DATA.profiles.map(p => p.top_dir);
  const el = document.getElementById("strat-legend");
  el.innerHTML = dirs.map(td => {{
    const dim = activeDirs.has(td) ? "" : "dim";
    return `<span class="legend-item ${{dim}}" data-dir="${{esc(td)}}"><span class="swatch" style="background:${{DIR_COLORS[td]}}"></span>${{esc(td)}}</span>`;
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
    out += `<line x1="${{pad.l}}" y1="${{y}}" x2="${{W - pad.r}}" y2="${{y}}" stroke="#26344f" stroke-dasharray="3,3"/>`;
    out += `<text x="${{pad.l - 8}}" y="${{y + 4}}" text-anchor="end" fill="#93a4c3" font-size="11" font-family="var(--mono)">${{fmt(Math.round(val))}}</text>`;
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
      out += `<rect x="${{x.toFixed(1)}}" y="${{yAcc.toFixed(1)}}" width="${{bw.toFixed(1)}}" height="${{Math.max(0.6, bh).toFixed(1)}}" fill="${{DIR_COLORS[d]}}"/>`;
    }});
    // Hover target rect
    out += `<rect class="bin-hit" data-idx="${{idx}}" x="${{x.toFixed(1)}}" y="${{pad.t}}" width="${{barW.toFixed(1)}}" height="${{plotH}}" fill="transparent"/>`;
    const labelStep = rows.length > 60 ? 20 : 5;
    const axisNum = stratAxis === "dist" ? r.dist : r.height;
    if (axisNum % labelStep === 0 || idx === rows.length - 1) {{
      out += `<text x="${{(x + barW/2).toFixed(1)}}" y="${{H - 16}}" text-anchor="middle" fill="#93a4c3" font-size="11" font-family="var(--mono)">${{axisNum}}</text>`;
    }}
  }});
  out += `<text x="${{pad.l + plotW/2}}" y="${{H - 2}}" text-anchor="middle" fill="#93a4c3" font-size="11">${{stratAxis === "dist" ? "Shortest Path Distance from Main.lean" : "Longest Height from Leaf Modules (out_degree = 0)"}}</text>`;
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
document.getElementById("btn-val-files").addEventListener("click", (e) => {{
  stratVal = "files";
  e.target.classList.add("active");
  document.getElementById("btn-val-lines").classList.remove("active");
  renderStratChart();
}});
document.getElementById("btn-val-lines").addEventListener("click", (e) => {{
  stratVal = "lines";
  e.target.classList.add("active");
  document.getElementById("btn-val-files").classList.remove("active");
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
      <td class="num">${{fmt(p.files)}}</td>
      <td class="num">${{fmt(p.leaf_files)}} (${{p.leaf_pct}}%)</td>
      <td class="num">${{p.dist_min}} / ${{p.dist_median}} / ${{p.dist_max}}</td>
      <td class="num">${{p.height_median}} / ${{p.height_max}}</td>
      <td class="num">${{fmt(p.lines)}}</td>
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

(function renderEdgeMatrix() {{
  const topEdges = DATA.edge_matrix.slice(0, 18);
  const maxE = Math.max(1, ...topEdges.map(x => x.edges));
  document.querySelector("#matrix-table tbody").innerHTML = topEdges.map(e => `
    <tr>
      <td>${{dirPill(e.src_top_dir)}}</td>
      <td>${{dirPill(e.dst_top_dir)}}</td>
      <td class="num">${{fmt(e.edges)}}</td>
      <td><span class="bar-bg"><span class="bar-fill" style="width:${{Math.max(2, 100 * Math.log10(e.edges + 1) / Math.log10(maxE + 1)).toFixed(1)}}%"></span></span></td>
    </tr>
  `).join("");
}})();

// ================= TAB 2: DOMINATORS =================
function showModuleDetail(boxId, node) {{
  const box = document.getElementById(boxId);
  const declHtml = (node.dcl && node.dcl.length)
    ? `<div style="margin-top:8px;font-size:0.78rem;color:var(--muted)">Sample declarations:</div><ul class="decl-list">${{node.dcl.map(x => `<li>${{esc(x)}}</li>`).join("")}}</ul>`
    : `<div style="margin-top:8px;font-size:0.78rem;color:var(--muted)">No parsed declarations in index.</div>`;
  const noteHtml = node.note ? `<div class="note-box"><b>Verified Source Role:</b> ${{esc(node.note)}}</div>` : "";
  const lineageHtml = node.lin
    ? `<div style="margin-top:8px;font-size:0.76rem;color:var(--muted)"><b>Dominator lineage:</b> <span style="font-family:var(--mono)">${{node.lin.map(esc).join(" &rarr; ")}}</span></div>`
    : (node.id ? `<div style="margin-top:8px;font-size:0.76rem;color:var(--muted)"><b>Immediate dominator:</b> <span style="font-family:var(--mono)">${{esc(node.id)}}</span> (depth ${{node.dd}})</div>` : "");
  const linesThmsVal = (node.l !== undefined && node.th !== undefined)
    ? `${{fmt(node.l)}} / ${{fmt(node.th)}}`
    : "&mdash;";
  const crossHtml = (node.bc !== undefined)
    ? `<div class="meta-kv">
         <div class="kv-item"><div class="kv-k">Cross Brandes</div><div class="kv-v">${{fmt(Math.round(node.bc))}}</div></div>
         <div class="kv-item"><div class="kv-k">Strict Transit</div><div class="kv-v">${{fmt(Math.round(node.bs))}}</div></div>
         <div class="kv-item"><div class="kv-k">Cross Fan In/Out</div><div class="kv-v">${{node.ci}} / ${{node.co}}</div></div>
         <div class="kv-item"><div class="kv-k">Path Stress</div><div class="kv-v">${{(node.pf*100).toFixed(2)}}%</div></div>
       </div>`
    : "";
  box.innerHTML = `
    <h3>${{esc(node.n)}}</h3>
    <div style="font-size:0.78rem;color:var(--muted);font-family:var(--mono);">${{esc(node.p)}} ${{dirPill(node.t)}}</div>
    <div class="meta-kv">
      <div class="kv-item"><div class="kv-k">Dominated Files</div><div class="kv-v">${{fmt(node.ds)}}</div></div>
      <div class="kv-item"><div class="kv-k">Dom Subtree Lines</div><div class="kv-v">${{fmt(node.dl)}}</div></div>
      <div class="kv-item"><div class="kv-k">Dist / Height</div><div class="kv-v">${{node.dm}} / ${{node.h}}</div></div>
      <div class="kv-item"><div class="kv-k">In / Out Deg</div><div class="kv-v">${{fmt(node.in)}} / ${{fmt(node.out)}}</div></div>
      <div class="kv-item"><div class="kv-k">Lines / Thms</div><div class="kv-v">${{linesThmsVal}}</div></div>
    </div>
    ${{crossHtml}}
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
    const badge = `<span style="font-family:var(--mono);color:var(--accent);font-weight:700">${{fmt(s.ds)}}</span>`;
    const row = `<div class="tree-row" data-name="${{esc(s.n)}}">${{dirPill(s.t)}} <span class="mod-name">${{esc(shortName(s.n))}}</span> <span style="margin-left:auto">${{badge}}</span></div>`;
    if (!ch.length) return row;
    const visibleCh = ch.slice(0, showChildren ? ch.length : 12);
    const more = ch.length > visibleCh.length ? `<div style="font-size:0.74rem;color:var(--muted);padding-left:18px;">+ ${{ch.length - visibleCh.length}} smaller direct children (&ge;300 files)...</div>` : "";
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
        <td class="num"><b>${{fmt(d.ds)}}</b></td>
        <td class="num">${{(100 * d.ds / DATA.audit.total_files).toFixed(2)}}%</td>
        <td class="num">${{fmt(d.dl)}}</td>
        <td class="num">${{d.dd}}</td>
        <td class="num">${{d.dm}} / ${{d.h}}</td>
        <td class="num">${{d.in}} / ${{d.out}}</td>
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
      : `<div style="font-size:0.78rem;color:var(--good);margin-top:6px;">Mandatory single-node choke at h=${{n.h}} (100% of 1,008 critical paths pass here)</div>`;
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
(function renderLeavesTab() {{
  const la = DATA.leaf_audit;
  const entries = Object.entries(la.by_top).sort((a,b) => b[1]-a[1]);
  const maxL = Math.max(1, ...entries.map(e => e[1]));
  document.getElementById("leaf-bars").innerHTML = entries.map(([td, cnt]) => `
    <div style="display:flex;align-items:center;gap:10px;margin:5px 0;font-size:0.82rem;">
      <div style="width:155px">${{dirPill(td)}}</div>
      <div style="flex:1;background:var(--bg2);height:12px;border-radius:6px;overflow:hidden;">
        <div style="width:${{(100*cnt/maxL).toFixed(1)}}%;height:100%;background:${{DIR_COLORS[td]||'#64748b'}}"></div>
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

  document.querySelector("#buildaid-table tbody").innerHTML = la.build_aid.map(b => `
    <tr>
      <td class="mod-name"><b>${{esc(b.n)}}</b></td>
      <td class="num">${{b.dm}}</td>
      <td class="num">${{b.in}}</td>
      <td class="mod-name" style="color:var(--muted)">${{esc(b.imp.slice(0,2).map(shortName).join(", "))}}</td>
    </tr>
  `).join("");

  document.querySelector("#leaf-ext-table tbody").innerHTML = la.top_ext.map(x => `
    <tr><td class="mod-name">${{esc(x.import)}}</td><td class="num">${{fmt(x.count)}}</td></tr>
  `).join("");
}})();

// Initial render
renderStratLegend();
renderStratChart();
renderProfiles();
renderDomTree();
renderDomTable();
renderCriticalPath();
renderHubs();
</script>
</body>
</html>
"""

    HTML_PATH.write_text(html)
    print(f"Wrote {HTML_PATH} ({HTML_PATH.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
