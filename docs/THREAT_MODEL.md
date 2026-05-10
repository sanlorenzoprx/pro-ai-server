# DroidShield Threat Model

## Assets

- Host workstation credentials and source repositories.
- Android sandbox node filesystem.
- Agent task prompts, logs, and generated code.
- Network credentials and private service endpoints.

## MVP Trust Boundaries

- AI agents are untrusted task authors.
- The gateway is trusted to authenticate, queue, and enforce policy.
- Android nodes are disposable workers and may be quarantined or wiped.
- The host must not expose secrets to the sandbox unless explicitly mounted or
  transferred through a policy-approved path.

## MVP Controls

- Command allowlist and blocklist.
- Sensitive path denylist.
- Append-only audit records.
- Node quarantine state.
- USB-first transport.
- Kill-switch commands planned at gateway level before broader orchestration.

## Explicit Non-Goals

- Perfect malware containment.
- Enterprise RBAC.
- Full network packet inspection.
- Custom LLM training.
- Running large local models as the primary product value.
