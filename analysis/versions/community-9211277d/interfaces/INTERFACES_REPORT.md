# Cross-Boundary Mathematical Interfaces & Contracts (`community-9211277d`)

This report translates the cross-boundary public mathematical interfaces of the proof across `src/` (**803 reachable modules**, **3 top-level theories**, **27 depth-2 sub-theories**), focusing on the mathematical specifications, theorem contracts, and bridges that link the major sub-theories (interactive browser in [interface_browser.html](interface_browser.html)).

## 1. Architectural Overview of Mathematical Boundaries

- **`(root)` Apex Entrypoints (`Main.lean`, `Statements.lean`):** Formulates the four target RH/GRH propositions over Mathlib alone (without `Lib/Speed.lean`) and exports the five unconditional theorems via `New/Main.lean` and `New/Reduction/OneSidedBound.lean`.
- **`New` as the Main Proof Architecture:** Organizes the proof into `Reduction`, `Derivatives`, `UpperBound`, `Spanning`, `Determinant`, `OneLift`, `Congruences`, and `Appendix`, decoupled cleanly across `Data`, `Rows`, `Columns`, `FitTwists`, and `SelmerHypotheses` contracts.
- **`Lib` as the Self-Contained Background Library:** Imports zero modules from `New/`, exporting verified mathematical interfaces for Galois representations (`AllRanks`), class field theory & Hecke avatars (`ArtinReciprocity`, `LocalGlobalCompatibility`), Shimura models (`Eigenspace`, `HolomorphicFamilies`), $p$-adic comparison & Kisin modules, Siegel–Weil & Rallis formulas (`SharpData`), and Weil representations (`WeilAction`, `KernelLaws`).

## 2. Sub-Theory Public APIs in Plain Mathematical English (28 Verified Interfaces)

Every interface below was resolved directly against the active reachable declaration index (`graph.sqlite`) for this codebase version.

### 2.1 `(root)`

