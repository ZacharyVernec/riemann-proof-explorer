# Codebase Structural Histograms & Lean 4 Comprehension Heuristics (`community-307cef33`)

This report quantitatively tests standard Lean 4 comprehension heuristics against the empirical structure of the **59,836** reachable modules and **764,486** declarations in `src/`:

- **Interactive Histogram Explorer:** [histograms.html](histograms.html) (offline SVG explorer with domain filtering across all discovered top-level directories)
- **Repeatable Generator:** [build_histograms.py](build_histograms.py)
- **Structured Dataset:** [histograms_data.json](histograms_data.json)
- **Module & Import Indexer:** [build_index.py](../build_index.py)

---

## 1. Standard Lean 4 Heuristics vs. Empirical Reality in This Codebase

Standard advice for reading Mathlib-style Lean 4 codebases assumes heavy `@[simp]` tagging, `/-! ... -/` module docstrings, `/-- ... -/` docstrings, and `private lemma` / `_aux` conventions. Across this proof codebase, some heuristics hold strongly while others invert completely:

| Heuristic | Empirical Finding in `src/` | Practical Reading Implication |
|---|---|---|
| **Read module `/-!` docstrings and bottom-of-file declarations first** | **11** files contain `/-!` module docstrings and **335** declarations carry `/--` docstrings (`243,994` line comments). Across **49,460** multi-declaration files, the **final declaration** is a public `theorem` **86.61%** of the time (**42,839** files), vs. **57.59%** for the first declaration (**28,485** files). | Docstrings remain sparse outside focal files, while bottom-of-file reading holds strongly because definitions and helpers precede public payoff theorems. |
| **Filter out `@[simp]` / `@[ext]` / `@[norm_cast]` glue and 1-line proofs** | Only **4,443** declarations (**0.58%**) carry any `@[…]` tag (`3,419` `@[simp]`, `71` `@[ext]`, `24` `@[fun_prop]`). Instead, **43,635** file-scoped `attribute […]` directives manage local typeclasses (`42,618` `local instance`), and **51,229** proofs (**8.53%** of theorems/lemmas) are 1-line tactics or `first \\| exact …` forwarding wrappers (**10,846**). | Filtering out forwarding wrappers (`first \\| exact …`), 1-line mechanical tactics (`38,700`), and `attribute [local instance]` boilerplate removes true glue better than scanning `@[…]` tags. |
| **Watch where stronger typeclasses enter** | Out of **776,830** signature binder occurrences, **55.94%** are baseline `Core Algebra` (`Field` `125,976`, `CommRing` `96,188`, `Algebra` `58,561`). Filtering out baseline classes surfaces domain-specific hypotheses: `NumberField` (`57,031`), `IsDomain` (`15,528`), `IsCMField` (`14,886`), `GrpObj` (`14,017`), `NormedAddCommGroup` (`12,343`), `IsLocalRing` (`8,247`), `FiniteDimensional` (`7,973`). | Excluding baseline algebraic/finiteness/topological classes isolates which mathematical theory layer a module operates in. |
| **Look for cross-namespace equivalence bridges** | Signature-only longest-match scanning detects **60,985** equivalence-bearing declarations (`29,204` logical `↔` plus **31,781** bundled mathematical equivalences such as `≃ₗ` `8,174`, `≃` `6,433`, `≃+*` `5,788`, `≃ₐ` `4,263`, `≅` `1,801`). Meanwhile, **25,978** modules (**43.42%**) import from 2+ distinct `depth-2` sub-theories. | Bundled equivalence symbols (`≃ₗ`, `≃+*`, `≃ₐ`, `≅`, `≃ₜ`, `≃L`) and multi-subtheory import modules directly pinpoint abstraction boundaries. |
| **Check non-`@[simp]` reference fan-in** | Out of **59,836** modules, **58,676** (**98.06%**) have zero `@[simp]` declarations (`1,160` contain `@[simp]`). Exactly **11,643** modules (**19.46%**) have `in_degree = 1`, while only **1,989** non-`@[simp]` modules (**3.32%**) reach `in_degree >= 26` and **10** reach `in_degree >= 500`. | Module import fan-in cleanly separates single-consumer proof steps from shared specification hubs (`IsCompletedStrictHens`, `LinksDefs`, `DataNLoc`). |
| **Scan proof bodies for conceptual moves, not line count** | Across **481,515** tactic proofs, direct rewriting (`rw`/`rwa` in **0.00%**, `exact` in **61.14%**) and `have` (**59.29%**) dominate, while `simp`/`simpa`/`simp_all`/`dsimp` appears in **0.00%**. Genuine structural moves are selective: `induction` (**7.05%**, `33,938`), `classical` (**6.00%**), `choose` (**4.42%**), `by_contra`/`contrapose` (**4.41%**). | Checking for `induction`, `by_contra`, `choose`, `classical`, `calc`, and multi-`obtain`/`have` blocks distinguishes conceptual steps from long `rw`/`ring` bookkeeping. |
| **Check `theorem` vs. `lemma` and `private` / `_aux`** | `theorem` accounts for **74.98%** of declarations (`573,228`) vs. **3.54%** for `lemma` (`27,026`). Only **8.02%** of `theorem`s are `private` (`45,949`), vs. **25.54%** of `lemma`s (`6,903`), and `187` declarations have `aux`-suffixed names. | `private` visibility is a much sharper helper signal than `lemma` or `_aux` naming (`private` drops from `7.32%` in Q1 and `5.12%` in Q5 to `0.05%` on final declarations). |

