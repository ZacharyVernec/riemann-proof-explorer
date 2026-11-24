# Proof Spine, Bottlenecks & Critical Dependency Chain (original-2026-11-20)

This report analyzes the logical dependency DAG of the proof—tracing its mandatory mathematical bottlenecks (dominator tree rooted at [Main.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean)), its deepest critical dependency chain from the final RH/GRH theorems down to foundational leaves, and the key bridge modules connecting the major theories (interactive explorer in [spine_dashboard.html](spine_dashboard.html)).

> **Edge Orientation Convention:** Throughout this report, a directed edge `(u, v)` means module `u` **depends on** `v` (`u` imports `v`). Hence `Main.lean` is the unique root/source at the apex of the proof, and foundational leaf modules sit at the base (`height = 0`).

---

## Executive Audit Summary

| Metric | Value |
|---|---:|
| Total Lean modules in codebase | 175,187 |
| Modules reachable from `Main.lean` | 175,187 |
| Unreachable / standalone modules excluded | 0 |
| Internal dependency edges (reachable DAG) | 753,261 |
| Strict DAG verified (`is_dag`) | Yes |
| Shortest distance span from `Main.lean` | 0 – 43 |
| Critical dependency chain length | 202 edges / 203 modules |
| Critical max-length paths | 1,008 |
| Foundational leaf modules (`out_degree = 0`) | 5,927 (615,171 lines) |
| Log10 total `Main → Leaf` dependency paths | 22.989 |

---

## 1. Entry Funnel & Foundational Base

### 1.1 Entry Funnel Near `Main.lean` (`dist ≤ 3`)

| Dist | Module | Dom Subtree | Out-Deg | Mathematical Role |
|---:|---|---:|---:|---|
| 0 | [Main](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean) | 175,187 | 2 | Final root export proving riemannHypothesis, riemannZeta_eq_zero_re, LFunction_ne_zero_of_half_lt_re, LFunction_eq_zero_re, and LFunction_eq_zero_re_of_isPrimitive. |
| 1 | [Supplements.Kernels.MainTheoremsAll](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsAll.lean) | 175,185 | 2 | Apex junction merging MainTheoremsCritical and SmallClassNumbers.CorGKOf; dominates the entire proof tree below Main. |
| 1 | [Statements](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Statements.lean) | 1 | 0 | `RiemannZetaZerosOnLine`, `DirichletLNonvanishingRightOfHalf`, `DirichletLZerosOnLine`, `PrimitiveDirichletLZerosOnLine` |
| 2 | [Supplements.Kernels.MainTheoremsCritical](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsCritical.lean) | 4,482 | 4 | Assembles MainTheorems with SmallClassNumbers (ClassNumberThree, LenEqZeroIff, OnePoint). |
| 2 | [Development.AutomorphicArithmetic.AutomorphicVarieties.SmallClassNumbers.CorGKOf](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean) | 1 | 4 |  |
| 3 | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.RowSrc](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/RowSrc.lean) | 13,055 | 2 | Bridges theta-kernel Parseval input (tLiftK) into galoisLocalGlobalStrong_recParameter (Row0b recT); shared by MainConclusion and CorGKOf. |
| 3 | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.TopMainZj](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/TopMainZj.lean) | 8,050 | 11 | Constructs LitLocAlt, LiteratureAutomorphyHypothesis, and LiteratureCMHypothesis from OpenImageCondition to build VWin. |
| 3 | [Supplements.Kernels.MainTheorems](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheorems.lean) | 4,479 | 3 | Exposes allChi, rhOfAll, critAll, and claimAll from CritLine, ClaimStrip, and MainConclusion. |
| 3 | [Development.AutomorphicArithmetic.Foundations.BaseChangeIdentities.DefiniteNHolds](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/BaseChangeIdentities/DefiniteNHolds.lean) | 14 | 3 |  |
| 3 | [Development.AutomorphicArithmetic.AutomorphicVarieties.SmallClassNumbers.ClassNumberThree](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/ClassNumberThree.lean) | 1 | 5 |  |
| 3 | [Development.AutomorphicArithmetic.AutomorphicVarieties.SmallClassNumbers.LenEqZeroIff](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/LenEqZeroIff.lean) | 1 | 1 |  |
| 3 | [Development.AutomorphicArithmetic.AutomorphicVarieties.SmallClassNumbers.OnePoint](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/OnePoint.lean) | 1 | 1 |  |

