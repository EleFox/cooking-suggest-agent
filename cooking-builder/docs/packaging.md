# 构建与离线打包

本文档面向**构建机器**，描述如何从源码构建三个镜像并生成可离线部署的 tar 包。
生产服务器上的部署步骤见 [deployment.md](./deployment.md)。

## 1. 镜像概览

系统拆分为三个镜像，源码均来自仓库内两个子项目：

| 服务 | 镜像名 | 源码目录 | 运行时基础镜像 | 端口 |
| --- | --- | --- | --- | --- |
| `frontend` | `cooking-web-frontend` | `cooking-web-service/frontend` | `nginx:1.27-alpine`（Node 24 + pnpm 10 多阶段构建） | 80 |
| `web-backend` | `cooking-web-backend` | `cooking-web-service/backend` | `python:3.13-slim` | 8000 |
| `agent-service` | `cooking-agent-service` | `cooking-agent-service` | `python:3.13-slim` | 9000 |

调用关系：

- 前端 Nginx 托管 Vite 产物，并把 `/api` 反向代理到 `web-backend`；
- `web-backend` 调用 `agent-service`（`AGENT_SERVICE_URL`）；
- `agent-service` 反向调用 `web-backend` 的菜谱接口；
- 三者位于 compose 网络 `cooking-net`，通过服务名互联。

## 2. 打包目录与文件职责

```
cooking-builder/
├── docker-compose.yml        # 运行编排：仅声明 image，不含 build
├── docker-compose.build.yml  # 构建覆盖：声明 context/dockerfile/platform（仅构建机器用）
├── .env.example              # 环境变量模板（配置项权威来源）
├── .env                      # 本地实际配置（含密钥，已 gitignore）
├── build.sh                  # 构建三个镜像
├── package.sh                # 构建 + 导出镜像 + 打包为 tar
├── load.sh                   # 生产端加载离线镜像
├── start.sh / stop.sh / logs.sh
├── web-backend/Dockerfile
├── agent-service/Dockerfile
└── frontend/
    ├── Dockerfile
    └── nginx.conf
```

> 仓库根目录另有 `.dockerignore`，用于排除 `node_modules`、`.venv`、`datas`、`.env`
> 等，避免依赖与密钥进入镜像。

## 3. 前置条件

- Docker Engine + Docker Compose v2（开发机上建议 Docker Desktop）。
- 构建机器需能访问网络以下载基础镜像与依赖（生产服务器不需要）。
- 目标平台的镜像构建能力：
  - `linux/amd64`：x86_64 机器原生支持；
  - `linux/arm64`：ARM 机器原生支持；在 x86 上构建 arm64 会走 QEMU 模拟，较慢。

## 4. 构建原理

### 4.1 Dockerfile 分层

三个 Dockerfile 均先拷贝依赖清单并安装依赖，再拷贝源码，以最大化利用镜像层缓存：

- 后端/Agent：`COPY .../requirements.txt` → `pip install` → `COPY` 源码；
- 前端：`COPY package.json pnpm-lock.yaml` → `pnpm install --frozen-lockfile`
  → `COPY` 源码 → `pnpm run build`，产物 `dist/` 再拷入 Nginx 镜像。

健康检查使用标准库/内置工具，不额外安装 `curl`：

- 后端 / Agent：`python -c "urllib.request.urlopen('.../api/health')"`；
- 前端：`wget -qO- http://127.0.0.1/`。

### 4.2 基础编排与构建编排分离

`docker-compose.yml`（运行用）只声明 `image`，**不含 `build`**；构建相关声明放在
`docker-compose.build.yml`（覆盖文件）。这样生产端只加载镜像即可启动，无需源码路径，
避免 `context: ..` 在服务器上不存在导致的问题。

