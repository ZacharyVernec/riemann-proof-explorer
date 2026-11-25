# Proof Spine, Bottlenecks & Critical Dependency Chain (community-9211277d)

This report analyzes the logical dependency DAG of the proof—tracing its mandatory mathematical bottlenecks (dominator tree rooted at [Main.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean)), its deepest critical dependency chain from the final RH/GRH theorems down to foundational leaves, and the key bridge modules connecting the major theories (interactive explorer in [spine_dashboard.html](spine_dashboard.html)).

> **Edge Orientation Convention:** Throughout this report, a directed edge `(u, v)` means module `u` **depends on** `v` (`u` imports `v`). Hence `Main.lean` is the unique root/source at the apex of the proof, and foundational leaf modules sit at the base (`height = 0`).

---

## Executive Audit Summary

| Metric | Value |
|---|---:|
| Total Lean modules in codebase | 803 |
| Modules reachable from `Main.lean` | 803 |
| Unreachable / standalone modules excluded | 0 |
| Internal dependency edges (reachable DAG) | 1,733 |
| Strict DAG verified (`is_dag`) | Yes |
| Shortest distance span from `Main.lean` | 0 – 21 |
| Critical dependency chain length | 53 edges / 54 modules |
| Critical max-length paths | 4 |
| Foundational leaf modules (`out_degree = 0`) | 2 (93 lines) |
| Log10 total `Main → Leaf` dependency paths | 7.594 |

---

## 1. Entry Funnel & Foundational Base

### 1.1 Entry Funnel Near `Main.lean` (`dist ≤ 3`)

| Dist | Module | Dom Subtree | Out-Deg | Mathematical Role |
|---:|---|---:|---:|---|
| 0 | [Main](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean) | 803 | 1 | Final root export proving riemannHypothesis, riemannZeta_eq_zero_re, LFunction_ne_zero_of_half_lt_re, LFunction_eq_zero_re, and LFunction_eq_zero_re_of_isPrimitive. |
| 1 | [New.Main](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Main.lean) | 802 | 1 | Bridges New.grh (DirichletLNonvanishingRightOfHalf) into New.zeros_on_line and New.zeta_zeros_on_line via the functional equation s <-> 1 - s. |
| 2 | [New.Reduction.OneSidedBound](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean) | 801 | 5 | Derives the one-sided bound eventually_primeRemainder_le_rpow and proves New.grh by combining star_inequality with the PNT cut-off and zero-free criterion. |
| 3 | [New.Reduction.MainInequality](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/MainInequality.lean) | 606 | 2 | Proves star_inequality (m * rem <= f * a * log^5 b) by cancelling the main amount between Theorems A & B (short/enough forms) and Theorem C (integral_forms_long). |
| 3 | [New.Reduction.Zeros.Criterion](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Zeros/Criterion.lean) | 5 | 3 |  |
| 3 | [New.Reduction.Zeros.PrimeNumberTheorem](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Zeros/PrimeNumberTheorem.lean) | 2 | 3 |  |
| 3 | [New.Reduction.Data.Existence](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/Existence.lean) | 1 | 2 |  |
| 3 | [Statements](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean) | 1 | 0 | `RiemannZetaZerosOnLine`, `DirichletLNonvanishingRightOfHalf`, `DirichletLZerosOnLine`, `PrimitiveDirichletLZerosOnLine` |

### 1.2 Top Foundational Leaves (`out_degree = 0`)

There are **2** foundational leaf modules (`93` lines, `0` theorems, `5` definitions). Modules with zero external imports: `0`.

| In-Deg | Lines | Top Directory | Module |
|---:|---:|---|---|
| 1 | 77 | `Lib` | [Lib.Speed](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Speed.lean) |
| 1 | 16 | `(root)` | [Statements](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean) |

---

## 2. Stratigraphic Layering Across Top-Level Theories

The readable-edition codebase stratifies cleanly into three top-level layers from the apex down to the base:

1. **Apex Entrypoints (`(root)`):** `Main.lean` and `Statements.lean` state and export the five unconditional RH and GRH theorems over Mathlib.
2. **Novel Proof Architecture (`New`):** Organizes the argument into `New/Main.lean` (functional-equation reflection), `New/Reduction/` (`OneSidedBound`, `MainInequality`, `ShortAndEnough`, twisted lattices, admissible data), `New/Derivatives/`, `New/UpperBound/`, `New/Spanning/`, `New/Determinant/` (`LongForms` Theorem C), `New/OneLift/`, `New/Congruences/` (modularity congruences, Selmer twisting, crystalline Kisin lifting), and `New/Appendix/`.
3. **Background Literature Library (`Lib`):** Self-contained background modules (importing nothing from `New/`) supplying adelic reduction and trace formulas, analytic PNT/Pólya–Vinogradov, class field theory, étale/Hodge cohomology, discrete series, Galois representations (`AllRanks`), $p$-adic comparison and Kisin modules, Shimura moduli, Siegel–Weil/Rallis formulas, and Weil representations.

