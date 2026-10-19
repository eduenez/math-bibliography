#!/usr/bin/env bash
# Validate BibTeX files using biber --tool --validate-datamodel.
# Exits non-zero if any ERROR-level messages are found in biber's log.
set -euo pipefail

for bib in "$@"; do
    # A field value ending in an unescaped backslash ({Phys. Rev. Lett.\}) is a control space
    # damaged by whitespace stripping; BibTeX passes the stray backslash on to the document.
    if ! python3 - "$bib" <<'EOF'
import re, sys
bad = [f'{sys.argv[1]}:{n}: {line.strip()}' for n, line in enumerate(open(sys.argv[1], encoding='utf-8'), 1)
       if re.search(r'(?<!\\)(?:\\\\)*\\\},?\s*$', line)]
print('\n'.join(['field value ends in a stray backslash (write the value without it):'] + bad) if bad else '', end='')
sys.exit(1 if bad else 0)
EOF
    then
        exit 1
    fi

    tmpdir=$(mktemp -d)
    cp "$bib" "$tmpdir/"
    basename="$(basename "$bib")"

    # Run biber in tool mode (creates ${basename%.bib}_bibertool.bib + biber.log)
    (cd "$tmpdir" && biber --tool --validate-datamodel --no-bblxml --quiet "$basename") || true

    logfile="$tmpdir/biber.log"
    if [[ -f "$logfile" ]] && grep -q '^ERROR' "$logfile"; then
        echo "biber validation errors in $bib:"
        grep '^ERROR' "$logfile"
        rm -rf "$tmpdir"
        exit 1
    fi

    rm -rf "$tmpdir"
done
