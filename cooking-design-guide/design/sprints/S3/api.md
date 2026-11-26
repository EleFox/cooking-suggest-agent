# api.md — 接口设计（S3）

> S3 · 成员管理 + 成员启停 + 成员偏好联调决策 + 菜谱手动扩充/维护
> 范围仅 web + service 端；Agent 端由其他团队负责。沿用 S2 接口风格与约定。

## 统一返回格式

遵循 `design/agreement/api-conventions.md`，所有接口返回统一信封 `{code, data, message}`；`code` 与 HTTP 状态码一致；错误时 `data=null`。

本轮沿用 `id 参数传输` 约定（路径不拼接资源 id）。

## 要素参数统一契约（本轮约定）

成员与菜谱接口中，**所有要素相关参数统一为数组**，与决策接口 `elements` 同构，支撑要素类型自由扩展（新增要素类型不改变接口字段）：

- **创建**：数组项为 `{name, type}`——后端按 `UNIQUE(type, name)` 完全匹配 **resolve-or-create**（存在取 id，不存在新建 `t_element` 行后关联）
- **更新**：数组项为 `{name, type, id, operate}`——**增量语义**，仅携带变更项，未变更的关联不传输：

| 字段 | 说明 |
|---|---|
| `id` | 既有要素的 `t_element.id`（新增项无此字段） |
| `name` | 要素名（`time` 类型为纯数字分钟数字符串，如 `"45"`） |
| `type` | 要素类型（`ingredient` / `technique` / `time` / `allergen` / `taste` / `difficulty`） |
| `operate` | 操作标识：`add` 新增关联 / `remove` 移除关联 / `edit` 修改该项要素 |

**operate 处理规则（服务端）**：

- `add`（无 `id`）：resolve-or-create `(name, type)` → 新建关联；关联已存在则幂等忽略
- `remove`（有 `id`）：删除该要素与资源的关联行；关联不存在则幂等忽略
- `edit`（有 `id`）：将 `id` 对应关联的要素改为 `(name, type)` resolve-or-create 的结果；语义等价 `remove(id)` + `add(name, type)` 的单条表达；新旧解析结果相同则为 no-op
- 同一资源的全部 operate 应用在**单事务**内完成
- 当前 UI 仅产生 `add` / `remove`（chips 仅支持添加与 × 移除）；`edit` 为契约预留，供未来行内编辑或前端 diff 算法使用

> 同义词归并（如"土豆/马铃薯"）不在本轮范围：resolve-or-create 仅做完全匹配，未来由大模型辅助判断。

## 成员接口（新增）

### 查询成员列表