---

## 2. Automation Attributes & Proof Glue

Out of **600,254** `theorem` and `lemma` declarations (**481,515** tactic proofs and **118,739** term-mode proofs), mutually exclusive proof-shape classification breaks down as follows:

| Proof Shape Bucket | Count | Share of Theorems & Lemmas |
|---|---:|---:|
| Wrapper (first \| exact …) | 10,846 | 1.81% |
| 1-line mechanical (simp/rfl/rw/exact/…) | 38,700 | 6.45% |
| 1-line solver (ring/omega/linarith/…) | 688 | 0.11% |
| 1-line other tactic | 995 | 0.17% |
| Term-mode (no by) | 118,739 | 19.78% |
| Short tactic (2–5 lines) | 152,845 | 25.46% |
| Medium tactic (6–20 lines) | 175,511 | 29.24% |
| Long tactic (21–50 lines) | 72,641 | 12.10% |
| Deep tactic (51+ lines) | 29,289 | 4.88% |

### Declaration Attributes vs. File-Scoped `attribute […]` Directives

Declaration-level `@[…]` attributes appear on **4,443** declarations (**0.58%** of `764,486`, totaling **4,507** tag occurrences), whereas file-scoped `attribute […]` directives appear **43,635** times—overwhelmingly activating local typeclass instances rather than rewriting rules:

| Top `@[…]` Declaration Tags | Count | Top File `attribute […]` Directives | Count |
|---|---:|---|---:|
| `@[simp]` | 3,419 | `attribute [local instance]` | 42,618 |
| `@[reducible]` | 657 | `attribute [instance]` | 701 |
| `@[reassoc]` | 176 | `attribute [-instance]` | 213 |
| `@[instance_reducible]` | 74 | `attribute [local irreducible]` | 68 |
| `@[ext]` | 71 | `attribute [local simp]` | 13 |
| `@[fun_prop]` | 24 | `attribute [irreducible]` | 11 |
| `@[no_expose]` | 20 | `attribute [local fun_prop]` | 4 |
| `@[to_additive]` | 14 | `attribute [-simp]` | 1 |

The most frequent `attribute [local instance]` targets include `Formalism.BasicNotions.Host.cmStar` (`21,586`), `Over.cartesianMonoidalCategory` (`12,395`), `GlobalTheory.LocalData.complRel` (`5,250`), `GlobalTheory.LocalData.isLocalField` (`5,241`), `Matrix.normedAddCommGroup` (`1,648`), `Matrix.normedSpace` (`1,648`), `borelKw` (`1,084`). Top compiler tuning options: `set_option autoImplicit` (`7,669`), `set_option maxSynthPendingDepth` (`5,617`), `set_option backward.isDefEq.respectTransparency` (`1,485`), `set_option synthInstance.maxHeartbeats` (`705`).

