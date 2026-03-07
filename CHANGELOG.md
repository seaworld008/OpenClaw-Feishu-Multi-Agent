# Changelog

## [1.1.3] - 2026-03-07

### Added
- 为 `V4.2` 增加基于远端 VMware 实测沉淀的两类运行前提：
  - 群级 prompt 变更后必须 fresh session（优先 `/reset`）
  - `supervisor_agent` 工作区必须完成生产化初始化，不能保留默认 `BOOTSTRAP.md`
- 新增自动化测试，覆盖：
  - `V4.2` 文档要求 fresh session
  - `V4.2` 文档要求生产化 workspace 初始化
  - `V4.2` 文档要求使用官方完整 `sessionKey` 格式
  - `check_v4_2_team_canary.sh` 在无 `rg` 环境下的回退执行

### Changed
- `V4.2` 主文档、README、SKILL、验收清单统一补充：
  - stale group session 的恢复步骤
  - workspace bootstrap 残留的排障规则
  - 飞书单群 `sessionKey` 必须使用 `agent:<agentId>:feishu:group:<peerId>`
- `check_v4_2_team_canary.sh` 改为在缺少 `rg` 时自动回退到 Python 检索，不再依赖目标机器预装 ripgrep。

### Fixed
- 修复 `V4.2` 在 fresh session 后仍可能被默认 workspace bootstrap 稀释掉团队调度行为的问题。
- 修复 `V4.2` 文档对固定 `sessionKey` 格式约束不够硬，导致主管错误使用 `feishu:chat:...` 并触发 `No session found` 的问题。
- 修复远端验收脚本在没有 `rg` 的客户环境下会假失败的问题。

## [1.1.2] - 2026-03-07

### Added
- 为 `V4.2` 增加基于远端实测的正式运行策略说明：`ACK timeoutSeconds=15 -> 详细任务 timeoutSeconds=0 -> sessions_history / worker session jsonl 二次收口`。
- 新增自动化测试，覆盖 `accepted + worker evidence` 的 fire-and-forget 成功路径。

### Changed
- `V4.2` 主文档、README、SKILL、验收清单统一升级为：
  - 全局 `messages.groupChat.mentionPatterns` + 主管级 `agents.list[].groupChat.mentionPatterns`
  - ACK / 正文双阶段派单
  - `sessions_history` 二次收口
- `V4`、`V4.1` 文档补充“历史/过渡版本”提示，明确单群生产优先使用 `V4.2`。
- 交叉验证记录补充 OpenClaw 官方 `timeoutSeconds=0 -> accepted` 语义与远端 VMware 运行结论。

### Fixed
- 修复 `V4.2` 文档仍停留在“只写 ACK 双阶段建议、未写 fire-and-forget / sessions_history 实施细节”的缺口。
- 修复 `V4.2` 文档未明确要求全局 `messages.groupChat.mentionPatterns` 兜底的问题。

## [1.1.1] - 2026-03-06

### Added
- 新增 `references/source-cross-validation-2026-03-06.md`，记录 `V4.2` 单群团队模式的最新交叉验证结论。
- `V4.2` canary 新增两类状态识别：
  - `TIMEOUT_BUT_WORKER_DELIVERED`
  - `TRIGGER_MISS_ON_MENTION_OR_FORMAT_WRAP`

### Changed
- `V4.2` 主管提示词与交付模板新增：
  - `mentionPatterns` 兜底
  - `PLAIN_TEXT` / 代码块包裹兼容
  - `timeout` 二次判定
  - ACK -> 正文 的双阶段派单建议
- README、SKILL、验收清单同步补齐 `V4.2` 的 timeout / NO_REPLY / mention 处理口径。

### Fixed
- 修复 `V4.2` canary 无法正确识别“被提及后落入 NO_REPLY”的问题。
- 修复 `V4.2` canary 未单独分类“timeout 但 worker 实际已执行”这一现场高频状态的问题。

## [1.1.0] - 2026-03-06

### Added
- 新增 `V4.2` 单群团队最佳实践方案，明确采用 `send-first probe`、展示层/控制面分离，并补齐完整交付提示词。
- 新增 `scripts/check_v4_2_team_canary.sh`，用于单群团队模式的真实派单链路校验，并支持 `SEND_PATH_AVAILABLE_BUT_LIST_MISS` 分类。
- 新增 `V4.2` 相关自动化测试，覆盖真实派单成功与 `list-miss / send-path` 分支。

### Changed
- README 升级为 `V1 / V2 / V3.1 / V4 / V4.1 / V4.2` 版本化说明，明确跨群与单群的推荐路线。
- 单群版本文档统一为 `send-first probe` 口径，修复 `sessions_list` 与 `sessions_spawn` 先后顺序的自相矛盾表述。
- `V4 / V4.1 / V4.2` 的验收与故障排查说明统一强调：
  - `session jsonl > gateway log`
  - 公开群里的 `@其他机器人` 仅作为展示层
  - `tool_call_required`、`warmup_required`、`SEND_PATH_AVAILABLE_BUT_LIST_MISS` 需分类处理
- 验收清单补齐 `V4 / V4.1 / V4.2` 的单群验证项，包括真实派单证据、互审约束、Feishu `sessions_spawn` 限制处理。

### Fixed
- 修复单群版本中“已经声明采用 send-first，但仍要求先 `sessions_spawn`”的错误引导。
- 修复 `V4.1` / `V4.2` 在首次上线和失败分流场景中的提示词不一致问题。
- 修复单群 canary 与文档之间的版本入口不一致问题。

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
