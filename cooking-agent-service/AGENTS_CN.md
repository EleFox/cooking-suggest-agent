# cooking-agent-service

## 项目定位

这个项目是一个用于辅助用户进行烹饪决策的轻量化 Agent 服务，是整个大 Agent 系统中的决策核心模块。它由上层业务模块调用，通过 LangGraph 编排的大模型 Agent 流程执行菜谱推荐决策，最终返回决策结果。

本项目不负责前端的页面展示，也不负责业务数据的持久化管理，这些由 `cooking-web-service` 承担。

## 技术栈

### Core：

- python
- 虚拟环境 `.venv`（项目根目录）

### 框架：

- langgraph
- langchain
- fastapi
- pydantic / pydantic-settings（`common/` 配置模块依赖）

## 项目目录说明

```
cooking-agent-service/
├── agent/                      # Agent 决策核心（LangGraph 编排）
│   ├── graph/                  # 图构建模块
│   │   ├── graph.py            # LangGraph 图构建与编译
│   │   ├── nodes.py            # 图节点逻辑
│   │   ├── state.py            # 图状态定义
│   │   └── llm.py              # LLM 统一引入与配置
│   ├── prompts/                # Prompt 模板模块
│   │   ├── system-*.md         # 系统 Prompt 模板
│   │   ├── human-*.md          # 用户 Prompt 模板
│   │   ├── ai-*.md             # AI Prompt 模板
│   │   └── utils.py            # Prompt 通用方法
│   ├── services/               # Agent 服务模块
│   │   └── ...                 # 存放具体的服务模块
│   └── tools/                  # Agent Tool 模块
│
├── app/                        # 对外 API 服务层
│   ├── api/
│   │   └── routes/             # API 路由（仅请求/响应处理）
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── services/               # 服务层
│   ├── core/                   # 本服务核心模块
│   ├── main.py                 # 应用入口（创建应用、注册路由、中间件）
│   └── __init__.py
│
├── common/                     # 跨服务共享的通用功能模块
│   ├── config.py               # 全部配置
│   └── logging.py              # 日志基础设施
│
├── tests/                      # 单元测试
├── scripts/                    # 项目级启动/辅助脚本
├── main.py                     # 项目入口
├── requirements.txt            # Python 依赖
├── .env.example                # 环境变量模板
└── ...
```

## 项目命令

以下命令均在项目根目录、激活虚拟环境（`.venv`）后执行：

- **Dev**: 运行 `python -m app.main`（使用 `uvicorn.run` 程序化启动，host/port/reload 从配置读取；后续由 `/scripts/start-agent.sh` 启动）
- **Format**: `ruff format agent/ app/ common/ tests/`（自动格式化）；仅检查不修改用 `ruff format --check agent/ app/ common/ tests/`
- **Lint**: `ruff check agent/ app/ common/ tests/`
- **Test**: `pytest`（带覆盖率报告用 `pytest --cov=app`）

## 外部引用文档

以下引用中存放了项目的文档，请在仅在需要的时候再通过下文中的指导阅读对应的需求，禁止一次性阅读。

- **@design-agreement**: 存放了最关键的各种约束文档，代码开发前一定需要按照文档指引阅读对应的内容并记住关键内容。
- **@web-service**: 存放了业务模块的前端代码和后台接口服务代码。本项目需要反向调用其菜谱查询/详情 API，对接时参考 `design/agreement/api-conventions.md` 的分页约定与接口契约，只读参考，不可修改其代码。
- **@requirements**：存放了项目的需求分析，阅读前先阅读 `99-summary.md`获取项目的概览以及文件用途指导
- **@sprints**：存放了项目的迭代计划，一般不需要查看，查看 `@design-docs`中的相关文档即可，仅供需要了解原始迭代计划时才需要查看。

## 边界约束和规范

本项目是整个系统的决策核心，只负责：

- 通过 HTTP API 接收业务模块透传的决策上下文
- 执行 Agent 决策流程：知识比对、推荐方向、候选筛选确认、最终排序
- 反向从 `cooking-web-service` 获取需要的菜谱和决策信息
- 返回决策结果

禁止：

- 实现任何前端展示逻辑
- 直接管理业务数据（成员、偏好/禁忌、菜谱主数据、权重、使用记录等），这些由 `cooking-web-service` 维护
- 修改 `cooking-agent-servie`之外的代码（除非我允许）
- 为业务模块实现接口契约之外的自定义决策行为