- **用途**：成员管理页列表 + 设置页成员启停区（含要素明细，供前端决策时展开）
- **接口**：`GET /api/members`
- **响应**：成员量少，**不分页**，`data` 直接为数组；每项含完整偏好/禁忌要素（无需单独详情接口）：

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "爸爸",
      "preferences": [
        { "id": 21, "name": "牛肉", "type": "ingredient" },
        { "id": 35, "name": "微辣", "type": "taste" }
      ],
      "taboos": [
        { "id": 42, "name": "香菜", "type": "ingredient" }
      ],
      "created_at": "2026-09-10T10:00:00+08:00",
      "updated_at": "2026-09-10T10:00:00+08:00"
    }
  ],
  "message": "ok"
}
```

| 字段 | 说明 |
|---|---|
| `id` / `name` | `t_member.id` / `t_member.name` |
| `preferences` | 偏好要素数组（`t_member_element` 中 `relation_type=preference`），每项 `{id, name, type}`（`id` = `t_element.id`） |
| `taboos` | 禁忌要素数组（`relation_type=taboo`），结构同上 |
| 空列表 | 0 成员时返回 `data: []` |

> 设计要点：列表直接携带要素 `id`，前端在发起决策时可本地展开为决策接口的 `elements`（`element_id` 取此 `id`），无需额外请求（与 S2 方案列表含完整 `element_ids` 同风格）。

### 创建成员

- **接口**：`POST /api/members`
- **请求体**：

```json
{
  "name": "爸爸",
  "preferences": [
    { "name": "牛肉", "type": "ingredient" },
    { "name": "鸡肉", "type": "ingredient" },
    { "name": "微辣", "type": "taste" }
  ],
  "taboos": [
    { "name": "香菜", "type": "ingredient" },
    { "name": "花生", "type": "ingredient" }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `name` | 成员名，必填，非空字符串；**允许重名** |
| `preferences` | 偏好要素数组，项为 `{name, type}`；可缺省或为空数组 |
| `taboos` | 禁忌要素数组，结构同上 |

- **校验**：`name` 为空 → `422`；要素项 `name` 为空 / `type` 非法 → `422`
- **冲突处理**：同一要素同时出现在偏好与禁忌中 → 允许保存（不校验交叉冲突，决策时由 Agent 判断）
- **成功响应**：`data` 返回创建后的成员对象（结构同列表项）
- **事务**：写 `t_member` + 全部要素 resolve-or-create + 批量写 `t_member_element` 在单事务内

### 更新成员

- **接口**：`PUT /api/members`
- **请求体**（要素为增量 operate 语义，见「要素参数统一契约」）：

```json
{
  "id": 1,
  "name": "爸爸",
  "preferences": [
    { "id": 35, "name": "微辣", "type": "taste", "operate": "remove" },
    { "name": "清淡", "type": "taste", "operate": "add" },
    { "id": 21, "name": "羊肉", "type": "ingredient", "operate": "edit" }
  ],
  "taboos": []
}
```

- **语义**：`name` 全量更新；`preferences` / `taboos` 仅携带变更项（未变更关联不传）；空数组 = 该关系无变更（**不是清空**）
- **校验**：`id` 不存在 → `404`；`name` 为空 → `422`；`operate` 非法 / `remove`、`edit` 缺 `id` → `422`
- **成功响应**：`data` 返回更新后的成员对象

### 删除成员

- **接口**：`DELETE /api/members`
- **请求体**：

```json
{ "id": 1 }
```

- **语义**：删除成员行 + 级联删除 `t_member_element` 关联行（单事务）；不触碰 `t_element`（要素只增不删）
- **校验**：`id` 不存在 → `404`
- **成功响应**：`code=200`、`data=null`

## 菜谱接口（新增）

### 查询菜谱列表

- **用途**：菜谱管理页列表（含搜索）；**同时作为 Agent 反向调用的菜谱查询 API**（见 `integrations.md`，契约前置落地，前后端 + Agent 共用）
- **接口**：`GET /api/recipes`
- **查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `keyword` | string | 否 | 按菜谱名模糊匹配（`t_recipe.name`） |
| `exclude_recipe_ids` | string | 否 | 逗号拼接的菜谱 id，返回结果中排除这些菜谱（防止重复推荐）；不设数量上限，传入的 id 不存在则忽略 |
| `page` / `page_size` | int | 否 | 分页参数，遵循 api-conventions（默认 `page=1` / `page_size=20`，上限 100） |

- **响应**：遵循 api-conventions 分页信封；**要素统一为 `elements` 数组**（替代 S2 的 `ingredients` / `time_estimate` / `difficulty` 摘要字段），由前端/Agent 按 `type` 识别：

```json
{
  "code": 200,
  "data": {
    "list": [
      {
        "id": 1,
        "name": "番茄牛腩煲",
        "elements": [
          { "id": 21, "type": "ingredient", "name": "番茄", "sort_order": 1 },
          { "id": 22, "type": "ingredient", "name": "牛腩", "sort_order": 2 },
          { "id": 58, "type": "technique", "name": "炖", "sort_order": 1 },
          { "id": 103, "type": "time", "name": "45", "sort_order": 3 },
          { "id": 120, "type": "taste", "name": "咸甜", "sort_order": 1 }
        ],
        "has_detail": true
      }
    ],
    "has_next": false,
    "total": 1,
    "page": 1,
    "page_size": 20
  },
  "message": "ok"
}
```

| 字段 | 来源 |
|---|---|
| `id` / `name` | `t_recipe.id` / `t_recipe.name` |
| `elements` | 菜谱关联的**全部**要素，每项 `{id, type, name, sort_order}`（`id` = `t_element.id`，`sort_order` = `t_element.sort_order`）；数组**不排序**，消费方按 `type` 识别、可依 `sort_order` 自行排序 |
| `has_detail` | 是否存在 MD 详情文件（`file_path` 非空），供前端展示/编辑提示 |

> 过滤顺序：先按 `keyword` 模糊匹配，再排除 `exclude_recipe_ids`；分页与 `total` / `has_next` 基于排除后的结果集。作为 Agent 反向调用的菜谱查询 API 时，**禁忌硬过滤由 Agent 端自行处理**，**去重通过 `exclude_recipe_ids` 支持**。

### 批量查询菜谱详情（编辑回显 + Agent 详情 API）

- **用途**：菜谱编辑表单回显 + Agent 筛选后读取候选详情；**同时作为 Agent 反向调用的菜谱详情 API**（见 `integrations.md`）
- **接口**：`GET /api/recipes/detail`
- **查询参数**：`ids`（必填），**逗号拼接**的资源 id，如 `ids=1,2,3`；不设数量上限
- **响应**：**不分页**，`data` 直接为数组（与列表项同构，`has_detail` 换成 `detail`）：

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "番茄牛腩煲",
      "elements": [
        { "id": 21, "type": "ingredient", "name": "番茄", "sort_order": 1 },
        { "id": 103, "type": "time", "name": "45", "sort_order": 3 }
      ],
      "detail": "牛腩焯水……"
    }
  ],
  "message": "ok"
}
```

| 字段 | 说明 |
|---|---|
| `elements` | 同列表接口，每项 `{id, type, name, sort_order}`；前端按 `type` 推导表单字段（`ingredient`→食材 chips；`technique`→手段勾选；`time`→分钟数（解析 name 数值）；`difficulty`→难度单选） |
| `detail` | 做法正文（读自 MD 文件；无详情则为 `null`） |

- **语义与边界**：
  - 菜谱不存在 → **忽略**，仅返回存在的；全部不存在 → `data: []`
  - 菜谱存在但无详情（`file_path` 为空或文件缺失）→ 照常返回，`detail: null`
  - 原"查询单个菜谱"接口（`GET /api/recipes/detail?id=`）**并入本接口**；编辑表单回显取数组首项
  - `ids` 空串 / 含非整数 → `422`

### 创建菜谱

- **接口**：`POST /api/recipes`
- **请求体**：

```json
{
  "name": "番茄牛腩煲",
  "elements": [
    { "name": "牛腩", "type": "ingredient" },
    { "name": "番茄", "type": "ingredient" },
    { "name": "土豆", "type": "ingredient" },
    { "name": "洋葱", "type": "ingredient" },
    { "name": "炖", "type": "technique" },
    { "name": "45", "type": "time" },
    { "name": "一般", "type": "difficulty" }
  ],
  "detail": "牛腩焯水后……"
}
```

| 字段 | 说明 |
|---|---|
| `name` | 菜名，必填，非空 |
| `elements` | 要素数组，项为 `{name, type}`（见「要素参数统一契约」）；全部 resolve-or-create（`technique` / `difficulty` 种子已存在则复用；`time` 按分钟数 name 匹配） |
| `detail` | 做法文本（可空）；**非空时生成 MD 详情文件**（front-matter 由表单字段生成 + 正文 = detail），`file_path` 指向文件；为空则 `file_path=null` |

- **校验**：`name` 为空 → `422`；要素项 `name` 为空 / `type` 非法 → `422`；`time` 类型要素 `name` 非正整数 → `422`；**`time` 类型要素至多 1 个、`difficulty` 类型要素至多 1 个**（单值约束，违反 → `422`）
- **成功响应**：`data` 返回创建后的菜谱摘要（同列表项）
- **事务**：写 `t_recipe` + 要素 resolve-or-create + `t_recipe_element` + 写 MD 文件在一个逻辑单元内；文件写入失败回滚表数据（保持一致性）

### 更新菜谱

- **接口**：`PUT /api/recipes`
- **请求体**：`id` 必填 + `name` / `detail` 全量 + `elements` 增量 operate（同成员更新语义；空数组 = 无变更）

```json
{
  "id": 1,
  "name": "番茄牛腩煲",
  "elements": [
    { "id": 21, "name": "牛腩", "type": "ingredient", "operate": "remove" },
    { "name": "牛肉", "type": "ingredient", "operate": "add" }
  ],
  "detail": "牛腩焯水后……"
}
```

- **语义**：`name` / `detail` 全量更新；`elements` 增量应用 operate；`time` / `difficulty` 单值约束在应用后校验（违反 → `422` 整体回滚）
- **MD 文件联动**：`detail` 非空则写/更新 MD 文件；`detail` 为空且原存在文件则删除文件并置 `file_path=null`
- **校验**：`id` 不存在 → `404`；其余同创建
- **成功响应**：`data` 返回更新后的菜谱摘要

### 删除菜谱

- **接口**：`DELETE /api/recipes`
- **请求体**：

```json
{ "id": 1 }
```

- **语义**：**物理删除**——删 `t_recipe` 行 + 级联删 `t_recipe_element` + 删除对应 MD 文件（若存在）；不可恢复，前端需确认交互
- **范围**：全池菜谱均可删除（含种子菜谱，不做来源区分）
- **校验**：`id` 不存在 → `404`
- **成功响应**：`code=200`、`data=null`

## 决策接口（契约更新）

- **接口**：`POST /api/decisions`（S1 定义 / S2 更新，本轮更新请求字段与响应结构）
- **请求体**：

```json
{
  "count": 1,
  "dedup_ids": [3],
  "elements": [
    { "type": "technique", "element_id": 3, "relation_type": "preference" },
    { "type": "time", "element_id": 5, "relation_type": "preference" },
    { "type": "ingredient", "element_id": 21, "relation_type": "taboo" }
  ]
}
```

| 字段 | 说明 |
|---|---|
| `count` | 本次生成数量（默认 1，步进器值） |
| `dedup_ids` | 已展示菜谱 id 数组，首次为 `[]` |
| `elements` | 要素偏好数组，每项 `{type, element_id, relation_type}`；前端仍只传 id，完整要素信息由服务端 enrich |
| `relation_type` | `preference` 偏好 / `taboo` 禁忌（**替代 S2 `sentiment:1/0`**，取值与 `t_member_element.relation_type` 一致） |

### ① 成员要素展开（前端组装）

- 前端在发起决策时，将**启用成员**的偏好/禁忌要素展开合并进 `elements` 数组：
  - 设置页勾选 → `relation_type=preference`
  - 成员偏好 → `relation_type=preference`
  - 成员禁忌 → `relation_type=taboo`（语义 = 硬排除）
- **合并规则**：
  1. 成员范围内：偏好并集、禁忌并集，各自按 `element_id` 去重
  2. 设置页勾选（料理偏好）与成员要素冲突（同 `element_id`）时：**优先采用设置页勾选项**（成员项丢弃）
  3. 同一要素同时出现在偏好并集与禁忌并集：**不做处理，原样传入**，由 Agent 判断
- 停用成员不展开、不传入；0 成员时 `elements` 仅含设置页勾选

### ② 生成数量（count）

- 设置页「生成数量」步进器启用（默认 1），随跳转携带至结果页，作为 `count` 传入决策接口
- 替代 S2 "本轮固定 1" 的约束；Agent 未就绪时模拟返回同样按 `count` 生成
- `dedup_ids` 语义不变（"再来一道" = 已展示全部 id）

### ③ 服务端预处理（转发 Agent 前）

服务端在透传 Agent 前对请求做富化：

- `count` 原样保留
- `elements` → 按 `element_id` 解析补全要素信息：`{id, type, name, sort_order, relation_type}`（`id` = `element_id`）
- `dedup_ids` → **复用批量详情接口的服务逻辑**（函数直接调用）翻译为完整菜谱数据 `{id, name, elements, detail}`（**含做法正文**）；菜谱不存在则忽略

- **校验**：`element_id` 不存在 → `422`；`type` 与要素实际类型不符 → `422`；`relation_type` 非 `preference`/`taboo` → `422`；`elements=[]` 合法（等价无偏好生成）

- **成功响应**：`data` 直接为**卡片数组**（无分页），每项与菜谱列表项同构（旧 `data.data` 结构废弃）：

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "name": "番茄牛腩煲",
      "elements": [
        { "id": 21, "type": "ingredient", "name": "番茄", "sort_order": 1 },
        { "id": 103, "type": "time", "name": "45", "sort_order": 3 }
      ],
      "has_detail": true
    }
  ],
  "message": "ok"
}
```

