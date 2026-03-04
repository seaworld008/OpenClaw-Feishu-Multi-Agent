# 交叉验证记录（2026-03-04）

## OpenClaw 官方
- docs/zh-CN/channels/feishu.md
  - 官方插件路径、配置字段（`channels.feishu.*`）
  - 多账号、群策略、`defaultAccount`、`requireMention` 相关字段
- docs/zh-CN/channels/channel-routing.md
  - 绑定匹配优先级（更具体规则优先）
- docs/zh-CN/concepts/multi-agent.md
  - 多 Agent 隔离模型、`agentId/accountId/bindings` 概念

## OpenClaw Release Notes
- v2026.3.2（2026-03-03）
  - Feishu 多 Bot mention 路由修复
  - Feishu 多 Agent 群广播派发增强
- v2026.3.1（2026-03-02）
  - Feishu 多账号稳定性增强、`defaultAccount` 相关能力
- v2026.2.26（2026-02-27）
  - 新增 agents 绑定 CLI，增强多账号配置迁移/修复

## 飞书官方文档（平台能力层）
- 事件订阅总览与配置
  - https://open.feishu.cn/document/server-docs/event-subscription-guide/introduction
  - https://open.feishu.cn/document/server-docs/event-subscription-guide/subscribe-to-events
- 消息事件与发送 API
  - https://open.feishu.cn/document/server-docs/im-v1/message/events/message_receive
  - https://open.feishu.cn/document/server-docs/im-v1/message/create
- 鉴权令牌
  - https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal

## 结论
- 交付默认应使用官方 `@openclaw/feishu` 插件模式（`channel=feishu`）。
- 旧 `chat-feishu` 只保留为 legacy 兼容路径。
- 免 @ 群触发必须联动敏感权限申请与多 Bot 风险控制。
