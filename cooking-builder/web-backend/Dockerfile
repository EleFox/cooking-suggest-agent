# 构建上下文：仓库根目录（cooking-suggest-agent/）
# 构建命令：docker build -f cooking-builder/web-backend/Dockerfile ..
# ---------------------------------------------------------------------------
# cooking-web-service 后端（FastAPI + SQLite）
# ---------------------------------------------------------------------------
FROM python:3.13-slim

# Python 运行时行为：实时日志、不写 pyc、pip 不缓存。
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 先装依赖，利用镜像层缓存：requirements 不变时无需重装。
COPY cooking-web-service/backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝源码（.dockerignore 已排除 .env / .venv / datas 等）。
COPY cooking-web-service/backend/ ./

# SQLite 数据库与菜谱 MD 的固定容器内目录，运行时由 volume 覆盖挂载。
RUN mkdir -p /app/datas

# 监听端口（与 scripts/start-backend.sh 保持一致）。
EXPOSE 8000

# 健康检查使用标准库，避免为镜像额外安装 curl。
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status==200 else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
