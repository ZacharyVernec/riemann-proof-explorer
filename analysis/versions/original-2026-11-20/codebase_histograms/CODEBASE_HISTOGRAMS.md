# Codebase Structural Histograms (`original-2026-11-20`)

Empirical structural analysis across `lean/src/` (**175,187 reachable modules**, **1,061,375 declarations**, **818,704 theorems & lemmas**) paired with the interactive explorer in [histograms.html](histograms.html).

---

## 1. Corpus Totals & Proof Glue

| Metric | Count / Share |
|---|---:|
| Reachable Lean modules | 175,187 |
| Total declarations | 1,061,375 |
| Theorems & lemmas | 818,704 |
| Tactic proofs (`by ...`) | 651,659 |
| Term-mode proofs | 167,045 |
| Attribute-tagged declarations | 8,444 |
| Modules defining `@[simp]` | 1,972 |

### Proof Shape Distribution

| Proof Shape | Count | Share of Thm/Lem |
|---|---:|---:|
| Wrapper (first | exact …) (`wrapper_forwarding`) | 43,992 | 5.4% |
| 1-line mechanical (simp/rfl/rw/exact/…) (`oneliner_mech`) | 49,252 | 6.0% |
| 1-line solver (ring/omega/linarith/…) (`oneliner_solver`) | 965 | 0.1% |
| 1-line other tactic (`oneliner_other`) | 1,334 | 0.2% |
| Term-mode (no by) (`term_mode`) | 167,045 | 20.4% |
| Short tactic (2–5 lines) (`short_2_5`) | 199,163 | 24.3% |
| Medium tactic (6–20 lines) (`medium_6_20`) | 227,340 | 27.8% |
| Long tactic (21–50 lines) (`long_21_50`) | 93,090 | 11.4% |
| Deep tactic (51+ lines) (`deep_51_plus`) | 36,523 | 4.5% |

### Domain Breakdown

| Domain | Modules | Declarations |
|---|---:|---:|
| `Development` | 141,928 | 692,943 |
| `Formalism` | 18,254 | 240,099 |
| `GroundTheory` | 8,507 | 75,102 |
| `ReciprocityTheory` | 3,845 | 36,446 |
| `CompanionTheory` | 2,027 | 11,775 |
| `PositivityTheory` | 449 | 4,746 |
| `Lemmata` | 167 | 251 |
| `BuildAid` | 5 | 0 |
| `Supplements` | 3 | 4 |
| `(root)` | 2 | 9 |

### Top Attributes & Typeclasses

| Attribute | Count | Typeclass Binder | Signature Occurrences |
|---|---:|---|---:|
| `@[simp]` | 6,881 | `[Field]` | 181,880 |
| `@[reducible]` | 853 | `[CommRing]` | 128,499 |
| `@[reassoc]` | 577 | `[NumberField]` | 90,884 |
| `@[ext]` | 127 | `[Algebra]` | 83,210 |
| `@[instance_reducible]` | 103 | `[Fintype]` | 55,638 |
| `@[simps]` | 68 | `[AddCommGroup]` | 44,318 |
| `@[to_additive]` | 33 | `[Module]` | 42,135 |
| `@[fun_prop]` | 25 | `[Fact]` | 32,325 |
| `@[elab_as_elim]` | 13 | `[TopologicalSpace]` | 29,757 |
| `@[irreducible]` | 12 | `[Group]` | 25,095 |

