# Formalized Proof Blueprint: Riemann Hypothesis & Generalized Riemann Hypothesis (`community-9211277d`)

This blueprint distills the Lean proof DAG (**803 reachable modules**, **477,124 lines**, **1,733 internal dependency edges**) into **51 mathematical milestones** across **5 architectural stages** (Stages 0–4) connected by **68 dependency links** (interactive DAG in [blueprint.html](blueprint.html)).

> **Direction Convention:** Stage 0 sits at the apex (`Main.lean`); arrows `A → B` mean milestone `A` depends directly on prerequisite `B`.

---

## Executive Overview: The Proof Strategy in Plain English

At the highest level, the proof establishes **both** the classical **Riemann Hypothesis (RH)** and the **Generalized Riemann Hypothesis (GRH)** for all Dirichlet $L$-functions by reducing critical-line zero localization ($\operatorname{Re}(s) = \tfrac{1}{2}$) to a single universal statement: **no Dirichlet $L$-function $L(\chi, s)$ vanishes anywhere in the open right half-plane $\operatorname{Re}(s) > \tfrac{1}{2}$** (away from the simple pole of $\zeta(s)$ at $s = 1$).

Once this right half-plane nonvanishing (`New.grh`) holds, `New/Main.lean` uses Gamma-factor nonvanishing for $\operatorname{Re}(s) > 0$ and the functional equations across $s \mapsto 1 - s$ to mirror every zero with $\operatorname{Re}(s) < \tfrac{1}{2}$ into $\operatorname{Re}(1 - s) > \tfrac{1}{2}$, forcing all critical-strip zeros onto $\operatorname{Re}(s) = \tfrac{1}{2}$.

To prove `New.grh` in the `src/New/` + `src/Lib/` readable architecture, the formalization executes a **height/covolume comparison of twisted lattices of unitary modular forms**:
1. **One-Sided Prime Remainder Criterion (`New/Reduction`):** For a modulus $q_0$ divisible by $18480$ and a prime $d \equiv q_0/2 - 1 \pmod{q_0}$ chosen via Pólya–Vinogradov zero-density bounds (`Lib/Analytic/QuadraticTwist`) so quadratic twists avoid any putative zero, Landau's one-sided criterion (`Criterion.lean`) turns a one-sided bound $R_{q_0}(y) \le y^{-1/2 + \varepsilon}$ on the prime remainder $R_{q_0}(y) = \sum_{n \le y} \Lambda(n)(1 - \chi_K(n))(1/n - 1/y) - \log y / \varphi(q_0) - c_{q_0}$ into zero-freeness on $\operatorname{Re}(s) > \tfrac{1}{2}$.
2. **Main Inequality & Cancellation (`star_inequality`):** At large scales $x, x_1, b$ (`eventually_exists_data`) over a CM field $E = \mathbb{Q}(\sqrt{-d})(\zeta_{q_1})$ with Behrend-sparse $b$-places, `MainInequality.lean` cancels `D.mainAmount` between an upper bound on the covolume and index of normalized Poincaré lifts (**Theorems A & B** in `ShortAndEnough.lean`) and a lower bound (**Theorem C**, `integral_forms_long` in `New/Determinant/Twist/LongForms.lean`), leaving $m \cdot \mathrm{rem} \le f a \log^5 b$, which PNT at $x_1$ (`x₁ ≥ x^{10⁶}`) turns into $R_{q_0}(y) \le y^{-1/2+\varepsilon}$.
3. **Upper Bound via Derivatives, Seesaw & Second Moment (`New/Derivatives`, `New/UpperBound`, `New/Spanning`):** `SeesawIdentity.lean` unfolds `lowerChain` on Poincaré maps into a composite definite lift, whose $p$-adic divisibility (`LocalDivisibility.lean`, `ElementaryDivisorTheorem.lean`) and archimedean norm (`ArchimedeanSize.lean`, `Sharpness/BoundAttained.lean`) match the prime sums, while `SpanningTheorem.lean` proves via second-moment unfolding and Bessel estimates that few `chosenGL` translates span almost all target forms.
4. **Lower Bound via Determinant Chains, One-Lift Comparisons & Congruences (`New/Determinant`, `New/OneLift`, `New/Congruences`):** The twisted-lattice product formula (`TwistedLattice.lean`), the exchange identity (`TheoremForPartners.lean`), and auxiliary spanning forms reduce `integral_forms_long` to bounding single-lift determinant heights (`LiftVolumeHeight.lean`) and constructing regular families of $m$-fold anticyclotomic twists (`FitTwistsExist.lean`) via Ribet's first-order method (`DenominatorBound.lean`), Selmer twisting (`TwistingTheorem.lean`), and Kisin-module crystalline lifting (`CupOrthogonalityBounds.lean`).
5. **Self-Contained Background Theories (`src/Lib/`):** All supporting theories—Galois representations of definite unitary eigenforms (`Lib/GaloisRep`), PEL Shimura towers and Eichler–Shimura (`Lib/Shimura`), étale/Hodge Woods Hole (`Lib/Cohomology`), $p$-adic comparison and Kisin frames (`Lib/PadicComparison`, `Lib/PadicHodge`), class field theory and Greenberg–Wiles counting (`Lib/ClassField`), odd-part $\text{Ш}$ bounds (`Lib/Cyclotomic`), Siegel–Weil and Rallis formulas (`Lib/SiegelWeil`), Weil models (`Lib/Weil`), discrete series (`Lib/DiscreteSeries`), and Chowla–Selberg (`Lib/CM`)—are proved in `src/Lib/` with zero imports from `src/New/`.

---

## Stage 0: Final Theorems (2 milestones)

Standalone target statements and top-level proved theorems for the Riemann Hypothesis, Dirichlet L-function half-plane nonvanishing, and Generalized Riemann Hypothesis.

### Main Theorems (RH, Half-Plane & GRH) (`main_export`)

