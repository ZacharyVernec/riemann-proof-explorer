# Topical Hierarchy & Sub-Theory Organization

This document maps the topical organization of the mathematical proof across its major directories and sub-theories.

## 1. Top-Level Mathematical Domains

| Domain | Mathematical Scope |
|---|---|
| [Main.lean](file:///home/ubuntu/riemann_proof/lean/src/Main.lean) & [Statements.lean](file:///home/ubuntu/riemann_proof/lean/src/Statements.lean) | Standalone target specifications and final proofs of the Riemann Hypothesis, right half-plane nonvanishing for Dirichlet $L$-functions, and the Generalized Riemann Hypothesis. |
| [Supplements](file:///home/ubuntu/riemann_proof/lean/src/Supplements) | Top-level assembly kernels uniting the critical-line theorem track with the explicit small-class-number Selmer bound over $\mathbb{Q}(\sqrt{-3})$. |
| [Development](file:///home/ubuntu/riemann_proof/lean/src/Development) | Primary proof synthesis across abelian varieties, automorphic arithmetic, automorphic spectrum, the Weil bound & Moriwaki bigness, étale cohomology, discrete groups, and resolution of singularities. |
| [Formalism](file:///home/ubuntu/riemann_proof/lean/src/Formalism) | Analytic and algebraic specification contracts: local-to-global theta lifts, sharp restriction, period integrals, Hermitian curvature, $\mathrm{GL}_3$ mean squares, and local Bloch-Kato cohomology. |
| [ReciprocityTheory](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory) | Reductive groups, PEL Shimura toroidal compactifications, Mumford semiabelian uniformisations, $L^2$ $\bar\partial$-estimates, dual lattices, and semistable reduction. |
| [GroundTheory](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory) | Arakelov heights and theta functions, automorphic multiplicity one, profinite Poitou-Tate cohomology, global/local fields, $p$-adic Hodge theory, and arithmetic geometry. |
| [CompanionTheory](file:///home/ubuntu/riemann_proof/lean/src/CompanionTheory) | Spectral geometry, real reductive groups and Flath factorization, Harish-Chandra discrete series characters, and tempered local spectra. |
| [PositivityTheory](file:///home/ubuntu/riemann_proof/lean/src/PositivityTheory) | Automorphic positivity estimates, Rankin-Selberg $\mathrm{GL}_3 \times \mathrm{GL}_2$ and $\mathrm{GL}_2 \times \mathrm{GL}_2$ zeta integrals, and parallel weight-one Hilbert Eisenstein series. |
| [Lemmata](file:///home/ubuntu/riemann_proof/lean/src/Lemmata) | Standalone linear-algebraic and matrix-determinant identities (such as Cauchy-Binet and dual Weyl pullbacks). |

## 2. Core Sub-Theories (`Depth 2` & `Depth 3`)

- **[Development/AbelianVarietyTheory](file:///home/ubuntu/riemann_proof/lean/src/Development/AbelianVarietyTheory):** Polarized abelian schemes, divisor and line-bundle proofs (`DivisorProofs`), inertia eigenvalues (`InertiaEigenvalues`), Iwasawa decompositions (`IwasawaDecomposition`), twisted operators (`TwistedOperators`), flag measures (`FlagMeasures`), Satake parameters (`SatakeParameters`), moduli and degeneration proofs, and the master catalog of literature specifications (`PublishedTheorems`).
- **[Development/AutomorphicArithmetic](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicArithmetic):** Windowed Chebyshev character boxes (`CharacterBoxes`), modularity-lifting threshold arguments and Kato's Euler system (`AutomorphicVarieties`), $\ell$-adic Galois representations and weight-one geometric realization (`Foundations`), unitary theta-correspondence pair lifts (`ThetaCorrespondence`), and Capelli differential operator identities (`IntegralCasts`).
- **[Development/AutomorphicSpectrum](file:///home/ubuntu/riemann_proof/lean/src/Development/AutomorphicSpectrum):** Block decomposition of smooth representations (`BlockDecomposition`), good root-tower and Arakelov volume theorems (`GeometryProofs`, `DivisibilityProofs`), and metric/Hermitian height comparisons (`MetricProofs`).
- **[Development/WeilBound](file:///home/ubuntu/riemann_proof/lean/src/Development/WeilBound):** Moriwaki arithmetic bigness and Hilbert-Samuel volume chains (`CoreStatements/AutomorphicKernels/MoriwakiBigness`), $p$-adic Hodge / étale cohomology comparisons, regularized Siegel-Weil and theta idempotents (`RepresentationTheoryGL`), and literature proof bridges (`CoreStatements/PublishedTheorems`).
- **[Formalism/LocalToGlobal](file:///home/ubuntu/riemann_proof/lean/src/Formalism/LocalToGlobal) & [Formalism/SharpRestriction](file:///home/ubuntu/riemann_proof/lean/src/Formalism/SharpRestriction):** Indefinite and definite theta-lift stages, Siegel lattice theory, growth and cusp-span norm bounds, local Bloch-Kato finite-part cohomology (`LevelLetterCocycles`), and the windowed Landau nonvanishing criterion (`TotientGaloisClasses`).
- **[ReciprocityTheory/ReductiveGroups](file:///home/ubuntu/riemann_proof/lean/src/ReciprocityTheory/ReductiveGroups):** PEL-type Shimura toroidal compactifications (`ToroidalCompactification`), Mumford semiabelian degeneration and descent (`ExtensionDescent`), and split algebraic tori (`SemiabelianSchemes`).
- **[GroundTheory/HeightsAndTheta](file:///home/ubuntu/riemann_proof/lean/src/GroundTheory/HeightsAndTheta):** Arakelov Hermitian vector bundles, Bost-Zhang small-height slope inequalities (`KernelsLattice`), complex analytic sets, arithmetic Bézout intersections, and Hilbert-Samuel growth bounds.
