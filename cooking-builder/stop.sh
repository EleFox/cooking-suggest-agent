#!/usr/bin/env bash
# 停止并移除全部容器（默认保留数据卷/数据目录）。
# 用法：./stop.sh          停止并移除容器
#       ./stop.sh --volumes 同时清理（谨慎：仅清理命名卷，bind 数据目录不受影响）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

docker compose -f docker-compose.yml down "$@"
