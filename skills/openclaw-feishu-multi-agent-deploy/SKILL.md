---
name: openclaw-feishu-multi-agent-deploy
description: Use when deploying or troubleshooting OpenClaw with Feishu in single-bot or multi-bot multi-agent routing, including credential collection, bindings, verification, and go-live checks.
---

# OpenClaw Feishu Multi-Agent Deploy

## Overview

Deploy OpenClaw + Feishu with predictable routing, low token cost, and fast validation.
This skill supports two production modes:

1. Single bot, multi-agent routing by chat binding
2. Multi bot, multi-agent routing by account + chat binding

## Preflight Inputs (Collect First)

Use `templates/deployment-inputs.example.yaml` and collect all required values before config edits.

Minimum required:
- OpenClaw host and process control command
- Feishu `appId` and `appSecret` (per bot/account)
- Feishu chat IDs (`oc_...`) for each target group
- Feishu user Open IDs (`ou_...`) if DM allowlist is enabled
- Agent IDs and their model/workspace mapping

Optional but recommended:
- Webhook callback URL + verification token (if using webhook mode)
- Dedicated supervisor agent ID for orchestration
- Rollback snapshot path for previous `openclaw.json`

## Mode Selection

Use single-bot mode when one visual bot is enough and routing happens by group.
Use multi-bot mode when each function/team needs a distinct bot identity in Feishu.

## Existing Deployment Compatibility (Brownfield Mode)

This skill is designed to work on already-running OpenClaw deployments.
Use **non-destructive incremental changes** instead of full-file replacement.

Brownfield rules:
- Always back up current `openclaw.json` before edits.
- Preserve unrelated keys and existing channels.
- Patch only the minimum required paths:
  - `channels.feishu`
  - `bindings`
  - `tools.agentToAgent` (if explicitly enabled)
- Do not remove existing routes unless explicitly requested.
- Run canary validation in one mapped group before full rollout.

Recommended brownfield sequence:
1. Snapshot current config and service status.
2. Build a route diff (add/update/delete) and review impact.
3. Apply additive patch first (new accounts/groups/bindings).
4. Restart service once, validate canary group.
5. Expand rollout to remaining groups.
6. Keep rollback snapshot until final sign-off.

## Deployment Workflow

1. Create and prepare agents

```bash
openclaw agents add writer --model deepseek/deepseek-chat --workspace ~/.openclaw/workspace-writer
openclaw agents add brainstorm --model zai/glm-4.7 --workspace ~/.openclaw/workspace-brainstorm
openclaw agents set-identity --agent writer --name "Writer" --emoji "✍️"
openclaw agents set-identity --agent brainstorm --name "Brainstorm" --emoji "🧠"
```

2. Configure Feishu channel
- Single-bot template: `templates/openclaw-single-bot-route.example.jsonc`
- Multi-bot template: `templates/openclaw-multi-bot-route.example.jsonc`

3. Add `bindings` routes
- Route by `channel=feishu` + `peer.kind=group` + `peer.id=oc_xxx`
- For multi-bot mode, add `accountId` in both channel account and binding match

4. Optional agent-to-agent orchestration

```json
{
  "tools": {
    "agentToAgent": {
      "enabled": true,
      "allow": ["main", "writer", "brainstorm", "coder"]
    }
  }
}
```

5. Restart and verify
- Restart OpenClaw
- Send test messages in each mapped Feishu group
- Confirm replies come from the expected agent identity and model behavior

## Change Safety (Required for Production)

- Avoid full rewrite of `openclaw.json` on customer environments.
- Prefer explicit change plan with three lists:
  - `to_add`
  - `to_update`
  - `to_keep_unchanged`
- Detect and resolve binding conflicts before restart:
  - same `channel/accountId/peer.id` matching multiple agents
  - stale bindings targeting removed agents
- Keep one-command rollback procedure documented in deployment ticket.

## Feishu Platform Settings Checklist

App permissions (pick by interaction mode):
- Baseline (always):
  - `im:message:send_as_bot`
  - `im:message.p2p_msg:readonly`
- If `requireMention: true` (mention-driven groups):
  - `im:message.group_at_msg:readonly`
- If `requireMention: false` (mention-free groups):
  - `im:message.group_msg` or `im:message.group_msg:readonly` (tenant-dependent naming)

Event subscriptions:
- `im.message.receive_v1`
- `card.action.trigger` (if card callbacks are used)

Bot setting:
- Enable "Bot can be @ in group chat"

Policy defaults for production:
- Prefer `dmPolicy: allowlist` or `pairing`, avoid `open` unless explicitly required
- Prefer explicit group control over broad wildcard behavior
- In multi-bot groups with mention-free mode, validate duplicate-trigger risk before rollout

## Troubleshooting Quick Table

- Symptom: Group message not triggering
  - Check `requireMention`; if `false`, ensure `group_msg` scope is approved and events are enabled
  - If `requireMention` is `true`, verify `group_at_msg:readonly` is approved
  - Check binding `peer.id` matches exact `oc_...` chat ID
- Symptom: Wrong agent responds
  - Check overlapping bindings and route precedence
  - In multi-bot mode, verify `accountId` exists and matches binding
- Symptom: Bot online but no inbound events
  - Verify connection mode (`websocket` vs `webhook`) and webhook verification token
  - Re-check event subscription status in Feishu console
- Symptom: DM blocked unexpectedly
  - Check `dmPolicy` and `allowFrom` Open IDs

## Validation SOP (Must Pass Before Go-Live)

1. Routing test: each Feishu group hits only the intended agent
2. Identity test: agent name/emoji/persona matches expected role
3. Isolation test: context from one group does not leak into another
4. Orchestration test: supervisor agent can call allowed sub-agents
5. Security test: no broad wildcard allowlist unless explicitly required

## Notes

- Some docs/examples use `peer.kind: dm`; newer schema commonly expects `direct`.
  - If route matching fails unexpectedly, verify against your installed OpenClaw schema/version.
- Prefer explicit allowlists and explicit bindings over broad open policies.
