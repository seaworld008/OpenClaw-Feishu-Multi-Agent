# V4.3.1 Cross-Platform Compatibility Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the V4.3.1 single-group production skill so it can be delivered consistently on Linux, macOS, and Windows (via WSL2) without changing the core workflow.

**Architecture:** Keep one V4.3.1 runtime model and add platform-specific deployment wrappers. Linux and WSL2 share the same runtime assumptions and watchdog flow; macOS gets a launchd wrapper; Windows native is documented as non-recommended and routed to WSL2.

**Tech Stack:** OpenClaw, Feishu plugin, Python 3 with sqlite3, systemd user services, launchd, Markdown docs, YAML templates.

---

### Task 1: Audit platform assumptions

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md`

**Step 1: Identify Linux-only assumptions**
Run: `rg -n "systemd|launchd|WSL|Windows|macOS|Linux|openclaw gateway restart|launchctl|userctl|\.service" README.md skills/openclaw-feishu-multi-agent-deploy`
Expected: list of Linux-specific references to replace or branch.

**Step 2: Document target compatibility policy**
Add a platform matrix and clear recommendations:
- Linux: recommended, systemd user service
- macOS: recommended, launchd
- Windows native: not recommended / not validated
- Windows + WSL2: recommended, same runtime model as Linux

### Task 2: Add platform delivery templates

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist`
- Create: `skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md`
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`

**Step 1: Add launchd template**
Create a user LaunchAgent plist equivalent to the existing watchdog timer.

**Step 2: Add Windows/WSL2 deployment notes**
Document WSL2 prerequisites, where OpenClaw should run, path expectations, and what is not recommended.

**Step 3: Wire docs to templates**
Expose both templates and notes from README and SKILL.

### Task 3: Update V4.3.1 production docs

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md`

**Step 1: Add platform-specific deployment section**
Document service manager differences without changing the core production workflow.

**Step 2: Add initialization/verification differences**
Keep the same `WARMUP`, canary, and SQLite checks, but branch service commands by platform.

### Task 4: Add regression coverage and validate

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`
- Modify: `CHANGELOG.md`
- Modify: `VERSION`

**Step 1: Add tests for new cross-platform artifacts**
Assert README, SKILL, V4.3.1 docs, launchd template, and WSL2 notes all exist and reference the intended platform policy.

**Step 2: Run verification**
Run:
- `python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py`
- `python3 -m py_compile skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_canary.py`
- `git diff --check`
Expected: all pass.
