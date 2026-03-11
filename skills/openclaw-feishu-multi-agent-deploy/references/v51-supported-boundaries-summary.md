# V5.1 Supported Boundaries Summary

这是一页交付摘要，只回答 3 个问题：

1. 当前主线正式支持什么  
2. 哪些能力不要再按旧心智去配  
3. 新机器部署时，最小可信做法是什么

适用范围：
- `V5.1 Hardening`
- `accounts + roleCatalog + teams`
- `parallel stage + publishOrder`

## 1. 当前正式主线

正式主路径只有这一条：

```text
ingress -> controller -> outbox -> sender -> callback sink
```

这意味着：
- supervisor 群会话是 `ingress-only`
- worker 只负责产出内容，不直接决定群里何时发消息
- 群里可见消息只允许由 `controller -> outbox -> sender` 发出

## 2. worker 正式协议

worker 只提交：
- `progressDraft`
- `finalDraft`
- `summary`
- `details`
- `risks`
- `actionItems`

完整 callback 成功后，只输出：

```text
CALLBACK_OK
```

不要再使用旧协议：
- `message(progress)`
- `message(final)`
- `NO_REPLY` 作为正常完成标志

## 3. 统一入口正式结构

统一入口固定按这三层维护：

```text
accounts
roleCatalog
teams
```

builder 自动派生：
- `channels.feishu`
- `bindings`
- `agents.list`
- `v51 runtime manifest`

不要手工维护：
- `routes`
- `bindings`
- `channels.feishu.accounts.<group>.systemPrompt`

## 4. 当前正式支持的可定制范围

### accounts

放：
- `accountId`
- `appId`
- `appSecret`
- `encryptKey`
- `verificationToken`

### roleCatalog

放角色默认定义：
- `name`
- `role`
- `visibleLabel`
- `description`
- `responsibility`
- `identity`
- `mentionPatterns`
- `visibility`
- `systemPrompt`
- `runtime`

### teams

放群和编排：
- `teamKey`
- `group.peerId`
- `group.entryAccountId`
- `group.requireMention`
- `supervisor`
- `workers`
- `workflow.stages`

### workflow

正式支持：
- `serial`
- `parallel`
- `stageKey`
- `agents`
- `publishOrder`

规则：
- `parallel` stage 必须写 `stageKey + agents + publishOrder`
- `publishOrder` 必须完整覆盖该 stage 的全部 worker，且顺序唯一

## 5. per-agent runtime override 的真实边界

当前统一入口已经支持 per-agent runtime override，但要按 OpenClaw 真实边界来理解。

### 正式支持

可写到：
- `roleCatalog.*.runtime`
- `teams[].supervisor.overrides.runtime`
- `teams[].workers[].overrides.runtime`

当前正式支持的字段只有：
- `model`
- `sandbox`

### 不要再配

不要下沉到单个 agent：
- `maxConcurrent`
- `subagents`

这些字段继续放在：
- `agents.defaults`

原因：
- OpenClaw 当前会把它们当作 `agents.list` 非法字段

## 6. 新机器部署最小可信做法

推荐步骤：
1. 先填 `accounts`
2. 再填 `roleCatalog`
3. 再填 `teams[].group`
4. 再填 `teams[].supervisor / workers`
5. 再填 `workflow.stages`
6. 最后才填 `runtime`

推荐输入模板：
- `references/input-template-v51-fixed-role-multi-group.json`
- `references/input-template-v51-team-orchestrator.json`

推荐 deploy：

```bash
python3 skills/openclaw-feishu-multi-agent-deploy/scripts/v51_team_orchestrator_deploy.py \
  --input skills/openclaw-feishu-multi-agent-deploy/references/input-template-v51-fixed-role-multi-group.json \
  --out skills/openclaw-feishu-multi-agent-deploy/references/generated \
  --openclaw-home ~/.openclaw \
  --systemd-user-dir ~/.config/systemd/user
```

这条命令会同时：
- 生成 patch / summary / runtime manifest
- merge active `~/.openclaw/openclaw.json`
- 写 active `~/.openclaw/v51-runtime-manifest.json`
- materialize runtime tools / workspace / systemd units

## 7. 当前不该再做的事

不要再：
- 让 supervisor 直接建单/接单/派单/收口
- 让 worker 直接 `message(progress/final)`
- 让 hidden main 承担正式 callback 协议
- 手工改 `bindings`
- 把旧 `routes` 当统一入口

## 8. 一句话原则

**全局默认放 `agents.defaults`，角色默认放 `roleCatalog`，单群特化放 `teams[].overrides`，流程编排只放 `workflow.stages`，群里可见消息永远只由控制面发送。**
