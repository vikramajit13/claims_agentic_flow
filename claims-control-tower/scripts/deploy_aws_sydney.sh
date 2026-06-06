#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/infra/aws_cdk"

AWS_REGION="${AWS_REGION:-ap-southeast-2}"
STAGE="${STAGE:-prod}"
OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://host.docker.internal:11434}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.1:8b}"
LANGSMITH_PROJECT="${LANGSMITH_PROJECT:-claims-control-tower}"
LANGSMITH_API_KEY="${LANGSMITH_API_KEY:-}"

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required." >&2
  exit 1
fi

if ! command -v cdk >/dev/null 2>&1; then
  echo "AWS CDK is required. Install with: npm install -g aws-cdk" >&2
  exit 1
fi

if [[ -z "$LANGSMITH_API_KEY" ]]; then
  echo "LANGSMITH_API_KEY must be set in the environment before deployment." >&2
  exit 1
fi

ACCOUNT_ID="${CDK_DEFAULT_ACCOUNT:-$(aws sts get-caller-identity --query Account --output text)}"

cd "$INFRA_DIR"

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

export CDK_DEFAULT_ACCOUNT="$ACCOUNT_ID"
export CDK_DEFAULT_REGION="$AWS_REGION"

cdk bootstrap "aws://${ACCOUNT_ID}/${AWS_REGION}"

cdk deploy --require-approval never \
  -c account="$ACCOUNT_ID" \
  -c region="$AWS_REGION" \
  -c stage="$STAGE" \
  -c ollamaBaseUrl="$OLLAMA_BASE_URL" \
  -c ollamaModel="$OLLAMA_MODEL" \
  -c langsmithProject="$LANGSMITH_PROJECT" \
  -c langsmithApiKey="$LANGSMITH_API_KEY"
