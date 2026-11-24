# Full Lean Module Dependency DAG (`community-307cef33`)

This document summarizes the deterministic Sugiyama layout, binary data packaging, graph-simplification modes, and WebGL visualization for `src/` (**59,836 reachable modules**, **367,774 internal import edges**, **94 layers**) in [full_dag.html](full_dag.html).

> **Direction Convention:** Every node represents a `.lean` module under the source tree. A directed edge **`A -> B`** means **`A` imports `B`** (`A` depends on `B`). Top-level theorem modules sit at the top (`layer 0`), and foundational leaves sit below.

---

## 1. Scale & Simplification Modes

| View Mode | Active Controls | Nodes | Edges | Layers |
|---|---|---:|---:|---:|
| **Full DAG** | Default (`C=off, H=off, L=off`) | 59,836 | 367,774 | 94 |
| **Full Hasse** | `H` (Transitive reduction) | 59,836 | 170,783 | 94 |
| **Existing-Theory Collapse** | `C` (74 literature supernodes) | 53,296 | 314,259 | 84 |
| **Existing-Theory Hasse** | `C + H` | 53,296 | 149,879 | 84 |
| **Chain/Leaf Simplified (`full_simp`)** | `L` | 56,808 | 363,081 | 94 |
| **Chain/Leaf Simplified (`full_hasse_simp`)** | `L` | 49,704 | 159,232 | 91 |
| **Chain/Leaf Simplified (`existing_simp`)** | `L` | 50,299 | 309,708 | 84 |
| **Chain/Leaf Simplified (`existing_hasse_simp`)** | `L` | 43,797 | 139,112 | 80 |

- **Existing-Theory Contraction:** Collapses **6,614** modules (11.1% of reachable codebase, anchored at **291** proof-root frontier modules) into **74 Literature Supernodes**, leaving **53,222** novel/shared interface modules.
- **Declarations Indexed (Reachable):** **761,777** Lean declarations across `src/`.
- **Binary Packaging (`LDAG` v3):** `7,591,928` raw bytes → `4,219,851` gzip bytes → `5,626,501` JS bytes (`full_dag_data.js`).

## 2. Domain Breakdown & Top Imported Hubs

| Top-Level Directory | Modules |
|---|---:|
| `Development` | 41,263 |
| `Formalism` | 9,901 |
| `GroundTheory` | 5,217 |
| `ReciprocityTheory` | 2,393 |
| `CompanionTheory` | 685 |
| `PositivityTheory` | 226 |
| `Lemmata` | 149 |
| `(root)` | 2 |

| Top Imported Hub Module | In-Degree | Out-Degree | Layer |
|---|---:|---:|---:|
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsCompletedStrictHens.lean` | 1,138 | 0 | 93 |
| `Formalism/LocalToGlobal/IndefiniteReal/LinksDefs.lean` | 986 | 8 | 71 |
| `Formalism/SharpRestriction/LevelLetterCocycles/DataNLoc.lean` | 895 | 1 | 90 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/CubicalStructures/CubeSymmetricSwapFirst.lean` | 813 | 0 | 93 |
| `Development/AbelianVarietyTheory/BlockTheory/DivisorBase/WeilTensorModels.lean` | 713 | 5 | 69 |
| `Formalism/SharpRestriction/GlobalSchurBounds/GeneralLinearActions/GenusMassVolumes.lean` | 611 | 1 | 92 |
| `Formalism/LocalToGlobal/IndefiniteReal/LocalNewformFunction.lean` | 596 | 1 | 74 |
| `Formalism/LocalToGlobal/ProjectiveLattices/ErealAddIInf.lean` | 546 | 0 | 91 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean` | 540 | 3 | 88 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/DiscreteValuationRings/LBPull.lean` | 521 | 2 | 91 |
| `Development/AbelianVarietyTheory/Proofs/FoundationProofs/ExistsContinuousPadic.lean` | 500 | 3 | 86 |
| `Formalism/SharpRestriction/CuspSpanNormBounds/Point.lean` | 484 | 0 | 93 |
| `Formalism/LocalRingCardinality/DataTheta.lean` | 458 | 2 | 85 |
| `Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean` | 453 | 2 | 90 |
| `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/CocycleRightZeroThd.lean` | 450 | 0 | 93 |