- 无结果 / 错误响应沿用 api-conventions（`data: []` + `message` 提示；服务异常 `code=500`）

### 模拟返回（方案 B）说明

- Agent 未就绪时，service 模拟返回**仅按 S2 既有偏好匹配逻辑**处理（时间区间 + 手段相等），响应结构同上述卡片数组
- **不对 `relation_type=taboo` 的禁忌要素做硬过滤**（硬过滤由 Agent 负责）；T3 单侧自测仅验证参数组装正确性
- 与 `persistence.md`「决策硬过滤 100% 排除禁忌（数据层保证）」的关系：该保证在 Agent 就绪的正式链路由 Agent 端达成，模拟链路不承担

## 与历史设计关系

| 功能 | 历史 | 本轮 |
|---|---|---|
| 成员管理 | 项目级表结构（`t_member` / `t_member_element`） | 落地成员 CRUD 接口；要素参数统一为 `{name,type}` / `{name,type,id,operate}` 数组契约，沿用表结构，不新增列 |
| 决策接口 | S2：`elements` 含 `element_id` + `sentiment:1/0`，count 固定 1，响应 `data.data` 卡片 | 请求 `sentiment`→`relation_type`（`preference`/`taboo`）；服务端 enrich elements + 将 `dedup_ids` 翻译为完整菜谱；响应改 `data` 卡片数组（elements 数组 + `has_detail`） |
| 菜谱池 | 项目级：种子导入，菜谱只读 | 落地菜谱 CRUD（要素统一数组契约）；`GET /api/recipes` 列表改 elements 数组；新增批量详情 `GET /api/recipes/detail?ids=`（同时作为 Agent 详情 API）；物理删除 |
| 要素字典 | S2：`GET /api/elements`（technique/time） | 本轮表单要素统一走 resolve-or-create（传 name）；`GET /api/elements` 保留供设置页勾选选项使用 |
