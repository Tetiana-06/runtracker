#!/usr/bin/env bash
# Тести з покриттям + запуск sonar-scanner для локального SonarQube.
# Використання: SONAR_TOKEN=xxx ./scripts/scan.sh
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT/backend"
pytest --cov=app --cov-report=xml:coverage.xml

cd "$ROOT"
sonar-scanner \
  -Dsonar.host.url="${SONAR_HOST_URL:-http://localhost:9000}" \
  -Dsonar.token="${SONAR_TOKEN:?Встановіть SONAR_TOKEN}"
