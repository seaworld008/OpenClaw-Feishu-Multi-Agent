# V5 Team Orchestrator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为仓库新增 `V5 Team Orchestrator` 生产级实现：支持用 `teams` 模型声明多个飞书群、每群一个 supervisor 和 N 个 worker，生成对应的 OpenClaw Feishu patch、team runtime manifest、完整文档、真实双群示例和可直接给 Codex 使用的长版提示词模板。

**Architecture:** 在现有 `build_openclaw_feishu_snippets.py` 基础上增加 `teams` 解析分支，保持对旧 `routes` 输入兼容。除 OpenClaw patch 外，还要输出 team runtime manifest，把 `workflow / visibility / responsibility / hidden main / db / watchdog` 全部显式化，供 Codex 和运维脚本使用。文档层新增 `V5` 交付手册与 JSONC 快照，README / SKILL / 测试同步升级，再进入远端现网迁移。

**Tech Stack:** Python 3、`unittest`、JSON/JSONC 模板、Markdown 文档

---

### Task 1: 固化 V5 设计与完整交付范围

**Files:**
- Modify: `docs/plans/2026-03-08-v5-team-orchestrator-design.md`
- Modify: `docs/plans/2026-03-08-v5-team-orchestrator-implementation.md`
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 写文档范围的 failing tests**

在 `tests/test_openclaw_feishu_multi_agent_skill.py` 新增断言：
- `V5` 设计文档存在
- `README` 提到 `V5 Team Orchestrator`
- `SKILL.md` 提到 `teams` 模型与 `1 supervisor + N workers`
- `V5` 文档明确包含当前两群 `oc_f785...`、`oc_7121...`
- `V5` 文档明确包含三个机器人账号与长版 Codex 提示词

**Step 2: 跑测试，确认 RED**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5DocumentationTests -v
```

Expected: 因 `V5` 文档还只是骨架、未包含完整双群生产信息而失败。

**Step 3: 写最小实现**

补齐设计与 README / SKILL 入口说明，明确双群生产基线、模板扩展方式与完整交付目标。

**Step 4: 再跑测试，确认 GREEN**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5DocumentationTests -v
```

### Task 2: 为构建脚本增加 `teams` 生产模型与 team manifest 输出

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/build_openclaw_feishu_snippets.py`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/references/input-template-v5-team-orchestrator.json`
- Create: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v5-team-orchestrator.example.jsonc`

**Step 1: 写 failing tests**

新增测试覆盖：
- `teams` 输入会生成 team-scoped `agents.list`
- `bindings` 只生成精确群绑定
- hidden main 会按 `agent:<supervisorAgentId>:main` 参数化出现在 team manifest 中
- 同账号多群时会生成多个 `channels.feishu.accounts[accountId].groups[peerId]`
- `channels.feishu.groups.<peerId>.requireMention` 会随 team group 配置生成
- `messages.groupChat.mentionPatterns` 与 `agents.defaults.sandbox.sessionToolsVisibility` 会进入 patch
- `teamKey` 非法时明确失败
- worker 默认 workspace / agentDir 路径和快照保持一致

**Step 2: 跑测试，确认 RED**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV5Tests -v
```

Expected: 失败，提示当前脚本虽然接受 `teams`，但没有落地 runtime 元数据与生产字段。

**Step 3: 写最小实现**

在脚本中新增：
- `validate_teams`
- `build_team_runtime_manifest`
- `build_team_groups_config`
- `build_team_messages_patch`
- `build_v5_plugin_patch`

并保持旧 `routes` 输入不破坏。

**Step 4: 跑测试，确认 GREEN**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV5Tests -v
```

### Task 3: 补 V5 双群真实模板、快照与长版提示词

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v5-team-orchestrator.md`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`

**Step 1: 写 failing tests**

新增断言：
- JSONC 快照包含当前两个正式团队群与三机器人真实映射
- 文档中明确 `One Team = 1 Supervisor + N Workers`
- 文档中包含可直接给 Codex 用的完整提示词
- README 链接到了 `V5` 模板、示例输入和 runtime manifest

**Step 2: 跑测试，确认 RED**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5TemplateTests -v
```

Expected: 因当前文件仍是骨架、没有真实双群配置与长版提示词而失败。

**Step 3: 写最小实现**

提供一个含 2 个正式团队、3 个机器人真实账号映射、完整长版提示词和扩展说明的生产示例。

**Step 4: 跑测试，确认 GREEN**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5TemplateTests -v
```

### Task 4: 升级 canary / hygiene / summary 到 team 生产视角

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/check_v4_3_canary.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v4_3_session_hygiene.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 写 failing tests**

新增断言：
- canary 能校验 supervisor 最终收口目标群
- canary 能在 `V5` 场景拦截 cross-team jobRef 污染
- session hygiene 输出 teamKey 与 team-scoped session keys
- summary 输出 team 数量、binding 数量和 runtime manifest 路径

**Step 2: 跑测试，确认 RED**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5ReadmeAndSkillTests -v
```

**Step 3: 写最小实现**

按 team 视角补 canary / hygiene / summary，不动远端现网逻辑。

**Step 4: 跑测试，确认 GREEN**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5ReadmeAndSkillTests -v
```

### Task 5: 更新版本文档并跑完整验证

**Files:**
- Modify: `README.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `CHANGELOG.md`
- Modify: `VERSION`
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: 跑 V5 新增测试集合**

Run:
```bash
python3 -m unittest \
  tests.test_openclaw_feishu_multi_agent_skill.V5DocumentationTests \
  tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetV5Tests \
  tests.test_openclaw_feishu_multi_agent_skill.V5RuntimeArtifactsTests \
  tests.test_openclaw_feishu_multi_agent_skill.V5TemplateTests \
  tests.test_openclaw_feishu_multi_agent_skill.V5ReadmeAndSkillTests -v
```

Expected: 全绿。

**Step 2: 跑仓库完整测试**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
```

Expected: 除当前已知 3 个 `V43RegistryTests` 基线失败外，不新增失败。

**Step 3: 跑静态校验**

Run:
```bash
git diff --check
```

Expected: 无空格与 patch 格式问题。
