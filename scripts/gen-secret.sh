#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# gen-secret.sh — Bootstrap AWS Ghost Developer secrets
#
# Usage:
#   ./scripts/gen-secret.sh [dev|staging|prod]
#
# What it does:
#   1. Generates a cryptographically secure API key
#   2. Deploys infra/secrets.yaml via CloudFormation
#   3. Prints the key for you to put in mcp_config.json
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

ENVIRONMENT="${1:-prod}"
STACK_NAME="aws-ghost-developer-secrets-${ENVIRONMENT}"
REGION="${AWS_DEFAULT_REGION:-ap-southeast-1}"
TEMPLATE_PATH="$(dirname "$0")/../infra/secrets.yaml"

# ── Validate environment ──────────────────────────────────────────────────────
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
  echo "ERROR: Environment must be dev, staging, or prod"
  exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " AWS Ghost Developer — Secret Bootstrap"
echo " Environment : ${ENVIRONMENT}"
echo " Region      : ${REGION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Generate API key ──────────────────────────────────────────────────────────
API_KEY=$(openssl rand -base64 48 | tr -d '/+=' | head -c 48)
echo ""
echo "Generated API key (save this — shown only once):"
echo ""
echo "  ${API_KEY}"
echo ""
read -r -p "Continue deploying to ${ENVIRONMENT}? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 0
fi

# ── Check if stack exists (create vs update) ─────────────────────────────────
if aws cloudformation describe-stacks \
     --stack-name "$STACK_NAME" \
     --region "$REGION" \
     --query "Stacks[0].StackStatus" \
     --output text 2>/dev/null | grep -q "COMPLETE"; then
  ACTION="update-stack"
  echo "Updating existing stack: ${STACK_NAME}"
else
  ACTION="create-stack"
  echo "Creating new stack: ${STACK_NAME}"
fi

aws cloudformation ${ACTION} \
  --stack-name "$STACK_NAME" \
  --region "$REGION" \
  --template-body "file://${TEMPLATE_PATH}" \
  --parameters \
    ParameterKey=Environment,ParameterValue="${ENVIRONMENT}" \
    ParameterKey=ApiKeyValue,ParameterValue="${API_KEY}" \
  --capabilities CAPABILITY_NAMED_IAM

echo ""
echo "Waiting for stack to complete..."
aws cloudformation wait stack-${ACTION//-stack/}-complete \
  --stack-name "$STACK_NAME" \
  --region "$REGION"

SECRET_NAME="${ENVIRONMENT}/ghost-developer/api-key"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " Done! Add this to mcp_config.json:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  \"headers\": {"
echo "    \"x-api-key\": \"${API_KEY}\""
echo "  }"
echo ""
echo "Secret stored at: ${SECRET_NAME}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
