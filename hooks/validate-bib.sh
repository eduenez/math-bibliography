#!/usr/bin/env bash
# Validate BibTeX files using biber --tool --validate-datamodel.
# Exits non-zero if any ERROR-level messages are found in biber's log.
set -euo pipefail

for bib in "$@"; do
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
