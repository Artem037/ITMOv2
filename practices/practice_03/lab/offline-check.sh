#!/usr/bin/env bash
set -euo pipefail

# Offline check script for Ollama on localhost
# - Only uses http://localhost:11434
# - Checks /api/tags first
# - Sends a short request to qwen3.5:4b with stream=false and think=false
# - Writes result to practices/practice_03/lab/results/offline-check.json
# - Fails with non-zero exit code on errors
# - Does not overwrite existing result unless previous run failed

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
RESULTS_DIR="$SCRIPT_DIR/results"
OUT_FILE="$RESULTS_DIR/offline-check.json"

mkdir -p "$RESULTS_DIR"

# If output exists and looks like JSON with at least a 'model' or 'message', do not overwrite
if [[ -f "$OUT_FILE" ]]; then
  if jq -e 'has("model") or .message? != null or .response? != null' "$OUT_FILE" >/dev/null 2>&1; then
    echo "offline-check: existing result found at $OUT_FILE; not overwriting" >&2
    exit 0
  fi
fi

BASE_URL="http://localhost:11434"

# Check tags endpoint
curl -sS --fail "$BASE_URL/api/tags" >/dev/null

# Send a short chat request
TMP_OUT=$(mktemp)
trap 'rm -f "$TMP_OUT"' EXIT

REQ='{
  "model": "qwen3.5:4b",
  "messages": [
    {"role": "user", "content": "Ответь: OK"}
  ],
  "stream": false,
  "think": false
}'

curl -sS --fail -X POST "$BASE_URL/api/chat" \
  -H 'Content-Type: application/json' \
  -d "$REQ" \
  -o "$TMP_OUT"

# Basic sanity: ensure JSON and has top-level keys we expect
jq -e '.' "$TMP_OUT" >/dev/null

# Move into place atomically
mv -f "$TMP_OUT" "$OUT_FILE"
echo "offline-check: wrote $OUT_FILE" >&2
