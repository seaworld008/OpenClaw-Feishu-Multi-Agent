# 融合与查漏补缺说明

## 输入来源
- 外部仓库：`OpenClaw-Feishu-Multi-Agent`（当前目录已手动拉取）
- 本地已有：`feishu-openclaw-multi-agent` Skill
- 官方最新：OpenClaw 文档 + OpenClaw Release + 飞书开放平台文档

## 外部仓库可复用内容
在当前拉取结果中，外部仓库包含：
- `README.md`
- `skills/openclaw-feishu-multi-agent-deploy/SKILL.md`
- 一组 `templates/*` 交付模板

核心贡献点是：
- 交付导向（可回滚、可验收、可复用）
- single-bot / multi-bot 双模式
- incremental / full_replace 变更策略
- Brownfield 交付模板思路

## 已融合到本 Skill 的内容
- 新增模板目录 `templates/`：
  - deployment-inputs.example.yaml
  - openclaw-single-bot-route.example.jsonc
  - openclaw-multi-bot-route.example.jsonc
  - brownfield-change-plan.example.md
  - verification-checklist.md
- 新增自动化脚本：
  - scripts/build_openclaw_feishu_snippets.py
- 新增交付/升级文档：
  - references/prerequisites-checklist.md
  - references/rollout-and-upgrade-playbook.md
  - references/codex-prompt-templates.md
  - references/source-cross-validation-2026-03-04.md
- 升级 SKILL.md 为交付 SOP 版

## 查漏补缺结果
- 将默认实现从历史 `chat-feishu` 升级为官方插件 `@openclaw/feishu`
- 补齐 `defaultAccount`、`bindings` 顺序、免@敏感权限联动
- 增加升级后回归与回滚标准流程

## 仍需注意
- 不同客户 OpenClaw 版本可能有字段差异，落地前必须执行：
  - `openclaw config validate`
  - canary 群回归
