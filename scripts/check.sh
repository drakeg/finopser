#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Backend lint"
python -m ruff check backend

echo "==> Django system and migration checks"
python backend/manage.py check
python backend/manage.py makemigrations --check --dry-run

echo "==> Backend tests"
python backend/manage.py test

echo "==> CLI tests"
python -m unittest discover -s cli/tests -v

echo "==> Frontend lint and build"
(
  cd frontend
  npm run lint
  npm run build
)

echo "==> Docker Compose validation"
docker compose config >/dev/null

echo "All local quality gates passed."
