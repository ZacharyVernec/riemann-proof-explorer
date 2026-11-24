# Codebase Structural Histograms & Lean 4 Comprehension Heuristics

This report quantitatively tests standard Lean 4 comprehension heuristics against the empirical structure of the **175,187** modules and **1,061,375** declarations in `lean/src/`:

- **Interactive Histogram Explorer:** [histograms.html](histograms.html) (offline SVG explorer with domain filtering across all discovered top-level directories)
- **Repeatable Generator:** [build_histograms.py](build_histograms.py)
- **Structured Dataset:** [histograms_data.json](histograms_data.json)
- **Module & Import Indexer:** [build_index.py](../build_index.py)

---

## 1. Standard Lean 4 Heuristics vs. Empirical Reality in This Codebase

Standard advice for reading Mathlib-style Lean 4 codebases assumes heavy `@[simp]` tagging, `/-! ... -/` module docstrings, `/-- ... -/` docstrings, and `private lemma` / `_aux` conventions. Across this proof codebase, some heuristics hold strongly while others invert completely:

| Heuristic | Empirical Finding in `lean/src/` | Practical Reading Implication |
|---|---|---|
| **Read module `/-!` docstrings and bottom-of-file declarations first** | **0** files contain `/-!` module docstrings and **0** declarations have `/--` docstrings (`0` `@[blueprint]` tags, `0` line comments). However, across **96,147** multi-declaration files, the **final declaration** is a public `theorem` **89.58%** of the time (**86,131** files), vs. **60.41%** for the first declaration (**58,084** files). | Skip docstring search; bottom-of-file reading works strongly because private helpers and definitions sit earlier and public payoff theorems sit at the end. |
| **Filter out `@[simp]` / `@[ext]` / `@[norm_cast]` / `@[aesop]` glue and 1-line proofs** | Only **8,444** declarations (**0.80%**) carry any `@[…]` tag (`6,881` `@[simp]`, `127` `@[ext]`, `25` `@[fun_prop]`, `3` `@[gcongr]`, `0` `@[norm_cast]`). Instead, **52,016** file-scoped `attribute […]` directives manage local typeclasses (`50,666` `local instance`), and **95,543** proofs (**11.67%** of theorems/lemmas) are 1-line tactics or `first \| exact …` forwarding wrappers (**43,992**). | Filtering out 1-line forwarding wrappers (`first \| exact …`), 1-line mechanical tactics (`49,252`), and `attribute [local instance]` boilerplate removes true glue better than scanning `@[…]` tags. |
| **Watch where stronger typeclasses enter** | Out of **1,090,043** signature binder occurrences, **54.83%** are baseline `Core Algebra` (`Field` `181,880`, `CommRing` `128,499`, `Algebra` `83,210`). Filtering out baseline classes surfaces domain-specific mathematical hypotheses: `NumberField` (`90,884`), `IsCMField` (`21,502`), `GrpObj` (`18,762`), `NormedAddCommGroup` (`16,409`), `IsLocalRing` (`10,973`), `ValuativeRel` (`10,824`), `IsNonarchimedeanLocalField` (`9,655`). | Excluding baseline algebraic/finiteness/topological classes isolates exactly which theory layer (`NumberField`/`IsCMField` vs. `NormedAddCommGroup`/`InnerProductSpace` vs. `GrpObj`/`IsLocalRing`) a module lives in. |
| **Look for cross-namespace equivalence bridges** | Signature-only longest-match scanning detects **84,580** equivalence-bearing declarations (`40,264` logical `↔` plus **44,316** bundled mathematical equivalences such as `≃ₗ` `10,706`, `≃` `9,297`, `≃+*` `8,314`, `≃ₐ` `5,935`, `≅` `2,842`). Meanwhile, **53,925** modules (**30.78%**) import from 2+ distinct `depth-2` sub-theories. | Bundled equivalence symbols (`≃ₗ`, `≃+*`, `≃ₐ`, `≅`, `≃ₜ`, `≃L`) and multi-subtheory import modules directly pinpoint abstraction boundaries. |
| **Check non-`@[simp]` reference fan-in** | Out of **175,187** modules, **173,215** (**98.87%**) have zero `@[simp]` declarations (`1,972` contain `@[simp]`). Exactly **106,668** modules (**60.89%**) have `in_degree = 1`, while only **3,871** non-`@[simp]` modules (**2.21%**) reach `in_degree >= 26` and only **62** reach `in_degree >= 500`. | Module import fan-in cleanly separates single-consumer proof steps from shared specification hubs (`CTSmallCone`, `UniformisationConclusion`, `UnifUniqSt`). |
| **Scan proof bodies for conceptual moves, not line count** | Across **651,659** tactic proofs, direct rewriting (`rw`/`rwa` in **70.08%** of tactic proofs, `exact` in **62.90%**) and `have` (**56.44%**) dominate, while `simp`/`simpa`/`simp_all`/`dsimp` appears in **48.99%**. Genuine structural branching moves are selective: `induction` (**6.43%**, `41,920` proofs), `classical` (**5.49%**), `choose` (**4.16%**), `by_contra`/`contrapose`/`exfalso` (**4.15%**), `filter_upwards` (**1.65%**). | Checking for `induction`, `by_contra`, `choose`, `classical`, `calc`, and multi-`obtain`/`have` blocks distinguishes conceptual steps from long `rw`/`ring`/`exact_mod_cast` bookkeeping. |
| **Check `theorem` vs. `lemma` and `private` / `_aux`** | `theorem` accounts for **73.87%** of all declarations (`784,043`) vs. **3.27%** for `lemma` (`34,661`). Only **6.86%** of `theorem`s are `private` (`53,754`), compared to **22.97%** of `lemma`s (`7,960`), and only **261** declarations have `aux`-suffixed names. | Like Mathlib, this repo uses `theorem` broadly; `private` visibility is a much sharper helper signal than `lemma` or `_aux` naming (`private` drops from `6.93%–7.28%` in Q1–Q3 to `0.14%` on final declarations). |