### 1.2 Top Foundational Leaves (`out_degree = 0`)

There are **5,927** foundational leaf modules (`615,171` lines, `21,610` theorems, `13,624` definitions). Modules with zero external imports: `0`.

| In-Deg | Lines | Top Directory | Module |
|---:|---:|---|---|
| 2,242 | 1 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.CohomologicalCsdTempered](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/CohomologicalCsdTempered.lean) |
| 568 | 130 | `ReciprocityTheory` | [ReciprocityTheory.AnalyticForms.RegularLocalRings.FinalTheorems](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean) |
| 520 | 1 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.DiscreteSeriesCoefficientsCuspidal](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/DiscreteSeriesCoefficientsCuspidal.lean) |
| 344 | 26 | `Development` | [Development.ResolutionOfSingularities.Foundations.BlowupUniversalProperty](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/ResolutionOfSingularities/Foundations/BlowupUniversalProperty.lean) |
| 277 | 161 | `Development` | [Development.AbelianVarietyTheory.Definitions.NonGaloisDescent.UnitLemmaGroup](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/UnitLemmaGroup.lean) |
| 252 | 39 | `ReciprocityTheory` | [ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.BirationalGeometry.ToroidalCompactification.IsCompletedStrictHens](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsCompletedStrictHens.lean) |
| 242 | 65 | `Development` | [Development.AbelianVarietyTheory.Definitions.Divisors.HasQIff](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/Divisors/HasQIff.lean) |
| 209 | 104 | `Development` | [Development.AbelianVarietyTheory.Definitions.AdelicHermitianForms.AdelicPair](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/AdelicHermitianForms/AdelicPair.lean) |
| 208 | 24 | `Formalism` | [Formalism.LocalToGlobal.IndefiniteForms.IndefiniteTree.RealCubicMeans.LogMeanShares.LogMeanStatements.HSClaim](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalToGlobal/IndefiniteForms/IndefiniteTree/RealCubicMeans/LogMeanShares/LogMeanStatements/HSClaim.lean) |
| 195 | 201 | `ReciprocityTheory` | [ReciprocityTheory.ReductiveGroups.ArithmeticGeometry.ExtensionDescent.ChartPullbacks.UniversalCharts.LePreimageOfNil](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/ChartPullbacks/UniversalCharts/LePreimageOfNil.lean) |
| 187 | 1 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.HodgeBundleWeights.TamagawaNumberSpecialUnitary](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/HodgeBundleWeights/TamagawaNumberSpecialUnitary.lean) |
| 182 | 123 | `GroundTheory` | [GroundTheory.HeightsAndTheta.Heights.KernelsLattice](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean) |
| 166 | 93 | `Development` | [Development.AbelianVarietyTheory.Definitions.CommutativeAlgebra.InvariantSubspaceMobiusInverseRecEqOfFinrankLt](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/CommutativeAlgebra/InvariantSubspaceMobiusInverseRecEqOfFinrankLt.lean) |
| 158 | 32 | `Development` | [Development.AbelianVarietyTheory.Definitions.CommutativeAlgebra.AbByPOfComm](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/CommutativeAlgebra/AbByPOfComm.lean) |
| 158 | 11 | `Development` | [Development.AbelianVarietyTheory.PublishedTheorems.GaloisCohomology₂.ChevalleyUnits](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/PublishedTheorems/GaloisCohomology₂/ChevalleyUnits.lean) |

### 1.3 `BuildAid` Modules (5)

- [BuildAid.D1](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/BuildAid/D1.lean) (dist 13, in-degree 3)
- [BuildAid.D2](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/BuildAid/D2.lean) (dist 12, in-degree 4)
- [BuildAid.D3](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/BuildAid/D3.lean) (dist 8, in-degree 25)
- [BuildAid.D4](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/BuildAid/D4.lean) (dist 8, in-degree 5)
- [BuildAid.D5](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/BuildAid/D5.lean) (dist 19, in-degree 1)

---

## 2. Stratigraphic Layering Across Top-Level Theories

