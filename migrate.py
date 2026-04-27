#!/usr/bin/env python3
r"""
migrate.py — Migrate TeX files to math-bibliography/references.bib

Scans one or more TeX files and optionally rewrites them to:

  1. Replace \bibliography{...} declarations with the correct relative path
     to references.bib (path is computed automatically from each file's
     location on disk relative to references.bib).

  2. Rename citation keys inside \cite{...}, \citet{...}, \citep{...}, etc.
     according to a JSON rekey map (--map).  If no map is provided the step
     is skipped.  The map has the form {"old_key": "new_key", ...}.

Usage
-----
  # Dry run — show what would change, touch nothing:
  python3 migrate.py path/to/paper.tex [more/files.tex ...]

  # Dry run on every TeX file under a directory tree:
  python3 migrate.py ~/repos/SomePaper/

  # Apply changes in place:
  python3 migrate.py --apply paper.tex

  # Apply with a key-rename map:
  python3 migrate.py --apply --map rekey.json paper.tex

The --apply flag rewrites files in place.  Without it the script prints a
unified diff for each file that would change and exits non-zero if any file
needs updating (useful for CI).

Key-rename map
--------------
During the initial merge of biblioteca.bib and iovino.bib into references.bib
NO keys were renamed, so the default map is empty and \cite{} commands need
no changes.  If you later decide to standardise keys (e.g. rename
"BenYaacov2013" → "BenYaacov:2013") you can build the map with:

  python3 migrate.py --print-keys   # prints all keys in references.bib

and then edit the resulting JSON to record any desired renames.

Bibliography path detection
---------------------------
The script recognises these legacy patterns (with or without leading %):

  \bibliography{../iovino,../biblioteca}
  \bibliography{../biblioteca,../iovino}
  \bibliography{../iovino}
  \bibliography{../biblioteca}
  \bibliography{../DImanuscripts/iovino,../DImanuscripts/biblioteca}
  \bibliography{../DImanuscripts/iovino}
  \bibliography{../DImanuscripts/biblioteca}
  \bibliography{bibdatabase,../iovino}       (ergodic sub-project)
  \bibliography{bibdatabase,iovino}          (ergodic sub-project)

and replaces them with a single \bibliography{<relative-path-to-references>},
where the relative path is computed for each file individually.
"""

import argparse
import difflib
import json
import os
import re
import sys
from pathlib import Path

# ── Location of references.bib ──────────────────────────────────────────────

# Resolve references.bib relative to this script's own location so the script
# works wherever it is invoked from.
SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_BIB = SCRIPT_DIR / "references.bib"

# ── Old bibliography patterns to replace ────────────────────────────────────

# Each pattern is a regex that matches the *argument* of \bibliography{...}.
# Order matters: more-specific patterns first.
_OLD_BIB_ARG_PATTERNS = [
    # Two-file combos (either order)
    r"\.\.\/DImanuscripts\/iovino\s*,\s*\.\.\/DImanuscripts\/biblioteca",
    r"\.\.\/DImanuscripts\/biblioteca\s*,\s*\.\.\/DImanuscripts\/iovino",
    r"\.\.\/iovino\s*,\s*\.\.\/biblioteca",
    r"\.\.\/biblioteca\s*,\s*\.\.\/iovino",
    # Single-file references
    r"\.\.\/DImanuscripts\/iovino",
    r"\.\.\/DImanuscripts\/biblioteca",
    r"\.\.\/iovino",
    r"\.\.\/biblioteca",
    # Ergodic sub-project variants (local bibdatabase paired with iovino)
    r"bibdatabase\s*,\s*\.\.\/iovino",
    r"bibdatabase\s*,\s*iovino",
]

# Build one combined regex that matches \bibliography{<old-arg>} (active or
# commented out).  Capture groups: (1) leading comment marker if any,
# (2) the old argument.
_OLD_BIB_RE = re.compile(
    r"(%?\s*\\bibliography\{)("
    + "|".join(_OLD_BIB_ARG_PATTERNS)
    + r")(\})",
    re.IGNORECASE,
)

# Ergodic patterns keep a local bibdatabase alongside references; we need to
# detect those to preserve "bibdatabase," in the replacement.
_ERGODIC_ARG_RE = re.compile(
    r"bibdatabase\s*,\s*(\.\.\/iovino|iovino)", re.IGNORECASE
)

# ── Citation command variants to scan ────────────────────────────────────────

