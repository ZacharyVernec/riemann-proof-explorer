# Full Lean Module Dependency DAG (`original-2026-11-20`)

This document summarizes the deterministic Sugiyama layout, binary data packaging, graph-simplification modes, and WebGL visualization for `lean/src/` (**175,187 reachable modules**, **753,261 internal import edges**, **203 layers**) in [full_dag.html](full_dag.html).

> **Direction Convention:** Every node represents a `.lean` module under the source tree. A directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Top-level theorem modules sit at the top (`layer 0`), and foundational leaves sit below.

---

## 1. Scale & Simplification Modes

| View Mode | Active Controls | Nodes | Edges | Layers |
|---|---|---:|---:|---:|
| **Full DAG** | Default (`C=off, H=off, L=off`) | 175,187 | 753,261 | 203 |
| **Full Hasse** | `H` (Transitive reduction) | 175,187 | 386,211 | 203 |
| **Existing-Theory Collapse** | `C` (83 literature supernodes) | 135,536 | 593,000 | 177 |
| **Existing-Theory Hasse** | `C + H` | 135,536 | 305,256 | 177 |
| **Chain/Leaf Simplified (`full_simp`)** | `L` | 148,009 | 712,764 | 202 |
| **Chain/Leaf Simplified (`full_hasse_simp`)** | `L` | 104,622 | 307,224 | 151 |
| **Chain/Leaf Simplified (`existing_simp`)** | `L` | 115,374 | 563,733 | 177 |
| **Chain/Leaf Simplified (`existing_hasse_simp`)** | `L` | 83,150 | 247,282 | 151 |

- **Existing-Theory Contraction:** Collapses **39,734** modules (22.7% of reachable codebase, anchored at **420** proof-root frontier modules) into **83 Literature Supernodes**, leaving **135,453** novel/shared interface modules.
- **Declarations Indexed (Reachable):** **1,057,807** Lean declarations across `lean/src/`.
- **Binary Packaging (`LDAG` v3):** `19,365,504` raw bytes → `9,305,882` gzip bytes → `12,407,877` JS bytes (`full_dag_data.js`).

## 2. Domain Breakdown & Top Imported Hubs

| Top-Level Directory | Modules |
|---|---:|
| `Development` | 141,928 |
| `Formalism` | 18,254 |
| `GroundTheory` | 8,507 |
| `ReciprocityTheory` | 3,845 |
| `CompanionTheory` | 2,027 |
| `PositivityTheory` | 449 |
| `Lemmata` | 167 |
| `BuildAid` | 5 |
| `Supplements` | 3 |
| `(root)` | 2 |

| Top Imported Hub Module | In-Degree | Out-Degree | Layer |
|---|---:|---:|---:|
| `Development/AbelianVarietyTheory/Definitions/Divisors/CTSmallCone.lean` | 3,088 | 2 | 160 |
| `Development/AbelianVarietyTheory/Definitions/Divisors/SiegelWeilAnisotropicHermitian.lean` | 2,972 | 23 | 149 |
| `Development/AbelianVarietyTheory/Definitions/Divisors/DiscreteSeriesHermitianUnique.lean` | 2,518 | 62 | 152 |
| `Development/AbelianVarietyTheory/PublishedTheorems/AutomorphicForms₂/ExistsNormLeHeightPow.lean` | 2,426 | 4 | 160 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean` | 2,390 | 5 | 193 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean` | 2,284 | 1 | 187 |
| `Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/CohomologicalCsdTempered.lean` | 2,242 | 0 | 171 |
| `Development/AbelianVarietyTheory/Definitions/Divisors/ToKnownTheoremsOf.lean` | 1,838 | 20 | 115 |
| `Development/AbelianVarietyTheory/PublishedTheorems/TwistedTraceFormula/HarishChandraModulesOn.lean` | 1,653 | 4 | 168 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean` | 1,429 | 1 | 196 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean` | 1,340 | 1 | 191 |
| `Development/AbelianVarietyTheory/PublishedTheorems/TwistedTraceFormula/AdmissibleDiscreteSeriesOfHasParam.lean` | 1,323 | 5 | 166 |
| `Development/AbelianVarietyTheory/BlockTheory/DivisorBase/WeilTensorModels.lean` | 1,307 | 5 | 162 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean` | 1,206 | 2 | 195 |
| `Development/AbelianVarietyTheory/Definitions/Degenerations/AdmissibleBaseOfCompleteDvr.lean` | 1,063 | 6 | 168 |

