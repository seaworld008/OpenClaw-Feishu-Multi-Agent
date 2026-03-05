#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
用法:
  check_v3_dispatch_canary.sh --log <path> --start-line <n> [--agents "a,b,c"]

说明:
  - 从日志指定起始行之后，检查是否出现目标 agent 会话派发轨迹
  - 默认 agent: sales_agent,ops_agent,finance_agent
  - 成功返回 0 (DISPATCH_OK)
  - 失败返回 2 (DISPATCH_INCOMPLETE)
EOF
}

LOG=""
START_LINE=""
AGENTS="sales_agent,ops_agent,finance_agent"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --log)
      LOG="${2:-}"
      shift 2
      ;;
    --start-line)
      START_LINE="${2:-}"
      shift 2
      ;;
    --agents)
      AGENTS="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$LOG" || -z "$START_LINE" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$LOG" ]]; then
  echo "日志文件不存在: $LOG" >&2
  exit 1
fi

if ! [[ "$START_LINE" =~ ^[0-9]+$ ]]; then
  echo "start-line 必须是正整数" >&2
  exit 1
fi

TMP_FILE="$(mktemp)"
trap 'rm -f "$TMP_FILE"' EXIT

tail -n "+$((START_LINE + 1))" "$LOG" > "$TMP_FILE"

IFS=',' read -r -a AGENT_LIST <<< "$AGENTS"

missing=()
for agent in "${AGENT_LIST[@]}"; do
  agent="$(echo "$agent" | xargs)"
  if [[ -z "$agent" ]]; then
    continue
  fi
  if rg -q "session=agent:${agent}:" "$TMP_FILE"; then
    echo "OK: found dispatch trace for ${agent}"
  else
    echo "MISS: no dispatch trace for ${agent}"
    missing+=("$agent")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "DISPATCH_INCOMPLETE: missing agents => ${missing[*]}"
  exit 2
fi

echo "DISPATCH_OK: all target agent session traces found"
exit 0

