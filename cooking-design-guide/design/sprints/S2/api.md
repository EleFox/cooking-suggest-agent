# api.md — 接口设计（S2）

> S2 · 料理偏好设置页 + 方案缓存 + 决策接口对接
> 范围仅 web + service 端；Agent 端由其他团队负责。不参考 S1 完成情况（S1 因 Agent 重大需求变更已不能反映现实）。

## 统一返回格式

遵循 `design/agreement/api-conventions.md`，所有接口返回统一信封 `{code, data, message}`；`code` 与 HTTP 状态码一致；错误时 `data=null`。

本轮沿用 `id 参数传输` 约定（路径不拼接资源 id）。

## 要素查询接口（新增）

- **用途**：前端获取设置页勾选选项（手段 / 时间档位），完成 `id ↔ name` 绑定
- **接口**：`GET /api/elements`
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `type` | string | 是 | 要素类型：`technique` / `time`（本轮设置页仅用这两类） |

- **成功响应**（小字典，**不分页**，`data` 直接为数组）：

```json
{
  "code": 200,
  "data": [
    { "id": 1, "type": "technique", "name": "煎", "sort_order": 1 },
    { "id": 8, "type": "time", "name": "30", "sort_order": 2 }
  ],
  "message": "ok"
}
```

| 字段 | 说明 |
|---|---|
| `id` | `t_element.id` |
| `type` | `t_element.type` |
| `name` | `t_element.name`（`time` 类型为纯数字分钟档位，如 `"15"`/`"30"`/`"60"`） |
| `sort_order` | `t_element.sort_order` 展示排序 |

- 结果按 `sort_order` 升序返回。
- `type` 缺失或非法 → `422`。

## 决策接口（契约更新）

- **用途**：首次生成 / 再来一道（沿用 S1 复用同一接口的语义）
- **接口**：`POST /api/decisions`
- **请求体**：

