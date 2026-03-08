# Script Namespace Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 一次性完成脚本命名体系重构，把仓库从历史遗留脚本名迁移到 `core_* / v31_* / v431_* / v51_*` 新规范，并同步更新所有文档、模板、测试和远端部署路径。

**Architecture:** 采用“公共基础层 + 版本公开入口”方案。`core_*` 保存稳定公共能力，`v31_* / v431_* / v51_*` 保存对外契约与版本语义；所有现有对旧脚本名的依赖统一切换到新入口，不保留兼容别名。迁移过程必须先测试后删旧名，确保仓库和远端运行时在任何时点都能被验证。

**Tech Stack:** Python 3、Markdown、`unittest`、`rg`

---

### Task 1: 先加“禁止旧名”回归测试

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write the failing test**

新增测试覆盖：
- 脚本目录必须存在新文件名
- 活跃文档、模板、README、SKILL、测试常量不能再引用旧名
- `V3.1 / V4.3.1 / V5.1` 应改用新入口名

**Step 2: Run test to verify it fails**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill -v
```

Expected: 失败，提示旧名仍存在且新入口未全部切换。

### Task 2: 建立 `core_*` 公共基础脚本

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_job_registry.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_session_hygiene.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_canary_engine.py`
- Retire: 历史 builder/runtime/hygiene 旧路径，不保留 shim

**Step 1: Write minimal implementation**

做法：
- 把现有 builder / registry / hygiene 核心逻辑迁入 `core_*`
- `core_canary_engine.py` 抽取日志/会话解析公共逻辑
- 旧文件彻底删除，不保留 shim

**Step 2: Run focused tests**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.BuildSnippetTests tests.test_openclaw_feishu_multi_agent_skill.V43RegistryTests -v
```

Expected: 全绿。

### Task 3: 建立版本公开入口脚本

**Files:**
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v31_cross_group_canary.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_runtime.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_hygiene.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v431_single_group_canary.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_runtime.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_hygiene.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_canary.py`
- Create: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py`
- Retire: 历史 canary 旧入口与 shell-only dispatch checker

**Step 1: Write the failing test**

确保：
- `V3.1` canary 改为 Python
- `V4.3.1` / `V5.1` 各有独立 runtime / hygiene / canary 入口
- 新入口的 CLI 参数与现有文档主命令保持兼容

**Step 2: Run test to verify it fails**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill -v
```

Expected: 失败，提示脚本常量与文档尚未切换。

**Step 3: Write minimal implementation**

实现要求：
- 版本入口只封装版本契约，不复制核心逻辑
- `v431_single_group_runtime.py` 与 `v51_team_orchestrator_runtime.py` 调用 `core_job_registry.py`
- `v31_cross_group_canary.py` 改用 Python 并尽量保持现有输出 token

**Step 4: Run focused tests**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5RuntimeArtifactsTests -v
```

Expected: 全绿。

### Task 4: 切换测试常量与脚本路径断言

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Write minimal implementation**

更新：
- `BUILD_SCRIPT`
- `CANARY_SCRIPT`
- `V4_3_CANARY_SCRIPT`
- `V4_3_REGISTRY`
- `V4_3_HYGIENE_SCRIPT`

并把所有字符串断言切到新命名。

**Step 2: Run focused tests**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill -v
```

Expected: 关键测试通过。

### Task 5: 全量更新 README / SKILL / 模板 / 参考文档

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/deployment-inputs.example.yaml`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/verification-checklist.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v4-3-1-single-group-production.example.jsonc`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/openclaw-v5-team-orchestrator.example.jsonc`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/systemd/v4-3-watchdog.service`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/templates/launchd/v4-3-watchdog.plist`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v3.1.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v4.3.1-single-group-production-C1.0.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/codex-prompt-templates-v5-team-orchestrator.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/rollout-and-upgrade-playbook.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/v4-3-1-quick-start.md`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/references/windows-wsl2-deployment-notes.md`
- Modify: `docs/plans/*.md` 中所有仍引用旧脚本名的文件

**Step 1: Write minimal implementation**

更新所有旧脚本路径为新命名。

重点替换：
- 公共生成器统一使用 `core_feishu_config_builder.py`
- 运行时状态机统一落在 `core_job_registry.py`，对外只暴露对应版本 runtime
- `V4.3.1` 统一使用 `v431_single_group_runtime.py / v431_single_group_hygiene.py / v431_single_group_canary.py`
- `V3.1` 统一使用 `v31_cross_group_canary.py`
- `V5.1` 统一使用 `v51_team_orchestrator_runtime.py / v51_team_orchestrator_hygiene.py / v51_team_orchestrator_canary.py / v51_team_orchestrator_deploy.py`

**Step 2: Run grep verification**

Run:
```bash
rg -n "v4_3_job_registry\\.py|v4_3_session_hygiene\\.py|check_v4_3_canary\\.py|check_v3_dispatch_canary\\.sh|build_openclaw_feishu_snippets\\.py" \
  README.md skills tests docs CHANGELOG.md
```

Expected: 只允许 `CHANGELOG.md` 中保留必要历史说明；其余全部为空。

### Task 6: 更新远端部署与 runtime manifest 路径契约

**Files:**
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py`
- Modify: `skills/openclaw-feishu-multi-agent-deploy/scripts/core_feishu_config_builder.py`
- Modify: 任何生成 `runtime manifest` 的脚本和模板

**Step 1: Write minimal implementation**

要求：
- `runtime manifest` 输出新脚本名
- 远端部署脚本只写入新路径
- 不再生成任何旧名引用

**Step 2: Run focused tests**

Run:
```bash
python3 -m unittest tests.test_openclaw_feishu_multi_agent_skill.V5RuntimeArtifactsTests -v
```

Expected: 全绿。

### Task 7: 跑完整验证

**Files:**
- Modify: `tests/test_openclaw_feishu_multi_agent_skill.py`

**Step 1: Run full test suite**

Run:
```bash
python3 -m unittest tests/test_openclaw_feishu_multi_agent_skill.py
```

Expected: 全绿。

**Step 2: Run formatting / patch hygiene**

Run:
```bash
git diff --check
```

Expected: 通过。

**Step 3: Final grep**

Run:
```bash
rg -n "v4_3_job_registry\\.py|v4_3_session_hygiene\\.py|check_v4_3_canary\\.py|check_v3_dispatch_canary\\.sh|build_openclaw_feishu_snippets\\.py" \
  README.md skills tests docs
```

Expected: 无结果。