The mathematical domains stratify naturally into five functional layers from the apex down to the base:

1. **Apex & Analytic Reflection Layer (`(root)`, `Supplements`, `Formalism/GammaFactorNonvanishing`):** Converts universal right half-plane nonvanishing (`EveryCharacter`) into RH and GRH via Euler-factor stripping (`ClaimStrip`) and functional-equation reflection (`CritLine`, `RhOfRight`).
2. **Upper Automorphic & Positivity Synthesis (`PositivityTheory`, upper `Development`):** Constructs parallel weight-one Hilbert Eisenstein series, Rankin–Selberg zeta integrals, local–global Galois representations, modularity-lifting patching reductions, and windowed Chebyshev character boxes.
3. **Core Geometric & Representation-Theoretic Engine (`Development/AbelianVarietyTheory`, `Development/AutomorphicSpectrum`, `Development/WeilBound`, `CompanionTheory`):** Develops polarized abelian schemes, de Rham and crystalline comparisons, Moriwaki arithmetic bigness, Harish-Chandra discrete series characters (`DSInfCharCap`), and Flath factorizations.
4. **Specification & Harmonic-Analytic Infrastructure (`Formalism`):** Provides local-to-global theta-lift stage contracts (`LinksStage`), differential operator chart-independence, the master CM host package (`D7`), local Bloch–Kato orthogonality (`LocCoh`), and local Tate duality.
5. **Algebraic-Geometric, Cohomological & Arakelov Bedrock (`ReciprocityTheory`, `GroundTheory`, `Lemmata`):** Supplies PEL Shimura toroidal compactifications (`UniformisationConclusion`), uniqueness of Mumford uniformisations (`UnifUniqSt`), polarized abelian scheme laws, Arakelov Bost–Zhang slope bounds (`KernelsLattice`), Whittaker multiplicity one, and Poitou–Tate duality.

| Top Directory | Files | Lines | Leaves | Dist (min/med/max) | Height (med/max) |
|---|---:|---:|---:|---|---|
| `Development` | 141,928 | 12,232,663 | 4,265 | 2 / 14.0 / 43 | 48.0 / 198 |
| `Formalism` | 18,254 | 3,200,748 | 766 | 4 / 13.0 / 43 | 22.0 / 93 |
| `GroundTheory` | 8,507 | 1,119,138 | 448 | 5 / 10.0 / 32 | 8.0 / 68 |
| `ReciprocityTheory` | 3,845 | 563,016 | 256 | 6 / 12.0 / 36 | 10.0 / 76 |
| `CompanionTheory` | 2,027 | 194,218 | 35 | 5 / 12.0 / 30 | 32.0 / 114 |
| `PositivityTheory` | 449 | 55,130 | 6 | 6 / 10.0 / 13 | 97.0 / 111 |
| `Lemmata` | 167 | 9,232 | 145 | 8 / 13.0 / 25 | 0.0 / 17 |
| `BuildAid` | 5 | 20 | 5 | 8 / 12.0 / 19 | 0.0 / 0 |
| `Supplements` | 3 | 22 | 0 | 1 / 2.0 / 3 | 200.0 / 201 |
| `(root)` | 2 | 28 | 1 | 0 / 0.5 / 1 | 101.0 / 202 |

### Major Cross-Theory Edge Flows

| Dependent (`src`) | Dependency (`dst`) | Edges |
|---|---|---:|
| `Development` | `Development` | 577,034 |
| `Formalism` | `Formalism` | 44,412 |
| `Development` | `Formalism` | 41,857 |
| `Development` | `ReciprocityTheory` | 38,051 |
| `GroundTheory` | `GroundTheory` | 20,797 |
| `ReciprocityTheory` | `ReciprocityTheory` | 8,711 |
| `Development` | `GroundTheory` | 7,532 |
| `CompanionTheory` | `CompanionTheory` | 5,034 |
| `Development` | `CompanionTheory` | 1,874 |
| `CompanionTheory` | `Development` | 1,437 |
| `GroundTheory` | `ReciprocityTheory` | 1,161 |
| `Development` | `PositivityTheory` | 1,057 |
| `PositivityTheory` | `PositivityTheory` | 773 |
| `CompanionTheory` | `Formalism` | 762 |
| `Lemmata` | `Formalism` | 634 |

