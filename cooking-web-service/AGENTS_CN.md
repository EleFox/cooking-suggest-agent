# cooking-web-service

## 项目定位

这个项目是一个用于辅助用户进行烹饪决策的轻量化移动端H5应用，当前服务是项目的前端和接口服务，用途是获取用户的决策条件然后对接另一个Agent服务（不在该项目文件夹下），并展示对应的结果。

## 技术栈

### 前端：

### Core

- React 19
- TypeScript
- Vite
- Node.js >= 24
- pnpm 10

### Styling and UI

- Tailwind CSS 4
- shadcn/ui
- Radix UI
- Lucide React

### Routing

- React Router

### Form Handling

- React Hook Form
- Zod
- @hookform/resolvers

### State Management

- Zustand

### Animation

- Framer Motion

### 后台：

### Core：

- python
- 虚拟环境 `backend\.venv`

### 框架：

- fastapi

## 项目目录说明

cooking-web-service/
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── Backend API request functions
│   │   │
│   │   ├── components/
│   │   │   └── Reusable UI components
│   │   │
│   │   ├── pages/
│   │   │   └── Page-level components
│   │   │
│   │   ├── router/
│   │   │   └── Route configuration
│   │   │
│   │   ├── stores/
│   │   │   └── Zustand global state
│   │   │
│   │   ├── hooks/
│   │   │   └── Reusable React hooks
│   │   │
│   │   ├── schemas/
│   │   │   └── Zod validation schemas
│   │   │
│   │   ├── types/
│   │   │   └── TypeScript type definitions
│   │   │
│   │   ├── lib/
│   │   │   └── Frontend utility functions
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   └── Api routes
│   │   │
│   │   ├── schemas/
│   │   │   └── Pydantic API request/response agent service
│   │   │
│   │   ├── services/
│   │   │   └── Services of api
│   │   │
│   │   ├── core/
│   │   │   └── Backend application configuration
│   │   │
│   │   ├── main.py
│   │   └── __init__.py
│   │
│   ├── tests/
│   ├── requirements.txt
│   └── ...
│
├── docs/
│   └── For project documents
│
├── scripts/
│   ├── Service start scripts
│   └── ...
└── ...

## 项目命令

### Frontend Development(In /frontend/)

- **Dev**: In /frontend/ run `npm run dev` OR run `/scripts/start-frontend.sh`
- **Build**: In /frontend/ run `npm build`
- **Format**: In /frontend/ run `npm run format`（自动格式化，等价 `prettier --write .`）；仅检查不修改用 `npm run format:check`（等价 `prettier --check .`）
- **Lint**: In /frontend/ run `npm run lint`（等价 `eslint .`）

### Backend Development(In /backend/)

- **Dev**: Run `/scripts/start-backend.sh`
- **Format**: In /backend/ 激活虚拟环境后运行 `ruff format app/ tests/`（自动格式化）；仅检查不修改用 `ruff format --check app/ tests/`
- **Lint**: In /backend/ 激活虚拟环境后运行 `ruff check app/ tests/`
- **Test**: In /backend/ 激活虚拟环境后运行 `pytest`（带覆盖率报告用 `pytest --cov=app`）

### Project

- **Start Dev**: Run `/scripts/start.sh`

## 外部引用文档

以下引用中存放了项目的文档，请在仅在需要的时候再通过下文中的指导阅读对应的需求，禁止一次性阅读。

- **@agent-docs**: 存放了系统核心的agent服务的项目文档，需要对接agent服务时，需要查看该目录下文档。除非我允许，不然不可查看非文档之外的内容来了解agent服务的业务。
- **@design-docs**: 存放了最关键的项目设计文档以及各种约束文档，代码开发前一定需要按照文档指引阅读对应的内容并记住关键内容。
- **@ui-docs**: 存放了使用 `penpot`设计的UI原型图（并非效果图），界面开发按照文档指引，了解页面的结构和交互，然后根据具体的要求实现该页面内容。该设计仅供基础参考，后续实现以具体要求为主。
- **@requirements**：存放了项目的需求分析，阅读前先阅读 `99-summary.md`获取项目的概览以及文件用途指导
- **@sprints**：存放了项目的迭代计划，一般不需要查看，查看 `@design-docs`中的相关文档即可，仅供需要了解原始迭代计划时才需要查看。

## 边界约束和规范

### 前端约束，遵循前后端分离的策略

前端项目只负责：