---

## 2. Automation Attributes & Proof Glue

Out of **818,704** `theorem` and `lemma` declarations (**651,659** tactic proofs and **167,045** term-mode proofs), mutually exclusive proof-shape classification breaks down as follows:

| Proof Shape Bucket | Count | Share of Theorems & Lemmas |
|---|---:|---:|
| Wrapper (`first \| exact …`) | 43,992 | 5.37% |
| 1-line mechanical (`simp`/`rfl`/`rw`/`exact`/…) | 49,252 | 6.02% |
| 1-line solver (`ring`/`omega`/`linarith`/…) | 965 | 0.12% |
| 1-line other tactic | 1,334 | 0.16% |
| Term-mode (no `by`) | 167,045 | 20.40% |
| Short tactic (2–5 lines) | 199,163 | 24.33% |
| Medium tactic (6–20 lines) | 227,340 | 27.77% |
| Long tactic (21–50 lines) | 93,090 | 11.37% |
| Deep tactic (51+ lines) | 36,523 | 4.46% |

### Declaration Attributes vs. File-Scoped `attribute […]` Directives

Declaration-level `@[…]` attributes appear on only **8,444** declarations (**0.80%** of `1,061,375`, totaling **8,723** tag occurrences), whereas file-scoped `attribute […]` directives appear **52,016** times—overwhelmingly activating local typeclass instances rather than rewriting rules:

| Top `@[…]` Declaration Tags | Count | Top File `attribute […]` Directives | Count |
|---|---:|---|---:|
| `@[simp]` | 6,881 | `attribute [local instance]` | 50,666 |
| `@[reducible]` | 853 | `attribute [instance]` | 796 |
| `@[reassoc]` (incl. `reassoc (attr := simp)`) | 577 | `attribute [-instance]` | 459 |
| `@[ext]` | 127 | `attribute [local irreducible]` | 61 |
| `@[instance_reducible]` | 103 | `attribute [irreducible]` | 13 |
| `@[simps]` | 68 | `attribute [local simp]` | 9 |
| `@[to_additive]` | 33 | `attribute [local fun_prop]` | 4 |
| `@[fun_prop]` | 25 | `attribute [to_additive]` | 2 |

