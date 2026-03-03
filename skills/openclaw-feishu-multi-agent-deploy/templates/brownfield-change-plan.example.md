# Brownfield Change Plan (Existing OpenClaw Deployment)

## Environment

- Customer:
- Environment: `prod` / `staging`
- Config file:
- Backup file:
- Deployment window:

## Scope

- Goal:
- Out of scope:

## Planned Changes

### to_add

- New Feishu account IDs:
- New group IDs:
- New bindings:
- New agent IDs:

### to_update

- Existing Feishu account settings:
- Existing bindings:
- `agentToAgent.allow`:

### to_keep_unchanged

- Existing non-Feishu channels:
- Existing model/auth settings:
- Existing logging/observability:

## Risk Check

- Any binding conflicts (same channel/account/group to multiple agents)?
- Any stale bindings (agent removed but route remains)?
- Any mention-free groups missing `group_msg` scope?

## Canary Plan

- Canary group ID:
- Expected agent:
- Test messages:
- Pass criteria:

## Rollback

- Rollback command:
- Backup path:
- Verification after rollback:
