# DroidShield Architecture

DroidShield turns inexpensive Android phones into physically isolated sandbox
nodes for autonomous AI agents. The first product surface is not local model
hosting. It is a safety layer between an agent and the infrastructure the agent
could damage.

## Runtime Shape

```text
AI Agent / MCP Client
        |
        v
DroidShield Gateway
        |
        v
Policy Engine -> Audit Log -> Dashboard / Alerts
        |
        v
Android Sandbox Node
        |
        v
Restricted Tool Runtime
```

## Core Modules

- `droidshield.gateway`: task intake, node selection, policy validation, and
  task receipts.
- `droidshield.policy`: allow/block decisions for commands, sensitive paths,
  and future network rules.
- `droidshield.node_runtime`: Android node identity, capabilities, transport,
  and quarantine state.
- `droidshield.monitoring`: append-only JSONL audit trail for accepted and
  blocked work.
- `droidshield.agentic`: autonomous development loop contracts: observe, plan,
  policy-check, sandbox-execute, verify, report.
- `droidshield.gateway_api`: stdlib HTTP API for node registration, task
  submission, job status, and operator kill requests.

## Gateway API

The MVP API is intentionally small and maps directly to the product handoff:

```text
POST /api/v1/nodes/register
POST /api/v1/tasks
GET  /api/v1/tasks/{job_id}
POST /api/v1/jobs/{job_id}/kill
```

Run it locally with:

```powershell
droidshield gateway-api
```

## Agentic Development Contract

Autonomous development should always produce:

1. Objective and repo context.
2. Proposed commands and file scopes.
3. Policy receipts before execution.
4. Sandbox execution logs.
5. Verification output.
6. Final report with diff summary and residual risk.

This makes agent autonomy inspectable instead of magical.