## 编码行为约束

### Agent 核心编码约束（`agent/`）：

- `agent/` 只承载 Agent 决策核心逻辑，不包含 HTTP 路由层逻辑
- 图定义集中在 `agent/graph/graph.py`，节点逻辑集中在 `agent/graph/nodes.py`，状态定义在 `agent/graph/state.py`，禁止在节点函数中直接构建图或修改状态定义
- LLM 统一从 `agent/graph/llm.py` 引入，禁止在业务代码中直接创建 LLM 实例或硬编码模型地址
- Prompt 统一存放在 `agent/prompts/` 下，通过 `agent/prompts/utils.py` 加载，禁止在代码中硬编码大段提示词
- `agent/services/` 负责 Agent 模块的实际执行逻辑，一般是具体 Agent 执行的入口

### API 服务层编码约束（`app/`）：

- FastAPI 的路由和 HTTP 层逻辑需要存放在 `/app/api` 下，路由只负责请求和响应的处理并调用对应的服务，禁止直接在路由层编写业务逻辑
- `/app/core/` 仅作为占位模块，配置统一存放在 `common/config.py`，共享基础设施统一存放在 `common/`，不应在此实现 Agent 功能
- `/app/main.py` 为应用的入口点，它只负责创建 FastAPI 应用、注册 API 路由、在需要时配置应用级中间件，禁止存放实际的业务逻辑
- 反向获取 web-service 信息的 HTTP 客户端逻辑存放在 `/app/services/` 下，遵循 `@web-service` 提供的接口契约与 `design/agreement/api-conventions.md` 的分页约定，禁止自行发挥

### 测试约束：

- 在实现业务代码前，先编写对应的单元测试，要求测试内容至少包括：正向路径；边界/边缘情况；无效输入。不允许单值断言
- 实现代码时，不得对特定测试硬编码数值。代码必须具有通用性，并遵循函数签名与业务逻辑
- 如果测试失败，不得修改、删除或放宽断言。应修复业务逻辑。如果测试用例本身根本错误，在编辑前应向用户说明原因

### 注释规范：

- 所有注释统一使用中文；docstring 采用 Google 风格（Args/Returns/Raises），行注释精简，解释"为什么"而非重复代码
- 仅模块与公共接口需要注释——每个模块必须有模块级 docstring；公开函数/类需 Google 风格 docstring；常量与复杂逻辑加行注释；私有（`_` 开头）函数无需 docstring

### 日志约束：

- 日志统一通过 `common/logging.py` 的 `get_logger(__name__)` 获取，禁止使用 `print` 或自行创建 logger
- 关键事件需记录日志：应用启动/关闭、Agent 决策调用（请求/响应/耗时/异常）在 `agent/services/` 中记录、反向调用 web-service 接口的请求与异常在 `app/services/` 中记录
- 路由层仅记录 debug 级日志，避免访问日志噪音

### 环境变量约束：

- 本项目的所有配置统一存放在 `common/config.py` 的 `Settings` 中，并通过 `get_settings()` 访问
- 仅在配置值随环境变化或属于部署专属时才引用环境变量，禁止在模块中硬编码此类值
- 禁止在应用代码中直接读取 `os.environ`，应添加为 `Settings` 字段
- 密钥（API Key、Token等）、环境配置必须来自 `Settings`/`.env`；以 `.env.example`为模板

### 项目行为约束：

- 项目的通用脚本需要统一在 `/scripts/` 中使用，并且也只有项目级脚本可以存放在 `/scripts/` 下
- 编码文件存放和功能需要遵循上文的文件夹规则，当现有文件夹不足以满足要求时，先提出来由我确认后才可以执行
- 如果当前项目需要新增新的库或者依赖来合理的完成对应的功能，请提出来由我确认后再执行
- 接口的实现与对接需要参考 `@web-service` 中的接口契约设计，禁止自行发挥
- 改动代码时需要关注当前注释是否符合改动后的逻辑，若注释与逻辑不符，需在本次改动中同步修改注释
- 编码完成后必须先执行对应的格式化命令，再执行代码检查命令。若代码检查出现报错，必须持续修复直至检查全部通过，任务才算完成（`ruff format agent/ app/ common/ tests/` 后 `ruff check agent/ app/ common/ tests/`）
- 改动涉及业务逻辑或 API 时，代码检查通过后还需运行 `pytest` 确保测试通过，任务才算完成
