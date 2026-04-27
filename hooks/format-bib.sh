#!/usr/bin/env bash
# Format BibTeX files with bibtex-tidy using the project's canonical options.
#
# Reads each .bib file, formats it via bibtex-tidy (stdin→stdout), and writes
# the result back in place. If the file content changes, pre-commit detects the
# diff and rejects the commit, prompting the author to 'git add' and recommit.
#
# This script delegates to the Python wrapper (hooks/format-bib.py) so that
# subprocess I/O is handled reliably regardless of the invocation context.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/format-bib.py" "$@"