#### [`Main.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean)
- **Role:** Apex Entrypoint | **Sub-Theory:** `(root)` | **Used by:** Top-level: None (apex) · Sub-theories: None
- **Plain-English Mathematical Summary:** The top-level proof driver of the formalization. Imports Statements.lean and New/Main.lean, and exports the five unconditional headline theorems: Mathlib's RiemannHypothesis, explicit zero-line localization for riemannZeta, half-plane nonvanishing for all Dirichlet L-functions on Re(s) > 1/2 (away from s = 1 for the trivial character), and GRH for arbitrary and primitive Dirichlet characters.
- **Key Exported Declarations:**
  - `theorem` [`riemannHypothesis`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean#L5) (L5): Proves Mathlib's canonical RiemannHypothesis statement via New.zeta_zeros_on_line New.grh.
  - `theorem` [`riemannZeta_eq_zero_re`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean#L8) (L8): Proves every nontrivial zero s != 1 of riemannZeta has Re(s) = 1/2.
  - `theorem` [`LFunction_ne_zero_of_half_lt_re`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean#L13) (L13): Proves L(chi, s) != 0 whenever Re(s) > 1/2 (except chi = 1, s = 1) directly via New.grh.
  - `theorem` [`LFunction_eq_zero_re`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean#L17) (L17): Proves every zero of any Dirichlet L-function in 0 < Re(s) < 1 has Re(s) = 1/2 via New.zeros_on_line New.grh.
  - `theorem` [`LFunction_eq_zero_re_of_isPrimitive`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean#L21) (L21): Specializes LFunction_eq_zero_re to primitive Dirichlet characters.

#### [`Statements.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean)
- **Role:** Apex Specification | **Sub-Theory:** `(root)` | **Used by:** Top-level: `New` · Sub-theories: `New/Reduction`
- **Plain-English Mathematical Summary:** Defines the four standalone target propositions imported by Main.lean over Mathlib alone (without Lib/Speed.lean or New/): explicit critical-line statements for riemannZeta and arbitrary/primitive Dirichlet L-functions, plus half-plane nonvanishing for Re(s) > 1/2.
- **Key Exported Declarations:**
  - `def` [`RiemannZetaZerosOnLine`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean#L3) (L3): Proposition that every zero of riemannZeta outside {-2, -4, ...} and {1} satisfies Re(s) = 1/2.
  - `def` [`DirichletLNonvanishingRightOfHalf`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean#L6) (L6): Proposition that L(chi, s) != 0 for all N >= 1, characters chi, and Re(s) > 1/2 (with chi != 1 or s != 1).
  - `def` [`DirichletLZerosOnLine`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean#L10) (L10): Proposition that all zeros of L(chi, s) with 0 < Re(s) < 1 satisfy Re(s) = 1/2.
  - `def` [`PrimitiveDirichletLZerosOnLine`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean#L14) (L14): Critical-line zero localization restricted to primitive Dirichlet characters.

### 2.2 `New`

#### [`New/Main.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Main.lean)
- **Role:** Analytic Reflection Bridge | **Sub-Theory:** `New` | **Used by:** Top-level: `(root)` · Sub-theories: `(root)`
- **Plain-English Mathematical Summary:** Final analytic step reducing critical-line zero localization for Dirichlet L-functions and riemannZeta to half-plane nonvanishing DirichletLNonvanishingRightOfHalf (New.grh) via nonvanishing of Gamma factors on Re(s) > 0 and functional-equation symmetry s <-> 1 - s.
- **Key Exported Declarations:**
  - `lemma` [`New.zeros_on_line`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Main.lean#L28) (L28): Deduces DirichletLZerosOnLine from DirichletLNonvanishingRightOfHalf via gammaFactor_eq_zero_or_LFunction_one_sub_eq_zero.
  - `lemma` [`New.zeta_zeros_on_line`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Main.lean#L47) (L47): Deduces RiemannZetaZerosOnLine from DirichletLNonvanishingRightOfHalf via completedRiemannZeta_one_sub.

#### [`New/UpperBound/Objects/Rows.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Rows.lean)
- **Role:** Target Spaces & Descent Pairs Interface | **Sub-Theory:** `New/UpperBound` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Spanning`, `New/Congruences`, `New/OneLift`
- **Plain-English Mathematical Summary:** Constructs the tower of hermitian spaces Y_j and W_j, the good-form projection D.e0 and D.targetForms, the target Harish-Chandra parameter, and the descent pairs (W_j, V_j) connecting UpperBound, Spanning, Determinant, and OneLift.
- **Key Exported Declarations:**
  - `def` [`New.Shape.besselIndexEquiv`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Rows.lean#L44) (L44): Canonical index bijection between Bessel coordinates and hyperbolic-plane strings.
  - `lemma` [`paramsCorrespond_descentPair`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Rows.lean#L810) (L810): Verifies Harish-Chandra parameter correspondence across each descent pair (W_j, V_j).
  - `lemma` [`fitsParams_descentPair`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Rows.lean#L841) (L841): Discharges FitsParams for the descent pairs used in OneLift and Congruences.

#### [`New/UpperBound/Size/ShortColumns.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Size/ShortColumns.lean)
- **Role:** Short Source Forms Contract | **Sub-Theory:** `New/UpperBound` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Derivatives`, `New/OneLift`, `New/Spanning`
- **Plain-English Mathematical Summary:** Defines prime-by-prime divisibility gauges and short ramified source forms, proving that short integral source forms span D.ramifiedSourceForms.
- **Key Exported Declarations:**
  - `lemma` [`span_isShort_ramifiedSourceForms_eq_top`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Size/ShortColumns.lean#L1002) (L1002): Proves that short forms span all ramified source forms on X_0.

#### [`New/Spanning/SecondMoment/SpanningTheorem.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/SecondMoment/SpanningTheorem.lean)
- **Role:** Second-Moment Spanning Interface | **Sub-Theory:** `New/Spanning` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Congruences`, `New/OneLift`, `New/Reduction`
- **Plain-English Mathematical Summary:** Converts the second-moment Hilbert-Schmidt near-isometry bound into the Filling.IsSpread property for D.goodPoincare over D.targetForms.
- **Key Exported Declarations:**
  - `theorem` [`sum_hilbertSchmidtNorm_scaledPoincare_sq_le`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/SecondMoment/SpanningTheorem.lean#L270) (L270): Bounds the average Hilbert-Schmidt discrepancy over the finite group chosenGL.
  - `theorem` [`isSpread_goodPoincare`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/SecondMoment/SpanningTheorem.lean#L339) (L339): Establishes the spreading property consumed by ShortAndEnough (Theorem B).

#### [`New/Determinant/Twist/FitTwists.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/FitTwists.lean)
- **Role:** Regular Twist Family Contract | **Sub-Theory:** `New/Determinant` | **Used by:** Top-level: None (apex) · Sub-theories: `New/OneLift`
- **Plain-English Mathematical Summary:** Defines the exact contract decoupling New/Congruences from New/Determinant: HasDenominatorsLe, HasSmallRatios, and IsRegularFamily for families of m-fold anticyclotomic twists indexed by PrimePadicIso.
- **Key Exported Declarations:**
  - `structure` [`HasDenominatorsLe`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/FitTwists.lean#L180) (L180): Bounds l-adic projection denominators of lifts along W_j -> V_j and rank-one character lifts.
  - `structure` [`HasSmallRatios`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/FitTwists.lean#L218) (L218): Ensures modulus coprimality to l and height <= x1 for inverse ratios of Hecke L-values.
  - `structure` [`IsRegularFamily`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/FitTwists.lean#L229) (L229): Combines HasSmallRatios and HasDenominatorsLe for every prime l and embedding iota.

#### [`New/Congruences/GaloisRepresentations/SelmerHypotheses.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/GaloisRepresentations/SelmerHypotheses.lean)
- **Role:** Selmer Setting & Conjugate Self-Dual Interface | **Sub-Theory:** `New/Congruences` | **Used by:** Top-level: None (apex) · Sub-theories: `New/OneLift`
- **Plain-English Mathematical Summary:** Defines IsLiftSetting and bad-place / l-adic avatar hypotheses linking modular forms with good labels to conjugate self-dual Galois representations in New/Congruences.
- **Key Exported Declarations:**
  - `lemma` [`IsLiftSetting.isChosen_chosenPlace`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/GaloisRepresentations/SelmerHypotheses.lean#L679) (L679): Exposes the chosen places and label idempotent projectors for lift settings.
  - `lemma` [`frequently_isSplit_notMem_places`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/GaloisRepresentations/SelmerHypotheses.lean#L727) (L727): Supplies infinitely many split places outside bad sets for Taylor-Wiles and Ribet arguments.

#### [`New/Reduction/Data/AdmissibleData.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/AdmissibleData.lean)
- **Role:** Core Parameter & Data Contract | **Sub-Theory:** `New/Reduction` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Congruences`
- **Plain-English Mathematical Summary:** Defines Parameters (q0, d, K = Q(sqrt(-d)), E = K(zeta_{q1}), Behrend-sparse IsSparse place sets) and the central Data P structure bundling scales x, x1, b, lift count m, rank r, a-places, b-places, weights, and level primes p0, p1, N.
- **Key Exported Declarations:**
  - `def` [`New.Parameters.constantBound`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/AdmissibleData.lean#L50) (L50): Packs all constants depending only on q0 and d (including chowlaSelbergConst d and vacuumBoundConst).
  - `def` [`New.Parameters.IsSparse`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/AdmissibleData.lean#L58) (L58): Behrend-style 3-term-free sparsity condition on infinite b-places modulo q1.
  - `structure` [`New.Data`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/AdmissibleData.lean#L77) (L77): Master parameter bundle passed across Reduction, Derivatives, UpperBound, Spanning, Determinant, OneLift, and Congruences.

#### [`New/UpperBound/Objects/Columns.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Columns.lean)
- **Role:** Source Chains & Composite Lift Interface | **Sub-Theory:** `New/UpperBound` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Determinant`
- **Plain-English Mathematical Summary:** Defines the chain of definite hermitian spaces X_0 -> ... -> X_m, restriction to Y_m, glued Schrödinger data at level N, IsChainDatum / IsWeakChainDatum, and D.compositeLift.
- **Key Exported Declarations:**
  - `def` [`restrictToYOfEq`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Columns.lean#L974) (L974): Restricts algebraic modular forms from X_m to the codimension-one block Y_m.
  - `def` [`compositeLift`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Columns.lean#L992) (L992): Evaluates a chain datum into a composite theta lift on target-level spaces.
  - `structure` [`IsWeakChainDatum`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Objects/Columns.lean#L1001) (L1001): Integrality and support contract for chain data produced by the seesaw identity.

#### [`New/Congruences/FitTwistsExist.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FitTwistsExist.lean)
- **Role:** Regular Twists Construction Bridge | **Sub-Theory:** `New/Congruences` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Determinant`
- **Plain-English Mathematical Summary:** Unites Ribet's first-order denominator bound (DenominatorBound) with the Selmer twisting theorem (TwistingTheorem) and Lib.GaloisRep to construct regular families of m-fold twists (exists_isRegularFamily).
- **Key Exported Declarations:**
  - `lemma` [`New.Selmer.exists_mFoldTwist_hasDenominatorsLe`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FitTwistsExist.lean#L475) (L475): Produces m-fold twists satisfying the l-adic clearing denominator bound.
  - `lemma` [`New.exists_isRegularFamily`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FitTwistsExist.lean#L517) (L517): Discharges IsRegularFamily for every admissible datum D.

#### [`New/Determinant/Twist/LongForms.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/LongForms.lean)
- **Role:** Theorem C Bottleneck | **Sub-Theory:** `New/Determinant` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Reduction`
- **Plain-English Mathematical Summary:** Proves Theorem C (integral_forms_long): any family of n >= (1 - 4/b^2) targetDim target forms has covolume plus twice its index bounded below by targetDim * (mainAmount - f a log^4 b - 2 b), using regular twist families and auxiliary forms.
- **Key Exported Declarations:**
  - `structure` [`IsAuxiliaryForm`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/LongForms.lean#L43) (L43): Target forms whose m-fold twisted lifts remain integral away from N(Q) with controlled archimedean norm.
  - `theorem` [`exists_hasSmallRatios_heightLe_liftDeterminant_div`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/LongForms.lean#L139) (L139): Supplies a regular twist family bounding single-lift Gram determinant heights Z_j(1)/Z_j(xi^j).
  - `theorem` [`integral_forms_long`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/LongForms.lean#L214) (L214): Theorem C lower bound on covolume + 2 * index for nearly spanning target families.

#### [`New/OneLift/LiftVolumeHeight.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/OneLift/LiftVolumeHeight.lean)
- **Role:** Single-Lift Determinant Height Interface | **Sub-Theory:** `New/OneLift` | **Used by:** Top-level: None (apex) · Sub-theories: `New/Determinant`
- **Plain-English Mathematical Summary:** Combines comparison operators, false-lift period vanishing, and rank-one theta-lift Hecke value heights to prove heightLe_liftDeterminant_ratio for Z_j(1)/Z_j(xi^j).
- **Key Exported Declarations:**
  - `lemma` [`heightLe_liftDeterminant_ratio`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/OneLift/LiftVolumeHeight.lean#L729) (L729): Bounds the height of single-lift Gram determinant ratios Z_j(1)/Z_j(theta^j) for regular twists.

#### [`New/Reduction/OneSidedBound.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean)
- **Role:** Half-Plane GRH Apex | **Sub-Theory:** `New/Reduction` | **Used by:** Top-level: None (apex) · Sub-theories: `New`
- **Plain-English Mathematical Summary:** Combines the main inequality (star_inequality) at scale x with the Prime Number Theorem remainder bound at the larger cutoff x1 to prove the one-sided bound R_{q0}(y) <= y^{-1/2 + eps}, and discharges New.grh by choosing a prime d avoiding putative zeros of quadratic twists.
- **Key Exported Declarations:**
  - `lemma` [`Data.primeRemainder_le`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean#L33) (L33): Converts star_inequality into an upper bound on R_{q0}(x) plus PNT remainder errors at x1.
  - `theorem` [`eventually_primeRemainder_le_rpow`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean#L200) (L200): Establishes R_{q0}(y) <= y^{-1/2 + eps} for all sufficiently large real y.
  - `theorem` [`grh`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean#L239) (L239): Unconditionally proves DirichletLNonvanishingRightOfHalf.

#### [`New/Reduction/Lattices/TwistedLattice.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Lattices/TwistedLattice.lean)
- **Role:** Twisted Lattice Product Formula | **Sub-Theory:** `New/Reduction` | **Used by:** Top-level: None (apex) · Sub-theories: None
- **Plain-English Mathematical Summary:** Formalizes TwistedLattice (maps from a finite-dimensional space to inner product spaces indexed by twists) together with IndexLe and CovolumeLe, proving the global product-formula inequality covolume_add_index_nonneg.
- **Key Exported Declarations:**
  - `theorem` [`covolume_add_index_nonneg`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Lattices/TwistedLattice.lean#L477) (L477): Proves 0 <= V + 2*delta + 2*c when covolume <= V, index <= delta, and twist determinant ratios have height <= c.

#### [`New/Reduction/MainInequality.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/MainInequality.lean)
- **Role:** Main Cancellation Bottleneck | **Sub-Theory:** `New/Reduction` | **Used by:** Top-level: None (apex) · Sub-theories: None
- **Plain-English Mathematical Summary:** Executes the central cancellation between upper and lower bounds: combines Theorems A and B (ShortAndEnough) with Theorem C (integral_forms_long) to cancel D.mainAmount and prove D.m * D.totalRemainder <= D.f * D.a * D.logB^5.
- **Key Exported Declarations:**
  - `theorem` [`star_inequality`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/MainInequality.lean#L87) (L87): Proves D.m * D.totalRemainder <= D.f * D.a * D.logB^5 for any admissible Data P.

#### [`New/Reduction/ShortAndEnough.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/ShortAndEnough.lean)
- **Role:** Theorems A & B Interface | **Sub-Theory:** `New/Reduction` | **Used by:** Top-level: None (apex) · Sub-theories: None
- **Plain-English Mathematical Summary:** Assembles the upper-bound side of the main inequality: Theorem A proves that normalized Poincare translates produce short integral target lifts with small lattice index, and Theorem B proves that O(dim * log b / dim_src) translates span at least (1 - 4/b^2) of the target space.
- **Key Exported Declarations:**
  - `theorem` [`indexLe_normalizedPoincare`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/ShortAndEnough.lean#L373) (L373): Theorem A(b): bounds the logarithmic index of normalized Poincare images in D.targetLattice.
  - `theorem` [`enough_forms`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/ShortAndEnough.lean#L448) (L448): Theorem B: selects a small set of chosenGL translates spanning almost all of D.targetForms.

### 2.3 `Lib`

#### [`Lib/General/NumberTheory/PadicLimitsValuation.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/General/NumberTheory/PadicLimitsValuation.lean)
- **Role:** p-adic Valuation & Algebraicity Interface | **Sub-Theory:** `Lib/General` | **Used by:** Top-level: `New` · Sub-theories: `Lib/CM`, `Lib/PadicHodge`, `New/Congruences`, `Lib/GaloisRep`
- **Plain-English Mathematical Summary:** High-fan-in utility interface relating p-adic valuations, normLength of finite modules, roots of unity as p-adic limits, and primitive roots.
- **Key Exported Declarations:**
  - `lemma` [`normLength_addVal`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/General/NumberTheory/PadicLimitsValuation.lean#L323) (L323): Computes module length via additive p-adic valuation.
  - `lemma` [`eventually_exists_isPrimitiveRoot`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/General/NumberTheory/PadicLimitsValuation.lean#L353) (L353): Constructs primitive roots of unity at sufficiently large primes.

#### [`Lib/Shimura/Uniformisation/HolomorphicFamilies.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Uniformisation/HolomorphicFamilies.lean)
- **Role:** Complex Shimura Uniformisation Interface | **Sub-Theory:** `Lib/Shimura` | **Used by:** Top-level: `New` · Sub-theories: `Lib/General`, `Lib/LocalGL`, `Lib/Weil`, `New/Appendix`
- **Plain-English Mathematical Summary:** High-fan-in interface defining holomorphic families of complex abelian-variety points, jets, uniformisations, and theta coordinates on ball charts.
- **Key Exported Declarations:**
  - `lemma` [`exists_theta_of_isSection`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Uniformisation/HolomorphicFamilies.lean#L891) (L891): Constructs theta-function representatives for sections along holomorphic families.
  - `lemma` [`riemannForm_eq_of_isFrame`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Uniformisation/HolomorphicFamilies.lean#L947) (L947): Identifies the Riemann form from adelic frame data.

#### [`Lib/Base.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Base.lean)
- **Role:** Core Hermitian Matrix Helper | **Sub-Theory:** `Lib` | **Used by:** Top-level: `New` · Sub-theories: `Lib/General`, `Lib/Adelic`, `Lib/Analytic`, `Lib/ClassField`
- **Plain-English Mathematical Summary:** Root library file imported across Lib/ and New/ (except Lib/Speed.lean), propagating speed settings and providing the Hermitian dot-product adjoint lemma star_mulVec_dotProduct.
- **Key Exported Declarations:**
  - `lemma` [`star_mulVec_dotProduct`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Base.lean#L14) (L14): Identifies star (B *ᵥ x) ⬝ᵥ y = star x ⬝ᵥ Bᴴ *ᵥ y over any StarRing.

#### [`Lib/Adelic/Unitary/Defs.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Adelic/Unitary/Defs.lean)
- **Role:** Adelic Unitary Group & Hermitian Space Contract | **Sub-Theory:** `Lib/Adelic` | **Used by:** Top-level: `New` · Sub-theories: `Lib/Cohomology`, `Lib/GLn`, `Lib/GaloisRep`, `Lib/General`
- **Plain-English Mathematical Summary:** Core foundational definitions for hermitian spaces over CM fields, adelic unitary groups G(A), standard definite spaces, integral lattices, and level subgroups.
- **Key Exported Declarations:** Pure import barrel / namespace directive.

#### [`Lib/ClassField/Avatar/HeckeBaseChange.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/HeckeBaseChange.lean)
- **Role:** Hecke Avatar & Base Change Interface | **Sub-Theory:** `Lib/ClassField` | **Used by:** Top-level: `New` · Sub-theories: `Lib/GaloisRep`, `Lib/SiegelWeil`, `Lib/Weil`, `New/UpperBound`
- **Plain-English Mathematical Summary:** Packages base change of U(1) and algebraic Hecke characters between CM fields, preserving L-functions, Hodge-Tate jumps, and killing polynomials on l-adic avatars.
- **Key Exported Declarations:**
  - `lemma` [`hasJumpsAt_scalarRep_cyclotomicCharIn_pow_mul`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/HeckeBaseChange.lean#L321) (L321): Computes Hodge-Tate jumps of twisted scalar avatar representations.
  - `lemma` [`Variety.exists_twist_algHeckeChar`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/HeckeBaseChange.lean#L392) (L392): Constructs algebraic Hecke twists realizing prescribed local character behavior.

#### [`Lib/Weil/DualPair/KernelLaws.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/DualPair/KernelLaws.lean)
- **Role:** Theta Kernel Formal Laws Interface | **Sub-Theory:** `Lib/Weil` | **Used by:** Top-level: `New` · Sub-theories: `Lib/ClassField`, `Lib/General`, `New/UpperBound`
- **Plain-English Mathematical Summary:** Exports formal equivariance, factorization, reindexing, and seesaw laws for unitary dual-pair theta kernels modulo ideals.
- **Key Exported Declarations:**
  - `lemma` [`modKernel_factor`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/DualPair/KernelLaws.lean#L480) (L480): Factors modular theta kernels across orthogonal decompositions.
  - `lemma` [`Rows.modKernelStdSpace_block`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/DualPair/KernelLaws.lean#L539) (L539): Block decomposition law for standard-space theta kernels.

#### [`Lib/SiegelWeil/RallisInner/SharpData.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/SiegelWeil/RallisInner/SharpData.lean)
- **Role:** Rallis Inner Product Interface | **Sub-Theory:** `Lib/SiegelWeil` | **Used by:** Top-level: `New` · Sub-theories: `Lib/GaloisRep`, `New/Determinant`
- **Plain-English Mathematical Summary:** Proves the doubling Rallis inner product formula for sharp data and expresses unramified vacuum sums as critical Hecke L-values divided by Euler factors.
- **Key Exported Declarations:**
  - `theorem` [`vacuumSum_eq_L_div_eulerProd`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/SiegelWeil/RallisInner/SharpData.lean#L946) (L946): Evaluates unramified sharp-data theta sums as ratios of critical Hecke L-values.

#### [`Lib/Weil/DualPair/WeilAction.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/DualPair/WeilAction.lean)
- **Role:** Dual-Pair Weil Action Interface | **Sub-Theory:** `Lib/Weil` | **Used by:** Top-level: `New` · Sub-theories: `New/UpperBound`
- **Plain-English Mathematical Summary:** Defines the Weil representation action of unitary dual pairs (U(S), U(T)) on Schwartz-Fock data, translations, real-place actions, and global theta lifts IsThetaLift.
- **Key Exported Declarations:**
  - `abbrev` [`twistedPairWeil`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/DualPair/WeilAction.lean#L768) (L768): Twisted dual-pair Weil action incorporating auxiliary Hecke characters.
  - `def` [`IsThetaLift`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/DualPair/WeilAction.lean#L801) (L801): Predicate specifying a global theta lift between unitary automorphic forms.

#### [`Lib/ClassField/Avatar/LocalGlobalCompatibility.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/LocalGlobalCompatibility.lean)
- **Role:** Avatar Local-Global Compatibility | **Sub-Theory:** `Lib/ClassField` | **Used by:** Top-level: None (apex) · Sub-theories: `Lib/GaloisRep`
- **Plain-English Mathematical Summary:** Proves local-global compatibility for l-adic avatars of algebraic Hecke characters at split places and over stably unramified CM fields (HasPrimitiveRoot5040).
- **Key Exported Declarations:**
  - `lemma` [`New.GaloisRep.avatar_baseChange`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/LocalGlobalCompatibility.lean#L44) (L44): Relates avatars under CM base change.
  - `lemma` [`New.GaloisRep.avatarCompatAt_of_hasPrimitiveRoot5040`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/LocalGlobalCompatibility.lean#L191) (L191): Establishes full local-global compatibility for rank-one avatars over stably unramified CM fields.

#### [`Lib/Shimura/Eigenspace.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Eigenspace.lean)
- **Role:** Shimura Eigenquotient Galois Interface | **Sub-Theory:** `Lib/Shimura` | **Used by:** Top-level: None (apex) · Sub-theories: `Lib/GaloisRep`
- **Plain-English Mathematical Summary:** Extracts l-adic Galois representations from cohomology eigenquotients of GU(1, n-1) Shimura towers and establishes the Eichler-Shimura killing-polynomial relation.
- **Key Exported Declarations:**
  - `lemma` [`New.Variety.Model.isKilledBy_heckePoly_of_isEigenQuotient`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Eigenspace.lean#L615) (L615): Shows the Hecke polynomial kills Frobenius on the eigenquotient cohomology.
  - `lemma` [`New.Variety.Model.exists_galois_rep`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Eigenspace.lean#L689) (L689): Constructs the attached Galois representation from a Shimura tower eigenquotient.

#### [`Lib/GaloisRep/Main/AllRanks.lean`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/AllRanks.lean)
- **Role:** Galois Representations Interface | **Sub-Theory:** `Lib/GaloisRep` | **Used by:** Top-level: None (apex) · Sub-theories: None
- **Plain-English Mathematical Summary:** Constructs attached l-adic Galois representations (matching Hecke polynomials on mostFrobenii, unramified/crystalline with Hodge-Tate jumps) for algebraic eigenforms on definite unitary groups of any positive rank.
- **Key Exported Declarations:**
  - `lemma` [`Isotypic.attached_galRep_of_exists`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/AllRanks.lean#L774) (L774): Attaches a Galois representation to any nonzero isotypic eigenform space.
  - `lemma` [`Isotypic.attached_galRep`](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/AllRanks.lean#L792) (L792): Unconditional attached Galois representation interface for definite unitary eigenforms.

