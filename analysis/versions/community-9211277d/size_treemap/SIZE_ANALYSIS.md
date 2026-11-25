# Codebase Size & Hierarchical Complexity Analysis (`community-9211277d`)

Quantitative breakdown of `src/` (**803 reachable modules**, **477,124 lines**, **28.7 MiB**, **148 directory nodes** across max depth **3**) paired with [treemap_sunburst.html](treemap_sunburst.html).

## 1. Top-Level Directory Breakdown

| Top Directory | Files (%) | Lines (%) | Theorems & Lemmas | Defs & Structs | Median Lines | 1-Decl Modules |
|---|---:|---:|---:|---:|---:|---:|
| `Lib` | 495 (61.64%) | 285,088 (59.75%) | 11,073 | 2,235 | 539 | 3 (0.6%) |
| `New` | 306 (38.11%) | 191,998 (40.24%) | 7,149 | 1,485 | 621.5 | 2 (0.7%) |
| `(root)` | 2 (0.25%) | 38 (0.01%) | 5 | 4 | 19 | 0 (0.0%) |

## 2. Module Granularity & Micro-Modules

- **Single-declaration files:** `5` (**0.62%**)
- **Files with ≤ 2 declarations:** `7` (**0.87%**)
- **Zero-declaration modules (import barrels / directives):** `0`
- **Statement wrapper files (`Statement` / statements dirs):** `0` (0.0%)

## 3. Largest Individual Modules (by Line Count)

| Module | Top Dir | Lines | Decls | Dist / Height |
|---|---|---:|---:|---|
| `New/OneLift/FalseLifts/BottomOfTower.lean` | `New` | 1,491 | 94 | 8 / 30 |
| `New/Spanning/Frames/RealPlaceGauge.lean` | `New` | 1,337 | 60 | 11 / 17 |
| `New/Congruences/FirstOrder/DenominatorBound.lean` | `New` | 1,333 | 39 | 6 / 47 |
| `New/Spanning/Unfolding/Climbing.lean` | `New` | 1,286 | 71 | 8 / 29 |
| `Lib/PadicComparison/Crystalline/ComparisonMap.lean` | `Lib` | 1,278 | 40 | 16 / 18 |
| `New/Spanning/Unfolding/Moments.lean` | `New` | 1,253 | 40 | 6 / 38 |
| `New/UpperBound/ElementaryDivisors/ElementaryDivisorTheorem.lean` | `New` | 1,250 | 55 | 8 / 14 |
| `New/Congruences/Lifting/CupProductBound.lean` | `New` | 1,248 | 54 | 12 / 25 |
| `Lib/Adelic/Adeles/Basic.lean` | `Lib` | 1,215 | 143 | 9 / 2 |
| `Lib/Cohomology/Etale/Basic.lean` | `Lib` | 1,211 | 125 | 9 / 3 |
| `New/Spanning/MainTerm/GlobalSieve.lean` | `New` | 1,206 | 64 | 12 / 22 |
| `Lib/Cohomology/ProperBaseChange/Theorem.lean` | `Lib` | 1,199 | 33 | 19 / 12 |
| `New/UpperBound/Seesaw/EdgePairEvaluation.lean` | `New` | 1,199 | 62 | 7 / 38 |
| `Lib/Weil/MixedModel/IsotropicSplitting.lean` | `Lib` | 1,193 | 102 | 10 / 19 |
| `New/Determinant/Exchange/LargeTriple.lean` | `New` | 1,185 | 36 | 10 / 33 |

