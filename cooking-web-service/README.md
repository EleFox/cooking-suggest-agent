# Cooking Web Service

用于对接独立 Python Agent Service 的 Web 服务骨架（MVP）。

```text
浏览器
  ↓
Web 前端 (React + Vite)
  ↓ HTTP
Web API (FastAPI)
  ↓ HTTP
独立 Agent Service（未来）
```

## 技术栈

- 前端：React + TypeScript + Vite + Tailwind CSS
- 后端：Python + FastAPI + Pydantic + Uvicorn
- 通信：普通 HTTP + JSON

## 项目目录

```text
cooking-web-service/
├── frontend/
│   ├── src/
│   │   ├── components/    # UI 组件
│   │   ├── pages/         # 页面
│   │   ├── api/           # 后端 API 封装
│   │   ├── types/         # TS 类型定义
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
├── backend/
│   ├── app/
│   │   ├── api/routes/    # HTTP 路由（health.py）
│   │   ├── schemas/       # Pydantic 模型
│   │   ├── services/      # 业务服务（agent_client.py 预留）
│   │   └── main.py
│   └── requirements.txt
├── scripts/
│   ├── start.sh
│   ├── start-backend.sh
│   └── start-frontend.sh
└── README.md
```

## 安装依赖

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## 启动 Backend

```bash
scripts/start-backend.sh
```

后端默认运行在 `http://localhost:8000`。

## 启动 Frontend

```bash
scripts/start-frontend.sh
```

前端 Vite dev server 运行在 `http://localhost:8905`，通过 Vite Proxy 将 `/api/*` 转发给后端（`localhost:8000`）。

## 同时启动

```bash
scripts/start.sh
```

## 浏览器访问地址

```text
http://localhost:8905
```

首页显示 `Hello`，并通过 HTTP 请求展示后端 health 结果：

```text
Hello

Backend Health
status: ok
```

## Health API 地址

```text
http://localhost:8905/api/health
```

返回：

```json
{
  "status": "ok"
}
```

（也可通过后端直连地址 `http://localhost:8000/api/health` 访问。）

## 后续 Agent Service 预期架构

```text
Frontend (React)
   ↓ HTTP
Web API (FastAPI)
   ↓ HTTP
Independent Agent Service
```

- Agent 调用统一封装在 `backend/app/services/agent_client.py`，当前为预留占位文件。
- React 不直接调用 Agent Service，只与 FastAPI 通信。
- API 路由只处理 HTTP 层，未来业务逻辑放入 `services/`。
