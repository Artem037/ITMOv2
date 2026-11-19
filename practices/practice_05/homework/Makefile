.PHONY: serve serve-fixture test python-test browser-test lint

ROOT := $(abspath ../../..)
CORE := $(ROOT)/practices/practice_04/homework
PORT ?= 8765
NODE := $(shell command -v node 2>/dev/null || echo "$(HOME)/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
UV := uv run --project "$(CORE)" --locked --offline

serve:
	$(UV) python web/server.py --port $(PORT)

serve-fixture:
	$(UV) python web/server.py --fixture --port $(PORT)

test: python-test browser-test

python-test:
	$(UV) python -m unittest discover -s tests -p 'test_adapter.py' -v

browser-test:
	"$(NODE)" --test tests/browser.test.mjs

lint:
	$(UV) ruff check --extend-select=E501,I --line-length=79 web tests
	$(UV) ruff format --check --line-length=79 web tests