---

## 3. Typeclass Usage & Mathematical Hypotheses

Restricting `[…]` extraction strictly to declaration signatures and `variable` headers yields **776,830** typeclass binder occurrences across six mathematical tiers:

| Mathematical Tier | Binder Occurrences | Share |
|---|---:|---:|
| Core Algebra (`Field`, `CommRing`, `Algebra`, `Module`, `AddCommGroup`, …) | 434,587 | 55.94% |
| Number & Local Fields (`NumberField`, `IsCMField`, `ValuativeRel`, …) | 103,312 | 13.30% |
| Commutative & Algebraic Geometry (`GrpObj`, `IsLocalRing`, `IsCommMonObj`, …) | 45,303 | 5.83% |
| Analysis, Topology & Measure (`TopologicalSpace`, `NormedAddCommGroup`, …) | 79,912 | 10.29% |
| Finiteness & Type-Level (`Fintype`, `Fact`, `DecidableEq`, …) | 88,410 | 11.38% |
| Other Domain-Specific (Project- and theory-specific predicates) | 25,306 | 3.26% |

Filtering out the **21** baseline classes exposes the specialized mathematical hypotheses driving each top-level domain:

- **Overall top stronger typeclasses:** `NumberField` (`57,031`), `IsDomain` (`15,528`), `IsCMField` (`14,886`), `GrpObj` (`14,017`), `NormedAddCommGroup` (`12,343`), `IsLocalRing` (`8,247`), `FiniteDimensional` (`7,973`), `ValuativeRel` (`7,270`), `StarRing` (`7,014`), `InnerProductSpace` (`6,937`), `MeasurableSpace` (`6,613`), `IsNonarchimedeanLocalField` (`6,286`).
- **Domain stratification:** `Development` (`41,263` modules: `NumberField` (`47,624`), `IsCMField` (`13,839`), `GrpObj` (`13,627`), `IsDomain` (`13,102`)); `Formalism` (`9,901` modules: `NumberField` (`5,941`), `NormedAddCommGroup` (`4,279`), `StarRing` (`2,544`), `InnerProductSpace` (`2,313`)); `GroundTheory` (`5,217` modules: `NumberField` (`1,334`), `IsDiscreteRep` (`826`), `FiniteDimensional` (`535`), `IsTopologicalGroup` (`530`)); `ReciprocityTheory` (`2,393` modules: `NumberField` (`1,050`), `NormedAddCommGroup` (`887`), `InnerProductSpace` (`606`), `IsCMField` (`470`)); `CompanionTheory` (`685` modules: `NumberField` (`788`), `NormedAddCommGroup` (`550`), `InnerProductSpace` (`405`), `MeasurableSpace` (`359`)).

---

## 4. Proof Strategies: Conceptual Moves vs. Automated Solvers

Scanning tactic bodies across all **481,515** tactic-mode proofs separates ubiquitous rewriting mechanics from targeted automated solvers and conceptual proof moves:

| Group | Tactic / Move | Tactic Proofs Using | Share of Tactic Proofs | Total Invocations |
|---|---|---:|---:|---:|
| Direct plumbing | rw / rwa | 354,541 | 73.63% | 1,300,593 |
| Direct plumbing | exact | 294,419 | 61.14% | 704,503 |
| Direct plumbing | refine | 197,214 | 40.96% | 371,531 |
| Direct plumbing | intro / intros / rintro | 181,230 | 37.64% | 441,894 |
| Direct plumbing | rfl | 172,962 | 35.92% | 379,472 |
| Conceptual | have (intermediate claim/object) | 285,473 | 59.29% | 1,604,353 |
| Conceptual | obtain / rcases / cases | 177,611 | 36.89% | 462,606 |
| Conceptual | let / set (local binding) | 70,892 | 14.72% | 162,487 |
| Conceptual | by_cases (case split) | 37,834 | 7.86% | 53,763 |
| Conceptual | induction | 33,938 | 7.05% | 39,010 |
| Conceptual | classical | 28,898 | 6.00% | 28,994 |
| Conceptual | calc (calculational chain) | 21,855 | 4.54% | 29,650 |
| Conceptual | choose (choice extraction) | 21,293 | 4.42% | 31,593 |
| Conceptual | by_contra / contrapose / exfalso | 21,239 | 4.41% | 26,519 |
| Conceptual | filter_upwards | 7,953 | 1.65% | 10,840 |
| Solver | simp / simpa / simp_all / dsimp | 248,051 | 51.51% | 589,076 |
| Solver | ring / noncomm_ring | 51,072 | 10.61% | 80,481 |
| Solver | omega | 37,844 | 7.86% | 95,793 |
| Solver | exact_mod_cast / push_cast / norm_cast | 33,997 | 7.06% | 61,037 |
| Solver | linarith / nlinarith | 21,378 | 4.44% | 62,600 |
| Solver | abel / group / module | 13,657 | 2.84% | 20,677 |
| Solver | positivity | 13,631 | 2.83% | 30,331 |
| Solver | linear_combination | 12,522 | 2.60% | 19,632 |
| Solver | field_simp | 10,127 | 2.10% | 13,449 |

