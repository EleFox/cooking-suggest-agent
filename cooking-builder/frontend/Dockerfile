# 构建上下文：仓库根目录（cooking-suggest-agent/）
# 构建命令：docker build -f cooking-builder/frontend/Dockerfile ..
# ---------------------------------------------------------------------------
# cooking-web-service 前端（React + Vite）
#   stage 1：Node 构建静态资源
#   stage 2：Nginx 托管静态资源，并把 /api 反向代理到 web-backend
# ---------------------------------------------------------------------------
FROM node:24-alpine AS build

WORKDIR /app

# 使用与本地一致的 pnpm 主版本（package.json engines 要求 node >= 24）。
RUN npm install -g pnpm@10

# 先装依赖，利用镜像层缓存；frozen-lockfile 保证可复现构建。
COPY cooking-web-service/frontend/package.json cooking-web-service/frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 拷贝其余源码并构建（tsc -b && vite build，输出到 dist/）。
COPY cooking-web-service/frontend/ ./
RUN pnpm run build

# ---------------------------------------------------------------------------
FROM nginx:1.27-alpine AS runtime

# 站点与反向代理配置。
COPY cooking-builder/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# 构建产物。
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
