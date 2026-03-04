# Changelog

## [1.0.0] - 2026-03-04

### Added
- 新增交付级 Skill 文档，覆盖 single-bot / multi-bot、incremental / full_replace、canary 发布与回滚要求。
- 新增模板集合：部署输入、单/多 bot 路由、brownfield 变更计划、验收检查清单。
- 新增配置生成脚本 `build_openclaw_feishu_snippets.py`，支持 plugin/core patch 生成。
- 新增参考文档：前提条件、升级回归手册、Codex 提示词模板、交叉验证记录、融合说明。
- 新增 `agents/openai.yaml` 作为 agent 元信息。

### Changed
- 默认路线升级为官方 `@openclaw/feishu`（`channel=feishu`）。
- 保留 `chat-feishu` 作为历史兼容路径。
- README 升级为可版本化仓库说明，并补齐执行入口与维护约定。

### Notes
- `references/generated/` 为本地临时产物目录，默认忽略提交。
