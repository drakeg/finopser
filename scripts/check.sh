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

if [[ "${FINOPSER_CHECK_COMPOSE:-0}" == "1" ]]; then
  echo "==> Docker Compose startup and health"
  cleanup() { docker compose down -v; }
  trap cleanup EXIT
  docker compose build backend frontend
  if ! docker compose up -d --no-build --wait; then
    docker compose ps -a
    docker compose logs --no-color --tail=200 backend worker scheduler frontend postgres redis
    exit 1
  fi
  curl --fail --retry 3 --retry-delay 1 http://127.0.0.1:8080/
  curl --fail --retry 3 --retry-delay 1 http://127.0.0.1:8000/api/ready/
fi

echo "All local quality gates passed."
