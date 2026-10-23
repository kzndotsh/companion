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
    uv run lint-imports --no-cache

check: lint typecheck layers test

replay turn:
    uv run companion replay {{turn}}

# jot an idea into docs/inbox/, e.g. just inbox what if it could say when it disagrees
inbox +text:
    @python3 -c 'import datetime, pathlib, re, sys; t = " ".join(sys.argv[1:]); s = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48] or "note"; p = pathlib.Path("docs/inbox") / f"{datetime.date.today()}-{s}.md"; p.write_text(f"# {t}\n\nAdded {datetime.date.today()}.\n"); print(p)' {{text}}

run:
    uv run companion run

# stop the running bot and start it again here; the "up as" line confirms the persona
restart:
    scripts/restart.sh

# commit only the named files, e.g. just commit "fix(x): message" src/a.py tests/test_a.py
commit message +files:
    scripts/commit.sh "{{message}}" {{files}}

# follow the full debug log (every stage of every turn, judges, model and Telegram calls)
logs:
    tail -n 60 -f data/logs/companion.log

# test coverage by file; a report only, no minimum enforced
cov:
    uv run pytest -m "not live" --cov=companion --cov-report=term-missing:skip-covered -n auto
