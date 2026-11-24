# Codebase Structural Histograms (`community-307cef33`)

Empirical structural analysis across `src/` (**59,836 reachable modules**, **764,486 declarations**, **600,254 theorems & lemmas**) paired with the interactive explorer in [histograms.html](histograms.html).

---

## 1. Corpus Totals & Proof Glue

| Metric | Count / Share |
|---|---:|
| Reachable Lean modules | 59,836 |
| Total declarations | 764,486 |
| Theorems & lemmas | 600,254 |
| Tactic proofs (`by ...`) | 481,515 |
| Term-mode proofs | 118,739 |
| Attribute-tagged declarations | 4,443 |
| Modules defining `@[simp]` | 1,160 |

### Proof Shape Distribution

| Proof Shape | Count | Share of Thm/Lem |
|---|---:|---:|
| Wrapper (first | exact …) (`wrapper_forwarding`) | 10,846 | 1.8% |
| 1-line mechanical (simp/rfl/rw/exact/…) (`oneliner_mech`) | 38,700 | 6.4% |
| 1-line solver (ring/omega/linarith/…) (`oneliner_solver`) | 688 | 0.1% |
| 1-line other tactic (`oneliner_other`) | 995 | 0.2% |
| Term-mode (no by) (`term_mode`) | 118,739 | 19.8% |
| Short tactic (2–5 lines) (`short_2_5`) | 152,845 | 25.5% |
| Medium tactic (6–20 lines) (`medium_6_20`) | 175,511 | 29.2% |
| Long tactic (21–50 lines) (`long_21_50`) | 72,641 | 12.1% |
| Deep tactic (51+ lines) (`deep_51_plus`) | 29,289 | 4.9% |

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

### Top Attributes & Typeclasses

| Attribute | Count | Typeclass Binder | Signature Occurrences |
|---|---:|---|---:|
| `@[simp]` | 3,419 | `[Field]` | 125,976 |
| `@[reducible]` | 657 | `[CommRing]` | 96,188 |
| `@[reassoc]` | 176 | `[Algebra]` | 58,561 |
| `@[instance_reducible]` | 74 | `[NumberField]` | 57,031 |
| `@[ext]` | 71 | `[Fintype]` | 40,692 |
| `@[fun_prop]` | 24 | `[AddCommGroup]` | 33,530 |
| `@[no_expose]` | 20 | `[Module]` | 31,776 |
| `@[to_additive]` | 14 | `[Fact]` | 22,432 |
| `@[simps]` | 12 | `[TopologicalSpace]` | 21,539 |
| `@[irreducible]` | 9 | `[Group]` | 20,219 |

