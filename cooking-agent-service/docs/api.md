# API 接口文档

> cooking-agent-service（Agent 服务）对外提供的 HTTP 接口说明。
> 统一协议遵循 `design/agreement/api-conventions.md`，本文档记录当前已实现并对外暴露的接口。
> Agent 内部工作流见 [`graph.md`](./graph.md)。

## 通用约定

### 基础信息

- 服务前缀：`/api`
- 数据格式：JSON
- 鉴权：无（单用户本地应用，不要求鉴权）
- 字段命名：统一 `snake_case`

### 统一返回信封

业务接口**成功**时返回 JSON 信封结构：

```json
{
  "code": 200,
  "data": {},
  "message": "ok"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | int | 状态码，与 HTTP 状态码一致 |
| `data` | any | 实际返回数据（可为对象 / 数组 / 标量 / null） |
| `message` | string | 状态解释；成功为 `ok` |

### 状态码约定

| code | 语义 | 典型场景 |
|---|---|---|
| 200 | 成功 | 正常返回；无结果（候选为空）视为正常业务结果，`data` 为空数组 |
| 422 | 请求体语义 / 业务校验失败 | 参数缺失、类型错误、枚举非法（FastAPI/Pydantic 默认） |
| 500 | 服务器内部错误 | 未捕获异常（FastAPI 默认兜底） |

> **错误响应说明**：成功响应为统一信封；`422` 由 FastAPI/Pydantic 在校验阶段直接返回，
> 结构为 `{"detail": [...]}`，`500` 为 FastAPI 兜底结构，二者**均不套用业务信封**。
> 调用方（`cooking-web-service`）应基于 **HTTP 状态码** 判断成功与否，仅在 `200` 时解析
> 信封中的 `data`。

## 接口列表

| 方法 | 路径 | 说明 | 信封 |
|---|---|---|---|
| GET | `/api/health` | 健康检查 | 否（运维专用） |
| POST | `/api/recipes` | 触发 Agent 获取菜谱 id 数组 | 是 |

---

## 1. 健康检查

- **方法 / 路径**：`GET /api/health`
- **说明**：服务存活探测，运维专用例外，**不套业务信封**。
- **请求参数**：无
- **响应示例**：

```json
{
  "status": "ok"
}
```

---

## 2. 获取菜谱

- **方法 / 路径**：`POST /api/recipes`
- **说明**：接收决策上下文（数量、偏好/禁忌要素、去重菜谱），触发 Agent 工作流（`agent.services.recipes.invoke_get_recipes`），返回菜谱 id 数组。
- **响应格式**：统一信封，`data` 为 `list[int]`。

### 请求体

| 字段 | 类型 | 必填 | 约束 | 说明 |
|---|---|---|---|---|
| `count` | int | 是 | `>= 1` | 需要获取的菜谱数量 |
| `elements` | array | 否 | 默认 `[]` | 富化后的偏好/禁忌要素数组 |
| `dedup` | array | 否 | 默认 `[]` | 已展示菜谱翻译成的完整去重列表 |

#### `elements[]`（决策要素）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | int | 是 | 要素 id |
| `type` | string | 是 | 要素类型：`ingredient` / `technique` / `time` / `taste` / `difficulty` |
| `name` | string | 是 | 要素名称（`time` 类型为纯数字分钟字符串） |
| `sort_order` | int | 是 | 要素排序值 |
| `relation_type` | string | 是 | 与决策的关系：`preference`（偏好）/ `taboo`（禁忌），其余取值返回 `422` |

> Agent 内部按 `relation_type` 将其拆分为偏好 / 禁忌两个通道，并对 `taboo` 执行硬过滤。

#### `dedup[]`（去重菜谱）

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `id` | int | 是 | 菜谱 id |
| `name` | string | 是 | 菜谱名 |
| `elements` | array | 否 | 该菜谱关联的全部要素（结构同 `elements[]`，不含 `relation_type`），默认 `[]` |
| `detail` | string \| null | 否 | 做法正文；无详情为 `null` |

> 去重菜谱写入 Agent 的 `select_recipes`，参与重复排除与均衡判断。

请求示例：

```json
{
  "count": 3,
  "elements": [
    { "id": 3, "type": "technique", "name": "炖", "sort_order": 1, "relation_type": "preference" },
    { "id": 21, "type": "ingredient", "name": "香菜", "sort_order": 1, "relation_type": "taboo" }
  ],
  "dedup": [
    {
      "id": 7,
      "name": "去重菜",
      "elements": [{ "id": 3, "type": "technique", "name": "炖", "sort_order": 1 }],
      "detail": "先切再炒"
    }
  ]
}
```

### 响应

| 状态码 | 场景 | `data` | `message` |
|---|---|---|---|
| 200 | 正常返回 | 菜谱 id 数组（`list[int]`） | `ok` |
| 200 | 无合适菜谱（正常业务结果） | `[]` | `ok` |
| 422 | `count` 缺失 / 为 0 / 负数 / 非整数；`elements` / `dedup` 结构非法；`relation_type` 非法 | 无（FastAPI 默认 `detail`） | — |
| 500 | 服务内部异常 | 无（FastAPI 默认兜底） | — |

响应示例：

```json
{
  "code": 200,
  "data": [2, 3, 5],
  "message": "ok"
}
```
