#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# bootstrap.sh — AWS Ghost Developer v1.0 — Full Setup
#
# Usage:
#   ./scripts/bootstrap.sh [dev|staging|prod]
#
# Steps:
#   1. Generate API key & deploy secrets stack (infra/secrets.yaml)
#   2. Build & deploy main SAM stack (template.yaml)
#   3. Print MCP endpoint + config snippet
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ENVIRONMENT="${1:-prod}"
if [[ -z "${AWS_DEFAULT_REGION:-}" ]]; then
  echo "ERROR: AWS_DEFAULT_REGION is not set."
  echo "  export AWS_DEFAULT_REGION=ap-southeast-1"
  exit 1
fi
REGION="$AWS_DEFAULT_REGION"
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Convert Git Bash /c/... paths to Windows C:/... paths for AWS CLI
if command -v cygpath >/dev/null 2>&1; then
  ROOT_DIR_WIN="$(cygpath -w "$ROOT_DIR")"
else
  ROOT_DIR_WIN="$ROOT_DIR"
fi

SECRETS_STACK="aws-ghost-developer-secrets-${ENVIRONMENT}"
APP_STACK="aws-ghost-developer-${ENVIRONMENT}"

# ── Validation ────────────────────────────────────────────────────────────────
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
  echo "ERROR: Environment must be dev, staging, or prod"
  exit 1
fi

command -v aws  >/dev/null 2>&1 || { echo "ERROR: aws CLI not found"; exit 1; }
command -v sam  >/dev/null 2>&1 || { echo "ERROR: sam CLI not found. Install: pip install aws-sam-cli"; exit 1; }
command -v openssl >/dev/null 2>&1 || { echo "ERROR: openssl not found"; exit 1; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AWS Ghost Developer v1.0 — Bootstrap"
echo "  Environment : ${ENVIRONMENT}"
echo "  Region      : ${REGION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 1: Secrets ───────────────────────────────────────────────────────────
echo "[ 1/2 ] Setting up secrets..."
echo ""

API_KEY=$(openssl rand -base64 48 | tr -d '/+=' | head -c 48)

echo "Generated API key (save this — shown only once):"
echo ""
echo "  ${API_KEY}"
echo ""
read -r -p "Continue? [y/N] " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name "$SECRETS_STACK" \
  --region "$REGION" \
  --query "Stacks[0].StackStatus" \
  --output text 2>/dev/null || echo "DOES_NOT_EXIST")

SECRET_NAME="${ENVIRONMENT}/ghost-developer/api-key"

if [[ "$STACK_STATUS" == "DOES_NOT_EXIST" ]] || [[ "$STACK_STATUS" == "DELETE_COMPLETE" ]]; then
  echo "Creating secrets stack: ${SECRETS_STACK}"
  aws cloudformation create-stack \
    --stack-name "$SECRETS_STACK" \
    --region "$REGION" \
    --template-body "file://${ROOT_DIR_WIN}/infra/secrets.yaml" \
    --parameters \
      ParameterKey=Environment,ParameterValue="${ENVIRONMENT}" \
      ParameterKey=ApiKeyValue,ParameterValue="${API_KEY}" \
    --capabilities CAPABILITY_NAMED_IAM \
    --output text > /dev/null

  echo "Waiting for secrets stack..."
  aws cloudformation wait stack-create-complete \
    --stack-name "$SECRETS_STACK" \
    --region "$REGION"
else
  echo "Secrets stack exists (${STACK_STATUS}). Updating secret value directly..."
  aws secretsmanager put-secret-value \
    --secret-id "$SECRET_NAME" \
    --secret-string "{\"api_key\": \"${API_KEY}\"}" \
    --region "$REGION" \
    --output text > /dev/null
fi

echo "Secrets stack ready."
echo ""

# ── Step 2: SAM Build & Deploy ────────────────────────────────────────────────
echo "[ 2/2 ] Building and deploying SAM stack..."
echo ""

cd "$ROOT_DIR"

sam build --cached --parallel

sam deploy \
  --stack-name "$APP_STACK" \
  --region "$REGION" \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides "Environment=${ENVIRONMENT}" \
  --resolve-s3 \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset

# ── Done — print config snippet ───────────────────────────────────────────────
MCP_URL=$(aws cloudformation describe-stacks \
  --stack-name "$APP_STACK" \
  --region "$REGION" \
  --query "Stacks[0].Outputs[?OutputKey=='McpEndpoint'].OutputValue" \
  --output text)

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done! Add this to mcp_config.json:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo '  {'
echo '    "mcpServers": {'
echo '      "aws-ghost-developer": {'
echo "        \"url\": \"${MCP_URL}\","
echo '        "transport": "http",'
echo '        "headers": {'
echo "          \"x-api-key\": \"${API_KEY}\""
echo '        }'
echo '      }'
echo '    }'
echo '  }'
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