---

## 3. Dominator Bottleneck Spine (Cooper–Harvey–Kennedy)

In the dependency DAG rooted at `Main.lean`, a module $d$ **dominates** a module $u$ if *every* dependency path from `Main.lean` to $u$ must pass through $d$ (242 skeleton nodes with dominated subtree size `≥ 300`). Top mandatory bottlenecks:

| Rank | Dom Subtree | Depth | Dist / H | Top Dir | Module |
|---:|---:|---:|---:|---|---|
| 1 | 175,187 (100.0%) | 0 | 0 / 202 | `(root)` | [Main](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean) |
| 2 | 175,185 (99.999%) | 1 | 1 / 201 | `Supplements` | [Supplements.Kernels.MainTheoremsAll](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsAll.lean) |
| 3 | 13,055 (7.452%) | 2 | 3 / 197 | `Development` | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.RowSrc](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/RowSrc.lean) |
| 4 | 12,272 (7.005%) | 3 | 4 / 196 | `Development` | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GaloisRepresentationsOfThetaLift](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GaloisRepresentationsOfThetaLift.lean) |
| 5 | 10,802 (6.166%) | 4 | 5 / 195 | `Development` | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.WeightOneGeometricRealization](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/WeightOneGeometricRealization.lean) |
| 6 | 10,430 (5.954%) | 5 | 6 / 194 | `Development` | [Development.AutomorphicArithmetic.Foundations.GaloisRepresentations.IntegralStructures.GeometricFlagBases.GeometricRealizationOfWeightOne](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean) |
| 7 | 10,065 (5.745%) | 2 | 5 / 167 | `Development` | [Development.AutomorphicArithmetic.CharacterBoxes.RiemannHypothesisOfEveryCharacter](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/RiemannHypothesisOfEveryCharacter.lean) |
| 8 | 8,050 (4.595%) | 2 | 3 / 170 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.TopMainZj](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/TopMainZj.lean) |
| 9 | 7,920 (4.521%) | 3 | 4 / 148 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.ThresholdArguments.DenseThresholdCases.WindowBoundOfLiteratureLevel](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/WindowBoundOfLiteratureLevel.lean) |
| 10 | 6,076 (3.468%) | 2 | 7 / 141 | `Development` | [Development.WeilBound.CoreStatements.AutomorphicKernels.MoriwakiBigness.HilbertSamuelApplications.TopCovolSlim2Use](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/TopCovolSlim2Use.lean) |
| 11 | 5,695 (3.251%) | 3 | 6 / 157 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfSlimAndHyp](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeOfSlimAndHyp.lean) |
| 12 | 4,897 (2.795%) | 4 | 7 / 156 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfHeightPrintsStatement](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeOfHeightPrintsStatement.lean) |
| 13 | 4,896 (2.795%) | 5 | 8 / 155 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeOfHeightHyp](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeOfHeightHyp.lean) |
| 14 | 4,482 (2.558%) | 2 | 2 / 200 | `Supplements` | [Supplements.Kernels.MainTheoremsCritical](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsCritical.lean) |
| 15 | 4,479 (2.557%) | 3 | 3 / 199 | `Supplements` | [Supplements.Kernels.MainTheorems](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheorems.lean) |
| 16 | 4,474 (2.554%) | 4 | 4 / 198 | `Development` | [Development.AutomorphicArithmetic.CharacterBoxes.MainConclusion](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean) |
| 17 | 4,472 (2.553%) | 5 | 5 / 171 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.EveryCharacterOfLiteratureOfVWin](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean) |
| 18 | 3,937 (2.247%) | 6 | 6 / 170 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.SiegelEisensteinSecondTermHypotheses](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/SiegelEisensteinSecondTermHypotheses.lean) |
| 19 | 3,746 (2.138%) | 3 | 11 / 129 | `Development` | [Development.AutomorphicSpectrum.Proofs.GeometryProofs.GoodTowerVolumeTheoremAlt](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicSpectrum/Proofs/GeometryProofs/GoodTowerVolumeTheoremAlt.lean) |
| 20 | 3,742 (2.136%) | 4 | 12 / 128 | `Development` | [Development.AutomorphicSpectrum.Proofs.GeometryProofs.FinalTheoremOfInputsRightStatement](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicSpectrum/Proofs/GeometryProofs/FinalTheoremOfInputsRightStatement.lean) |
| 21 | 3,741 (2.135%) | 5 | 13 / 127 | `Development` | [Development.AutomorphicSpectrum.Proofs.GeometryProofs.FinalTheoremOfInputsRight](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicSpectrum/Proofs/GeometryProofs/FinalTheoremOfInputsRight.lean) |
| 22 | 2,935 (1.675%) | 6 | 14 / 126 | `Development` | [Development.AutomorphicSpectrum.Proofs.DivisibilityProofs.GoodTowerVolumeTheoremStatement](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicSpectrum/Proofs/DivisibilityProofs/GoodTowerVolumeTheoremStatement.lean) |
| 23 | 2,934 (1.675%) | 7 | 15 / 125 | `Development` | [Development.AutomorphicSpectrum.Proofs.DivisibilityProofs.GoodTowerVolumeTheorem](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicSpectrum/Proofs/DivisibilityProofs/GoodTowerVolumeTheorem.lean) |
| 24 | 2,047 (1.168%) | 4 | 6 / 121 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.ModularityArgument.KatoQuadraticCharacters.UnramifiedZeta.ZetaUr](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean) |
| 25 | 1,942 (1.109%) | 2 | 5 / 166 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.ToroidalCompactificationFanLogKodairaSpencerIso](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/ToroidalCompactificationFanLogKodairaSpencerIso.lean) |
| 26 | 1,854 (1.058%) | 7 | 7 / 141 | `Development` | [Development.AutomorphicArithmetic.ThetaCorrespondence.ThetaPairLifts.ThirdPlaceSeries.HypothesesNonemptyOfUnramifiedExponents](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/HypothesesNonemptyOfUnramifiedExponents.lean) |
| 27 | 1,672 (0.954%) | 6 | 9 / 142 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.QuotingOfPublishedInputsStatement](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/QuotingOfPublishedInputsStatement.lean) |
| 28 | 1,671 (0.954%) | 7 | 10 / 141 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.KnownOfPublishedInputs](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/KnownOfPublishedInputs.lean) |
| 29 | 1,633 (0.932%) | 8 | 11 / 140 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.KnownOfLieSlope](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/KnownOfLieSlope.lean) |
| 30 | 1,503 (0.858%) | 6 | 9 / 154 | `Development` | [Development.AbelianVarietyTheory.Proofs.DivisorProofs.CovolumeFromHeightTheoremsStatement](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeFromHeightTheoremsStatement.lean) |

