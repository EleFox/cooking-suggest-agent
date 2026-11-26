# cooking-builder

Cooking Suggest 的容器化打包目录。使用 `docker-compose` 将系统拆分为三个镜像：

| 服务 | 镜像 | 源码 | 运行时 |
| --- | --- | --- | --- |
| `frontend` | `cooking-web-frontend` | `cooking-web-service/frontend` | Nginx（托管 Vite 产物 + 反向代理 `/api`） |
| `web-backend` | `cooking-web-backend` | `cooking-web-service/backend` | FastAPI + SQLite |
| `agent-service` | `cooking-agent-service` | `cooking-agent-service` | FastAPI + LangGraph/LangChain |

## 架构与调用关系

```
                 ┌─────────────────────────────┐
   浏览器  ───▶  │ frontend (Nginx :80)        │
                 │  /       -> 静态 SPA        │
                 │  /api/   -> web-backend     │
                 └──────────────┬──────────────┘
                                │ (compose 网络)
                                ▼
                 ┌─────────────────────────────┐        ┌──────────────────────┐
                 │ web-backend (FastAPI :8000) │ ─────▶ │ agent-service :9000  │
                 │   SQLite + 菜谱 MD          │ ◀───── │  LangGraph 决策      │
                 └──────────────┬──────────────┘  反向   └──────────┬───────────┘
                                │                菜谱查询              │
                                ▼                                    ▼
                    /app/datas (volume)                     Ollama / 自定义 LLM
                    ├── cooking.db
                    └── recipes/r-*.md
```

- Web 前端对所有 `/api` 请求使用相对路径，由 Nginx 转发到 `web-backend`。
- `web-backend` 通过 `AGENT_SERVICE_URL` 调用 `agent-service`。
- `agent-service` 通过 `API_RECIPES_QUERY` / `API_RECIPE_DETAIL_QUERY` **反向**调用 `web-backend` 的菜谱接口。
- 三个服务处于同一 compose 网络 `cooking-net`，通过服务名互联，无需暴露内部端口。

## 目录结构

```
cooking-builder/
├── docker-compose.yml        # 运行编排（仅声明 image，不含 build）
├── docker-compose.build.yml  # 构建覆盖文件（仅构建机器使用）
├── .env.example              # 环境变量模板（复制为 .env）
├── .gitignore
├── build.sh                  # 构建镜像（构建机器）
├── package.sh                # 离线打包为 tar 包（构建机器）
├── load.sh                   # 生产环境加载离线镜像
├── start.sh / stop.sh / logs.sh
├── web-backend/Dockerfile
├── agent-service/Dockerfile
├── docs/
│   ├── packaging.md          # 构建与离线打包
│   └── deployment.md         # 生产部署、升级与运维
└── frontend/
    ├── Dockerfile
    └── nginx.conf
```

> 构建上下文为仓库根目录（`..`），因此仓库根还新增了 `.dockerignore`
> 用于排除 `node_modules`、`.venv`、`datas`、`.env` 等，避免依赖与密钥进入镜像。

## 前置条件

- Docker Engine + Docker Compose v2
- 可访问的 LLM：
  - 当前 Agent 默认使用 **OpenAI 兼容的自定义服务**（`CUSTOM_*`），必须配置 `CUSTOM_API_KEY`；
  - 或使用本地 Ollama（`OLLAMA_*`，`host.docker.internal` 指向宿主机）。

## 快速开始

```bash
cd cooking-builder
cp .env.example .env          # 编辑 .env，至少填写 CUSTOM_API_KEY
./build.sh                    # 构建三个镜像
./start.sh                    # 后台启动
./logs.sh -f                  # 查看实时日志
./stop.sh                     # 停止并移除容器（保留数据）
```

启动后访问 `http://localhost:${FRONTEND_PORT}`（默认 `8906`）。

