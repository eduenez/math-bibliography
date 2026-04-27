#!/usr/bin/env python3
"""
generate_rekey_map.py — Normalize all citation keys in references.bib to
Author-Author:YYYY format and produce rekey.json for migrate.py.

Usage:
    python3 generate_rekey_map.py          # dry run: show proposed renames
    python3 generate_rekey_map.py --apply  # rewrite references.bib + write rekey.json

Key convention:
    LastName1-LastName2:YYYY
    - Hyphenated surnames preserved (Tomczak-Jaegermann → Tomczak-Jaegermann)
    - Space-joined compounds CamelCased, particles lowercase
      (Ben Yaacov → BenYaacov, von Neumann → vonNeumann, van den Dries → vandenDries)
    - TeX accents and Unicode diacritics stripped to ASCII base letter
    - Entries without year: no ':YYYY' suffix
    - Conflicts: sorted by file position, then suffixed a, b, c, ...
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REFERENCES_BIB = SCRIPT_DIR / "references.bib"
REKEY_JSON = SCRIPT_DIR / "rekey.json"

# ── TeX and Unicode normalisation ─────────────────────────────────────────────

# Accent commands: two forms:
#   1. Braced: \'{e}, \c{c}, \v{S}  → capture group 1
#   2. Bare (non-alpha accent \'x):  → capture group 2
#   3. Bare (alpha accent \cx) only when x is NOT followed by more letters,
#      to avoid matching user macros like \cprime → capture group 3
_ACCENT_RE = re.compile(
    r"\\['\`\^\"~=\.uvHcdb]\{([A-Za-z])\}"     # braced:  \'{e}, \c{c}    → group 1
    r"|\\['\`\^\"~=\.]([A-Za-z])"              # bare non-alpha: \'e      → group 2
    r"|\\[uvHcdb]([A-Za-z])(?![A-Za-z])",       # bare alpha: \ce NOT \cprime → group 3
)

# Special letter macros (order: longer patterns first to avoid partial matches)
_SPECIALS = [
    (re.compile(r"\\OE\b\s*"), "OE"),
    (re.compile(r"\\oe\b\s*"), "oe"),
    (re.compile(r"\\AE\b\s*"), "AE"),
    (re.compile(r"\\ae\b\s*"), "ae"),
    (re.compile(r"\\AA\b\s*"), "A"),
    (re.compile(r"\\aa\b\s*"), "a"),
    (re.compile(r"\\ss\b\s*"), "ss"),
    (re.compile(r"\\O\b\s*"),  "O"),
    (re.compile(r"\\o\b\s*"),  "o"),
    (re.compile(r"\\L\b\s*"),  "L"),
    (re.compile(r"\\l\b\s*"),  "l"),
    (re.compile(r"\\i\b\s*"),  "i"),
]

# Lowercase von-particle words that stay lowercase inside a surname
_PARTICLES = frozenset(
    "von van de del di du dos das den der le la les ter ten af op of".split()
)


def strip_tex_and_unicode(s: str) -> str:
    """Return plain ASCII from a string with TeX commands and/or Unicode."""
    # Accent commands with braced or bare argument (must run BEFORE ~ replacement
    # so that \~{n} → 'n' rather than breaking the command)
    s = _ACCENT_RE.sub(lambda m: m.group(1) or m.group(2) or m.group(3), s)
    # Special letter macros (consume trailing whitespace so no phantom space)
    for pat, repl in _SPECIALS:
        s = pat.sub(repl, s)
    # Remaining TeX commands (word commands: \Name, \name)
    s = re.sub(r"\\[A-Za-z]+\s*", "", s)
    # Braces
    s = re.sub(r"[{}]", "", s)
    # TeX non-breaking space ~ → regular space (after accent processing)
    s = s.replace("~", " ")
    # Unicode diacritics: decompose NFD and drop combining marks
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    # Keep only ASCII
    s = s.encode("ascii", errors="ignore").decode("ascii")
    return s


def normalize_surname(raw: str) -> str:
    """
    Convert a (possibly multi-word, possibly hyphenated, possibly TeX-laden)
    last name into the key component form.

    Examples:
        van Moerbeke  → vanMoerbeke
        von Neumann   → vonNeumann
        van den Dries → vandenDries
        Ben Yaacov    → BenYaacov
        Tomczak-Jaegermann → Tomczak-Jaegermann   (hyphen preserved)
        Pulmannov\'a  → Pulmannova
        Tsirel'son    → Tsirelson
    """
    clean = strip_tex_and_unicode(raw).strip()
    # Process each hyphen-separated chunk independently
    hyphen_parts = clean.split("-")
    result_chunks = []
    for chunk in hyphen_parts:
        words = chunk.split()
        if not words:
            continue
        normalized_words = []
        for i, w in enumerate(words):
            # Strip non-letter chars (apostrophes, dots, digits, etc.)
            w_clean = re.sub(r"[^A-Za-z]", "", w)
            if not w_clean:
                continue
            is_last = (i == len(words) - 1)
            if not is_last and w_clean.lower() in _PARTICLES:
                normalized_words.append(w_clean.lower())
            else:
                # Capitalize first letter, preserve rest
                normalized_words.append(w_clean[0].upper() + w_clean[1:])
        result_chunks.append("".join(normalized_words))
    return "-".join(r for r in result_chunks if r)


def extract_last_name(single_name: str) -> str:
    """
    Extract last name from one BibTeX author name token.
    Handles comma-first ("Last, First") and natural order ("First Last").
    Pre-strips TeX so that tilde, backslash-o, etc. don't interfere with word splitting.
    """
    # Pre-strip TeX/Unicode so ~ and other non-space separators become spaces
    name = strip_tex_and_unicode(single_name).strip()
    if "," in name:
        last = name.split(",", 1)[0].strip()
    else:
        # Natural order: last word is the surname (ignore preceding initials/given names)
        parts = name.split()
        last = parts[-1] if parts else ""
    return normalize_surname(last)


def parse_names(field_value: str) -> list[str]:
    """Return list of normalized last names from an author/editor field value."""
    tokens = re.split(r"\s+and\s+", field_value, flags=re.IGNORECASE)
    result = []
    for tok in tokens:
        ln = extract_last_name(tok)
        if ln:
            result.append(ln)
    return result


def extract_year(year_value: str) -> str:
    """Return first 4-digit sequence found in a year field value, or ''."""
    m = re.search(r"\d{4}", year_value)
    return m.group() if m else ""


def canonical_base(last_names: list[str], year: str) -> str:
    """Build canonical key (without conflict suffix)."""
    base = "-".join(last_names)
    return f"{base}:{year}" if year else base


# ── BibTeX entry extraction ───────────────────────────────────────────────────

_ENTRY_HEADER_RE = re.compile(r"@(\w+)\s*\{([^,\s]+)\s*,", re.IGNORECASE)


def iter_entries(text: str):
    """
    Yield (start, end, entry_type, key, fields_dict) for each @entry in text.
    Uses brace counting to find the end of each entry.
    """
    n = len(text)
    pos = 0
    while pos < n:
        at = text.find("@", pos)
        if at == -1:
            break

        m = _ENTRY_HEADER_RE.match(text, at)
        if not m:
            pos = at + 1
            continue

        entry_type = m.group(1).lower()
        key = m.group(2)
        # Find matching closing brace
        brace_open = text.index("{", at)
        depth = 0
        i = brace_open
        while i < n:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        end = i + 1

        if entry_type not in ("preamble", "comment", "string"):
            inner = text[brace_open + 1 : i]
            fields = _parse_fields(inner)
            yield at, end, entry_type, key, fields

        pos = end


def _parse_fields(inner: str) -> dict[str, str]:
    """Parse key-value fields from the body of a @entry{...} block."""
    # Skip the leading citation key (everything up to and including the first comma)
    comma = inner.find(",")
    if comma == -1:
        return {}
    body = inner[comma + 1 :]

    fields: dict[str, str] = {}
    pos = 0
    n = len(body)
    while pos < n:
        fm = re.match(r"\s*(\w+)\s*=\s*", body[pos:])
        if not fm:
            break
        fname = fm.group(1).lower()
        pos += fm.end()
        if pos >= n:
            break

        ch = body[pos]
        if ch == "{":
            depth = 0
            j = pos
            while j < n:
                if body[j] == "{":
                    depth += 1
                elif body[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            fields[fname] = body[pos + 1 : j]
            pos = j + 1
        elif ch == '"':
            j = pos + 1
            while j < n:
                if body[j] == '"':
                    break
                j += 1
            fields[fname] = body[pos + 1 : j]
            pos = j + 1
        else:
            vm = re.match(r"([^,\s}]+)", body[pos:])
            if vm:
                fields[fname] = vm.group(1)
                pos += vm.end()
            else:
                break
        # Skip comma separator
        cm = re.match(r"\s*,?\s*", body[pos:])
        if cm:
            pos += cm.end()

    return fields


# ── Key generation ────────────────────────────────────────────────────────────

def build_rekey_map(text: str) -> dict[str, str]:
    """
    Parse references.bib, compute a canonical key for every entry,
    resolve conflicts, and return {old_key: new_key} for changed entries only.
    """
    # Collect (position, old_key, canonical_base) for all entries
    raw_entries: list[tuple[int, str, str]] = []
    for start, end, etype, key, fields in iter_entries(text):
        author_str = fields.get("author") or fields.get("editor") or ""
        year_str = fields.get("year", "")

        names = parse_names(author_str) if author_str else []
        year = extract_year(year_str)

        if names:
            base = canonical_base(names, year)
        else:
            # No author/editor: keep existing key unchanged
            base = key

        raw_entries.append((start, key, base))

    # Group by canonical base to detect conflicts
    from collections import defaultdict
    groups: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for start, old_key, base in raw_entries:
        groups[base].append((start, old_key))

    # Assign final keys; entries in conflict get a/b/c... by file order
    rekey: dict[str, str] = {}
    for base, members in groups.items():
        if len(members) == 1:
            _start, old_key = members[0]
            new_key = base
            if old_key != new_key:
                rekey[old_key] = new_key
        else:
            # Sort by file position, then assign suffixes
            members.sort(key=lambda x: x[0])
            for i, (_start, old_key) in enumerate(members):
                suffix = chr(ord("a") + i)
                new_key = f"{base}{suffix}"
                if old_key != new_key:
                    rekey[old_key] = new_key

    return rekey


def apply_rekey_to_bib(text: str, rekey: dict[str, str]) -> str:
    """Rename citation keys in the .bib file itself."""
    # Replace @type{old_key, with @type{new_key,
    def replacer(m: re.Match) -> str:
        at_type = m.group(1)   # e.g. "@article{"
        old_key = m.group(2)
        comma = m.group(3)
        new_key = rekey.get(old_key, old_key)
        return f"{at_type}{new_key}{comma}"

    return re.sub(
        r"(@\w+\s*\{)([^,\s]+)(\s*,)",
        replacer,
        text,
        flags=re.IGNORECASE,
    )


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Rewrite references.bib in place and write rekey.json.",
    )
    args = parser.parse_args()

    if not REFERENCES_BIB.exists():
        print(f"Error: {REFERENCES_BIB} not found.", file=sys.stderr)
        return 1

    text = REFERENCES_BIB.read_text(encoding="utf-8")
    rekey = build_rekey_map(text)

    if not rekey:
        print("All keys already conform — nothing to do.")
        return 0

    print(f"{'─'*70}")
    print(f"{'APPLY' if args.apply else 'DRY RUN'}: {len(rekey)} key rename(s)\n")
    for old, new in sorted(rekey.items()):
        print(f"  {old!r:45s} → {new!r}")
    print(f"{'─'*70}")

    if args.apply:
        new_text = apply_rekey_to_bib(text, rekey)
        REFERENCES_BIB.write_text(new_text, encoding="utf-8")
        print(f"Written: {REFERENCES_BIB}")

        REKEY_JSON.write_text(
            json.dumps(rekey, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Written: {REKEY_JSON}")
    else:
        print("Dry run complete. Run with --apply to write changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
