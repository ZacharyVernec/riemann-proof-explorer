# Formalized Proof Blueprint: Riemann Hypothesis & Generalized Riemann Hypothesis (`original-2026-11-20`)

This blueprint distills the Lean proof DAG (**175,187 reachable modules**, **17,374,215 lines**, **753,261 internal dependency edges**) into **45 mathematical milestones** across **5 architectural stages** (Stages 0–4) connected by **112 dependency links** (interactive DAG in [blueprint.html](blueprint.html)).

> **Direction Convention:** Stage 0 sits at the apex (`Main.lean`); arrows `A → B` mean milestone `A` depends directly on prerequisite `B`.

---

## Executive Overview: The Proof Strategy in Plain English

At the highest level, the proof establishes **both** the classical **Riemann Hypothesis (RH)** and the **Generalized Riemann Hypothesis (GRH)** for all Dirichlet $L$-functions by reducing critical-line zero localization ($\operatorname{Re}(s) = \tfrac{1}{2}$) to a single universal statement: **no Dirichlet $L$-function $L(\chi, s)$ vanishes anywhere in the open right half-plane $\operatorname{Re}(s) > \tfrac{1}{2}$** (away from the pole of $\zeta(s)$ at $s = 1$).

Once this right half-plane nonvanishing holds, the functional equations of $\zeta(s)$ and primitive Dirichlet $L$-functions (plus Euler-factor nonvanishing for $\operatorname{Re}(s) > 0$) mirror every zero with $\operatorname{Re}(s) < \tfrac{1}{2}$ onto a zero with $\operatorname{Re}(1 - s) > \tfrac{1}{2}$, forcing all nontrivial zeros onto $\operatorname{Re}(s) = \tfrac{1}{2}$.

To prove $L(\chi, s) \neq 0$ for $\operatorname{Re}(s) > \tfrac{1}{2}$, the formalization executes a **windowed Landau–Chebyshev–Galois strategy**:
1. **Windowed Chebyshev-to-Zero-Free Principle (Analytic Engine):** By a finite-level variant of Landau's nonnegativity theorem on cyclic character groups $\Lambda_\psi = \langle \psi \rangle$, if the weighted Chebyshev-type prime-power error sum $G_{\Lambda_\psi}(x) \le x^{\frac{1}{2} + O(\varepsilon)}$ holds throughout sufficiently wide logarithmic windows $[Y, Y^\lambda]$ ($\lambda > 1$) as $x \to \infty$ (for arbitrarily small $\varepsilon > 0$), then $L(\psi, s)$ cannot vanish in $\operatorname{Re}(s) > \tfrac{1}{2}$.
2. **Galois-Theoretic Family Designs & Selmer/Shafarevich-Tate Growth Control:** To build families of auxiliary primes and cyclic character twists that achieve these windowed Chebyshev cancellations without hitting a bottleneck from exceptional zeros or bad ramification, the proof couples explicit prime-pair sieve/design bounds with **polynomial-in-log-conductor / subexponential upper bounds on Shafarevich-Tate / Bloch-Kato Selmer group lengths** (`VWin`) across cyclotomic/abelian number fields.
3. **Modularity Lifting, $U(3)$ Selmer Counting & Kato's Euler System:** Those Selmer growth bounds (`VWin`, and its explicit specialization to $\mathbb{Q}(\sqrt{-3})$) are proved via automorphy lifting, patching arguments, $U(3)$ Galois-cohomology counting over auxiliary imaginary quadratic fields $K^*(p)$, Poitou-Tate nine-term duality, weight-1 Hilbert Eisenstein series, and Kato's Euler system (`ZetaUr`).
4. **Local-Global Compatibility & Theta-Correspondence Lifts:** The modularity and Selmer machinery requires strong local-global compatibility (`Row0b`) between $\ell$-adic Galois representations and polarized regular algebraic cuspidal automorphic representations of $\mathrm{GL}_n$, together with an explicit Local Langlands correspondence preserving tame/depth-zero types (`recTExists`). The formalization establishes `Row0b` via a **weight-one geometric realization** (crystalline towers, finite-étale Kodaira-Spencer models, and the holomorphic Lefschetz fixed-point formula) combined with **global unitary theta-kernel Parseval lifts** (`TLiftK`), paired with Siegel-Weil formulas, Harish-Chandra infinitesimal characters, and Flath factorization.
5. **Arakelov Geometry & Moriwaki Bigness (`CovolX`):** Controlling the rank, height, and lattice covolume constants of the arithmetic parameter families requires global Arakelov intersection lower bounds (`CovolX`, `VolumeTheoremX`), proved via PEL-type Shimura toroidal compactifications, Mumford semiabelian uniformisations, functorial resolution of singularities in characteristic zero, twisted étale cohomology finiteness, Bost-Zhang Hermitian lattice slope bounds, and Moriwaki's arithmetic bigness and Hilbert-Samuel volume theorems.

---

## Stage 0: Final Theorems (3 milestones)

Standalone target statements and top-level proved theorems for the Riemann Hypothesis, Dirichlet L-function half-plane nonvanishing, and Generalized Riemann Hypothesis.

### Main Theorems (RH, Half-Plane & GRH) (`main_export`)

