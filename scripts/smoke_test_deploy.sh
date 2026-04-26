#!/usr/bin/env bash
# Quick deployment smoke test — verifies all endpoints work end-to-end.
# Usage:  ./scripts/smoke_test_deploy.sh https://your-render-app.onrender.com

set -euo pipefail

API="${1:?Usage: $0 <https://your-render-app.onrender.com>}"
API="${API%/}"  # strip trailing slash

echo "═══════════════════════════════════════════════════════════════"
echo "Smoke test: ${API}"
echo "═══════════════════════════════════════════════════════════════"

echo
echo "1. /api/health"
curl -fsS "${API}/api/health" | jq .

echo
echo "2. /api/config/countries (auto-discovery proof)"
curl -fsS "${API}/api/config/countries" | jq -r '.[].code'

echo
echo "3. /api/config/BGD (cross-regional proof — Bangladesh)"
curl -fsS "${API}/api/config/BGD" | jq '.country, .ui.script, .labor_data.currency'

echo
echo "4. /api/opportunities/BEN/signals (econometric signal)"
curl -fsS "${API}/api/opportunities/BEN/signals" | jq '.wage.current_estimated_xof, .growth.growth_flagged_sectors'

echo
echo "5. /api/opportunities/BEN (read all opportunities)"
curl -fsS "${API}/api/opportunities/BEN" | jq 'length'

echo
echo "═══════════════════════════════════════════════════════════════"
echo "All endpoints live. Backend deploy verified."
echo "═══════════════════════════════════════════════════════════════"