> 本地开发构建使用 `docker-compose.build.yml` 覆盖文件，`build.sh` 已封装；
> 若手动构建请用
> `docker compose -f docker-compose.yml -f docker-compose.build.yml build`。
> 基础 `docker-compose.yml` 只声明 `image`，因此生产环境加载镜像后可直接启动。

## 生产部署（离线 tar 包）

适合内网/无外网的生产服务器：在构建机器上打包镜像，拷贝到服务器后加载运行，
服务器无需源码、无需联网拉取基础镜像。

**1. 构建机器：生成离线包**

```bash
cd cooking-builder
vi .env                # 确认 IMAGE_TAG、TARGET_PLATFORM（如 linux/amd64）、密钥
./package.sh           # 构建 + docker save + 打包
# 产物：dist/cooking-suggest-<IMAGE_TAG>.tar.gz（含三个镜像与运行时文件）
```

- 目标架构由 `TARGET_PLATFORM` 决定（默认 `linux/amd64`）；跨架构构建需确保
  Docker 支持对应平台（Apple Silicon 构建 amd64 会走模拟，较慢）。
- `./package.sh --no-build` 可跳过构建，直接用本地已有镜像打包。

**2. 生产服务器：解包并启动**

```bash
tar xzf cooking-suggest-<tag>.tar.gz
cd cooking-suggest-<tag>
./load.sh                          # docker load 导入三个镜像
cp .env.example .env && vi .env    # 配置密钥、端口、WEB_DATA_SOURCE 等
./start.sh                         # 启动
```

包内文件：`docker-compose.yml`、`.env.example`、`load.sh`、`start.sh`、`stop.sh`、
`logs.sh`、`README.md`、`docs/`、`images.tar.gz`。生产端不包含 Dockerfile 与源码。

**升级**：在新版本重新 `./package.sh`，把新 tar 包传到服务器，`./stop.sh` 后
`./load.sh && ./start.sh`。数据目录（`WEB_DATA_SOURCE`）不受影响；如需回滚，
让旧 tar 包使用不同 `IMAGE_TAG` 并重新加载即可。

## 环境变量

模板见 `.env.example`。Compose 会自动加载同目录的 `.env` 做变量替换，并把对应
变量注入容器。主要分组：

| 变量 | 作用 | 默认 |
| --- | --- | --- |
| `FRONTEND_PORT` / `FRONTEND_BIND` | 前端对外端口/绑定 | `8906` / `0.0.0.0` |
| `WEB_BACKEND_PORT` / `AGENT_SERVICE_PORT` | 后端调试端口 | `8000` / `9000` |
| `LOCAL_BIND` | 上两个端口的绑定地址 | `127.0.0.1` |
| `WEB_DATA_SOURCE` | SQLite 与菜谱数据的数据源（目录或命名卷） | `./data/web` |
| `WEB_DATA_VOLUME_NAME` | 命名卷名称（`WEB_DATA_SOURCE=cooking-web-datas` 时生效） | `cooking-web-datas` |
| `DB_FILENAME` | SQLite 文件名 | `cooking.db` |
| `DEBUG` / `LOG_LEVEL` | 通用调试与日志级别 | `false` / `INFO` |
| `AGENT_SERVICE_TIMEOUT` | web-backend 调用 Agent 超时（秒） | `600.0` |
| `DECISION_MAX_WORKERS` | 决策线程池大小 | `4` |
| `LLM_PROVIDER` | Agent 主模型供应方：`custom` / `ollama` / `deepseek` | `custom` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | 本地 Ollama | `192.168.123.35:11434` / `qwen3.5:9b` |
| `CUSTOM_BASE_URL` / `CUSTOM_MODEL` / `CUSTOM_API_KEY` | OpenAI 兼容服务（默认 LLM） | 见模板 |
| `DEEPSEEK_BASE_URL` / `DEEPSEEK_MODEL` / `DEEPSEEK_API_KEY` | DeepSeek 官方（备用） | 见模板 |
| `API_TIMEOUT` | Agent 反向调用菜谱接口超时（秒） | `30` |
| `IMAGE_TAG` | 镜像标签，用于回滚 | `latest` |
| `TARGET_PLATFORM` | 镜像目标平台（生产服务器架构） | `linux/amd64` |

