# Cross-Boundary Interface & Compression Analysis

This report extracts and analyzes the cross-boundary public interfaces of the Lean 4 codebase in [`lean/src`](file:///home/ubuntu/riemann_proof/lean/src), built from [`analysis/data/graph.sqlite`](file:///home/ubuntu/riemann_proof/analysis/data/graph.sqlite) and verified directly against the `.lean` source files.

An **interface file** of a directory `D` is defined as any `.lean` module inside `D` that is directly imported by at least one module strictly outside `D`. The **compression ratio** is `interface_files / total_files` (smaller ratios indicate tighter encapsulation behind narrow boundary contracts).

## 1. Executive Summary & Architectural Findings

- **Global Scale & Boundary Compression:** Out of **175,187 files** (17,374,215 lines; 100% reachable from `Main.lean` in a strict DAG with 753,261 internal edges), only **9,261 files (5.29%)** cross a top-level directory boundary (96,497 cross-boundary edges), and **27,175 files (15.51%)** cross a depth-2 sub-theory boundary (145,414 cross-boundary edges across 330 depth-2 buckets).
- **Extreme Encapsulation of `Development` (118.8x compression):** `Development` contains **141,928 files** (81.0% of the repository, 12.23M lines), yet exports only **1,195 interface files** (`0.0084` compression ratio, `0.0132` by lines) outside `Development`. Its final proof outputs funnel through a 6-file bottleneck into `Supplements/Kernels/` and from there via a single barrel file (`MainTheoremsAll.lean`) into `Main.lean`.
- **`Formalism` & `ReciprocityTheory` as High-Traffic Specification Hubs:** Together, `Formalism` (**43,538** incoming external edges into 3,640 interface files) and `ReciprocityTheory` (**39,723** incoming external edges into 1,503 interface files) absorb **86.3%** of all cross-top-directory imports (`83,261 / 96,497`). Reading the highest fan-in files reveals that they primarily export **mathematical specification packages (`Prop` predicates and `structure` contracts)**—such as `UniformisationConclusion`, `PELUnif`, `UnifUniqSt`, `HeckeKer`, `Laws`, `Laws2`, `LocCoh`, `D7`, and `LocalTateDualityK`—rather than raw leaf lemmas.
- **Depth-2 Sub-Theory Extremes:** Among depth-2 sub-theories with at least 20 files, the tightest compression occurs in `Formalism/AdmissibleDesigns` (**4.30%**, 4/93), `Formalism/WachLatticeTwists` (**4.58%**, 12/262), `Development/AutomorphicArithmetic` (**5.56%**, 1,024/18,431), `ReciprocityTheory/Chebotarev` (**6.38%**, 3/47), `Development/ResolutionOfSingularities` (**7.62%**, 38/499), and `Development/AbelianVarietyTheory` (**9.58%**, 9,498/99,187). Conversely, foundational leaf toolkits such as `Lemmata/*` (**100.0%**, 167 single-file modules), `Formalism/FrobeniusOrbits` (**96.88%**), `Formalism/RealPlaceAnalysis` (**90.74%**), and `Formalism/HarderNarasimhan` (**90.70%**) expose nearly all their modules externally.
- **Bidirectional Directory Coupling within a Strict Module DAG:** Although module imports form a strict acyclic DAG (`is_dag = true`), directories exhibit rich two-way interdependence: `Development` heavily imports `Formalism` (41,857 edges) and `ReciprocityTheory` (38,051 edges), while `CompanionTheory` imports `Development` (1,437 edges) and `PositivityTheory` imports `Development` (632 edges), and `Development` in turn imports `CompanionTheory` (1,874 edges) and `PositivityTheory` (1,057 edges).
- **Architectural Idioms Discovered in Source:** Direct reading uncovered thin 1-line re-export facades (`CompanionTheory/EightfoldTheory/VariationTheory/AutomorphicForms/Newform.lean`, imported 248 times by `Development`) and 4-line library-suggestion deny-list directives (`BuildAid/D1.lean`–`D5.lean`), illustrating how namespace facades and build-tuning hooks appear alongside mathematical theorem/definition interfaces.

## 2. Top-Level Directory Compression & Dependency Flow

| Top-Level Directory | Total Files | Interface Files | Compression Ratio | Compression Factor | Ext Import Edges (In) | Unique Ext Importers | Ext Outgoing Edges | Total Lines | Interface Lines (Ratio) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `Development` | 141,928 | 1,195 | 0.0084 (0.84%) | 118.77x | 2,385 | 1,009 | 90,406 | 12,232,663 | 161,151 (0.0132) |
| `Formalism` | 18,254 | 3,640 | 0.1994 (19.94%) | 5.01x | 43,538 | 20,792 | 704 | 3,200,748 | 953,895 (0.2980) |
| `GroundTheory` | 8,507 | 2,178 | 0.2560 (25.60%) | 3.91x | 7,709 | 3,678 | 1,230 | 1,119,138 | 367,642 (0.3285) |
| `ReciprocityTheory` | 3,845 | 1,503 | 0.3909 (39.09%) | 2.56x | 39,723 | 16,432 | 334 | 563,016 | 225,278 (0.4001) |
| `CompanionTheory` | 2,027 | 402 | 0.1983 (19.83%) | 5.04x | 1,878 | 1,005 | 2,421 | 194,218 | 43,014 (0.2215) |
| `PositivityTheory` | 449 | 170 | 0.3786 (37.86%) | 2.64x | 1,057 | 822 | 753 | 55,130 | 17,793 (0.3227) |
| `Lemmata` | 167 | 167 | 1.0000 (100.00%) | 1.00x | 168 | 153 | 641 | 9,232 | 9,232 (1.0000) |
| `BuildAid` | 5 | 5 | 1.0000 (100.00%) | 1.00x | 38 | 38 | 0 | 20 | 20 (1.0000) |
| `Supplements` | 3 | 1 | 0.3333 (33.33%) | 3.00x | 1 | 1 | 7 | 22 | 2 (0.0909) |
| `(root)` | 2 | 0 | 0.0000 (0.00%) | Apex (0 exports) | 0 | 0 | 1 | 28 | 0 (0.0000) |

> **Note on `(root)` and `Formalism` at depth 2:** At depth-1 (`top_dir`), `(root)` contains `Main.lean` and `Statements.lean`, with `0` external importers because `Main.lean` sits at the root of the DAG (`dist_from_main = 0`). At depth-2 (`depth2_dir`), `dir_stats` partitions root-level files directly inside `Formalism/*.lean` (9 files such as `Formalism/ZetaRealNonvanish.lean` and `Formalism/StatementOC.lean`) separately from `Formalism/<Subdir>` (107 subdirectories).

### Major Cross-Boundary Dependency Flows (`src` imports `dst`)

| Source Top-Dir | Target Top-Dir | Import Edges | Source Files | Target Interface Files |
|---|---|---:|---:|---:|
| `Development` | `Formalism` | 41,857 | 20,174 | 3,315 |
| `Development` | `ReciprocityTheory` | 38,051 | 15,393 | 1,302 |
| `Development` | `GroundTheory` | 7,532 | 3,591 | 2,152 |
| `Development` | `CompanionTheory` | 1,874 | 1,001 | 400 |
| `CompanionTheory` | `Development` | 1,437 | 604 | 623 |
| `GroundTheory` | `ReciprocityTheory` | 1,161 | 716 | 215 |
| `Development` | `PositivityTheory` | 1,057 | 822 | 170 |
| `CompanionTheory` | `Formalism` | 762 | 388 | 336 |
| `Lemmata` | `Formalism` | 634 | 18 | 270 |
| `PositivityTheory` | `Development` | 632 | 153 | 308 |
| `Formalism` | `ReciprocityTheory` | 348 | 225 | 229 |
| `ReciprocityTheory` | `Formalism` | 266 | 196 | 137 |
| `Formalism` | `Development` | 236 | 177 | 209 |
| `CompanionTheory` | `ReciprocityTheory` | 154 | 92 | 85 |
| `Formalism` | `Lemmata` | 118 | 109 | 118 |
| `PositivityTheory` | `GroundTheory` | 111 | 46 | 59 |
| `CompanionTheory` | `GroundTheory` | 65 | 40 | 53 |
| `GroundTheory` | `Development` | 57 | 55 | 56 |

## 3. Depth-2 Sub-Theory Compression Statistics

### 3.1 Top 35 Largest Depth-2 Sub-Theories (by Total Files)

| Depth-2 Directory | Files | Interface Files | Ratio | Ext Edges (In) | Unique Ext Importers | Top Interface File (Ext Fan-In) |
|---|---:|---:|---:|---:|---:|---|
| `Development/AbelianVarietyTheory` | 99,187 | 9,498 | 0.0958 | 25,920 | 11,788 | [IrreducibleAdmissibleGL.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/PublishedTheorems/Divisors₂/IrreducibleAdmissibleGL.lean) (269) |
| `Development/AutomorphicArithmetic` | 18,431 | 1,024 | 0.0556 | 1,541 | 988 | [LocIsotypic.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean) (64) |
| `Development/AutomorphicSpectrum` | 15,147 | 3,755 | 0.2479 | 6,930 | 2,035 | [BdryChart.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Definitions/GlobalGeometry/BdryChart.lean) (43) |
| `Development/WeilBound` | 7,051 | 1,909 | 0.2707 | 7,716 | 5,872 | [Imports.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/CoreStatements/PadicHodgeComparison/EtaleCohomologyComparison/CechPairings/Imports.lean) (210) |
| `GroundTheory/HeightsAndTheta` | 6,410 | 1,601 | 0.2498 | 4,481 | 1,627 | [StatementsFlagIndependence.lean](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/DiscreteValuationNumbers/StatementsFlagIndependence.lean) (199) |
| `Formalism/LocalToGlobal` | 5,501 | 1,798 | 0.3268 | 21,534 | 11,201 | [LinksStage.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal/IndefiniteReal/LinksStage.lean) (523) |
| `Formalism/PeriodIntegrals` | 4,350 | 974 | 0.2239 | 2,004 | 1,156 | [DSInfCharCap.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PeriodIntegrals/DSInfCharCap.lean) (89) |
| `Formalism/SharpRestriction` | 3,093 | 868 | 0.2806 | 11,723 | 7,691 | [ThExprUniqOfChartIndep2.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/Divisibility/GeneratorPowers/ThExprUniqOfChartIndep2.lean) (871) |
| `ReciprocityTheory/ReductiveGroups` | 2,799 | 1,096 | 0.3916 | 34,802 | 13,818 | [UniformisationConclusion.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean) (2,379) |
| `Formalism/HermitianCurvature` | 1,922 | 359 | 0.1868 | 1,495 | 802 | [StatementQ.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/StatementQ.lean) (68) |
| `Development/EtaleCohomology` | 1,398 | 536 | 0.3834 | 694 | 164 | [H0TwistOverClosedField.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean) (31) |
| `CompanionTheory/SpectralGeometry` | 1,254 | 470 | 0.3748 | 1,557 | 551 | [IsEulerProd.lean](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/CountingDefinitions/AdelicEulerProducts/IsEulerProd.lean) (110) |
| `GroundTheory/AutomorphicForms` | 542 | 229 | 0.4225 | 1,577 | 1,028 | [Injective.lean](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean) (127) |
| `Development/ResolutionOfSingularities` | 499 | 38 | 0.0762 | 62 | 26 | [AffineBlowupUniversal.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/ResolutionOfSingularities/Foundations/Blowup/AffineBlowupUniversal.lean) (7) |
| `CompanionTheory/AutomorphicTheory` | 457 | 94 | 0.2057 | 393 | 321 | [H1StructureDimLe.lean](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/AutomorphicTheory/TemperedLocalSpectra/ObstructionLifting/H1StructureDimLe.lean) (51) |
| `GroundTheory/ProfiniteCohomology` | 450 | 83 | 0.1844 | 213 | 100 | [IsUnramifiedOutsideIffLeMaxUnramifiedOutside.lean](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ProfiniteCohomology/RestrictedRamification/IsUnramifiedOutsideIffLeMaxUnramifiedOutside.lean) (23) |
| `PositivityTheory/AutomorphicForms` | 445 | 166 | 0.3730 | 1,053 | 819 | [RationalPrimesBelowPlaces.lean](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/KFiniteVectors/KFiniteThetaLifts/RationalPrimesBelowPlaces.lean) (160) |
| `Formalism/GL3MeanSquares` | 440 | 128 | 0.2909 | 336 | 229 | [PrimeCountAsymptoticInProgressions.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GL3MeanSquares/PrimeCountAsymptoticInProgressions.lean) (84) |
| `GroundTheory/GlobalFields` | 384 | 174 | 0.4531 | 1,045 | 744 | [IdeleNorms.lean](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/GlobalFields/IdeleGroups/IdeleNorms.lean) (49) |
| `Formalism/ThetaLogCoordinates` | 292 | 62 | 0.2123 | 94 | 61 | [FinalS.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/ThetaLogCoordinates/UniformThetaSubstitution/FinalS.lean) (19) |
| `Formalism/WachLatticeTwists` | 262 | 12 | 0.0458 | 49 | 47 | [FibreDualStable.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/WachLatticeTwists/LatticeDualFibres/FibreDualStable.lean) (26) |
| `ReciprocityTheory/L2DbarEstimates` | 227 | 66 | 0.2907 | 550 | 302 | [FourSignHolds.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/L2DbarEstimates/PlurisubharmonicCharts/FourSignHolds.lean) (155) |
| `GroundTheory/PAdicHodge` | 226 | 54 | 0.2389 | 147 | 117 | [FieldOfNormsCyclBase.lean](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/PAdicHodge/FieldOfNormsCyclBase.lean) (18) |
| `GroundTheory/ArithmeticGeometry` | 218 | 75 | 0.3440 | 215 | 170 | [RingKrullDimLeRingKrullDimQuotientAddOne.lean](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ArithmeticGeometry/AbelianVarieties/JacobianSmoothness/RingKrullDimLeRingKrullDimQuotientAddOne.lean) (48) |
| `Development/DiscreteGroups` | 215 | 50 | 0.2326 | 233 | 111 | [PiVecExHolds.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean) (41) |
| `ReciprocityTheory/AnalyticForms` | 192 | 125 | 0.6510 | 2,272 | 1,731 | [FinalTheorems.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean) (563) |
| `ReciprocityTheory/DualLattices` | 183 | 86 | 0.4699 | 1,082 | 467 | [TowerZeroSurjective.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/DualLattices/TowerZeroSurjective.lean) (193) |
| `Formalism/LocalRingCardinality` | 173 | 107 | 0.6185 | 4,130 | 3,175 | [RhoDetPrimeEqMuTildeMulChiPow.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean) (902) |
| `GroundTheory/LocalFields` | 159 | 94 | 0.5912 | 456 | 325 | [WeilRepQuadratic.lean](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/LocalFields/QuadraticAbelian/WeilRepQuadratic.lean) (96) |
| `CompanionTheory/RealGroups` | 155 | 20 | 0.1290 | 252 | 240 | [LKTExists.lean](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/RealGroups/DiscreteSeries/DiscreteSeriesClassification/DiscreteSeriesExhaustion/FarRegularity/LKTExists.lean) (46) |
| `CompanionTheory/HarishChandraModules` | 130 | 66 | 0.5077 | 415 | 256 | [DiscreteSeriesInfinitesimalCharacter.lean](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean) (51) |
| `ReciprocityTheory/SemistableReduction` | 119 | 50 | 0.4202 | 292 | 250 | [TorusL2CauchyInequality.lean](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/SemistableReduction/TorusL2CauchyInequality.lean) (147) |
| `Formalism/GradedWeylDivisibility` | 103 | 47 | 0.4563 | 438 | 289 | [FinalD.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GradedWeylDivisibility/FinalD.lean) (87) |
| `Formalism/PieriBlockIdeals` | 98 | 22 | 0.2245 | 87 | 67 | [StatementLA.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PieriBlockIdeals/StatementLA.lean) (31) |
| `Formalism/AdmissibleDesigns` | 93 | 4 | 0.0430 | 16 | 16 | [RestrictedSevenEightOfFull.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/AdmissibleDesigns/RestrictedSevenEightOfFull.lean) (10) |

### 3.2 Highest-Compression Depth-2 Sub-Theories (`total_files >= 20`, Lowest Ratio)

| Depth-2 Directory | Files | Interface Files | Ratio | Compression Factor | Ext Edges (In) |
|---|---:|---:|---:|---:|---:|
| `Formalism/AdmissibleDesigns` | 93 | 4 | 0.0430 | 23.25x | 16 |
| `Formalism/WachLatticeTwists` | 262 | 12 | 0.0458 | 21.83x | 49 |
| `Development/AutomorphicArithmetic` | 18,431 | 1,024 | 0.0556 | 18.00x | 1,541 |
| `ReciprocityTheory/Chebotarev` | 47 | 3 | 0.0638 | 15.67x | 24 |
| `Formalism/JumpKernelCokernel` | 27 | 2 | 0.0741 | 13.50x | 5 |
| `Development/ResolutionOfSingularities` | 499 | 38 | 0.0762 | 13.13x | 62 |
| `Development/AbelianVarietyTheory` | 99,187 | 9,498 | 0.0958 | 10.44x | 25,920 |
| `Formalism/EllipticTorsion` | 48 | 6 | 0.1250 | 8.00x | 20 |
| `CompanionTheory/RealGroups` | 155 | 20 | 0.1290 | 7.75x | 252 |
| `CompanionTheory/ThickeningEstimates` | 22 | 3 | 0.1364 | 7.33x | 4 |
| `Formalism/DistinguishedUnitIdeals` | 44 | 7 | 0.1591 | 6.29x | 10 |
| `GroundTheory/ProfiniteCohomology` | 450 | 83 | 0.1844 | 5.42x | 213 |
| `Formalism/HermitianCurvature` | 1,922 | 359 | 0.1868 | 5.35x | 1,495 |
| `CompanionTheory/AutomorphicTheory` | 457 | 94 | 0.2057 | 4.86x | 393 |
| `Formalism/ThetaLogCoordinates` | 292 | 62 | 0.2123 | 4.71x | 94 |

### 3.3 Top 15 Depth-2 Sub-Theories by Cross-Boundary Fan-In

| Depth-2 Directory | Ext Import Edges | Unique Ext Importers | Interface / Total Files | Ratio |
|---|---:|---:|---:|---:|
| `ReciprocityTheory/ReductiveGroups` | 34,802 | 13,818 | 1,096 / 2,799 | 0.3916 |
| `Development/AbelianVarietyTheory` | 25,920 | 11,788 | 9,498 / 99,187 | 0.0958 |
| `Formalism/LocalToGlobal` | 21,534 | 11,201 | 1,798 / 5,501 | 0.3268 |
| `Formalism/SharpRestriction` | 11,723 | 7,691 | 868 / 3,093 | 0.2806 |
| `Development/WeilBound` | 7,716 | 5,872 | 1,909 / 7,051 | 0.2707 |
| `Development/AutomorphicSpectrum` | 6,930 | 2,035 | 3,755 / 15,147 | 0.2479 |
| `GroundTheory/HeightsAndTheta` | 4,481 | 1,627 | 1,601 / 6,410 | 0.2498 |
| `Formalism/LocalRingCardinality` | 4,130 | 3,175 | 107 / 173 | 0.6185 |
| `ReciprocityTheory/AnalyticForms` | 2,272 | 1,731 | 125 / 192 | 0.6510 |
| `Formalism/PeriodIntegrals` | 2,004 | 1,156 | 974 / 4,350 | 0.2239 |
| `GroundTheory/AutomorphicForms` | 1,577 | 1,028 | 229 / 542 | 0.4225 |
| `CompanionTheory/SpectralGeometry` | 1,557 | 551 | 470 / 1,254 | 0.3748 |
| `Development/AutomorphicArithmetic` | 1,541 | 988 | 1,024 / 18,431 | 0.0556 |
| `Formalism/HermitianCurvature` | 1,495 | 802 | 359 / 1,922 | 0.1868 |
| `Formalism/RealPlaceAnalysis` | 1,395 | 868 | 49 / 54 | 0.9074 |

## 4. Sub-Theory Public APIs in Plain Mathematical English (59 Verified Interface Files)

Every file below was read directly from `/home/ubuntu/riemann_proof/lean/src/`, and all listed declaration names and line numbers were verified against `graph.sqlite`.

### 4.1 `(root)` (2 files -> 0 top-dir interfaces, ratio `0.0000`)

#### [`Main.lean`](file:///home/ubuntu/riemann_proof/lean/src/Main.lean)
- **Role:** Apex Entrypoint | **Depth-2:** `(root)` | **Lines:** 12 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 0 | **Total In-Degree:** 0 (`dist=0`, `height=202`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: None
- **Plain-English Mathematical Summary:** The top-level proof driver of the entire 175,187-file codebase. Imports Statements.lean and Supplements/Kernels/MainTheoremsAll.lean, and exports the five headline theorems: the classical Riemann Hypothesis (in Mathlib's canonical formulation and an explicit zero-line formulation), nonvanishing of all Dirichlet L-functions in the half-plane Re(s) > 1/2 (away from the pole at s = 1 for the trivial character), and the Generalized Riemann Hypothesis placing all nontrivial zeros of arbitrary and primitive Dirichlet L-functions on the critical line Re(s) = 1/2.
- **Key Exported Declarations:**
  - `theorem` [`riemannHypothesis`](file:///home/ubuntu/riemann_proof/lean/src/Main.lean#L4) (L4): Proves Mathlib's canonical RiemannHypothesis statement via rhOfAll.
  - `theorem` [`riemannZeta_eq_zero_re`](file:///home/ubuntu/riemann_proof/lean/src/Main.lean#L6) (L6): Proves every non-trivial zero s != 1 of the Riemann zeta function satisfies Re(s) = 1/2.
  - `theorem` [`LFunction_ne_zero_of_half_lt_re`](file:///home/ubuntu/riemann_proof/lean/src/Main.lean#L8) (L8): Proves L(chi, s) != 0 whenever Re(s) > 1/2 (except chi = 1, s = 1) for every Dirichlet character chi.
  - `theorem` [`LFunction_eq_zero_re`](file:///home/ubuntu/riemann_proof/lean/src/Main.lean#L10) (L10): Proves every zero of any Dirichlet L-function in the critical strip 0 < Re(s) < 1 has Re(s) = 1/2.
  - `theorem` [`LFunction_eq_zero_re_of_isPrimitive`](file:///home/ubuntu/riemann_proof/lean/src/Main.lean#L12) (L12): Proves every zero of any primitive Dirichlet L-function in 0 < Re(s) < 1 lies on Re(s) = 1/2.

#### [`Statements.lean`](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean)
- **Role:** Apex Specification | **Depth-2:** `(root)` | **Lines:** 16 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 0 | **Total In-Degree:** 1 (`dist=1`, `height=0`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: None
- **Plain-English Mathematical Summary:** Defines the four standalone target propositions imported by Main.lean: explicit zero-line statements for the Riemann zeta function and for arbitrary or primitive Dirichlet L-functions, plus half-plane nonvanishing for Re(s) > 1/2. Kept minimal (16 lines depending only on Mathlib) so external auditors can read the exact theorems proved without navigating the deep proof tree.
- **Key Exported Declarations:**
  - `def` [`RiemannZetaZerosOnLine`](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean#L3) (L3): Proposition that all zeros of zeta(s) other than negative even integers and s = 1 satisfy Re(s) = 1/2.
  - `def` [`DirichletLNonvanishingRightOfHalf`](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean#L6) (L6): Proposition that L(chi, s) != 0 for all moduli N >= 1, Dirichlet characters chi, and Re(s) > 1/2 (with chi != 1 or s != 1).
  - `def` [`DirichletLZerosOnLine`](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean#L10) (L10): Proposition that all critical-strip zeros (0 < Re(s) < 1) of any Dirichlet L-function satisfy Re(s) = 1/2.
  - `def` [`PrimitiveDirichletLZerosOnLine`](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean#L14) (L14): Same critical-line zero statement restricted to primitive Dirichlet characters.

### 4.2 `Supplements` (3 files -> 1 top-dir interfaces, ratio `0.3333`)

#### [`Supplements/Kernels/MainTheoremsAll.lean`](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheoremsAll.lean)
- **Role:** Root Interface Barrel | **Depth-2:** `Supplements/Kernels` | **Lines:** 2 | **Top-Dir Ext Fan-In:** 1 | **Depth-2 Ext Fan-In:** 1 | **Total In-Degree:** 1 (`dist=1`, `height=201`)
- **External Importers:** Top-dirs: `(root)` (1) | Depth-2 dirs: `(root)` (1)
- **Plain-English Mathematical Summary:** The sole interface file of the Supplements directory imported directly by Main.lean. Aggregates MainTheoremsCritical.lean (which itself combines MainTheorems.lean with small-class-number Selmer bounds) and CorGKOf.lean, wiring the completed Development and Formalism proofs into the root theorem file.
- **Key Exported Declarations:** No local `theorem`/`def`/`structure` declarations (pure import barrel / command directive).

#### [`Supplements/Kernels/MainTheorems.lean`](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheorems.lean)
- **Role:** Top-Level Bottleneck Bridge | **Depth-2:** `Supplements/Kernels` | **Lines:** 16 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 0 | **Total In-Degree:** 1 (`dist=3`, `height=199`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: None
- **Plain-English Mathematical Summary:** Assembles the final headline theorems exported to Main.lean by combining UpperTheory.FinalTheorems.everyCharacter (from Development) with the functional-equation reflection reductions Formalism.VW.rh_of_every, Formalism.VW.critLine, and Claim.strip / Claim.zeta.
- **Key Exported Declarations:**
  - `theorem` [`allChi`](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheorems.lean#L7) (L7): Instantiates UpperTheory.EveryCharacter (nonvanishing of all Dirichlet L-functions in Re(s) > 1/2).
  - `theorem` [`rhOfAll`](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheorems.lean#L9) (L9): Deduces Mathlib's RiemannHypothesis from allChi via Formalism.VW.rh_of_every.
  - `theorem` [`critAll`](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheorems.lean#L11) (L11): Deduces critical-line localization for primitive Dirichlet L-functions via Formalism.VW.critLine.
  - `theorem` [`claimAll`](file:///home/ubuntu/riemann_proof/lean/src/Supplements/Kernels/MainTheorems.lean#L15) (L15): Packages the conjunction Claim.HalfPlane /\ Claim.Strip /\ Claim.Zeta for arbitrary characters and zeta.

### 4.3 `Development` (141,928 files -> 1,195 top-dir interfaces, ratio `0.0084`)

#### [`Development/AbelianVarietyTheory/Definitions/Jets/SumIoPr.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/Jets/SumIoPr.lean)
- **Role:** Archimedean Branching & Representation Algebra | **Depth-2:** `Development/AbelianVarietyTheory` | **Lines:** 59 | **Top-Dir Ext Fan-In:** 167 | **Depth-2 Ext Fan-In:** 167 | **Total In-Degree:** 584 (`dist=8`, `height=4`)
- **External Importers:** Top-dirs: `CompanionTheory` (167) | Depth-2 dirs: `CompanionTheory/AutomorphicTheory` (167)
- **Plain-English Mathematical Summary:** Defines algebraic structures for branching and tensor-product decomposition of unitary Lie algebra representations U(p, q): Casimir bounds (CasKLe, casG), weight-neighborhood subspaces (WtNear, Lev), the dual tensor decomposition AlgTens (splitting a representation via embeddings io_s and projections pr_s satisfying orthogonality with respect to the indefinite signature form hhJ and sum_io_pr), and asymptotic parameter regimes (Shape).
- **Key Exported Declarations:**
  - `def` [`CasKLe`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/Jets/SumIoPr.lean#L16) (L16): Bounds the compact Casimir operator CasK on a finite-dimensional K-stable submodule containing w.
  - `def` [`IsMod`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/Jets/SumIoPr.lean#L29) (L29): Specifies a unitary gl_n-module with global Casimir eigenvalue casG(mu).
  - `structure` [`AlgTens`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/Jets/SumIoPr.lean#L39) (L39): Algebraic decomposition of a tensor-product gl_n-module into orthogonal summands N_s with intertwining injections io_s, projections pr_s, and signature signs +/-1.
  - `def` [`Shape`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/Jets/SumIoPr.lean#L53) (L53): Defines the separated highest-weight and signature regime for branching estimates.

#### [`Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean)
- **Role:** Master Literature Package | **Depth-2:** `Development/AbelianVarietyTheory` | **Lines:** 139 | **Top-Dir Ext Fan-In:** 66 | **Depth-2 Ext Fan-In:** 104 | **Total In-Degree:** 122 (`dist=5`, `height=95`)
- **External Importers:** Top-dirs: `PositivityTheory` (66) | Depth-2 dirs: `PositivityTheory/AutomorphicForms` (66), `Development/AutomorphicArithmetic` (38)
- **Plain-English Mathematical Summary:** Bundles 60+ foundational theorems from modern representation theory, automorphic forms, Galois cohomology, and arithmetic geometry into four structured hypothesis bundles (LitLoc for local GL_n/LLC/Bernstein-Zelevinsky, LitAut for global cuspidal spectrum/Clozel purity/Caraiani compatibility, LitCoh for Poitou-Tate/Bloch-Kato/Greenberg-Wiles, LitCM for CM abelian varieties/Deligne-Ribet/Hecke-Tate) combined into LitN.
- **Key Exported Declarations:**
  - `structure` [`LitLoc`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean#L60) (L60): Packages 23 local GL_n representation-theory theorems (Bernstein-Zelevinsky, Moy-Prasad, Local Langlands, Local Converse, Brauer degree zero).
  - `structure` [`LitAut`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean#L85) (L85): Packages 18 global automorphic theorems (Jacquet-Shalika, Moeglin-Waldspurger residual spectrum, base change, Galois representations, purity, Berger).
  - `structure` [`LitCoh`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean#L105) (L105): Packages 12 Galois cohomology theorems (Poitou-Tate, local/global Tate duality and Euler characteristic, Greenberg-Wiles, Bloch-Kato).
  - `structure` [`LitCM`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean#L119) (L119): Packages 12 CM/abelian-variety theorems (Hilbert-Blumenthal, Grothendieck deformation, Serre-Tate, period comparison, Siegel-Klingen-Deligne-Ribet).
  - `structure` [`LitN`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership/Brauer.lean#L133) (L133): Aggregates LitLoc, LitAut, LitCoh, and LitCM into the unified literature input structure.

#### [`Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/Langlands.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/Langlands.lean)
- **Role:** Local Langlands & Galois Transport Interface | **Depth-2:** `Development/AbelianVarietyTheory` | **Lines:** 101 | **Top-Dir Ext Fan-In:** 64 | **Depth-2 Ext Fan-In:** 80 | **Total In-Degree:** 256 (`dist=6`, `height=42`)
- **External Importers:** Top-dirs: `PositivityTheory` (63), `CompanionTheory` (1) | Depth-2 dirs: `PositivityTheory/AutomorphicForms` (63), `Development/AutomorphicArithmetic` (14), `Development/WeilBound` (2), `CompanionTheory/RealGroups` (1)
- **Plain-English Mathematical Summary:** Defines the axiomatic characterization of the Local Langlands Correspondence for GL_n over p-adic completions (LawsMin, LawsLit, IsRecLit) matching irreducible smooth representations to Weil-Deligne representations via epsilon-factors, twists, central characters, and contragredients, together with place-isomorphism transport relations (RepRel, WeilRel, WDRel, PlaceIso) across field automorphisms.
- **Key Exported Declarations:**
  - `structure` [`LawsMin`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/Langlands.lean#L20) (L20): Minimal Local Langlands axioms: bijection, dimension matching, character compatibility, pair epsilon-factors, cuspidal-irreducible correspondence, and Zelevinsky segment sum.
  - `structure` [`LawsLit`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/Langlands.lean#L38) (L38): Extends LawsMin with twist compatibility, central character determinant matching, and contragredient duality.
  - `def` [`IsRecLit`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/Langlands.lean#L52) (L52): Asserts existence of a Deligne epsilon-factor family and local Artin map satisfying LawsLit.
  - `structure` [`PlaceIso`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/NonGaloisDescent/Langlands.lean#L84) (L84): Packages compatible isomorphisms of algebraic closures, number fields, and p-adic completions for transporting Local Langlands data.

#### [`Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean)
- **Role:** Local-Global Compatibility Interface | **Depth-2:** `Development/AutomorphicArithmetic` | **Lines:** 135 | **Top-Dir Ext Fan-In:** 64 | **Depth-2 Ext Fan-In:** 64 | **Total In-Degree:** 141 (`dist=7`, `height=47`)
- **External Importers:** Top-dirs: `PositivityTheory` (63), `CompanionTheory` (1) | Depth-2 dirs: `PositivityTheory/AutomorphicForms` (63), `CompanionTheory/EightfoldTheory` (1)
- **Plain-English Mathematical Summary:** Defines the core local-global compatibility predicates linking l-adic Galois representations and cuspidal automorphic representations of GL_n over number fields: Weil-Deligne level conditions (IsLevelWD, WDAway, WDAbove), local isotypic components (LocIsotypic, LocCompC, LocCompR), Satake parameters matching Frobenius eigenvalues (SatLoc, SatFrob), crystalline slopes / Hodge-Tate jumps (CrysSlopes, JumpsAbove), and algebraic Weyl-module dimension bounds (WeylC, WeylQ, CohBound).
- **Key Exported Declarations:**
  - `def` [`LocIsotypic`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean#L27) (L27): States that a global smooth GL_n(A_F) representation decomposes locally at w as a direct sum of copies of an irreducible smooth representation sigma.
  - `def` [`WDAbove`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean#L45) (L45): Characterizes the Weil-Deligne representation at places dividing l for potentially semistable Galois representations with flag filtration.
  - `def` [`SatFrob`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean#L89) (L89): Identifies Frobenius eigenvalues of an l-adic Galois representation at unramified places with the Satake parameters of the corresponding local GL_n representation.
  - `def` [`CrysSlopes`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean#L97) (L97): Relates Newton slopes of Satake parameters at crystalline places p to the Hodge-Tate weights m_i.
  - `def` [`CompatAtLQ`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/LocIsotypic.lean#L124) (L124): States full local-global compatibility at l for regular algebraic cuspidal automorphic representations over Q.

#### [`Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/RealTransport/RealTransport.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/RealTransport/RealTransport.lean)
- **Role:** CM Base Change & Quadratic Transport Interface | **Depth-2:** `Development/AutomorphicArithmetic` | **Lines:** 76 | **Top-Dir Ext Fan-In:** 64 | **Depth-2 Ext Fan-In:** 64 | **Total In-Degree:** 74 (`dist=9`, `height=48`)
- **External Importers:** Top-dirs: `PositivityTheory` (63), `CompanionTheory` (1) | Depth-2 dirs: `PositivityTheory/AutomorphicForms` (63), `CompanionTheory/EightfoldTheory` (1)
- **Plain-English Mathematical Summary:** Packages base-change and CM-field descent properties used to transport cuspidal automorphic representations from a totally real field F to quadratic CM extensions K/F: existence of CM extensions with prescribed inertia behavior (QuadCM, ExQuadR), absence of self-twists (NoTwistRam), descent of Hecke characters to maximal real subfields (RealTransport), and conjugate self-duality after quadratic base change (CsdTw, BcDual).
- **Key Exported Declarations:**
  - `def` [`ExQuadR`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/RealTransport/RealTransport.lean#L28) (L28): Constructs a quadratic CM extension K/F ramified or non-split at an auxiliary place outside a cofinite set while controlling local Galois extensions.
  - `def` [`NoTwistRam`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/RealTransport/RealTransport.lean#L37) (L37): Rules out quadratic character self-twists of cuspidal representations when the Galois representation has nontrivial image on the quadratic extension.
  - `def` [`RealTransport`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/RealTransport/RealTransport.lean#L47) (L47): Transports a Hecke character on F to one on the maximal real subfield of K preserving archimedean signs and unramified local values.
  - `def` [`BcDual`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/AutomorphicForms/RealTransport/RealTransport.lean#L69) (L69): Deduces conjugate-self-duality (up to a Hecke twist) of the base change P to K of a polarized cuspidal representation pi on F.

#### [`Development/AbelianVarietyTheory/PublishedTheorems/Divisors₂/IrreducibleAdmissibleGL.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/PublishedTheorems/Divisors₂/IrreducibleAdmissibleGL.lean)
- **Role:** Published Theorem Specification | **Depth-2:** `Development/AbelianVarietyTheory` | **Lines:** 17 | **Top-Dir Ext Fan-In:** 13 | **Depth-2 Ext Fan-In:** 269 | **Total In-Degree:** 322 (`dist=6`, `height=4`)
- **External Importers:** Top-dirs: `CompanionTheory` (13) | Depth-2 dirs: `Development/AutomorphicSpectrum` (215), `Development/WeilBound` (24), `Development/AutomorphicArithmetic` (17), `CompanionTheory/SpectralGeometry` (9)
- **Plain-English Mathematical Summary:** Single-declaration interface exporting the classical theorem that every smooth irreducible complex representation of GL_n(k) over a non-archimedean local field k is admissible.
- **Key Exported Declarations:**
  - `def` [`IrreducibleAdmissibleGL`](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/PublishedTheorems/Divisors₂/IrreducibleAdmissibleGL.lean#L10) (L10): States that any smooth irreducible complex representation of GL_n(k) over a non-archimedean local field is admissible.

#### [`Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean)
- **Role:** Selmer / Galois Cohomology Realization | **Depth-2:** `Development/AutomorphicArithmetic` | **Lines:** 29 | **Top-Dir Ext Fan-In:** 1 | **Depth-2 Ext Fan-In:** 1 | **Total In-Degree:** 1 (`dist=2`, `height=198`)
- **External Importers:** Top-dirs: `Supplements` (1) | Depth-2 dirs: `Supplements/Kernels` (1)
- **Plain-English Mathematical Summary:** Instantiates the abstract literature hypotheses LiteratureRankNHypothesis (via open-image Galois conditions, base change, and CM abelian inputs) and combines patching hypotheses with unitary U(3) class-number-1 arithmetic over Q(sqrt(-3)) to prove CorGK and the polynomial Selmer-length growth bound Bound.
- **Key Exported Declarations:**
  - `theorem` [`corGK_of`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L10) (L10): Derives the unitary U(3) Selmer growth corollary U3.CorGK from automorphic patching hypotheses HypothesesH'.
  - `theorem` [`litN`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L20) (L20): Constructs LiteratureRankNHypothesis from open-image, local, automorphic, Galois-cohomological, and CM abelian variety inputs.
  - `theorem` [`corGK`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L25) (L25): Unconditionally establishes U3.CorGK using litN and patching reduction descWeak.
  - `theorem` [`bound`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L27) (L27): Proves the explicit polynomial bound C * (e + 1)^A on weighted sums of Shafarevich-Tate lengths over Q(sqrt(-3)).

#### [`Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean)
- **Role:** Analytic Reduction Bridge | **Depth-2:** `Development/AutomorphicArithmetic` | **Lines:** 104 | **Top-Dir Ext Fan-In:** 1 | **Depth-2 Ext Fan-In:** 1 | **Total In-Degree:** 1 (`dist=4`, `height=1`)
- **External Importers:** Top-dirs: `Supplements` (1) | Depth-2 dirs: `Supplements/Kernels` (1)
- **Plain-English Mathematical Summary:** Elementary analytic bridge converting half-plane nonvanishing (Re(s) > 1/2) for all Dirichlet L-functions into critical-line localization (Re(s) = 1/2) in 0 < Re(s) < 1 for arbitrary (possibly imprimitive) Dirichlet characters and the Riemann zeta function. Uses Euler factor nonvanishing for Re(s) > 0 to pass to the primitive character, applies the completed L-function functional equation across s <-> 1 - s, and handles zeta's trivial zeros via Gamma_R.
- **Key Exported Declarations:**
  - `theorem` [`factor_ne_zero`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L7) (L7): Shows each Euler factor 1 - psi(p) p^(-s) is nonzero for Re(s) > 0 since |psi(p) p^(-s)| < 1.
  - `theorem` [`prim_zero`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L23) (L23): Transfers any critical-strip zero of L(chi, s) to the primitive character L(chi.primitiveCharacter, s) = 0.
  - `theorem` [`prim_reflect`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L42) (L42): Reflects a critical-strip zero of a primitive L-function at s to L(psi^(-1), 1 - s) = 0 via the completed functional equation.
  - `theorem` [`strip`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L59) (L59): Proves HalfPlane -> Strip: all critical-strip zeros of every Dirichlet L-function lie on Re(s) = 1/2.
  - `theorem` [`zeta`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L75) (L75): Proves HalfPlane -> Zeta: all nontrivial zeros of riemannZeta lie on Re(s) = 1/2.

#### [`Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean)
- **Role:** Top-Level Bottleneck Theorem | **Depth-2:** `Development/AutomorphicArithmetic` | **Lines:** 14 | **Top-Dir Ext Fan-In:** 1 | **Depth-2 Ext Fan-In:** 1 | **Total In-Degree:** 1 (`dist=4`, `height=198`)
- **External Importers:** Top-dirs: `Supplements` (1) | Depth-2 dirs: `Supplements/Kernels` (1)
- **Plain-English Mathematical Summary:** Top-of-pyramid bridge inside Development/AutomorphicArithmetic that discharges the Galois local-global modularity hypothesis UpperTheory.Gal.Int.galoisLocalGlobalStrong_recParameter and combines it with local Langlands reciprocity existence (recTExists) and vWin_of_row to prove UpperTheory.FinalTheorems.everyCharacter (nonvanishing of all Dirichlet L-functions on Re(s) > 1/2) and RiemannHypothesis.
- **Key Exported Declarations:**
  - `theorem` [`UpperTheory.FinalTheorems.everyCharacter_of_row`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L7) (L7): Derives EveryCharacter from a single Galois local-global row parameter hypothesis via literature modularity theorems and vWin_of_row.
  - `theorem` [`UpperTheory.FinalTheorems.everyCharacter`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L10) (L10): Unconditional proof that every Dirichlet L-function is nonzero on Re(s) > 1/2 (away from chi = 1, s = 1).
  - `theorem` [`UpperTheory.FinalTheorems.riemannHypothesis`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L13) (L13): Unconditional proof of RiemannHypothesis from everyCharacter.

#### [`Development/WeilBound/RepresentationTheoryGL/RegularisedSiegelWeil/ThetaIdempotents/HeckeEta.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/RepresentationTheoryGL/RegularisedSiegelWeil/ThetaIdempotents/HeckeEta.lean)
- **Role:** Theta Idempotent & Meromorphic Pole Interface | **Depth-2:** `Development/WeilBound` | **Lines:** 30 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 153 | **Total In-Degree:** 153 (`dist=19`, `height=53`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `Development/AutomorphicSpectrum` (153)
- **Plain-English Mathematical Summary:** Exports three clean propositions used in the regularized Siegel-Weil / Godement-Jacquet L-function pipeline: existence of Hecke characters satisfying a residue condition on the adelic algebra AE D (HeckeEta), right half-plane identity principle for holomorphic functions (RightId), and contour-integral residue extraction at real poles of meromorphic ratios h(s)/d(s) (PoleReal).
- **Key Exported Declarations:**
  - `def` [`HeckeEta`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/RepresentationTheoryGL/RegularisedSiegelWeil/ThetaIdempotents/HeckeEta.lean#L11) (L11): Asserts existence of a continuous Circle-valued Hecke character chi on (AE D)^x satisfying IsHeckeChar and ResEta at level k.
  - `def` [`RightId`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/RepresentationTheoryGL/RegularisedSiegelWeil/ThetaIdempotents/HeckeEta.lean#L13) (L13): Identity theorem on right-half domains: holomorphic functions agreeing for Re(s) > sigma agree on the whole domain intersected with Re(s) > c.
  - `def` [`PoleReal`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/RepresentationTheoryGL/RegularisedSiegelWeil/ThetaIdempotents/HeckeEta.lean#L17) (L17): Characterizes simple poles vs holomorphicity at a real point s_0 of h(s)/d(s) via boundedness along the real axis and circle contour integrals.

#### [`Development/WeilBound/CoreStatements/TemperedRepresentationTheory/PlaneSupports/PlaneSupp.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/CoreStatements/TemperedRepresentationTheory/PlaneSupports/PlaneSupp.lean)
- **Role:** Adelic Unitary Group Generation Interface | **Depth-2:** `Development/WeilBound` | **Lines:** 67 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 104 | **Total In-Degree:** 104 (`dist=7`, `height=29`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `Development/AutomorphicSpectrum` (104)
- **Plain-English Mathematical Summary:** Formulates the strong-approximation / subgroup-generation criterion for adelic unitary groups SU(J)(A_F) of rank M >= 2: defines nondegenerate two-planes PlaneND and plane stabilizers PlaneSupp, and states that closed subgroups generated by rational elements and local supports around nondegenerate planes fill the full adelic special unitary group (PropPlane, PropGen, PropProd).
- **Key Exported Declarations:**
  - `def` [`PlaneND`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/CoreStatements/TemperedRepresentationTheory/PlaneSupports/PlaneSupp.lean#L21) (L21): Non-degeneracy of the 2x2 Hermitian Gram determinant spanned by vectors u_0, u_1.
  - `def` [`PlaneSupp`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/CoreStatements/TemperedRepresentationTheory/PlaneSupports/PlaneSupp.lean#L24) (L24): Subgroup/set of adelic unitary matrices fixing the Hermitian orthogonal complement of u_0, u_1.
  - `def` [`PropPlane`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/CoreStatements/TemperedRepresentationTheory/PlaneSupports/PlaneSupp.lean#L39) (L39): States that noncompact plane-stabilizer supports lie in the closure of the rational-times-support set SASet.
  - `def` [`PropProd`](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound/CoreStatements/TemperedRepresentationTheory/PlaneSupports/PlaneSupp.lean#L59) (L59): Concludes that any closed subgroup containing all local place-idempotent supports contains the entire adelic special unitary group.

#### [`Development/AutomorphicSpectrum/Definitions/GlobalGeometry/BdryChart.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Definitions/GlobalGeometry/BdryChart.lean)
- **Role:** Complex Boundary Chart Interface | **Depth-2:** `Development/AutomorphicSpectrum` | **Lines:** 64 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 43 | **Total In-Degree:** 468 (`dist=11`, `height=9`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `Development/WeilBound` (43)
- **Plain-English Mathematical Summary:** Defines complex-analytic boundary charts BdryChart on toroidal compactifications Moduli D l of unitary Shimura varieties: maps a punctured polydisc in C^n holomorphically into a semiabelian scheme SAB over Spec R mapping into Xo.X, equipped with a Lie-algebra trivialization M, logarithmic distance function logSize, and Hodge-metric Gram matrix identification IsRiem.
- **Key Exported Declarations:**
  - `def` [`punct`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Definitions/GlobalGeometry/BdryChart.lean#L12) (L12): Punctured polydisc in C^n of radius rho where the first a coordinates are nonzero.
  - `def` [`logSize`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Definitions/GlobalGeometry/BdryChart.lean#L14) (L14): Logarithmic boundary proximity weight 1 + sum |log ||z_i|||.
  - `structure` [`BdryChart`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Definitions/GlobalGeometry/BdryChart.lean#L19) (L19): Analytic chart around a toroidal boundary stratum of Xo.X carrying a semiabelian scheme, Lie model, open immersion V -> Spec R, and holomorphic point family.
  - `def` [`BdryChart.IsRiem`](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Definitions/GlobalGeometry/BdryChart.lean#L57) (L57): Matches the Hodge-metric Gram matrix IsHodgeGram at z with pi times the Hermitian form Hm.

#### [`Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean)
- **Role:** Cuspidal Vector Square-Integrability Proof | **Depth-2:** `Development/DiscreteGroups` | **Lines:** 80 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 41 | **Total In-Degree:** 42 (`dist=8`, `height=80`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `Development/AutomorphicArithmetic` (41)
- **Plain-English Mathematical Summary:** Proves PiVecEx: multiplying a smooth cusp form psi on G(A) (invariant under split center) by a compactly supported continuous cutoff u(ldet x) yields a function in L^2(H_n, nu) with rapidly decaying moments against every power of the height weight wt(x)^M.
- **Key Exported Declarations:**
  - `theorem` [`piVecEx_holds`](file:///home/ubuntu/riemann_proof/lean/src/Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean#L16) (L16): Proves L^2-integrability and polynomial weight-moment finiteness for compactly-supported determinant twists of cusp forms.

#### [`Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean)
- **Role:** Etale Cohomology Finiteness Reduction | **Depth-2:** `Development/EtaleCohomology` | **Lines:** 180 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 31 | **Total In-Degree:** 41 (`dist=13`, `height=7`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `Development/AutomorphicArithmetic` (31)
- **Plain-English Mathematical Summary:** Contains the structural inductive proof (goal_of) of finiteness of twisted etale cohomology H^n(X, Z/qZ(i)) for proper schemes over a field (EtaleChapterEFour), decomposing the induction over Krull dimension into explicit leaf statements: H^0 invariance over algebraically closed fields, zero-dimensional varieties, alterations/Chow reductions, curve cohomology via Kummer theory (LeafUnits, LeafPic, LeafKum, LeafCurve), Lefschetz-style fiber families (LeafGeo), and specialization/ghost-killing (LeafSpec, LeafGhost).
- **Key Exported Declarations:**
  - `def` [`H0TwistOverClosedField`](file:///home/ubuntu/riemann_proof/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L25) (L25): Finiteness and pullback bijectivity for H^0(X, Z/qZ(i)) on connected schemes over an algebraically closed field.
  - `def` [`LeafCurve`](file:///home/ubuntu/riemann_proof/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L53) (L53): Finiteness of H^1, H^2 and vanishing of H^m (m >= 3) for smooth proper curves over an algebraically closed field.
  - `def` [`LeafGeo`](file:///home/ubuntu/riemann_proof/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L73) (L73): Geometric fibration lemma slicing a positive-dimensional proper integral scheme into families of curves over a lower-dimensional base.
  - `theorem` [`goal_of`](file:///home/ubuntu/riemann_proof/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L114) (L114): Assembles the 13 leaf hypotheses via double induction on cohomological degree n and Krull dimension e to prove EtaleChapterEFour.

#### [`Development/ResolutionOfSingularities/Statements.lean`](file:///home/ubuntu/riemann_proof/lean/src/Development/ResolutionOfSingularities/Statements.lean)
- **Role:** Resolution of Singularities Specification | **Depth-2:** `Development/ResolutionOfSingularities` | **Lines:** 267 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 7 | **Total In-Degree:** 8 (`dist=7`, `height=0`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `Development/WeilBound` (7)
- **Plain-English Mathematical Summary:** Defines canonical functorial embedded resolution of singularities and principalization of ideal sheaves in characteristic zero over schemes: blowup sequences (BlowupSequence), strict normal crossings divisors (IsStrictNormalCrossings, HasSimpleNormalCrossings), pullback compatibility under smooth morphisms and field extensions, and the headline propositions FunctorialResolutionCharZero and FunctorialPrincipalizationCharZero.
- **Key Exported Declarations:**
  - `structure` [`BlowupSequence`](file:///home/ubuntu/riemann_proof/lean/src/Development/ResolutionOfSingularities/Statements.lean#L35) (L35): Finite sequence of blowups along closed centers over a base scheme X.
  - `def` [`IsResolutionRuleCharZero`](file:///home/ubuntu/riemann_proof/lean/src/Development/ResolutionOfSingularities/Statements.lean#L126) (L126): Requires a resolution rule to produce a smooth scheme properly birational over the smooth locus with strict normal crossings exceptional divisor.
  - `def` [`FunctorialResolutionCharZero`](file:///home/ubuntu/riemann_proof/lean/src/Development/ResolutionOfSingularities/Statements.lean#L150) (L150): Existence of a resolution rule functorial with respect to smooth morphisms and field extensions in char 0.
  - `def` [`FunctorialPrincipalizationCharZero`](file:///home/ubuntu/riemann_proof/lean/src/Development/ResolutionOfSingularities/Statements.lean#L260) (L260): Existence of a functorial principalization rule turning any nonzero ideal sheaf into a monomial exceptional product.

### 4.4 `Formalism` (18,254 files -> 3,640 top-dir interfaces, ratio `0.1994`)

#### [`Formalism/SharpRestriction/Divisibility/GeneratorPowers/ThExprUniqOfChartIndep2.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/Divisibility/GeneratorPowers/ThExprUniqOfChartIndep2.lean)
- **Role:** Differential Operator Chart-Independence | **Depth-2:** `Formalism/SharpRestriction` | **Lines:** 41 | **Top-Dir Ext Fan-In:** 871 | **Depth-2 Ext Fan-In:** 871 | **Total In-Degree:** 873 (`dist=9`, `height=12`)
- **External Importers:** Top-dirs: `Development` (870), `ReciprocityTheory` (1) | Depth-2 dirs: `Development/AbelianVarietyTheory` (869), `Development/AutomorphicSpectrum` (1), `ReciprocityTheory/ReductiveGroups` (1)
- **Plain-English Mathematical Summary:** Proves ThExprUniqSt (the highest-fan-in Formalism file, imported 871 times externally) from ChartIndepSt2: two formal differential operators nab_1, nab_2 acting on global sections of powers of the polarization line bundle L^k over a framed Shimura point y produce the exact same value on harmonic polynomials P when evaluated via local formal charts.
- **Key Exported Declarations:**
  - `def` [`ChartIndepSt2`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/Divisibility/GeneratorPowers/ThExprUniqOfChartIndep2.lean#L12) (L12): States that chart evaluations chartVal C k f P on harmonic polynomials P in harmA agree across any two formal charts C, C' at y.
  - `theorem` [`thExprUniq_of_chartIndep2`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/Divisibility/GeneratorPowers/ThExprUniqOfChartIndep2.lean#L24) (L24): Proves uniqueness of formal differential theta expressions (ThExprUniqSt) from ChartIndepSt2.

#### [`Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean)
- **Role:** Master Arithmetic-Automorphic Data Structure | **Depth-2:** `Formalism/LocalRingCardinality` | **Lines:** 393 | **Top-Dir Ext Fan-In:** 780 | **Depth-2 Ext Fan-In:** 902 | **Total In-Degree:** 921 (`dist=7`, `height=14`)
- **External Importers:** Top-dirs: `Development` (780) | Depth-2 dirs: `Development/AbelianVarietyTheory` (723), `Formalism/SharpRestriction` (99), `Development/AutomorphicSpectrum` (29), `Development/AutomorphicArithmetic` (22)
- **Plain-English Mathematical Summary:** Defines self-dual Hermitian lattices (IsSDLat, SDLat), inert-prime indices (GIdx), and the central 200+ field packaging structure D7 that coordinates CM host fields, Shimura spaces, member column chains, relative Hermitian determinants (relDet), Fontaine period rings (loc, locA, locT), Galois representations and types (nd, ntw, naut, ntypes), and theta jets. Also states key compatibility conjectures/predicates (BuRational, bridge_cols_conj, FactDGam, AnisotropicLineIndepOfMember).
- **Key Exported Declarations:**
  - `def` [`IsSDLat`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L56) (L56): Defines a finitely generated, full-span, self-dual O_E-lattice in E^N with respect to the standard Hermitian form stdH.
  - `structure` [`Member`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L71) (L71): Packages a column chain C, columns-at-T data A, and period map P for a rank tuple hc.
  - `structure` [`D7`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L76) (L76): Master coordination structure linking CM host, Hermitian spaces, divisibility data, relative determinants, local Fontaine period rings, Galois types, and S-arithmetic data.
  - `def` [`FactBuUnique`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L376) (L376): Uniqueness of the bilinear period-column pairing Bu determined by its values on V_0(mu_0).
  - `def` [`AnisotropicLineIndepOfMember`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L385) (L385): Asserts that member T-parameters differ from the base member u_0 only by norms c * conj(c) in E.

#### [`Formalism/LocalRingCardinality/AdicCompletionLocal/LocTied.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/AdicCompletionLocal/LocTied.lean)
- **Role:** p-adic Period Ring Identification | **Depth-2:** `Formalism/LocalRingCardinality` | **Lines:** 38 | **Top-Dir Ext Fan-In:** 775 | **Depth-2 Ext Fan-In:** 775 | **Total In-Degree:** 776 (`dist=7`, `height=7`)
- **External Importers:** Top-dirs: `Development` (775) | Depth-2 dirs: `Development/AbelianVarietyTheory` (738), `Development/AutomorphicSpectrum` (29), `Development/WeilBound` (6), `Development/AutomorphicArithmetic` (2)
- **Plain-English Mathematical Summary:** Defines the structure LocTied tying an abstract local Fontaine period-ring package (P : LocPrime l, AI : LocAinf l P) to the canonical concrete period rings Per.Bcris l and Per.BdR l via Galois-, Frobenius-, filtration-, and t-compatible ring isomorphisms eB and eD.
- **Key Exported Declarations:**
  - `structure` [`LocTied`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalRingCardinality/AdicCompletionLocal/LocTied.lean#L11) (L11): Packages ring isomorphisms eB : P.R.B ~= B_cris and eD : P.R.BdR ~= B_dR preserving Z_l, Galois action, Frobenius, Hodge filtration, Fontaine's t, and A_inf.

#### [`Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean)
- **Role:** Local Bloch-Kato & Tate Duality Core | **Depth-2:** `Formalism/SharpRestriction` | **Lines:** 195 | **Top-Dir Ext Fan-In:** 649 | **Depth-2 Ext Fan-In:** 649 | **Total In-Degree:** 654 (`dist=7`, `height=3`)
- **External Importers:** Top-dirs: `Development` (649) | Depth-2 dirs: `Development/AbelianVarietyTheory` (642), `Development/AutomorphicArithmetic` (5), `Development/WeilBound` (2)
- **Plain-English Mathematical Summary:** Defines continuous p-adic Galois representations GRep over Q_p-extensions LL with integral rings O, de Rham representations (IsDR), Tate-twisted linear and lattice dualities (IsDual1, IsDualLat1), cup products (cupL, cupLD), and the local Bloch-Kato / Tate duality specifications bkACore, bkBCore, LocalTateTopDegree, TateFiniteness, and drDualCore.
- **Key Exported Declarations:**
  - `def` [`IsDR`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L21) (L21): De Rham criterion: dim_LL D_dR(rho) = [K : Q_p] * dim_LL(V).
  - `structure` [`GRep`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L36) (L36): Continuous finite-dimensional LL-linear representation of a topological group G equipped with module topology and O-structure.
  - `def` [`bkACore`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L154) (L154): Rational Bloch-Kato orthogonality: finite-part cocycles H^1_f(A) and H^1_f(A') are exact annihilators under the local cup product.
  - `def` [`bkBCore`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L161) (L161): Integral lattice Bloch-Kato orthogonality between divisible H^1_f(LA') and integral H^1_f(LA) modulo O.
  - `def` [`TateFiniteness`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L182) (L182): Finiteness (Noetherianness over O) of integral lattice cohomology.

#### [`Formalism/LocalToGlobal/IndefiniteReal/LinksStage.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal/IndefiniteReal/LinksStage.lean)
- **Role:** Indefinite Theta-Lift Stage Interface | **Depth-2:** `Formalism/LocalToGlobal` | **Lines:** 315 | **Top-Dir Ext Fan-In:** 523 | **Depth-2 Ext Fan-In:** 523 | **Total In-Degree:** 524 (`dist=7`, `height=35`)
- **External Importers:** Top-dirs: `Development` (523) | Depth-2 dirs: `Development/AbelianVarietyTheory` (507), `Development/AutomorphicArithmetic` (9), `Development/AutomorphicSpectrum` (7)
- **Plain-English Mathematical Summary:** Defines the inductive construction stages (RealDat.Pre0, Pre1, upd1..upd6) and analytic/representation-theoretic input bundle Inputs for indefinite unitary theta lifts and seesaw/doubling identities on Hermitian spaces over CM fields: Cartan involutions (CartanOK), self-dual frames (SelfDualOK), Weil representations (FullY, FullP, VecTheta), fundamental-domain Petersson inner products (PetAll), and Schur multipliers (SchurAll).
- **Key Exported Declarations:**
  - `structure` [`Pre0`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal/IndefiniteReal/LinksStage.lean#L31) (L31): Initial stage invariant for RealDat ensuring level characters, groups, families, and infinite-place models are initialized.
  - `def` [`SplitAt`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal/IndefiniteReal/LinksStage.lean#L109) (L109): Specifies Hecke character splitting and eta-restriction compatibility along the tower of unitary spaces.
  - `def` [`ThetaPExists`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal/IndefiniteReal/LinksStage.lean#L171) (L171): Existence of theta-lift linear maps landing inside the distinguished subspace Wall with prescribed period data.
  - `structure` [`Inputs`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal/IndefiniteReal/LinksStage.lean#L290) (L290): Master input bundle (19 fields) combining Weil representations, Cartan/self-dual checks, fundamental domains, Petersson positivity, Harish-Chandra finiteness, and Hecke actions.

#### [`Formalism/PairingDivisors/StatementH.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PairingDivisors/StatementH.lean)
- **Role:** Arakelov Height & Local Valuation Bound Interface | **Depth-2:** `Formalism/PairingDivisors` | **Lines:** 139 | **Top-Dir Ext Fan-In:** 482 | **Depth-2 Ext Fan-In:** 482 | **Total In-Degree:** 484 (`dist=7`, `height=8`)
- **External Importers:** Top-dirs: `Development` (482) | Depth-2 dirs: `Development/AbelianVarietyTheory` (482)
- **Plain-English Mathematical Summary:** States the adelic product-formula and local-valuation height inequalities connecting non-archimedean divisibility valuations vA(w) to archimedean norm bounds of algebraic numbers a^12 / De^M and CM normalizing constants cmConst (HeightCore, HeightBoundOfLocalValuations, PlaceVaryingValuesBound, BBSize).
- **Key Exported Declarations:**
  - `def` [`SumValNat`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PairingDivisors/StatementH.lean#L19) (L19): Local log-valuation sum over finite places w of K for a natural number n equals log(n).
  - `def` [`HeightCore`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PairingDivisors/StatementH.lean#L30) (L30): Bounds sum_w lw * |vA(w)| in terms of the archimedean mean log norm of a^12 / De^M plus level error terms.
  - `def` [`HeightBoundOfLocalValuations`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PairingDivisors/StatementH.lean#L72) (L72): Extends HeightCore using CM constant normalization cmConst and Gamma factors to bound valuation sums by BB.
  - `def` [`BBSize`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PairingDivisors/StatementH.lean#L120) (L120): Explicit linear-in-b*(L + log x) asymptotic upper bound on the height constant BB.

#### [`Formalism/GaloisCohomology/LocalTateDualityK.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GaloisCohomology/LocalTateDualityK.lean)
- **Role:** Local & Global Galois Cohomology Duality | **Depth-2:** `Formalism/GaloisCohomology` | **Lines:** 65 | **Top-Dir Ext Fan-In:** 377 | **Depth-2 Ext Fan-In:** 380 | **Total In-Degree:** 380 (`dist=6`, `height=6`)
- **External Importers:** Top-dirs: `Development` (375), `CompanionTheory` (1), `ReciprocityTheory` (1) | Depth-2 dirs: `Development/AbelianVarietyTheory` (361), `Development/AutomorphicArithmetic` (13), `Formalism/SharpRestriction` (3), `CompanionTheory/AutomorphicTheory` (1)
- **Plain-English Mathematical Summary:** Exports global Selmer-submodule length preservation under restriction to ramification-restricted Galois groups GS(S) (SelAllLeInf, SelAllLen) alongside the full local Galois cohomology package over arbitrary finite extensions K / Q_l (CycKSpec, LocalFinitenessK, LocalTateDualityK via cup products H^0 x H^2 -> Z/l^r and H^1 x H^1 -> Z/l^r, and LocalEulerCharK).
- **Key Exported Declarations:**
  - `def` [`SelAllLeInf`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GaloisCohomology/LocalTateDualityK.lean#L10) (L10): Inclusions showing Selmer groups unramified outside S lie in the image of inflation from GS(S).
  - `def` [`LocalFinitenessK`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GaloisCohomology/LocalTateDualityK.lean#L41) (L41): Finiteness of H^0, H^1, H^2 and vanishing of H^n (n >= 3) for finite Z/l^r-representations of G_K.
  - `def` [`LocalTateDualityK`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GaloisCohomology/LocalTateDualityK.lean#L47) (L47): States H^2(G_K, mu_{l^r}) ~= Z/l^r and bijectivity of all local Tate cup-product pairings.
  - `def` [`LocalEulerCharK`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GaloisCohomology/LocalTateDualityK.lean#L57) (L57): Local Euler characteristic formula: |H^1| = |H^0| * |H^2| * |M|^[K:Q_l].

#### [`Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean)
- **Role:** Unitary Hecke Algebra & Compact Subgroup Library | **Depth-2:** `Formalism/SatakeDualWeyl` | **Lines:** 532 | **Top-Dir Ext Fan-In:** 305 | **Depth-2 Ext Fan-In:** 321 | **Total In-Degree:** 321 (`dist=7`, `height=10`)
- **External Importers:** Top-dirs: `Development` (303), `CompanionTheory` (2) | Depth-2 dirs: `Development/AbelianVarietyTheory` (291), `Formalism/LocalToGlobal` (8), `Development/AutomorphicArithmetic` (7), `Formalism/SharpRestriction` (5)
- **Plain-English Mathematical Summary:** Realizes and exports 40+ proved theorems on adelic unitary groups U(J)(A_F), compact open level subgroups (KpqSubgroupCompact, StabFinite, ClassSetFinite), Cartan decompositions (CartanDecomp, CartanUnique), Hecke operators T_j and their Satake transforms (SatakeTj, SatakeInert, SatMul), spherical functions, and Weyl-module stability.
- **Key Exported Declarations:**
  - `theorem` [`CartanDecomp`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean#L148) (L148): Cartan double-coset decomposition for local unitary groups.
  - `theorem` [`ClassSetFinite`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean#L151) (L151): Finiteness of double-coset class sets for adelic unitary groups.
  - `theorem` [`SatakeTj`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean#L156) (L156): Evaluates the Satake transform of the local unitary Hecke operator T_j.
  - `theorem` [`KpqSubgroupCompact`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean#L516) (L516): Proves compactness of the maximal compact subgroup K_{p,q} of the real unitary group.
  - `theorem` [`WeylGLStable`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SatakeDualWeyl/KpqSubgroupCompact.lean#L530) (L530): Stability of integral Weyl modules under the global GL action.

#### [`Formalism/RealPlaceAnalysis/ThirdArithmeticHolds.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/RealPlaceAnalysis/ThirdArithmeticHolds.lean)
- **Role:** Lie Algebra & Quantum Determinant Identities | **Depth-2:** `Formalism/RealPlaceAnalysis` | **Lines:** 87 | **Top-Dir Ext Fan-In:** 228 | **Depth-2 Ext Fan-In:** 233 | **Total In-Degree:** 235 (`dist=7`, `height=4`)
- **External Importers:** Top-dirs: `Development` (168), `CompanionTheory` (59), `ReciprocityTheory` (1) | Depth-2 dirs: `Development/AbelianVarietyTheory` (108), `Development/AutomorphicSpectrum` (53), `CompanionTheory/SpectralGeometry` (52), `Development/AutomorphicArithmetic` (7)
- **Plain-English Mathematical Summary:** Proves 18 algebraic and representation-theoretic identities for unitary gl_n-modules at archimedean places: Casimir eigenvalues on highest-weight vectors (casKHighest, casCentral), sum-of-squares and W-D Casimir identities (sumSq, wdCas), unitary spectral gap (uGap), Taylor analyticity bounds (growthIter, taylorRadius), and Capelli/quantum-determinant relations (qSkewRow, qDetHW, qDetCentral, qComatrix).
- **Key Exported Declarations:**
  - `theorem` [`wdCas`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/RealPlaceAnalysis/ThirdArithmeticHolds.lean#L19) (L19): Relates global Casimir, compact Casimir CasK, and noncompact root norm squares in a unitary representation.
  - `theorem` [`uGap`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/RealPlaceAnalysis/ThirdArithmeticHolds.lean#L64) (L64): Establishes the unitary spectral gap lower bound.
  - `theorem` [`taylorRadius`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/RealPlaceAnalysis/ThirdArithmeticHolds.lean#L66) (L66): Establishes convergence radius / summability of Taylor power series in Lie operators.
  - `theorem` [`qDetHW`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/RealPlaceAnalysis/ThirdArithmeticHolds.lean#L84) (L84): Evaluates the quantum determinant on highest-weight vectors.
  - `theorem` [`qDetCentral`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/RealPlaceAnalysis/ThirdArithmeticHolds.lean#L85) (L85): Proves centrality of the quantum determinant in the universal enveloping algebra.

#### [`Formalism/PeriodIntegrals/DSInfCharCap.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PeriodIntegrals/DSInfCharCap.lean)
- **Role:** Discrete Series Capelli Infinitesimal Character | **Depth-2:** `Formalism/PeriodIntegrals` | **Lines:** 47 | **Top-Dir Ext Fan-In:** 89 | **Depth-2 Ext Fan-In:** 89 | **Total In-Degree:** 91 (`dist=7`, `height=4`)
- **External Importers:** Top-dirs: `Development` (76), `CompanionTheory` (13) | Depth-2 dirs: `Development/AbelianVarietyTheory` (57), `Development/AutomorphicSpectrum` (18), `CompanionTheory/SpectralGeometry` (8), `CompanionTheory/AutomorphicTheory` (3)
- **Plain-English Mathematical Summary:** Constructs the complexified Lie algebra action actU on smooth vectors of discrete series representations IsDS of U(p, q) and states DSInfCharCap: the quantum determinant qdet(Egl n)(Y + (n-1)/2) acts on every smooth vector as the scalar Harish-Chandra infinitesimal character polynomial capP(lam, Y).
- **Key Exported Declarations:**
  - `def` [`dsigC`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PeriodIntegrals/DSInfCharCap.lean#L19) (L19): Complexified Lie algebra action combining symmetric and skew-symmetric parts under Cartan involution thetaJ.
  - `def` [`actU`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PeriodIntegrals/DSInfCharCap.lean#L33) (L33): Action of the free enveloping algebra of gl_n on smooth vectors.
  - `def` [`DSInfCharCap`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PeriodIntegrals/DSInfCharCap.lean#L40) (L40): Capelli identity equating the quantum determinant action on smooth discrete-series vectors to the scalar Harish-Chandra polynomial capP.

#### [`Formalism/GL3MeanSquares/PrimeCountAsymptoticInProgressions.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GL3MeanSquares/PrimeCountAsymptoticInProgressions.lean)
- **Role:** Siegel-Zero-Aware Prime Distribution & Character Cancellation | **Depth-2:** `Formalism/GL3MeanSquares` | **Lines:** 144 | **Top-Dir Ext Fan-In:** 84 | **Depth-2 Ext Fan-In:** 84 | **Total In-Degree:** 89 (`dist=7`, `height=2`)
- **External Importers:** Top-dirs: `Development` (84) | Depth-2 dirs: `Development/AbelianVarietyTheory` (84)
- **Plain-English Mathematical Summary:** States analytic number theory estimates for prime counting in arithmetic progressions possibly affected by a real Siegel zero beta < 1 (PrimeCountAsymptoticInProgressions, ZeroFreeSymmetric, ZeroSumBoundSmall, ZeroSumBoundLarge, PartialSumIntegralBound) together with Jacobi-symbol quadratic reciprocity cancellation lemmas (KronOdd, KronTwo, LamSumZero, MuConst, MuSmall) and square/prime-power remainder bounds (SizeR, SizeSpSq).
- **Key Exported Declarations:**
  - `def` [`ZeroFreeSymmetric`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GL3MeanSquares/PrimeCountAsymptoticInProgressions.lean#L34) (L34): Confines any zero of a real primitive Dirichlet L-function in |Im(s)| <= Q to the strip 1/400 <= Re(s) <= 1 - 1/400.
  - `def` [`PrimeCountAsymptoticInProgressions`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GL3MeanSquares/PrimeCountAsymptoticInProgressions.lean#L67) (L67): Asymptotic count of primes p <= Y in p == a (mod m) with explicit main term Emain(theta, beta, Y) allowing a single exceptional character beta.
  - `def` [`LamSumZero`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GL3MeanSquares/PrimeCountAsymptoticInProgressions.lean#L95) (L95): Exact cancellation of Jacobi symbols (b|s) over residue classes b == a_0 (mod m_0).
  - `def` [`SizeR`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GL3MeanSquares/PrimeCountAsymptoticInProgressions.lean#L133) (L133): Upper bound on the square and small-prime remainder sum Rsum(x, m_0).

#### [`Formalism/HermitianCurvature/StatementTBB.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/StatementTBB.lean)
- **Role:** Bergman-Kernel Curvature & Inductive Energy Estimates | **Depth-2:** `Formalism/HermitianCurvature` | **Lines:** 205 | **Top-Dir Ext Fan-In:** 55 | **Depth-2 Ext Fan-In:** 56 | **Total In-Degree:** 61 (`dist=10`, `height=19`)
- **External Importers:** Top-dirs: `Development` (53), `CompanionTheory` (2) | Depth-2 dirs: `Development/AbelianVarietyTheory` (53), `CompanionTheory/AutomorphicTheory` (2), `Formalism/LocalToGlobal` (1)
- **Plain-English Mathematical Summary:** Formulates the inductive energy-estimate pipeline (StepOne, StepUp, LemmaS, CorS, PtBound, ThmBpAt) for holomorphic sections of polarized vector bundles over Siegel/Hermitian spaces: propagates pointwise kernel bounds NP and energy integrals Ew along chains of local test points via dual lattice Fourier bounds (BlockGrowthBound) and weighted determinant regularity bounds (RegularityBoundBigCell).
- **Key Exported Declarations:**
  - `def` [`KernelFourierIntegralBound`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/StatementTBB.lean#L58) (L58): Fourier decay bound mn(Lambda, K, ||s||) on oscillatory integrals of the normalized kernel NP.
  - `def` [`BlockGrowthBound`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/StatementTBB.lean#L75) (L75): Poisson/lattice summation bound over Z x Z periods relating one-step higher energy sums to dual-lattice limsup bounds.
  - `def` [`StepOne`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/StatementTBB.lean#L137) (L137): Base step bounding first-stage energy Ew(j+1) by (3/pi)*Lambda^2 * Ew(j).
  - `def` [`StepUp`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/StatementTBB.lean#L145) (L145): Inductive step propagating pointwise energy bounds across block stages s >= 2.
  - `def` [`ThmBpAt`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/StatementTBB.lean#L130) (L130): Final pointwise Bergman-kernel bound in terms of Gram determinant Gp^(-2p0-n0) and L^2 energy jN2.

#### [`Formalism/GammaFactorNonvanishing/CritLine.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean)
- **Role:** Critical-Line Reflection Proof | **Depth-2:** `Formalism/GammaFactorNonvanishing` | **Lines:** 32 | **Top-Dir Ext Fan-In:** 1 | **Depth-2 Ext Fan-In:** 1 | **Total In-Degree:** 1 (`dist=4`, `height=90`)
- **External Importers:** Top-dirs: `Supplements` (1) | Depth-2 dirs: `Supplements/Kernels` (1)
- **Plain-English Mathematical Summary:** Proves that archimedean Gamma factors of Dirichlet characters are nonzero for Re(s) > 0, and deduces both critical-line localization for primitive Dirichlet L-functions (critLine) and Mathlib's RiemannHypothesis (rh_of_every) from half-plane nonvanishing UpperTheory.EveryCharacter.
- **Key Exported Declarations:**
  - `theorem` [`Formalism.VW.gammaFactor_ne_zero`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean#L6) (L6): Proves gammaFactor(chi, s) != 0 whenever Re(s) > 0 by parity case split.
  - `theorem` [`Formalism.VW.critLine`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean#L11) (L11): Proves every zero of a primitive Dirichlet L-function in 0 < Re(s) < 1 has Re(s) = 1/2 using completedLFunction_one_sub.
  - `theorem` [`Formalism.VW.rh_of_every`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean#L29) (L29): Deduces RiemannHypothesis by specializing EveryCharacter to the trivial character mod 1.

#### [`Formalism/ZetaRealNonvanish.lean`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/ZetaRealNonvanish.lean)
- **Role:** Mellin Transform & Landau Nonvanishing Setup | **Depth-2:** `Formalism` | **Lines:** 80 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 8 | **Total In-Degree:** 9 (`dist=12`, `height=1`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `Formalism/ZetaNonvanishing` (8)
- **Plain-English Mathematical Summary:** Exports the foundational complex-analytic specifications for the Chebyshev/Mellin approach to zeta(s) and real Dirichlet L-functions: Mellin transform differentiation (MellinDeriv), Landau's abscissa-of-convergence theorem for nonnegative functions (LandauLemma), the explicit Mellin transform of S(chi, x) (MellinS), real-axis nonvanishing statements for zeta and quadratic characters mod 3, 4, 7 (ZetaRealNonvanish, LRealNonvanish), and RHofHalfPlane.
- **Key Exported Declarations:**
  - `def` [`LandauLemma`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/ZetaRealNonvanish.lean#L20) (L20): Landau's theorem: the Mellin integral of a nonnegative function H converges up to the rightmost real singularity of its analytic continuation.
  - `def` [`MellinS`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/ZetaRealNonvanish.lean#L29) (L29): Identifies the Mellin transform of the weighted prime-power sum S(chi, x) with LSeries(LamF chi) / (s(s-1)).
  - `def` [`ZetaRealNonvanish`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/ZetaRealNonvanish.lean#L63) (L63): Statement that riemannZeta(sigma) != 0 for real 0 < sigma < 1.
  - `def` [`RHofHalfPlane`](file:///home/ubuntu/riemann_proof/lean/src/Formalism/ZetaRealNonvanish.lean#L74) (L74): Implication from zeta(s) != 0 on Re(s) > 1/2 to RiemannHypothesis.

### 4.5 `ReciprocityTheory` (3,845 files -> 1,503 top-dir interfaces, ratio `0.3909`)

#### [`ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean)
- **Role:** Top-Impact PEL-Shimura Uniformisation Contract | **Depth-2:** `ReciprocityTheory/ReductiveGroups` | **Lines:** 229 | **Top-Dir Ext Fan-In:** 2,379 | **Depth-2 Ext Fan-In:** 2,379 | **Total In-Degree:** 2,390 (`dist=6`, `height=9`)
- **External Importers:** Top-dirs: `Development` (2374), `Formalism` (5) | Depth-2 dirs: `Development/AbelianVarietyTheory` (2008), `Development/AutomorphicSpectrum` (315), `Development/WeilBound` (50), `Formalism/LocalToGlobal` (3)
- **Plain-English Mathematical Summary:** The single most imported interface file in the entire repository (2,379 external imports from Development and Formalism). Packages PEL-type Shimura toroidal boundary uniformisation (PELUnif, UniformisationConclusion, Model.N3), torsion identification with Mumford quotients compatible with O_E-action and Weil pairings (PELUnif.TorsionIso), formal-arc period data (TateIsoQ, ArcIn, Model.HasArcData, Model.N4), and the global toroidal compactification theorem PartI.
- **Key Exported Declarations:**
  - `structure` [`PELUnif`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L83) (L83): Packages degeneration data D, polarized abelian scheme A over Frac(R), uniformisation U, O_E-linearity, and trace-form twist.
  - `def` [`PELUnif.TorsionIso`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L101) (L101): Identifies k-torsion of the abelian scheme A with Mumford-Tate quotient points QkPt preserving addition, O_E-action, and Weil pairings.
  - `def` [`Model.N3`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L122) (L122): Boundary uniformisation over complete integrally closed Noetherian local rings around split-extension residue points.
  - `structure` [`ArcIn`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L144) (L144): Input package for formal power-series arcs Spec O'[[X]] with positive-definite Hermitian form be and Tate torsion data TateIsoQ.
  - `def` [`Model.N4`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L209) (L209): Existence and uniqueness of formal arcs Spec O'[[X]] -> Y.X carrying prescribed boundary arc data.
  - `def` [`PartI`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L223) (L223): Master toroidal compactification specification asserting integral models Y with split fibres, N2, N3, N4, and N6.

#### [`ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean)
- **Role:** Axiomatic Specification Contract | **Depth-2:** `ReciprocityTheory/ReductiveGroups` | **Lines:** 63 | **Top-Dir Ext Fan-In:** 2,283 | **Depth-2 Ext Fan-In:** 2,283 | **Total In-Degree:** 2,284 (`dist=7`, `height=15`)
- **External Importers:** Top-dirs: `Development` (2283) | Depth-2 dirs: `Development/AbelianVarietyTheory` (2283)
- **Plain-English Mathematical Summary:** Second-highest external fan-in file in the codebase (2,283 external imports from Development). States UnifUniqSt (wrapped in Laws6): uniqueness of Mumford semiabelian uniformisations U, U' sharing the same polarized semiabelian scheme G and compatible rigidified line bundle isomorphism wL, giving a canonical isomorphism of degeneration data compatible with theta sections, thick-level coordinates, and O-actions.
- **Key Exported Declarations:**
  - `def` [`UnifUniqSt`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L17) (L17): Uniqueness up to canonical isomorphism of Mumford degeneration and uniformisation data over an admissible local base (R, I).
  - `structure` [`Laws6`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L60) (L60): Single-field Prop wrapper exporting UnifUniqSt.

#### [`ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean)
- **Role:** Toroidal Level & Hecke Compatibility Contract | **Depth-2:** `ReciprocityTheory/ReductiveGroups` | **Lines:** 95 | **Top-Dir Ext Fan-In:** 1,429 | **Depth-2 Ext Fan-In:** 1,429 | **Total In-Degree:** 1,429 (`dist=7`, `height=6`)
- **External Importers:** Top-dirs: `Development` (1425), `Formalism` (4) | Depth-2 dirs: `Development/AbelianVarietyTheory` (1273), `Development/AutomorphicSpectrum` (126), `Development/WeilBound` (25), `Formalism/LocalToGlobal` (4)
- **Plain-English Mathematical Summary:** Third-highest external fan-in file (1,429 external imports). Defines congruence-level automorphisms (Sim, Moduli.LevAut), finite etale level-compatibility across dividing levels (ToroidalLevelCompatibility), prime-to-level Hecke kernel subgroups (SAB.HeckeKer) and prime-to-level Hecke correspondences on toroidal compactifications (ToroidalHeckeCompatibility), bundled into N1.
- **Key Exported Declarations:**
  - `structure` [`Sim`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean#L18) (L18): Compatible family of O_E-linear level-n similitudes of the lattice D.La preserving the symplectic form up to nu(n).
  - `def` [`ToroidalLevelCompatibility`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean#L37) (L37): Existence of finite etale level-transition morphisms between toroidal models Xo_2 -> Xo with Galois/LevAut quotient fibers.
  - `def` [`SAB.HeckeKer`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean#L59) (L59): Characterizes isotropic O_E-stable Hecke kernel subgroups C of p-torsion with prescribed cardinality.
  - `def` [`ToroidalHeckeCompatibility`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean#L73) (L73): Constructs unique Hecke-isogenous target points y'' on Xo.X with Weil pairing scaling by p^2.
  - `def` [`N1`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/HeckeKer.lean#L91) (L91): Combines moduli nonemptiness N1ab with level and Hecke compatibility.

#### [`ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean)
- **Role:** Abelian Scheme Cohomology & Base Change Contract | **Depth-2:** `ReciprocityTheory/ReductiveGroups` | **Lines:** 79 | **Top-Dir Ext Fan-In:** 1,337 | **Depth-2 Ext Fan-In:** 1,337 | **Total In-Degree:** 1,340 (`dist=7`, `height=11`)
- **External Importers:** Top-dirs: `Development` (1337) | Depth-2 dirs: `Development/AbelianVarietyTheory` (1337)
- **Plain-English Mathematical Summary:** Fourth-highest external fan-in file (1,337 external imports). States four foundational theorems/laws for polarized abelian schemes (Laws2): local existence of base-change-compatible global section bases of L^n (SecBaseChangeAnySt), base-change and residue lifting for twisted bundles L^(q-1) otimes t_c^* L (SecTwistSt), Weil-pairing character duality for N-torsion over algebraically closed fields (CharPairSt), and density of the smooth locus (SmoothDenseSt).
- **Key Exported Declarations:**
  - `def` [`SecBaseChangeAnySt`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean#L16) (L16): Local freeness and arbitrary-base-change compatibility for H^0(A, L^n) of rank n^g over any base scheme S.
  - `def` [`SecTwistSt`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean#L49) (L49): Existence of global section bases and residue-field lifts for translated/twisted bundles L^(q-1) otimes t_c^* L over local rings.
  - `def` [`CharPairSt`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean#L60) (L60): Represents every homomorphism from N-torsion points to units via Weil pairing with a unique N-torsion point b.
  - `structure` [`Laws2`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/SecBaseChangeAnySt.lean#L73) (L73): Packages SecBaseChangeAnySt, SecTwistSt, CharPairSt, and SmoothDenseSt.

#### [`ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean)
- **Role:** Complex-Analytic Shimura Uniformisation Contract | **Depth-2:** `ReciprocityTheory/ReductiveGroups` | **Lines:** 116 | **Top-Dir Ext Fan-In:** 1,203 | **Depth-2 Ext Fan-In:** 1,203 | **Total In-Degree:** 1,206 (`dist=7`, `height=7`)
- **External Importers:** Top-dirs: `Development` (1201), `Formalism` (2) | Depth-2 dirs: `Development/AbelianVarietyTheory` (1151), `Development/AutomorphicSpectrum` (46), `Development/WeilBound` (4), `Formalism/LocalToGlobal` (2)
- **Plain-English Mathematical Summary:** Fifth-highest external fan-in file (1,203 external imports). Formulates complex-analytic uniformisation of unitary Shimura varieties: polarized CM-type period maps (IsTypeFn, IsPeriod), holomorphic period families (IsHolPeriods), tangent-space identification via dual numbers (IsDerivAt0), Riemann theta frames (IsThetaFrame), and the global complex uniformisation bundle FamilyUnif / N1c.
- **Key Exported Declarations:**
  - `def` [`IsPeriod`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean#L16) (L16): Defines a period lattice map D.La -> C^g compatible with O_E-embeddings and positive-definite Hermitian Riemann form matching D.EF.
  - `def` [`IsThetaFrame`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean#L37) (L37): Matches pullbacks of algebraic rigidified line-bundle sections along complex uniformisations with analytic theta series.
  - `structure` [`FamilyUnif`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean#L51) (L51): Complete analytic uniformisation of the complex fiber Xo.X_sigma by period lattices across connected components, including holomorphic lifts and theta functions.
  - `def` [`N1c`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/IsHolPeriods.lean#L111) (L111): Asserts existence of FamilyUnif at every complex embedding sigma of KA(l).

#### [`ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean)
- **Role:** Abelian Scheme Foundations Contract | **Depth-2:** `ReciprocityTheory/ReductiveGroups` | **Lines:** 213 | **Top-Dir Ext Fan-In:** 698 | **Depth-2 Ext Fan-In:** 698 | **Total In-Degree:** 713 (`dist=7`, `height=10`)
- **External Importers:** Top-dirs: `Development` (695), `Formalism` (3) | Depth-2 dirs: `Development/AbelianVarietyTheory` (396), `Development/AutomorphicSpectrum` (282), `Development/WeilBound` (17), `Formalism/SharpRestriction` (3)
- **Plain-English Mathematical Summary:** Defines the 24-field foundational algebraic-geometry contract Laws for polarized abelian schemes over arbitrary schemes: Riemann-Roch rank dim H^0(A, L^n) = n^g (GlobalSectionsRankAlgClosed), base change (SecBaseChangeSt), ampleness/projectivity (AmpleSt), Theorem of the Cube and Square (CubeSt, SquareSt), Rigidity (RigiditySt), Weil pairing nondegeneracy (WeilNondegSt), Mumford's theta-group irreducibility (IrredSt), Serre's torsion-rigidity lemma (SerreSt), finite-flat quotients (QuotientSt), and unramified complete DVR lifts (UnramExtSt).
- **Key Exported Declarations:**
  - `def` [`GlobalSectionsRankAlgClosed`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L19) (L19): States finrank_k H^0(A, L^n) = n^g over algebraically closed fields for n >= 1.
  - `def` [`IrredSt`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L126) (L126): Irreducibility of the finite theta-group action on H^0(A, L^k) for k = 1 or k >= 4.
  - `def` [`SerreSt`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L143) (L143): Serre's lemma: an automorphism of a polarized abelian scheme fixing M-torsion (M >= 3) pointwise is the identity.
  - `def` [`QuotientSt`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L166) (L166): Existence of abelian scheme quotients P.A / H by finite flat subgroup schemes H.
  - `structure` [`Laws`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L187) (L187): Master 24-law algebraic geometry contract for polarized abelian schemes.

#### [`ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean)
- **Role:** Quasi-Excellent Resolution & Log-Resolution Interface | **Depth-2:** `ReciprocityTheory/AnalyticForms` | **Lines:** 130 | **Top-Dir Ext Fan-In:** 563 | **Depth-2 Ext Fan-In:** 563 | **Total In-Degree:** 568 (`dist=7`, `height=0`)
- **External Importers:** Top-dirs: `Development` (563) | Depth-2 dirs: `Development/AbelianVarietyTheory` (562), `Development/AutomorphicArithmetic` (1)
- **Plain-English Mathematical Summary:** Defines resolution of singularities and log-resolution specifications for Noetherian reduced quasi-excellent schemes (QERing, QE) with finite-Frobenius residue fields (FFinRes): Cartier blowups (Blowup), simple normal crossings (Snc, LSncAt), and global/local log-resolution theorems GFR, GFLogR, GFLogStR, LocLog0R.
- **Key Exported Declarations:**
  - `def` [`Blowup`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean#L10) (L10): Universal property of blowing up an ideal sheaf I on a scheme X.
  - `def` [`QERing`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean#L29) (L29): Grothendieck's quasi-excellence axioms: Noetherian, geometrically regular formal completion fibers, and open regular loci.
  - `def` [`GFR`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean#L61) (L61): Resolution of singularities for reduced Noetherian quasi-excellent schemes with finite Frobenius residue fields.
  - `def` [`GFLogStR`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/AnalyticForms/RegularLocalRings/FinalTheorems.lean#L108) (L108): Strong log-resolution leaving the pre-existing simple normal crossings locus untouched.

#### [`ReciprocityTheory/DualLattices/TowerZeroSurjective.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/DualLattices/TowerZeroSurjective.lean)
- **Role:** p-adic Tower & Hodge-Tate Link Interface | **Depth-2:** `ReciprocityTheory/DualLattices` | **Lines:** 63 | **Top-Dir Ext Fan-In:** 193 | **Depth-2 Ext Fan-In:** 193 | **Total In-Degree:** 202 (`dist=9`, `height=8`)
- **External Importers:** Top-dirs: `Development` (193) | Depth-2 dirs: `Development/AbelianVarietyTheory` (178), `Development/AutomorphicSpectrum` (11), `Development/WeilBound` (3), `Development/AutomorphicArithmetic` (1)
- **Plain-English Mathematical Summary:** Defines the structure Dat packaging a formal chart at zero, Witt/weight data, finite-level approximations FIN, O_e-actions, Hodge-Tate data, and a tower surjection Tw.q 0 whose kernel is generated by p (tower_zero_surjective, tower_zero_ker), plus evaluation maps evAll and spans evImg on p-torsion neighborhoods Nb p g.
- **Key Exported Declarations:**
  - `structure` [`Dat`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/DualLattices/TowerZeroSurjective.lean#L13) (L13): Bundles formal chart, tower surjectivity mod p, Hodge-Tate data, and finite-level evaluation maps.
  - `def` [`evAll`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/DualLattices/TowerZeroSurjective.lean#L54) (L54): Evaluates finite-level coordinate sections on p-torsion neighborhood points Nb p g into a field C.
  - `def` [`evImg`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/DualLattices/TowerZeroSurjective.lean#L58) (L58): Submodule spanned by the evaluation maps evAll.

#### [`ReciprocityTheory/ThetaQuasiPeriods/ThetaQuasiPeriodStatement.lean`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ThetaQuasiPeriods/ThetaQuasiPeriodStatement.lean)
- **Role:** Riemann Theta Function Axioms | **Depth-2:** `ReciprocityTheory/ThetaQuasiPeriods` | **Lines:** 88 | **Top-Dir Ext Fan-In:** 55 | **Depth-2 Ext Fan-In:** 56 | **Total In-Degree:** 58 (`dist=8`, `height=1`)
- **External Importers:** Top-dirs: `Development` (55) | Depth-2 dirs: `Development/AbelianVarietyTheory` (54), `Development/AutomorphicArithmetic` (1), `ReciprocityTheory/ReductiveGroups` (1)
- **Plain-English Mathematical Summary:** Exports 15 specification statements for multivariable Riemann theta functions with real characteristics (a, b) on the Siegel upper half-space SiegelH and ThetaDomain: absolute summability, Weierstrass M-test, holomorphicity in (z, tau), quasi-periodicity under lattice shifts (ThetaQuasiPeriodStatement), real/half-integer characteristic shifts, GL_n(Z) modular transformation (ThetaGLStatement), block-diagonal splitting (ThetaBlockStatement), and genus-1 identification with jacobiTheta_2.
- **Key Exported Declarations:**
  - `def` [`ThetaHoloStatement`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ThetaQuasiPeriods/ThetaQuasiPeriodStatement.lean#L25) (L25): Complex differentiability of theta(a, b, z, tau) on C^g x ThetaDomain.
  - `def` [`ThetaQuasiPeriodStatement`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ThetaQuasiPeriods/ThetaQuasiPeriodStatement.lean#L30) (L30): Quasi-periodicity transformation of theta(a, b, z, tau) under z -> z + tau*n + n'.
  - `def` [`ThetaGLStatement`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ThetaQuasiPeriods/ThetaQuasiPeriodStatement.lean#L67) (L67): Symplectic GL_g(Z) change-of-variables identity transforming tau -> U tau U^T.
  - `def` [`ThetaBlockStatement`](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ThetaQuasiPeriods/ThetaQuasiPeriodStatement.lean#L76) (L76): Decomposition of a block-matrix theta function into a series of lower-genus theta functions.

### 4.6 `GroundTheory` (8,507 files -> 2,178 top-dir interfaces, ratio `0.2560`)

#### [`GroundTheory/HeightsAndTheta/Heights/DiscreteValuationNumbers/StatementsFlagIndependence.lean`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/DiscreteValuationNumbers/StatementsFlagIndependence.lean)
- **Role:** Intersection / Pairing Number Flag Independence | **Depth-2:** `GroundTheory/HeightsAndTheta` | **Lines:** 65 | **Top-Dir Ext Fan-In:** 199 | **Depth-2 Ext Fan-In:** 199 | **Total In-Degree:** 204 (`dist=12`, `height=4`)
- **External Importers:** Top-dirs: `Development` (199) | Depth-2 dirs: `Development/AutomorphicSpectrum` (173), `Development/WeilBound` (26)
- **Plain-English Mathematical Summary:** States Arakelov/DVR vertical-intersection pairing independence theorems: invariance of local pairing numbers pairNum under different polynomial expansions of a homogeneous form A (PairNumberExpansionIndependence.Statement), invariance under changing the flag of a ChartBundle on the generic fibre for complete symmetric polynomials hsymmTimes (HsymmPairFlagIndependence.Statement), and spanning of symmetric homogeneous polynomials by hsymmPart.
- **Key Exported Declarations:**
  - `def` [`PairNumberExpansionIndependence.Statement`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/DiscreteValuationNumbers/StatementsFlagIndependence.lean#L11) (L11): Pairing numbers pairNum over a DVR model do not depend on the choice of pair expansion As vs Bs of a homogeneous polynomial A.
  - `def` [`HsymmPairFlagIndependence.Statement`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/DiscreteValuationNumbers/StatementsFlagIndependence.lean#L26) (L26): Complete-symmetric pairing numbers are independent of the choice of coordinate flag on generically isomorphic chart bundles B, B'.
  - `def` [`SymmetricSpanHsymm.Statement`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/DiscreteValuationNumbers/StatementsFlagIndependence.lean#L48) (L48): Every homogeneous symmetric polynomial over Z lies in the Z-span of products of complete homogeneous symmetric polynomials.

#### [`GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean)
- **Role:** Arakelov Hermitian Vector Bundle & Slope Interface | **Depth-2:** `GroundTheory/HeightsAndTheta` | **Lines:** 123 | **Top-Dir Ext Fan-In:** 167 | **Depth-2 Ext Fan-In:** 169 | **Total In-Degree:** 182 (`dist=9`, `height=0`)
- **External Importers:** Top-dirs: `Development` (167) | Depth-2 dirs: `Development/AutomorphicSpectrum` (163), `Development/WeilBound` (4), `GroundTheory/PowerSubgroups` (2)
- **Plain-English Mathematical Summary:** Defines Hermitian lattices (HermLattice) over number fields K (finitely generated full O_K-lattices with conjugation-equivariant positive-definite metrics at all complex embeddings), their Arakelov subDegrees, quotDegrees, slopes, and lineDegrees, and states the Bost/Zhang-style slope bounds OrthogonalLines.Statement and LineOfLargeDegree.Statement (existence of a small-height nonzero vector after finite field extension).
- **Key Exported Declarations:**
  - `structure` [`HermLattice`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L24) (L24): Arakelov Hermitian vector bundle over O_K: projective/lattice O_K-submodule in K^n with positive-definite Hermitian metrics at infinite places.
  - `def` [`subDegree`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L34) (L34): Arakelov degree of a sublattice generated by u via log generalized index minus 1/2 log Gram determinant.
  - `def` [`OrthogonalLines.Statement`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L75) (L75): Lower bound k*mu <= quotDegree for diagonal Hermitian ideal lattices whose coordinate lines have slope >= mu.
  - `def` [`LineOfLargeDegree.Statement`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L85) (L85): Existence of a nonzero vector v over an extension K'/K with lineDegree >= slope(F) - (1/2)log(i) - eps.

#### [`GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean)
- **Role:** Whittaker Multiplicity-One Proof | **Depth-2:** `GroundTheory/AutomorphicForms` | **Lines:** 106 | **Top-Dir Ext Fan-In:** 127 | **Depth-2 Ext Fan-In:** 127 | **Total In-Degree:** 128 (`dist=9`, `height=34`)
- **External Importers:** Top-dirs: `Development` (127) | Depth-2 dirs: `Development/AbelianVarietyTheory` (124), `Development/AutomorphicArithmetic` (3)
- **Plain-English Mathematical Summary:** Proves the Shalika/Piatetski-Shapiro theorem (eq_zero_of_whittaker_eq_zero) for smooth cuspidal automorphic forms on GL_n(A_K): by upward induction on k from 1 to n using Fourier expansions along unipotent rows (partialCoeff_succ_eq_zero), if all Whittaker coefficients of a cusp form phi vanish identically, then phi itself vanishes identically.
- **Key Exported Declarations:**
  - `theorem` [`partialCoeff_succ_eq_zero`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L17) (L17): Inductive Fourier-expansion step showing vanishing of k-th partial Fourier coefficients implies vanishing of (k+1)-st partial coefficients for a cusp form.
  - `theorem` [`eq_zero_of_whittaker_eq_zero`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L77) (L77): Proves a smooth left-invariant cuspidal automorphic form on GL_n(A_K) with identically zero Whittaker function is zero.

#### [`GroundTheory/LocalFields/QuadraticAbelian/WeilRepQuadratic.lean`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/LocalFields/QuadraticAbelian/WeilRepQuadratic.lean)
- **Role:** Local Quadratic Extension & Norm Character Library | **Depth-2:** `GroundTheory/LocalFields` | **Lines:** 304 | **Top-Dir Ext Fan-In:** 96 | **Depth-2 Ext Fan-In:** 96 | **Total In-Degree:** 96 (`dist=7`, `height=23`)
- **External Importers:** Top-dirs: `Development` (96) | Depth-2 dirs: `Development/AutomorphicSpectrum` (96)
- **Plain-English Mathematical Summary:** Develops the local class-field/valuation theory of separable quadratic extensions E/K of non-archimedean local fields: proves E/K is Galois of order 2 with conjugation conj, shows conjugation preserves valuations, Haar measure, and modulus, proves index [K^x : N(E^x)] = 2 and openness of the norm subgroup, and defines the associated quadratic character quadChar : K^x -> C^x.
- **Key Exported Declarations:**
  - `def` [`conj`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/LocalFields/QuadraticAbelian/WeilRepQuadratic.lean#L56) (L56): The unique nontrivial K-automorphism of a separable quadratic field extension E/K.
  - `theorem` [`modulus_norm`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/LocalFields/QuadraticAbelian/WeilRepQuadratic.lean#L195) (L195): Equates local field modulus of Norm_{E/K}(x) in K to the modulus of x in E.
  - `theorem` [`index_range_normUnits_eq_two`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/LocalFields/QuadraticAbelian/WeilRepQuadratic.lean#L219) (L219): Proves the norm subgroup N_{E/K}(E^x) has index 2 in K^x.
  - `def` [`quadChar`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/LocalFields/QuadraticAbelian/WeilRepQuadratic.lean#L248) (L248): Defines the quadratic character K^x -> C^x with kernel equal to the norm subgroup N(E^x).

#### [`GroundTheory/GlobalFields/IdeleGroups/IdeleNorms.lean`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/GlobalFields/IdeleGroups/IdeleNorms.lean)
- **Role:** Adelic & Idelic Norm Product Formula Library | **Depth-2:** `GroundTheory/GlobalFields` | **Lines:** 259 | **Top-Dir Ext Fan-In:** 47 | **Depth-2 Ext Fan-In:** 49 | **Total In-Degree:** 53 (`dist=8`, `height=1`)
- **External Importers:** Top-dirs: `Development` (47) | Depth-2 dirs: `Development/AbelianVarietyTheory` (44), `Development/AutomorphicArithmetic` (1), `Development/AutomorphicSpectrum` (1), `Development/WeilBound` (1)
- **Plain-English Mathematical Summary:** Constructs the continuous surjective idelic module homomorphism ideleModule : IdeleGroup K -> R_{>0} as the product of infinite-place moduli and finite-place p-adic norms, proves it vanishes on principal ideles K^x via the product formula (ideleModule_diagonal), and defines the closed norm-one subgroup normOneSubgroup on both the idele group and idele class group.
- **Key Exported Declarations:**
  - `def` [`ideleModule`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/GlobalFields/IdeleGroups/IdeleNorms.lean#L88) (L88): Multiplicative idelic norm homomorphism (infiniteModule * finiteModule) : IdeleGroup K -> R_{>0}.
  - `theorem` [`ideleModule_surjective`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/GlobalFields/IdeleGroups/IdeleNorms.lean#L154) (L154): Proves surjectivity of ideleModule onto R_{>0}.
  - `theorem` [`ideleModule_diagonal`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/GlobalFields/IdeleGroups/IdeleNorms.lean#L192) (L192): Product formula: principal ideles lie in the kernel of ideleModule.
  - `def` [`normOneSubgroup`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/GlobalFields/IdeleGroups/IdeleNorms.lean#L241) (L241): Norm-1 subgroup C_K^1 of the idele class group (in namespace IdeleClassGroup).

#### [`GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean)
- **Role:** Global Galois Cohomology & Poitou-Tate Duality Proof | **Depth-2:** `GroundTheory/ProfiniteCohomology` | **Lines:** 71 | **Top-Dir Ext Fan-In:** 19 | **Depth-2 Ext Fan-In:** 19 | **Total In-Degree:** 21 (`dist=8`, `height=61`)
- **External Importers:** Top-dirs: `Development` (19) | Depth-2 dirs: `Development/WeilBound` (19)
- **Plain-English Mathematical Summary:** Proves the classical Poitou-Tate theorems for finite Z/NZ-modules M over the Galois group G_{K,S} unramified outside a finite set of places S containing primes dividing N (assuming N odd or K totally complex): Poitou-Tate compact duality (poitouTate_duality_gs), finiteness and perfect pairing of Tate-Shafarevich groups Sha^1 and Sha^2 (poitouTate_sha_gs), and exactness of the nine-term Poitou-Tate sequence (poitouTate_nineTerm_gs).
- **Key Exported Declarations:**
  - `theorem` [`poitouTate_duality_gs`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L36) (L36): Proves bijectivity of the Poitou-Tate compact-support duality map in degrees r + s = 3.
  - `theorem` [`poitouTate_sha_gs`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L42) (L42): Proves finiteness of Sha^1(G_{K,S}, M) and Sha^2(G_{K,S}, M^*(1)) and nondegeneracy of the Poitou-Tate Sha pairing.
  - `theorem` [`poitouTate_nineTerm_gs`](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L50) (L50): Proves exactness of the full 9-term Poitou-Tate sequence from H^0 through H^2 and its duals.

### 4.7 `CompanionTheory` (2,027 files -> 402 top-dir interfaces, ratio `0.1983`)

#### [`CompanionTheory/EightfoldTheory/VariationTheory/AutomorphicForms/Newform.lean`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/EightfoldTheory/VariationTheory/AutomorphicForms/Newform.lean)
- **Role:** 1-Line Re-Export Facade | **Depth-2:** `CompanionTheory/EightfoldTheory` | **Lines:** 1 | **Top-Dir Ext Fan-In:** 248 | **Depth-2 Ext Fan-In:** 248 | **Total In-Degree:** 248 (`dist=10`, `height=10`)
- **External Importers:** Top-dirs: `Development` (248) | Depth-2 dirs: `Development/AbelianVarietyTheory` (248)
- **Plain-English Mathematical Summary:** A 1-line pure import facade ('import Development.AutomorphicArithmetic.AutomorphicVarieties.AutomorphicForms.Newform') with zero local declarations, acting as a cross-directory alias imported 248 times by Development modules (exemplifying the thin 9-file EightfoldTheory re-export layer).
- **Key Exported Declarations:** No local `theorem`/`def`/`structure` declarations (pure import barrel / command directive).

#### [`CompanionTheory/SpectralGeometry/CountingDefinitions/AdelicEulerProducts/IsEulerProd.lean`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/CountingDefinitions/AdelicEulerProducts/IsEulerProd.lean)
- **Role:** Adelic Siegel-Weil Euler Product Interface | **Depth-2:** `CompanionTheory/SpectralGeometry` | **Lines:** 125 | **Top-Dir Ext Fan-In:** 109 | **Depth-2 Ext Fan-In:** 110 | **Total In-Degree:** 378 (`dist=6`, `height=2`)
- **External Importers:** Top-dirs: `Development` (109) | Depth-2 dirs: `Development/AutomorphicSpectrum` (103), `Development/WeilBound` (5), `CompanionTheory/AutomorphicTheory` (1), `Development/AutomorphicArithmetic` (1)
- **Plain-English Mathematical Summary:** Defines the measure-theoretic framework for the regularized/convergent unitary Siegel-Weil formula: local coordinate measures on R otimes_F E and Hermitian matrices HermR (coordK, coordW, coordHerm), Gram-matrix fiber disintegration measures (IsGramFib), global orbital theta-counting measure (thetaMeas), Euler-product factorization of adelic test-function integrals (IsEulerProd), and the Siegel-Weil measure identity statement SWMeas.
- **Key Exported Declarations:**
  - `def` [`IsGramFib`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/CountingDefinitions/AdelicEulerProducts/IsEulerProd.lean#L61) (L61): Disintegration of Lebesgue/Haar measure on matrix space along the Hermitian Gram map gramR into fiber measures over HermR.
  - `def` [`thetaMeas`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/CountingDefinitions/AdelicEulerProducts/IsEulerProd.lean#L84) (L84): Adelic orbital measure obtained by pushing forward Haar measure on U(J)(F)\U(J)(A) over rational solutions X.
  - `def` [`IsEulerProd`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/CountingDefinitions/AdelicEulerProducts/IsEulerProd.lean#L99) (L99): Defines when an adelic measure I factors into an infinite Euler product of local fiber measures m_v and archimedean measure m_inf.
  - `def` [`SWMeas`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/CountingDefinitions/AdelicEulerProducts/IsEulerProd.lean#L111) (L111): Measure-level Siegel-Weil identity equating thetaMeas on {gram = T} to the Euler product of local Gram-fiber measures.

#### [`CompanionTheory/SpectralGeometry/LocalGlobalProofs/AdelicAnalysis/TensorLocallyCompactRingStatement.lean`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/LocalGlobalProofs/AdelicAnalysis/TensorLocallyCompactRingStatement.lean)
- **Role:** Topological Ring Tensor Bridge | **Depth-2:** `CompanionTheory/SpectralGeometry` | **Lines:** 8 | **Top-Dir Ext Fan-In:** 103 | **Depth-2 Ext Fan-In:** 105 | **Total In-Degree:** 171 (`dist=10`, `height=4`)
- **External Importers:** Top-dirs: `Development` (103) | Depth-2 dirs: `Development/AutomorphicSpectrum` (94), `Development/WeilBound` (9), `CompanionTheory/AutomorphicTheory` (2)
- **Plain-English Mathematical Summary:** Proves the topological and measure-theoretic foundation theorem GlobalTheory.T.tensor_locally_compact_ring: for any CM extension E/F and locally compact second-countable T2 topological F-algebra R, R otimes_F E inherits topological ring structure, local compactness, Borel measurability, continuity of involution/trace/Gram maps, and closedness of the Hermitian matrix locus HermR.
- **Key Exported Declarations:**
  - `theorem` [`_root_.GlobalTheory.T.tensor_locally_compact_ring`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry/LocalGlobalProofs/AdelicAnalysis/TensorLocallyCompactRingStatement.lean#L7) (L7): Proves R otimes_F E is locally compact, second-countable, and T2 with continuous trace, involution, and Hermitian Gram maps.

#### [`CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean)
- **Role:** Harish-Chandra Infinitesimal Character Proof | **Depth-2:** `CompanionTheory/HarishChandraModules` | **Lines:** 72 | **Top-Dir Ext Fan-In:** 46 | **Depth-2 Ext Fan-In:** 51 | **Total In-Degree:** 52 (`dist=7`, `height=27`)
- **External Importers:** Top-dirs: `Development` (46) | Depth-2 dirs: `Development/AbelianVarietyTheory` (42), `CompanionTheory/AutomorphicTheory` (3), `Development/AutomorphicSpectrum` (2), `CompanionTheory/RealGroups` (1)
- **Plain-English Mathematical Summary:** Assembles 31 intermediate algebraic and analytic steps (chain CAR, Koszul resolution, Verma covers, Casselman-Osborne, PRV highest-weight bounds, smooth module brackets, K-finite stability) to prove PI.DSInfCharCap.DSInfCharCap: the Capelli/quantum-determinant infinitesimal character identity for discrete series representations of U(p, q).
- **Key Exported Declarations:**
  - `theorem` [`hCO`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L44) (L44): Casselman-Osborne theorem for Lie algebra cohomology in the discrete-series setup.
  - `theorem` [`hAlgCore`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L54) (L54): Core algebraic Capelli identity on K-finite / Verma modules.
  - `theorem` [`discrete_series_infinitesimal_character`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L68) (L68): Unconditionally proves DSInfCharCap for all smooth vectors of discrete series representations of U(p, q).

#### [`CompanionTheory/AutomorphicTheory/TemperedLocalSpectra/ObstructionLifting/H1StructureDimLe.lean`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/AutomorphicTheory/TemperedLocalSpectra/ObstructionLifting/H1StructureDimLe.lean)
- **Role:** Picard / Abelian Duality & Descent Interface | **Depth-2:** `CompanionTheory/AutomorphicTheory` | **Lines:** 148 | **Top-Dir Ext Fan-In:** 0 | **Depth-2 Ext Fan-In:** 51 | **Total In-Degree:** 58 (`dist=19`, `height=91`)
- **External Importers:** Top-dirs: None (apex) | Depth-2 dirs: `CompanionTheory/SpectralGeometry` (51)
- **Plain-English Mathematical Summary:** Formulates the geometric descent and Picard-functor duality toolkit for abelian schemes (used in proving existence and properties of dual abelian varieties): H^1(A, O_A) dimension bound <= g (H1StructureDimLe), closedness and flatness of triviality loci of line bundles on A x Y (IsTrivLocus, TrivLocus, FewEquations, TrivLocusFlat), Hilbert 90 and rigidified line-bundle descent (H90, RigDescent), and existence of dual polarized abelian schemes (Construct, FinDual, DualPol).
- **Key Exported Declarations:**
  - `def` [`H1StructureDimLe`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/AutomorphicTheory/TemperedLocalSpectra/ObstructionLifting/H1StructureDimLe.lean#L17) (L17): Bounds dim_k H^1(A, O_A) <= g for a g-dimensional abelian scheme over a field.
  - `def` [`TrivLocus`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/AutomorphicTheory/TemperedLocalSpectra/ObstructionLifting/H1StructureDimLe.lean#L25) (L25): Existence of a closed subscheme Z -> Y representing the locus where a line bundle N on A x Y is fiberwise trivial.
  - `def` [`RigDescent`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/AutomorphicTheory/TemperedLocalSpectra/ObstructionLifting/H1StructureDimLe.lean#L92) (L92): Faithfully flat descent for rigidified line bundles on A x X.
  - `def` [`DualPol`](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/AutomorphicTheory/TemperedLocalSpectra/ObstructionLifting/H1StructureDimLe.lean#L138) (L138): Existence of a dual abelian scheme B with Poincaré biextension P for any polarized abelian scheme (A, L).

### 4.8 `PositivityTheory` (449 files -> 170 top-dir interfaces, ratio `0.3786`)

#### [`PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/KFiniteVectors/KFiniteThetaLifts/RationalPrimesBelowPlaces.lean`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/KFiniteVectors/KFiniteThetaLifts/RationalPrimesBelowPlaces.lean)
- **Role:** Quadratic Base Change GL(3) x GL(2) Interface | **Depth-2:** `PositivityTheory/AutomorphicForms` | **Lines:** 106 | **Top-Dir Ext Fan-In:** 160 | **Depth-2 Ext Fan-In:** 160 | **Total In-Degree:** 161 (`dist=7`, `height=57`)
- **External Importers:** Top-dirs: `Development` (160) | Depth-2 dirs: `Development/AutomorphicSpectrum` (160)
- **Plain-English Mathematical Summary:** Defines the local-global Rankin-Selberg / quadratic base-change specification for GL(3) x GL(2) over quadratic fields K/Q: rational-prime indexing (RationalPrimesBelowPlaces), Euler-product grouping (REGRP), Casselman-Shalika unramified zeta-integral evaluation (CasselmanShalikaGL3GL2), local functional equations (LFEV), theta-lift/Eisenstein-like global Rankin-Selberg unfolding (EXP, DEC, ENT, GFE, UNF), and Euler factorization (FAC).
- **Key Exported Declarations:**
  - `def` [`BCEX`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/KFiniteVectors/KFiniteThetaLifts/RationalPrimesBelowPlaces.lean#L21) (L21): Existence of quadratic base change DK of a GL(3)/Q cusp-form datum D to K.
  - `def` [`RationalPrimesBelowPlaces`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/KFiniteVectors/KFiniteThetaLifts/RationalPrimesBelowPlaces.lean#L25) (L25): Matches finite sets of primes of K to the rational primes lying below them.
  - `def` [`CasselmanShalikaGL3GL2`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/KFiniteVectors/KFiniteThetaLifts/RationalPrimesBelowPlaces.lean#L39) (L39): Unramified local GL(3) x GL(2) Rankin-Selberg zeta integral evaluates to the local L-factor lfV.
  - `def` [`FAC`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/KFiniteVectors/KFiniteThetaLifts/RationalPrimesBelowPlaces.lean#L96) (L96): Global Euler-product factorization of the Rankin-Selberg integral JG into archimedean, ramified, and unramified factors.

#### [`PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/VerticalStrips/UnramifiedEulerProductIntegral.lean`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/VerticalStrips/UnramifiedEulerProductIntegral.lean)
- **Role:** Rankin-Selberg GL(2) x GL(2) & Non-Dihedral Criteria | **Depth-2:** `PositivityTheory/AutomorphicForms` | **Lines:** 310 | **Top-Dir Ext Fan-In:** 128 | **Depth-2 Ext Fan-In:** 128 | **Total In-Degree:** 130 (`dist=8`, `height=54`)
- **External Importers:** Top-dirs: `Development` (128) | Depth-2 dirs: `Development/AutomorphicSpectrum` (128)
- **Plain-English Mathematical Summary:** Comprehensive 64-definition specification of Rankin-Selberg zeta integrals on GL(2)/Q and holomorphic modular newforms of weight k >= 3: local Godement-Jacquet/Whittaker functional equations (A1-A11, LocalGammaFunctionalEquation), Atkin-Lehner/newform uniqueness (U1, U0, M1, M0, E4), adelic Poisson summation and Eisenstein continuation (G1-G5, AdelicThetaPoissonSummation), Hecke-eigenform lifts (F0-F7), and the global Rankin-Selberg integral proof of non-dihedrality (UnramifiedEulerProductIntegral, G6, X0, X1).
- **Key Exported Declarations:**
  - `def` [`LocalGammaFunctionalEquation`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/VerticalStrips/UnramifiedEulerProductIntegral.lean#L69) (L69): Local Tate/Godement-Jacquet gamma-factor functional equation gam(c, s) * gam(c^(-1), 1-s) = c(-1).
  - `def` [`AdelicThetaPoissonSummation`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/VerticalStrips/UnramifiedEulerProductIntegral.lean#L169) (L169): Adelic GL_2 theta-series Poisson summation formula for Schwartz-Bruhat functions.
  - `def` [`HeckeSumLocalTranslates`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/VerticalStrips/UnramifiedEulerProductIntegral.lean#L235) (L235): Translates classical Hecke eigenvalue action T_p into adelic right-translation sums on GL_2(A_Q).
  - `def` [`UnramifiedEulerProductIntegral`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/VerticalStrips/UnramifiedEulerProductIntegral.lean#L261) (L261): Euler-product factorization of the adelic Rankin-Selberg integral of Wh(phi) * conj(Wh(phi)) twisted by a Hecke character c.
  - `def` [`X1`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/VerticalStrips/UnramifiedEulerProductIntegral.lean#L305) (L305): Final analytic input FE(a, D) for pure weight-k newforms needed for symmetric-power / automorphy pipelines.

#### [`PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/SquareIntegrable/SSmooth.lean`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/SquareIntegrable/SSmooth.lean)
- **Role:** Local GL(2) Whittaker / Schwartz-Bruhat Interface | **Depth-2:** `PositivityTheory/AutomorphicForms` | **Lines:** 114 | **Top-Dir Ext Fan-In:** 81 | **Depth-2 Ext Fan-In:** 81 | **Total In-Degree:** 86 (`dist=7`, `height=53`)
- **External Importers:** Top-dirs: `Development` (81) | Depth-2 dirs: `Development/AutomorphicSpectrum` (81)
- **Plain-English Mathematical Summary:** States the local Kirillov/Whittaker model properties for GL_2 over a non-archimedean local field F: transformation under unipotent (SPsi), center (SCen), and GL_2(F) right-translation (STrans), smoothness under open compact subgroups (SSmooth), asymptotic/support bounds on the torus (SBound), nonvanishing (SNe), unramified spherical Whittaker matching (SUnr), local Tate duality (STate), and the resulting GL_2 local functional equation (FeGen, SFe).
- **Key Exported Declarations:**
  - `def` [`SSmooth`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/SquareIntegrable/SSmooth.lean#L35) (L35): Every GL_2 Whittaker function associated to a Schwartz-Bruhat function is right-invariant under an open compact subgroup.
  - `def` [`SBound`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/SquareIntegrable/SSmooth.lean#L41) (L41): Growth bound ||W2(diag(a,1) k)|| <= C * |a|^(1/2 - eps) and compact support in a for large |a|.
  - `def` [`SUnr`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/SquareIntegrable/SSmooth.lean#L54) (L54): Evaluates W2 on the indicator of O_F^2 as the Shintani/Casselman-Shalika spherical Whittaker function.
  - `def` [`FeGen`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/CuspidalContinuity/ArchimedeanCuspidal/SquareIntegrable/SSmooth.lean#L101) (L101): Full local GL_2 Whittaker functional equation with Tate gamma factors gam(mu_1 c, s) * gam(mu_2 c, s).

#### [`PositivityTheory/Representations/BoundaryCones/ArchimedeanCones/ConeOverlaps/OpenConeCriteria/OpenConeFormulation/IsOpenConeInvariant.lean`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/Representations/BoundaryCones/ArchimedeanCones/ConeOverlaps/OpenConeCriteria/OpenConeFormulation/IsOpenConeInvariant.lean)
- **Role:** Archimedean Positive-Definite Cone Openness | **Depth-2:** `PositivityTheory/Representations` | **Lines:** 55 | **Top-Dir Ext Fan-In:** 1 | **Depth-2 Ext Fan-In:** 1 | **Total In-Degree:** 1 (`dist=13`, `height=21`)
- **External Importers:** Top-dirs: `Development` (1) | Depth-2 dirs: `Development/WeilBound` (1)
- **Plain-English Mathematical Summary:** Proves isOpen_cone_of_hbFacts: the cone of real parameter tuples v whose Hermitian matrix hOf(v) is positive definite is an open subset of Euclidean parameter space, using compactness of the unit sphere in C^n and continuity of the quadratic form.
- **Key Exported Declarations:**
  - `theorem` [`isOpen_cone_of_hbFacts`](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/Representations/BoundaryCones/ArchimedeanCones/ConeOverlaps/OpenConeCriteria/OpenConeFormulation/IsOpenConeInvariant.lean#L14) (L14): Proves openness of the positive-definite Hermitian matrix cone cone(n) via compactness of the unit sphere.

### 4.9 `Lemmata` (167 files -> 167 top-dir interfaces, ratio `1.0000`)

#### [`Lemmata/GeneralBFact/Imports.lean`](file:///home/ubuntu/riemann_proof/lean/src/Lemmata/GeneralBFact/Imports.lean)
- **Role:** Standalone Matrix Lemma | **Depth-2:** `Lemmata/GeneralBFact` | **Lines:** 25 | **Top-Dir Ext Fan-In:** 2 | **Depth-2 Ext Fan-In:** 2 | **Total In-Degree:** 2 (`dist=12`, `height=0`)
- **External Importers:** Top-dirs: `ReciprocityTheory` (2) | Depth-2 dirs: `ReciprocityTheory/ReductiveGroups` (2)
- **Plain-English Mathematical Summary:** Proves the Cauchy-Binet determinant expansion for a rectangular matrix product (A * B).det over any commutative ring R, exported as Bl.general_b_fact.goal1 and imported twice by ReciprocityTheory.
- **Key Exported Declarations:**
  - `theorem` [`goal1`](file:///home/ubuntu/riemann_proof/lean/src/Lemmata/GeneralBFact/Imports.lean#L8) (L8): Cauchy-Binet identity expanding det(A * B) for i x N and N x i matrices over a commutative ring.

### 4.10 `BuildAid` (5 files -> 5 top-dir interfaces, ratio `1.0000`)

#### [`BuildAid/D3.lean`](file:///home/ubuntu/riemann_proof/lean/src/BuildAid/D3.lean)
- **Role:** Build Directive | **Depth-2:** `BuildAid` | **Lines:** 4 | **Top-Dir Ext Fan-In:** 25 | **Depth-2 Ext Fan-In:** 25 | **Total In-Degree:** 25 (`dist=8`, `height=0`)
- **External Importers:** Top-dirs: `Development` (25) | Depth-2 dirs: `Development/AutomorphicSpectrum` (15), `Development/AbelianVarietyTheory` (10)
- **Plain-English Mathematical Summary:** One of five 4-line Lean metaprogramming files (D1-D5) that add namespace prefixes ('CompanionTheory', 'CrystallineSemistableComparison', 'GlobalTheory', 'PositivityTheory', 'UpperTheory') to Lean.LibrarySuggestions.nameDenyListExt to guide automated premise selection during builds. Exports no mathematical theorems or definitions.
- **Key Exported Declarations:** No local `theorem`/`def`/`structure` declarations (pure import barrel / command directive).