- **Statement:** Unconditionally establishes the Riemann Hypothesis for ζ(s), nonvanishing of every Dirichlet L-function L(χ, s) on the open half-plane Re(s) > 1/2 (away from s = 1 when χ = 1), and the Generalized Riemann Hypothesis for both arbitrary and primitive Dirichlet characters.
- **Assumptions:** None — all five headline theorems are completely unconditional.
- **Proof strategy:** Directly instantiates the standalone target statements using `New.grh` and the Stage 1 functional-equation reflection lemmas `New.zeros_on_line` and `New.zeta_zeros_on_line`.
- **Lean anchor:** `riemannHypothesis` in [Main.lean#L5](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean#L5) · Dominates **803** modules
- **Depends on:** `Standalone Target Theorem Statements`, `Functional-Equation Reflection (`s ↔ 1 − s`)`, `One-Sided Prime Remainder Bound & Half-Plane GRH (`New.grh`)`
- **Notes:** Root module (dist=0, height=53). Exports all 5 headline theorems via New.Main and New.Reduction.OneSidedBound.

### Standalone Target Theorem Statements (`statements_spec`)

- **Statement:** Formulates the four target propositions — critical-line zeros of ζ(s), half-plane nonvanishing of L(χ, s) on Re(s) > 1/2, and GRH for arbitrary and primitive characters — importing only Mathlib.
- **Assumptions:** None — pure definitions stating the mathematical claims without any project-internal machinery.
- **Proof strategy:** Contains no proof; isolates the exact statements from the proof machinery and global settings (`Lib/Speed.lean`).
- **Lean anchor:** `RiemannZetaZerosOnLine` in [Statements.lean#L3](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean#L3)
- **Depends on:** None (foundation)
- **Notes:** Pure specification leaf importing only Mathlib (does not import Lib/Speed.lean).

---

## Stage 1: Functional-Equation & One-Sided Bound Reductions (2 milestones)

Analytic bridges reducing critical-line zero localization for ζ(s) and arbitrary/primitive Dirichlet L-functions to half-plane nonvanishing Re(s) > 1/2 (`New.grh`), proved from the one-sided prime remainder bound `R_{q₀}(y) ≤ y^{-1/2+ε}`.

### Functional-Equation Reflection (`s ↔ 1 − s`) (`new_main_reflection`)

- **Statement:** Deduces `DirichletLZerosOnLine` and `RiemannZetaZerosOnLine` from `DirichletLNonvanishingRightOfHalf`.
- **Assumptions:** Takes `h : DirichletLNonvanishingRightOfHalf` as a hypothesis.
- **Proof strategy:** Uses nonvanishing of the Gamma factor `χ.gammaFactor s` (and `Gammaℝ s`) on `Re(s) > 0` to reflect any zero with `Re(s) < 1/2` across `s ↦ 1 − s` into `Re(1 − s) > 1/2`, contradicting `h`.
- **Lean anchor:** `New.zeros_on_line` in [New/Main.lean#L28](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Main.lean#L28) · Dominates **802** modules
- **Depends on:** `Standalone Target Theorem Statements`, `One-Sided Prime Remainder Bound & Half-Plane GRH (`New.grh`)`
- **Notes:** Entry module inside New/ (dist=1, height=52, dominates 802 modules).

### One-Sided Prime Remainder Bound & Half-Plane GRH (`New.grh`) (`one_sided_bound`)

- **Statement:** Proves `eventually_primeRemainder_le_rpow` (`R_{q₀}(y) ≤ y^{-1/2+ε}` for large `y`) and deduces `New.grh : DirichletLNonvanishingRightOfHalf`.
- **Assumptions:** Unconditional — instantiates `Parameters` for `q₀ = 18480 * q` and an auxiliary prime `d ≡ q₀/2 - 1 (mod q₀)` chosen so quadratic twists avoid any putative zero `ρ`.
- **Proof strategy:** Divides `star_inequality` (`m · rem ≤ f a log⁵ b`) by `m a #Φ_b`, controls the `x₁`-cut-off terms by PNT (`x⁻²`), interpolates from integers to real `y`, and invokes Landau's one-sided criterion.
- **Lean anchor:** `grh` in [New/Reduction/OneSidedBound.lean#L239](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean#L239) · Dominates **801** modules
- **Depends on:** `The Main Inequality (`star_inequality`)`, `Existence of Admissible Data at Large Scales`, `One-Sided Landau Criterion for Zero-Free Half-Plane`, `Prime Number Theorem Bound for `R_q` at Cut-Off `x₁``
- **Notes:** Dominates 801 of 803 modules (dist=2, height=51). Ends with theorem grh.

---

## Stage 2: Main Inequality & Primary Proof Bridges (6 milestones)

The core cancellation inequality (`star_inequality`) balancing Theorems A & B (`short_and_enough`) against Theorem C (`integral_forms_long`), together with regular families of m-fold twists, second-moment spanning, and existence of admissible data.

### The Main Inequality (`star_inequality`) (`main_inequality`)

Proves `D.m * D.totalRemainder ≤ D.f * D.a * D.logB ^ 5` by bounding `(V + 2δ) / dim` from above via Theorems A & B (`short_and_enough`) and from below via Theorem C (`integral_forms_long`), cancelling `D.mainAmount`.

- **Mathematical form:** `mainAmount ≤ (V + 2δ)/dim ≤ mainAmount − (n/dim) m·rem + err ⇒ m·rem ≤ f a log⁵ b`
- **Lean anchor:** `star_inequality` in [New/Reduction/MainInequality.lean#L87](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/MainInequality.lean#L87) · Dominates **606** modules
- **Depends on:** `Theorems A & B: Short Forms & Enough Translates`, `Theorem C: Integral Forms Are Long (`integral_forms_long`)`
- **Notes:** Central bottleneck of the entire proof (dist=3, height=50, dominates 606 modules).

### Theorems A & B: Short Forms & Enough Translates (`short_and_enough`)

Proves Theorem A (`span_short_integralRamified_eq_top` and `indexLe_normalizedPoincare`: short lifts and index bound `≤ #t · dim src · 2 f a log³ b`) and Theorem B (`enough_forms`: few `chosenGL` translates span `(1 - 4/b²) dim` of target forms).

- **Mathematical form:** `Theorem A (size & index of Θ ∘ 𝔭) ∧ Theorem B (spanning ≥ (1 - 4/b²) d_T)`
- **Lean anchor:** `enough_forms` in [New/Reduction/ShortAndEnough.lean#L448](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/ShortAndEnough.lean#L448) · Dominates **36** modules
- **Depends on:** `Iterated Seesaw Identity (`seesaw_identity`)`, `Prime-by-Prime Divisibility of the Composite Lift`, `Archimedean Size of the Composite Lift`, `Second-Moment Spanning Theorem (`isSpread_goodPoincare`)`
- **Notes:** Upper half of the main inequality (dist=4, height=47, dominates 36 modules).

### Theorem C: Integral Forms Are Long (`integral_forms_long`) (`long_forms_thm_c`)

Proves the lower bound `D.m * D.k * D.directionAmount ≤ (V + 2δ)/d + f a log⁴ b + 2 b` for any `n ≥ (1 - 4/b²) d` target forms using `TwistedLattice.covolume_add_index_nonneg`, auxiliary forms, and regular families of `m`-fold twists.

- **Mathematical form:** `CovolumeLe(V) ∧ IndexLe(δ) ⇒ mainAmount ≤ (V + 2δ)/d + f a log⁴ b + 2 b`
- **Lean anchor:** `integral_forms_long` in [New/Determinant/Twist/LongForms.lean#L214](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/LongForms.lean#L214) · Dominates **228** modules
- **Depends on:** `Existence of Regular Families of `m`-Fold Twists`, `Spanning Auxiliary Forms on the Two-Grid Last Path`, `Single-Lift Determinant Height Bound (`Z_j(1)/Z_j(ξ^j)`)`, `Twisted Lattice Product Formula (`covolume_add_index_nonneg`)`
- **Notes:** Lower-bound apex bottleneck (dist=4, height=49, dominates 228 modules).

### Existence of Regular Families of `m`-Fold Twists (`fit_twists_exist`)

Proves `New.exists_isRegularFamily`: every admissible datum admits a family `θ : PrimePadicIso → D.MFoldTwist` with small Hecke `L`-value ratios (`HasSmallRatios`) and clearing denominator bounds (`HasDenominatorsLe`) at all primes `ℓ`.

- **Mathematical form:** `∀ D : Data P, ∃ θ, D.IsRegularFamily θ`
- **Lean anchor:** `New.exists_isRegularFamily` in [New/Congruences/FitTwistsExist.lean#L517](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FitTwistsExist.lean#L517) · Dominates **74** modules
- **Depends on:** `First-Order Ribet Method & Clearing Denominator Bound`, `Anticyclotomic Twisting Theorem for Selmer Groups`, `Attached Galois Representations in Every Positive Rank`
- **Notes:** Connects congruences, Ribet's method, and Selmer bounds into Theorem C (dist=5, height=48, dominates 74 modules).

### Second-Moment Spanning Theorem (`isSpread_goodPoincare`) (`spanning_theorem`)

Proves that translates of `D.goodPoincare` spread uniformly across `D.targetForms` by showing the second-moment Petersson operator norm is close to an isometry.

- **Mathematical form:** `isSpread_goodPoincare : Filling.IsSpread (D.goodPoincare) (D.targetDim)`
- **Lean anchor:** `isSpread_goodPoincare` in [New/Spanning/SecondMoment/SpanningTheorem.lean#L339](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/SecondMoment/SpanningTheorem.lean#L339) · Dominates **58** modules
- **Depends on:** `Second-Moment Unfolding & Near-Isometry (`Moments`)`, `Simple Trace Formula Comparison Across Real Signatures`
- **Notes:** Top bottleneck of New/Spanning (dist=5, height=42, dominates 58 modules).

### Existence of Admissible Data at Large Scales (`eventually_exists_data`)

Constructs admissible data `D : Data P` for all sufficiently large `x`, choosing `x₁ = ⌊exp(x^{ε/6})⌋`, `log b ∈ [x^ε, x^ε + 1]`, Behrend-sparse `b`-places, CM field `E = K(ζ_{q₁})`, and primes `p₀, p₁, N`.

- **Mathematical form:** `0 < ε < 1/100 ⇒ ∀ᶠ x, ∃ D : Data P, D.x = x ∧ ...`
- **Lean anchor:** `eventually_exists_data` in [New/Reduction/Data/Existence.lean#L898](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/Existence.lean#L898)
- **Depends on:** `Sharpness of the Theta-Derivative Valuation Bound`, `Chowla–Selberg Formula for CM Curves`
- **Notes:** Provides concrete scales and Behrend-sparse place sets feeding OneSidedBound.

---

## Stage 3: Major `New/` Proof Pillars (22 milestones)

The eight proof engines of `src/New/`: Landau zero-free criterion and PNT cut-off, twisted-lattice product formula, theta derivatives & sharpness, composite-lift seesaw & divisibility, elementary divisors, second-moment unfolding & Bessel frames, determinant exchange & auxiliary forms, single-lift comparisons, and congruence/Selmer/Kisin bounds.

### One-Sided Landau Criterion for Zero-Free Half-Plane (`criterion_zero_free`)

Proves that if `primeRemainder d q₀ y ≤ y^{-1/2+ε}` for all large `y` (for every `ε > 0`), then no character induced by `q₀` (or twisted by `χ_K`) has a zero of `L(χ, s)` in `Re(s) > 1/2`.

- **Mathematical form:** `(∀ ε > 0, eventually R_{q₀}(y) ≤ y^{-1/2+ε}) ⇒ L(χ, s) ≠ 0 (Re s > 1/2)`
- **Lean anchor:** `New.LFunction_ne_zero_of_primeRemainder_le` in [New/Reduction/Zeros/Criterion.lean#L37](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Zeros/Criterion.lean#L37) · Dominates **5** modules
- **Depends on:** None (foundation)
- **Notes:** Finite-level Landau nonnegativity bridge (dist=3, height=9).

### Prime Number Theorem Bound for `R_q` at Cut-Off `x₁` (`pnt_remainder`)

Applies the zero-free region and Tauberian theorem in `Lib/Analytic/PrimeNumberTheorem` to prove `|R_q(y)| ≤ 1 / (log y)^B` for any `B`.

- **Mathematical form:** `∀ B : ℕ, eventually |primeRemainder d q y| ≤ (log y)^{-B}`
- **Lean anchor:** `eventually_abs_primeRemainder_le` in [New/Reduction/Zeros/PrimeNumberTheorem.lean#L217](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Zeros/PrimeNumberTheorem.lean#L217) · Dominates **2** modules
- **Depends on:** None (foundation)
- **Notes:** Controls the `x₁` remainder terms in OneSidedBound.

### Twisted Lattice Product Formula (`covolume_add_index_nonneg`) (`twisted_lattice_product`)

Proves the global product-formula inequality `0 ≤ V + 2δ + 2c` for a twisted lattice: Gram determinant covolume plus twice the `ℓ`-adic clearing-matrix index plus twist height is non-negative.

- **Mathematical form:** `CovolumeLe V ∧ IndexLe δ ∧ HeightLe c (det ratios) ⇒ 0 ≤ V + 2δ + 2c`
- **Lean anchor:** `covolume_add_index_nonneg` in [New/Reduction/Lattices/TwistedLattice.lean#L477](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Lattices/TwistedLattice.lean#L477)
- **Depends on:** None (foundation)
- **Notes:** Abstract Bost/Laurent-style product formula driving Theorem C.

### Iterated Seesaw Identity (`seesaw_identity`) (`seesaw_identity`)

Unfolds the composite chain `D.lowerChain` applied to the Poincaré map on ramified source forms into a finite linear combination `D.compositeLift` of definite chains `X₀ → … → X_m` restricted to `Y_m`.

- **Mathematical form:** `∃ c_ss ≠ 0, ∃ datum, lowerChain ∘ poincareAt = c_ss • compositeLift datum`
- **Lean anchor:** `seesaw_identity` in [New/UpperBound/Seesaw/SeesawIdentity.lean#L624](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Seesaw/SeesawIdentity.lean#L624) · Dominates **17** modules
- **Depends on:** `Adelic Weil Representation & Mixed-Model Slice Unfolding`, `Rallis Inner Product Formula for Sharp Data`
- **Notes:** Top bottleneck of New/UpperBound/Seesaw (dist=5, height=44, dominates 17 modules).

### Prime-by-Prime Divisibility of the Composite Lift (`local_divisibility`)

Establishes the `p`-adic gauge divisibility (`gaugeLe`) of `D.compositeLift` at every prime `p`: using level-`N` valuations, non-split valuations, and scaled Hecke operators (`MarkOperator`) with bounded colength.

- **Mathematical form:** `∃ span/colength control, gaugeLe (compositeLift) ≤ exp(-gain + error)`
- **Lean anchor:** `exists_err_gaugeLe_compositeLift` in [New/UpperBound/Divisibility/LocalDivisibility.lean#L494](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Divisibility/LocalDivisibility.lean#L494) · Dominates **17** modules
- **Depends on:** `Elementary Divisors of Edge Hecke Operators`, `Divisibility of Theta Jets Along Products of Minors`
- **Notes:** Top bottleneck of New/UpperBound/Divisibility (dist=5, height=44, dominates 17 modules).

### Archimedean Size of the Composite Lift (`archimedean_size`)

Bounds the Weyl norm squared of `D.compositeLift` at every complex conjugate using jet-conjugate bounds on the integral vacuum and projects onto `targetForms` via `goodProjTranslate`.

- **Mathematical form:** `weylNormSq (compositeLift) ≤ exp(mainAmount + error) ∧ normSqAt_goodProjTranslate_le`
- **Lean anchor:** `weylNormSq_compositeLift_le` in [New/UpperBound/Size/ArchimedeanSize.lean#L436](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Size/ArchimedeanSize.lean#L436)
- **Depends on:** `Sharpness of the Theta-Derivative Valuation Bound`
- **Notes:** Connects theta derivative sharpness to Theorem A and Theorem C auxiliary forms.

### Elementary Divisors of Edge Hecke Operators (`elementary_divisors`)

Bounds the colength of the image of scaled Hecke operators on integral source forms via Stepanov's root lemma, Frobenius defect counts, Pieri cones, and Schur-algebra averaging.

- **Mathematical form:** `elementary_divisors : colength bound on edge Hecke pairing map`
- **Lean anchor:** `elementary_divisors` in [New/UpperBound/ElementaryDivisors/ElementaryDivisorTheorem.lean#L1166](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/ElementaryDivisors/ElementaryDivisorTheorem.lean#L1166) · Dominates **10** modules
- **Depends on:** `Integral `GL(n+1) → GL(n)` Branching Maps`
- **Notes:** Culmination of the 10-file New/UpperBound/ElementaryDivisors folder.

### Sharpness of the Theta-Derivative Valuation Bound (`derivatives_sharpness`)

Proves that the `p`-adic valuation bound achieved by derivatives of CM theta functions along normal-form couplings is tight up to `b`-place near-pair losses, calibrating `P.vacuumBoundConst`.

- **Mathematical form:** `p^{-localPrimeSumTotal} ≤ ‖coeff(indicatorDatum)‖`
- **Lean anchor:** `exists_rpow_neg_localPrimeSumTotal_le_norm_coeff` in [New/Derivatives/Sharpness/BoundAttained.lean#L381](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Derivatives/Sharpness/BoundAttained.lean#L381) · Dominates **5** modules
- **Depends on:** `Divisibility of Theta Jets Along Products of Minors`, `Chowla–Selberg Formula for CM Curves`
- **Notes:** Culmination of New/Derivatives (Sharpness).

### Divisibility of Theta Jets Along Products of Minors (`derivatives_divisibility`)

Proves that high-order derivatives (`schurJet`) of theta series in normal form along coupled directions accumulate `p`-adic divisibility proportional to prime-power counts.

- **Mathematical form:** `‖schurJet(normalForm)‖_p ≤ ‖jet_minorProd‖_p ≤ p^{-charge}`
- **Lean anchor:** `norm_jet_minorProd_le_of_hasNormalForm` in [New/Derivatives/Divisibility/Count.lean#L707](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Derivatives/Divisibility/Count.lean#L707)
- **Depends on:** None (foundation)
- **Notes:** Core p-adic divisibility engine of New/Derivatives.

### Second-Moment Unfolding & Near-Isometry (`Moments`) (`second_moment_unfolding`)

Unfolds the second moment of Petersson Poincaré operators `P* s P` into near/remaining terms and the main term, proving that `piTensorElem` is a near-isometry on good forms.

- **Mathematical form:** `‖1 − piTensorElem_comp‖_HS^2 ≤ ε ⇒ isNearIsometry`
- **Lean anchor:** `HasAmplitudeBlocks.isNearIsometry_piTensorElem_comp` in [New/Spanning/Unfolding/Moments.lean#L1230](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/Unfolding/Moments.lean#L1230) · Dominates **34** modules
- **Depends on:** `Bound on Remaining Orbit Terms in Second Moment`, `Main-Term Kloosterman Sieve Energy Estimate`, `Discrete-Series Period Lower Bounds by Laplace's Method`
- **Notes:** Unfolding synthesis dominating 34 modules in New/Spanning.

### Bound on Remaining Orbit Terms in Second Moment (`remaining_terms_sum`)

Bounds the off-diagonal / remaining orbit terms in the second-moment unfolding using Siegel's lemma, lattice discriminants, bordered determinants, and Schur's test.

- **Mathematical form:** `secondMoment_remainingTerms_le`
- **Lean anchor:** `secondMoment_remainingTerms_le` in [New/Spanning/RemainingTerms/Sum.lean#L682](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/RemainingTerms/Sum.lean#L682) · Dominates **8** modules
- **Depends on:** None (foundation)
- **Notes:** Culmination of the 23-file RemainingTerms track.

### Main-Term Kloosterman Sieve Energy Estimate (`main_term_energy`)

Bounds the main-term energy over open-cell reductions fixing prescribed vectors via one-sided Poisson summation, Kloosterman orbital integrals, and two-frame local densities.

- **Mathematical form:** `linkSecondMoment_isOpenElement_le`
- **Lean anchor:** `linkSecondMoment_isOpenElement_le` in [New/Spanning/MainTerm/EnergyEstimate.lean#L631](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/MainTerm/EnergyEstimate.lean#L631) · Dominates **21** modules
- **Depends on:** None (foundation)
- **Notes:** Combines New/Spanning/MainTerm and the 22-file New/Spanning/Frames folder.

### Discrete-Series Period Lower Bounds by Laplace's Method (`discrete_series_periods`)

Proves quantitative lower bounds for real Bessel/discrete-series matrix-coefficient integrals near compact subgroups via second-order Taylor expansions and Laplace's method.

- **Mathematical form:** `IsLaplaceDatum.laplace_method`
- **Lean anchor:** `IsLaplaceDatum.laplace_method` in [New/Appendix/DiscreteSeries/Periods.lean#L493](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Appendix/DiscreteSeries/Periods.lean#L493) · Dominates **5** modules
- **Depends on:** `Real Discrete Series & Local Theta Correspondence`
- **Notes:** Appendix module supporting real Bessel lower bounds.

### Spanning Auxiliary Forms on the Two-Grid Last Path (`auxiliary_spanning_forms`)

Constructs spanning auxiliary target forms via monotone paths and square turns across the two-grid theta diagram, bounding their denominators and archimedean sizes.

- **Mathematical form:** `∃ scalar, span {y | IsAuxiliaryForm γ y} = ⊤`
- **Lean anchor:** `exists_span_short_lifts_eq_top` in [New/Determinant/AuxiliaryForms/SpanningForms.lean#L773](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/AuxiliaryForms/SpanningForms.lean#L773) · Dominates **7** modules
- **Depends on:** `Factorization of the Chain Gram Determinant `Z(ξ)``, `Exchange Identity for Matched Theta Integrals`
- **Notes:** Culmination of the 11-file New/Determinant/AuxiliaryForms track.

### Factorization of the Chain Gram Determinant `Z(ξ)` (`norm_of_chain`)

Factorizes `D.chainDeterminant 1 / D.chainDeterminant ϑ` as the product of the single-lift determinant ratios `Z_j(1) / Z_j(ϑ^j)` times explicit powers of Hecke `L`-value quotient ratios.

- **Mathematical form:** `Z(1) / Z(ϑ) = scalar(ϑ)^{-d_T} · ∏_{j=1}^m (Z_j(1) / Z_j(ϑ))`
- **Lean anchor:** `exists_chainDeterminant_pos_and_div_chainDeterminant_one_eq` in [New/Determinant/Chain/NormOfChain.lean#L419](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Chain/NormOfChain.lean#L419)
- **Depends on:** `Exchange Identity for Matched Theta Integrals`, `Rallis Inner Product Formula for Sharp Data`
- **Notes:** Reduces chain Gram determinants to single-lift determinants.

### Exchange Identity for Matched Theta Integrals (`exchange_identity`)

Proves that theta integrals over complementary-rank unitary groups `U(V)` and `U(V')` agree for matched ramified data up to a nonzero scalar `c` whose squared norm is a product of partial Hecke `L`-values.

- **Mathematical form:** `∃ c ≠ 0, ‖c‖² = const · ∏ L_S(...) ∧ θ_V = c · θ_{V'}`
- **Lean anchor:** `exchange_identity` in [New/Determinant/Exchange/TheoremForPartners.lean#L1051](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Exchange/TheoremForPartners.lean#L1051) · Dominates **8** modules
- **Depends on:** `Convergent Unitary Siegel–Weil Formula`, `Adelic Weil Representation & Mixed-Model Slice Unfolding`
- **Notes:** Core Siegel–Weil-type exchange theorem powering Chain and OneSquare.

### Single-Lift Determinant Height Bound (`Z_j(1)/Z_j(ξ^j)`) (`lift_volume_height`)

Combines the comparison operator `P_V`, gluing maps, false-lift period vanishing, and twisted Hecke-value heights to bound the height of `Z_j(1)/Z_j(ξ^j)` in terms of `directionAmount` and `denominatorBudget`.

- **Mathematical form:** `HeightLe (d · k · (logB · denominatorBudget − directionAmount)) (Z_j(1)/Z_j(ξ^j))`
- **Lean anchor:** `heightLe_liftDeterminant_ratio` in [New/OneLift/LiftVolumeHeight.lean#L729](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/OneLift/LiftVolumeHeight.lean#L729) · Dominates **15** modules
- **Depends on:** `Heights of Twisted-to-Untwisted Hecke L-Values`, `Rallis Inner Product Formula for Sharp Data`
- **Notes:** Top bottleneck of New/OneLift (dist=5, height=47).

### Heights of Twisted-to-Untwisted Hecke L-Values (`twisted_value_heights`)

Expresses products of critical Hecke `L`-value ratios via rank-one theta lifts from `U(1)` and bounds their global heights across all `p`-adic and archimedean embeddings.

- **Mathematical form:** `heightLe_inv_heckeValueProd_div`
- **Lean anchor:** `heightLe_inv_heckeValueProd_div` in [New/OneLift/HeckeValues/TwistedValueHeights.lean#L1066](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/OneLift/HeckeValues/TwistedValueHeights.lean#L1066) · Dominates **7** modules
- **Depends on:** `Rallis Inner Product Formula for Sharp Data`
- **Notes:** Culmination of New/OneLift/HeckeValues.

### First-Order Ribet Method & Clearing Denominator Bound (`denominator_bound_ribet`)

Uses Amitsur's formula, Fitting ideals, Taylor–Wiles auxiliary primes, and Ribet's congruence element to bound the `ℓ`-adic clearing determinant (`DenominatorLe`) against Selmer lengths and local crystalline defects.

- **Mathematical form:** `denominatorLe_clearingBound`
- **Lean anchor:** `denominatorLe_clearingBound` in [New/Congruences/FirstOrder/DenominatorBound.lean#L1321](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FirstOrder/DenominatorBound.lean#L1321) · Dominates **24** modules
- **Depends on:** `Spherical Chain Lemma for Unitary Representations of `GL_N``, `Attached Galois Representations in Every Positive Rank`, `Local Crystalline Defect Bound Above `ℓ``
- **Notes:** Critical-path hub (height=47, 1,333 lines, dominates 24 modules).

### Anticyclotomic Twisting Theorem for Selmer Groups (`selmer_twisting`)

Constructs `m`-fold anticyclotomic twists `ϑ` whose tied Bloch–Kato Selmer groups satisfy logarithmic length bounds controlled by Stickelberger/Katz `L`-value systems and Taylor–Wiles descent.

- **Mathematical form:** `exists_mFoldTwist_hasDivisibleSelmerLengthLe`
- **Lean anchor:** `exists_mFoldTwist_hasDivisibleSelmerLengthLe` in [New/Congruences/Selmer/TwistingTheorem.lean#L370](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/Selmer/TwistingTheorem.lean#L370) · Dominates **20** modules
- **Depends on:** `Uniform Bound on Odd-Part Ш Over Cyclotomic Fields`, `Greenberg–Wiles Cocycle Counting Without Local Duality`, `Global Artin Reciprocity & Sign Law`, `Local-Global Compatibility for Hecke Character Avatars`, `Local Crystalline Defect Bound Above `ℓ``
- **Notes:** Culmination of the 16-file New/Congruences/Selmer folder (dominates 20 modules).

### Local Crystalline Defect Bound Above `ℓ` (`crystalline_defect`)

Bounds the length lost at places dividing `ℓ` between crystalline classes and congruent dual lattices for main-summand Galois representations with tame types and sparse `b`-places.

- **Mathematical form:** `New.Selmer.summand_defect_le_at_place`
- **Lean anchor:** `New.Selmer.summand_defect_le_at_place` in [New/Congruences/LocalLoss/CrystallineDefect.lean#L647](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/LocalLoss/CrystallineDefect.lean#L647)
- **Depends on:** `Crystalline Extension Lifting & Kummer Chart Orthogonality`, `Breuil–Kisin Module Frame Theorem`
- **Notes:** Bridges Kisin lifting bounds into Ribet and Selmer estimates.

### Crystalline Extension Lifting & Kummer Chart Orthogonality (`kisin_cup_orthogonality`)

Bounds cup-product orthogonality exponents on paired sides of tame Kummer charts for Breuil–Kisin modules in large weight, controlling local crystalline extension losses above `ℓ`.

- **Mathematical form:** `hasCupExponent_of_isTameType`
- **Lean anchor:** `hasCupExponent_of_isTameType` in [New/Congruences/Lifting/CupOrthogonalityBounds.lean#L532](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/Lifting/CupOrthogonalityBounds.lean#L532) · Dominates **15** modules
- **Depends on:** `Breuil–Kisin Module Frame Theorem`
- **Notes:** Culmination of the 11-file New/Congruences/Lifting folder (dominates 15 modules).

---

## Stage 4: Foundational `Lib/` Background Machinery (19 milestones)

Self-contained peer-reviewed background theories in `src/Lib/` (importing nothing from `src/New/`): Galois representations in all ranks, class field theory & Greenberg–Wiles counting, odd-part Ш bounds, Shimura moduli & Eichler–Shimura, p-adic comparison & Kisin frame theorems, Siegel–Weil & Rallis formulas, Weil models, discrete series, and Chowla–Selberg.

### Attached Galois Representations in Every Positive Rank (`lib_galois_all_ranks`)

Constructs attached `ℓ`-adic Galois representations `Isotypic.attached_galRep` (and `sphericalCompat_std`) for algebraic eigenforms on definite unitary groups of arbitrary rank `n ≥ 1`, via lifts to rank `2n + 1` and cancellation.

- **Mathematical form:** `New.GaloisRep.sphericalCompat_std ∧ Isotypic.attached_galRep`
- **Lean anchor:** `Isotypic.attached_galRep` in [Lib/GaloisRep/Main/AllRanks.lean#L792](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/AllRanks.lean#L792) · Dominates **93** modules
- **Depends on:** `Local-Global Compatibility for Hecke Character Avatars`, `Shimura Eigenquotients & Galois Representations`, `Limits of Crystalline Representations via Trace Limits`, `Simple Trace Formula Comparison Across Real Signatures`
- **Notes:** Top Lib/ dominator (rank 6 overall, dominates 93 modules).

### Local-Global Compatibility for Hecke Character Avatars (`lib_local_global_avatar`)

Establishes base change and local-global compatibility for `ℓ`-adic avatars of algebraic Hecke characters over stably unramified CM fields (`HasPrimitiveRoot5040`).

- **Mathematical form:** `New.GaloisRep.avatarCompatAt_of_hasPrimitiveRoot5040`
- **Lean anchor:** `New.GaloisRep.avatarCompatAt_of_hasPrimitiveRoot5040` in [Lib/ClassField/Avatar/LocalGlobalCompatibility.lean#L191](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/LocalGlobalCompatibility.lean#L191) · Dominates **91** modules
- **Depends on:** `Global Artin Reciprocity & Sign Law`
- **Notes:** Rank 7 dominator overall (dominates 91 modules).

### Global Artin Reciprocity & Sign Law (`lib_artin_reciprocity`)

Proves global Artin reciprocity on finite ideles (`artin_reciprocity`) and the complex-conjugation sign law for profinite characters over totally complex number fields.

- **Mathematical form:** `artin_reciprocity ∧ abelianLift_artinMap_principalIdele_eq_one_iff`
- **Lean anchor:** `artin_reciprocity` in [Lib/ClassField/Global/ArtinReciprocity.lean#L453](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Global/ArtinReciprocity.lean#L453)
- **Depends on:** None (foundation)
- **Notes:** Replaces classical global class field theory on finite ideles.

### Greenberg–Wiles Cocycle Counting Without Local Duality (`lib_greenberg_wiles`)

Counts trivialised Galois cocycles at split auxiliary places via `S`-units and power-residue reciprocity, providing the finite-module Selmer upper bound used in descent.

- **Mathematical form:** `New.IsLargeLevel.SplitPlaces.hasFewCocycles_of_central`
- **Lean anchor:** `New.IsLargeLevel.SplitPlaces.hasFewCocycles_of_central` in [Lib/ClassField/GreenbergWiles/CocycleCounts.lean#L707](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/GreenbergWiles/CocycleCounts.lean#L707)
- **Depends on:** None (foundation)
- **Notes:** Replaces Greenberg–Wiles formula in Selmer counting.

### Uniform Bound on Odd-Part Ш Over Cyclotomic Fields (`lib_odd_sha`)

Proves an explicit uniform integer bound (`New.exists_length_shaOdd_le`) on the length of odd-part unramified Galois cocycle modules of a CM field at every prime `ℓ` via Stickelberger and Kolyvagin classes.

- **Mathematical form:** `New.exists_length_shaOdd_le`
- **Lean anchor:** `New.exists_length_shaOdd_le` in [Lib/Cyclotomic/OddSha.lean#L645](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Cyclotomic/OddSha.lean#L645) · Dominates **4** modules
- **Depends on:** None (foundation)
- **Notes:** Culmination of Lib/Cyclotomic.

### Integral Kuga–Sato / PEL Shimura Models & Congruence Relation (`lib_shimura_tower`)

Constructs integral projective models of `GU(1, n−1)` PEL Shimura towers (`New.Variety.exists_model`) via Appell–Humbert complex uniformisation and theta-null embeddings, with Eichler–Shimura congruence.

- **Mathematical form:** `New.Variety.exists_model`
- **Lean anchor:** `New.Variety.exists_model` in [Lib/Shimura/IntegralModel/TowerExistence.lean#L388](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/IntegralModel/TowerExistence.lean#L388)
- **Depends on:** None (foundation)
- **Notes:** Culmination of Lib/Shimura/Uniformisation, ThetaModuli, and IntegralModel.

### Shimura Eigenquotients & Galois Representations (`lib_shimura_eigenspace`)

Cuts `ℓ`-adic Galois representations out of étale cohomology of `GU(1, n−1)` Shimura towers (`exists_galois_rep`) killed by the Eichler–Shimura Hecke polynomial.

- **Mathematical form:** `New.Variety.Model.exists_galois_rep`
- **Lean anchor:** `New.Variety.Model.exists_galois_rep` in [Lib/Shimura/Eigenspace.lean#L689](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Eigenspace.lean#L689) · Dominates **46** modules
- **Depends on:** `Integral Kuga–Sato / PEL Shimura Models & Congruence Relation`, `p-adic Crystalline & Hodge–Tate Comparison Theorems`, `Woods Hole Fixed-Point Formula in Hodge Cohomology`
- **Notes:** Dominates 46 modules in Lib/Shimura, Lib/Cohomology, and Lib/PadicComparison.

### p-adic Crystalline & Hodge–Tate Comparison Theorems (`lib_padic_comparison`)

Proves crystallinity of `p`-adic étale cohomology for charted proper smooth schemes and Frobenius congruence relations (`ellAdicCohom.isCrystalline_and_linearFrob_rel`), via primitive comparison and almost `v`-descent.

- **Mathematical form:** `ellAdicCohom.isCrystalline_and_linearFrob_rel`
- **Lean anchor:** `ellAdicCohom.isCrystalline_and_linearFrob_rel` in [Lib/PadicComparison/CrystallineFrobenius.lean#L713](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/PadicComparison/CrystallineFrobenius.lean#L713) · Dominates **8** modules
- **Depends on:** `Woods Hole Fixed-Point Formula in Hodge Cohomology`
- **Notes:** Culmination of Lib/PadicComparison.

### Woods Hole Fixed-Point Formula in Hodge Cohomology (`lib_woods_hole`)

Proves the Woods Hole / Atiyah–Bott fixed-point vanishing theorem (`woods_hole`) for Hodge classes of correspondences on charted varieties.

- **Mathematical form:** `New.Variety.ellAdicCohom.woods_hole`
- **Lean anchor:** `New.Variety.ellAdicCohom.woods_hole` in [Lib/Cohomology/WoodsHole.lean#L214](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Cohomology/WoodsHole.lean#L214) · Dominates **10** modules
- **Depends on:** None (foundation)
- **Notes:** Culmination of Lib/Cohomology.

### Breuil–Kisin Module Frame Theorem (`lib_kisin_frame`)

Constructs Kummer charts, period matrices, and Kisin modules for integral crystalline lattices (`mem_kisinModule_iff_crysForms`), proving stability under normalising Galois elements.

- **Mathematical form:** `mem_kisinModule_iff_crysForms`
- **Lean anchor:** `mem_kisinModule_iff_crysForms` in [Lib/PadicHodge/Kisin/FrameTheorem.lean#L942](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/PadicHodge/Kisin/FrameTheorem.lean#L942) · Dominates **4** modules
- **Depends on:** None (foundation)
- **Notes:** Culmination of Lib/PadicHodge/Kisin.

### Limits of Crystalline Representations via Trace Limits (`lib_trace_limit`)

Proves that `ℓ`-adic limits of crystalline representations with bounded Hodge–Tate weights remain crystalline with bounded denominators (`local_clauses_of_trace_limit`).

- **Mathematical form:** `local_clauses_of_trace_limit`
- **Lean anchor:** `local_clauses_of_trace_limit` in [Lib/PadicHodge/Limit/TraceLimit.lean#L894](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/PadicHodge/Limit/TraceLimit.lean#L894)
- **Depends on:** `Breuil–Kisin Module Frame Theorem`
- **Notes:** Culmination of Lib/PadicHodge/Limit.

### Convergent Unitary Siegel–Weil Formula (`lib_siegel_weil`)

Proves the unitary Siegel–Weil formula in Weil's convergent range over CM fields (`siegel_weil`), equating theta integrals to Eisenstein series via Siegel sets and Lagrangian zero terms.

- **Mathematical form:** `New.SiegelWeil.siegel_weil`
- **Lean anchor:** `New.SiegelWeil.siegel_weil` in [Lib/SiegelWeil/Formula/WeilRange.lean#L757](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/SiegelWeil/Formula/WeilRange.lean#L757)
- **Depends on:** None (foundation)
- **Notes:** Core Siegel–Weil theorem in Lib/SiegelWeil.

### Rallis Inner Product Formula for Sharp Data (`lib_rallis_sharp`)

Proves the doubling Rallis inner product formula for sharp ramified data (`vacuumSum_eq_L_div_eulerProd`), relating theta-lift norms to critical Hecke `L`-values.

- **Mathematical form:** `vacuumSum_eq_L_div_eulerProd`
- **Lean anchor:** `vacuumSum_eq_L_div_eulerProd` in [Lib/SiegelWeil/RallisInner/SharpData.lean#L946](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/SiegelWeil/RallisInner/SharpData.lean#L946) · Dominates **5** modules
- **Depends on:** None (foundation)
- **Notes:** Feeds both New/OneLift and New/Determinant.

### Adelic Weil Representation & Mixed-Model Slice Unfolding (`lib_weil_mixed_model`)

Constructs the adelic Weil representation of unitary dual pairs and proves mixed-model zero-term and slice unfolding formulas (`IsAdapted.slice_omega_eq_integral`).

- **Mathematical form:** `IsAdapted.slice_omega_eq_integral`
- **Lean anchor:** `IsAdapted.slice_omega_eq_integral` in [Lib/Weil/MixedModel/ZeroTerm.lean#L785](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/MixedModel/ZeroTerm.lean#L785)
- **Depends on:** None (foundation)
- **Notes:** Central hub of Lib/Weil.

### Real Discrete Series & Local Theta Correspondence (`lib_discrete_series_theta`)

Establishes Flensted-Jensen discrete series coefficients `c_λ` on `U(p,q)`, Haar/Bruhat floor disintegrations, and Howe local theta correspondence via joint Fock harmonics.

- **Mathematical form:** `exists_bump_integratedRep_eq`
- **Lean anchor:** `exists_bump_integratedRep_eq` in [Lib/DiscreteSeries/Theta/LocalCorrespondence.lean#L734](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/DiscreteSeries/Theta/LocalCorrespondence.lean#L734)
- **Depends on:** None (foundation)
- **Notes:** Culmination of Lib/DiscreteSeries.

### Simple Trace Formula Comparison Across Real Signatures (`lib_trace_comparison`)

Compares simple trace formulas on unitary groups differing only at real places (`trace_comparison`), transferring Hecke multiplicities between definite spaces and `W_j`.

- **Mathematical form:** `trace_comparison`
- **Lean anchor:** `trace_comparison` in [Lib/Adelic/TraceFormula/TraceComparison.lean#L665](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Adelic/TraceFormula/TraceComparison.lean#L665)
- **Depends on:** None (foundation)
- **Notes:** Culmination of Lib/Adelic/TraceFormula.

### Chowla–Selberg Formula for CM Curves (`lib_chowla_selberg`)

Proves the Chowla–Selberg formula (`CMLattice.chowla_selberg`) relating periods of CM elliptic curves over `ℚ(√−d)` to `L'/L(1, χ_K)` and `γ`.

- **Mathematical form:** `CMLattice.chowla_selberg`
- **Lean anchor:** `CMLattice.chowla_selberg` in [Lib/CM/ChowlaSelberg.lean#L696](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/CM/ChowlaSelberg.lean#L696)
- **Depends on:** None (foundation)
- **Notes:** Supplies `chowlaSelbergConst d` in `New/Reduction/Data/AdmissibleData`.

### Spherical Chain Lemma for Unitary Representations of `GL_N` (`lib_spherical_chain`)

Proves `New.Patching.chain_lemma`: Satake parameters of unitary unramified `GL_N` representations arrange into chains, yielding integral operators at Taylor–Wiles auxiliary places.

- **Mathematical form:** `New.Patching.chain_lemma`
- **Lean anchor:** `New.Patching.chain_lemma` in [Lib/LocalGL/SphericalChainLemma.lean#L445](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/LocalGL/SphericalChainLemma.lean#L445)
- **Depends on:** None (foundation)
- **Notes:** Supplies auxiliary-place operators for Ribet's method.

### Integral `GL(n+1) → GL(n)` Branching Maps (`lib_gln_branching`)

Constructs integral unitarily equivariant branching maps between polynomial Schur/Weyl representations of `GL(n+1)` and `GL(n)` (`exists_branching_matrix`) with explicit norm bounds.

- **Mathematical form:** `_root_.New.exists_branching_matrix`
- **Lean anchor:** `_root_.New.exists_branching_matrix` in [Lib/GLn/Branching/IntegralMap.lean#L472](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GLn/Branching/IntegralMap.lean#L472)
- **Depends on:** None (foundation)
- **Notes:** Core representation-theoretic input from Lib/GLn.

---

## How Background Results & Axioms Are Organized

To verify that the five headline theorems in `Main.lean` are completely unconditional:

- **Clean separation of statements from `Lib/Speed.lean`:** [Statements.lean#LStatements.lean](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean#LStatements.lean) imports only `Mathlib`, ensuring the target statements use standard definitions and are unaffected by the `simp`/instance-priority settings in `Lib/Speed.lean`.
- **No unproved hypothesis bundles or custom axioms:** Every theorem in `New/` and `Lib/` is proved directly in Lean 4 using only Lean's standard axioms (`propext`, `Quot.sound`, `Classical.choice`), with zero imports from `New/` inside `Lib/`.
- **Tailored literature formulations in `Lib/`:** As documented in `GUIDE.md` and `INDEX.md`, `Lib/` proves self-contained forms of classical background results (e.g., Galois representations matching Hecke polynomials on `mostFrobenii`, local killing polynomials without full Weil–Deligne representations, and Greenberg–Wiles cocycle inequalities without dual Selmer pairings).

---

## Complete Milestone Index (51 Nodes)

<details>
<summary>Expand full table of all 51 verified blueprint milestones</summary>

| Stage | ID | Title | Lean Symbol | Source Link |
|---:|---|---|---|---|
| 0 | `main_export` | Main Theorems (RH, Half-Plane & GRH) | `riemannHypothesis` | [Main.lean#L5](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Main.lean#L5) |
| 0 | `statements_spec` | Standalone Target Theorem Statements | `RiemannZetaZerosOnLine` | [Statements.lean#L3](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Statements.lean#L3) |
| 1 | `new_main_reflection` | Functional-Equation Reflection (`s ↔ 1 − s`) | `New.zeros_on_line` | [New/Main.lean#L28](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Main.lean#L28) |
| 1 | `one_sided_bound` | One-Sided Prime Remainder Bound & Half-Plane GRH (`New.grh`) | `grh` | [New/Reduction/OneSidedBound.lean#L239](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/OneSidedBound.lean#L239) |
| 2 | `main_inequality` | The Main Inequality (`star_inequality`) | `star_inequality` | [New/Reduction/MainInequality.lean#L87](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/MainInequality.lean#L87) |
| 2 | `short_and_enough` | Theorems A & B: Short Forms & Enough Translates | `enough_forms` | [New/Reduction/ShortAndEnough.lean#L448](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/ShortAndEnough.lean#L448) |
| 2 | `long_forms_thm_c` | Theorem C: Integral Forms Are Long (`integral_forms_long`) | `integral_forms_long` | [New/Determinant/Twist/LongForms.lean#L214](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Twist/LongForms.lean#L214) |
| 2 | `fit_twists_exist` | Existence of Regular Families of `m`-Fold Twists | `New.exists_isRegularFamily` | [New/Congruences/FitTwistsExist.lean#L517](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FitTwistsExist.lean#L517) |
| 2 | `spanning_theorem` | Second-Moment Spanning Theorem (`isSpread_goodPoincare`) | `isSpread_goodPoincare` | [New/Spanning/SecondMoment/SpanningTheorem.lean#L339](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/SecondMoment/SpanningTheorem.lean#L339) |
| 2 | `eventually_exists_data` | Existence of Admissible Data at Large Scales | `eventually_exists_data` | [New/Reduction/Data/Existence.lean#L898](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Data/Existence.lean#L898) |
| 3 | `criterion_zero_free` | One-Sided Landau Criterion for Zero-Free Half-Plane | `New.LFunction_ne_zero_of_primeRemainder_le` | [New/Reduction/Zeros/Criterion.lean#L37](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Zeros/Criterion.lean#L37) |
| 3 | `pnt_remainder` | Prime Number Theorem Bound for `R_q` at Cut-Off `x₁` | `eventually_abs_primeRemainder_le` | [New/Reduction/Zeros/PrimeNumberTheorem.lean#L217](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Zeros/PrimeNumberTheorem.lean#L217) |
| 3 | `twisted_lattice_product` | Twisted Lattice Product Formula (`covolume_add_index_nonneg`) | `covolume_add_index_nonneg` | [New/Reduction/Lattices/TwistedLattice.lean#L477](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Reduction/Lattices/TwistedLattice.lean#L477) |
| 3 | `seesaw_identity` | Iterated Seesaw Identity (`seesaw_identity`) | `seesaw_identity` | [New/UpperBound/Seesaw/SeesawIdentity.lean#L624](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Seesaw/SeesawIdentity.lean#L624) |
| 3 | `local_divisibility` | Prime-by-Prime Divisibility of the Composite Lift | `exists_err_gaugeLe_compositeLift` | [New/UpperBound/Divisibility/LocalDivisibility.lean#L494](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Divisibility/LocalDivisibility.lean#L494) |
| 3 | `archimedean_size` | Archimedean Size of the Composite Lift | `weylNormSq_compositeLift_le` | [New/UpperBound/Size/ArchimedeanSize.lean#L436](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/Size/ArchimedeanSize.lean#L436) |
| 3 | `elementary_divisors` | Elementary Divisors of Edge Hecke Operators | `elementary_divisors` | [New/UpperBound/ElementaryDivisors/ElementaryDivisorTheorem.lean#L1166](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/UpperBound/ElementaryDivisors/ElementaryDivisorTheorem.lean#L1166) |
| 3 | `derivatives_sharpness` | Sharpness of the Theta-Derivative Valuation Bound | `exists_rpow_neg_localPrimeSumTotal_le_norm_coeff` | [New/Derivatives/Sharpness/BoundAttained.lean#L381](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Derivatives/Sharpness/BoundAttained.lean#L381) |
| 3 | `derivatives_divisibility` | Divisibility of Theta Jets Along Products of Minors | `norm_jet_minorProd_le_of_hasNormalForm` | [New/Derivatives/Divisibility/Count.lean#L707](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Derivatives/Divisibility/Count.lean#L707) |
| 3 | `second_moment_unfolding` | Second-Moment Unfolding & Near-Isometry (`Moments`) | `HasAmplitudeBlocks.isNearIsometry_piTensorElem_comp` | [New/Spanning/Unfolding/Moments.lean#L1230](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/Unfolding/Moments.lean#L1230) |
| 3 | `remaining_terms_sum` | Bound on Remaining Orbit Terms in Second Moment | `secondMoment_remainingTerms_le` | [New/Spanning/RemainingTerms/Sum.lean#L682](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/RemainingTerms/Sum.lean#L682) |
| 3 | `main_term_energy` | Main-Term Kloosterman Sieve Energy Estimate | `linkSecondMoment_isOpenElement_le` | [New/Spanning/MainTerm/EnergyEstimate.lean#L631](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Spanning/MainTerm/EnergyEstimate.lean#L631) |
| 3 | `discrete_series_periods` | Discrete-Series Period Lower Bounds by Laplace's Method | `IsLaplaceDatum.laplace_method` | [New/Appendix/DiscreteSeries/Periods.lean#L493](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Appendix/DiscreteSeries/Periods.lean#L493) |
| 3 | `auxiliary_spanning_forms` | Spanning Auxiliary Forms on the Two-Grid Last Path | `exists_span_short_lifts_eq_top` | [New/Determinant/AuxiliaryForms/SpanningForms.lean#L773](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/AuxiliaryForms/SpanningForms.lean#L773) |
| 3 | `norm_of_chain` | Factorization of the Chain Gram Determinant `Z(ξ)` | `exists_chainDeterminant_pos_and_div_chainDeterminant_one_eq` | [New/Determinant/Chain/NormOfChain.lean#L419](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Chain/NormOfChain.lean#L419) |
| 3 | `exchange_identity` | Exchange Identity for Matched Theta Integrals | `exchange_identity` | [New/Determinant/Exchange/TheoremForPartners.lean#L1051](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Determinant/Exchange/TheoremForPartners.lean#L1051) |
| 3 | `lift_volume_height` | Single-Lift Determinant Height Bound (`Z_j(1)/Z_j(ξ^j)`) | `heightLe_liftDeterminant_ratio` | [New/OneLift/LiftVolumeHeight.lean#L729](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/OneLift/LiftVolumeHeight.lean#L729) |
| 3 | `twisted_value_heights` | Heights of Twisted-to-Untwisted Hecke L-Values | `heightLe_inv_heckeValueProd_div` | [New/OneLift/HeckeValues/TwistedValueHeights.lean#L1066](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/OneLift/HeckeValues/TwistedValueHeights.lean#L1066) |
| 3 | `denominator_bound_ribet` | First-Order Ribet Method & Clearing Denominator Bound | `denominatorLe_clearingBound` | [New/Congruences/FirstOrder/DenominatorBound.lean#L1321](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/FirstOrder/DenominatorBound.lean#L1321) |
| 3 | `selmer_twisting` | Anticyclotomic Twisting Theorem for Selmer Groups | `exists_mFoldTwist_hasDivisibleSelmerLengthLe` | [New/Congruences/Selmer/TwistingTheorem.lean#L370](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/Selmer/TwistingTheorem.lean#L370) |
| 3 | `crystalline_defect` | Local Crystalline Defect Bound Above `ℓ` | `New.Selmer.summand_defect_le_at_place` | [New/Congruences/LocalLoss/CrystallineDefect.lean#L647](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/LocalLoss/CrystallineDefect.lean#L647) |
| 3 | `kisin_cup_orthogonality` | Crystalline Extension Lifting & Kummer Chart Orthogonality | `hasCupExponent_of_isTameType` | [New/Congruences/Lifting/CupOrthogonalityBounds.lean#L532](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/New/Congruences/Lifting/CupOrthogonalityBounds.lean#L532) |
| 4 | `lib_galois_all_ranks` | Attached Galois Representations in Every Positive Rank | `Isotypic.attached_galRep` | [Lib/GaloisRep/Main/AllRanks.lean#L792](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GaloisRep/Main/AllRanks.lean#L792) |
| 4 | `lib_local_global_avatar` | Local-Global Compatibility for Hecke Character Avatars | `New.GaloisRep.avatarCompatAt_of_hasPrimitiveRoot5040` | [Lib/ClassField/Avatar/LocalGlobalCompatibility.lean#L191](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Avatar/LocalGlobalCompatibility.lean#L191) |
| 4 | `lib_artin_reciprocity` | Global Artin Reciprocity & Sign Law | `artin_reciprocity` | [Lib/ClassField/Global/ArtinReciprocity.lean#L453](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/Global/ArtinReciprocity.lean#L453) |
| 4 | `lib_greenberg_wiles` | Greenberg–Wiles Cocycle Counting Without Local Duality | `New.IsLargeLevel.SplitPlaces.hasFewCocycles_of_central` | [Lib/ClassField/GreenbergWiles/CocycleCounts.lean#L707](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/ClassField/GreenbergWiles/CocycleCounts.lean#L707) |
| 4 | `lib_odd_sha` | Uniform Bound on Odd-Part Ш Over Cyclotomic Fields | `New.exists_length_shaOdd_le` | [Lib/Cyclotomic/OddSha.lean#L645](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Cyclotomic/OddSha.lean#L645) |
| 4 | `lib_shimura_tower` | Integral Kuga–Sato / PEL Shimura Models & Congruence Relation | `New.Variety.exists_model` | [Lib/Shimura/IntegralModel/TowerExistence.lean#L388](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/IntegralModel/TowerExistence.lean#L388) |
| 4 | `lib_shimura_eigenspace` | Shimura Eigenquotients & Galois Representations | `New.Variety.Model.exists_galois_rep` | [Lib/Shimura/Eigenspace.lean#L689](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Shimura/Eigenspace.lean#L689) |
| 4 | `lib_padic_comparison` | p-adic Crystalline & Hodge–Tate Comparison Theorems | `ellAdicCohom.isCrystalline_and_linearFrob_rel` | [Lib/PadicComparison/CrystallineFrobenius.lean#L713](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/PadicComparison/CrystallineFrobenius.lean#L713) |
| 4 | `lib_woods_hole` | Woods Hole Fixed-Point Formula in Hodge Cohomology | `New.Variety.ellAdicCohom.woods_hole` | [Lib/Cohomology/WoodsHole.lean#L214](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Cohomology/WoodsHole.lean#L214) |
| 4 | `lib_kisin_frame` | Breuil–Kisin Module Frame Theorem | `mem_kisinModule_iff_crysForms` | [Lib/PadicHodge/Kisin/FrameTheorem.lean#L942](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/PadicHodge/Kisin/FrameTheorem.lean#L942) |
| 4 | `lib_trace_limit` | Limits of Crystalline Representations via Trace Limits | `local_clauses_of_trace_limit` | [Lib/PadicHodge/Limit/TraceLimit.lean#L894](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/PadicHodge/Limit/TraceLimit.lean#L894) |
| 4 | `lib_siegel_weil` | Convergent Unitary Siegel–Weil Formula | `New.SiegelWeil.siegel_weil` | [Lib/SiegelWeil/Formula/WeilRange.lean#L757](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/SiegelWeil/Formula/WeilRange.lean#L757) |
| 4 | `lib_rallis_sharp` | Rallis Inner Product Formula for Sharp Data | `vacuumSum_eq_L_div_eulerProd` | [Lib/SiegelWeil/RallisInner/SharpData.lean#L946](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/SiegelWeil/RallisInner/SharpData.lean#L946) |
| 4 | `lib_weil_mixed_model` | Adelic Weil Representation & Mixed-Model Slice Unfolding | `IsAdapted.slice_omega_eq_integral` | [Lib/Weil/MixedModel/ZeroTerm.lean#L785](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Weil/MixedModel/ZeroTerm.lean#L785) |
| 4 | `lib_discrete_series_theta` | Real Discrete Series & Local Theta Correspondence | `exists_bump_integratedRep_eq` | [Lib/DiscreteSeries/Theta/LocalCorrespondence.lean#L734](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/DiscreteSeries/Theta/LocalCorrespondence.lean#L734) |
| 4 | `lib_trace_comparison` | Simple Trace Formula Comparison Across Real Signatures | `trace_comparison` | [Lib/Adelic/TraceFormula/TraceComparison.lean#L665](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/Adelic/TraceFormula/TraceComparison.lean#L665) |
| 4 | `lib_chowla_selberg` | Chowla–Selberg Formula for CM Curves | `CMLattice.chowla_selberg` | [Lib/CM/ChowlaSelberg.lean#L696](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/CM/ChowlaSelberg.lean#L696) |
| 4 | `lib_spherical_chain` | Spherical Chain Lemma for Unitary Representations of `GL_N` | `New.Patching.chain_lemma` | [Lib/LocalGL/SphericalChainLemma.lean#L445](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/LocalGL/SphericalChainLemma.lean#L445) |
| 4 | `lib_gln_branching` | Integral `GL(n+1) → GL(n)` Branching Maps | `_root_.New.exists_branching_matrix` | [Lib/GLn/Branching/IntegralMap.lean#L472](https://github.com/leanprover-community/riemann-hypothesis/blob/9211277d096b7abc3f9c30184bdb2e32d98dcffb/src/Lib/GLn/Branching/IntegralMap.lean#L472) |

</details>