---

## 5. Cross-Namespace & Equivalence "Bridge" Signatures

Longest-match tokenization over declaration signatures identifies **60,985** declarations containing explicit equivalence/isomorphism constructors:

| Constructor | Declarations | Total Occurrences |
|---|---:|---:|
| Logical iff (↔) | 29,204 | 32,223 |
| Linear equiv (≃ₗ) | 8,174 | 9,249 |
| Type equivalence (≃) | 6,433 | 7,185 |
| Ring equiv (≃+*) | 5,788 | 6,226 |
| Algebra equiv (≃ₐ) | 4,263 | 5,213 |
| Categorical iso (≅) | 1,801 | 2,090 |
| Multiplicative equiv (≃*) | 1,556 | 1,646 |
| Additive equiv (≃+) | 1,351 | 1,592 |
| Homeomorphism (≃ₜ) | 1,240 | 1,322 |
| Linear isometric equiv (≃ₗᵢ) | 571 | 625 |
| Continuous linear equiv (≃L) | 326 | 334 |
| Measurable equiv (≃ᵐ) | 241 | 246 |
| Order iso (≃o) | 37 | 37 |

Cross-module synthesis is also visible in import breadth and `open` headers: **25,978** modules (**43.42%**) import from 2+ distinct `depth-2` sub-theories, **18,900** modules (**31.59%**) import from 2+ distinct top-level domains, and **35,883** modules (**59.97%**) open **5+** distinct root namespaces simultaneously (led by `GlobalTheory` in `30,850` files, `NumberField` in `29,574` files, `Formalism` in `29,250` files, `Matrix` in `20,704` files).

---

## 6. Non-`@[simp]` Reference Fan-In & Reuse

Joining file-level `@[simp]` detection with the SQLite import graph (`graph.sqlite`) shows a steep heavy-tailed reuse distribution:

| Module `in_degree` | Non-`@[simp]` Modules | `@[simp]` Modules | Total Modules | Share |
|---|---:|---:|---:|---:|
| `0` | 1 | 0 | 1 | 0.00% |
| `1` | 11,474 | 169 | 11,643 | 19.46% |
| `2` | 18,664 | 197 | 18,861 | 31.52% |
| `3-5` | 16,477 | 274 | 16,751 | 27.99% |
| `6-10` | 6,374 | 190 | 6,564 | 10.97% |
| `11-25` | 3,697 | 173 | 3,870 | 6.47% |
| `26-100` | 1,691 | 126 | 1,817 | 3.04% |
| `101-500` | 288 | 31 | 319 | 0.53% |
| `500+` | 10 | 0 | 10 | 0.02% |

The top non-`@[simp]` hub modules are foundational definition contracts and shared theory interfaces, led by `IsCompletedStrictHens` (`in_degree = 1,138`), `LinksDefs` (`in_degree = 986`), `DataNLoc` (`in_degree = 895`), `CubeSymmetricSwapFirst` (`in_degree = 813`), `WeilTensorModels` (`in_degree = 713`), `GenusMassVolumes` (`in_degree = 611`), `LocalNewformFunction` (`in_degree = 596`).

