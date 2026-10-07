#!/bin/sh
# One read-only check command, independent of the caller's current directory.
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$TASK_ROOT"
uvx --from ruff==0.16.10 ruff check --extend-select=E501,I --line-length=79 practices/practice_03/lab/demo
uvx --from ruff==0.16.10 ruff format --check --line-length=79 practices/practice_03/lab/demo
make -C practices/practice_03/lab/demo test