---

## 4. Critical Dependency Chain & Longest Intra-Directory Chains

The longest dependency chain spans **202 edges (203 modules)** across **1,008** total max-length paths, with **182** single-node chokes and **21** branching heights.

| Top Directory | Max Intra-Dir Edges | Start → End |
|---|---:|---|
| `Development` | 174 | `CorGKOf` → `WeightAddLeOfMemSupportDividedContraction` |
| `Formalism` | 93 | `SiteGoodPrimeTorsion` → `StatementA` |
| `ReciprocityTheory` | 72 | `FormalDegreeConstantDiscrete` → `IsInfUnitary` |
| `GroundTheory` | 68 | `FieldNumbersProjectionFormulaDegree` → `ProfiniteInteger` |
| `CompanionTheory` | 40 | `Imports` → `IsEulerProd` |
| `PositivityTheory` | 11 | `FourierExpansionCentral` → `AdFormOf` |
| `Supplements` | 2 | `MainTheoremsAll` → `MainTheorems` |
| `(root)` | 1 | `Main` → `Statements` |
| `BuildAid` | 0 | `D1` → `D1` |
| `Lemmata` | 0 | `AddValProd` → `AddValProd` |

---

## 5. Top Cross-Theory Bridges & Path-Stress Hubs

Modules ranked by **Brandes weighted cross-directory betweenness** (`brandes_weighted_cross_top`) alongside cross-directory fan-in × fan-out (`Cross Fan`), identifying high-stress interfaces connecting distinct top-level mathematical theories:

| Rank | Brandes Cross-Dir | Cross Fan (In×Out) | In / Out | Top Dir | Module |
|---:|---:|---:|---:|---|---|
| 1 | 48,663,966.6 | 0 | 122 / 53 | `Development` | [Development.AbelianVarietyTheory.Definitions.AutomorphicMembership.Brauer](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean) |
| 2 | 46,082,869.4 | 0 | 6 / 51 | `Development` | [Development.AbelianVarietyTheory.Definitions.AutomorphicMembership.ParMem](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/ParMem.lean) |
| 3 | 29,865,457.9 | 0 | 76 / 7 | `Development` | [Development.AutomorphicArithmetic.AutomorphicVarieties.AutomorphicForms.Hypotheses2](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/Hypotheses2.lean) |
| 4 | 24,385,412.8 | 0 | 31 / 9 | `Development` | [Development.AbelianVarietyTheory.Definitions.GlobalTwisting.APerTw](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/GlobalTwisting/APerTw.lean) |
| 5 | 18,791,986.9 | 0 | 431 / 11 | `Formalism` | [Formalism.LocalRingCardinality.RankBoundMonotoneInDimension](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalRingCardinality/RankBoundMonotoneInDimension.lean) |
| 6 | 16,179,729.8 | 0 | 20 / 19 | `Development` | [Development.AbelianVarietyTheory.Definitions.GlobalTwisting.CountsIrreducibilityConstants](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/GlobalTwisting/CountsIrreducibilityConstants.lean) |
| 7 | 16,011,237.7 | 0 | 11 / 23 | `Development` | [Development.AbelianVarietyTheory.Definitions.AutomorphicMembership.CmHostRootComplexEqPmSqrt](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/CmHostRootComplexEqPmSqrt.lean) |
| 8 | 14,215,908.3 | 0 | 19 / 370 | `Formalism` | [Formalism.HermitianCurvature.HeisenbergConjugationMeasurePreserving](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/HermitianCurvature/HeisenbergConjugationMeasurePreserving.lean) |
| 9 | 14,129,231.8 | 0 | 2 / 6 | `Formalism` | [Formalism.LocalToGlobal.SiegelLatticeTheory.CokernelGLCounts.RankPointCounts.KloostermanDiagonalOfType](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalToGlobal/SiegelLatticeTheory/CokernelGLCounts/RankPointCounts/KloostermanDiagonalOfType.lean) |
| 10 | 13,640,967.8 | 0 | 9 / 10 | `Formalism` | [Formalism.LocalToGlobal.SiegelLatticeTheory.FlagStabilizerTensors.SpectralTiesReal](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalToGlobal/SiegelLatticeTheory/FlagStabilizerTensors/SpectralTiesReal.lean) |
| 11 | 13,548,617.3 | 0 | 11 / 3 | `Formalism` | [Formalism.LocalToGlobal.SiegelLatticeTheory.FlagStabilizerTensors.RowsPos](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalToGlobal/SiegelLatticeTheory/FlagStabilizerTensors/RowsPos.lean) |
| 12 | 13,470,267.6 | 0 | 1 / 17 | `Formalism` | [Formalism.LocalToGlobal.SiegelLatticeTheory.CokernelGLCounts.RankPointCounts.MainEqHolds](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalToGlobal/SiegelLatticeTheory/CokernelGLCounts/RankPointCounts/MainEqHolds.lean) |
| 13 | 11,537,573.3 | 0 | 13 / 13 | `Formalism` | [Formalism.LocalToGlobal.IndefiniteReal.TrISepWith](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalToGlobal/IndefiniteReal/TrISepWith.lean) |
| 14 | 11,462,974.4 | 0 | 1 / 7 | `Formalism` | [Formalism.LocalToGlobal.SiegelLatticeTheory.FlagStabilizerTensors.TheoremS](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalToGlobal/SiegelLatticeTheory/FlagStabilizerTensors/TheoremS.lean) |
| 15 | 10,449,634.8 | 0 | 28 / 8 | `Development` | [Development.AbelianVarietyTheory.Definitions.LatticeFrames.MiPinnedWithFinIff](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Definitions/LatticeFrames/MiPinnedWithFinIff.lean) |