| Top Directory | Files | Lines | Leaves | Dist (min/med/max) | Height (med/max) |
|---|---:|---:|---:|---|---|
| `Lib` | 495 | 285,088 | 1 | 4 / 10.0 / 21 | 15.0 / 36 |
| `New` | 306 | 191,998 | 0 | 1 / 8.0 / 15 | 31.0 / 52 |
| `(root)` | 2 | 38 | 1 | 0 / 1.5 / 3 | 26.5 / 53 |

### Major Cross-Theory Edge Flows

| Dependent (`src`) | Dependency (`dst`) | Edges |
|---|---|---:|
| `Lib` | `Lib` | 999 |
| `New` | `New` | 524 |
| `New` | `Lib` | 208 |
| `(root)` | `New` | 1 |
| `New` | `(root)` | 1 |

---

## 3. Dominator Bottleneck Spine (Cooper–Harvey–Kennedy)

In the dependency DAG rooted at `Main.lean`, a module $d$ **dominates** a module $u$ if *every* dependency path from `Main.lean` to $u$ must pass through $d$ (20 skeleton nodes with dominated subtree size `≥ 20`). Top mandatory bottlenecks:

| Rank | Dom Subtree | Depth | Dist / H | Top Dir | Module |
|---:|---:|---:|---:|---|---|
| 1 | 803 (100.0%) | 0 | 0 / 53 | `(root)` | [Main](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean) |
| 2 | 802 (99.875%) | 1 | 1 / 52 | `New` | [New.Main](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Main.lean) |
| 3 | 801 (99.751%) | 2 | 2 / 51 | `New` | [New.Reduction.OneSidedBound](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean) |
| 4 | 606 (75.467%) | 3 | 3 / 50 | `New` | [New.Reduction.MainInequality](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/MainInequality.lean) |
| 5 | 228 (28.394%) | 4 | 4 / 49 | `New` | [New.Determinant.Twist.LongForms](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/LongForms.lean) |
| 6 | 93 (11.582%) | 5 | 9 / 34 | `Lib` | [Lib.GaloisRep.Main.AllRanks](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/AllRanks.lean) |
| 7 | 91 (11.333%) | 6 | 10 / 31 | `Lib` | [Lib.ClassField.Avatar.LocalGlobalCompatibility](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/LocalGlobalCompatibility.lean) |
| 8 | 90 (11.208%) | 7 | 11 / 30 | `Lib` | [Lib.GaloisRep.Main.OddRank](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/OddRank.lean) |
| 9 | 89 (11.083%) | 8 | 12 / 29 | `Lib` | [Lib.GaloisRep.Main.SplitCase](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/SplitCase.lean) |
| 10 | 86 (10.71%) | 9 | 13 / 27 | `Lib` | [Lib.GaloisRep.Main.SeedRepresentation](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/SeedRepresentation.lean) |
| 11 | 74 (9.215%) | 5 | 5 / 48 | `New` | [New.Congruences.FitTwistsExist](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FitTwistsExist.lean) |
| 12 | 58 (7.223%) | 4 | 5 / 42 | `New` | [New.Spanning.SecondMoment.SpanningTheorem](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/SecondMoment/SpanningTheorem.lean) |
| 13 | 46 (5.729%) | 10 | 14 / 25 | `Lib` | [Lib.Shimura.Eigenspace](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Eigenspace.lean) |
| 14 | 36 (4.483%) | 4 | 4 / 47 | `New` | [New.Reduction.ShortAndEnough](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/ShortAndEnough.lean) |
| 15 | 34 (4.234%) | 5 | 6 / 38 | `New` | [New.Spanning.Unfolding.Moments](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/Unfolding/Moments.lean) |
| 16 | 31 (3.861%) | 6 | 7 / 37 | `New` | [New.Spanning.Unfolding.MomentBounds](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/Unfolding/MomentBounds.lean) |
| 17 | 24 (2.989%) | 6 | 6 / 47 | `New` | [New.Congruences.FirstOrder.DenominatorBound](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FirstOrder/DenominatorBound.lean) |
| 18 | 21 (2.615%) | 7 | 8 / 35 | `New` | [New.Spanning.MainTerm.EnergyEstimate](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/MainTerm/EnergyEstimate.lean) |
| 19 | 20 (2.491%) | 6 | 6 / 46 | `New` | [New.Congruences.Selmer.TwistingTheorem](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/Selmer/TwistingTheorem.lean) |
| 20 | 20 (2.491%) | 8 | 9 / 33 | `New` | [New.Spanning.MainTerm.FiniteSieveSystem](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/MainTerm/FiniteSieveSystem.lean) |
| 21 | 17 (2.117%) | 5 | 5 / 44 | `New` | [New.UpperBound.Divisibility.LocalDivisibility](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Divisibility/LocalDivisibility.lean) |
| 22 | 17 (2.117%) | 5 | 5 / 44 | `New` | [New.UpperBound.Seesaw.SeesawIdentity](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Seesaw/SeesawIdentity.lean) |
| 23 | 16 (1.993%) | 6 | 9 / 32 | `New` | [New.Congruences.LocalLoss.CrystallineCocycles](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/LocalLoss/CrystallineCocycles.lean) |
| 24 | 15 (1.868%) | 7 | 10 / 30 | `New` | [New.Congruences.Lifting.CupOrthogonalityBounds](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/Lifting/CupOrthogonalityBounds.lean) |
| 25 | 15 (1.868%) | 5 | 5 / 47 | `New` | [New.OneLift.LiftVolumeHeight](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/OneLift/LiftVolumeHeight.lean) |
| 26 | 12 (1.494%) | 6 | 6 / 42 | `New` | [New.UpperBound.Divisibility.MarkOperator](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Divisibility/MarkOperator.lean) |
| 27 | 12 (1.494%) | 6 | 6 / 43 | `New` | [New.UpperBound.Seesaw.Cut](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Seesaw/Cut.lean) |
| 28 | 11 (1.37%) | 7 | 7 / 31 | `New` | [New.Congruences.Selmer.GeneralTheorem](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/Selmer/GeneralTheorem.lean) |
| 29 | 11 (1.37%) | 7 | 7 / 41 | `New` | [New.UpperBound.Divisibility.HeckeEdges](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Divisibility/HeckeEdges.lean) |
| 30 | 10 (1.245%) | 11 | 15 / 22 | `Lib` | [Lib.Cohomology.WoodsHole](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Cohomology/WoodsHole.lean) |

