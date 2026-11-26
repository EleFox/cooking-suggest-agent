# 生产部署、升级与运维

本文档面向**生产服务器**，描述如何加载离线 tar 包、启动服务、保留数据以及升级回滚。
构建与打包见 [packaging.md](./packaging.md)。

## 1. 前置条件

- Docker Engine + Docker Compose v2。
- 生产服务器**无需**源码，**无需**外网（基础镜像与依赖已含在离线包中）。
- 若使用 `LLM_PROVIDER=custom` 或 `deepseek`，服务器需能访问对应 LLM 服务地址；
  若使用 `ollama`，需能访问 Ollama 服务。
- 确认服务器架构与离线包的 `TARGET_PLATFORM` 一致（`uname -m`）。

## 2. 加载与启动

```bash
tar xzf cooking-suggest-<tag>.tar.gz
cd cooking-suggest-<tag>

./load.sh                          # 导入三个镜像
cp .env.example .env
vi .env                            # 填写密钥、端口、数据源等
./start.sh                         # 后台启动并打印状态
```

启动后访问 `http://<服务器IP>:${FRONTEND_PORT}`（默认 `8906`）。

`start.sh` 会：

1. 若 `.env` 不存在则从 `.env.example` 生成；
2. 若 `WEB_DATA_SOURCE` 是目录则创建之（命名卷无需）；
3. `docker compose up -d --remove-orphans` 并输出状态与访问地址。

## 3. 配置（`.env`）

配置项说明见 [packaging.md#7-环境变量参考](./packaging.md#7-环境变量参考)。
生产环境通常只需关注：

| 变量 | 生产建议 |
| --- | --- |
| `IMAGE_TAG` | 与离线包标签一致，勿随意改动 |
| `FRONTEND_PORT` | 对外访问端口 |
| `FRONTEND_BIND` | 对外可填 `0.0.0.0`，置于反向代理后可用 `127.0.0.1` |
| `LOCAL_BIND` | 后端/Agent 调试端口默认仅本机，建议保持 `127.0.0.1` |
| `WEB_DATA_SOURCE` | **持久化关键**，见第 4 节；生产建议用命名卷或独立数据盘目录 |
| `LLM_PROVIDER` 及对应密钥 | 按实际使用的供应方填写 |
| `DEBUG` / `LOG_LEVEL` | 生产建议 `false` / `INFO` |

> `.env` 含密钥，请限制文件权限（如 `chmod 600 .env`），勿提交到仓库。

## 4. 数据持久化

`web-backend` 把 SQLite 与菜谱 MD 统一放在容器内**固定路径** `/app/datas`：

```
/app/datas/
├── ${DB_FILENAME}        # 默认 cooking.db（WAL 模式，另有 -wal/-shm）
└── recipes/r-{id}.md     # 菜谱做法正文
```

该路径通过 `WEB_DATA_SOURCE` 映射到容器外，两种方式：

1. **宿主机目录（默认）**：`WEB_DATA_SOURCE=./data/web`
   数据直接可见，便于备份与迁移；默认落在解包目录下的 `data/web`。
   也可指向独立数据盘，如 `/data/cooking/web`。
2. **命名卷**：`WEB_DATA_SOURCE=cooking-web-datas`
   在 macOS/Windows 的 Docker Desktop 上，命名卷存于 Linux 虚拟机内部文件系统，
   SQLite 文件锁语义更完整，可避免 bind mount 下偶发的 `database is locked`。

为什么路径固定很重要：数据库 `t_recipe.file_path` 存储的是**容器内绝对路径**
（如 `/app/datas/recipes/r-1.md`）。容器内挂载点固定不变，因此升级重建容器后，
旧库记录仍能正确解析到菜谱文件。

### 迁移已有数据

```bash
# bind 方式最直接：停止服务后，把旧数据库与菜谱目录放入数据源
./stop.sh
mkdir -p data/web
cp /path/to/old/cooking.db data/web/          # 连同 -wal / -shm 更稳妥
cp -r /path/to/old/recipes data/web/
./start.sh
```

> 建议先停服再复制，或对 SQLite 执行 `PRAGMA wal_checkpoint(TRUNCATE)`，保证一致性。

首次启动且数据源为空时，服务会自动建表并写入要素字典种子数据（不含业务数据）。

## 5. 升级与回滚

升级流程：

```bash
# 1) 新版本在构建机器上打包
./package.sh                       # IMAGE_TAG 建议改为新版本号

# 2) 传到服务器，解包并加载
tar xzf cooking-suggest-<newtag>.tar.gz && cd cooking-suggest-<newtag>
./load.sh
# 3) 复用原数据源与配置：从旧目录拷贝 .env，或按需修改
cp ../cooking-suggest-<oldtag>/.env .env
./start.sh
```

- 数据源（`WEB_DATA_SOURCE`）不被容器重建影响，升级不丢数据。
- 回滚：让旧 tar 包使用独立 `IMAGE_TAG`，`./load.sh` 加载旧镜像后启动即可；
  或将 `.env` 的 `IMAGE_TAG` 指回旧标签。

## 6. 备份与恢复

**bind 方式**：直接备份数据目录。

```bash
./stop.sh
tar czf datas-$(date +%Y%m%d).tgz -C data/web .
./start.sh
```

**命名卷方式**：

```bash
docker run --rm \
  -v cooking-web-datas:/data \
  -v "$PWD":/backup \
  alpine tar czf /backup/datas-$(date +%Y%m%d).tgz -C /data .
```

恢复时将归档内容解回同一数据源后再启动。

## 7. 运维命令

```bash
./logs.sh                      # 状态 + 最近日志
./logs.sh -f                   # 实时跟踪全部
./logs.sh agent-service -f     # 仅跟踪某服务
./stop.sh                      # 停止并移除容器（保留数据）
```

直接使用 compose（在解包目录内）：

```bash
docker compose -f docker-compose.yml ps
docker compose -f docker-compose.yml restart web-backend
docker compose -f docker-compose.yml exec web-backend sh
```

## 8. 故障排查

- **agent-service 反复重启**：多为 LLM 相关。
  - `LLM_PROVIDER=custom` 但 `CUSTOM_API_KEY` 为空：`agent/graph/llm.py` 在导入期
    构造模型会抛 `openai.OpenAIError: Missing credentials`。填写密钥后
    `docker compose -f docker-compose.yml up -d agent-service`。
  - 查看原因：`./logs.sh agent-service`。
- **SQLite `database is locked`**：Docker Desktop（macOS/Windows）下 bind mount 的
  文件锁语义不完整。将 `WEB_DATA_SOURCE` 改为命名卷（`cooking-web-datas`）。
- **端口占用**：修改 `.env` 中对应端口，或调整 `FRONTEND_BIND` / `LOCAL_BIND`。
- **`exec format error`**：镜像架构与服务器不符，用匹配 `TARGET_PLATFORM` 的包。
- **前端 200 但接口 404/502**：确认 `web-backend` 容器健康（`./logs.sh`），
  Nginx 会在后端未就绪时先启动并通过 resolver 延迟解析上游。
- **决策请求超时**：长耗时链路由 `AGENT_SERVICE_TIMEOUT`（默认 600s）与 Nginx
  的 `proxy_read_timeout` 控制，按需调大。
