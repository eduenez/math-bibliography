#!/usr/bin/env python3
"""
Format BibTeX files with bibtex-tidy using the project's canonical options.

Called by hooks/format-bib.sh (and thus by the pre-commit hook).
Reads each .bib file given as a command-line argument, pipes it through
bibtex-tidy (stdin → stdout mode), and writes the result back in place.

Using Python for subprocess I/O avoids shell-level stdin/stdout redirect
quirks that can occur when called from pre-commit's execution environment.
"""
import shlex
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ARGS_FILE = SCRIPT_DIR.parent / ".bibtex-tidy-args"
BIBTEX_TIDY = "bibtex-tidy"


def load_args() -> list[str]:
    """Read bibtex-tidy flags from .bibtex-tidy-args (one per line)."""
    text = ARGS_FILE.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def format_bib(bib_path: Path, args: list[str]) -> None:
    content = bib_path.read_bytes()

    result = subprocess.run(
        [BIBTEX_TIDY] + args,
        input=content,
        capture_output=True,
    )

    if result.returncode != 0:
        sys.stderr.write(
            f"bibtex-tidy error on {bib_path}:\n"
            + result.stderr.decode(errors="replace")
        )
        sys.exit(result.returncode)

    formatted = result.stdout
    if not formatted:
        # bibtex-tidy produced no output — likely a parse failure; leave file alone
        sys.stderr.write(
            f"Warning: bibtex-tidy produced no output for {bib_path}; "
            "file left unchanged.\n"
        )
        sys.stderr.write(result.stderr.decode(errors="replace"))
        sys.exit(1)

    if formatted != content:
        bib_path.write_bytes(formatted)


def main() -> None:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} file.bib [file.bib ...]")
        sys.exit(1)

    args = load_args()
    for path_str in sys.argv[1:]:
        format_bib(Path(path_str), args)


if __name__ == "__main__":
    main()
