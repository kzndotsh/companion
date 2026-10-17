#!/usr/bin/env bash
# Commit only the named files. Usage: just commit "feat(x): message" path [path...]
set -euo pipefail

msg="${1:-}"
shift || true
if [[ -z "$msg" || $# -eq 0 ]]; then
  echo "usage: just commit \"message\" file [file...]" >&2
  exit 2
fi

for f in "$@"; do
  case "$f" in
    . | .. | -* | */) echo "name files, not '$f' (no directories, no flags)" >&2; exit 2 ;;
    .env | data/* | evals/local/* | evals/results/*)
      echo "never commit '$f'" >&2; exit 2 ;;
  esac
  [[ -f "$f" ]] || git ls-files --deleted --error-unmatch -- "$f" >/dev/null 2>&1 \
    || { echo "no such file: $f" >&2; exit 2; }
done

if echo "$msg" | grep -Eiq 'co-authored-by|generated with|claude code'; then
  echo "no attribution lines in commit messages" >&2
  exit 2
fi

if ! git diff --cached --quiet; then
  echo "something is already staged; unstage it first (git restore --staged <path>):" >&2
  git diff --cached --name-only >&2
  exit 2
fi

git add -- "$@"
git commit -q -m "$msg"
git log --oneline -1
