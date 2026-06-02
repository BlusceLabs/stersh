#!/bin/bash
# smoke_test.sh — full end-to-end smoke test for the Watchfy stack.
#
# Verifies that the running stack responds correctly to real HTTP
# requests, that all services are healthy, and that the security
# posture is intact. Run after `make up` or `make docker-up`.
#
# Usage:
#   ./smoke_test.sh
#   FRONTEND_URL=http://localhost:4321 ./smoke_test.sh
#   GATEWAY_URL=http://localhost:8080 ./smoke_test.sh
#
# Exit codes:
#   0  all checks passed
#   1  one or more checks failed

set -uo pipefail

FRONTEND_URL="${FRONTEND_URL:-http://localhost:4321}"
EXTRACTOR_URL="${EXTRACTOR_URL:-http://localhost:8000}"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8080}"

PASS=0
FAIL=0

# ── Color output ────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  GREEN=$'\033[0;32m'
  RED=$'\033[0;31m'
  YELLOW=$'\033[0;33m'
  BOLD=$'\033[1m'
  RESET=$'\033[0m'
else
  GREEN=""
  RED=""
  YELLOW=""
  BOLD=""
  RESET=""
fi

check() {
  local name="$1"
  local result="$2"
  if [ "$result" = "ok" ]; then
    echo "${GREEN}✓${RESET} ${name}"
    PASS=$((PASS + 1))
  else
    echo "${RED}✗${RESET} ${name}"
    [ -n "${3:-}" ] && echo "  ${YELLOW}${3}${RESET}"
    FAIL=$((FAIL + 1))
  fi
}

# Helper: fetch headers for a URL. Returns "ok" if the status is < 400.
check_status() {
  local url="$1"
  local expected_max="${2:-399}"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")
  if [ "$code" -ge 200 ] && [ "$code" -le "$expected_max" ]; then
    echo "ok"
  else
    echo "fail:$code"
  fi
}

# Helper: check a response header is present and matches an expected value.
check_header() {
  local url="$1"
  local header="$2"
  local expected="$3"
  local actual
  actual=$(curl -s -I --max-time 10 "$url" 2>/dev/null | tr -d '\r' | grep -i "^${header}:" | head -1 | cut -d':' -f2- | sed 's/^ *//')
  if [ -z "$expected" ]; then
    if [ -n "$actual" ]; then echo "ok"; else echo "fail:header missing"; fi
  else
    if echo "$actual" | grep -qi "$expected"; then echo "ok"; else echo "fail:got '$actual'"; fi
  fi
}

echo "${BOLD}Watchfy smoke test${RESET}"
echo "  Frontend:  $FRONTEND_URL"
echo "  Extractor: $EXTRACTOR_URL"
echo "  Gateway:   $GATEWAY_URL"
echo

# ── Service health ─────────────────────────────────────────────────────────
echo "${BOLD}Service health${RESET}"

result=$(check_status "$FRONTEND_URL/")
check "Frontend reachable (/)" "$result" "${result#fail:}"

result=$(check_status "$EXTRACTOR_URL/api/health")
check "Extractor /api/health" "$result" "${result#fail:}"

result=$(check_status "$EXTRACTOR_URL/api/version")
check "Extractor /api/version" "$result" "${result#fail:}"

result=$(check_status "$GATEWAY_URL/health")
check "Gateway /health" "$result" "${result#fail:}"

result=$(check_status "$FRONTEND_URL/health")
check "Frontend /health (Docker HEALTHCHECK target)" "$result" "${result#fail:}"

echo

# ── Security headers ───────────────────────────────────────────────────────
echo "${BOLD}Security headers${RESET}"

# HSTS only fires on HTTPS in production, so the local HTTP frontend
# will not send it. The header presence test is best-effort.
result=$(check_header "$FRONTEND_URL/" "X-Content-Type-Options" "nosniff")
check "X-Content-Type-Options: nosniff" "$result" "${result#fail:}"

result=$(check_header "$FRONTEND_URL/" "X-Frame-Options" "SAMEORIGIN")
check "X-Frame-Options: SAMEORIGIN" "$result" "${result#fail:}"

result=$(check_header "$FRONTEND_URL/" "Referrer-Policy" "strict-origin-when-cross-origin")
check "Referrer-Policy" "$result" "${result#fail:}"

result=$(check_header "$FRONTEND_URL/" "Content-Security-Policy" "default-src")
check "Content-Security-Policy" "$result" "${result#fail:}"

result=$(check_header "$FRONTEND_URL/" "Permissions-Policy" "camera=()")
check "Permissions-Policy disables camera" "$result" "${result#fail:}"

result=$(check_header "$FRONTEND_URL/" "Cross-Origin-Opener-Policy" "same-origin")
check "Cross-Origin-Opener-Policy" "$result" "${result#fail:}"

echo

# ── API surface ────────────────────────────────────────────────────────────
echo "${BOLD}API surface${RESET}"

# TMDB passthrough
result=$(check_status "$EXTRACTOR_URL/api/tmdb/trending/movie/week")
check "TMDB trending (movies)" "$result" "${result#fail:}"

result=$(check_status "$EXTRACTOR_URL/api/tmdb/trending/tv/week")
check "TMDB trending (TV)" "$result" "${result#fail:}"

# CORS preflight
result=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
  -X OPTIONS \
  -H "Origin: $FRONTEND_URL" \
  -H "Access-Control-Request-Method: GET" \
  "$EXTRACTOR_URL/api/tmdb/trending/movie/week")
if [ "$result" -ge 200 ] && [ "$result" -lt 400 ]; then
  check "CORS preflight (OPTIONS) accepted" "ok"
else
  check "CORS preflight (OPTIONS) accepted" "fail:$result"
fi

echo

# ── Manual verification checklist ──────────────────────────────────────────
cat <<EOF
${BOLD}Manual verification checklist${RESET} (cannot be automated)
  [ ] Open $FRONTEND_URL/ in a browser, hero carousel auto-rotates
  [ ] Click a media card, details page loads with poster + metadata
  [ ] Click "Play", HLS stream starts within 5 seconds
  [ ] Switch server (white <-> black), stream re-binds without page reload
  [ ] On a TV show, switch season, episode list updates
  [ ] On a TV show, click "Next Episode", URL updates and player rebinds
  [ ] Press the browser back button, watch position is restored (continue watching)
  [ ] Open $FRONTEND_URL/ in a mobile viewport (<768px), bottom nav appears
  [ ] In mobile viewport, tap a nav item, navigates correctly
  [ ] In mobile viewport, tap targets are at least 44px (DevTools a11y audit)
  [ ] Navigate to /search, type a query, results appear after 350ms debounce
  [ ] Navigate to /search?q=avengers, deep link works
  [ ] Sign in flow works (if you have an account)
  [ ] Add to My List, refresh, item persists
  [ ] Open the same movie in two tabs, close both, reopen — Continue Watching
      shows the same progress (continue_watching backend test)
EOF

echo
echo "${BOLD}Summary${RESET}: ${GREEN}${PASS} passed${RESET}, ${RED}${FAIL} failed${RESET}"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
exit 0