- 页面展示
- 处理用户信息录入
- 调用 API 对接后台服务
- 合理展示后台服务返回内容

禁止：

- 在前端实现 Agent 逻辑
- 直接调用 LLM
- 直接读取知识库
- 存储业务规则

### 后台服务约束：

后台项目只负责：

- 为前端提供 HTTP API
- 校验 API 请求
- 协调应用层业务逻辑
- 与独立的 Agent Service 通信
- 向前端返回数据

禁止：

- 自行调用 LLM 接口
- 自行实现 Agent 功能

## 编码行为约束

### 前端编码约束：

- 所有后端请求必须通过在 `src/api/`下写入对应的接口，后续通过引入方式调用
- 组件必须优先使用 `shadcn/ui`组件实现功能，缺少对应的组件时再尝试自己实现
- 样式使用 `Tailwind CSS`编写，禁止手写大量CSS、引入其他UI库
- 全局状态统一使用 `Zustand`，禁止自定义状态管理、禁止引入其他状态框架
- 组件简单状态使用 `React useState`，跨页面时才使用 `Zustand`
- 所有复杂表单使用 `React Hook Form + Zod`，禁止手写表单状态和字段校验功能

### 后台编码约束：

- FastAPI的路由喝HTTP层逻辑需要存放在 `/backend/app/api`下，并且路由应该只负责请求和响应的处理并调用对应的服务，禁止直接在路由层编写业务逻辑。
- `/backend/app/core/`下包含后端级别的配置和跨应用共享的基础设施，不应该实现Agent功能。
- `backend/app/main.py`为应用的入口点，它只负责创建 FastAPI 应用、注册 API 路由、在需要时配置应用级中间件，禁止存放实际的业务逻辑。
- 在实现业务代码前，先编写对应的单元测试，要求测试内容至少包括：正向路径；边界/边缘情况；无效输入。不允许单值断言。
- 实现代码时，不得对特定测试硬编码数值。代码必须具有通用性，并遵循函数签名与业务逻辑。
- 如果测试失败，不得修改、删除或放宽断言。应修复业务逻辑。如果测试用例本身根本错误，在编辑前应向用户说明原因。
- 日志统一通过 `app/core/logging.py`的 `get_logger(__name__)`获取，禁止使用 `print`或自行创建logger
- 关键事件需记录日志：应用启动/关闭、Agent外部调用（请求/响应/耗时/异常）在 `services/`中记录
- 路由层仅记录debug级日志，避免访问日志噪音
- 所有环境变量驱动的配置（端口、URL、开关、密钥等）必须声明在 `app/core/config.py`的 `Settings`中，并通过 `get_settings()`访问
- 仅在配置值随环境变化或属于部署专属时才引用环境变量，禁止在模块中硬编码此类值
- 禁止在应用代码中直接读取 `os.environ`，应添加为 `Settings`字段
- 密钥（API Key、Token等）、环境配置必须来自 `Settings`/`.env`；以 `.env.example`为模板

### 注释规范：

- 所有注释统一使用中文；docstring 采用 Google 风格（Args/Returns/Raises），行注释精简，解释"为什么"而非重复代码
- 后端：仅模块与公共接口需要注释——每个模块必须有模块级 docstring；公开函数/类需 Google 风格 docstring；常量与复杂逻辑加行注释；私有（`_` 开头）函数无需 docstring
- 前端：仅公共方法/函数、导出的组件、全局常量/变量需要注释

### 项目行为约束：

- 项目的通用脚本需要统一在 `/scripts/`中使用，并且也只有项目级脚本可以存放在 `/scripts/`下
- 编码文件存放和功能需要遵循上文的文件夹规则，当现有文件夹不足以满足要求时，先提出来由我确认后才可以执行
- 如果当前项目需要新增新的库或者依赖来合理的完成对应的功能，请提出来由我确认后再执行
- 接口的实现与对接需要参考 `apis`文档中的设计，禁止自行发挥
- 改动代码时需要关注当前注释是否符合改动后的逻辑，若注释与逻辑不符，需在本次改动中同步修改注释
- 编码完成后必须先执行对应的格式化命令，再执行代码检查命令。若代码检查出现报错，必须持续修复直至检查全部通过，任务才算完成（前端：`npm run format` 后 `npm run lint`；后端：`ruff format app/ tests/` 后 `ruff check app/ tests/`）
- 后台服务修改涉及业务逻辑或 API 时，代码检查通过后还需运行 `pytest` 确保测试通过，任务才算完成