The most frequent `attribute [local instance]` targets reflect the codebase's core algebraic-geometric and local-field scaffolding: `Formalism.BasicNotions.Host.cmStar` (`24,775`), `Over.cartesianMonoidalCategory` (`15,195`), `GlobalTheory.LocalData.complRel` (`6,905`), `GlobalTheory.LocalData.isLocalField` (`6,891`), `Matrix.normedAddCommGroup` (`1,796`), `Matrix.normedSpace` (`1,796`), and `borelKw` / `borelSpaceKw` (`1,429` each). Compiler tuning options are also concentrated on `set_option maxHeartbeats` (`57,545`), `autoImplicit` (`11,202`), `maxSynthPendingDepth` (`7,478`), and `synthInstance.maxHeartbeats` (`7,357`).

---

## 3. Typeclass Usage & Mathematical Hypotheses

Restricting `[…]` extraction strictly to declaration signatures and `variable` headers yields **1,090,043** typeclass binder occurrences across six mathematical tiers:

| Mathematical Tier | Binder Occurrences | Share |
|---|---:|---:|
| Core Algebra (`Field`, `CommRing`, `Algebra`, `Module`, `AddCommGroup`, …) | 597,657 | 54.83% |
| Number & Local Fields (`NumberField`, `IsCMField`, `ValuativeRel`, …) | 161,376 | 14.80% |
| Finiteness & Type-Level (`Fintype`, `Fact`, `DecidableEq`, …) | 121,806 | 11.17% |
| Analysis, Topology & Measure (`TopologicalSpace`, `NormedAddCommGroup`, …) | 111,805 | 10.26% |
| Commutative & Algebraic Geometry (`GrpObj`, `IsLocalRing`, `IsCommMonObj`, …) | 63,409 | 5.82% |
| Other Domain-Specific | 33,990 | 3.12% |

Filtering out the **21** baseline classes (`Field`, `CommRing`, `Algebra`, `Fintype`, `AddCommGroup`, `Module`, `Fact`, `TopologicalSpace`, `Group`, `DecidableEq`, `CharZero`, `NeZero`, etc.) exposes the specialized mathematical hypotheses driving each top-level domain:

- **Overall top stronger typeclasses:** `NumberField` (`90,884`), `IsCMField` (`21,502`), `IsDomain` (`21,141`), `GrpObj` (`18,762`), `NormedAddCommGroup` (`16,409`), `FiniteDimensional` (`11,556`), `IsLocalRing` (`10,973`), `ValuativeRel` (`10,824`), `MeasurableSpace` (`9,826`), `IsNonarchimedeanLocalField` (`9,655`), `InnerProductSpace` (`9,143`), `StarRing` (`8,864`).
- **Domain stratification:** `Development` (`141,928` modules) concentrates on `NumberField` (`78,763`), `IsCMField` (`20,299`), `IsDomain` (`18,372`), `GrpObj` (`18,337`), and `IsLocalRing` (`10,412`); `Formalism` (`18,254` modules) shifts toward `NormedAddCommGroup` (`5,031`), `StarRing` (`3,105`), and `InnerProductSpace` (`2,861`); `GroundTheory` (`8,507` modules) highlights `IsDiscreteRep` (`865`), `ValuativeRel` (`584`), `IsTopologicalGroup` (`543`), and `IsNonarchimedeanLocalField` (`459`); `PositivityTheory` (`449` modules) centers on `NumberField` (`350`), `IsTotallyReal` (`174`), `IsNonarchimedeanLocalField` (`121`), and `IsAlgClosure` (`102`).

---

## 4. Proof Strategies: Conceptual Moves vs. Automated Solvers

Scanning tactic bodies across all **651,659** tactic-mode proofs separates ubiquitous rewriting mechanics from targeted automated solvers and conceptual proof moves:

