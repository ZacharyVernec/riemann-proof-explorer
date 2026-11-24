# Formalized Proof Blueprint: Riemann Hypothesis & Generalized Riemann Hypothesis (`community-307cef33`)

This blueprint distills the Lean proof DAG (**59,836 reachable modules**, **16,014,995 lines**, **367,774 internal dependency edges**) into **38 mathematical milestones** across **5 architectural stages** (Stages 0–4) connected by **109 dependency links** (interactive DAG in [blueprint.html](blueprint.html)).

> **Direction Convention:** Stage 0 sits at the apex (`Main.lean`); arrows `A → B` mean milestone `A` depends directly on prerequisite `B`.

---

## Stage 0: Final Theorems (2 milestones)

Standalone target statements and top-level proved theorems for the Riemann Hypothesis, Dirichlet L-function half-plane nonvanishing, and Generalized Riemann Hypothesis.

### Main Theorems (RH, Half-Plane & GRH) (`main_export`)

- **Statement:** Unconditionally establishes the Riemann Hypothesis for ζ(s), nonvanishing of every Dirichlet L-function L(χ, s) on the open half-plane Re(s) > 1/2 (away from the pole at s = 1), and the Generalized Riemann Hypothesis for both arbitrary and primitive Dirichlet characters.
- **Assumptions:** None — all five headline theorems are completely unconditional.
- **Proof strategy:** Directly matches the proved theorems produced by the Stage 1 analytic reductions to the standalone target statements, introducing no new assumptions.
- **Lean anchor:** `riemannHypothesis` in [Main.lean#L46](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Main.lean#L46) · Dominates **59,836** modules
- **Depends on:** `Standalone Target Theorem Statements`, `Small-Class-Number Selmer Length Growth Bound over Q(sqrt(-3))`, `Imprimitive Character Strip Reduction`, `Master Proof Synthesis (UpperTheory.FinalTheorems.everyCharacter)`, `Character-Box Window Assembly (plugWin & plugAll)`
- **Notes:** Root module (dist=0, height=202). Exports riemannHypothesis (L4), riemannZeta_eq_zero_re (L6), LFunction_ne_zero_of_half_lt_re (L8), LFunction_eq_zero_re (L10), and LFunction_eq_zero_re_of_isPrimitive (L12).

### Standalone Target Theorem Statements (`statements_spec`)

- **Statement:** Formulates the four target propositions — critical-line zeros of ζ(s), half-plane nonvanishing of L(χ, s) on Re(s) > 1/2, and GRH for arbitrary and primitive characters — using only standard complex-analytic definitions.
- **Assumptions:** None — this milestone states definitions only and proves or assumes no theorems.
- **Proof strategy:** Contains no proof; isolates the exact mathematical claims from the proof machinery so a reader can verify what is being proved independently of how it is proved.
- **Lean anchor:** `RiemannZetaZerosOnLine` in [Statements.lean#L7](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Statements.lean#L7)
- **Depends on:** None (foundation)
- **Notes:** pure specification leaf depending only on Mathlib (dist=1, height=0).

---

## Stage 1: Functional-Equation & Character Reductions (2 milestones)

Analytic bridges reducing critical-line zero localization for ζ(s) and arbitrary/primitive Dirichlet L-functions to half-plane nonvanishing Re(s) > 1/2 via Euler factors, Gamma factors, and functional equations.

### Imprimitive Character Strip Reduction (`claim_strip`)

- **Statement:** Shows that right half-plane nonvanishing for all Dirichlet L-functions implies GRH for every character χ modulo N (including imprimitive ones) as well as the classical Riemann Hypothesis for ζ(s).
- **Assumptions:** Assumes L(χ, s) ≠ 0 for all N ≥ 1, all χ mod N, and all Re(s) > 1/2 (away from s = 1 when χ = 1), plus the classical fact that ζ(s) ≠ 0 for Re(s) ≥ 1.
- **Proof strategy:** Factors L(χ, s) = L(ψ, s) ∏_{p | N} (1 − ψ(p)p^{−s}) via the inducing primitive character ψ; since |ψ(p)p^{−s}| < 1 for Re(s) > 0, no Euler factor vanishes, reducing to a zero of L(ψ, s) which reflects across s ↦ 1 − s into Re > 1/2.
- **Lean anchor:** `strip` in [Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L86](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/ClaimStrip.lean#L86)
- **Depends on:** `Half-Plane, Strip & Zeta Definitions`
- **Notes:** Also proves Claim.zeta (L75) and Claim.zeta_iff (L102).

### Half-Plane, Strip & Zeta Definitions (`half_plane_def`)

- **Statement:** Defines the three core analytic propositions linked by Stage 1: right half-plane nonvanishing for all Dirichlet L-functions, critical-strip localization (GRH) for all characters, and the Riemann Hypothesis for ζ(s).
- **Assumptions:** None — pure definitions using standard complex analysis and Dirichlet L-functions.
- **Proof strategy:** Contains no proof; establishes the clean interface separating the deep Stage 2–4 proof of nonvanishing on Re(s) > 1/2 from the elementary Stage 1 reflection arguments.
- **Lean anchor:** `Claim.HalfPlane` in [Development/AutomorphicArithmetic/CharacterBoxes/HalfPlane.lean#L9](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/HalfPlane.lean#L9)
- **Depends on:** None (foundation)
- **Notes:** Mathlib leaf file defining Claim.HalfPlane, Claim.Strip, and Claim.Zeta.

---

## Stage 2: Main Bridge Theorems & Dominators (10 milestones)

High-impact assembly bottlenecks merging local-global Galois representations, modularity/Selmer windows, theta-correspondence lifts, and Arakelov covolume bounds.

### Master Proof Synthesis (UpperTheory.FinalTheorems.everyCharacter) (`main_conclusion`)

Unconditionally proves half-plane nonvanishing for every Dirichlet L-function by feeding the proved strong local-global Galois compatibility theorem and Local Langlands reciprocity existence into both the modularity-Selmer window theorem (VWin) and the theta-correspondence main theorem.

- **Mathematical form:** `UpperTheory.FinalTheorems.everyCharacter : ∀ N ≥ 1, ∀ χ mod N, ∀ s ∈ ℂ, Re(s) > 1/2 ∧ (χ ≠ 1 ∨ s ≠ 1) ⇒ L(χ, s) ≠ 0`
- **Lean anchor:** `UpperTheory.FinalTheorems.everyCharacter` in [Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L994](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L994) · Dominates **59,831** modules
- **Depends on:** `Theta-Correspondence, Covolume & Literature Package Synthesis`, `Modularity Window Bridge (VwinOfRow)`, `Local Langlands Correspondence for GL_n with Tame Inertia Types`, `Strong Local-Global Galois Compatibility from Theta Parseval`, `Character-Box Window Assembly (plugWin & plugAll)`, `Covolume Lower Bound from Slimness & Height Theorems`
- **Notes:** apex inside Development (dist=4, height=198). Discharges OpenLiteratureStatements via ⟨row_src, rec_t_exists, row_src⟩ and OpenImageCondition via ⟨row_src⟩.

### Character-Box Window Assembly (plugWin & plugAll) (`every_character_def`)

Combines the Green prime-character condition, the Selmer growth window bound VWin (for threshold exponent 401), and the family-design theorem TopShape to establish nonvanishing of all primitive and imprimitive Dirichlet L-functions in Re(s) > 1/2.

- **Mathematical form:** `Green ∧ VWin ∧ Nonempty(Hyps LinkN DRS) ⇒ ZeroFreeAll ⇒ EveryCharacter`
- **Lean anchor:** `UpperTheory.EveryCharacter` in [Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean#L8](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/EveryCharacter.lean#L8)
- **Depends on:** `Windowed Chebyshev Inequality from Design Choices (topDesWin)`, `Windowed Landau Nonvanishing Criterion (zeroFreeOn_of_tiedWin_cyc)`
- **Notes:** bridge connecting ShapeOf, ShapeWin, SupplyChi, and Imprimitive to ZeroFreeAll.

### Theta-Correspondence, Covolume & Literature Package Synthesis (`every_character_of_lit_vwin`)

Assembles over 70 proved theorems across harmonic analysis, unitary Siegel-Weil, Galois cohomology, and Arakelov geometry, feeding Moriwaki bigness and resolution into TopCovolSlim2Use and combining with definite-side theta lifts and VWin to prove EveryCharacter.

- **Mathematical form:** `OpenLiteratureStatements ∧ VWin ⇒ EveryCharacter (instantiating CovolX via topCovolSlim2_use_alt_alt and definite-side theta lifts)`
- **Lean anchor:** `UpperTheory.LiteratureTheorems.every_character_of_literature_of_vWin` in [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L1500](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L1500) · Dominates **31,637** modules
- **Depends on:** `Arakelov Self-Intersection & Covolume Bridge (CovolX)`, `Moriwaki Arithmetic Bigness & Hilbert-Samuel Volume Chain`, `Functorial Resolution of Singularities in Characteristic Zero`, `Poitou-Tate Nine-Term Exact Sequence & Sha Duality`, `Whittaker Multiplicity One on GL_n(A_K)`, `Capelli Infinitesimal Character of U(p, q) Discrete Series`, `Unitary U(3) Selmer Growth Bound (CorGK → CountI)`, `Character-Box Window Assembly (plugWin & plugAll)`, `Covolume Lower Bound from Slimness & Height Theorems`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** synthesis hub (dist=5, height=171, out_degree=201). All but 3 fields of OpenLiteratureStatements are unconditionally proved theorems imported from PositivityTheory/CompanionTheory/GroundTheory/Development; the 3 fields are discharged in MainConclusion.

### Strong Local-Global Galois Compatibility from Theta Parseval (`row_src`)

Establishes strong local-global compatibility (Row0b recT) for l-adic Galois representations attached to polarized regular algebraic cuspidal automorphic representations by feeding the theta-kernel Parseval lift (TLiftK) and weight-one geometric realization (GeoOne) into the Galois representation construction.

- **Mathematical form:** `UpperTheory.GalStar.Row0b recT (l-adic Frobenius-Satake matching away from l and potentially semistable Weil-Deligne compatibility above l)`
- **Lean anchor:** `galoisLocalGlobalStrong_recParameter` in [Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L973](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L973)
- **Depends on:** `Weight-One Geometric Realization (Crystalline Towers & Kodaira-Spencer)`, `Holomorphic Lefschetz Fixed-Point Formula for Finite Etale Correspondences`, `Theta-Kernel Parseval Lift & Nonvanishing (tLift_holds_k)`, `Local Langlands Correspondence for GL_n with Tame Inertia Types`, `Rapid Decay & L² Moments of Compactly Supported Cusp-Form Twists`, `Capelli Infinitesimal Character of U(p, q) Discrete Series`, `Whittaker Multiplicity One on GL_n(A_K)`
- **Notes:** Rank 3 overall dominator (dist=3, height=197) via GaloisRepresentationsOfThetaLift and WeightOneGeometricRealization. [Relocated from RowSrc.lean to Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean] [Shares module MainConclusion.lean]

### Modularity Window Bridge (VwinOfRow) (`vwin_of_row`)

Converts the strong local-global Galois compatibility theorem Row0b together with isobaric base-change identities into the universal Selmer-growth window bound VWin needed by the analytic character-box machinery.

- **Mathematical form:** `UpperTheory.GalStar.Row0b (IsRecT) ⇒ UpperTheory.Top.VWin`
- **Lean anchor:** `UpperTheory.One.vwin_of_row` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L1644](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L1644) · Dominates **4,455** modules
- **Depends on:** `Automorphic, Galois & CM Inputs Assembly (TopMainZj)`
- **Notes:** bridge calling automorphic_window_of_inputs with OpenImageCondition.mk h and baseChangeN.

### Automorphic, Galois & CM Inputs Assembly (TopMainZj) (`top_main_zj`)

Packages local GL_n representation theory (LitLocAlt), global automorphy (LiteratureAutomorphyHypothesis), Galois cohomology, and CM abelian variety theorems into LiteratureRankNHypothesis to prove the window bound VWin.

- **Mathematical form:** `OpenImageCondition ∧ BaseChangeIsobaricN ∧ RowT ⇒ LiteratureRankNHypothesis ⇒ VWin`
- **Lean anchor:** `UpperTheory.One.Join.automorphic_window_of_inputs` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L1627](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L1627)
- **Depends on:** `Descent-Vanishing Patching Reduction for VWin`, `Poitou-Tate Nine-Term Exact Sequence & Sha Duality`, `Moriwaki Arithmetic Bigness & Hilbert-Samuel Volume Chain`, `Functorial Resolution of Singularities in Characteristic Zero`, `Good Root-Tower Existence & Arakelov Volume Theorem`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Rank 8 dominator (dist=3, height=170). Discharges every field of LiteratureRankNHypothesis except the RowT argument supplied by RowSrc. [Relocated from TopMainZj.lean to Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean] [Shares module VwinOfRow.lean]

### Descent-Vanishing Patching Reduction for VWin (`window_bound_lit`)

Derives the Selmer window bound VWin from LiteratureRankNHypothesis by executing automorphy lifting, descent-vanishing patching (HypothesesH'), Kato's unramified zeta bounds, and unitary U(3) Selmer counting.

- **Mathematical form:** `LiteratureRankNHypothesis ⇒ HypothesesH' ⇒ CountI ∧ CountII ∧ CountIII ∧ CountV ⇒ VWin`
- **Lean anchor:** `v_window_of_automorphy_csd_ss_mono_odd` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L1553](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean#L1553)
- **Depends on:** `Unitary U(3) Selmer Growth Bound (CorGK → CountI)`, `Kato Euler System & Smoothed Zeta-Class Hodge-Tate Law`, `Weight-One Hilbert Eisenstein Series Construction`, `Local Langlands Correspondence for GL_n with Tame Inertia Types`, `Whittaker Multiplicity One on GL_n(A_K)`, `Rapid Decay & L² Moments of Compactly Supported Cusp-Form Twists`, `Capelli Infinitesimal Character of U(p, q) Discrete Series`
- **Notes:** Rank 9 dominator (dist=4, height=148) linking PublishedHypothesesFromPatching and HVCore. [Relocated from WindowBoundOfLiteratureLevel.lean to Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/VwinOfRow.lean] [Shares module VwinOfRow.lean]

### Arakelov Self-Intersection & Covolume Bridge (CovolX) (`top_covol_slim2_use`)

Synthesizes resolution of singularities, Moriwaki bigness, Fargues' exact sequence, Zarhin's trick, Nef Riemann-Roch, Scholze-Weinstein, and Fubini-Study Chow heights to establish the global Arakelov covolume bound CovolX.

- **Mathematical form:** `Resolution ∧ MoriwakiBig ∧ FarguesExact ∧ Zarhin ∧ NefRR ∧ ScholzeWeinstein ⇒ GlobalTheory.CovTop.CovolX`
- **Lean anchor:** `topCovolSlim2_use_alt_alt` in [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolSlim2Use.lean#L957](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolSlim2Use.lean#L957) · Dominates **3,679** modules
- **Depends on:** `Good Root-Tower Existence & Arakelov Volume Theorem`, `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Rank 10 dominator (dist=7, height=141) connecting TopCovolSlim2 and DeepStR. [Relocated from TopCovolSlim2Use.lean to Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolSlim2Use.lean]

### Covolume Lower Bound from Slimness & Height Theorems (`covolume_of_slim`)

Deduces the Arakelov lattice covolume bound CovolX from the Slimness condition and height-pairing hypotheses HypothesesXH by producing the Ch2Const parameter and passing through Moret-Bailly second jets.

- **Mathematical form:** `Slim ∧ HypothesesXH ⇒ CovolX (via exists_ch2Const_of_prints and covolume_of_height)`
- **Lean anchor:** `covolX_of_lift_bounds_and_coreLe` in [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolG.lean#L904](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolG.lean#L904) · Dominates **744** modules
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Rank 11 dominator (dist=6, height=157) wrapping CovolumeOfHeightPrintsStatement and CovolumeOfHeightHyp . [Relocated from CovolumeOfSlimAndHyp.lean to Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopCovolG.lean]

### Small-Class-Number Selmer Length Growth Bound over Q(sqrt(-3)) (`small_class_cor_gk`)

Instantiates LiteratureRankNHypothesis unconditionally and applies the unitary U(3) Selmer patching theorem to Q(sqrt(-3)) (class number 1), yielding an explicit polynomial bound C*(e+1)^A on weighted sums of Shafarevich-Tate lengths.

- **Mathematical form:** `∃ C A ∈ ℕ, ∀ e ≥ 1 even, ∑_{l ∈ Ls} log(l) · length(Sha_U(χ_cyc^{-e})) / e_O ≤ C · (e + 1)^A`
- **Lean anchor:** `UpperTheory.V.U3.corGK` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/LinkedUnlE.lean#L1196](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/LinkedUnlE.lean#L1196) · Dominates **85** modules
- **Depends on:** `Automorphic, Galois & CM Inputs Assembly (TopMainZj)`, `Strong Local-Global Galois Compatibility from Theta Parseval`, `Unitary U(3) Selmer Growth Bound (CorGK → CountI)`
- **Notes:** Top-level Selmer realization (dist=2, height=198) proved alongside bound (L27). [Relocated from CorGKOf.lean to Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/LinkedUnlE.lean]

---

## Stage 3: Major Theory Pillars (12 milestones)

Core mathematical engines: windowed Chebyshev/Landau zero-free regions, weight-one geometric realization and Lefschetz traces, theta-kernel Parseval lifts, Local Langlands with tame types, U(3) Selmer growth, Kato's Euler system, Moriwaki bigness, and Harish-Chandra/Flath representation theory.

### Windowed Chebyshev Inequality from Design Choices (topDesWin) (`top_des_win`)

Transforms admissible finite-family designs (DesignExists) and closed parameter bounds (LinkN, LinkDIVt, LinkG, LinkS, LinkIRR, LinkGLOBAL) into a connected family satisfying the tied Chebyshev inequality on scale windows.

- **Mathematical form:** `DesignExists(WithTw(WithSm 𝒞')) ∧ LinkN ∧ LinkDIVt ∧ LinkG ∧ LinkS ∧ LinkIRR ∧ LinkGLOBAL ⇒ FamilyClassConnected ℰ`
- **Lean anchor:** `topDesWin` in [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopShape.lean#L177](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopShape.lean#L177) · Dominates **225** modules
- **Depends on:** `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Feeds ShapeWin and EveryCharacter; operates over the FamP parameter family (ParConsts.lean). [Relocated from DesWin.lean to Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/TopShape.lean]

### Windowed Landau Nonvanishing Criterion (zeroFreeOn_of_tiedWin_cyc) (`top_win_landau`)

Proves that if for every primitive character ψ the smoothed prime-power sum Gm(x) on its cyclic subgroup level satisfies Gm(x) <= x^{1/2 + O(eps)} along unbounded windows [Y, Y^λ] (λ > 1), then L(ψ, s) ≠ 0 for all Re(s) > 1/2.

- **Mathematical form:** `(∀ ψ, ChebyshevInequalityAtWindowScale λ (Level.cyc ψ)) ∧ (∀ ψ, Λ_ψ.Gm(x) ≤ x^{1/2 + C·ε}) ⇒ ∀ ψ, Re(s) > 1/2 ⇒ L(ψ, s) ≠ 0`
- **Lean anchor:** `zeroFreeOn_of_tiedWin_cyc` in [Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/TopWin.lean#L103](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/SharpRestriction/RamificationFrobenius/TotientGaloisClasses/TopWin.lean#L103)
- **Depends on:** `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Wraps Landau.zero_free_of_Chebyshev_growth (Landau.lean L538) and ExplicitFormulaErrorOfHostConditions; coupled with CoreGm (CoreGm.lean L12).

### Weight-One Geometric Realization (Crystalline Towers & Kodaira-Spencer) (`geom_real_weight_one`)

Synthesizes crystalline comparison towers, p-adic Witt lattices, finite-etale Kodaira-Spencer models (ksGood_holds), and Hodge-Tate jumps from the holomorphic Lefschetz trace formula to construct the weight-one geometric realization GeoOne.

- **Mathematical form:** `HolomorphicLefschetzFormula ∧ CrysStep ∧ JumpStep ∧ KSGood ⇒ GeoOne`
- **Lean anchor:** `geometric_realization_of_weight_one` in [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean#L1247](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/IntegralStructures/GeometricFlagBases/GeometricRealizationOfWeightOne.lean#L1247) · Dominates **3,153** modules
- **Depends on:** `Finiteness of Twisted Etale Cohomology Over Fields`, `24-Law Contract for Polarized Abelian Schemes`, `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Rank 6 dominator (dist=6, height=194), immediate child of WeightOneGeometricRealization .

### Holomorphic Lefschetz Fixed-Point Formula for Finite Etale Correspondences (`lefschetz_correspondence`)

Proves the holomorphic Lefschetz fixed-point formula for finite etale correspondences (c1, c2 : Y → Z) on smooth projective schemes over C, equating the alternating trace on Hodge cohomology H^b(Z, Ω^a) to fixed-point tangent-matrix residues.

- **Mathematical form:** `∑_{b=0}^d (-1)^b Tr(Tr_{c₁} ∘ c₂^* | H^b(Z, Ω^a)) = ∑_{y ∈ Fix(c₁, c₂)} [X^a] det(I + X·A_y) / det(I - A_y)`
- **Lean anchor:** `UpperTheory.Cb.lefschetz_fixedPoint_finite_etale_correspondence` in [Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L826](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean#L826)
- **Depends on:** `24-Law Contract for Polarized Abelian Schemes`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`
- **Notes:** complete proof decomposing Z into integral clopen components and reducing via Hodge restriction isomorphisms. [Relocated from LefschetzFixedPointFiniteEtaleCorrespondence.lean to Development/AutomorphicArithmetic/CharacterBoxes/MainConclusion.lean] [Shares module MainConclusion.lean]

### Theta-Kernel Parseval Lift & Nonvanishing (tLift_holds_k) (`t_lift_k`)

Constructs nonvanishing global unitary theta lifts U → U' from U(n) to large definite/skew unitary spaces U(d) using the regularized Siegel-Weil formula, doubling method, Rallis inner product, and Schwartz-Bruhat test vectors.

- **Mathematical form:** `∀ U ⊂ 𝒜_cusp(U(n)) of regular weight λ, ∀ d ≥ d₀, ∃ U' ⊂ 𝒜(U(d)), IsLift(χ_X, χ_W, U, U')`
- **Lean anchor:** `tLift_holds_k` in [Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/ThetaKernels/TPGHolds.lean#L1577](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/GaloisRepresentations/ThetaParseval/ThetaKernels/TPGHolds.lean#L1577) · Dominates **37** modules
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Assembles tools_holds_k (Siegel-Weil standard, Eisenstein continuation, doubling, unimodularity) to discharge UpperTheory.TP.TLiftK in TLiftK.lean.

### Local Langlands Correspondence for GL_n with Tame Inertia Types (`rec_t_exists`)

Constructs a local reciprocity correspondence rc mapping irreducible smooth representations of GL_n(E_w) to Weil-Deligne representations, extending the supercuspidal correspondence via Bernstein-Zelevinsky segments and verifying dimension, character twists, central characters, duals, injectivity, and depth-zero tame type laws.

- **Mathematical form:** `∀ E_w non-archimedean, ∃ rc : Irr(GL_n(E_w)) → WD(W_{E_w}), LawsT(rc) (bijection, segments, twists, central chars, depth-0 types)`
- **Lean anchor:** `UpperTheory.Zero.LLC.recTExists` in [Development/AutomorphicArithmetic/Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean#L1398](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/Foundations/LocalLanglands/LocalCentralUnits/RecTExists.lean#L1398) · Dominates **10** modules
- **Depends on:** `Capelli Infinitesimal Character of U(p, q) Discrete Series`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Combines local Artin map (artEx), supercuspidal correspondence (cuspEx), Zelevinsky extension (exists_isLExt), and depth-zero cuspidality (DzLCusp).

### Unitary U(3) Selmer Growth Bound (CorGK → CountI) (`u3_count_i`)

Converts the global U(3) Selmer growth inequality CorGK over auxiliary imaginary quadratic fields K*(p) into the prime-averaged Selmer length bound CountI across cyclic character orbits.

- **Mathematical form:** `U3.CorGK ⇒ ∀ χ, ∃ A r₁ r₂, ∑_{l ∈ Ls} log(l) · ∑_{ψ ∈ X(c_l, e)} V_n(ψ) ≤ (N·t)^A`
- **Lean anchor:** `UpperTheory.V.U3.countI` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/LinkedUnlE.lean#L1411](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/LinkedUnlE.lean#L1411)
- **Depends on:** `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`, `Split Tori & Semiabelian Torsion Primitives (Critical Spine Base)`
- **Notes:** Key Selmer counting step using subgroup orbit decomposition (orbSum) and cyclicity of (Z/NZ)^× / K' inside UnitaryThreeGroups. [Relocated from CountI.lean to Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/ThresholdArguments/DenseThresholdCases/LinkedUnlE.lean] [Shares module LinkedUnlE.lean]

### Kato Euler System & Smoothed Zeta-Class Hodge-Tate Law (`zeta_ur`)

Establishes the unramified zeta-element divisibility criterion ZetaUr by combining Kato's Euler-system integrality with the smoothed zeta-class Hodge-Tate law and admissible Hecke projection nonvanishing.

- **Mathematical form:** `KatoEulerSystemIntegrality ∧ SmoothedZetaClassHodgeTateLaw ⇒ GlobalTheory.Ord2.ZetaUr`
- **Lean anchor:** `zetaUr` in [Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean#L1738](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/AutomorphicVarieties/ModularityArgument/KatoQuadraticCharacters/UnramifiedZeta/ZetaUr.lean#L1738) · Dominates **558** modules
- **Depends on:** `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Rank 24 dominator (dist=6, height=121) feeding KatoTwo in WindowBoundOfLiteratureLevel.

### Good Root-Tower Existence & Arakelov Volume Theorem (`good_tower_volume`)

Proves both the existence of good root towers of Shimura models and the Arakelov volume lower bound VolumeTheoremX by combining Arakelov intersection systems, Moriwaki Hilbert-Samuel/bigness, Fargues Hodge-Tate, Zarhin, Bost-Zhang slope vectors, and complex theta uniformisation.

- **Mathematical form:** `ArithIntersectionSystem ∧ MoriwakiHS ∧ MoriwakiBig ∧ FarguesHodgeTate ∧ Zarhin ⇒ GoodTowerExistsX ∧ VolumeTheoremX`
- **Lean anchor:** `good_tower_volume_theorem_bis` in [Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/GoodTowerVolumeTheoremBis.lean#L1350](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/GoodTowerVolumeTheoremBis.lean#L1350) · Dominates **1,409** modules
- **Depends on:** `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `Uniqueness of Mumford Semiabelian Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Rank 19 dominator (dist=11, height=129) wrapping FinalTheoremOfInputsRight and GoodTowerVolumeTheorem . [Relocated from GoodTowerVolumeTheoremAlt.lean to Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/HilbertSamuelApplications/GoodTowerVolumeTheoremBis.lean]

### Moriwaki Arithmetic Bigness & Hilbert-Samuel Volume Chain (`moriwaki_big`)

Proves Moriwaki's arithmetic bigness criterion unconditionally from resolution of singularities, the Poincare-Lelong formula for Arakelov intersection systems, and dense bounded-height curves via an arithmetic Hilbert-Samuel devissage chain.

- **Mathematical form:** `MoriwakiBigStatement ∧ HSUse (arithmetic volume bigness for nef/semipositive adelic line bundles)`
- **Lean anchor:** `moriwakiBig_outright` in [Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/MoriwakiBigTheorem/Outright.lean#L1707](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/WeilBound/CoreStatements/AutomorphicKernels/MoriwakiBigness/MoriwakiBigTheorem/Outright.lean#L1707) · Dominates **294** modules
- **Depends on:** `Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities`, `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Instantiates MoriwakiBigStatement and HSUse outright (dist=7, height=100) via HSChain.lean.

### Weight-One Hilbert Eisenstein Series Construction (`hilbert_eis_weight_one`)

Constructs holomorphic Hilbert modular Eisenstein series of parallel weight one over totally real fields, proving Poisson summation, moderate growth, smoothness, K-finiteness, level conditions, and explicit Fourier expansions.

- **Mathematical form:** `UpperTheory.V.Published.HilbertEisOne (existence & Fourier expansions of weight-1 Hilbert Eisenstein series)`
- **Lean anchor:** `UpperTheory.V.Published.hilbert_eisenstein_weight_one_holds` in [PositivityTheory/AutomorphicForms/PublishedInputs/HilbertEisenstein/HilbertEisensteinWeightOneHolds.lean#L1657](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/PositivityTheory/AutomorphicForms/PublishedInputs/HilbertEisenstein/HilbertEisensteinWeightOneHolds.lean#L1657)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`, `Local Bloch-Kato Orthogonality & Tate Duality Core`, `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** Key PositivityTheory realization (dist=7, height=110) used in automorphy-lifting/congruence arguments.

### Capelli Infinitesimal Character of U(p, q) Discrete Series (`discrete_series_inf_char`)

Proves via Casselman-Osborne Lie algebra cohomology, Koszul resolutions, and Verma covers that the quantum determinant in U(gl_n) acts on smooth vectors of any discrete series representation of U(p, q) as the scalar Harish-Chandra polynomial.

- **Mathematical form:** `∀ π ∈ DiscreteSeries(U(p, q)) of parameter λ, ∀ v ∈ π^∞, qdet(E + (n-1)/2 + Y) · v = capP(λ, Y) · v`
- **Lean anchor:** `discrete_series_infinitesimal_character` in [CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L1794](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/CompanionTheory/HarishChandraModules/LowKTypeMultiplicity/DiscreteSeriesCharacters/DiscreteSeriesInfinitesimalCharacter.lean#L1794)
- **Depends on:** `Master Arithmetic-Automorphic Coordination Package (D7)`
- **Notes:** CompanionTheory assembly proving PI.DSInfCharCap.DSInfCharCap .

---

## Stage 4: Foundational Machinery (12 milestones)

Underlying arithmetic-geometric, cohomological, and analytic infrastructure: PEL Shimura toroidal compactification and Mumford semiabelian uniformisation, resolution of singularities, twisted etale cohomology finiteness, Poitou-Tate duality, Whittaker multiplicity one, Arakelov slope bounds, and Formalism specification contracts.

### PEL Shimura Toroidal Compactification & Boundary Uniformisation (`uniformisation_conclusion`)

Defines the global PEL-type unitary Shimura toroidal compactification specification PartI: existence of integral toroidal models with split boundary fibers, Mumford semiabelian uniformisation N3, torsion/Weil-pairing isomorphisms, and formal power-series arc lifts N4.

- **Mathematical form:** `PartI : ∀ (E CM) (H) (D), ∃ integral toroidal models Y with SplitFibres, Model.N2, Model.N3 (PELUnif), Model.N4 (formal arcs Spec O'[[X]] → Y)`
- **Lean anchor:** `PartI` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L228](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/BirationalGeometry/ToroidalCompactification/UniformisationConclusion.lean#L228)
- **Depends on:** `Split Tori & Semiabelian Torsion Primitives (Critical Spine Base)`
- **Notes:** #1 most-imported interface file in the entire repository .

### Uniqueness of Mumford Semiabelian Uniformisation (`unif_uniq_st`)

Formulates UnifUniqSt (wrapped in Laws6): any two Mumford degeneration uniformisations of the same polarized semiabelian scheme compatible with rigidified line bundles are canonically isomorphic, preserving O_E-actions, theta sections, and thick-level coordinates.

- **Mathematical form:** `UnifUniqSt : (U, U' uniformisations of G over (R, I) with w_L) ⇒ ∃! isomorphism D ≅ D' compatible with O_E and theta frames`
- **Lean anchor:** `UnifUniqSt` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L21](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/UnifUniqSt.lean#L21)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** #2 most-imported external interface file .

### 24-Law Contract for Polarized Abelian Schemes (`global_sections_laws`)

Packages 24 foundational theorems for polarized abelian schemes over arbitrary Noetherian bases: Riemann-Roch section rank n^g, base change, ampleness (n >= 4), Theorem of the Cube and Square, rigidity, Weil pairing nondegeneracy, Mumford theta-group irreducibility, Serre's M-torsion rigidity (M >= 3), and finite-flat quotients.

- **Mathematical form:** `Laws : dim H⁰(A, L^n) = n^g ∧ Ample(n≥4) ∧ Cube ∧ Square ∧ Rigidity ∧ WeilNondeg ∧ ThetaIrred ∧ Serre(M≥3) ∧ Quotient`
- **Lean anchor:** `Laws` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L194](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/ExtensionDescent/GlobalSectionsRankAlgClosed.lean#L194)
- **Depends on:** `Split Tori & Semiabelian Torsion Primitives (Critical Spine Base)`
- **Notes:** contract . Its realization connects to TheoremOfCubeAbelianSchemeOverArbitraryBase (h=97 on the 202-edge critical spine).

### Split Tori & Semiabelian Torsion Primitives (Critical Spine Base) (`split_torus_aff`)

Constructs split algebraic tori Spec(R[X]) as Hopf-algebra group schemes over arbitrary base schemes S, together with character groups, multiplication-by-N maps, and N-torsion subgroup schemes.

- **Mathematical form:** `splitTorus(S, X) = Spec(O_S[X]), G_m(S), mulN : G → G, torsion(G, N) = ker([N] : G → G)`
- **Lean anchor:** `splitTorusAff` in [ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/SplitTori/SplitTorusAff.lean#L25](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/ReciprocityTheory/ReductiveGroups/ArithmeticGeometry/SemiabelianSchemes/SplitTori/SplitTorusAff.lean#L25)
- **Depends on:** None (foundation)
- **Notes:** Terminal height-0 leaf of the longest 202-edge (203-module) critical spine in the entire DAG.

### Finiteness of Twisted Etale Cohomology Over Fields (`etale_finiteness`)

Proves finiteness of twisted etale cohomology H^n(X, Z/qZ(i)) for proper schemes X over arbitrary fields k (with q invertible in k) by double induction on cohomological degree n and Krull dimension, slicing into families of smooth curves via alterations, Kummer theory, and ghost-killing.

- **Mathematical form:** `∀ k field, q ∈ k^×, X/k proper, ∀ n i ∈ ℤ, Finite(H^n_et(X, Z/qZ(i)))`
- **Lean anchor:** `H0TwistOverClosedField` in [Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L71](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/EtaleCohomology/EtaleSheaves/H0TwistOverClosedField.lean#L71)
- **Depends on:** None (foundation)
- **Notes:** Core inductive engine (goal_of) for Development/EtaleCohomology .

### Functorial Resolution of Singularities in Characteristic Zero (`resolution_char_zero`)

Establishes functorial embedded resolution of singularities and ideal principalization over characteristic-zero schemes via iterated blowups along smooth centers, producing strict normal crossings exceptional divisors compatible with smooth morphisms and field extensions.

- **Mathematical form:** `FunctorialResolutionCharZero ⇒ ResolutionCharZero (smooth blowup resolution with SNC exceptional divisor)`
- **Lean anchor:** `resolutionCharZero` in [Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L789](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean#L789)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** Bridges Development/ResolutionOfSingularities into Arakelov height and Moriwaki bigness pipelines. [Relocated from ResolutionCharZero.lean to Development/AutomorphicArithmetic/ThetaCorrespondence/ThetaPairLifts/ThirdPlaceSeries/EveryCharacterOfLiteratureOfVWin.lean] [Shares module EveryCharacterOfLiteratureOfVWin.lean]

### Poitou-Tate Nine-Term Exact Sequence & Sha Duality (`poitou_tate_gs`)

Proves Poitou-Tate global-local duality for finite Z/NZ Galois modules over G_{K,S} (for N odd or K totally complex): finiteness and perfect pairing of Tate-Shafarevich groups Sha^1 and Sha^2, compact-support duality, and exactness of the full nine-term Poitou-Tate sequence.

- **Mathematical form:** `Finite(Sha¹(G_{K,S}, M)) ∧ Finite(Sha²(G_{K,S}, M*(1))) ∧ Exact(0 → H⁰ → ∏' H⁰ → H²* → ... → ∏' H² → 0)`
- **Lean anchor:** `poitouTate_nineTerm_gs` in [GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L1499](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/GroundTheory/ProfiniteCohomology/PoitouTate/PoitouTateNineTermGs.lean#L1499)
- **Depends on:** None (foundation)
- **Notes:** Complete proof in GroundTheory/ProfiniteCohomology of poitouTate_duality_gs, poitouTate_sha_gs, and poitouTate_nineTerm_gs.

### Whittaker Multiplicity One on GL_n(A_K) (`multiplicity_one`)

Proves the Piatetski-Shapiro / Shalika Fourier-Whittaker theorem for smooth cuspidal automorphic forms on GL_n(A_K): by upward induction on unipotent row expansions, if all Whittaker coefficients of a cusp form vanish, then the form itself is identically zero.

- **Mathematical form:** `∀ ϕ ∈ 𝒜_cusp(GL_n(K)\GL_n(A_K)), (∀ g, W_ϕ(g) = 0) ⇒ ϕ = 0`
- **Lean anchor:** `eq_zero_of_whittaker_eq_zero` in [GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L82](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/GroundTheory/AutomorphicForms/MultiplicityOne/Injective.lean#L82)
- **Depends on:** None (foundation)
- **Notes:** proof in GroundTheory/AutomorphicForms .

### Arakelov Hermitian Vector Bundles & Bost-Zhang Slope Inequalities (`kernels_lattice`)

Defines Hermitian lattices (metrized projective O_K-modules with conjugate-compatible positive-definite inner products at infinite places), Arakelov sub/quotient degrees and slopes, and formalizes the Bost-Zhang small-height vector existence bound.

- **Mathematical form:** `∀ (F : HermLattice K i), ∀ ε > 0, ∃ K'/K finite, ∃ v ∈ F ⊗ K' \ {0}, lineDegree(v) ≥ μ(F) - (1/2)log(i) - ε`
- **Lean anchor:** `HermLattice` in [GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L32](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/GroundTheory/HeightsAndTheta/Heights/KernelsLattice.lean#L32)
- **Depends on:** None (foundation)
- **Notes:** core interface in GroundTheory/HeightsAndTheta .

### Rapid Decay & L² Moments of Compactly Supported Cusp-Form Twists (`pi_vec_ex`)

Proves that multiplying a smooth cusp form invariant under the split center by any compactly supported continuous cutoff of log|det| yields an L² function on H_n with finite moments against all powers of the Siegel height weight.

- **Mathematical form:** `∀ ψ cusp form, ∀ u ∈ C_c(ℝ), ψ(x) · u(ldet x) ∈ L²(H_n, ν) ∧ ∫ wt(x)^{2M} |ψ(x)u(ldet x)|² dν < ∞`
- **Lean anchor:** `piVecEx_holds` in [Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean#L59](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Development/DiscreteGroups/PiInvariants/CompactSupportTwists/PiVecExHolds.lean#L59)
- **Depends on:** `PEL Shimura Toroidal Compactification & Boundary Uniformisation`, `24-Law Contract for Polarized Abelian Schemes`
- **Notes:** proof in Development/DiscreteGroups , top interface file of DiscreteGroups.

### Local Bloch-Kato Orthogonality & Tate Duality Core (`loc_coh_bk`)

Specifies continuous p-adic Galois representations GRep, de Rham criteria (dim D_dR = [K:Q_p] dim V), and rational/integral Bloch-Kato exact orthogonality of finite-part cocycles H¹_f under the local Tate cup-product pairing.

- **Mathematical form:** `IsDR(ρ) ⇒ (H¹_f(G_K, V) ⊥ H¹_f(G_K, V*(1))) ∧ (H¹_f(T_A) ⊥ H¹_f(T_{A'})) under local cup product`
- **Lean anchor:** `bkACore` in [Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L195](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/SharpRestriction/LevelLetterCocycles/LocCoh.lean#L195)
- **Depends on:** None (foundation)
- **Notes:** Highest cross-top-directory boundary bridge .

### Master Arithmetic-Automorphic Coordination Package (D7) (`rho_det_d7`)

Defines self-dual Hermitian lattices, inert-prime indices, and the central 200+ field structure D7 coordinating CM host fields, Shimura spaces, column chains, relative Hermitian determinants, Fontaine period rings, Galois types, and theta jets.

- **Mathematical form:** `structure D7 : (Ranks, Host, Hermitian Spaces, Member Column Chains, DivData, Fontaine Period Rings, Galois Types)`
- **Lean anchor:** `D7` in [Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L108](https://github.com/leanprover-community/riemann-hypothesis/blob/307cef33f046955ee79dba47e0d828d06496d75f/src/Formalism/LocalRingCardinality/RhoDetPrimeEqMuTildeMulChiPow.lean#L108)
- **Depends on:** None (foundation)
- **Notes:** Central Formalism data contract .

---

## Baseline Milestones Merged or Removed in This Version

The following **7** baseline milestones were merged, inlined, or eliminated in `src/` (prerequisite edges were transitively rewired across kept milestones):

- **Stage 0** (`main_theorems_all`): Top-Level Theorem & Selmer Combination
- **Stage 1** (`main_theorems_critical`): Critical-Line & ℚ(√−3) Arithmetic
- **Stage 1** (`main_theorems_bridge`): RH & GRH from Half-Plane Nonvanishing
- **Stage 1** (`crit_line`): Functional-Equation Reflection (Primitive)
- **Stage 1** (`rh_of_right`): Zeta Reflection via Functional Equation
- **Stage 2** (`rh_of_every_char`): 208-Input Operator & Covolume Assembly (RiemannHypothesisOfEveryCharacter)
- **Stage 3** (`final_b_flath`): Unitary Admissibility & Flath Tensor Product Factorization