---

## 4. Critical Dependency Chain & Longest Intra-Directory Chains

The longest dependency chain spans **53 edges (54 modules)** across **4** total max-length paths, with **52** single-node chokes and **2** branching heights.

| Top Directory | Max Intra-Dir Edges | Start → End |
|---|---:|---|
| `Lib` | 36 | `LabelCompatibility` → `Speed` |
| `New` | 27 | `Main` → `FieldsAndPlaces` |
| `(root)` | 0 | `Main` → `Main` |

---

## 5. Top Cross-Theory Bridges & Path-Stress Hubs

Modules ranked by **Brandes weighted cross-directory betweenness** (`brandes_weighted_cross_top`) alongside cross-directory fan-in × fan-out (`Cross Fan`), identifying high-stress interfaces connecting distinct top-level mathematical theories:

| Rank | Brandes Cross-Dir | Cross Fan (In×Out) | In / Out | Top Dir | Module |
|---:|---:|---:|---:|---|---|
| 1 | 5,898.2 | 0 | 9 / 4 | `New` | [New.UpperBound.Objects.Rows](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Rows.lean) |
| 2 | 4,821.1 | 0 | 3 / 7 | `New` | [New.UpperBound.Objects.Columns](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Columns.lean) |
| 3 | 4,345.6 | 0 | 4 / 4 | `Lib` | [Lib.ClassField.Avatar.HeckeBaseChange](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/HeckeBaseChange.lean) |
| 4 | 3,991.9 | 0 | 11 / 3 | `Lib` | [Lib.General.NumberTheory.PadicLimitsValuation](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/General/NumberTheory/PadicLimitsValuation.lean) |
| 5 | 3,919.3 | 0 | 2 / 5 | `New` | [New.Derivatives.Vacuum.TightFrames](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Derivatives/Vacuum/TightFrames.lean) |
| 6 | 3,824.5 | 0 | 3 / 3 | `New` | [New.Derivatives.Vacuum.IntegralVacuum](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Derivatives/Vacuum/IntegralVacuum.lean) |
| 7 | 3,672.4 | 0 | 6 / 6 | `Lib` | [Lib.Weil.DualPair.WeilAction](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/DualPair/WeilAction.lean) |
| 8 | 3,441.3 | 0 | 5 / 5 | `New` | [New.Congruences.GaloisRepresentations.SelmerHypotheses](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/GaloisRepresentations/SelmerHypotheses.lean) |
| 9 | 3,362.9 | 0 | 3 / 2 | `New` | [New.Reduction.Data.AdmissibleData](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/AdmissibleData.lean) |
| 10 | 3,251.0 | 0 | 4 / 4 | `Lib` | [Lib.GaloisRep.Main.SelmerModules](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/SelmerModules.lean) |
| 11 | 3,134.8 | 0 | 5 / 4 | `New` | [New.UpperBound.Seesaw.AdmissibleCombinations](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Seesaw/AdmissibleCombinations.lean) |
| 12 | 2,989.2 | 0 | 3 / 4 | `Lib` | [Lib.ClassField.HeckeCharacter.AlgebraicValues](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/HeckeCharacter/AlgebraicValues.lean) |
| 13 | 2,836.6 | 0 | 11 / 5 | `Lib` | [Lib.Shimura.Uniformisation.HolomorphicFamilies](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Uniformisation/HolomorphicFamilies.lean) |
| 14 | 2,788.4 | 0 | 5 / 4 | `New` | [New.UpperBound.Size.ShortColumns](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Size/ShortColumns.lean) |
| 15 | 2,731.1 | 0 | 2 / 2 | `Lib` | [Lib.GaloisRep.Main.AllRanks](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/AllRanks.lean) |

