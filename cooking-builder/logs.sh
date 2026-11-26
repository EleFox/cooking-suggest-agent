#!/usr/bin/env bash
# 查看服务状态 / 日志。
# 用法：./logs.sh           汇总最近日志
#       ./logs.sh -f        实时跟踪
#       ./logs.sh web-backend -f   仅跟踪指定服务
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ "${1:-}" = "" ]; then
  docker compose -f docker-compose.yml ps
  docker compose -f docker-compose.yml logs --tail=80
else
  docker compose -f docker-compose.yml logs "$@"
fi
