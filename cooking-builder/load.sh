#!/usr/bin/env bash
# 在生产服务器上加载离线镜像包。
# 用法：./load.sh
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

IMG="images.tar.gz"
if [ ! -f "$IMG" ]; then
  echo "[load] 未找到 $IMG，请确认离线包完整。" >&2
  exit 1
fi

echo "[load] 正在加载镜像（可能需要数十秒）..."
gunzip -c "$IMG" | docker load

echo "[load] 已加载镜像："
docker images | grep -E "cooking-(web-backend|web-frontend|agent-service)" || true
