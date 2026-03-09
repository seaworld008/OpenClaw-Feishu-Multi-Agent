# OpenClaw 飞书多 Agent 最佳实践（截至 2026-03-04）

> 当前多群生产主线已经收口到 `V5.1 Hardening`。
> 若目标是正式交付、角色模板化扩容或真实双群生产，请优先使用
> `references/input-template-v51-fixed-role-multi-group.json`，
> 不要从通用 plugin 模板直接起步。

## 1. 一手来源（官方优先）
- OpenClaw 官方文档：
  - `docs/zh-CN/channels/feishu.md`
  - `docs/zh-CN/channels/channel-routing.md`
  - `docs/zh-CN/concepts/multi-agent.md`
- OpenClaw 官方 Release：
  - `v2026.3.2`（2026-03-03）
  - `v2026.3.1`（2026-03-02）
  - `v2026.2.26`（2026-02-27）
- OpenClaw 仓库当前推送时间：2026-03-04（main 分支）

> 兼容参考：社区插件 `m1heng/clawdbot-feishu`（历史多账号能力来源），但新项目建议优先采用官方 `@openclaw/feishu`。

## 2. 结论：你的方案仍然成立，但要切到官方插件默认

### 2.1 核心思路仍正确
- 用 `bindings` 做 `(channel, accountId, peer)` 精确分流
- 一个网关承载多个 Agent/多个账号
- 通过群/私聊 `peer.id` 做业务隔离，降低上下文污染和 Token 浪费

### 2.2 需要升级的默认实现
- 默认通道写法应为 `channel: "feishu"`（官方插件）
- 当前默认只维护官方 `@openclaw/feishu` 插件配置。
- 推荐插件安装方式：`openclaw plugins install @openclaw/feishu`

## 3. 最近更新对方案的影响

### 3.1 `v2026.3.2`（2026-03-03）与 Feishu 相关
- 修复多 Bot 群提及判定，减少 `requireMention` 下误触发。
- 增强 Feishu 多 Agent 群广播派发（含跨账号去重与隔离策略）。
- 改善重启后去重状态恢复，降低重复回复概率。

### 3.2 `v2026.3.1`（2026-03-02）与 Feishu 相关
- 强化多账号+回复可靠性，支持 `channels.feishu.defaultAccount` 出站默认账号。
- 增加群会话范围/线程回复等能力（群场景可更细分隔离）。
- 增强多种富媒体与文档工具能力，但不改变核心路由方法。

### 3.3 `v2026.2.26`（2026-02-27）与路由相关
- 新增 `openclaw agents bind/unbind/bindings` CLI，方便绑定维护。
- 多账号配置迁移和修复逻辑增强（`doctor --fix` 可修复部分混合形态）。

## 4. 当前推荐配置策略（生产）

### 4.1 路由优先级
按“最具体优先”组织 `bindings`：
1. `peer` 精确规则（群/私聊）
2. `accountId` 规则
3. 渠道兜底规则（如 `accountId="*"`）

### 4.2 提及策略
- 默认：`requireMention=true`
- 要免 @ 时：
  - 明确设置 `requireMention=false`（建议按群精细配置）
  - 申请 `im:message.group_msg`（敏感权限）
  - 多 Bot 群默认保留 `allowMentionlessInMultiBotGroup=false`

### 4.3 连接模式
- 默认优先 `websocket`（无需公网回调 URL）
- `webhook` 仅在已有公网反向代理场景启用

### 4.4 多账号稳定性
- 显式设置 `channels.feishu.defaultAccount`
- 在 `bindings` 显式写 `match.accountId`
- 不同业务群绑定不同 `agentId`，避免宽泛规则抢先命中

## 5. 最小权限与事件清单

### 5.1 最小权限
- `im:message`
- `im:message.p2p_msg:readonly`
- `im:message.group_at_msg:readonly`
- `im:message:send_as_bot`
- `im:resource`

### 5.2 免 @ 追加权限
- `im:message.group_msg`

### 5.3 事件订阅
- 必需：`im.message.receive_v1`
- 常见辅助：`im.chat.member.bot.added_v1`、`im.chat.member.bot.deleted_v1`

## 6. 已知限制与规避
- 多 Bot 同群里 Bot-to-Bot `@` 不是可靠通信手段（平台限制）；需要 Agent 协作时优先走 OpenClaw 内部会话转发。
- 配置升级后先执行：
  - `openclaw config validate`
  - `openclaw agents list --bindings`
  - 每条绑定做实测（DM + 群）

## 7. 模板建议
- 当前最新稳定版 `V5.1 Hardening`：
  - `references/input-template-v51-fixed-role-multi-group.json`（正式推荐，适合客户交付）
  - `references/input-template-v51-team-orchestrator.json`（真实双群生产基线）
- 老项目若仍使用旧字段结构，先统一迁移到 `channels.feishu.*` 再继续交付。
