# Proof Spine, Bottlenecks & Critical Dependency Chain (community-307cef33)

This report analyzes the logical dependency DAG of the proof—tracing its mandatory mathematical bottlenecks (dominator tree rooted at [Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Main.lean)), its deepest critical dependency chain from the final RH/GRH theorems down to foundational leaves, and the key bridge modules connecting the major theories (interactive explorer in [spine_dashboard.html](spine_dashboard.html)).

> **Edge Orientation Convention:** Throughout this report, a directed edge `(u, v)` means module `u` **depends on** `v` (`u` imports `v`). Hence `Main.lean` is the unique root/source at the apex of the proof, and foundational leaf modules sit at the base (`height = 0`).

---

## Executive Audit Summary

| Metric | Value |
|---|---:|
| Total Lean modules in codebase | 59,884 |
| Modules reachable from `Main.lean` | 59,836 |
| Unreachable / standalone modules excluded | 48 |
| Internal dependency edges (reachable DAG) | 367,774 |
| Strict DAG verified (`is_dag`) | Yes |
| Shortest distance span from `Main.lean` | 0 – 15 |
| Critical dependency chain length | 93 edges / 94 modules |
| Critical max-length paths | 405 |
| Foundational leaf modules (`out_degree = 0`) | 2,692 (384,013 lines) |
| Log10 total `Main → Leaf` dependency paths | 16.586 |

---

## 1. Entry Funnel & Foundational Base

### 1.1 Entry Funnel Near `Main.lean` (`dist ≤ 3`)

