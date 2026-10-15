default:
    @just --list

sync:
    uv sync

test:
    uv run pytest -m "not live"

lint:
    uv run ruff format --check
    uv run ruff check

fix:
    uv run ruff format
    uv run ruff check --fix

typecheck:
    uv run basedpyright

layers:
    uv run lint-imports

check: lint typecheck layers test

replay turn db:
    uv run companion replay {{turn}} --db {{db}}

run:
    uv run companion run
