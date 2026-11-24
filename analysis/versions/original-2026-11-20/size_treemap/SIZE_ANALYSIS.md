# Codebase Size & Hierarchical Complexity Analysis (`original-2026-11-20`)

Quantitative breakdown of `lean/src/` (**175,187 reachable modules**, **17,374,215 lines**, **982.8 MiB**, **3,615 directory nodes** across max depth **10**) paired with [treemap_sunburst.html](treemap_sunburst.html).

## 1. Top-Level Directory Breakdown

| Top Directory | Files (%) | Lines (%) | Theorems & Lemmas | Defs & Structs | Median Lines | 1-Decl Modules |
|---|---:|---:|---:|---:|---:|---:|
| `Development` | 141,928 (81.02%) | 12,232,663 (70.41%) | 562,329 | 117,861 | 49 | 72,184 (50.9%) |
| `Formalism` | 18,254 (10.42%) | 3,200,748 (18.42%) | 162,118 | 73,406 | 115 | 2,451 (13.4%) |
| `GroundTheory` | 8,507 (4.86%) | 1,119,138 (6.44%) | 54,211 | 17,764 | 89 | 2,680 (31.5%) |
| `ReciprocityTheory` | 3,845 (2.19%) | 563,016 (3.24%) | 27,722 | 7,945 | 129 | 512 (13.3%) |
| `CompanionTheory` | 2,027 (1.16%) | 194,218 (1.12%) | 9,419 | 2,221 | 58 | 868 (42.8%) |
| `PositivityTheory` | 449 (0.26%) | 55,130 (0.32%) | 2,702 | 1,898 | 88 | 72 (16.0%) |
| `Lemmata` | 167 (0.10%) | 9,232 (0.05%) | 245 | 6 | 40 | 113 (67.7%) |
| `BuildAid` | 5 (0.00%) | 20 (0.00%) | 0 | 0 | 4 | 0 (0.0%) |
| `Supplements` | 3 (0.00%) | 22 (0.00%) | 4 | 0 | 4 | 0 (0.0%) |
| `(root)` | 2 (0.00%) | 28 (0.00%) | 5 | 4 | 14 | 0 (0.0%) |

## 2. Module Granularity & Micro-Modules

- **Single-declaration files:** `78,880` (**45.03%**)
- **Files with ≤ 2 declarations:** `95,256` (**54.37%**)
- **Zero-declaration modules (import barrels / directives):** `178`
- **Statement wrapper files (`Statement` / statements dirs):** `46,610` (26.61%)

## 3. Largest Individual Modules (by Line Count)

| Module | Top Dir | Lines | Decls | Dist / Height |
|---|---|---:|---:|---|
| `Formalism/HermitianCurvature/HermitianCurvatureProofs/IsAdmissibleSplittingCharPairMulTwist.lean` | `Formalism` | 17,981 | 1,352 | 12 / 16 |
| `Formalism/SharpRestriction/CuspSpanNormBounds/LatticeGluingRadicals.lean` | `Formalism` | 9,252 | 642 | 9 / 24 |
| `Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/FixPiIff.lean` | `Development` | 8,029 | 2 | 11 / 53 |
| `Formalism/SharpRestriction/CuspSpanNormBounds/KappaEndpoints.lean` | `Formalism` | 6,945 | 423 | 11 / 34 |
| `Formalism/HermitianCurvature/HermitianCurvatureProofs/UnipotentCoordinatesMeasurePreserving.lean` | `Formalism` | 6,929 | 560 | 12 / 23 |
| `Formalism/SharpRestriction/CuspSpanNormBounds/OscillatoryIntegralBounds.lean` | `Formalism` | 6,333 | 531 | 10 / 26 |
| `Formalism/HermitianCurvature/HermitianCurvatureProofs/CoordinateCommuteRaisingConstant.lean` | `Formalism` | 6,205 | 808 | 12 / 14 |
| `Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/CovariantDegrees.lean` | `Development` | 6,170 | 29 | 11 / 0 |
| `Formalism/SharpRestriction/GrowthBounds/WittFrameLocaliserOrders.lean` | `Formalism` | 5,833 | 433 | 10 / 26 |
| `Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/MemOfClosed.lean` | `Development` | 5,746 | 12 | 12 / 0 |
| `Formalism/LocalToGlobal/KernelLattices/KernelLocalFactors/InterlaceDifferenceShiftInvariant.lean` | `Formalism` | 5,303 | 469 | 12 / 29 |
| `Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/MulMemIntA.lean` | `Development` | 4,969 | 9 | 21 / 0 |
| `Formalism/SharpRestriction/LevelLetterCocycles/BaseChangePreservesUnitaryOf.lean` | `Formalism` | 4,861 | 305 | 11 / 20 |
| `Formalism/SharpRestriction/LevelLetterCocycles/FrobeniusPowUniformizerFactorisation.lean` | `Formalism` | 4,707 | 358 | 12 / 19 |
| `Formalism/SharpRestriction/CuspSpanNormBounds/BlockEstimateWords.lean` | `Formalism` | 4,671 | 278 | 9 / 28 |

