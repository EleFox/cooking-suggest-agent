#!/usr/bin/env bash
# 启动全部服务（后台运行）。首次使用建议先执行 ./build.sh。
# 用法：./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "[start] 未发现 .env，正在根据 .env.example 生成。"
  cp .env.example .env
fi

# 若使用宿主机目录作为数据源，则提前创建，确保 bind mount 落位正确。
DATA_SOURCE="$(grep -E '^WEB_DATA_SOURCE=' .env | tail -n1 | cut -d= -f2- || true)"
case "${DATA_SOURCE:-./data/web}" in
  /*|./*|../*) mkdir -p "${DATA_SOURCE}" ;;
  *) : ;; # 命名卷由 Docker 管理，无需创建目录
esac

echo "[start] 启动服务..."
docker compose -f docker-compose.yml up -d --remove-orphans

echo "[start] 当前状态："
docker compose -f docker-compose.yml ps
FRONTEND_PORT="$(grep -E '^FRONTEND_PORT=' .env | tail -n1 | cut -d= -f2- || true)"
echo "[start] 前端访问：http://localhost:${FRONTEND_PORT:-8906}"