| Dist | Module | Dom Subtree | Out-Deg | Mathematical Role |
|---:|---|---:|---:|---|
| 0 | [Main](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Main.lean) | 59,836 | 3 | Final root export proving riemannHypothesis, riemannZeta_eq_zero_re, LFunction_ne_zero_of_half_lt_re, LFunction_eq_zero_re, and LFunction_eq_zero_re_of_isPrimitive. |
| 1 | [Development.AutomorphicArithmetic.CharacterBoxes.MainConclusion](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean) | 59,831 | 28 | Proves UpperTheory.FinalTheorems.everyCharacter and riemannHypothesis from RowSrc + EveryCharacterOfLiteratureOfVWin + VwinOfRow. |
| 1 | [Development.AutomorphicArithmetic.CharacterBoxes.ClaimStrip](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean) | 1 | 1 |  |
| 1 | [Statements](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Statements.lean) | 1 | 0 | `RiemannZetaZerosOnLine`, `DirichletLNonvanishingRightOfHalf`, `DirichletLZerosOnLine`, `PrimitiveDirichletLZerosOnLine` |
| 2 | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.EveryCharacterOfLiteratureOfVWin](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean) | 31,637 | 233 | Synthesis binding OpenLiteratureStatements, published_results_arithmetic, and topCovolSlim2_use_alt_alt into EveryCharacter. |
| 2 | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.VwinOfRow](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean) | 4,455 | 168 | `OpenImageCondition`, `elliptic_main_theorem_cm_of_open`, `hecke_tate_functional_equation_of_open`, `hilbert_class_field_j_of_open` |
| 2 | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.GeometricRealizationOfWeightOne](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean) | 3,153 | 46 | Synthesizes crystalline towers, p-adic Witt lattices, finite-etale Kodaira-Spencer (ksGood_holds), and Hodge Lefschetz sums into GeoOne. |
| 2 | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.Development](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/Development.lean) | 381 | 69 | `cplMem_of`, `genMul_of`, `dGenMul_of`, `getD_eq` |
| 2 | [Development.AutomorphicArithmetic.Foundations.EtaleClopenDescent.HolomorphicLefschetzFiniteEtaleIntegral](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/EtaleClopenDescent/HolomorphicLefschetzFiniteEtaleIntegral.lean) | 140 | 33 |  |
| 2 | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.ThetaParseval.ThetaKernels.TPGHolds](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/ThetaKernels/TPGHolds.lean) | 37 | 94 |  |
| 2 | [Development.AutomorphicArithmetic.Foundations.LocalLanglands.LocalCentralUnits.RecTExists](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean) | 10 | 41 | `sumList_perm`, `charZero_adicCompletion`, `exists_isLExt`, `extDepth` |
| 2 | [Development.AbelianVarietyTheory.Definitions.Divisors.IsGaloisCover](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/Divisors/IsGaloisCover.lean) | 1 | 3 |  |
| 2 | [Development.AbelianVarietyTheory.Definitions.GaloisGeometry.CoeEqAlgebraMapZeroEquiv](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/GaloisGeometry/CoeEqAlgebraMapZeroEquiv.lean) | 1 | 2 |  |
| 2 | [Development.AbelianVarietyTheory.Definitions.GaloisGeometry.OmegaPullOmegaTraceOfSecTraceOne](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/GaloisGeometry/OmegaPullOmegaTraceOfSecTraceOne.lean) | 1 | 3 |  |
| 2 | [Development.AbelianVarietyTheory.Definitions.GaloisGeometry.SurjectiveOfLocallySurjective](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/GaloisGeometry/SurjectiveOfLocallySurjective.lean) | 1 | 3 |  |
| 2 | [Development.AbelianVarietyTheory.Proofs.CoherentCohomologyProofs.CechModulesFunctorShortExactOfIsAffineOpen](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/CoherentCohomologyProofs/CechModulesFunctorShortExactOfIsAffineOpen.lean) | 1 | 5 |  |
| 2 | [Development.AbelianVarietyTheory.Proofs.CoherentCohomologyProofs.ExistsAddEquivOfSurjectiveOfKerIff](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/CoherentCohomologyProofs/ExistsAddEquivOfSurjectiveOfKerIff.lean) | 1 | 0 | `exists_addEquiv_of_surjective_of_ker_iff` |
| 2 | [Development.AbelianVarietyTheory.Proofs.SatakeParameters.ExistsIntegralClopenDecompositionOfSmooth](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/SatakeParameters/ExistsIntegralClopenDecompositionOfSmooth.lean) | 1 | 5 |  |
| 2 | [Development.AbelianVarietyTheory.Proofs.SatakeParameters.FormResFormPullFormPull](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/SatakeParameters/FormResFormPullFormPull.lean) | 1 | 2 |  |
| 2 | [Development.AbelianVarietyTheory.Proofs.SatakeParameters.HodgePullHodgePull](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/SatakeParameters/HodgePullHodgePull.lean) | 1 | 1 |  |
| 2 | [Development.AutomorphicArithmetic.CharacterBoxes.EveryCharacter](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean) | 1 | 1 |  |
| 2 | [Development.AutomorphicArithmetic.CharacterBoxes.HalfPlane](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/HalfPlane.lean) | 1 | 2 |  |
| 2 | [Development.AutomorphicArithmetic.CommutativeAlgebra.FiniteDimensionalHodgeCohomologyOfSmoothProj](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CommutativeAlgebra/FiniteDimensionalHodgeCohomologyOfSmoothProj.lean) | 1 | 6 |  |
| 2 | [Development.AutomorphicArithmetic.Foundations.EtaleClopenDescent.CompactSpaceOfProjectiveAndOfFinite](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/EtaleClopenDescent/CompactSpaceOfProjectiveAndOfFinite.lean) | 1 | 4 |  |
| 2 | [Development.AutomorphicArithmetic.Foundations.EtaleClopenDescent.ExistsUniqueComplexPointLiftClopenCover](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/EtaleClopenDescent/ExistsUniqueComplexPointLiftClopenCover.lean) | 1 | 3 |  |

### 1.2 Top Foundational Leaves (`out_degree = 0`)

There are **2,692** foundational leaf modules (`384,013` lines, `11,619` theorems, `8,808` definitions). Modules with zero external imports: `0`.

