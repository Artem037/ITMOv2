# Python style for Notify Mini

Source: [PEP 8](https://peps.python.org/pep-0008/), consulted 2026-10-02.
The example to follow is the existing `subscribe` function in `service.py`.

1. Indent with four spaces; do not use tabs.
2. Name functions and variables in `snake_case` (for example, `unsubscribe` and `cleaned_name`).
3. Separate top-level function definitions with two blank lines.
4. Keep Python code lines within 79 characters.

The repository's pre-commit hook checks the demo Python files with Ruff
and runs `make test`. The Ruff rules and formatter check selected here cover
the mechanical style rules; code review still checks naming and clarity.