- **Statement:** Unconditionally establishes the Riemann Hypothesis for ζ(s), nonvanishing of every Dirichlet L-function L(χ, s) on the open half-plane Re(s) > 1/2 (away from the pole at s = 1), and the Generalized Riemann Hypothesis for both arbitrary and primitive Dirichlet characters.
- **Assumptions:** None — all five headline theorems are completely unconditional.
- **Proof strategy:** Directly matches the proved theorems produced by the Stage 1 analytic reductions to the standalone target statements, introducing no new assumptions.
- **Lean anchor:** `riemannHypothesis` in [Main.lean#L4](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean#L4) · Dominates **175,187** modules
- **Depends on:** `Standalone Target Theorem Statements`, `Top-Level Theorem & Selmer Combination`
- **Notes:** Root module (dist=0, height=202). Exports riemannHypothesis (L4), riemannZeta_eq_zero_re (L6), LFunction_ne_zero_of_half_lt_re (L8), LFunction_eq_zero_re (L10), and LFunction_eq_zero_re_of_isPrimitive (L12).

### Standalone Target Theorem Statements (`statements_spec`)

- **Statement:** Formulates the four target propositions — critical-line zeros of ζ(s), half-plane nonvanishing of L(χ, s) on Re(s) > 1/2, and GRH for arbitrary and primitive characters — using only standard complex-analytic definitions.
- **Assumptions:** None — this milestone states definitions only and proves or assumes no theorems.
- **Proof strategy:** Contains no proof; isolates the exact mathematical claims from the proof machinery so a reader can verify what is being proved independently of how it is proved.
- **Lean anchor:** `RiemannZetaZerosOnLine` in [Statements.lean#L3](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Statements.lean#L3)
- **Depends on:** None (foundation)
- **Notes:** pure specification leaf depending only on Mathlib (dist=1, height=0).

### Top-Level Theorem & Selmer Combination (`main_theorems_all`)

- **Statement:** Unites the proved RH/GRH theorem suite (and its ℚ(√−3) arithmetic companions) with the unconditional polynomial upper bound on Selmer/Shafarevich–Tate group sizes over ℚ(√−3).
- **Assumptions:** None — both incoming branches (the Stage 1 critical-line theorems and the Stage 2 Selmer bound over ℚ(√−3)) are unconditionally proved.
- **Proof strategy:** Pure structural aggregation combining the analytic main theorems and the standalone arithmetic Selmer corollary into a single top-level package.
- **Lean anchor:** `Supplements.Kernels.MainTheoremsAll` in [Supplements/Kernels/MainTheoremsAll.lean#L1](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsAll.lean#L1) · Dominates **175,185** modules
- **Depends on:** `Critical-Line & ℚ(√−3) Arithmetic`, `Small-Class-Number Selmer Length Growth Bound over Q(sqrt(-3))`
- **Notes:** pure import barrel (dist=1, height=201) dominating all downstream proof modules.

---

## Stage 1: Functional-Equation & Character Reductions (6 milestones)

Analytic bridges reducing critical-line zero localization for ζ(s) and arbitrary/primitive Dirichlet L-functions to half-plane nonvanishing Re(s) > 1/2 via Euler factors, Gamma factors, and functional equations.

### Critical-Line & ℚ(√−3) Arithmetic (`main_theorems_critical`)

- **Statement:** Pairs the proved RH/GRH theorems with three arithmetic results for ℚ(√−3): class number h(ℚ(√−3)) = 1, a cocycle-vanishing criterion for Selmer length zero, and a Galois-representation existence criterion when length is nonzero.
- **Assumptions:** RH, GRH, h(ℚ(√−3)) = 1, and the length-zero equivalence are unconditional; the Selmer bound specialization and representation-existence lemma take the Stage 2 U(3) modularity inputs.
- **Proof strategy:** Proves h(ℚ(√−3)) = 1 via Minkowski's discriminant bound, characterizes length zero by every locally trivial Galois 1-cocycle being a coboundary (forcing vanishing once log l > C(e + 1)^{A}), and links nonzero length to an admissible 3-dimensional Galois representation.
- **Lean anchor:** `Supplements.Kernels.MainTheoremsCritical` in [Supplements/Kernels/MainTheoremsCritical.lean#L1](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsCritical.lean#L1) · Dominates **4,482** modules
- **Depends on:** `RH & GRH from Half-Plane Nonvanishing`
- **Notes:** assembly barrel (dist=2, height=200) importing MainTheorems, ClassNumberThree, LenEqZeroIff, and OnePoint.

### RH & GRH from Half-Plane Nonvanishing (`main_theorems_bridge`)

- **Statement:** Combines the unconditional Stage 2 half-plane nonvanishing theorem with Stage 1's complex-analytic reflections to deduce RH for ζ(s), GRH for primitive characters, and GRH for all Dirichlet characters.
- **Assumptions:** Unconditional overall — receives the proved half-plane nonvanishing theorem from Stage 2 and plugs it into the conditional Stage 1 reflection theorems.
- **Proof strategy:** Feeds L(χ, s) ≠ 0 on Re(s) > 1/2 into (1) zeta functional-equation reflection via the trivial character mod 1, (2) primitive-character reflection, and (3) Euler-factor reduction for imprimitive characters.
- **Lean anchor:** `allChi` in [Supplements/Kernels/MainTheorems.lean#L7](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheorems.lean#L7) · Dominates **4,479** modules
- **Depends on:** `Functional-Equation Reflection (Primitive)`, `Imprimitive Character Strip Reduction`, `Master Proof Synthesis (UpperTheory.FinalTheorems.everyCharacter)`
- **Notes:** Top bottleneck in Supplements/Kernels (dist=3, height=199).

### Functional-Equation Reflection (Primitive) (`crit_line`)

- **Statement:** Proves that the Gamma factor γ(χ, s) of any Dirichlet character never vanishes for Re(s) > 0, and deduces from half-plane nonvanishing that every critical-strip zero of a primitive L-function lies on Re(s) = 1/2 (plus RH for ζ).
- **Assumptions:** Nonvanishing of γ(χ, s) is unconditional; the critical-line conclusions assume L(χ, s) ≠ 0 for all χ and all Re(s) > 1/2 (away from s = 1 when χ = 1).
- **Proof strategy:** Uses γ(χ, s) ≠ 0 to transfer a putative zero with 0 < Re(s) < 1/2 to the completed L-function Λ(χ, s), reflects via the functional equation to obtain L(χ^{−1}, 1 − s) = 0 with Re(1 − s) > 1/2, and reaches a contradiction.
- **Lean anchor:** `Formalism.VW.critLine` in [Formalism/GammaFactorNonvanishing/CritLine.lean#L11](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean#L11)
- **Depends on:** `Zeta Reflection via Functional Equation`, `Character-Box Window Assembly (plugWin & plugAll)`
- **Notes:** Also proves Formalism.VW.rh_of_every (L29) by specializing EveryCharacter to the trivial character mod 1.

### Zeta Reflection via Functional Equation (`rh_of_right`)

- **Statement:** If ζ(s) has no zeros in the open right half-plane Re(s) > 1/2 (excluding s = 1), then every nontrivial zero of ζ(s) lies on the critical line Re(s) = 1/2.
- **Assumptions:** Assumes ζ(s) ≠ 0 for all s ∈ ℂ with Re(s) > 1/2 and s ≠ 1, plus standard properties of ζ(s), Γ(s), and cos(z).
- **Proof strategy:** Splits a nontrivial zero s by trichotomy on Re(s) vs. 1/2; for Re(s) < 1/2, applies Riemann's asymmetric functional equation at 1 − s and checks that 2(2π)^{−(1−s)}, Γ(1 − s), cos(π(1 − s)/2), and ζ(1 − s) are all nonzero.
- **Lean anchor:** `Formalism.VW.rh_of_right` in [Formalism/GammaFactorNonvanishing/RhOfRight.lean#L5](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/GammaFactorNonvanishing/RhOfRight.lean#L5)
- **Depends on:** None (foundation)
- **Notes:** leaf theorem proved directly from Mathlib's riemannZeta_one_sub.

### Imprimitive Character Strip Reduction (`claim_strip`)

- **Statement:** Shows that right half-plane nonvanishing for all Dirichlet L-functions implies GRH for every character χ modulo N (including imprimitive ones) as well as the classical Riemann Hypothesis for ζ(s).
- **Assumptions:** Assumes L(χ, s) ≠ 0 for all N ≥ 1, all χ mod N, and all Re(s) > 1/2 (away from s = 1 when χ = 1), plus the classical fact that ζ(s) ≠ 0 for Re(s) ≥ 1.
- **Proof strategy:** Factors L(χ, s) = L(ψ, s) ∏_{p | N} (1 − ψ(p)p^{−s}) via the inducing primitive character ψ; since |ψ(p)p^{−s}| < 1 for Re(s) > 0, no Euler factor vanishes, reducing to a zero of L(ψ, s) which reflects across s ↦ 1 − s into Re > 1/2.
- **Lean anchor:** `strip` in [Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L59](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L59)
- **Depends on:** `Half-Plane, Strip & Zeta Definitions`
- **Notes:** Also proves Claim.zeta (L75) and Claim.zeta_iff (L102).

### Half-Plane, Strip & Zeta Definitions (`half_plane_def`)

- **Statement:** Defines the three core analytic propositions linked by Stage 1: right half-plane nonvanishing for all Dirichlet L-functions, critical-strip localization (GRH) for all characters, and the Riemann Hypothesis for ζ(s).
- **Assumptions:** None — pure definitions using standard complex analysis and Dirichlet L-functions.
- **Proof strategy:** Contains no proof; establishes the clean interface separating the deep Stage 2–4 proof of nonvanishing on Re(s) > 1/2 from the elementary Stage 1 reflection arguments.
- **Lean anchor:** `Claim.HalfPlane` in [Development/AutomorphicArithmetic/CharacterBoxes/HalfPlane.lean#L3](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/HalfPlane.lean#L3)
- **Depends on:** None (foundation)
- **Notes:** Mathlib leaf file defining Claim.HalfPlane, Claim.Strip, and Claim.Zeta.

---

## Stage 2: Main Bridge Theorems & Dominators (11 milestones)

High-impact assembly bottlenecks merging local-global Galois representations, modularity/Selmer windows, theta-correspondence lifts, and Arakelov covolume bounds.

### Master Proof Synthesis (UpperTheory.FinalTheorems.everyCharacter) (`main_conclusion`)

Unconditionally proves half-plane nonvanishing for every Dirichlet L-function by feeding the proved strong local-global Galois compatibility theorem and Local Langlands reciprocity existence into both the modularity-Selmer window theorem (VWin) and the theta-correspondence main theorem.

- **Mathematical form:** `UpperTheory.FinalTheorems.everyCharacter : ∀ N ≥ 1, ∀ χ mod N, ∀ s ∈ ℂ, Re(s) > 1/2 ∧ (χ ≠ 1 ∨ s ≠ 1) ⇒ L(χ, s) ≠ 0`
- **Lean anchor:** `UpperTheory.FinalTheorems.everyCharacter` in [Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L10](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L10) · Dominates **4,474** modules
- **Depends on:** `Theta-Correspondence, Covolume & Literature Package Synthesis`, `Modularity Window Bridge (VwinOfRow)`, `Local Langlands Correspondence for GL_n with Tame Inertia Types`, `Strong Local-Global Galois Compatibility from Theta Parseval`, `208-Input Operator & Covolume Assembly (RiemannHypothesisOfEveryCharacter)`
- **Notes:** apex inside Development (dist=4, height=198). Discharges OpenLiteratureStatements via ⟨row_src, rec_t_exists, row_src⟩ and OpenImageCondition via ⟨row_src⟩.

### 208-Input Operator & Covolume Assembly (RiemannHypothesisOfEveryCharacter) (`rh_of_every_char`)

Gathers 208 representation-theoretic, interpolation, and Arakelov covolume modules and provides the direct deduction of RiemannHypothesis from EveryCharacter.

- **Mathematical form:** `UpperTheory.EveryCharacter ⇒ RiemannHypothesis (via completedRiemannZeta_one_sub and covolX_of_slim₂)`
- **Lean anchor:** `UpperTheory.riemannHypothesis_of_everyCharacter` in [Development/AutomorphicArithmetic/CharacterBoxes/RiemannHypothesisOfEveryCharacter.lean#L215](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/RiemannHypothesisOfEveryCharacter.lean#L215) · Dominates **10,065** modules
- **Depends on:** `Character-Box Window Assembly (plugWin & plugAll)`, `Covolume Lower Bound from Slimness & Height Theorems`
- **Notes:** Rank 7 dominator (dom_subtree=10,065, out_degree=208, dist=5, height=167).

### Character-Box Window Assembly (plugWin & plugAll) (`every_character_def`)

Combines the Green prime-character condition, the Selmer growth window bound VWin (for threshold exponent 401), and the family-design theorem TopShape to establish nonvanishing of all primitive and imprimitive Dirichlet L-functions in Re(s) > 1/2.

- **Mathematical form:** `Green ∧ VWin ∧ Nonempty(Hyps LinkN DRS) ⇒ ZeroFreeAll ⇒ EveryCharacter`
- **Lean anchor:** `UpperTheory.Top.plugAll` in [Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean#L16](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean#L16)
- **Depends on:** `Windowed Chebyshev Inequality from Design Choices (topDesWin)`, `Windowed Landau Nonvanishing Criterion (zeroFreeOn_of_tiedWin_cyc)`
- **Notes:** bridge connecting ShapeOf, ShapeWin, SupplyChi, and Imprimitive to ZeroFreeAll.

### Theta-Correspondence, Covolume & Literature Package Synthesis (`every_character_of_lit_vwin`)

Assembles over 70 proved theorems across harmonic analysis, unitary Siegel-Weil, Galois cohomology, and Arakelov geometry, feeding Moriwaki bigness and resolution into TopCovolSlim2Use and combining with definite-side theta lifts and VWin to prove EveryCharacter.

- **Mathematical form:** `OpenLiteratureStatements ∧ VWin ⇒ EveryCharacter (instantiating CovolX via topCovolSlim2_use_alt_alt and definite-side theta lifts)`
- **Lean anchor:** `UpperTheory.LiteratureTheorems.every_character_of_literature_of_vWin` in [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L810](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L810) · Dominates **4,472** modules
- **Depends on:** `208-Input Operator & Covolume Assembly (RiemannHypothesisOfEveryCharacter)`, `Arakelov Self-Intersection & Covolume Bridge (CovolX)`, `Moriwaki Arithmetic Bigness & Hilbert-Samuel Volume Chain`, `Functorial Resolution of Singularities in Characteristic Zero`, `Poitou-Tate Nine-Term Exact Sequence & Sha Duality`, `Whittaker Multiplicity One on GL_n(A_K)`, `Unitary Admissibility & Flath Tensor Product Factorization`, `Capelli Infinitesimal Character of U(p, q) Discrete Series`, `Unitary U(3) Selmer Growth Bound (CorGK → CountI)`
- **Notes:** synthesis hub (dist=5, height=171, out_degree=201). All but 3 fields of OpenLiteratureStatements are unconditionally proved theorems imported from PositivityTheory/CompanionTheory/GroundTheory/Development; the 3 fields are discharged in MainConclusion.

### Strong Local-Global Galois Compatibility from Theta Parseval (`row_src`)

Establishes strong local-global compatibility (Row0b recT) for l-adic Galois representations attached to polarized regular algebraic cuspidal automorphic representations by feeding the theta-kernel Parseval lift (TLiftK) and weight-one geometric realization (GeoOne) into the Galois representation construction.

- **Mathematical form:** `UpperTheory.GalStar.Row0b recT (l-adic Frobenius-Satake matching away from l and potentially semistable Weil-Deligne compatibility above l)`
- **Lean anchor:** `galoisLocalGlobalStrong_recParameter` in [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/RowSrc.lean#L6](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/RowSrc.lean#L6) · Dominates **13,055** modules
- **Depends on:** `Weight-One Geometric Realization (Crystalline Towers & Kodaira-Spencer)`, `Holomorphic Lefschetz Fixed-Point Formula for Finite Etale Correspondences`, `Theta-Kernel Parseval Lift & Nonvanishing (tLift_holds_k)`, `Local Langlands Correspondence for GL_n with Tame Inertia Types`, `Rapid Decay & L² Moments of Compactly Supported Cusp-Form Twists`, `Capelli Infinitesimal Character of U(p, q) Discrete Series`, `Whittaker Multiplicity One on GL_n(A_K)`
- **Notes:** Rank 3 overall dominator (dist=3, height=197) via GaloisRepresentationsOfThetaLift and WeightOneGeometricRealization.

### Modularity Window Bridge (VwinOfRow) (`vwin_of_row`)

Converts the strong local-global Galois compatibility theorem Row0b together with isobaric base-change identities into the universal Selmer-growth window bound VWin needed by the analytic character-box machinery.

- **Mathematical form:** `UpperTheory.GalStar.Row0b (IsRecT) ⇒ UpperTheory.Top.VWin`
- **Lean anchor:** `UpperTheory.One.vwin_of_row` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L4](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L4)
- **Depends on:** `Automorphic, Galois & CM Inputs Assembly (TopMainZj)`
- **Notes:** bridge calling automorphic_window_of_inputs with OpenImageCondition.mk h and baseChangeN.

### Automorphic, Galois & CM Inputs Assembly (TopMainZj) (`top_main_zj`)

Packages local GL_n representation theory (LitLocAlt), global automorphy (LiteratureAutomorphyHypothesis), Galois cohomology, and CM abelian variety theorems into LiteratureRankNHypothesis to prove the window bound VWin.

- **Mathematical form:** `OpenImageCondition ∧ BaseChangeIsobaricN ∧ RowT ⇒ LiteratureRankNHypothesis ⇒ VWin`
- **Lean anchor:** `UpperTheory.One.Join.automorphic_window_of_inputs` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/TopMainZj.lean#L71](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/TopMainZj.lean#L71) · Dominates **8,050** modules
- **Depends on:** `Descent-Vanishing Patching Reduction for VWin`, `Poitou-Tate Nine-Term Exact Sequence & Sha Duality`, `Moriwaki Arithmetic Bigness & Hilbert-Samuel Volume Chain`, `Functorial Resolution of Singularities in Characteristic Zero`, `Unitary Admissibility & Flath Tensor Product Factorization`, `Good Root-Tower Existence & Arakelov Volume Theorem`
- **Notes:** Rank 8 dominator (dist=3, height=170). Discharges every field of LiteratureRankNHypothesis except the RowT argument supplied by RowSrc.

### Descent-Vanishing Patching Reduction for VWin (`window_bound_lit`)

Derives the Selmer window bound VWin from LiteratureRankNHypothesis by executing automorphy lifting, descent-vanishing patching (HypothesesH'), Kato's unramified zeta bounds, and unitary U(3) Selmer counting.

- **Mathematical form:** `LiteratureRankNHypothesis ⇒ HypothesesH' ⇒ CountI ∧ CountII ∧ CountIII ∧ CountV ⇒ VWin`
- **Lean anchor:** `UpperTheory.V.v_window_of_literal_automorphy_n` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/WindowBoundOfLiteratureLevel.lean#L33](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/WindowBoundOfLiteratureLevel.lean#L33) · Dominates **7,920** modules
- **Depends on:** `Unitary U(3) Selmer Growth Bound (CorGK → CountI)`, `Kato Euler System & Smoothed Zeta-Class Hodge-Tate Law`, `Weight-One Hilbert Eisenstein Series Construction`, `Local Langlands Correspondence for GL_n with Tame Inertia Types`, `Whittaker Multiplicity One on GL_n(A_K)`, `Rapid Decay & L² Moments of Compactly Supported Cusp-Form Twists`, `Capelli Infinitesimal Character of U(p, q) Discrete Series`
- **Notes:** Rank 9 dominator (dist=4, height=148) linking PublishedHypothesesFromPatching and HVCore.

### Arakelov Self-Intersection & Covolume Bridge (CovolX) (`top_covol_slim2_use`)

Synthesizes resolution of singularities, Moriwaki bigness, Fargues' exact sequence, Zarhin's trick, Nef Riemann-Roch, Scholze-Weinstein, and Fubini-Study Chow heights to establish the global Arakelov covolume bound CovolX.

- **Mathematical form:** `Resolution ∧ MoriwakiBig ∧ FarguesExact ∧ Zarhin ∧ NefRR ∧ ScholzeWeinstein ⇒ GlobalTheory.CovTop.CovolX`
- **Lean anchor:** `topCovolSlim2_use` in [Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/TopCovolSlim2Use.lean#L13](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/TopCovolSlim2Use.lean#L13) · Dominates **6,076** modules
- **Depends on:** `Good Root-Tower Existence & Arakelov Volume Theorem`, `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Rank 10 dominator (dist=7, height=141) connecting TopCovolSlim2 and DeepStR.

### Covolume Lower Bound from Slimness & Height Theorems (`covolume_of_slim`)

Deduces the Arakelov lattice covolume bound CovolX from the Slimness condition and height-pairing hypotheses HypothesesXH by producing the Ch2Const parameter and passing through Moret-Bailly second jets.

- **Mathematical form:** `Slim ∧ HypothesesXH ⇒ CovolX (via exists_ch2Const_of_prints and covolume_of_height)`
- **Lean anchor:** `covolX_of_slim₂` in [Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeOfSlimAndHyp.lean#L22](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeOfSlimAndHyp.lean#L22) · Dominates **5,695** modules
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Rank 11 dominator (dist=6, height=157) wrapping CovolumeOfHeightPrintsStatement and CovolumeOfHeightHyp .

### Small-Class-Number Selmer Length Growth Bound over Q(sqrt(-3)) (`small_class_cor_gk`)

Instantiates LiteratureRankNHypothesis unconditionally and applies the unitary U(3) Selmer patching theorem to Q(sqrt(-3)) (class number 1), yielding an explicit polynomial bound C*(e+1)^A on weighted sums of Shafarevich-Tate lengths.

- **Mathematical form:** `∃ C A ∈ ℕ, ∀ e ≥ 1 even, ∑_{l ∈ Ls} log(l) · length(Sha_U(χ_cyc^{-e})) / e_O ≤ C · (e + 1)^A`
- **Lean anchor:** `corGK` in [Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L25](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L25)
- **Depends on:** `Automorphic, Galois & CM Inputs Assembly (TopMainZj)`, `Strong Local-Global Galois Compatibility from Theta Parseval`, `Unitary U(3) Selmer Growth Bound (CorGK → CountI)`
- **Notes:** Top-level Selmer realization (dist=2, height=198) proved alongside bound (L27).

---

## Stage 3: Major Theory Pillars (13 milestones)

Core mathematical engines: windowed Chebyshev/Landau zero-free regions, weight-one geometric realization and Lefschetz traces, theta-kernel Parseval lifts, Local Langlands with tame types, U(3) Selmer growth, Kato's Euler system, Moriwaki bigness, and Harish-Chandra/Flath representation theory.

### Windowed Chebyshev Inequality from Design Choices (topDesWin) (`top_des_win`)

Transforms admissible finite-family designs (DesignExists) and closed parameter bounds (LinkN, LinkDIVt, LinkG, LinkS, LinkIRR, LinkGLOBAL) into a connected family satisfying the tied Chebyshev inequality on scale windows.

- **Mathematical form:** `DesignExists(WithTw(WithSm 𝒞')) ∧ LinkN ∧ LinkDIVt ∧ LinkG ∧ LinkS ∧ LinkIRR ∧ LinkGLOBAL ⇒ FamilyClassConnected ℰ`
- **Lean anchor:** `topDesWin` in [Development/AutomorphicArithmetic/CharacterBoxes/DesWin.lean#L11](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/DesWin.lean#L11)
- **Depends on:** `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Feeds ShapeWin and EveryCharacter; operates over the FamP parameter family (ParConsts.lean).

### Windowed Landau Nonvanishing Criterion (zeroFreeOn_of_tiedWin_cyc) (`top_win_landau`)

Proves that if for every primitive character ψ the smoothed prime-power sum Gm(x) on its cyclic subgroup level satisfies Gm(x) <= x^{1/2 + O(eps)} along unbounded windows [Y, Y^λ] (λ > 1), then L(ψ, s) ≠ 0 for all Re(s) > 1/2.

- **Mathematical form:** `(∀ ψ, ChebyshevInequalityAtWindowScale λ (Level.cyc ψ)) ∧ (∀ ψ, Λ_ψ.Gm(x) ≤ x^{1/2 + C·ε}) ⇒ ∀ ψ, Re(s) > 1/2 ⇒ L(ψ, s) ≠ 0`
- **Lean anchor:** `zeroFreeOn_of_tiedWin_cyc` in [Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/TopWin.lean#L90](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/TopWin.lean#L90)
- **Depends on:** `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Wraps Landau.zero_free_of_Chebyshev_growth (Landau.lean L538) and ExplicitFormulaErrorOfHostConditions; coupled with CoreGm (CoreGm.lean L12).

### Weight-One Geometric Realization (Crystalline Towers & Kodaira-Spencer) (`geom_real_weight_one`)

Synthesizes crystalline comparison towers, p-adic Witt lattices, finite-etale Kodaira-Spencer models (ksGood_holds), and Hodge-Tate jumps from the holomorphic Lefschetz trace formula to construct the weight-one geometric realization GeoOne.

- **Mathematical form:** `HolomorphicLefschetzFormula ∧ CrysStep ∧ JumpStep ∧ KSGood ⇒ GeoOne`
- **Lean anchor:** `geometric_realization_of_weight_one` in [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean#L25](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean#L25) · Dominates **10,430** modules
- **Depends on:** `Finiteness of Twisted Etale Cohomology Over Fields`, `24-Law Contract for Polarized Abelian Schemes`, `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Rank 6 dominator (dist=6, height=194), immediate child of WeightOneGeometricRealization .

### Holomorphic Lefschetz Fixed-Point Formula for Finite Etale Correspondences (`lefschetz_correspondence`)

Proves the holomorphic Lefschetz fixed-point formula for finite etale correspondences (c1, c2 : Y → Z) on smooth projective schemes over C, equating the alternating trace on Hodge cohomology H^b(Z, Ω^a) to fixed-point tangent-matrix residues.

- **Mathematical form:** `∑_{b=0}^d (-1)^b Tr(Tr_{c₁} ∘ c₂^* | H^b(Z, Ω^a)) = ∑_{y ∈ Fix(c₁, c₂)} [X^a] det(I + X·A_y) / det(I - A_y)`
- **Lean anchor:** `UpperTheory.Cb.lefschetz_fixedPoint_finite_etale_correspondence` in [Development/AutomorphicArithmetic/Foundations/EtaleClopenDescent/LefschetzFixedPointFiniteEtaleCorrespondence.lean#L255](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/EtaleClopenDescent/LefschetzFixedPointFiniteEtaleCorrespondence.lean#L255) · Dominates **351** modules
- **Depends on:** `24-Law Contract for Polarized Abelian Schemes`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`
- **Notes:** complete proof decomposing Z into integral clopen components and reducing via Hodge restriction isomorphisms.

### Theta-Kernel Parseval Lift & Nonvanishing (tLift_holds_k) (`t_lift_k`)

Constructs nonvanishing global unitary theta lifts U → U' from U(n) to large definite/skew unitary spaces U(d) using the regularized Siegel-Weil formula, doubling method, Rallis inner product, and Schwartz-Bruhat test vectors.

- **Mathematical form:** `∀ U ⊂ 𝒜_cusp(U(n)) of regular weight λ, ∀ d ≥ d₀, ∃ U' ⊂ 𝒜(U(d)), IsLift(χ_X, χ_W, U, U')`
- **Lean anchor:** `tLift_holds_k` in [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/ThetaKernels/TPGHolds.lean#L58](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/ThetaKernels/TPGHolds.lean#L58) · Dominates **766** modules
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Assembles tools_holds_k (Siegel-Weil standard, Eisenstein continuation, doubling, unimodularity) to discharge UpperTheory.TP.TLiftK in TLiftK.lean.

### Local Langlands Correspondence for GL_n with Tame Inertia Types (`rec_t_exists`)

Constructs a local reciprocity correspondence rc mapping irreducible smooth representations of GL_n(E_w) to Weil-Deligne representations, extending the supercuspidal correspondence via Bernstein-Zelevinsky segments and verifying dimension, character twists, central characters, duals, injectivity, and depth-zero tame type laws.

- **Mathematical form:** `∀ E_w non-archimedean, ∃ rc : Irr(GL_n(E_w)) → WD(W_{E_w}), LawsT(rc) (bijection, segments, twists, central chars, depth-0 types)`
- **Lean anchor:** `UpperTheory.Zero.LLC.recTExists` in [Development/AutomorphicArithmetic/Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean#L20](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean#L20)
- **Depends on:** `Capelli Infinitesimal Character of U(p, q) Discrete Series`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Combines local Artin map (artEx), supercuspidal correspondence (cuspEx), Zelevinsky extension (exists_isLExt), and depth-zero cuspidality (DzLCusp).

### Unitary U(3) Selmer Growth Bound (CorGK → CountI) (`u3_count_i`)

Converts the global U(3) Selmer growth inequality CorGK over auxiliary imaginary quadratic fields K*(p) into the prime-averaged Selmer length bound CountI across cyclic character orbits.

- **Mathematical form:** `U3.CorGK ⇒ ∀ χ, ∃ A r₁ r₂, ∑_{l ∈ Ls} log(l) · ∑_{ψ ∈ X(c_l, e)} V_n(ψ) ≤ (N·t)^A`
- **Lean anchor:** `UpperTheory.V.U3.countI` in [Development/AutomorphicArithmetic/AutomorphicVarieties/UnitaryThreeGroups/CountI.lean#L22](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/UnitaryThreeGroups/CountI.lean#L22)
- **Depends on:** `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`, `Split Tori & Semiabelian Torsion Primitives (Critical Spine Base)`
- **Notes:** Key Selmer counting step using subgroup orbit decomposition (orbSum) and cyclicity of (Z/NZ)^× / K' inside UnitaryThreeGroups.

### Kato Euler System & Smoothed Zeta-Class Hodge-Tate Law (`zeta_ur`)

Establishes the unramified zeta-element divisibility criterion ZetaUr by combining Kato's Euler-system integrality with the smoothed zeta-class Hodge-Tate law and admissible Hecke projection nonvanishing.

- **Mathematical form:** `KatoEulerSystemIntegrality ∧ SmoothedZetaClassHodgeTateLaw ⇒ GlobalTheory.Ord2.ZetaUr`
- **Lean anchor:** `zetaUr` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean#L9](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean#L9) · Dominates **2,047** modules
- **Depends on:** `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Rank 24 dominator (dist=6, height=121) feeding KatoTwo in WindowBoundOfLiteratureLevel.

### Good Root-Tower Existence & Arakelov Volume Theorem (`good_tower_volume`)

Proves both the existence of good root towers of Shimura models and the Arakelov volume lower bound VolumeTheoremX by combining Arakelov intersection systems, Moriwaki Hilbert-Samuel/bigness, Fargues Hodge-Tate, Zarhin, Bost-Zhang slope vectors, and complex theta uniformisation.

- **Mathematical form:** `ArithIntersectionSystem ∧ MoriwakiHS ∧ MoriwakiBig ∧ FarguesHodgeTate ∧ Zarhin ⇒ GoodTowerExistsX ∧ VolumeTheoremX`
- **Lean anchor:** `good_tower_and_volume_final` in [Development/AutomorphicSpectrum/Proofs/GeometryProofs/GoodTowerVolumeTheoremAlt.lean#L32](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicSpectrum/Proofs/GeometryProofs/GoodTowerVolumeTheoremAlt.lean#L32) · Dominates **3,746** modules
- **Depends on:** `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Rank 19 dominator (dist=11, height=129) wrapping FinalTheoremOfInputsRight and GoodTowerVolumeTheorem .

### Moriwaki Arithmetic Bigness & Hilbert-Samuel Volume Chain (`moriwaki_big`)

Proves Moriwaki's arithmetic bigness criterion unconditionally from resolution of singularities, the Poincare-Lelong formula for Arakelov intersection systems, and dense bounded-height curves via an arithmetic Hilbert-Samuel devissage chain.

- **Mathematical form:** `MoriwakiBigStatement ∧ HSUse (arithmetic volume bigness for nef/semipositive adelic line bundles)`
- **Lean anchor:** `moriwakiBig_outright` in [Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/MoriwakiBigTheorem/Outright.lean#L9](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/MoriwakiBigTheorem/Outright.lean#L9) · Dominates **402** modules
- **Depends on:** `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Instantiates MoriwakiBigStatement and HSUse outright (dist=7, height=100) via HSChain.lean.

### Weight-One Hilbert Eisenstein Series Construction (`hilbert_eis_weight_one`)

Constructs holomorphic Hilbert modular Eisenstein series of parallel weight one over totally real fields, proving Poisson summation, moderate growth, smoothness, K-finiteness, level conditions, and explicit Fourier expansions.

- **Mathematical form:** `UpperTheory.V.Published.HilbertEisOne (existence & Fourier expansions of weight-1 Hilbert Eisenstein series)`
- **Lean anchor:** `UpperTheory.V.Published.hilbert_eisenstein_weight_one_holds` in [PositivityTheory/AutomorphicForms/PublishedInputs/HilbertEisenstein/HilbertEisensteinWeightOneHolds.lean#L19](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/HilbertEisenstein/HilbertEisensteinWeightOneHolds.lean#L19)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Key PositivityTheory realization (dist=7, height=110) used in automorphy-lifting/congruence arguments.

### Capelli Infinitesimal Character of U(p, q) Discrete Series (`discrete_series_inf_char`)

Proves via Casselman-Osborne Lie algebra cohomology, Koszul resolutions, and Verma covers that the quantum determinant in U(gl_n) acts on smooth vectors of any discrete series representation of U(p, q) as the scalar Harish-Chandra polynomial.

- **Mathematical form:** `∀ π ∈ DiscreteSeries(U(p, q)) of parameter λ, ∀ v ∈ π^∞, qdet(E + (n-1)/2 + Y) · v = capP(λ, Y) · v`
- **Lean anchor:** `discrete_series_infinitesimal_character` in [CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L68](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L68)
- **Depends on:** `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** CompanionTheory assembly proving PI.DSInfCharCap.DSInfCharCap .

### Unitary Admissibility & Flath Tensor Product Factorization (`final_b_flath`)

Proves that every irreducible smooth/unitary representation of an adelic unitary group U(J)(A_F) is admissible and decomposes as a restricted tensor product over all archimedean and non-archimedean places.

- **Mathematical form:** `UnitaryIrreducibleAdmissible ∧ FlathTensorProduct (π ≅ ⊗'_v π_v over all places v)`
- **Lean anchor:** `flathTensorProduct` in [CompanionTheory/RealGroups/UnitaryAdmissibility/ArchimedeanUnitaryDual/FinalB.lean#L55](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/CompanionTheory/RealGroups/UnitaryAdmissibility/ArchimedeanUnitaryDual/FinalB.lean#L55)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Proved in CompanionTheory/RealGroups from Hecke algebra commutativity, Witt/Cartan decompositions, and archimedean principal series.

---

## Stage 4: Foundational Machinery (12 milestones)

Underlying arithmetic-geometric, cohomological, and analytic infrastructure: PEL Shimura toroidal compactification and Mumford semiabelian uniformisation, resolution of singularities, twisted etale cohomology finiteness, Poitou-Tate duality, Whittaker multiplicity one, Arakelov slope bounds, and Formalism specification contracts.

### PEL Shimura Toroidal Compactification & Boundary Uniformisation (`uniformisation_conclusion`)

Defines the global PEL-type unitary Shimura toroidal compactification specification PartI: existence of integral toroidal models with split boundary fibers, Mumford semiabelian uniformisation N3, torsion/Weil-pairing isomorphisms, and formal power-series arc lifts N4.

- **Mathematical form:** `PartI : ∀ (E CM) (H) (D), ∃ integral toroidal models Y with SplitFibres, Model.N2, Model.N3 (PELUnif), Model.N4 (formal arcs Spec O'[[X]] → Y)`
- **Lean anchor:** `PartI` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L223](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L223)
- **Depends on:** `Split Tori & Semiabelian Torsion Primitives (Critical Spine Base)`
- **Notes:** #1 most-imported interface file in the entire repository .

### Uniqueness of Mumford Semiabelian Uniformisation (`unif_uniq_st`)

Formulates UnifUniqSt (wrapped in Laws6): any two Mumford degeneration uniformisations of the same polarized semiabelian scheme compatible with rigidified line bundles are canonically isomorphic, preserving O_E-actions, theta sections, and thick-level coordinates.

- **Mathematical form:** `UnifUniqSt : (U, U' uniformisations of G over (R, I) with w_L) ⇒ ∃! isomorphism D ≅ D' compatible with O_E and theta frames`
- **Lean anchor:** `UnifUniqSt` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L17](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L17)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** #2 most-imported external interface file .

### 24-Law Contract for Polarized Abelian Schemes (`global_sections_laws`)

Packages 24 foundational theorems for polarized abelian schemes over arbitrary Noetherian bases: Riemann-Roch section rank n^g, base change, ampleness (n >= 4), Theorem of the Cube and Square, rigidity, Weil pairing nondegeneracy, Mumford theta-group irreducibility, Serre's M-torsion rigidity (M >= 3), and finite-flat quotients.

- **Mathematical form:** `Laws : dim H⁰(A, L^n) = n^g ∧ Ample(n≥4) ∧ Cube ∧ Square ∧ Rigidity ∧ WeilNondeg ∧ ThetaIrred ∧ Serre(M≥3) ∧ Quotient`
- **Lean anchor:** `Laws` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L187](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L187)
- **Depends on:** `Split Tori & Semiabelian Torsion Primitives (Critical Spine Base)`
- **Notes:** contract . Its realization connects to TheoremOfCubeAbelianSchemeOverArbitraryBase (h=97 on the 202-edge critical spine).

### Split Tori & Semiabelian Torsion Primitives (Critical Spine Base) (`split_torus_aff`)

Constructs split algebraic tori Spec(R[X]) as Hopf-algebra group schemes over arbitrary base schemes S, together with character groups, multiplication-by-N maps, and N-torsion subgroup schemes.

- **Mathematical form:** `splitTorus(S, X) = Spec(O_S[X]), G_m(S), mulN : G → G, torsion(G, N) = ker([N] : G → G)`
- **Lean anchor:** `splitTorusAff` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/SplitTori/SplitTorusAff.lean#L27](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/SplitTori/SplitTorusAff.lean#L27)
- **Depends on:** None (foundation)
- **Notes:** Terminal height-0 leaf of the longest 202-edge (203-module) critical spine in the entire DAG.

### Finiteness of Twisted Etale Cohomology Over Fields (`etale_finiteness`)

Proves finiteness of twisted etale cohomology H^n(X, Z/qZ(i)) for proper schemes X over arbitrary fields k (with q invertible in k) by double induction on cohomological degree n and Krull dimension, slicing into families of smooth curves via alterations, Kummer theory, and ghost-killing.

- **Mathematical form:** `∀ k field, q ∈ k^×, X/k proper, ∀ n i ∈ ℤ, Finite(H^n_et(X, Z/qZ(i)))`
- **Lean anchor:** `H0TwistOverClosedField` in [Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L25](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L25)
- **Depends on:** None (foundation)
- **Notes:** Core inductive engine (goal_of) for Development/EtaleCohomology .

### Functorial Resolution of Singularities in Characteristic Zero (`resolution_char_zero`)

Establishes functorial embedded resolution of singularities and ideal principalization over characteristic-zero schemes via iterated blowups along smooth centers, producing strict normal crossings exceptional divisors compatible with smooth morphisms and field extensions.

- **Mathematical form:** `FunctorialResolutionCharZero ⇒ ResolutionCharZero (smooth blowup resolution with SNC exceptional divisor)`
- **Lean anchor:** `resolutionCharZero` in [Development/WeilBound/CoreStatements/ResolutionCharZero/ResolutionCharZero.lean#L6](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/WeilBound/CoreStatements/ResolutionCharZero/ResolutionCharZero.lean#L6)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Bridges Development/ResolutionOfSingularities into Arakelov height and Moriwaki bigness pipelines.

### Poitou-Tate Nine-Term Exact Sequence & Sha Duality (`poitou_tate_gs`)

Proves Poitou-Tate global-local duality for finite Z/NZ Galois modules over G_{K,S} (for N odd or K totally complex): finiteness and perfect pairing of Tate-Shafarevich groups Sha^1 and Sha^2, compact-support duality, and exactness of the full nine-term Poitou-Tate sequence.

- **Mathematical form:** `Finite(Sha¹(G_{K,S}, M)) ∧ Finite(Sha²(G_{K,S}, M*(1))) ∧ Exact(0 → H⁰ → ∏' H⁰ → H²* → ... → ∏' H² → 0)`
- **Lean anchor:** `poitouTate_nineTerm_gs` in [GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L50](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L50)
- **Depends on:** None (foundation)
- **Notes:** Complete proof in GroundTheory/ProfiniteCohomology of poitouTate_duality_gs, poitouTate_sha_gs, and poitouTate_nineTerm_gs.

### Whittaker Multiplicity One on GL_n(A_K) (`multiplicity_one`)

Proves the Piatetski-Shapiro / Shalika Fourier-Whittaker theorem for smooth cuspidal automorphic forms on GL_n(A_K): by upward induction on unipotent row expansions, if all Whittaker coefficients of a cusp form vanish, then the form itself is identically zero.

- **Mathematical form:** `∀ ϕ ∈ 𝒜_cusp(GL_n(K)\GL_n(A_K)), (∀ g, W_ϕ(g) = 0) ⇒ ϕ = 0`
- **Lean anchor:** `eq_zero_of_whittaker_eq_zero` in [GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L77](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L77)
- **Depends on:** None (foundation)
- **Notes:** proof in GroundTheory/AutomorphicForms .

### Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities (`kernels_lattice`)

Defines Hermitian lattices (metrized projective O_K-modules with conjugate-compatible positive-definite inner products at infinite places), Arakelov sub/quotient degrees and slopes, and formalizes the Bost-Zhang small-height vector existence bound.

- **Mathematical form:** `∀ (F : HermLattice K i), ∀ ε > 0, ∃ K'/K finite, ∃ v ∈ F ⊗ K' \ {0}, lineDegree(v) ≥ μ(F) - (1/2)log(i) - ε`
- **Lean anchor:** `HermLattice` in [GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L24](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L24)
- **Depends on:** None (foundation)
- **Notes:** core interface in GroundTheory/HeightsAndTheta .

### Rapid Decay & L² Moments of Compactly Supported Cusp-Form Twists (`pi_vec_ex`)

Proves that multiplying a smooth cusp form invariant under the split center by any compactly supported continuous cutoff of log|det| yields an L² function on H_n with finite moments against all powers of the Siegel height weight.

- **Mathematical form:** `∀ ψ cusp form, ∀ u ∈ C_c(ℝ), ψ(x) · u(ldet x) ∈ L²(H_n, ν) ∧ ∫ wt(x)^{2M} |ψ(x)u(ldet x)|² dν < ∞`
- **Lean anchor:** `piVecEx_holds` in [Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean#L16](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean#L16)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** proof in Development/DiscreteGroups , top interface file of DiscreteGroups.

### Local Bloch-Kato Orthogonality & Tate Duality Core (`loc_coh_bk`)

Specifies continuous p-adic Galois representations GRep, de Rham criteria (dim D_dR = [K:Q_p] dim V), and rational/integral Bloch-Kato exact orthogonality of finite-part cocycles H¹_f under the local Tate cup-product pairing.

- **Mathematical form:** `IsDR(ρ) ⇒ (H¹_f(G_K, V) ⊥ H¹_f(G_K, V*(1))) ∧ (H¹_f(T_A) ⊥ H¹_f(T_{A'})) under local cup product`
- **Lean anchor:** `bkACore` in [Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L154](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L154)
- **Depends on:** None (foundation)
- **Notes:** Highest cross-top-directory boundary bridge .

### Master Arithmetic-Automorphic Coordination Package (D7) (`rho_det_d7`)

Defines self-dual Hermitian lattices, inert-prime indices, and the central 200+ field structure D7 coordinating CM host fields, Shimura spaces, column chains, relative Hermitian determinants, Fontaine period rings, Galois types, and theta jets.

- **Mathematical form:** `structure D7 : (Ranks, Host, Hermitian Spaces, Member Column Chains, DivData, Fontaine Period Rings, Galois Types)`
- **Lean anchor:** `D7` in [Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L76](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L76)
- **Depends on:** None (foundation)
- **Notes:** Central Formalism data contract .

---

## How Literature & Hypothesis Bundles Are Discharged

To understand what is unconditionally proved versus parameterized in intermediate modules:

- Despite directory and structure names such as `PublishedTheorems`, `PublishedInputs`, `LiteratureTheorems`, `OpenLiteratureStatements`, `OpenImageCondition`, and `LiteratureRankNHypothesis`, **direct inspection of the source confirms that these are NOT unproved axioms or uninstantiated assumptions in the final theorems:**
  - In [Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#LMainConclusion.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#LMainConclusion.lean), `UpperTheory.FinalTheorems.everyCharacter` takes **zero external hypothesis arguments** and invokes `everyCharacter_of_row UpperTheory.Gal.Int.galoisLocalGlobalStrong_recParameter`.
  - Inside `everyCharacter_of_row` ([Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#LMainConclusion.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#LMainConclusion.lean)), [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#LOpenLiteratureStatements](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#LOpenLiteratureStatements) (which bundles `caraianiLocalGlobalDual`, `localLanglandsExists`, `galoisRepOfPolarizedPairLit`) is **unconditionally discharged** using `UpperTheory.Zero.LLC.recTExists` and the proved strong local-global compatibility theorem.
  - Likewise, `OpenImageCondition` (`galoisRepOfPolarizedPairLit`) is **unconditionally discharged** in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#LVwinOfRow.lean](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#LVwinOfRow.lean) via `OpenImageCondition.mk h`.
  - All other results packaged inside the synthesis modules (including Moriwaki bigness, characteristic-zero resolution, Poitou-Tate duality, global Artin reciprocity, Bernstein-Zelevinsky finiteness, Jacquet-Shalika rigidity, Casselman-Wallach, Clozel purity, unitary Siegel-Weil, and Grothendieck deformation) are **proved theorems** in `PositivityTheory`, `CompanionTheory`, `Development`, and `GroundTheory`.
  - Similarly, `Formalism` structures (`D7`, `LocCoh`, `FamP`) and `ReciprocityTheory` specifications (`PartI`, `UnifUniqSt`, `Laws`) serve as abstract mathematical interface contracts (`Prop` definitions / `structure`s) whose concrete obligations are fulfilled by proved theorems along the proof chain.

---

## Complete Milestone Index (45 Nodes)

<details>
<summary>Expand full table of all 45 verified blueprint milestones</summary>

| Stage | ID | Title | Lean Symbol | Source Link |
|---:|---|---|---|---|
| 0 | `main_export` | Main Theorems (RH, Half-Plane & GRH) | `riemannHypothesis` | [Main.lean#L4](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Main.lean#L4) |
| 0 | `statements_spec` | Standalone Target Theorem Statements | `RiemannZetaZerosOnLine` | [Statements.lean#L3](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Statements.lean#L3) |
| 0 | `main_theorems_all` | Top-Level Theorem & Selmer Combination | `Supplements.Kernels.MainTheoremsAll` | [Supplements/Kernels/MainTheoremsAll.lean#L1](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsAll.lean#L1) |
| 1 | `main_theorems_critical` | Critical-Line & ℚ(√−3) Arithmetic | `Supplements.Kernels.MainTheoremsCritical` | [Supplements/Kernels/MainTheoremsCritical.lean#L1](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheoremsCritical.lean#L1) |
| 1 | `main_theorems_bridge` | RH & GRH from Half-Plane Nonvanishing | `allChi` | [Supplements/Kernels/MainTheorems.lean#L7](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Supplements/Kernels/MainTheorems.lean#L7) |
| 1 | `crit_line` | Functional-Equation Reflection (Primitive) | `Formalism.VW.critLine` | [Formalism/GammaFactorNonvanishing/CritLine.lean#L11](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/GammaFactorNonvanishing/CritLine.lean#L11) |
| 1 | `rh_of_right` | Zeta Reflection via Functional Equation | `Formalism.VW.rh_of_right` | [Formalism/GammaFactorNonvanishing/RhOfRight.lean#L5](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/GammaFactorNonvanishing/RhOfRight.lean#L5) |
| 1 | `claim_strip` | Imprimitive Character Strip Reduction | `strip` | [Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L59](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L59) |
| 1 | `half_plane_def` | Half-Plane, Strip & Zeta Definitions | `Claim.HalfPlane` | [Development/AutomorphicArithmetic/CharacterBoxes/HalfPlane.lean#L3](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/HalfPlane.lean#L3) |
| 2 | `main_conclusion` | Master Proof Synthesis (UpperTheory.FinalTheorems.everyCharacter) | `UpperTheory.FinalTheorems.everyCharacter` | [Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L10](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L10) |
| 2 | `rh_of_every_char` | 208-Input Operator & Covolume Assembly (RiemannHypothesisOfEveryCharacter) | `UpperTheory.riemannHypothesis_of_everyCharacter` | [Development/AutomorphicArithmetic/CharacterBoxes/RiemannHypothesisOfEveryCharacter.lean#L215](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/RiemannHypothesisOfEveryCharacter.lean#L215) |
| 2 | `every_character_def` | Character-Box Window Assembly (plugWin & plugAll) | `UpperTheory.Top.plugAll` | [Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean#L16](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean#L16) |
| 2 | `every_character_of_lit_vwin` | Theta-Correspondence, Covolume & Literature Package Synthesis | `UpperTheory.LiteratureTheorems.every_character_of_literature_of_vWin` | [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L810](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L810) |
| 2 | `row_src` | Strong Local-Global Galois Compatibility from Theta Parseval | `galoisLocalGlobalStrong_recParameter` | [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/RowSrc.lean#L6](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/RowSrc.lean#L6) |
| 2 | `vwin_of_row` | Modularity Window Bridge (VwinOfRow) | `UpperTheory.One.vwin_of_row` | [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L4](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L4) |
| 2 | `top_main_zj` | Automorphic, Galois & CM Inputs Assembly (TopMainZj) | `UpperTheory.One.Join.automorphic_window_of_inputs` | [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/TopMainZj.lean#L71](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/TopMainZj.lean#L71) |
| 2 | `window_bound_lit` | Descent-Vanishing Patching Reduction for VWin | `UpperTheory.V.v_window_of_literal_automorphy_n` | [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/WindowBoundOfLiteratureLevel.lean#L33](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/WindowBoundOfLiteratureLevel.lean#L33) |
| 2 | `top_covol_slim2_use` | Arakelov Self-Intersection & Covolume Bridge (CovolX) | `topCovolSlim2_use` | [Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/TopCovolSlim2Use.lean#L13](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/TopCovolSlim2Use.lean#L13) |
| 2 | `covolume_of_slim` | Covolume Lower Bound from Slimness & Height Theorems | `covolX_of_slim₂` | [Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeOfSlimAndHyp.lean#L22](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AbelianVarietyTheory/Proofs/DivisorProofs/CovolumeOfSlimAndHyp.lean#L22) |
| 2 | `small_class_cor_gk` | Small-Class-Number Selmer Length Growth Bound over Q(sqrt(-3)) | `corGK` | [Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L25](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/SmallClassNumbers/CorGKOf.lean#L25) |
| 3 | `top_des_win` | Windowed Chebyshev Inequality from Design Choices (topDesWin) | `topDesWin` | [Development/AutomorphicArithmetic/CharacterBoxes/DesWin.lean#L11](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/CharacterBoxes/DesWin.lean#L11) |
| 3 | `top_win_landau` | Windowed Landau Nonvanishing Criterion (zeroFreeOn_of_tiedWin_cyc) | `zeroFreeOn_of_tiedWin_cyc` | [Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/TopWin.lean#L90](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/TopWin.lean#L90) |
| 3 | `geom_real_weight_one` | Weight-One Geometric Realization (Crystalline Towers & Kodaira-Spencer) | `geometric_realization_of_weight_one` | [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean#L25](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean#L25) |
| 3 | `lefschetz_correspondence` | Holomorphic Lefschetz Fixed-Point Formula for Finite Etale Correspondences | `UpperTheory.Cb.lefschetz_fixedPoint_finite_etale_correspondence` | [Development/AutomorphicArithmetic/Foundations/EtaleClopenDescent/LefschetzFixedPointFiniteEtaleCorrespondence.lean#L255](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/EtaleClopenDescent/LefschetzFixedPointFiniteEtaleCorrespondence.lean#L255) |
| 3 | `t_lift_k` | Theta-Kernel Parseval Lift & Nonvanishing (tLift_holds_k) | `tLift_holds_k` | [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/ThetaKernels/TPGHolds.lean#L58](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/ThetaKernels/TPGHolds.lean#L58) |
| 3 | `rec_t_exists` | Local Langlands Correspondence for GL_n with Tame Inertia Types | `UpperTheory.Zero.LLC.recTExists` | [Development/AutomorphicArithmetic/Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean#L20](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean#L20) |
| 3 | `u3_count_i` | Unitary U(3) Selmer Growth Bound (CorGK → CountI) | `UpperTheory.V.U3.countI` | [Development/AutomorphicArithmetic/AutomorphicVarieties/UnitaryThreeGroups/CountI.lean#L22](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/UnitaryThreeGroups/CountI.lean#L22) |
| 3 | `zeta_ur` | Kato Euler System & Smoothed Zeta-Class Hodge-Tate Law | `zetaUr` | [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean#L9](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean#L9) |
| 3 | `good_tower_volume` | Good Root-Tower Existence & Arakelov Volume Theorem | `good_tower_and_volume_final` | [Development/AutomorphicSpectrum/Proofs/GeometryProofs/GoodTowerVolumeTheoremAlt.lean#L32](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/AutomorphicSpectrum/Proofs/GeometryProofs/GoodTowerVolumeTheoremAlt.lean#L32) |
| 3 | `moriwaki_big` | Moriwaki Arithmetic Bigness & Hilbert-Samuel Volume Chain | `moriwakiBig_outright` | [Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/MoriwakiBigTheorem/Outright.lean#L9](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/MoriwakiBigTheorem/Outright.lean#L9) |
| 3 | `hilbert_eis_weight_one` | Weight-One Hilbert Eisenstein Series Construction | `UpperTheory.V.Published.hilbert_eisenstein_weight_one_holds` | [PositivityTheory/AutomorphicForms/PublishedInputs/HilbertEisenstein/HilbertEisensteinWeightOneHolds.lean#L19](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/PositivityTheory/AutomorphicForms/PublishedInputs/HilbertEisenstein/HilbertEisensteinWeightOneHolds.lean#L19) |
| 3 | `discrete_series_inf_char` | Capelli Infinitesimal Character of U(p, q) Discrete Series | `discrete_series_infinitesimal_character` | [CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L68](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L68) |
| 3 | `final_b_flath` | Unitary Admissibility & Flath Tensor Product Factorization | `flathTensorProduct` | [CompanionTheory/RealGroups/UnitaryAdmissibility/ArchimedeanUnitaryDual/FinalB.lean#L55](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/CompanionTheory/RealGroups/UnitaryAdmissibility/ArchimedeanUnitaryDual/FinalB.lean#L55) |
| 4 | `uniformisation_conclusion` | PEL Shimura Toroidal Compactification & Boundary Uniformisation | `PartI` | [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L223](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L223) |
| 4 | `unif_uniq_st` | Uniqueness of Mumford Semiabelian Uniformisation | `UnifUniqSt` | [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L17](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L17) |
| 4 | `global_sections_laws` | 24-Law Contract for Polarized Abelian Schemes | `Laws` | [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L187](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L187) |
| 4 | `split_torus_aff` | Split Tori & Semiabelian Torsion Primitives (Critical Spine Base) | `splitTorusAff` | [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/SplitTori/SplitTorusAff.lean#L27](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/SplitTori/SplitTorusAff.lean#L27) |
| 4 | `etale_finiteness` | Finiteness of Twisted Etale Cohomology Over Fields | `H0TwistOverClosedField` | [Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L25](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L25) |
| 4 | `resolution_char_zero` | Functorial Resolution of Singularities in Characteristic Zero | `resolutionCharZero` | [Development/WeilBound/CoreStatements/ResolutionCharZero/ResolutionCharZero.lean#L6](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/WeilBound/CoreStatements/ResolutionCharZero/ResolutionCharZero.lean#L6) |
| 4 | `poitou_tate_gs` | Poitou-Tate Nine-Term Exact Sequence & Sha Duality | `poitouTate_nineTerm_gs` | [GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L50](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L50) |
| 4 | `multiplicity_one` | Whittaker Multiplicity One on GL_n(A_K) | `eq_zero_of_whittaker_eq_zero` | [GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L77](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L77) |
| 4 | `kernels_lattice` | Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities | `HermLattice` | [GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L24](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L24) |
| 4 | `pi_vec_ex` | Rapid Decay & L² Moments of Compactly Supported Cusp-Form Twists | `piVecEx_holds` | [Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean#L16](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean#L16) |
| 4 | `loc_coh_bk` | Local Bloch-Kato Orthogonality & Tate Duality Core | `bkACore` | [Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L154](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L154) |
| 4 | `rho_det_d7` | Master Arithmetic-Automorphic Coordination Package (D7) | `D7` | [Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L76](https://github.com/ZacharyVernec/riemann-proof-explorer/blob/main/lean/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L76) |

</details>

