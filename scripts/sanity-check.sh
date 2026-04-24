#!/usr/bin/env bash
set -euo pipefail

# Health check all local services

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  ✓ $name"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $name"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Sanity Check ==="
echo ""

echo "Services:"
check "Postgres" "pg_isready -h localhost -p 5432 -U postgres"
check "Redis" "redis-cli -h localhost -p 6379 ping"

echo ""
echo "API:"
check "FastAPI health" "curl -sf http://localhost:8000/health"

echo ""
echo "Frontend:"
check "Next.js" "curl -sf http://localhost:3000"

echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "All checks passed ($PASS/$((PASS + FAIL)))"
  exit 0
else
  echo "$FAIL check(s) failed. $PASS/$((PASS + FAIL)) passed."
  exit 1
fi