| Group | Tactic / Move | Tactic Proofs Using | Share of Tactic Proofs | Total Invocations |
|---|---|---:|---:|---:|
| Direct plumbing | `rw` / `rwa` | 456,683 | 70.08% | 1,649,995 |
| Direct plumbing | `exact` | 409,881 | 62.90% | 976,393 |
| Direct plumbing | `intro` / `intros` / `rintro` | 277,014 | 42.51% | 600,110 |
| Direct plumbing | `refine` | 253,493 | 38.90% | 473,367 |
| Direct plumbing | `rfl` | 222,114 | 34.08% | 484,543 |
| Conceptual | `have` (intermediate claim/object) | 367,824 | 56.44% | 2,057,401 |
| Conceptual | `obtain` / `rcases` / `cases` | 230,409 | 35.36% | 594,728 |
| Conceptual | `let` / `set` (local binding) | 90,419 | 13.88% | 205,255 |
| Conceptual | `by_cases` (case split) | 47,767 | 7.33% | 67,174 |
| Conceptual | `induction` | 41,920 | 6.43% | 48,239 |
| Conceptual | `classical` | 35,755 | 5.49% | 35,837 |
| Conceptual | `calc` (calculational chain) | 28,273 | 4.34% | 38,725 |
| Conceptual | `choose` (choice extraction) | 27,112 | 4.16% | 40,236 |
| Conceptual | `by_contra` / `contrapose` / `exfalso` | 27,017 | 4.15% | 33,554 |
| Conceptual | `filter_upwards` | 10,720 | 1.65% | 14,497 |
| Solver | `simp` / `simpa` / `simp_all` / `dsimp` | 319,237 | 48.99% | 751,872 |
| Solver | `ring` / `noncomm_ring` | 67,263 | 10.32% | 106,190 |
| Solver | `omega` | 48,684 | 7.47% | 120,023 |
| Solver | `exact_mod_cast` / `push_cast` / `norm_cast` | 45,257 | 6.94% | 81,293 |
| Solver | `linarith` / `nlinarith` | 29,852 | 4.58% | 89,783 |
| Solver | `positivity` | 19,152 | 2.94% | 43,527 |
| Solver | `abel` / `group` / `module` | 16,886 | 2.59% | 25,390 |
| Solver | `linear_combination` | 15,683 | 2.41% | 24,522 |
| Solver | `field_simp` | 13,985 | 2.15% | 18,734 |

---

## 5. Cross-Namespace & Equivalence "Bridge" Signatures

Longest-match tokenization over declaration signatures identifies **84,580** declarations containing explicit equivalence/isomorphism constructors:

| Constructor | Declarations | Total Occurrences |
|---|---:|---:|
| Logical iff (`↔`) | 40,264 | 44,425 |
| Linear equiv (`≃ₗ`) | 10,706 | 12,122 |
| Type equivalence (`≃`) | 9,297 | 10,404 |
| Ring equiv (`≃+*`) | 8,314 | 8,881 |
| Algebra equiv (`≃ₐ`) | 5,935 | 7,336 |
| Categorical iso (`≅`) | 2,842 | 3,391 |
| Multiplicative equiv (`≃*`) | 2,056 | 2,175 |
| Additive equiv (`≃+`) | 1,970 | 2,365 |
| Homeomorphism (`≃ₜ`) | 1,712 | 1,840 |
| Linear isometric equiv (`≃ₗᵢ`) | 700 | 759 |
| Continuous linear equiv (`≃L`) | 442 | 454 |
| Measurable equiv (`≃ᵐ`) | 282 | 287 |
| Order iso (`≃o`) & Isometry equiv (`≃ᵢ`) | 60 | 60 |

Cross-module synthesis is also visible in import breadth and `open` headers: **53,925** modules (**30.78%**) import from 2+ distinct `depth-2` sub-theories (`42,303` from `2`, `11,540` from `3–5`, `82` from `6+`), **37,379** modules (**21.34%**) import from 2+ distinct top-level domains, and **107,212** modules (**61.20%**) open **5+** distinct root namespaces simultaneously (led by `GlobalTheory` in `110,792` files, `NumberField` in `88,828`, `Formalism` in `84,111`, and `ReciprocityTheory` in `57,908`).

---

## 6. Non-`@[simp]` Reference Fan-In & Reuse

Joining file-level `@[simp]` detection with the SQLite import graph (`analysis/data/graph.sqlite`) shows a steep heavy-tailed reuse distribution:

| Module `in_degree` | Non-`@[simp]` Modules | `@[simp]` Modules | Total Modules | Share |
|---|---:|---:|---:|---:|
| `0` (`Main`) | 1 | 0 | 1 | 0.00% |
| `1` | 106,042 | 626 | 106,668 | 60.89% |
| `2` | 29,082 | 281 | 29,363 | 16.76% |
| `3–5` | 21,344 | 372 | 21,716 | 12.40% |
| `6–10` | 7,491 | 215 | 7,706 | 4.40% |
| `11–25` | 5,384 | 252 | 5,636 | 3.22% |
| `26–100` | 3,068 | 187 | 3,255 | 1.86% |
| `101–500` | 741 | 38 | 779 | 0.44% |
| `500+` | 62 | 1 | 63 | 0.04% |

