# math-bibliography

Shared BibTeX bibliography database for research papers by Dueñez and Iovino.

## Contents

| File / Directory | Purpose |
|---|---|
| `references.bib` | Unified database — 808 entries, UTF-8, normalized |
| `.bibtex-tidy-args` | Canonical bibtex-tidy flags (used by hooks and sort script) |
| `.pre-commit-config.yaml` | Pre-commit hook configuration |
| `hooks/validate-bib.sh` | Validation hook (biber) |
| `hooks/sort-bib.sh` | Manual re-sort script (run after bulk additions) |
| `migrate.py` | Migration script for existing TeX files |

## Using this database in a new paper repository

Add this repository as a git submodule:

```bash
git submodule add https://github.com/eduenez/math-bibliography.git bib
```

Then in your TeX file:

```latex
\bibliography{bib/references}   % from the repo root
\bibliography{../bib/references} % from a subdirectory
```

When cloning a repo that already contains this submodule:

```bash
git clone --recurse-submodules <repo-url>
# or, after a plain clone:
git submodule update --init
```

## Citation keys

The database merges two legacy files (`biblioteca.bib` and `iovino.bib`).
Keys from each file are preserved as-is:

- `biblioteca.bib` style: `AuthorAbbrevYYYY` — e.g. `BenYaacov2013`, `AdlerFoNavM2000`
- `iovino.bib` style: `Author-Author:YYYY` — e.g. `Aerts-Pulmannova:2006`, `Argyros-Haydon:2011`

**New entries** should follow the `Author-Author:YYYY` convention
(full last names, hyphen-separated, colon before year).

To list all current keys:

```bash
python3 migrate.py --print-keys
```

## Formatting and validation (pre-commit hooks)

Install the hooks once after cloning:

```bash
pre-commit install
```

Every `git commit` then runs two checks automatically:

1. **bibtex-tidy** — reformats entries in place (lowercase field names,
   curly-brace values, numeric year/volume, removes obsolete fields).
   If the file changes, the commit is rejected; `git add` the reformatted
   file and recommit.

2. **biber --validate-datamodel** — checks for missing required fields and
   malformed syntax. Fails on ERROR-level messages.

### Re-sorting after bulk additions

`--sort` is excluded from the commit hook because bibtex-tidy's sort mode
uses stdin/stdout (not in-place), which is fragile in the pre-commit
environment. Re-sort manually when needed:

```bash
hooks/sort-bib.sh           # sorts references.bib
hooks/sort-bib.sh other.bib # sorts a different file
git add references.bib
git commit
```

### Running the format check without committing

```bash
pre-commit run bibtex-tidy-format --all-files
pre-commit run biber-validate --all-files
```

## Migrating existing TeX files

The legacy workflow uses two separate files:

```latex
% old — paths as seen from a DImanuscripts subdirectory:
\bibliography{../iovino,../biblioteca}

% old — from an external repo that references DImanuscripts:
\bibliography{../DImanuscripts/iovino,../DImanuscripts/biblioteca}
```

`migrate.py` updates these declarations to point to `references.bib`
and can also rename `\cite{}` keys if the citation key convention is
ever unified.

### Dry run (default — no files are written)

```bash
# Single file:
python3 migrate.py path/to/paper.tex

# Entire directory tree:
python3 migrate.py ~/repos/SomePaper/

# Multiple files:
python3 migrate.py file1.tex file2.tex
```

The script prints a unified diff of every file that would change and
exits with code 1 if any changes are pending (useful in CI).

### Applying changes

```bash
python3 migrate.py --apply paper.tex
python3 migrate.py --apply ~/repos/SomePaper/
```

The script computes the correct relative path to `references.bib`
for each TeX file individually, so it works regardless of where the
TeX file lives under `~/repos/`.

### Renaming citation keys (future use)

No keys were renamed during the initial merge.  If you later decide
to unify the key naming convention, build a JSON rename map and apply
it together with the bibliography path update:

```bash
# 1. Print all current keys to a file for reference:
python3 migrate.py --print-keys > all-keys.txt

# 2. Create a JSON map of renames (only entries that actually change):
cat > rekey.json <<'EOF'
{
  "BenYaacov2013":  "BenYaacov:2013",
  "AdlerFoNavM2000": "Adler-etal:2000"
}
EOF

# 3. Dry run to review:
python3 migrate.py --map rekey.json paper.tex

# 4. Apply:
python3 migrate.py --apply --map rekey.json paper.tex
```

`\cite{}`, `\citet{}`, `\citep{}`, and all other cite-command variants
are updated. Multiple keys in a single `\cite{key1,key2}` are each
handled independently.

### Legacy patterns recognised by migrate.py

The script handles all known variants of the old bibliography declarations,
both active and commented out:

| Old declaration | Replacement |
|---|---|
| `\bibliography{../iovino,../biblioteca}` | `\bibliography{<rel-path>/references}` |
| `\bibliography{../biblioteca,../iovino}` | `\bibliography{<rel-path>/references}` |
| `\bibliography{../iovino}` | `\bibliography{<rel-path>/references}` |
| `\bibliography{../biblioteca}` | `\bibliography{<rel-path>/references}` |
| `\bibliography{../DImanuscripts/iovino,...}` | `\bibliography{<rel-path>/references}` |
| `\bibliography{bibdatabase,../iovino}` | `\bibliography{bibdatabase,<rel-path>/references}` |
| `\bibliography{bibdatabase,iovino}` | `\bibliography{bibdatabase,<rel-path>/references}` |

The `bibdatabase,` prefix (used in the `ergodic` sub-project) is
preserved alongside the new path.
