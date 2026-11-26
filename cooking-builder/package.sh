#!/usr/bin/env bash
# 离线打包：构建三个镜像并导出为可在生产服务器直接部署的 tar 包。
#
# 产物：dist/cooking-suggest-<IMAGE_TAG>.tar.gz，解压后包含：
#   docker-compose.yml / .env.example / load.sh / start.sh / stop.sh / logs.sh / README.md
#   images.tar.gz（docker save 导出的三个镜像）
#
# 生产部署：
#   tar xzf cooking-suggest-<tag>.tar.gz && cd cooking-suggest-<tag>
#   ./load.sh && cp .env.example .env && (编辑 .env) && ./start.sh
#
# 用法：./package.sh [--no-cache] [--no-build]
#   --no-build  跳过构建，仅用本地已有镜像打包（要求三个镜像已存在）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  echo "[package] 未发现 .env，已根据 .env.example 生成；请按需修改（尤其是密钥）。"
  cp .env.example .env
fi

# 从 .env 读取镜像标签（仅取需要的一项，避免 source 整个文件）。
TAG="$(grep -E '^IMAGE_TAG=' .env | tail -n1 | cut -d= -f2- | tr -d '"' || true)"
TAG="${TAG:-latest}"

BUILD_ARGS=()
SKIP_BUILD=0
for arg in "$@"; do
  if [ "$arg" = "--no-build" ]; then
    SKIP_BUILD=1
  else
    BUILD_ARGS+=("$arg")
  fi
done

if [ "$SKIP_BUILD" -eq 0 ]; then
  echo "[package] 构建镜像（tag=${TAG}）..."
  docker compose -f docker-compose.yml -f docker-compose.build.yml build "${BUILD_ARGS[@]}"
else
  echo "[package] 跳过构建，使用本地已有镜像（tag=${TAG}）。"
fi

IMAGES=(
  "cooking-web-backend:${TAG}"
  "cooking-web-frontend:${TAG}"
  "cooking-agent-service:${TAG}"
)

# 确认镜像存在，避免打包出空包。
for img in "${IMAGES[@]}"; do
  if ! docker image inspect "$img" >/dev/null 2>&1; then
    echo "[package] 错误：缺少镜像 $img，请先执行 ./build.sh（或去掉 --no-build）。" >&2
    exit 1
  fi
done

DIST="$ROOT/dist"
STAGE="$DIST/cooking-suggest-${TAG}"
rm -rf "$STAGE"
mkdir -p "$STAGE"

echo "[package] 导出镜像到 images.tar（随后压缩）..."
docker save -o "$STAGE/images.tar" "${IMAGES[@]}"
if command -v pigz >/dev/null 2>&1; then
  pigz -f "$STAGE/images.tar"
else
  gzip -f "$STAGE/images.tar"
fi

echo "[package] 复制运行时文件..."
cp docker-compose.yml .env.example load.sh start.sh stop.sh logs.sh README.md "$STAGE/"
cp -r docs "$STAGE/"

OUT="$DIST/cooking-suggest-${TAG}.tar.gz"
echo "[package] 生成离线包：$OUT"
tar -czf "$OUT" -C "$DIST" "cooking-suggest-${TAG}"

echo "[package] 完成。"
ls -lh "$OUT"
echo "[package] 生产部署："
echo "  tar xzf $(basename "$OUT") && cd cooking-suggest-${TAG}"
echo "  ./load.sh && cp .env.example .env && vi .env && ./start.sh"
