# OpenClaw Feishu Multi-Agent Verification Checklist

## 1) Config Integrity

- `openclaw.json` is valid JSON/JSONC
- Every `bindings[].agentId` exists in agent registry
- Every Feishu `peer.id` exists and is reachable
- In multi-bot mode, every `bindings[].match.accountId` exists in `channels.feishu.accounts`

## 2) Feishu App Readiness

- App permissions granted:
  - Baseline:
    - `im:message:send_as_bot`
    - `im:message.p2p_msg:readonly`
  - Mention-required groups:
    - `im:message.group_at_msg:readonly`
  - Mention-free groups:
    - `im:message.group_msg` or `im:message.group_msg:readonly`
- Event subscriptions enabled:
  - `im.message.receive_v1`
  - `card.action.trigger` (if used)
- Bot setting enabled: can be @ in group chat

## 3) Runtime Health

- OpenClaw process restarted successfully
- No auth/config errors in startup logs
- Feishu channel connection is established

## 4) Routing Tests

- Group A -> expected agent only
- Group B -> expected agent only
- Group C -> expected agent only
- No cross-group context leak

## 5) Orchestration Tests

- Supervisor agent can call allowed agents
- Supervisor agent cannot call non-allowlisted agents
- Failure fallback path logs are observable

## 6) Security Checks

- `allowFrom` is not overly broad in production
- No plaintext secrets committed to git
- Rollback file exists and is restorable

## 7) Go/No-Go Gate

- All tests above pass
- Stakeholder signs off route map and fallback behavior
