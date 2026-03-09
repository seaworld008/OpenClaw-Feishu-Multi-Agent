# Skill Mainline Pruning Design

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把仓库公开主线收敛为 `V5.1 Hardening`，移除旧跨群主线以及 `V4 / V4.3.1 / V4.3.1-C1.0` 这类旧入口在文档、模板、脚本入口和测试中的公开暴露，避免 skill 仓库继续同时维护多套冲突规范。

**Architecture:** 这次不动 `V5.1 Hardening` 的底层 shared core，只裁剪“版本入口层”。对外只保留 `V5.1 Hardening` 的 README、SKILL、交付模板、SOP、watchdog 模板和测试契约；`core_job_registry.py`、`core_session_hygiene.py`、`core_canary_engine.py` 这类被 `V5.1 Hardening` 仍直接依赖的内部模块继续保留，但会去掉旧主线语义。所有旧跨群主线与 `V4.3.1` 相关资料要么删除，要么把仍有价值的通用内容抽回到通用模板中。

**Tech Stack:** Markdown、JSON/JSONC、Python 3、`unittest`

---

## 现状问题

仓库当前已经形成两个事实：

1. `V5.1` 已经是最新主线，并且 roleCatalog、deterministic orchestrator、runtime manifest 都围绕 `V5.1 Hardening` 收敛。
2. `V4.3.1` 仍在 README、SKILL、模板、watchdog、SOP、测试里被当成并列主线维护。

这会导致两个持续成本：

- 用户不知道应该从旧跨群主线、`V4.3.1` 还是 `V5.1` 起步。
- 每次 `V5.1` 演进时，还要同步想办法保持 `V4.3.1` 文档、模板和断言不漂移。

既然仓库目标已经明确成“只保留 `V5.1` 最新稳定版”，就应该把旧跨群主线与 `V4.3.1` 一起从主线入口彻底拿掉。

## 方案比较

### 方案 A：只改 README / SKILL 入口，不删旧文件

优点：
- 风险最低
- 修改最小

缺点：
- 仓库里仍然堆着旧模板、旧脚本和旧测试
- 后续继续有人误用 `V4.3.1`

结论：不够彻底。

### 方案 B：删除 `V4.3.1` 的公开资产，保留 `V5.1` 仍依赖的内部 core

优点：
- 对外主线清晰
- 仓库维护面明显缩小
- 不会误删 `V5.1` 的真实依赖

缺点：
- 需要同步改测试、模板和引用

结论：推荐方案。

### 方案 C：把旧主线全量归档到 `legacy/`

优点：
- 信息还在
- 历史可追溯

缺点：
- skill 仓库仍然在维护一套“半公开遗留区”
- 与用户“只要 V5.1 最新稳定版”不一致

结论：当前不做。

## 收口范围

### 保留

- `V5.1 Hardening` 相关入口、模板、SOP、watchdog、reconcile
- `core_feishu_config_builder.py`
- `core_job_registry.py`
- `core_session_hygiene.py`
- `core_canary_engine.py`
- 通用输入模板、验证清单、deployment inputs、Brownfield 模板

### 删除

- `references/codex-prompt-templates-v4.3.1-single-group-production*.md`
- `references/v4-3-1-quick-start.md`
- `references/source-cross-validation-2026-03-07-v4-3-1.md`
- `references/source-cross-validation-2026-03-07-platforms.md`
- `references/windows-wsl2-deployment-notes.md`
- `templates/openclaw-v4-3-1-single-group-production.example.jsonc`
- `templates/systemd/v4-3-watchdog.*`
- `templates/launchd/v4-3-watchdog.plist`
- `templates/v4-3-job-registry.example.sql`
- `scripts/v431_single_group_runtime.py`
- `scripts/v431_single_group_hygiene.py`
- `scripts/v431_single_group_canary.py`
- `docs/plans/2026-03-07-v4-3-1-*.md`

## 文档保值策略

不是所有 `V4.3.1` 内容都没价值。需要保留的通用信息应该被吸回：

- README / SKILL 中的平台矩阵继续保留 `Linux / macOS / WSL2`
- `templates/windows/wsl.conf.example` 继续保留，作为 WSL2 通用模板
- `templates/deployment-inputs.example.yaml` 和 `templates/verification-checklist.md` 改成只描述 `V5.1`
- `references/rollout-and-upgrade-playbook.md` 改成通用 Brownfield / V5.1 路线

## 测试策略

测试契约要同步改成新的真相：

1. 新脚本入口只检查 `V5.1`
2. README / SKILL 必须显式包含 `V5.1 Hardening`
3. README / SKILL 不再允许宣称 `V4.3.1` / `C1.0` 是当前主线
4. `V3 / V4` 资产必须不存在
5. registry / hygiene / canary 的共享能力测试改为走 `core_*` 或 `V5.1` 公共入口

## 风险与兼容

### 风险 1：测试仍隐式依赖 V4 文件

处理：
- 先改测试常量和断言，再删文件。

### 风险 2：V5.1 仍复用旧 V4 wrapper 名称

处理：
- 共享能力测试直接切到 `core_job_registry.py` / `core_session_hygiene.py` 或 `v51_*` 入口。

### 风险 3：平台说明被误删

处理：
- 保留 README / SKILL 中的平台矩阵，保留 `templates/windows/wsl.conf.example`。

## 验收标准

- README、SKILL、模板和测试里只把 `V5.1 Hardening` 当主线版本
- `V4.3.1/C1.0` 公开资产已从仓库删除
- `V5.1` 相关测试仍全部通过
- `git diff --check` 通过