---

## 7. Declaration Taxonomy & Top-to-Bottom File Order

Across all **764,486** declarations:

| Kind | Public | Private | Protected | Total | Share |
|---|---:|---:|---:|---:|---:|
| `theorem` | 527,279 | 45,949 | 0 | 573,228 | 74.98% |
| `def` | 138,571 | 3,134 | 3 | 141,708 | 18.54% |
| `lemma` | 20,123 | 6,903 | 0 | 27,026 | 3.54% |
| `abbrev` | 9,874 | 217 | 1 | 10,092 | 1.32% |
| `structure` | 6,260 | 46 | 1 | 6,307 | 0.82% |
| `instance` | 5,942 | 65 | 0 | 6,007 | 0.79% |
| `inductive` | 82 | 1 | 0 | 83 | 0.01% |
| `class` | 35 | 0 | 0 | 35 | 0.00% |

Within the **43,948** files containing 3+ declarations (`Q1`–`Q5`) and the **49,460** files containing 2+ declarations (`First Decl` vs. `Last Decl`), top-down build order is strongly polarized:

- **Definitions front-loaded:** `def` / `abbrev` makes up **24.92%** of `Q1` (`41,211`) vs. **14.62%** in `Q5` (`19,015`), dropping to **11.68%** on the final declaration.
- **Public theorems back-loaded:** Public `theorem` rises from **62.82%** in `Q1` (`103,888`) to **76.99%** in `Q5` (`100,160`), reaching **86.61%** (`42,839`) on the final declaration.
- **Private helpers excluded from payoff slot:** `private theorem`/`private lemma` comprises **7.32%** in `Q1`, falls to **5.12%** in `Q5`, and drops to **0.05%** (`26` files) on the final declaration.
- **File granularity:** **10,031** modules (**16.76%**) hold 1 declaration, **5,512** (**9.21%**) hold 2, **11,774** (**19.68%**) hold 3–5, and **32,174** (**53.77%**) hold 6+.

### Domain Breakdown

| Domain | Modules | Declarations |
|---|---:|---:|
| `Development` | 41,263 | 504,832 |
| `Formalism` | 9,901 | 168,605 |
| `GroundTheory` | 5,217 | 49,290 |
| `ReciprocityTheory` | 2,393 | 29,201 |
| `CompanionTheory` | 685 | 9,336 |
| `PositivityTheory` | 226 | 3,013 |
| `Lemmata` | 149 | 200 |
| `(root)` | 2 | 9 |

---

## 8. Repeatable Extraction Methodology & Caveats

1. **Deterministic Pipeline (`build_histograms.py`):** Loads the sorted reachable module and edge tables from `graph.sqlite`, discovers all top-level domains dynamically sorted by `(-module_count, top_dir)`, and scans all `.lean` files in deterministic sorted chunks using multiprocessing.
2. **Signature-Only vs. Proof-Body Separation:** Typeclasses (`[…]`) and equivalence constructors (`≃ₗᵢ|≃+*|≃ₗ|…|↔`) are extracted strictly from declaration headers (before `:=` or trailing `where`) and `variable` lines so tactic arguments such as `rw [Finset.sum_comm]` never contaminate typeclass counts, and longest-match alternation prevents `≃+*` or `≃ₗᵢ` from double-counting as `≃`.
3. **Syntactic Scope Caveat:** Because the scanner parses Lean source text rather than elaborated `.olean` environments, implicit typeclass synthesis, tactic-generated sub-calls inside `simp`/`aesop`, and macro expansions are not unrolled. All counts are exact syntactic counts over `src/` (totaling `764,486` declarations vs. `761,777` in `meta.json`—a `+0.36%` difference attributable to anonymous `instance` declarations and `set_option ... in` headers).
4. **Regeneration:** To rebuild after a codebase change:

```bash
python3 analysis/build_all.py --version community-307cef33 --steps index,histograms
# Or standalone:
python3 analysis/codebase_histograms/build_histograms.py --db-path analysis/versions/community-307cef33/data/graph.sqlite --out-dir analysis/versions/community-307cef33/codebase_histograms --version-label community-307cef33
node analysis/render_reports.js
```
