#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
CLAIM_NUMBER="${CLAIM_NUMBER:-LOCAL-SMOKE-001}"

require() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require curl
require jq

echo "Checking API health at ${API_BASE_URL}/health"
curl -fsS "${API_BASE_URL}/health" | jq .

echo "Creating claim ${CLAIM_NUMBER}"
CLAIM_RESPONSE="$(
  curl -fsS -X POST "${API_BASE_URL}/v1/claims" \
    -H 'Content-Type: application/json' \
    -d "{
      \"claim_number\": \"${CLAIM_NUMBER}\",
      \"customer_id\": 1001,
      \"claim_type\": \"motor\",
      \"incident_date\": \"2026-07-30\",
      \"claim_amount\": 2400,
      \"description\": \"Local smoke test for graph and tool-calling.\"
    }"
)"
CLAIM_ID="$(printf '%s' "${CLAIM_RESPONSE}" | jq -r '.id')"
echo "Created claim id: ${CLAIM_ID}"

echo "Presigning a PDF document"
PRESIGN_RESPONSE="$(
  curl -fsS -X POST "${API_BASE_URL}/v1/claims/${CLAIM_ID}/documents/presign" \
    -H 'Content-Type: application/json' \
    -d '{
      "file_name": "repair-invoice.pdf",
      "content_type": "application/pdf",
      "run_ocr": true
    }'
)"
DOCUMENT_ID="$(printf '%s' "${PRESIGN_RESPONSE}" | jq -r '.document_id // .document.id')"
echo "Document id: ${DOCUMENT_ID}"

echo "Completing upload in local mock mode"
curl -fsS -X POST "${API_BASE_URL}/v1/claims/${CLAIM_ID}/documents/${DOCUMENT_ID}/complete-upload" \
  -H 'Content-Type: application/json' \
  -d '{}' | jq .

echo "Starting workflow with hitl_required=false"
WORKFLOW_RESPONSE="$(
  curl -fsS -X POST "${API_BASE_URL}/v1/workflows/claims/${CLAIM_ID}/start" \
    -H 'Content-Type: application/json' \
    -d '{
      "hitl_required": false,
      "notes": ["Local smoke test run"]
    }'
)"
printf '%s\n' "${WORKFLOW_RESPONSE}" | jq .

echo "Fetching final claim payload"
curl -fsS "${API_BASE_URL}/v1/claims/${CLAIM_ID}" | jq .