The top non-`@[simp]` hub modules are foundational definition contracts and literature interfaces, including `CTSmallCone` (`in_degree = 3,088`, `54` defs/structs), `SiegelWeilAnisotropicHermitian` (`2,972`), `DiscreteSeriesHermitianUnique` (`2,518`), `ExistsNormLeHeightPow` (`2,426`), `UniformisationConclusion` (`2,390`, `7` importer sub-theories), `UnifUniqSt` (`2,284`), and `CohomologicalCsdTempered` (`2,242`).

---

## 7. Declaration Taxonomy & Top-to-Bottom File Order

Across all **1,061,375** declarations:

| Kind | Public | Private | Protected | Total | Share |
|---|---:|---:|---:|---:|---:|
| `theorem` | 730,289 | 53,754 | 0 | 784,043 | 73.87% |
| `def` | 209,288 | 3,531 | 0 | 212,819 | 20.05% |
| `lemma` | 26,701 | 7,960 | 0 | 34,661 | 3.27% |
| `abbrev` | 12,989 | 212 | 1 | 13,202 | 1.24% |
| `structure` | 8,241 | 45 | 0 | 8,286 | 0.78% |
| `instance` | 8,139 | 61 | 0 | 8,200 | 0.77% |
| `inductive` | 120 | 1 | 0 | 121 | 0.01% |
| `class` | 43 | 0 | 0 | 43 | 0.00% |

Within the **79,955** files containing 3+ declarations (normalized into five equal declaration-order quintiles `Q1`–`Q5`) and the **96,147** files containing 2+ declarations (`First Decl` vs. `Last Decl`), top-down build order is strongly polarized:

- **Definitions front-loaded:** `def` / `abbrev` makes up **28.70%** of `Q1` (`63,059` declarations) and declines monotonically to **18.36%** in `Q5` (`28,517`), dropping to **9.19%** on the final declaration.
- **Public theorems back-loaded:** Public `theorem` rises from **59.18%** in `Q1` (`130,047`) to **75.16%** in `Q5` (`116,751`), and reaches **89.58%** (`86,131`) on the final declaration of multi-declaration files.
- **Private helpers excluded from the payoff slot:** `private theorem`/`private lemma` comprises **6.93%–7.28%** across `Q1`–`Q3`, falls to **3.17%** in `Q5`, and drops to **0.14%** (`133` files) as the final declaration.
- **File granularity:** **78,866** modules (**45.02%**) hold a single declaration, **16,192** (**9.24%**) hold 2, **28,794** (**16.44%**) hold 3–5, and **51,161** (**29.20%**) hold 6+.

---

## 8. Repeatable Extraction Methodology & Caveats

1. **Deterministic Pipeline (`build_histograms.py`):** Loads the sorted module and edge tables from `analysis/data/graph.sqlite` (optionally regenerating them via `--rebuild-index`), discovers all top-level domains dynamically sorted by `(-module_count, top_dir)`, and scans all `.lean` files in deterministic sorted chunks using multiprocessing.
2. **Signature-Only vs. Proof-Body Separation:** Typeclasses (`[…]`) and equivalence constructors (`≃ₗᵢ|≃+*|≃ₗ|…|↔`) are extracted strictly from declaration headers (before `:=` or trailing `where`) and `variable` lines so tactic arguments such as `rw [Finset.sum_comm]` never contaminate typeclass counts, and longest-match alternation prevents `≃+*` or `≃ₗᵢ` from double-counting as `≃`.
3. **Syntactic Scope Caveat:** Because the scanner parses Lean source text rather than elaborated `.olean` environments, implicit typeclass synthesis, tactic-generated sub-calls inside `simp`/`aesop`, and macro expansions are not unrolled. All counts are exact syntactic counts over `lean/src/` (totaling `1,061,375` declarations vs. `1,057,807` in `analysis/data/meta.json`—a `+0.34%` difference attributable to anonymous `instance` declarations and `set_option ... in` headers).
4. **Regeneration:** After any codebase refactor, run:

```bash
python3 analysis/codebase_histograms/build_histograms.py --rebuild-index
node analysis/render_reports.js
```
