# 前提条件清单（交付前必须满足）

## 1. OpenClaw 侧
- 已安装 OpenClaw，建议版本 `v2026.3.1+`
- 已安装官方 Feishu 插件：`@openclaw/feishu`
- 已明确目标平台：`Linux` / `macOS` / `WSL2`
- 若客户是 Windows，默认采用 `WSL2`，不把 Windows 原生 service 作为默认生产路线
- 可访问并修改配置文件：`~/.openclaw/openclaw.json`
- 可执行命令：
  - `openclaw config validate`
  - `openclaw gateway restart`
  - `openclaw logs --follow`
  - `openclaw agents list --bindings`
- 若使用 V3“主管派单 -> 三群执行”：
  - `tools.allow` 需包含 `group:sessions`（建议同时包含 `group:messaging`）
  - `tools.sessions.visibility` 需可见目标会话（建议 `all`）
  - `session.sendPolicy` 需放行跨会话发送（建议 `default=allow`）

## 2. 飞书开放平台侧
- 已创建企业自建应用
- 已获取每个机器人的：
  - `appId`
  - `appSecret`
  - `encryptKey`
  - `verificationToken`
- 事件订阅已配置：
  - `im.message.receive_v1`（必需）
- 如使用卡片交互回调，追加：
  - `card.action.trigger`
- 应用已发布且在目标租户可用
- 已开启“机器人可在群聊被 @”能力

## 3. 权限（Scopes）
最小必需：
- `im:message`
- `im:message.p2p_msg:readonly`
- `im:message.group_at_msg:readonly`
- `im:message:send_as_bot`
- `im:resource`

免 @ 群触发额外需要：
- `im:message.group_msg`（敏感权限）

外部群额外检查：
- 不靠新增 `scope` 解决，先确认应用已开启“对外共享/允许外部用户使用”并审批生效
- 先验证机器人能被加入外部群，再验证 `@机器人` 消息能进入 gateway
- 不要把飞书客户端里的“已查看/已读”展示当成唯一验收标准

## 4. 路由素材
- 每个目标 Agent 的 `agentId`
- 每个群 `chat_id`（`oc_xxx`）或私聊对象 ID
- 路由表（哪个 accountId + 哪个群/私聊 → 哪个 agent）

## 5. 变更管理
- 已确认变更窗口
- 已准备备份和回滚路径
- 已指定 canary 验证群
