# 交叉验证记录（2026-03-05）

## OpenClaw 官方来源
- 主仓库：
  - https://github.com/openclaw/openclaw
- Feishu 渠道文档（官方插件、权限、群组 ID 获取、defaultAccount、requireMention）：
  - https://docs.openclaw.ai/zh-CN/channels/feishu
- 路由规则文档（匹配优先级、bindings）：
  - https://docs.openclaw.ai/channels/channel-routing
- 多 Agent 概念文档（agentId、bindings、隔离模型）：
  - https://docs.openclaw.ai/zh-CN/concepts/multi-agent
- Releases：
  - https://github.com/openclaw/openclaw/releases

## 飞书官方来源
- 事件订阅总览：
  - https://open.feishu.cn/document/server-docs/event-subscription-guide/introduction
- 订阅事件配置：
  - https://open.feishu.cn/document/server-docs/event-subscription-guide/subscribe-to-events
- 接收消息事件：
  - https://open.feishu.cn/document/server-docs/im-v1/message/events/message_receive
- 多维表格概述（Base/Bitable）：
  - https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview
- 鉴权（tenant_access_token）：
  - https://open.feishu.cn/document/server-docs/authentication-management/access-token/tenant_access_token_internal

## 本次结论
1. `@openclaw/feishu` 仍是推荐默认路线，`match.channel = "feishu"`。
2. 群 ID 采集优先使用 `openclaw logs --follow` 读取入站会话字段（`chat_id/peer.id`）。
3. 当前 `V5.1 Hardening` 主线统一入口是 `accounts + roleCatalog + teams`；生产输入不再手写 `routes`，最终由 builder 派生 `bindings`。
4. 多 Agent 绑定应保持“精确优先 + 第一个命中生效”的 bindings 顺序；多账号必须显式维护 `defaultAccount`，并在统一入口 `accounts[]` 中定义 `accountId`。
5. 免 @ 触发要与飞书权限 `im:message.group_msg` 联动，默认建议保持 `requireMention=true`。
6. 多维表格权限在飞书控制台可能以 `bitable:*` 或 `base:*` 命名展示，最终应以目标 API 页面“权限要求”为准。
7. 截至 2026-03-05，OpenClaw 主仓库有更新提交，最新 release 仍为 v2026.3.2（2026-03-03）。
