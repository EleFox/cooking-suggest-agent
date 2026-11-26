# 构建上下文：仓库根目录（cooking-suggest-agent/）
# 构建命令：docker build -f cooking-builder/agent-service/Dockerfile ..
# ---------------------------------------------------------------------------
# cooking-agent-service（LangGraph / LangChain 决策服务）
# ---------------------------------------------------------------------------
FROM python:3.13-slim

# Python 运行时行为：实时日志、不写 pyc、pip 不缓存。
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 先装依赖，利用镜像层缓存。
COPY cooking-agent-service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 再拷贝源码（含 agent/ app/ common/ 及 prompts 下的 md 模板）。
COPY cooking-agent-service/ ./

# 监听端口（SERVER_PORT 由环境变量驱动，见 common/config.py）。
EXPOSE 9000

HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:9000/api/health', timeout=3).status==200 else 1)"

# 与 scripts/start-agent.sh 一致，由 app.main.run() 读取 SERVER_HOST/PORT 启动。
CMD ["python", "-m", "app.main"]