手动构建需同时指定两个文件：

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml build
```

### 4.3 目标平台

构建覆盖文件为每个服务设置 `platform: ${TARGET_PLATFORM:-linux/amd64}`。
`TARGET_PLATFORM` 必须与生产服务器架构一致，否则镜像无法运行（见第 8 节）。

## 5. 本地构建

```bash
cd cooking-builder
[ -f .env ] || cp .env.example .env   # 首次
vi .env                                # 确认 TARGET_PLATFORM、密钥等
./build.sh                             # 等价于带覆盖文件的 compose build
```

`./build.sh --no-cache` 可强制不使用缓存重建。

仅重建单个服务：

```bash
docker compose -f docker-compose.yml -f docker-compose.build.yml build web-backend
```

## 6. 离线打包

```bash
./package.sh               # 构建 + docker save + gzip + tar
./package.sh --no-cache    # 强制重建后打包
./package.sh --no-build    # 跳过构建，用本地已有镜像打包
```

`package.sh` 的执行步骤：

1. 读取 `.env` 中的 `IMAGE_TAG`（默认 `latest`）；
2. 构建三个镜像（除非 `--no-build`）；
3. 校验三个镜像均存在，避免打出空包；
4. `docker save` 导出为一个 `images.tar` 并 gzip（优先 `pigz`）；
5. 复制运行时文件（compose、`.env.example`、脚本、README）；
6. 打包为 `dist/cooking-suggest-<IMAGE_TAG>.tar.gz`。

### 产物结构

```
dist/cooking-suggest-<tag>.tar.gz
└── cooking-suggest-<tag>/
    ├── docker-compose.yml     # 运行编排（无 build）
    ├── .env.example           # 环境变量模板（不含真实密钥）
    ├── images.tar.gz          # docker save 导出的三个镜像
    ├── load.sh                # 加载镜像
    ├── start.sh / stop.sh / logs.sh
    ├── README.md
    └── docs/                  # 本文档与部署文档
```

生产端不包含 Dockerfile 与源码。

### 版本与标签

- 建议每次发布使用明确的 `IMAGE_TAG`（如 `v1.2.0`），便于识别与回滚。
- 改动 `.env` 的 `IMAGE_TAG` 后重新 `./package.sh` 即可产出对应标签的包。

## 7. 环境变量参考

完整模板见 [../.env.example](../.env.example)。构建/部署相关：

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `IMAGE_TAG` | 镜像标签 | `latest` |
| `TARGET_PLATFORM` | 镜像目标平台 | `linux/amd64` |
| `FRONTEND_PORT` / `FRONTEND_BIND` | 前端对外端口 / 绑定地址 | `8906` / `0.0.0.0` |
| `WEB_BACKEND_PORT` / `AGENT_SERVICE_PORT` | 后端调试端口 | `8000` / `9000` |
| `LOCAL_BIND` | 上述两个调试端口的绑定地址 | `127.0.0.1` |
| `WEB_DATA_SOURCE` | SQLite 与菜谱数据的数据源（目录或命名卷） | `./data/web` |
| `WEB_DATA_VOLUME_NAME` | 命名卷名称 | `cooking-web-datas` |
| `DB_FILENAME` | SQLite 文件名 | `cooking.db` |
| `DEBUG` / `LOG_LEVEL` | 通用调试与日志级别 | `false` / `INFO` |
| `AGENT_SERVICE_TIMEOUT` | web-backend 调用 Agent 超时（秒） | `600.0` |
| `DECISION_MAX_WORKERS` | 决策线程池大小 | `4` |
| `LLM_PROVIDER` | Agent 主模型供应方：`custom` / `ollama` / `deepseek` | `custom` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 本地 Ollama | 见模板 |
| `CUSTOM_BASE_URL` / `CUSTOM_MODEL` / `CUSTOM_API_KEY` | OpenAI 兼容自定义服务 | 见模板 |
| `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` / `DEEPSEEK_API_KEY` | DeepSeek 官方 | 见模板 |
| `API_TIMEOUT` | Agent 反向调用菜谱接口超时（秒） | `30` |

由 compose 固定的内部地址（无需在 `.env` 配置）：

- `AGENT_SERVICE_URL=http://agent-service:9000`
- `API_RECIPES_QUERY=http://web-backend:8000/api/recipes`
- `API_RECIPE_DETAIL_QUERY=http://web-backend:8000/api/recipes/detail`
- `DATABASE_PATH=/app/datas/${DB_FILENAME}`

> 只有被选中的 `LLM_PROVIDER` 会被实例化，因此未选中的供应方无需填写密钥。

## 8. 常见构建问题

- **架构不匹配**：镜像构建为 `amd64` 但服务器是 `arm64`（或反之），运行时会报
  `exec format error`。用 `docker image inspect <image> --format '{{.Architecture}}'`
  核对，并将 `TARGET_PLATFORM` 调整为服务器架构（`uname -m` / `docker version`）。
- **pnpm 提示 `Ignored build scripts: esbuild`**：pnpm 10 默认拦截依赖构建脚本。
  esbuild 通过平台可选依赖安装二进制，`vite build` 仍可成功，无需处理。
- **构建上下文过大**：确认根目录 `.dockerignore` 生效，且 `node_modules`、`.venv`
  未被纳入上下文。
- **Agent 镜像较大（约 400MB）**：LangChain/LangGraph/pandas 等依赖所致，属正常。