| In-Deg | Lines | Top Directory | Module |
|---:|---:|---|---|
| 1,138 | 39 | `ReciprocityTheory` | [ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.BirationalGeometry.ToroidalCompactification.IsCompletedStrictHens](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsCompletedStrictHens.lean) |
| 813 | 203 | `ReciprocityTheory` | [ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.SemiabelianSchemes.CubicalStructures.CubeSymmetricSwapFirst](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/CubicalStructures/CubeSymmetricSwapFirst.lean) |
| 546 | 134 | `Formalism` | [Formalism.LocalToGlobal.ProjectiveLattices.ErealAddIInf](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/ProjectiveLattices/ErealAddIInf.lean) |
| 484 | 61 | `Formalism` | [Formalism.SharpRestriction.CuspSpanNormBounds.Point](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/SharpRestriction/CuspSpanNormBounds/Point.lean) |
| 450 | 227 | `ReciprocityTheory` | [ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.BirationalGeometry.ToroidalCompactification.CocycleRightZeroThd](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/CocycleRightZeroThd.lean) |
| 420 | 209 | `ReciprocityTheory` | [ReciprocityTheory.GaloisValuations.GlobalA](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/GaloisValuations/GlobalA.lean) |
| 401 | 393 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.CommutativeAlgebra.ResMapBijective](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/CommutativeAlgebra/ResMapBijective.lean) |
| 388 | 84 | `Formalism` | [Formalism.ConjugateSelfDual.Statement](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/ConjugateSelfDual/Statement.lean) |
| 306 | 192 | `Development` | [Development.AutomorphicArithmetic.IntegralCasts.IsOpenStabOfMemNhds](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/IntegralCasts/IsOpenStabOfMemNhds.lean) |
| 282 | 241 | `Development` | [Development.AbelianVarietyTheory.Definitions.Foundations.SmoothPartStable](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/Foundations/SmoothPartStable.lean) |
| 263 | 78 | `Formalism` | [Formalism.LocalToGlobal.IndefiniteReal.IndefiniteWeightData](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/IndefiniteReal/IndefiniteWeightData.lean) |
| 259 | 166 | `ReciprocityTheory` | [ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.FundamentalDomains.Signature](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/FundamentalDomains/Signature.lean) |
| 232 | 115 | `Development` | [Development.AbelianVarietyTheory.Definitions.Foundations.MatrixMeasurableSpace](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/Foundations/MatrixMeasurableSpace.lean) |
| 188 | 362 | `Formalism` | [Formalism.UnipotentAdelicQuotients.SWXSDefs](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/UnipotentAdelicQuotients/SWXSDefs.lean) |
| 187 | 285 | `Development` | [Development.AbelianVarietyTheory.Definitions.Foundations.IsIwasawaOfIsCompact](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/Foundations/IsIwasawaOfIsCompact.lean) |

---

## 2. Stratigraphic Layering Across Top-Level Theories

The mathematical domains stratify naturally into five functional layers from the apex down to the base:

1. **Apex & Analytic Reflection Layer (`(root)`, `Formalism/GammaFactorNonvanishing`):** Converts universal right half-plane nonvanishing (`EveryCharacter`) into RH and GRH via Euler-factor stripping (`ClaimStrip`) and functional-equation reflection (`CritLine`, `RhOfRight`).
2. **Upper Automorphic & Positivity Synthesis (`PositivityTheory`, upper `Development`):** Constructs parallel weight-one Hilbert Eisenstein series, Rankin–Selberg zeta integrals, local–global Galois representations, modularity-lifting patching reductions, and windowed Chebyshev character boxes.
3. **Core Geometric & Representation-Theoretic Engine (`Development/AbelianVarietyTheory`, `Development/AutomorphicSpectrum`, `Development/WeilBound`, `CompanionTheory`):** Develops polarized abelian schemes, de Rham and crystalline comparisons, Moriwaki arithmetic bigness, Harish-Chandra discrete series characters (`DSInfCharCap`), and Flath factorizations.
4. **Specification & Harmonic-Analytic Infrastructure (`Formalism`):** Provides local-to-global theta-lift stage contracts (`LinksStage`), differential operator chart-independence, the master CM host package (`D7`), local Bloch–Kato orthogonality (`LocCoh`), and local Tate duality.
5. **Algebraic-Geometric, Cohomological & Arakelov Bedrock (`ReciprocityTheory`, `GroundTheory`, `Lemmata`):** Supplies PEL Shimura toroidal compactifications (`UniformisationConclusion`), uniqueness of Mumford uniformisations (`UnifUniqSt`), polarized abelian scheme laws, Arakelov Bost–Zhang slope bounds (`KernelsLattice`), Whittaker multiplicity one, and Poitou–Tate duality.