```json
{
  "count": 1,
  "dedup_ids": [],
  "elements": [
    { "type": "technique", "element_id": 3, "sentiment": 1 },
    { "type": "time", "element_id": 5, "sentiment": 1 }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `count` | 本次生成数量（本轮固定 1） |
| `dedup_ids` | 已展示菜谱 id 数组，首次为 `[]` |
| `elements` | 要素偏好数组，每项 `{type, element_id, sentiment}` |
| `elements[].type` | 要素类型（`technique` / `time` 等，与要素表一致） |
| `elements[].element_id` | **本轮新增必填**：指向 `t_element.id`，接口按 id 解析要素（替代 S1"按 name 解析"） |
| `elements[].sentiment` | 偏好：`1` 喜欢 / `0` 厌恶（设置页仅正向勾选，固定 `1`） |

> **契约变更说明**：S1 契约 `elements` 仅 `{type, sentiment}`，接口无法得知具体偏好要素，本轮补上 `element_id`。前端/方案缓存直接传 id，与 `t_scheme_element` 存储一致。

- **偏好解析规则（服务端）**：
  - `time` 类型偏好：**数值区间匹配**——菜谱关联的 `time` 要素值（分钟数）`<=` 偏好档位值即满足（如菜谱 45 分钟满足偏好 60、不满足 30）
  - 其余类型（`technique` 等）：**相等匹配**——菜谱关联要素与偏好 `element_id` 相同即满足
- **校验**：`element_id` 不存在 → `422`；`type` 与要素实际类型不一致 → `422`；`elements=[]` 合法（0 偏好，等价无偏好生成）
- **成功响应**：沿用 S1 卡片结构（`data.data` 卡片数组）。卡片字段 `time_estimate` 来源改为菜谱关联的 `time` 要素值（分钟数，展示"约 X 分钟"）：

| 卡片字段 | 来源 |
|---|---|
| `id` / `name` | `t_recipe.id` / `t_recipe.name` |
| `ingredients` | `t_recipe_element` → `t_element`（type=ingredient）名称数组 |
| `time_estimate` | 菜谱关联 `time` 要素（type=time）的分钟数 |
| `difficulty` | `t_recipe_element` → `t_element`（type=difficulty）名称 |

- **无结果 / 错误响应**：沿用 S1（`data.data=[]` + `message` 提示；服务异常 `code=500`）。Agent 未就绪时由接口服务返回种子菜谱模拟结果（方案 B 不变）。

## 方案接口（新增）

### 创建方案

- **接口**：`POST /api/preference-schemes`
- **请求体**：

```json
{ "name": "家常快手", "element_ids": [3, 5] }
```

| 字段 | 说明 |
|---|---|
| `name` | 方案名，必填，非空字符串；**允许重名** |
| `element_ids` | 偏好要素 id 数组（`technique` 勾选 + 一个 `time` 档位）；可为空数组（存空方案） |

- **校验**：`name` 为空 → `422`；`element_ids` 含不存在的要素 id → `422`
- **成功响应**：`data` 返回创建后的方案对象（含 `id`、`created_at`）：

```json
{
  "code": 200,
  "data": { "id": 10, "name": "家常快手", "is_default": 0, "element_ids": [3, 5], "created_at": "2026-09-06T10:00:00+08:00", "updated_at": "2026-09-06T10:00:00+08:00" },
  "message": "ok"
}
```

### 查询方案列表

- **接口**：`GET /api/preference-schemes`
- **用途**：方案管理页列表 + 设置页调出/编辑时按 `id` 定位方案
- **响应**：遵循 api-conventions 分页信封，每项含完整 `element_ids`（无需单独详情接口）：

```json
{
  "code": 200,
  "data": {
    "list": [
      { "id": 10, "name": "家常快手", "is_default": 0, "element_ids": [3, 5], "created_at": "2026-09-06T10:00:00+08:00", "updated_at": "2026-09-06T10:00:00+08:00" }
    ],
    "has_next": false,
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "message": "ok"
}
```

- 方案量少，前端按全量取（默认 `page_size=20`，上限 100）。

### 更新方案

- **接口**：`PUT /api/preference-schemes`
- **请求体**：

```json
{ "id": 10, "name": "家常快手", "element_ids": [3, 6], "is_default": 1 }
```

| 字段 | 说明 |
|---|---|
| `id` | 必填，目标方案 id |
| `name` | 方案名，非空 |
| `element_ids` | 更新后的勾选要素 id 数组 |
| `is_default` | 默认标记：`1` 设为默认 / `0` 取消默认 |

- **默认方案唯一性（服务端保证）**：当 `is_default=1` 时，同一事务内先将其余方案 `is_default` 置 `0`，再标记目标方案为默认；`is_default=0` 仅取消本方案默认，不影响其他方案
- **校验**：`id` 不存在 → `404`；`name` 为空 → `422`；`element_ids` 含不存在要素 → `422`
- **成功响应**：`data` 返回更新后的方案对象

### 删除方案

- **接口**：`DELETE /api/preference-schemes`
- **请求体**：

```json
{ "id": 10 }
```

- 单资源删除本轮用 `id`（批量 `ids` 仅约定预留，不实施）
- **校验**：`id` 不存在 → `404`
- **成功响应**：`code=200`、`data=null`
- **删除默认方案**：直接删除，系统不再有默认方案（不转移给其他方案）；同时删除 `t_scheme_element` 关联行（事务内）

## 与历史设计关系

| 功能 | 历史 | 本轮 |
|---|---|---|
| 决策接口 | S1 `elements={type,sentiment}` | 更新为携带 `element_id`，卡片 `time_estimate` 来源改为 time 要素 |
| 方案缓存 | 项目级表结构（`t_preference_scheme` / `t_scheme_element`） | 落地 CRUD 接口，沿用表结构，不新增列 |
| 要素字典 | 项目级 `t_element` | 新增 `GET /api/elements` 查询接口 |