# Windows / WSL2 部署说明（V4.3.1）

## 结论

- Windows 客户若要跑 `V4.3.1` 单群生产稳定版，推荐路线是：`Windows + WSL2 + Ubuntu LTS`。
- 不推荐把 OpenClaw Gateway、watchdog 和 SQLite 状态层直接跑在 Windows 原生 shell / service 上。
- 原因不是“绝对不能跑”，而是当前官方文档与我们现网验证都更稳定地落在 `WSL2` 路线。

## 官方依据

1. OpenClaw 安装页明确说明：Windows 上强烈建议在 `WSL2` 中运行 OpenClaw。  
   来源：[OpenClaw Install](https://docs.openclaw.ai/install/index)
2. OpenClaw 平台页明确说明：
   - macOS：`LaunchAgent`
   - Linux/WSL2：`systemd` 用户服务  
   来源：[OpenClaw 平台](https://docs.openclaw.ai/zh-CN/platforms)
3. Microsoft 官方文档说明：WSL2 支持 `systemd`，在 `/etc/wsl.conf` 中加 `[boot] systemd=true` 后可用。  
   来源：[Advanced settings configuration in WSL](https://learn.microsoft.com/en-us/windows/wsl/wsl-config)

## 推荐环境

- Windows 11 或较新的 Windows 10
- WSL 版本 `0.67.6+`
- Ubuntu `22.04 LTS` 或 `24.04 LTS`
- `python3` 可用，且内置 `sqlite3`
- OpenClaw CLI 按 Linux 方式安装在 WSL2 内

## 安装步骤

### 1. 安装 WSL2

在 PowerShell 中执行：

```powershell
wsl --install -d Ubuntu-24.04
```

安装完成后，首次进入 Ubuntu 完成 Linux 用户初始化。

### 2. 启用 systemd

在 WSL2 的 Ubuntu 中写入 `/etc/wsl.conf`：

```ini
[boot]
systemd=true
```

可直接参考模板：
- `templates/windows/wsl.conf.example`

然后回到 PowerShell 执行：

```powershell
wsl.exe --shutdown
```

重新打开 Ubuntu 后验证：

```bash
systemctl --user status
```

## V4.3.1 部署建议

- OpenClaw、SQLite、watchdog、session transcript 全部放在 WSL2 内部路径，例如：

```text
~/.openclaw
```

- 不要把 SQLite 主状态库放在 `/mnt/c/...` 这类 Windows 挂载盘里。
- 原因：跨文件系统权限、大小写与锁行为更复杂，不利于稳定写入。

## watchdog 路线

在 WSL2 中，直接复用 Linux 方案：
- `templates/systemd/v4-3-watchdog.service`
- `templates/systemd/v4-3-watchdog.timer`

安装后建议执行：

```bash
systemctl --user daemon-reload
systemctl --user enable --now v4-3-watchdog.timer
systemctl --user status v4-3-watchdog.timer
```

## 验收建议

### 基础检查

```bash
openclaw gateway status
python3 --version
python3 - <<'PY'
import sqlite3
print(sqlite3.sqlite_version)
PY
systemctl --user is-active openclaw-gateway.service || true
systemctl --user is-active v4-3-watchdog.timer || true
```

### 生产验收

仍按 Linux 路线执行：
- 一次性 `WARMUP`
- `check_v4_3_canary.py`
- SQLite `jobs / job_participants / job_events`
- 群内 6 类可见消息校验

## 不推荐的路线

### 1. Windows 原生服务化

当前不推荐把以下能力直接放在 Windows 原生服务里做正式交付：
- OpenClaw Gateway 主运行时
- V4.3.1 watchdog
- SQLite 状态机主路径

原因：
- 当前官方平台文档没有把 Windows 原生 service 作为推荐主路径
- 我们这套 skill 的稳定交付经验也全部基于 Linux / WSL2 / macOS 的类 Unix 运行模型

### 2. 把核心状态放在 Windows 挂载盘

例如：

```text
/mnt/c/Users/<name>/.openclaw
```

这会增加：
- 锁行为差异
- 路径转义问题
- service 用户上下文差异

生产不建议。

## 交付建议

如果客户是 Windows：
1. 默认把交付目标定义为 `WSL2`。
2. README、SOP、Codex 提示词里都明确写：`platform=wsl2`。
3. watchdog 与 OpenClaw service 完全复用 Linux 路线。
4. 只在客户明确拒绝 WSL2 时，再单独评估 Windows 原生偏差，不默认承诺。 
