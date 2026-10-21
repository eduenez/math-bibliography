#!/usr/bin/env bash
# Re-sort references.bib alphabetically by citation key.
#
# This script is intentionally NOT a pre-commit hook: re-sorting moves many
# entries at once, which is a deliberate, reviewed change, not a formatting fix.
# It pipes the file through bibtex-tidy (stdin → stdout) and replaces the file
# only when that produced output. Works with the bash 3.2 that macOS ships.
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

# Read formatting args (one per line, skip blanks). A plain read loop, not mapfile:
# macOS ships bash 3.2, which has no mapfile.
FORMAT_ARGS=()
while IFS= read -r line || [ -n "$line" ]; do
  case "$line" in *[![:space:]]*) FORMAT_ARGS+=("$line") ;; esac
done < "$ARGS_FILE"

TARGET="${1:-$REPO_ROOT/references.bib}"

echo "Sorting $TARGET …"
tmpfile=$(mktemp)
trap 'rm -f "$tmpfile"' EXIT
bibtex-tidy ${FORMAT_ARGS[@]+"${FORMAT_ARGS[@]}"} --sort < "$TARGET" > "$tmpfile"
# Never replace the file with nothing (a bibtex-tidy failure that still exits 0, a parse error, …).
if [ ! -s "$tmpfile" ]; then
  echo "bibtex-tidy produced no output; $TARGET left unchanged." >&2
  exit 1
fi
mv "$tmpfile" "$TARGET"
echo "Done. Remember to 'git add $TARGET' before committing."
