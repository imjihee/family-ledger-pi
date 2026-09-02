#!/usr/bin/env bash
# Start a temporary authenticated Flask API and Cloudflare Quick Tunnel.

set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FLASK_LOG=""
TUNNEL_LOG=""
FLASK_PID=""
TUNNEL_PID=""

cleanup() {
  trap - EXIT INT TERM
  echo
  echo "Stopping Flask and Cloudflare Quick Tunnel..."
  [[ -n "$TUNNEL_PID" ]] && kill "$TUNNEL_PID" 2>/dev/null || true
  [[ -n "$FLASK_PID" ]] && kill "$FLASK_PID" 2>/dev/null || true
  [[ -n "$TUNNEL_PID" ]] && wait "$TUNNEL_PID" 2>/dev/null || true
  [[ -n "$FLASK_PID" ]] && wait "$FLASK_PID" 2>/dev/null || true
  [[ -n "$FLASK_LOG" ]] && rm -f "$FLASK_LOG"
  [[ -n "$TUNNEL_LOG" ]] && rm -f "$TUNNEL_LOG"
}

trap cleanup EXIT INT TERM

cd "$PROJECT_DIR"

if [[ ! -x .venv/bin/python ]]; then
  echo "Error: .venv/bin/python is missing. Install dependencies first." >&2
  exit 1
fi

if [[ ! -x ./bin/cloudflared ]]; then
  echo "Error: ./bin/cloudflared is missing." >&2
  exit 1
fi

if ss -ltn 'sport = :8080' | grep -q LISTEN; then
  echo "Error: port 8080 is already in use. Stop the existing Flask server first." >&2
  exit 1
fi

API_BEARER_TOKEN="$(openssl rand -hex 32)"
export API_BEARER_TOKEN
FLASK_LOG="$(mktemp)"
TUNNEL_LOG="$(mktemp)"

.venv/bin/python app.py >"$FLASK_LOG" 2>&1 &
FLASK_PID=$!

for _ in {1..30}; do
  if curl --silent --output /dev/null http://127.0.0.1:8080/event; then
    break
  fi
  if ! kill -0 "$FLASK_PID" 2>/dev/null; then
    echo "Error: Flask failed to start." >&2
    cat "$FLASK_LOG" >&2
    exit 1
  fi
  sleep 0.2
done

./bin/cloudflared tunnel --url http://localhost:8080 >"$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

TUNNEL_URL=""
for _ in {1..150}; do
  TUNNEL_URL="$(grep -Eo 'https://[^[:space:]]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -n 1 || true)"
  [[ -n "$TUNNEL_URL" ]] && break
  if ! kill -0 "$TUNNEL_PID" 2>/dev/null; then
    echo "Error: Cloudflare Quick Tunnel failed to start." >&2
    cat "$TUNNEL_LOG" >&2
    exit 1
  fi
  sleep 0.2
done

if [[ -z "$TUNNEL_URL" ]]; then
  echo "Error: Timed out waiting for the Quick Tunnel URL." >&2
  cat "$TUNNEL_LOG" >&2
  exit 1
fi

cat <<EOF

Quick Tunnel is ready.

URL:   $TUNNEL_URL/event
TOKEN: $API_BEARER_TOKEN

Example external request:
curl -X POST '$TUNNEL_URL/event' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer $API_BEARER_TOKEN' \\
  -d '{"command":"capture","message":"external test"}'

Keep this terminal open while using the URL. Press Ctrl+C to stop both services.
EOF

tail -n 0 -F "$FLASK_LOG" "$TUNNEL_LOG" &
TAIL_PID=$!
wait "$TUNNEL_PID"
kill "$TAIL_PID" 2>/dev/null || true
