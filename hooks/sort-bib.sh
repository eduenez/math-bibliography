#!/usr/bin/env bash
# Re-sort references.bib alphabetically by citation key.
#
# This script is intentionally NOT a pre-commit hook because bibtex-tidy's
# --sort flag uses stdin→stdout mode rather than in-place mode; running it
# through pre-commit would require subprocess redirection that is fragile
# across different shell environments.
#
# Run manually after adding several new entries, then 'git add' the result:
#
#   hooks/sort-bib.sh              # sorts references.bib in place
#   hooks/sort-bib.sh other.bib    # sorts a different bib file
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ARGS_FILE="$REPO_ROOT/.bibtex-tidy-args"

# Read formatting args (one per line, skip blanks)
mapfile -t FORMAT_ARGS < <(grep -v '^\s*$' "$ARGS_FILE")

TARGET="${1:-$REPO_ROOT/references.bib}"

echo "Sorting $TARGET …"
tmpfile=$(mktemp)
bibtex-tidy "${FORMAT_ARGS[@]}" --sort < "$TARGET" > "$tmpfile"
mv "$tmpfile" "$TARGET"
echo "Done. Remember to 'git add $TARGET' before committing."
