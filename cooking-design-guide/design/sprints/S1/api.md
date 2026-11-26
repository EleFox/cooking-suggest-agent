# api.md — 接口设计（S1）

> S1 · 菜谱卡片列表页 + "再来一道"
> 范围：前端（React+Vite）+ 后端接口服务（FastAPI）均已搭建完成骨架，本迭代只开发**结果卡片列表页**与**决策接口（模拟返回）**。

## 统一返回格式

遵循 `design/agreement/api-conventions.md`，所有接口返回：

```json
{
  "code": 200,
  "data": {},
  "message": "ok"
}
```

- `code`：状态码，本轮仅约定成功 `200`；其余枚举后续确定
- `data`：接口实际返回数据
- `message`：状态解释

## 决策接口（生成 / 再来一道）

- **用途**：首次生成 1 道菜 + "再来一道"追加生成（复用同一接口）
- **接口名**：`POST /api/decisions`
- **方法**：`POST`
- **请求体**：

```json
{
  "count": 1,
  "dedup_ids": [],
  "elements": [
    { "type": "technique", "sentiment": 1 },
    { "type": "time", "sentiment": 1 }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `count` | 一级参数，本次生成数量（本轮固定 1） |
| `dedup_ids` | 一级参数，去重列表：已展示菜谱 id 数组，首次为 `[]`，"再来一道"为已展示全部 id |
| `elements` | 要素偏好数组，每项 `{ type, sentiment }` |
| `elements[].type` | 要素表类型（`ingredient` / `technique` / `time` / `allergen` / `tag` / `difficulty`） |
| `elements[].sentiment` | 偏好：`1` 喜欢 / `0` 厌恶 |

> 具体要素名不随请求传入，由接口服务按要素表解析（名称存于 `t_element.name`）。

> **非分页列表**：决策接口按 `count` 返回固定数量卡片，属"生成 N 道"语义，**不适用** `api-conventions.md` 的分页约定（`page`/`has_next`/`total`）。分页约定适用于未来菜谱查询 API（见 `integrations.md`）。

- **成功响应**（`data` 内层结构）：

```json
{
  "code": 200,
  "data": {
    "data": [
      {
        "id": 1,
        "name": "番茄牛腩煲",
        "ingredients": ["牛腩", "番茄", "土豆", "洋葱"],
        "time_estimate": 45,
        "difficulty": "一般"
      }
    ],
    "message": ""
  },
  "message": "ok"
}
```

`data.data` 为菜谱卡片数组（长度 = count）：

| 卡片字段 | 来源 |
|---|---|
| `id` | `t_recipe.id` |
| `name` | `t_recipe.name` |
| `ingredients` | `t_recipe_element` → `t_element`（type=ingredient）名称数组 |
| `time_estimate` | `t_recipe.time_estimate`（分钟，前端展示为"约 X 分钟"） |
| `difficulty` | `t_recipe_element` → `t_element`（type=difficulty）名称 |

- **无结果响应**（候选池已耗尽 / 无合适菜谱）：

```json
{
  "code": 200,
  "data": {
    "data": [],
    "message": "没有合适的菜了"
  },
  "message": "ok"
}
```

前端按 `data.data` 为空 + `data.message` 展示提示，不新增卡片。

- **错误响应**（服务异常 / 超时）：

```json
{
  "code": 500,
  "data": null,
  "message": "服务暂时不可用，请稍后重试"
}
```

## 与 Agent 的关系（本轮）

- 本轮 **Agent（黑盒）未就绪**，决策接口由接口服务返回**固定/种子菜谱模拟结果**（方案 B）。
- 透传 Agent 的契约不变（见 `design/project/integrations.md`），Agent 就绪后接入，接口返回结构保持本页定义。
- 菜谱查询 / 详情 API（供 Agent 反向调用）本轮不实施，待 Agent 接入迭代实现。

## 幂等 / 边界

- 决策接口为**只读查询 + 模拟返回**，无持久化副作用，天然幂等。
- `dedup_ids` 由接口服务作为过滤条件，保证返回卡片不与已展示菜谱重复。
- 请求重复提交由前端禁用按钮控制（见 business.md）。