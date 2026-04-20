#!/usr/bin/env bash
# MCP protocol smoke test for kdp-niche-scorer-mcp.
#
# Usage:
#   # Start the server in another terminal:
#   PORT=8765 PYTHONUTF8=1 uv run python -m kdp_niche_scorer_mcp.server
#
#   # Then run this:
#   MCP_URL=http://localhost:8765 bash test-mcp.sh
#
# Requires a real RAPIDAPI_KEY in .env for live tools/call assertions.

set -euo pipefail

MCP_URL="${MCP_URL:-http://localhost:8765}"
HEALTH_URL="$MCP_URL/health"
MCP_ENDPOINT="$MCP_URL/mcp"

GREEN=$'\033[0;32m'
RED=$'\033[0;31m'
YELLOW=$'\033[0;33m'
BOLD=$'\033[1m'
NC=$'\033[0m'

pass() { echo "${GREEN}PASS${NC} $1"; }
fail() { echo "${RED}FAIL${NC} $1"; exit 1; }
warn() { echo "${YELLOW}WARN${NC} $1"; }

mcp_headers() {
  echo "-H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream'"
}

# Strip the "event: message\ndata: " prefix from Streamable HTTP responses.
strip_sse() { sed -n 's/^data: //p'; }

echo "${BOLD}==> Waiting for health endpoint at $HEALTH_URL${NC}"
for i in 1 2 3 4 5 6 7 8 9 10; do
  if curl -s -f "$HEALTH_URL" >/dev/null 2>&1; then
    pass "health endpoint is up"
    break
  fi
  if [ "$i" = "10" ]; then
    fail "server did not come up at $HEALTH_URL"
  fi
  sleep 1
done

echo
echo "${BOLD}==> 1. initialize handshake (capture session id)${NC}"
INIT_RAW=$(curl -s -i -X POST "$MCP_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test-mcp.sh","version":"1.0"}}}')

SID=$(echo "$INIT_RAW" | grep -i "^mcp-session-id:" | tr -d '\r' | awk '{print $2}')
if [ -z "$SID" ]; then
  fail "no mcp-session-id header in initialize response"
fi
pass "initialize returned session id ${SID:0:8}..."

# Send required initialized notification
curl -s -X POST "$MCP_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","method":"notifications/initialized"}' >/dev/null

echo
echo "${BOLD}==> 2. tools/list${NC}"
LIST_RESPONSE=$(curl -s -X POST "$MCP_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' | strip_sse)

for tool in score_niche get_top_competitors estimate_sales_from_bsr; do
  if echo "$LIST_RESPONSE" | grep -q "\"$tool\""; then
    pass "tool registered: $tool"
  else
    fail "tool not registered: $tool"
  fi
done

echo
echo "${BOLD}==> 3. tools/call estimate_sales_from_bsr (offline — no API key needed)${NC}"
EST_RESPONSE=$(curl -s -X POST "$MCP_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"estimate_sales_from_bsr","arguments":{"bsr":45000,"price":6.99}}}' | strip_sse)

if echo "$EST_RESPONSE" | grep -q '"monthly_revenue":440'; then
  pass 'estimate_sales_from_bsr returned expected revenue (440/mo at BSR 45k, 6.99 Kindle)'
elif echo "$EST_RESPONSE" | grep -q '"monthly_revenue"'; then
  pass "estimate_sales_from_bsr returned monthly_revenue"
else
  fail "estimate_sales_from_bsr response missing monthly_revenue: $EST_RESPONSE"
fi

echo
echo "${BOLD}==> 4. tools/call score_niche (live — requires RAPIDAPI_KEY)${NC}"
SCORE_RESPONSE=$(curl -s -X POST "$MCP_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"score_niche","arguments":{"keyword":"low content journal","marketplace":"US"}}}' | strip_sse)

if echo "$SCORE_RESPONSE" | grep -q 'RAPIDAPI_KEY is not configured'; then
  warn "score_niche: RAPIDAPI_KEY not set — set it in .env for full live verification"
elif echo "$SCORE_RESPONSE" | grep -q '"score":[0-9]'; then
  SCORE=$(echo "$SCORE_RESPONSE" | grep -oE '"score":[0-9]+' | head -1 | cut -d: -f2)
  pass "score_niche returned score=$SCORE for 'low content journal'"
elif echo "$SCORE_RESPONSE" | grep -q '"verdict":"no_data"'; then
  warn "score_niche: keyword returned no results (broaden the keyword)"
else
  warn "score_niche unexpected: $(echo "$SCORE_RESPONSE" | head -c 300)"
fi

echo
echo "${BOLD}==> 5. tools/call get_top_competitors (live — requires RAPIDAPI_KEY)${NC}"
COMP_RESPONSE=$(curl -s -X POST "$MCP_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"get_top_competitors","arguments":{"keyword":"tarot for beginners","n":5,"marketplace":"US"}}}' | strip_sse)

if echo "$COMP_RESPONSE" | grep -q 'RAPIDAPI_KEY is not configured'; then
  warn "get_top_competitors: RAPIDAPI_KEY not set"
elif echo "$COMP_RESPONSE" | grep -q '"competitors"'; then
  COUNT=$(echo "$COMP_RESPONSE" | grep -oE '"asin":"[^"]+' | wc -l)
  pass "get_top_competitors returned $COUNT competitors"
else
  warn "get_top_competitors unexpected: $(echo "$COMP_RESPONSE" | head -c 300)"
fi

echo
echo "${BOLD}==> 6. ping${NC}"
PING_RESPONSE=$(curl -s -X POST "$MCP_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Mcp-Session-Id: $SID" \
  -d '{"jsonrpc":"2.0","id":6,"method":"ping"}' | strip_sse)

if echo "$PING_RESPONSE" | grep -q '"jsonrpc"'; then
  pass "ping returned a JSON-RPC response"
else
  fail "ping failed: $PING_RESPONSE"
fi

echo
echo "${GREEN}${BOLD}Smoke test complete.${NC}"