| Top Directory | Files | Lines | Leaves | Dist (min/med/max) | Height (med/max) |
|---|---:|---:|---:|---|---|
| `Development` | 41,263 | 11,657,315 | 1,425 | 1 / 6.0 / 15 | 25.0 / 92 |
| `Formalism` | 9,901 | 2,765,150 | 543 | 3 / 8.0 / 14 | 14.0 / 56 |
| `GroundTheory` | 5,217 | 868,235 | 378 | 2 / 5.0 / 13 | 5.0 / 41 |
| `ReciprocityTheory` | 2,393 | 494,752 | 224 | 2 / 7.0 / 14 | 5.0 / 47 |
| `CompanionTheory` | 685 | 178,444 | 26 | 3 / 6.0 / 13 | 13.0 / 69 |
| `PositivityTheory` | 226 | 44,166 | 3 | 3 / 6.0 / 7 | 34.0 / 45 |
| `Lemmata` | 149 | 6,857 | 92 | 4 / 8.0 / 12 | 0.0 / 10 |
| `(root)` | 2 | 76 | 1 | 0 / 0.5 / 1 | 46.5 / 93 |

### Major Cross-Theory Edge Flows

| Dependent (`src`) | Dependency (`dst`) | Edges |
|---|---|---:|
| `Development` | `Development` | 235,089 |
| `Formalism` | `Formalism` | 38,495 |
| `Development` | `Formalism` | 32,714 |
| `Development` | `ReciprocityTheory` | 22,116 |
| `GroundTheory` | `GroundTheory` | 14,676 |
| `ReciprocityTheory` | `ReciprocityTheory` | 7,228 |
| `Development` | `GroundTheory` | 6,514 |
| `CompanionTheory` | `CompanionTheory` | 2,129 |
| `GroundTheory` | `ReciprocityTheory` | 1,774 |
| `Development` | `CompanionTheory` | 1,423 |
| `CompanionTheory` | `Formalism` | 1,143 |
| `CompanionTheory` | `Development` | 1,034 |
| `ReciprocityTheory` | `Formalism` | 614 |
| `PositivityTheory` | `Development` | 597 |
| `Formalism` | `ReciprocityTheory` | 474 |

---

## 3. Dominator Bottleneck Spine (Cooper–Harvey–Kennedy)

In the dependency DAG rooted at `Main.lean`, a module $d$ **dominates** a module $u$ if *every* dependency path from `Main.lean` to $u$ must pass through $d$ (105 skeleton nodes with dominated subtree size `≥ 101`). Top mandatory bottlenecks:

