# Consumers of math-bibliography

*Generated from `LaTeX-shared-files/vendor-registry.json` by `python3 _scripts/consumers.py --write` (run in LaTeX-shared-files). Edit the registry, not this file.*

Every repository that carries, links or cites the master `references.bib`. When keys are renamed or entries change here, **these** are the
repositories to update. Key renames are recorded in the `rekey-*.json` files (`rekey-2026-10.json` composes the October 2026 renames);
apply them to a consumer's TeX sources with `texfix.py cites --map rekey-2026-10.json …` (see `CONVERTING.md` in the template).

| Repository | Model | Pinned | Notes |
|---|---|---|---|
| [`eduenez/no-free-lunch`](https://github.com/eduenez/no-free-lunch) | vendored-json | `29cf9b3` | project .sty NFL.sty snapshot in children/; branch revendor-2026-10 pending merge |
| [`eduenez/topos-logic`](https://github.com/eduenez/topos-logic) | vendored-json | `29cf9b3` | has references-local.bib for entries not in the master; PR workflow (collaborators); branch revendor-2026-10 pending merge |
| [`eduenez/LaTeX-codespace-template`](https://github.com/eduenez/LaTeX-codespace-template) | vendored-simple | `936fa41` | template for new multi-paper repositories; ships the full set of di-* packages Toolkit (scripts, templates, shared root files) vendored from toolkit/, pinned in _scripts/vendor.lock. |
| [`eduenez/QuantumDI`](https://github.com/eduenez/QuantumDI) | vendored-simple | `29cf9b3` | multi-paper repository (Dueñez-Iovino); private Toolkit (scripts, templates, shared root files) vendored from toolkit/, pinned in _scripts/vendor.lock. |
| [`eduenez/QuantumTeam`](https://github.com/eduenez/QuantumTeam) | vendored-simple | `29cf9b3` | multi-paper repository (team papers and books); private Toolkit (scripts, templates, shared root files) vendored from toolkit/, pinned in _scripts/vendor.lock. |
| [`eduenez/ProbabilityModels`](https://github.com/eduenez/ProbabilityModels) | vendored-simple | `29cf9b3` | converted from submodules to vendored copies on branch vendored-model (pushed, pending merge); flat layout with several papers at the root — candidate for full consolidation into a multi-paper repository later |
| [`eduenez/RealRandom`](https://github.com/eduenez/RealRandom) | vendored-simple | `29cf9b3` | converted from submodules to vendored copies on branch vendored-model (pushed, pending merge); flat layout with several papers at the root — candidate for full consolidation into a multi-paper repository later |
| [`eduenez/RealStructures`](https://github.com/eduenez/RealStructures) | vendored-simple | `29cf9b3` | converted from submodules to vendored copies on branch vendored-model (pushed, pending merge); flat layout with several papers at the root — candidate for full consolidation into a multi-paper repository later |
| [`eduenez/DImanuscripts`](https://github.com/eduenez/DImanuscripts) | submodule | `ff5f219` | bibliography submodule only; private/solo or legacy: submodule kept deliberately |
| [`eduenez/eduenez.github.io`](https://github.com/eduenez/eduenez.github.io) | submodule | `064cc5d` | bibliography submodule only (path math-bibliography/); private/solo or legacy: submodule kept deliberately |
| [`eduenez/talks`](https://github.com/eduenez/talks) | submodule | `8f8a419` | bibliography submodule only (path math-bibliography/); private/solo or legacy: submodule kept deliberately |
| [`eduenez/grants`](https://github.com/eduenez/grants) | legacy-bib | `-` | NOT on the master: uses legacy biblioteca.bib / iovino.bib (and ../../DImanuscripts/iovino); candidate for migration to the master bibliography with math-bibliography/migrate.py --map rekey.json; PLANNED (deferred): convert each of the 6 subdirectories to a grants_* paper directory in QuantumDI (see QuantumDI/docs/plans/grants-conversion.md) |
| [`eduenez/research`](https://github.com/eduenez/research) | submodule | `936fa41` | solo repository; both masters as submodules (_packages = LaTeX-shared-files). Still carries COPIES of the toolkit scripts in _scripts/ (to be replaced by _packages/toolkit/, see toolkit/README.md) |

**Models.** *vendored-json*: copies in `_packages/` with `vendor.lock.json` and a frozen bibliography baseline; maintained with
`vendor.py` and `vendor_sty.py` run from LaTeX-shared-files. *vendored-simple*: copies in `_packages/` with `vendor.lock` (SHA-256 per file);
the repository updates itself with `make update-shared`. *submodule*: git submodules pinned to old commits (the old model; bumping a
pointer needs retrofitting of citation keys and preambles). *legacy-bib*: still uses the old biblioteca.bib / iovino.bib files (not the master).

## Retired (consolidated; do not update)

- QuantumStructures / Soler_axioms → QuantumTeam/quantum_structures_Soler (same GitHub repository (renamed); obsolete notice pushed)
- Quantum_stability, Quantum_NIP, Quantum_simple_unstable, Bipartite_observables_survey → QuantumDI/Qbipartite_* (obsolete notices pushed)
- Quantum_logic, Stability, Games, LogicTextbookUTSA, DiscreteMathTextbookUTSA → QuantumTeam/* (obsolete notices pushed)
