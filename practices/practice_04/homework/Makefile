.PHONY: install test lint

install:
	uv sync --locked

test:
	uv run --locked --offline python -m unittest discover -s tests -v

lint:
	uv run --locked --offline ruff check .
	uv run --locked --offline ruff format --check .
