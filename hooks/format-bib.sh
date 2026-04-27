#!/usr/bin/env bash
# Format BibTeX files with bibtex-tidy using the project's canonical options.
#
# Reads each .bib file, formats it via bibtex-tidy (stdin→stdout), and writes
# the result back in place. If the file content changes, pre-commit detects the
# diff and rejects the commit, prompting the author to 'git add' and recommit.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ARGS_FILE="$SCRIPT_DIR/../.bibtex-tidy-args"

# Build args array from the args file (one flag per line)
mapfile -t TIDY_ARGS < "$ARGS_FILE"

for bib in "$@"; do
    tmpfile=$(mktemp)
    bibtex-tidy "${TIDY_ARGS[@]}" < "$bib" > "$tmpfile"
    mv "$tmpfile" "$bib"
done
