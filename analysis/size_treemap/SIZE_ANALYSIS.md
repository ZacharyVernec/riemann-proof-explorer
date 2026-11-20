# Codebase Size, Hierarchy & Micro-Module Analysis (`lean/src`)

**Generated from:** [graph.sqlite](file:///home/ubuntu/riemann_proof/analysis/data/graph.sqlite) and [meta.json](file:///home/ubuntu/riemann_proof/analysis/data/meta.json) via [build_hierarchy.py](file:///home/ubuntu/riemann_proof/analysis/size_treemap/build_hierarchy.py)
**Interactive Explorer:** [treemap_sunburst.html](file:///home/ubuntu/riemann_proof/analysis/size_treemap/treemap_sunburst.html) · **Full Data:** [hierarchy_sizes.json](file:///home/ubuntu/riemann_proof/analysis/size_treemap/hierarchy_sizes.json)

---

## 1. Executive Summary

- **Scale & Reachability:** [lean/src](file:///home/ubuntu/riemann_proof/lean/src) contains **175,187 `.lean` files** (**17,374,215 lines**, **1,030,531,854 bytes / 982.79 MiB / 1.03 GB**) across **3,615 directory nodes** (3,402 directories containing direct `.lean` files: 2,923 pure leaf directories and 479 intermediate directories with both direct files and subdirectories, up to depth 10). **100% of files** are reachable from [Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean) (`753,261` internal dependency edges, DAG with max distance `43` and max height `202`).
- **Extreme Concentration in `Development`:** `Development` holds **141,928 files (81.02%)**, **12,232,663 lines (70.41%)**, and **767,288,236 bytes (74.46%)**. One single depth-2 subtree — [Development/AbelianVarietyTheory](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory) — holds **99,187 files (56.62% of the entire repository)** and **8,142,960 lines (46.87%)**, and a single leaf directory — [DivisorProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs) — accounts for **42,424 files (24.22% of all files)** and **2,848,282 lines (16.39%)**.
- **Bimodal Micro- vs. Macro-Module Architecture:** Overall, the repository skews strongly toward **"one-lemma-per-file" micro-modules** (median **2 declarations**, median **1 theorem/lemma**, median **58 lines**; **45.03%** of all files contain **exactly 1 declaration** and **50.05%** have **≤ 1 theorem/lemma**). Yet line volume is bimodal across top-level layers: `Development` and `Lemmata` are dominated by micro-modules and **46,610 `*Statement.lean` wrapper files** (**26.61%** of the entire repo), whereas `Formalism` (**10.42%** of files, **18.42%** of lines, **33.20%** of defs/structures) and `ReciprocityTheory` use dense multi-declaration macro-modules (median **7 declarations**, **115–129 lines**, and outliers up to **17,981 lines / 1,518 declarations**).

---

## 2. Where the 175k Files & 17.4M Lines Live

### 2.1 Complete Breakdown by `top_dir`

| `top_dir` | Files | % Files | Lines | % Lines | Bytes | % Bytes | Thm + Lem | Def + Str | All Decls | Mean / Med Lines | Mean / Med Decls | 1-Decl Files (%) | `*Statement.lean` | Avg Dist / Max H |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| [Development](file:///home/ubuntu/riemann_proof/lean/src/Development) | 141,928 | 81.02% | 12,232,663 | 70.41% | 767,288,236 | 74.46% | 562,329 | 117,861 | 690,879 | 86.19 / 49 | 4.87 / 1 | 72,184 (50.86%) | 45,751 | 15.03 / 198 |
| [Formalism](file:///home/ubuntu/riemann_proof/lean/src/Formalism) | 18,254 | 10.42% | 3,200,748 | 18.42% | 164,903,481 | 16.00% | 162,118 | 73,406 | 239,627 | 175.35 / 115 | 13.13 / 7 | 2,451 (13.43%) | 119 | 13.80 / 93 |
| [GroundTheory](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory) | 8,507 | 4.86% | 1,119,138 | 6.44% | 54,564,791 | 5.29% | 54,211 | 17,764 | 74,280 | 131.55 / 89 | 8.73 / 4 | 2,680 (31.50%) | 11 | 10.74 / 68 |
| [ReciprocityTheory](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory) | 3,845 | 2.19% | 563,016 | 3.24% | 28,914,051 | 2.81% | 27,722 | 7,945 | 36,296 | 146.43 / 129 | 9.44 / 7 | 512 (13.32%) | 110 | 12.78 / 76 |
| [CompanionTheory](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory) | 2,027 | 1.16% | 194,218 | 1.12% | 11,296,366 | 1.10% | 9,419 | 2,221 | 11,748 | 95.82 / 58 | 5.80 / 2 | 868 (42.82%) | 618 | 12.87 / 114 |
| [PositivityTheory](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory) | 449 | 0.26% | 55,130 | 0.32% | 3,109,326 | 0.30% | 2,702 | 1,898 | 4,713 | 122.78 / 88 | 10.50 / 6 | 72 (16.04%) | 1 | 9.55 / 111 |
| [Lemmata](file:///home/ubuntu/riemann_proof/lean/src/Lemmata) | 167 | 0.10% | 9,232 | 0.05% | 452,342 | 0.04% | 245 | 6 | 251 | 55.28 / 40 | 1.50 / 1 | 113 (67.66%) | 0 | 13.69 / 17 |
| [BuildAid](file:///home/ubuntu/riemann_proof/lean/src/BuildAid) | 5 | 0.00% | 20 | 0.00% | 850 | 0.00% | 0 | 0 | 0 | 4.00 / 4 | 0.00 / 0 | 0 (0.00%) | 0 | 12.00 / 0 |
| [Supplements](file:///home/ubuntu/riemann_proof/lean/src/Supplements) | 3 | 0.00% | 22 | 0.00% | 1,195 | 0.00% | 4 | 0 | 4 | 7.33 / 4 | 1.33 / 0 | 0 (0.00%) | 0 | 2.00 / 201 |
| `(root)` ([Main](file:///home/ubuntu/riemann_proof/lean/src/Main.lean), [Statements](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean)) | 2 | 0.00% | 28 | 0.00% | 1,216 | 0.00% | 5 | 4 | 9 | 14.00 / 14 | 4.50 / 4.5 | 0 (0.00%) | 0 | 0.50 / 202 |
| **Total** | **175,187** | **100%** | **17,374,215** | **100%** | **1,030,531,854** | **100%** | **818,755** | **221,105** | **1,057,807** | **99.18 / 58** | **6.04 / 2** | **78,880 (45.03%)** | **46,610** | **14.58 / 202** |

### 2.2 Why `Development` Dominates (~81% of Files)

Three structural mechanisms observed directly in `graph.sqlite` and the `.lean` source explain why `Development` accounts for 81.02% of files yet only 70.41% of lines and 53.31% of defs/structures:

1. **Fine-Grained Proof Splitting in `AbelianVarietyTheory` and `AutomorphicSpectrum`:**
   - [Development/AbelianVarietyTheory/Proofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs) alone holds **95,418 files** (54.47% of the repo) at a mean of only **77.94 lines/file**.
   - [Development/AutomorphicSpectrum/Proofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Proofs) holds **14,864 files** (8.49% of the repo) at **78.27 lines/file**.
   - Across `Development`, **72,184 files (50.86%)** have **exactly 1 declaration** and **46,043 files (32.44%)** are **≤ 20 lines** long.
2. **Systematic `*Statement.lean` Re-Export Wrappers (45,751 files):**
   - Out of **46,610 `*Statement.lean` files** in the entire repository, **45,751 (98.16%)** live in `Development` (and **38,695** inside `Development/AbelianVarietyTheory/Proofs`, including **18,306** inside `DivisorProofs` alone).
   - Inspecting pairs such as [AbelianAmpleSymmPreservedFieldBaseChange.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/AbelianAmpleSymmPreservedFieldBaseChange.lean) (38 lines) alongside [AbelianAmpleSymmPreservedFieldBaseChangeStatement.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/AbelianAmpleSymmPreservedFieldBaseChangeStatement.lean) (12 lines) shows that each proof module is paired with a ~12-line statement-export module defining a canonical `_root_.GlobalTheory.T.*` theorem via `first | exact ...`. These 45,751 wrapper files contribute **614,784 lines** (~13.44 lines/file on average) while accounting for **32.24% of all files in `Development`**.
3. **Dense Single-Topic Proof & Definition Subtrees vs. `Formalism`:**
   - Inside `Development`, `Definitions` subtrees (e.g., [AbelianVarietyTheory/Definitions](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions), 2,198 files, mean **231.38 lines/file**, 25,010 defs/structures) are multi-declaration infrastructure, whereas the `Proofs` directories fan out every downstream consequence into separate files.
   - By contrast, `Formalism` packages dense analytic machinery into fewer, larger files (**175.35 mean lines**, **13.13 mean declarations**, only **119 `*Statement.lean`** wrappers). For example, [Formalism/HermitianCurvature/HermitianCurvatureProofs](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HermitianCurvatureProofs) produces **437,211 lines** and **30,688 theorems/lemmas/defs/structures** from just **1,854 files**.

---

## 3. Directory Hierarchy Breakdown (`depth2_dir`, `depth3_dir`, and Heaviest Leaf Folders)

There are **330 distinct `depth2_dir` groups** and **746 distinct `depth3_dir` groups** in `graph.sqlite` (all 330 `depth2_dir` entries are exported in [hierarchy_sizes.json](file:///home/ubuntu/riemann_proof/analysis/size_treemap/hierarchy_sizes.json)).

### 3.1 Top 25 `depth2_dir` Subtrees (Ordered by Lines)

| Rank | `depth2_dir` | Files | % Files | Lines | % Lines | Bytes | Thm + Lem | Def + Str | Mean L/File | Avg Dist | Max H |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | [Development/AbelianVarietyTheory](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory) | 99,187 | 56.62% | 8,142,960 | 46.87% | 519,866,127 | 375,914 | 72,750 | 82.10 | 15.89 | 189 |
| 2 | [Development/AutomorphicArithmetic](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic) | 18,431 | 10.52% | 1,776,375 | 10.22% | 110,939,648 | 71,155 | 18,849 | 96.38 | 11.32 | 198 |
| 3 | [Development/AutomorphicSpectrum](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum) | 15,147 | 8.65% | 1,195,844 | 6.88% | 72,332,162 | 58,894 | 9,264 | 78.95 | 15.35 | 130 |
| 4 | [Formalism/LocalToGlobal](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal) | 5,501 | 3.14% | 955,843 | 5.50% | 49,605,549 | 49,840 | 21,694 | 173.76 | 13.59 | 87 |
| 5 | [Development/WeilBound](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound) | 7,051 | 4.03% | 848,547 | 4.88% | 48,734,349 | 41,740 | 12,603 | 120.34 | 12.72 | 143 |
| 6 | [Formalism/SharpRestriction](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction) | 3,093 | 1.77% | 709,436 | 4.08% | 37,418,210 | 33,822 | 19,715 | 229.37 | 14.92 | 93 |
| 7 | [GroundTheory/HeightsAndTheta](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta) | 6,410 | 3.66% | 641,322 | 3.69% | 31,626,989 | 25,830 | 11,080 | 100.05 | 10.48 | 68 |
| 8 | [Formalism/HermitianCurvature](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature) | 1,922 | 1.10% | 460,802 | 2.65% | 24,655,327 | 28,075 | 7,606 | 239.75 | 14.41 | 92 |
| 9 | [Formalism/PeriodIntegrals](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PeriodIntegrals) | 4,350 | 2.48% | 451,856 | 2.60% | 21,879,248 | 23,534 | 8,454 | 103.87 | 13.42 | 83 |
| 10 | [ReciprocityTheory/ReductiveGroups](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups) | 2,799 | 1.60% | 409,976 | 2.36% | 21,268,891 | 20,326 | 5,464 | 146.47 | 13.02 | 76 |
| 11 | [GroundTheory/AutomorphicForms](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/AutomorphicForms) | 542 | 0.31% | 150,005 | 0.86% | 7,366,228 | 8,570 | 1,977 | 276.76 | 10.81 | 52 |
| 12 | [Development/ResolutionOfSingularities](file:///home/ubuntu/riemann_proof/lean/src/Development/ResolutionOfSingularities) | 499 | 0.29% | 140,709 | 0.81% | 8,379,570 | 6,676 | 1,130 | 281.98 | 9.31 | 36 |
| 13 | [CompanionTheory/SpectralGeometry](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/SpectralGeometry) | 1,254 | 0.72% | 105,437 | 0.61% | 6,076,697 | 5,179 | 645 | 84.08 | 13.38 | 114 |
| 14 | [Development/EtaleCohomology](file:///home/ubuntu/riemann_proof/lean/src/Development/EtaleCohomology) | 1,398 | 0.80% | 104,525 | 0.60% | 5,781,649 | 6,828 | 3,023 | 74.77 | 13.84 | 95 |
| 15 | [GroundTheory/ProfiniteCohomology](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ProfiniteCohomology) | 450 | 0.26% | 84,902 | 0.49% | 4,162,794 | 4,384 | 1,323 | 188.67 | 11.03 | 68 |
| 16 | [Formalism/GL3MeanSquares](file:///home/ubuntu/riemann_proof/lean/src/Formalism/GL3MeanSquares) | 440 | 0.25% | 78,320 | 0.45% | 4,066,947 | 3,029 | 1,089 | 178.00 | 13.55 | 46 |
| 17 | [GroundTheory/GlobalFields](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/GlobalFields) | 384 | 0.22% | 72,305 | 0.42% | 3,404,788 | 4,610 | 894 | 188.29 | 10.33 | 54 |
| 18 | [GroundTheory/PAdicHodge](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/PAdicHodge) | 226 | 0.13% | 64,317 | 0.37% | 3,105,103 | 4,305 | 760 | 284.59 | 14.70 | 35 |
| 19 | [PositivityTheory/AutomorphicForms](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory/AutomorphicForms) | 445 | 0.25% | 54,970 | 0.32% | 3,101,742 | 2,697 | 1,898 | 123.53 | 9.54 | 111 |
| 20 | [Formalism/ThetaLogCoordinates](file:///home/ubuntu/riemann_proof/lean/src/Formalism/ThetaLogCoordinates) | 292 | 0.17% | 54,555 | 0.31% | 2,666,347 | 3,012 | 1,160 | 186.83 | 13.73 | 24 |
| 21 | [CompanionTheory/AutomorphicTheory](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory/AutomorphicTheory) | 457 | 0.26% | 47,957 | 0.28% | 2,929,392 | 2,159 | 620 | 104.94 | 13.39 | 102 |
| 22 | [GroundTheory/ArithmeticGeometry](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/ArithmeticGeometry) | 218 | 0.12% | 45,046 | 0.26% | 2,096,782 | 2,625 | 830 | 206.63 | 13.36 | 28 |
| 23 | [GroundTheory/LocalFields](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/LocalFields) | 159 | 0.09% | 40,767 | 0.24% | 1,878,980 | 2,627 | 445 | 256.40 | 10.23 | 26 |
| 24 | [Formalism/WachLatticeTwists](file:///home/ubuntu/riemann_proof/lean/src/Formalism/WachLatticeTwists) | 262 | 0.15% | 38,367 | 0.22% | 2,294,510 | 722 | 847 | 146.44 | 21.02 | 35 |
| 25 | [ReciprocityTheory/AnalyticForms](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/AnalyticForms) | 192 | 0.11% | 36,680 | 0.21% | 1,865,688 | 1,790 | 501 | 191.04 | 10.88 | 26 |

*(Note: By file count, ranks 21–25 shift slightly to include [ReciprocityTheory/L2DbarEstimates](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/L2DbarEstimates) [227 files, 33,734 lines] and [Development/DiscreteGroups](file:///home/ubuntu/riemann_proof/lean/src/Development/DiscreteGroups) [215 files, 23,703 lines]; those top-25 lists are both stored in `hierarchy_sizes.json`.)*

### 3.2 Top 30 `depth3_dir` Subtrees (Ordered by Lines)

| Rank | `depth3_dir` | Files | % Files | Lines | % Lines | Thm + Lem | Def + Str | Mean L/File |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `Development/AbelianVarietyTheory/Proofs` | 95,418 | 54.47% | 7,436,698 | 42.80% | 336,348 | 33,989 | 77.94 |
| 2 | `Development/AutomorphicSpectrum/Proofs` | 14,864 | 8.49% | 1,163,468 | 6.70% | 57,509 | 7,085 | 78.27 |
| 3 | `Development/AutomorphicArithmetic/AutomorphicVarieties` | 7,959 | 4.54% | 848,614 | 4.88% | 35,088 | 8,991 | 106.62 |
| 4 | `GroundTheory/HeightsAndTheta/Heights` | 6,348 | 3.62% | 626,821 | 3.61% | 25,056 | 10,502 | 98.74 |
| 5 | `Development/AbelianVarietyTheory/Definitions` | 2,198 | 1.26% | 508,569 | 2.93% | 32,831 | 25,010 | 231.38 |
| 6 | `Development/WeilBound/CoreStatements` | 3,746 | 2.14% | 455,457 | 2.62% | 21,553 | 5,708 | 121.58 |
| 7 | `Formalism/HermitianCurvature/HermitianCurvatureProofs` | 1,854 | 1.06% | 437,211 | 2.52% | 26,542 | 4,146 | 235.82 |
| 8 | `Formalism/PeriodIntegrals/UnitaryGroupMassFormula` | 3,615 | 2.06% | 430,489 | 2.48% | 22,869 | 6,360 | 119.08 |
| 9 | `Development/AutomorphicArithmetic/Foundations` | 4,413 | 2.52% | 419,572 | 2.42% | 18,649 | 6,202 | 95.08 |
| 10 | `Formalism/LocalToGlobal/SiegelLatticeTheory` | 2,085 | 1.19% | 339,004 | 1.95% | 16,907 | 5,468 | 162.59 |
| 11 | `Development/WeilBound/RepresentationTheoryGL` | 2,486 | 1.42% | 274,147 | 1.58% | 13,773 | 5,494 | 110.28 |
| 12 | `ReciprocityTheory/ReductiveGroups/ArithmeticGeometry` | 1,623 | 0.93% | 239,112 | 1.38% | 10,826 | 3,683 | 147.33 |
| 13 | `Formalism/SharpRestriction/GrowthBounds` | 1,210 | 0.69% | 231,225 | 1.33% | 11,586 | 4,364 | 191.10 |
| 14 | `Development/AutomorphicArithmetic/ThetaCorrespondence` | 3,201 | 1.83% | 178,983 | 1.03% | 5,645 | 856 | 55.91 |
| 15 | `Formalism/SharpRestriction/LevelLetterCocycles` | 758 | 0.43% | 170,849 | 0.98% | 7,138 | 3,404 | 225.39 |
| 16 | `ReciprocityTheory/ReductiveGroups/DiscreteSeries` | 1,021 | 0.58% | 154,332 | 0.89% | 8,565 | 1,617 | 151.16 |
| 17 | `Development/ResolutionOfSingularities/EmbeddedResolution` | 477 | 0.27% | 135,525 | 0.78% | 6,315 | 1,031 | 284.12 |
| 18 | `Formalism/SharpRestriction/CuspSpanNormBounds` | 399 | 0.23% | 132,978 | 0.77% | 6,418 | 4,572 | 333.28 |
| 19 | `Development/AutomorphicArithmetic/IntegralCasts` | 907 | 0.52% | 123,617 | 0.71% | 2,906 | 1,091 | 136.29 |
| 20 | `Development/WeilBound/ThetaLifts` | 788 | 0.45% | 115,848 | 0.67% | 6,224 | 1,349 | 147.02 |
| 21 | `CompanionTheory/SpectralGeometry/LocalGlobalProofs` | 1,250 | 0.71% | 104,890 | 0.60% | 5,164 | 578 | 83.91 |
| 22 | `Development/AbelianVarietyTheory/BlockTheory` | 753 | 0.43% | 104,027 | 0.60% | 1,999 | 11,336 | 138.15 |
| 23 | `Formalism/LocalToGlobal/Columns` | 376 | 0.22% | 95,905 | 0.55% | 5,313 | 2,300 | 255.07 |
| 24 | `Formalism/LocalToGlobal/IndefiniteReal` | 435 | 0.25% | 78,821 | 0.45% | 4,014 | 2,655 | 181.20 |
| 25 | `Formalism/LocalToGlobal/TorsionIntegrality` | 489 | 0.28% | 70,444 | 0.41% | 4,581 | 1,439 | 144.06 |
| 26 | `Formalism/LocalToGlobal/GlobalTheory` | 389 | 0.22% | 69,295 | 0.40% | 3,562 | 1,243 | 178.14 |
| 27 | `GroundTheory/PAdicHodge` | 226 | 0.13% | 64,317 | 0.37% | 4,305 | 760 | 284.59 |
| 28 | `Formalism/SharpRestriction/Divisibility` | 274 | 0.16% | 63,162 | 0.36% | 2,670 | 3,053 | 230.52 |
| 29 | `GroundTheory/AutomorphicForms` | 217 | 0.12% | 61,033 | 0.35% | 3,537 | 812 | 281.26 |
| 30 | `Development/AbelianVarietyTheory/PublishedTheorems` | 493 | 0.28% | 56,194 | 0.32% | 2,744 | 1,525 | 113.98 |

### 3.3 Top 25 Heaviest Leaf Directories (`dir_path` Without Subdirectories)

*(When including intermediate directories' direct files—matching `dir_stats level = 0`—[Formalism/HermitianCurvature/HermitianCurvatureProofs](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HermitianCurvatureProofs) ranks #6 at **1,810 direct files / 431,754 lines** and [CapelliIdentities](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities) ranks #18 at **846 direct files / 115,426 lines**. The table below lists the top 25 pure leaf directories with no subdirectories.)*

| Rank | Pure Leaf Directory | Files | Lines | Bytes | Thm + Lem | Def + Str | Avg Dist | Max H |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | [DivisorProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs) | 42,424 | 2,848,282 | 189,325,218 | 120,856 | 13,031 | 16.63 | 189 |
| 2 | [BlockDecomposition](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Proofs/BlockDecomposition) | 8,354 | 689,539 | 39,795,647 | 36,505 | 5,049 | 11.23 | 117 |
| 3 | [InertiaEigenvalues](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/InertiaEigenvalues) | 8,951 | 676,661 | 42,591,992 | 31,119 | 2,897 | 15.95 | 123 |
| 4 | [IwasawaDecomposition](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/IwasawaDecomposition) | 7,769 | 600,348 | 39,670,443 | 27,498 | 3,549 | 15.70 | 129 |
| 5 | [TwistedOperators](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/TwistedOperators) | 6,642 | 548,833 | 36,651,101 | 24,963 | 2,510 | 13.86 | 152 |
| 6 | [FlagMeasures](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/FlagMeasures) | 4,003 | 394,262 | 23,717,553 | 18,735 | 1,311 | 16.68 | 100 |
| 7 | [DecoratedLatticeProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/DecoratedLatticeProofs) | 5,063 | 362,431 | 25,667,008 | 17,343 | 1,352 | 17.89 | 125 |
| 8 | [FoundationProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/FoundationProofs) | 3,411 | 291,980 | 16,886,338 | 15,034 | 1,458 | 14.32 | 118 |
| 9 | [SatakeParameters](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/SatakeParameters) | 3,462 | 236,891 | 15,293,573 | 11,214 | 1,233 | 17.47 | 181 |
| 10 | [GeometryProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Proofs/GeometryProofs) | 3,001 | 220,952 | 14,961,994 | 9,655 | 814 | 21.89 | 129 |
| 11 | [ModuliProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/ModuliProofs) | 1,539 | 170,603 | 11,435,512 | 7,418 | 703 | 15.15 | 81 |
| 12 | [DegenerationProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/DegenerationProofs) | 1,563 | 146,184 | 9,896,395 | 6,348 | 461 | 16.30 | 85 |
| 13 | [JetHarmonics](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/JetHarmonics) | 1,417 | 129,447 | 8,203,173 | 5,988 | 509 | 18.52 | 96 |
| 14 | [Definitions/Divisors](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/Divisors) | 573 | 127,646 | 6,656,916 | 7,735 | 6,840 | 11.24 | 140 |
| 15 | [GlobalInterpolation](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/GlobalInterpolation) | 1,298 | 121,938 | 7,157,535 | 5,746 | 481 | 13.44 | 121 |
| 16 | [MetricProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum/Proofs/MetricProofs) | 1,576 | 118,136 | 7,629,393 | 5,151 | 543 | 22.68 | 106 |
| 17 | [UniformizationProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/UniformizationProofs) | 869 | 100,548 | 6,933,671 | 4,289 | 390 | 16.03 | 81 |
| 18 | [ThirdPlaceSeries](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries) | 2,251 | 100,458 | 9,167,319 | 3,217 | 721 | 14.01 | 171 |
| 19 | [AutomorphicMembership](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Definitions/AutomorphicMembership) | 334 | 86,330 | 4,513,078 | 5,925 | 3,527 | 11.34 | 107 |
| 20 | [UnitaryExistence](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/UnitaryExistence) | 767 | 81,679 | 5,117,586 | 3,612 | 459 | 12.31 | 86 |
| 21 | [ComplexAnalyticSets](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta/Heights/ComplexAnalyticSets) | 994 | 74,689 | 3,923,328 | 2,316 | 873 | 8.51 | 18 |
| 22 | [SiegelThetaTransformation](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/SiegelThetaTransformation) | 516 | 68,832 | 4,161,168 | 3,346 | 226 | 15.65 | 78 |
| 23 | [CuspFormEvaluations](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/CuspFormEvaluations) | 586 | 68,402 | 4,205,129 | 3,337 | 314 | 13.87 | 81 |
| 24 | [ThetaShiftProofs](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/ThetaShiftProofs) | 476 | 67,728 | 4,463,938 | 3,554 | 411 | 15.44 | 85 |
| 25 | [PAdicHodge](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/PAdicHodge) | 226 | 64,317 | 3,105,103 | 4,305 | 760 | 14.70 | 35 |

---

## 4. File Size Distribution & Micro-Module vs. Macro-Module Architecture

### 4.1 Overall Quantiles Across 175,187 Modules

| Metric | Min | p10 | p25 | Median | Mean | p75 | p90 | p95 | p99 | Max | Total Sum |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Lines** | 1 | 10 | 17 | **58** | **99.18** | 132 | 233 | 319 | 560 | 17,981 | 17,374,215 |
| **Bytes** | 15 | 1,078 | 1,654 | **3,478** | **5,882.47** | 7,589 | 13,268 | 17,972 | 31,395.56 | 913,995 | 1,030,531,854 |
| **All Declarations** | 0 | 1 | 1 | **2** | **6.04** | 7 | 15 | 23 | 48 | 1,518 | 1,057,807 |
| **Theorems + Lemmas** | 0 | 1 | 1 | **1** | **4.67** | 5 | 12 | 18 | 35 | 1,518 | 818,755 |
| **Defs + Structures** | 0 | 0 | 0 | **0** | **1.26** | 1 | 3 | 6 | 22 | 205 | 221,105 |

### 4.2 Distribution Buckets (Files vs. Line Share)

| Declarations / File | Files | % Files | Total Lines | | Lines / File | Files | % Files | Total Lines |
|---|---:|---:|---:|---|---|---:|---:|---:|
| `0` decls | 178 | 0.10% | 1,184 | | `1–20` lines | 49,487 | 28.25% | 590,868 |
| `1` decl | **78,880** | **45.03%** | 2,059,915 | | `21–50` lines | 31,441 | 17.95% | 1,069,558 |
| `2` decls | 16,198 | 9.25% | 1,117,318 | | `51–100` lines | 35,267 | 20.13% | 2,598,442 |
| `3–5` decls | 28,814 | 16.45% | 2,854,337 | | `101–200` lines | 35,499 | 20.26% | 5,061,122 |
| `6–10` decls | 23,144 | 13.21% | 3,402,645 | | `201–500` lines | 21,077 | 12.03% | 6,108,647 |
| `11–25` decls | 20,885 | 11.92% | 4,667,158 | | `501–1000` lines | 2,093 | 1.19% | 1,344,538 |
| `26–100` decls | 6,758 | 3.86% | 2,773,735 | | `1001+` lines | 323 | 0.18% | 601,040 |
| `101+` decls | 330 | 0.19% | 497,923 | | **Sum ≤ 200 lines** | **151,694** | **86.59%** | **9,319,990** |

### 4.3 Does It Follow a "One-Lemma-Per-File" Architecture?

**Yes at the file-count majority, but strongly stratified by theory layer:**
- **Micro-module majority:** **78,880 files (45.03%)** have **exactly 1 declaration**, **95,256 files (54.37%)** have **≤ 2 declarations**, and **87,682 files (50.05%)** have **≤ 1 theorem/lemma**. `Lemmata` (67.66% 1-decl, 167 files across 167 single-file subfolders), `Development` (50.86% 1-decl), and `CompanionTheory` (42.82% 1-decl) exemplify strict micro-module decomposition.
- **Macro-module core:** Conversely, those 45.03% single-declaration files contribute only **11.86% of lines (2.06M)**, whereas files with **11+ declarations** (**15.97%** of files) contribute **45.69% of all lines (7.94M)**. `Formalism` (p50 = 115 lines / 7 decls; p99 = 1,142.87 lines / 107 decls) and `ReciprocityTheory` (p50 = 129 lines / 7 decls) concentrate the core mathematical APIs and large multi-theorem developments.

---

## 5. Top 25 Largest Individual `.lean` Files

Two distinct classes of monolithic outliers emerge:
1. **Dense Proof / Aggregator Macro-Files (`Formalism`):** Led by [IsAdmissibleSplittingCharPairMulTwist.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HermitianCurvatureProofs/IsAdmissibleSplittingCharPairMulTwist.lean) (**17,981 lines**, **913,995 bytes**, **1,352 declarations**). Notice also [HeisenbergConjugationMeasurePreserving.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HeisenbergConjugationMeasurePreserving.lean), which packs **1,518 theorems** into **2,178 lines / 231,107 bytes** (#21 by bytes) as a bulk theorem-export aggregator.
2. **Elaborated-Term Outliers (`CapelliIdentities` in `Development`):** Files such as [FixPiIff.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/FixPiIff.lean) (**8,029 lines**, **732,359 bytes**, yet only **2 theorems**) and [CovariantDegrees.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/CovariantDegrees.lean) (**6,170 lines**, **504,790 bytes**, **29 decls**) contain verbose explicit `@...` typeclass instance terms expanded across hundreds of indented lines, inflating byte size faster than line count (pushing them up in the top-25-by-bytes ranking).

| Rank | File (clickable `file://` link) | Lines | Bytes | Thm+Lem | Def+Str | Other | Total Decls | Dist / H | Bytes Rank |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | [IsAdmissibleSplittingCharPairMulTwist.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HermitianCurvatureProofs/IsAdmissibleSplittingCharPairMulTwist.lean) | 17,981 | 913,995 | 1,201 | 140 | 11 | 1,352 | 12 / 16 | #1 |
| 2 | [LatticeGluingRadicals.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/CuspSpanNormBounds/LatticeGluingRadicals.lean) | 9,252 | 454,809 | 579 | 60 | 3 | 642 | 9 / 24 | #5 |
| 3 | [FixPiIff.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/FixPiIff.lean) | 8,029 | 732,359 | 2 | 0 | 0 | 2 | 11 / 53 | #2 |
| 4 | [KappaEndpoints.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/CuspSpanNormBounds/KappaEndpoints.lean) | 6,945 | 381,379 | 336 | 87 | 0 | 423 | 11 / 34 | #8 |
| 5 | [UnipotentCoordinatesMeasurePreserving.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HermitianCurvatureProofs/UnipotentCoordinatesMeasurePreserving.lean) | 6,929 | 411,977 | 458 | 91 | 11 | 560 | 12 / 23 | #6 |
| 6 | [OscillatoryIntegralBounds.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/CuspSpanNormBounds/OscillatoryIntegralBounds.lean) | 6,333 | 321,152 | 454 | 74 | 3 | 531 | 10 / 26 | #10 |
| 7 | [CoordinateCommuteRaisingConstant.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HermitianCurvatureProofs/CoordinateCommuteRaisingConstant.lean) | 6,205 | 342,067 | 718 | 90 | 0 | 808 | 12 / 14 | #9 |
| 8 | [CovariantDegrees.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/CovariantDegrees.lean) | 6,170 | 504,790 | 20 | 9 | 0 | 29 | 11 / 0 | #3 |
| 9 | [WittFrameLocaliserOrders.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/GrowthBounds/WittFrameLocaliserOrders.lean) | 5,833 | 313,605 | 371 | 62 | 0 | 433 | 10 / 26 | #11 |
| 10 | [MemOfClosed.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/MemOfClosed.lean) | 5,746 | 478,050 | 8 | 4 | 0 | 12 | 12 / 0 | #4 |
| 11 | [InterlaceDifferenceShiftInvariant.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal/KernelLattices/KernelLocalFactors/InterlaceDifferenceShiftInvariant.lean) | 5,303 | 257,823 | 433 | 36 | 0 | 469 | 12 / 29 | #15 |
| 12 | [MulMemIntA.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/MulMemIntA.lean) | 4,969 | 405,284 | 4 | 5 | 0 | 9 | 21 / 0 | #7 |
| 13 | [BaseChangePreservesUnitaryOf.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/BaseChangePreservesUnitaryOf.lean) | 4,861 | 260,806 | 232 | 68 | 5 | 305 | 11 / 20 | #14 |
| 14 | [FrobeniusPowUniformizerFactorisation.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/FrobeniusPowUniformizerFactorisation.lean) | 4,707 | 238,215 | 316 | 35 | 7 | 358 | 12 / 19 | #18 |
| 15 | [BlockEstimateWords.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/CuspSpanNormBounds/BlockEstimateWords.lean) | 4,671 | 255,181 | 211 | 64 | 3 | 278 | 9 / 28 | #16 |
| 16 | [SuperdiagonalAdditionInvariance.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/FlagUnipotentLattices/MinkowskiFactorialBounds/SuperdiagonalAdditionInvariance.lean) | 4,546 | 236,044 | 235 | 9 | 0 | 244 | 11 / 4 | #19 |
| 17 | [TopChoiceBounds.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/GrowthBounds/TopChoiceBounds.lean) | 4,516 | 231,737 | 227 | 8 | 0 | 235 | 9 / 27 | #20 |
| 18 | [LatticeSystems.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/GrowthBounds/LatticeSystems.lean) | 4,451 | 224,188 | 230 | 47 | 6 | 283 | 10 / 23 | #22 |
| 19 | [CountingStatementReduction.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/GrowthBounds/CountingStatementReduction.lean) | 3,880 | 203,454 | 244 | 63 | 8 | 315 | 10 / 40 | #25 |
| 20 | [ComplexNormedInstanceCompat.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/ComplexNormedInstanceCompat.lean) | 3,669 | 283,079 | 10 | 17 | 0 | 27 | 8 / 0 | #12 |
| 21 | [HloweqTransfer.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/HloweqTransfer.lean) | 3,658 | 282,214 | 10 | 17 | 0 | 27 | 9 / 0 | #13 |
| 22 | [SelectionLemmas.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/SelectionLemmas.lean) | 3,547 | 252,719 | 23 | 11 | 0 | 34 | 10 / 0 | #17 |
| 23 | [TieOps.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/PolynomialDimension/MultinomialDepth/TieOps.lean) | 3,480 | 184,147 | 182 | 23 | 0 | 205 | 12 / 11 | — |
| 24 | [RestrictionIrrelevantDoubleLevelOperator.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HermitianCurvatureProofs/RestrictionIrrelevantDoubleLevelOperator.lean) | 3,447 | 174,971 | 254 | 33 | 1 | 288 | 10 / 15 | — |
| 25 | [FirstClaimLemmaTwoFourOfLemmaTwoThree.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction/GlobalSchurBounds/FirstClaimLemmaTwoFourOfLemmaTwoThree.lean) | 3,397 | 180,319 | 169 | 30 | 0 | 199 | 8 / 23 | — |

*(Files in the top 25 by bytes that fall just outside top 25 by lines: #21 [HeisenbergConjugationMeasurePreserving.lean](file:///home/ubuntu/riemann_proof/lean/src/Formalism/HermitianCurvature/HeisenbergConjugationMeasurePreserving.lean) at 231,107 B / 2,178 L; #23 [CoefMapNormEquivariantBasisOfFive.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/CoefMapNormEquivariantBasisOfFive.lean) at 212,920 B / 2,825 L; #24 [FreeModuleQuotient.lean](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic/IntegralCasts/CapelliIdentities/FreeModuleQuotient.lean) at 207,153 B / 2,516 L.)*
