#!/bin/sh
# One read-only check command, independent of the caller's current directory.
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$TASK_ROOT"
TASK_HW=practices/practice_04/homework
uv run --project "$TASK_HW" --locked --offline ruff check --extend-select=E501,I --line-length=79 practices/practice_03/lab/demo "$TASK_HW"
uv run --project "$TASK_HW" --locked --offline ruff format --check --line-length=79 practices/practice_03/lab/demo "$TASK_HW"
make -C practices/practice_03/lab/demo test
make -C "$TASK_HW" test
if command -v node >/dev/null 2>&1; then
  node --test tests/check-after-edit.test.mjs
elif [ -x "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node" ]; then
  "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node" --test tests/check-after-edit.test.mjs
else
  echo "Node.js required for hook tests; install Node.js and rerun." >&2
  exit 1
fi