| Rank | Dom Subtree | Depth | Dist / H | Top Dir | Module |
|---:|---:|---:|---:|---|---|
| 1 | 59,836 (100.0%) | 0 | 0 / 93 | `(root)` | [Main](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Main.lean) |
| 2 | 59,831 (99.992%) | 1 | 1 / 92 | `Development` | [Development.AutomorphicArithmetic.CharacterBoxes.MainConclusion](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean) |
| 3 | 31,637 (52.873%) | 2 | 2 / 89 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.EveryCharacterOfLiteratureOfVWin](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean) |
| 4 | 17,087 (28.556%) | 3 | 3 / 88 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.SiegelEisensteinSecondTermHypotheses](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/SiegelEisensteinSecondTermHypotheses.lean) |
| 5 | 4,455 (7.445%) | 2 | 2 / 91 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.VwinOfRow](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean) |
| 6 | 3,679 (6.148%) | 3 | 3 / 79 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.TopCovolSlim2Use](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolSlim2Use.lean) |
| 7 | 3,598 (6.013%) | 4 | 4 / 87 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.HypothesesNonemptyOfUnramifiedExponents](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/HypothesesNonemptyOfUnramifiedExponents.lean) |
| 8 | 3,153 (5.269%) | 2 | 2 / 81 | `Development` | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.GeometricRealizationOfWeightOne](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean) |
| 9 | 2,298 (3.84%) | 4 | 4 / 74 | `Development` | [Development.WeilBound.CoreStatements.AutomorphicKernels.MoriwakiBigness.HilbertSamuelApplications.AhSlimU](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/AhSlimU.lean) |
| 10 | 2,281 (3.812%) | 5 | 5 / 73 | `Development` | [Development.WeilBound.CoreStatements.AutomorphicKernels.MoriwakiBigness.HilbertSamuelApplications.DeepStROfUse](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/DeepStROfUse.lean) |
| 11 | 1,409 (2.355%) | 6 | 6 / 72 | `Development` | [Development.WeilBound.CoreStatements.AutomorphicKernels.MoriwakiBigness.HilbertSamuelApplications.GoodTowerVolumeTheoremBis](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/GoodTowerVolumeTheoremBis.lean) |
| 12 | 1,336 (2.233%) | 3 | 3 / 77 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.ToroidalCompactificationFanLogKodairaSpencerIso](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/ToroidalCompactificationFanLogKodairaSpencerIso.lean) |
| 13 | 1,174 (1.962%) | 4 | 4 / 76 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.RigidBoundaryChartsForFanUnitaryDatumStatement](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/RigidBoundaryChartsForFanUnitaryDatumStatement.lean) |
| 14 | 1,106 (1.848%) | 5 | 5 / 62 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.LinkROfIsLinked](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/LinkROfIsLinked.lean) |
| 15 | 887 (1.482%) | 4 | 4 / 81 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.SurjectiveAndLowWeightOfUnramifiedExponents](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/SurjectiveAndLowWeightOfUnramifiedExponents.lean) |
| 16 | 744 (1.243%) | 5 | 5 / 86 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.MemberBundlesLargeUnramifiedExponents](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/MemberBundlesLargeUnramifiedExponents.lean) |
| 17 | 744 (1.243%) | 4 | 4 / 78 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.TopCovolG](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolG.lean) |
| 18 | 664 (1.11%) | 4 | 4 / 82 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.OpenOrbitOfUnramifiedExponents](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/OpenOrbitOfUnramifiedExponents.lean) |
| 19 | 639 (1.068%) | 3 | 3 / 80 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.KatoTwoWOfPublishedH](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/KatoTwoWOfPublishedH.lean) |
| 20 | 606 (1.013%) | 5 | 5 / 85 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.LinkNFam](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/LinkNFam.lean) |
| 21 | 601 (1.004%) | 4 | 4 / 50 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.KatoQuadraticCharacters.SphericalDecomposition.SphAtTw](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/SphericalDecomposition/SphAtTw.lean) |
| 22 | 597 (0.998%) | 5 | 5 / 65 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.MainTheoremPublishedInputsThird](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/MainTheoremPublishedInputsThird.lean) |
| 23 | 558 (0.933%) | 5 | 5 / 49 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.KatoQuadraticCharacters.UnramifiedZeta.ZetaUr](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean) |
| 24 | 546 (0.912%) | 3 | 3 / 48 | `Development` | [Development.WeilBound.CoreStatements.TemperedRepresentationTheory.PoincareLelong.PoincareLelongInv](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/WeilBound/CoreStatements/TemperedRepresentationTheory/PoincareLelong/PoincareLelongInv.lean) |
| 25 | 520 (0.869%) | 6 | 6 / 64 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.MainTheoremFromPublishedResultsAltAltAltAltAlt](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/MainTheoremFromPublishedResultsAltAltAltAltAlt.lean) |
| 26 | 519 (0.867%) | 7 | 7 / 71 | `Development` | [Development.AutomorphicSpectrum.Proofs.DivisibilityProofs.VolumeTheoremOfInputs](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicSpectrum/Proofs/DivisibilityProofs/VolumeTheoremOfInputs.lean) |
| 27 | 505 (0.844%) | 7 | 7 / 63 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.FamAllQOfAllTrueStatement](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/FamAllQOfAllTrueStatement.lean) |
| 28 | 486 (0.812%) | 3 | 4 / 75 | `Development` | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.KunnethLefschetz.EtSideGood](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/KunnethLefschetz/EtSideGood.lean) |
| 29 | 459 (0.767%) | 5 | 5 / 75 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.RigidBoundaryChartsForFanOfUnitarySeparationStatement](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/RigidBoundaryChartsForFanOfUnitarySeparationStatement.lean) |
| 30 | 430 (0.719%) | 6 | 6 / 85 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.ExistsBaseLatticeOfPrime](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/ExistsBaseLatticeOfPrime.lean) |

---

## 4. Critical Dependency Chain & Longest Intra-Directory Chains

The longest dependency chain spans **93 edges (94 modules)** across **405** total max-length paths, with **56** single-node chokes and **38** branching heights.

| Top Directory | Max Intra-Dir Edges | Start → End |
|---|---:|---|
| `Development` | 76 | `MainConclusion` → `SpanSingletonEqTopIffIsUnitOfIsBaseChange` |
| `Formalism` | 56 | `LinkGConcreteNoKer` → `Complexify` |
| `GroundTheory` | 41 | `NonemptyOfNatCastMemOfNeOne` → `ProfiniteInteger` |
| `ReciprocityTheory` | 36 | `FormalDegreeConstantDiscrete` → `IsInfUnitary` |
| `CompanionTheory` | 16 | `Imports` → `IsEulerProd` |
| `PositivityTheory` | 6 | `HilbertEisensteinWeightOneHolds` → `SSmooth` |
| `(root)` | 1 | `Main` → `Statements` |
| `Lemmata` | 1 | `Denom` → `ExistsNatMulIsIntegral` |

