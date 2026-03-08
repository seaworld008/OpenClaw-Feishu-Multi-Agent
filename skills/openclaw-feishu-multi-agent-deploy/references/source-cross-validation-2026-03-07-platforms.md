# V4.3.1 跨平台交叉验证（2026-03-07）

## 结论

`V4.3.1` 的运行模型可以跨平台复用，但服务管理和正式推荐路径需要明确分层：

- Linux：正式推荐，`systemd` 用户服务
- macOS：正式推荐，`launchd` / `LaunchAgent`
- Windows 原生：不作为默认生产推荐
- Windows + WSL2：正式推荐，复用 Linux 路线

## 核心来源

### OpenClaw 官方安装页
- 文档：<https://docs.openclaw.ai/install/index>
- 关键信息：Windows 强烈建议在 `WSL2` 中运行 OpenClaw。

### OpenClaw 官方平台页
- 文档：<https://docs.openclaw.ai/zh-CN/platforms>
- 关键信息：
  - macOS 使用 `LaunchAgent`
  - Linux/WSL2 使用 `systemd`

### Microsoft WSL 官方文档
- 文档：<https://learn.microsoft.com/en-us/windows/wsl/wsl-config>
- 关键信息：WSL2 可通过 `/etc/wsl.conf` 开启 `systemd`。

## 对 skill 的直接影响

1. `V4.3.1` 的核心协议、SQLite 状态层、`v431_single_group_canary.py`、`WARMUP`、群内 6 类可见消息规则，不需要按平台分叉。
2. 平台差异主要集中在：
   - service manager
   - watchdog 挂载方式
   - 运维 SOP
3. 因此最稳的交付方式不是做三套不同架构，而是：
   - 一套运行模型
   - Linux/WSL2 一套 systemd 模板
   - macOS 一套 launchd 模板
   - Windows 原生只保留说明，不默认承诺正式生产支持

## 最终推荐

- 跨平台交付时，统一对外声明：
  - Linux：推荐
  - macOS：推荐
  - Windows：推荐走 WSL2
- skill 中的部署文档、模板、验收清单都按上述策略输出，避免交付时出现“文档说支持 Windows，但实际上没有正式运维路径”的认知偏差。
