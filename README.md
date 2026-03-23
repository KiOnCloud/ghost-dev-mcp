# AWS Ghost Developer — MCP Serverless Agent

**Version: 1.0**

An MCP (Model Context Protocol) server running on AWS Lambda that acts as a secure proxy between an AI assistant (Claude, Cursor) and your AWS infrastructure. It gives the AI read-only access to your systems so it can help investigate incidents without needing human copy-paste of logs.

---

## What it does (v1.0)

This version focuses on **triage** — collecting raw data from two sources fast enough that an AI can summarize what is failing and where.

| Tool | What it answers |
|---|---|
| `list_dlqs` | "Which Dead Letter Queues have messages piling up?" |
| `inspect_dlq_payload` | "What do those failed messages look like?" |
| `search_log_groups` | "Which CloudWatch log groups exist for this service?" |
| `get_error_traces` | "What errors appeared in these log groups recently?" |

### Honest scope

v1.0 helps an AI identify **symptoms** (error messages, failed payloads) but does not determine root cause automatically. It is most useful for:

- On-call triage at odd hours — reduce time-to-data from 30+ minutes to under a minute
- Letting a junior engineer hand off context to an AI before escalating
- Situations where copy-pasting logs manually is the main bottleneck

It does **not** (yet) cover: X-Ray service maps, deployment correlation, infrastructure metrics.

---

## Architecture

```
Claude / Cursor
      │  HTTPS + x-api-key header
      ▼
API Gateway (HTTP API)
      │
      ▼  Lambda Authorizer (validates API key via Secrets Manager)
      ▼
Lambda: mcp-router
      ├── SQS   → list_dlqs, inspect_dlq_payload
      └── Logs  → search_log_groups, get_error_traces
```

Two CloudFormation stacks:

- `aws-ghost-developer-secrets-{env}` — manages the API key in Secrets Manager
- `aws-ghost-developer-{env}` — Lambda, API Gateway, IAM roles (deployed via SAM)

---

## Prerequisites

- AWS CLI configured (`aws configure`)
- AWS SAM CLI (`pip install aws-sam-cli`)
- Python 3.12+
- `openssl` (available on macOS/Linux by default)

---

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd aws-ghost-developer
pip install -r requirements.txt
```

### 2. Run bootstrap (one command does everything)

```bash
./scripts/bootstrap.sh prod
```

This will:
1. Generate a cryptographically secure API key
2. Deploy `infra/secrets.yaml` to store the key in Secrets Manager
3. Build and deploy the SAM stack
4. Print the final `mcp_config.json` snippet

For other environments:

```bash
./scripts/bootstrap.sh dev
./scripts/bootstrap.sh staging
```

### 3. Add to your MCP client

Paste the printed config into your Claude Desktop or Cursor MCP config file.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "aws-ghost-developer": {
      "url": "https://<api-id>.execute-api.ap-southeast-1.amazonaws.com/mcp",
      "transport": "http",
      "headers": {
        "x-api-key": "<your-generated-key>"
      }
    }
  }
}
```

---

## Usage examples

Once connected, you can ask the AI naturally:

> "Check if there are any failed messages in our SQS queues for the payment service"

> "Look at the dead letter queue for order-processor and tell me what's failing"

> "Find the CloudWatch logs for the auth service and show me errors from the last hour"

> "Search log groups for 'checkout' and query them for 5xx errors in the last 30 minutes"

---

## Project structure

```
aws-ghost-developer/
├── src/
│   ├── handler.py              # Lambda entrypoint, MCP JSON-RPC router
│   ├── authorizer.py           # Lambda authorizer — validates x-api-key
│   ├── transport/
│   │   └── sse.py              # MCP response/error formatters
│   ├── tools/
│   │   ├── __init__.py         # Tool registry
│   │   ├── list_dlqs.py        # List SQS Dead Letter Queues
│   │   ├── inspect_dlq.py      # Peek at DLQ messages
│   │   ├── search_log_groups.py # Discover CloudWatch log groups
│   │   └── get_error_traces.py  # Query Logs Insights (async-safe)
│   └── utils/
│       ├── redact.py           # Auto-redact secrets from responses
│       └── secrets.py          # Secrets Manager wrapper with TTL cache
├── infra/
│   └── secrets.yaml            # CloudFormation — Secrets Manager stack
├── scripts/
│   ├── bootstrap.sh            # Full setup: secrets + SAM deploy
│   └── gen-secret.sh           # Secrets only (for key rotation)
├── tests/
│   └── unit/
├── template.yaml               # SAM template — Lambda + API Gateway
├── samconfig.toml              # SAM deploy defaults
└── requirements.txt
```

---

## Security

- All tools are **read-only**. No write/delete permissions are granted.
- API key is stored in AWS Secrets Manager, never in environment variables.
- The Lambda authorizer validates every request using constant-time comparison.
- IAM role follows least-privilege — each permission is scoped to the minimum required action.
- DLQ messages are peeked with a 30-second visibility timeout and **never deleted**.
- Sensitive values (passwords, tokens) in message payloads are automatically redacted before being returned to the AI.

---

## Rotating the API key

```bash
./scripts/gen-secret.sh prod
```

Then update `mcp_config.json` with the new key. No redeployment needed.

---

## Running tests

```bash
pip install pytest
python -m pytest tests/unit/ -v
```

---

## Roadmap

v1.0 covers triage. Planned for future versions:

- **v1.1** — X-Ray service map (`get_service_map`) to trace which service in a chain is failing
- **v1.2** — Deployment correlation (`get_recent_deployments`) via CloudTrail to link errors to releases
- **v2.0** — Multi-region support, structured RCA report generation