---

## 5. Top Cross-Theory Bridges & Path-Stress Hubs

Modules ranked by **Brandes weighted cross-directory betweenness** (`brandes_weighted_cross_top`) alongside cross-directory fan-in × fan-out (`Cross Fan`), identifying high-stress interfaces connecting distinct top-level mathematical theories:

| Rank | Brandes Cross-Dir | Cross Fan (In×Out) | In / Out | Top Dir | Module |
|---:|---:|---:|---:|---|---|
| 1 | 2,775,151.9 | 0 | 311 / 16 | `Formalism` | [Formalism.LocalRingCardinality.RankBoundMonotoneInDimension](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalRingCardinality/RankBoundMonotoneInDimension.lean) |
| 2 | 1,426,332.1 | 0 | 8 / 23 | `Development` | [Development.AbelianVarietyTheory.Definitions.AutomorphicMembership.CmHostRootComplexEqPmSqrt](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/CmHostRootComplexEqPmSqrt.lean) |
| 3 | 1,256,633.4 | 0 | 10 / 7 | `Development` | [Development.AbelianVarietyTheory.Definitions.AutomorphicMembership.MultiplicationLatticeSecond](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/MultiplicationLatticeSecond.lean) |
| 4 | 1,188,099.9 | 0 | 23 / 2 | `Development` | [Development.AbelianVarietyTheory.Definitions.AutomorphicMembership.ExistsIvDOfDefinite](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/ExistsIvDOfDefinite.lean) |
| 5 | 1,130,271.9 | 0 | 125 / 43 | `Formalism` | [Formalism.SatakeDualWeyl.KpqSubgroupCompact](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean) |
| 6 | 1,073,549.1 | 0 | 986 / 8 | `Formalism` | [Formalism.LocalToGlobal.IndefiniteReal.LinksDefs](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/IndefiniteReal/LinksDefs.lean) |
| 7 | 1,004,430.0 | 0 | 9 / 13 | `Formalism` | [Formalism.LocalToGlobal.IndefiniteReal.TrISepWith](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/IndefiniteReal/TrISepWith.lean) |
| 8 | 968,557.4 | 0 | 149 / 16 | `Development` | [Development.AbelianVarietyTheory.Definitions.Divisors.TupleReadBaseTupleEqFamily](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/Divisors/TupleReadBaseTupleEqFamily.lean) |
| 9 | 965,847.4 | 0 | 300 / 1 | `Development` | [Development.AbelianVarietyTheory.Definitions.AutomorphicMembership.SumMulEqZeroOfSumToReal](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/SumMulEqZeroOfSumToReal.lean) |
| 10 | 848,113.4 | 0 | 416 / 8 | `Formalism` | [Formalism.LocalRingCardinality.RhoDetPrimeEqMuTildeMulChiPow](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean) |
| 11 | 826,299.2 | 0 | 2 / 2 | `Formalism` | [Formalism.LocalToGlobal.IndefiniteReal.CxToPkgFamIn](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/IndefiniteReal/CxToPkgFamIn.lean) |
| 12 | 821,279.0 | 0 | 17 / 7 | `Formalism` | [Formalism.LocalToGlobal.SiegelLatticeTheory.FlagStabilizerTensors.SpectralTiesReal](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/SiegelLatticeTheory/FlagStabilizerTensors/SpectralTiesReal.lean) |
| 13 | 776,687.2 | 0 | 4 / 4 | `Formalism` | [Formalism.LocalToGlobal.IndefiniteReal.RealTB](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/IndefiniteReal/RealTB.lean) |
| 14 | 755,699.2 | 0 | 10 / 18 | `Formalism` | [Formalism.LocalToGlobal.Divisibility.DivisionHeightBoundStatement](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalToGlobal/Divisibility/DivisionHeightBoundStatement.lean) |
| 15 | 672,646.6 | 0 | 9 / 24 | `Development` | [Development.AbelianVarietyTheory.Proofs.UnitaryExistence.ExistsUnfFamily](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AbelianVarietyTheory/Proofs/UnitaryExistence/ExistsUnfFamily.lean) |

