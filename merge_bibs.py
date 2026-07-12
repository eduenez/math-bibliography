#!/usr/bin/env python3
r"""
(Script for historical/archival purposes only: has no live role in the current pipeline.)
ONE-SHOT PROVENANCE SCRIPT — run once to create the initial references.bib.

This is the first stage of the merge->rekey->migrate pipeline (see also
generate_rekey_map.py and migrate.py). It is kept in version control to
document how references.bib was originally produced; it is NOT a live tool.
It hard-codes SRC_DIR below and reads two source files that do not live in
this repo, so it will not run as-is on another machine.

Merge biblioteca.bib (ISO-8859-1) and iovino.bib (UTF-8) into references.bib (UTF-8).

Actions performed:
  - Converts biblioteca.bib from ISO-8859-1 to UTF-8
  - Keeps the @Preamble from biblioteca.bib (defines \cprime used in some entries)
  - Expands all @string macro references in iovino.bib to their inline values
  - Strips @string definitions, @comment blocks, and encoding comment lines from iovino.bib
  - Concatenates into one references.bib, ready for bibtex-tidy to finish normalizing
"""

import re
import sys

SRC_DIR = "/Users/eduenez/repos/DImanuscripts"

# ── Read source files ──────────────────────────────────────────────────────────

with open(f"{SRC_DIR}/biblioteca.bib", encoding="utf-8") as f:
    biblioteca = f.read()

with open(f"{SRC_DIR}/iovino.bib", encoding="utf-8") as f:
    iovino = f.read()

# ── Extract @string macros from iovino.bib (case-insensitive keys) ─────────────

string_macros: dict[str, str] = {}
for m in re.finditer(
    r'@string\s*\{\s*(\w+)\s*=\s*(?:\{([^}]*)\}|"([^"]*)")\s*\}',
    iovino,
    re.IGNORECASE,
):
    key = m.group(1).lower()
    value = m.group(2) if m.group(2) is not None else m.group(3)
    string_macros[key] = value

print(f"Found @string macros: {list(string_macros.keys())}")

# ── Expand macro references in field values ────────────────────────────────────
# Matches:   = MACRONAME,   or   = MACRONAME }   (bare word, not in braces/quotes)

def expand_string_macros(text: str, macros: dict[str, str]) -> str:
    macro_pattern = re.compile(r"(=\s*)([A-Za-z]\w*)\s*(?=[,\n}])")
    def replace(m: re.Match) -> str:
        key = m.group(2).lower()
        if key in macros:
            return f"{m.group(1)}{{{macros[key]}}}"
        return m.group(0)
    return macro_pattern.sub(replace, text)

iovino_expanded = expand_string_macros(iovino, string_macros)

# Verify all macro references were expanded
unexpanded = re.findall(r"=\s*([A-Za-z]\w*)\s*[,\n}]", iovino_expanded)
still_macro = [u for u in unexpanded if u.lower() in string_macros]
if still_macro:
    print(f"WARNING: unexpanded macros remaining: {still_macro}", file=sys.stderr)
else:
    print("All @string macros expanded successfully.")

# ── Clean iovino.bib ───────────────────────────────────────────────────────────

# Remove @string definitions (simple — no nested braces in these)
iovino_clean = re.sub(
    r'@string\s*\{[^}]*\}\s*\n?', "", iovino_expanded, flags=re.IGNORECASE
)
# Remove @comment blocks
iovino_clean = re.sub(
    r'@comment\s*\{[^}]*\}\s*\n?', "", iovino_clean, flags=re.IGNORECASE
)
# Remove BibDesk %% header comment lines
iovino_clean = re.sub(r'^%%.*\n', "", iovino_clean, flags=re.MULTILINE)

# ── Extract @Preamble from biblioteca.bib using brace-counting ─────────────────
# Simple regex cannot handle nested braces inside the @Preamble string, so we
# use a character-by-character brace counter.

def extract_at_block(text: str, keyword: str) -> tuple[str, int, int]:
    """Return (block_text, start, end) for the first @keyword{...} in text,
    correctly handling nested braces."""
    pat = re.compile(r'@' + keyword + r'\s*\{', re.IGNORECASE)
    m = pat.search(text)
    if not m:
        return ("", -1, -1)
    start = m.start()
    depth = 0
    for i, ch in enumerate(text[m.end() - 1:], start=m.end() - 1):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return (text[start:i + 1], start, i + 1)
    return ("", -1, -1)  # unclosed block

preamble, p_start, p_end = extract_at_block(biblioteca, "Preamble")
if preamble:
    # Rewrite as a clean single-line preamble so bibtex-tidy parses it easily.
    # Extract the inner TeX content from the quoted string inside the braces.
    inner = re.search(r'"(.*?)"', preamble, re.DOTALL)
    tex_content = inner.group(1).strip() if inner else ""
    preamble = f'@preamble{{"{tex_content}"}}'
    print(f"Keeping @Preamble: {preamble!r}")

# ── Clean biblioteca.bib ───────────────────────────────────────────────────────

if p_start >= 0:
    biblioteca_clean = biblioteca[:p_start] + biblioteca[p_end:]
else:
    biblioteca_clean = biblioteca

# Remove encoding declaration comment
biblioteca_clean = re.sub(
    r'^%\s*Encoding:.*\n', "", biblioteca_clean, flags=re.MULTILINE
)
# Remove @Comment blocks (e.g. jabref-meta)
biblioteca_clean = re.sub(
    r'@[Cc]omment\s*\{[^}]*\}\s*\n?', "", biblioteca_clean
)

# ── Assemble merged file ───────────────────────────────────────────────────────

parts = []
if preamble:
    parts.append(preamble)
parts.append(biblioteca_clean.strip())
parts.append(iovino_clean.strip())

merged = "\n\n".join(parts) + "\n"

with open("references.bib", "w", encoding="utf-8") as f:
    f.write(merged)

# ── Report ─────────────────────────────────────────────────────────────────────

bib_count = len(re.findall(
    r'^@(?!preamble|string|comment)', merged, re.IGNORECASE | re.MULTILINE
))
print(f"\nWrote references.bib: {bib_count} entries, {len(merged.splitlines())} lines.")
