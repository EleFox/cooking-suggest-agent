#!/usr/bin/env bash
# 构建三个镜像（前端 / web-backend / agent-service）。
# 仅构建机器需要执行；生产环境请使用 package.sh 产出的离线 tar 包。
# 用法：./build.sh [--no-cache]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "[build] 未发现 .env，已根据 .env.example 生成；请按需修改（尤其是密钥）。"
  cp .env.example .env
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.build.yml)

echo "[build] 开始构建镜像..."
"${COMPOSE[@]}" build "$@"

echo "[build] 构建完成。查看镜像："
docker images | grep -E "cooking-(web-backend|web-frontend|agent-service)" || true