服务间的内部地址（`AGENT_SERVICE_URL`、`API_RECIPES_QUERY`、`API_RECIPE_DETAIL_QUERY`）
由 compose 固定为网络内服务名，无需也不建议在 `.env` 中覆盖。

## 数据持久化（升级不丢老数据）

`web-backend` 把 SQLite 与菜谱 MD 统一存放在容器内固定路径 `/app/datas`：

- `/app/datas/${DB_FILENAME}`：SQLite 数据库（WAL 模式，含 `-wal`/`-shm`）；
- `/app/datas/recipes/r-{id}.md`：菜谱做法正文。

该目录通过 `${WEB_DATA_SOURCE}` 映射到宿主机目录或命名卷：

- **宿主机目录（默认，`WEB_DATA_SOURCE=./data/web`）**：数据直接可见，便于备份与
  迁移已有数据（默认落在 `cooking-builder/data/web`）；
- **命名卷（`WEB_DATA_SOURCE=cooking-web-datas`）**：在 macOS/Windows 的
  Docker Desktop 上，命名卷存储在 Linux 虚拟机内部文件系统，SQLite 文件锁语义更
  完整，可避免 bind mount（virtiofs/osxfs）下偶发的 `database is locked`。

因此：

1. **升级不丢数据**：`./build.sh && ./start.sh` 重建/替换容器不会删除数据源；
2. **路径稳定**：`t_recipe.file_path` 存储的是容器内绝对路径（如
   `/app/datas/recipes/r-1.md`），容器内挂载点固定，旧库记录在升级后仍能解析；
3. **迁移老数据（bind 方式最直接）**：把已有 `cooking.db`（连同 `-wal`/`-shm`，
   建议先停服做一致性快照）和 `recipes/` 目录放入 `${WEB_DATA_SOURCE}` 后再启动；
   也可直接将 `WEB_DATA_SOURCE` 指向上游项目的 `../cooking-web-service/backend/datas`；
4. **备份**：bind 方式直接备份该目录；命名卷可用
   `docker run --rm -v cooking-web-datas:/data -v "$PWD":/backup alpine tar czf /backup/datas.tgz -C /data .`。

> 首次启动且数据目录为空时，服务会自动建表并写入要素字典种子数据（不含业务数据）。

## 常用操作

```bash
# 仅重建某个服务
docker compose -f docker-compose.yml up -d --build web-backend

# 回滚到旧镜像（构建时用不同 IMAGE_TAG 产出）
IMAGE_TAG=v1.2.0 docker compose -f docker-compose.yml up -d

# 进入容器排查
docker compose -f docker-compose.yml exec web-backend sh
```

## 说明

- 后端与 Agent 端口默认只绑定 `127.0.0.1`，对外访问请统一走前端 Nginx；
  如需局域网直连，将 `LOCAL_BIND` 改为 `0.0.0.0`。
- `.env` 含密钥，已在 `cooking-builder/.gitignore` 与根 `.dockerignore` 中排除。

## 常见问题

- **agent-service 反复重启（Restarting）**：多为 `CUSTOM_API_KEY` 为空。
  `agent/graph/llm.py` 在导入时就构造 `ChatOpenAI`，缺少密钥会直接抛
  `openai.OpenAIError: Missing credentials` 导致进程退出。在 `.env` 填写
  `CUSTOM_API_KEY`（或切换为 Ollama）后执行
  `docker compose -f docker-compose.yml up -d agent-service` 即可。
  查看原因：`./logs.sh agent-service`。
- **容器时间/日志时区**：镜像默认 UTC，如需本地时区可在 compose 中为服务加
  `TZ=Asia/Shanghai` 环境变量。