# Matches \cite, \citet, \citep, \citealt, \citealp, \citeauthor, \citeyear,
# \Citet, \Citep, \Cite, etc. — with or without optional pre/post notes.
_CITE_RE = re.compile(
    r"(\\[Cc]ite(?:t|p|alt|alp|author|year|num|text)?\*?)"  # command
    r"(?:\[[^\]]*\])*"                                         # optional [pre][post]
    r"\{([^}]+)\}",                                            # {key,key,...}
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def relative_bib_path(tex_file: Path) -> str:
    """Return the path string to use in \bibliography{} for a given TeX file."""
    tex_dir = tex_file.resolve().parent
    rel = os.path.relpath(REFERENCES_BIB.with_suffix(""), tex_dir)
    # BibTeX uses forward slashes even on Windows
    return rel.replace(os.sep, "/")


def update_bibliography(text: str, tex_file: Path) -> str:
    """Replace old \bibliography{...} arguments with the new references path."""
    new_bib_arg = relative_bib_path(tex_file)

    def replacer(m: re.Match) -> str:
        prefix = m.group(1)   # e.g. "\bibliography{" or "%\bibliography{"
        old_arg = m.group(2)
        suffix = m.group(3)   # "}"
        # Ergodic files keep their local bibdatabase entry
        if _ERGODIC_ARG_RE.match(old_arg):
            replacement_arg = f"bibdatabase,{new_bib_arg}"
        else:
            replacement_arg = new_bib_arg
        return f"{prefix}{replacement_arg}{suffix}"

    return _OLD_BIB_RE.sub(replacer, text)


def apply_rekey_map(text: str, rekey: dict[str, str]) -> tuple[str, list[str]]:
    """Rename citation keys in all \\cite{} variants.  Returns (new_text, changes)."""
    if not rekey:
        return text, []

    changes: list[str] = []

    def replace_keys(m: re.Match) -> str:
        cmd = m.group(1)
        keys_str = m.group(2)
        # Preserve whitespace around commas
        keys = [k.strip() for k in keys_str.split(",")]
        new_keys = []
        for k in keys:
            if k in rekey:
                changes.append(f"  \\cite key: {k!r} → {rekey[k]!r}")
                new_keys.append(rekey[k])
            else:
                new_keys.append(k)
        new_keys_str = ", ".join(new_keys)
        # Reconstruct, preserving any optional args (they were consumed but not
        # captured separately — re-match the full original span is safer)
        return m.group(0).replace(keys_str, new_keys_str)

    new_text = _CITE_RE.sub(replace_keys, text)
    return new_text, changes


def collect_tex_files(paths: list[str]) -> list[Path]:
    result: list[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            result.extend(path.rglob("*.tex"))
        elif path.suffix == ".tex":
            result.append(path)
        else:
            print(f"Warning: skipping non-TeX file {p}", file=sys.stderr)
    return sorted(result)


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "paths",
        nargs="*",
        metavar="TEX_FILE_OR_DIR",
        help="TeX files or directories to process.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite files in place.  Without this flag the script is a dry run.",
    )
    parser.add_argument(
        "--map",
        metavar="KEY_MAP.json",
        help='JSON file {"old_key": "new_key", ...} for renaming citation keys.',
    )
    parser.add_argument(
        "--print-keys",
        action="store_true",
        help="Print all citation keys in references.bib and exit.",
    )
    args = parser.parse_args()

    # ── --print-keys mode ──────────────────────────────────────────────────
    if args.print_keys:
        if not REFERENCES_BIB.exists():
            print(f"Error: {REFERENCES_BIB} not found.", file=sys.stderr)
            return 1
        key_re = re.compile(r"^@\w+\{(\S+?),", re.MULTILINE)
        text = REFERENCES_BIB.read_text(encoding="utf-8")
        keys = key_re.findall(text)
        for k in sorted(keys, key=str.lower):
            print(k)
        return 0

    if not args.paths:
        parser.print_help()
        return 0

    # ── Load rekey map ─────────────────────────────────────────────────────
    rekey: dict[str, str] = {}
    if args.map:
        with open(args.map, encoding="utf-8") as f:
            rekey = json.load(f)
        print(f"Loaded {len(rekey)} key rename(s) from {args.map}")

    # ── Verify references.bib exists ──────────────────────────────────────
    if not REFERENCES_BIB.exists():
        print(f"Error: {REFERENCES_BIB} not found.", file=sys.stderr)
        return 1

    tex_files = collect_tex_files(args.paths)
    if not tex_files:
        print("No TeX files found.")
        return 0

    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] Processing {len(tex_files)} file(s) …\n")

    any_changed = False

    for tex_file in tex_files:
        original = tex_file.read_text(encoding="utf-8")

        # Step 1: update \bibliography{}
        updated = update_bibliography(original, tex_file)

        # Step 2: rename \cite keys
        updated, cite_changes = apply_rekey_map(updated, rekey)

        if updated == original:
            continue  # nothing to do

        any_changed = True
        diff = list(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                updated.splitlines(keepends=True),
                fromfile=str(tex_file),
                tofile=str(tex_file) + " (migrated)",
                n=2,
            )
        )

        print(f"{'─' * 70}")
        print(f"File: {tex_file}")
        if cite_changes:
            print("Key renames:")
            for c in cite_changes:
                print(c)
        print("Diff:")
        sys.stdout.writelines(diff)
        print()

        if args.apply:
            tex_file.write_text(updated, encoding="utf-8")
            print(f"  → Written.")

    print(f"{'─' * 70}")
    if not any_changed:
        print("No files need updating.")
        return 0
    if args.apply:
        print("Done. All files updated.")
        return 0
    else:
        print("Dry run complete. Run with --apply to write changes.")
        return 1  # non-zero signals CI that changes are pending


if __name__ == "__main__":
    sys.exit(main())
