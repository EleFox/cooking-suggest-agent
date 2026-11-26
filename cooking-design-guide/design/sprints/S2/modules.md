# modules.md — 模块设计（S2）

> S2 · 料理偏好设置页 + 方案缓存 + 决策接口对接

## 前端模块（React + Vite）

### 页面路由

| 路由 | 页面 | 说明 |
|---|---|---|
| `/preferences` | 料理偏好设置页 | 本轮新建；先进设置再进结果 |
| `/schemes` | 方案管理页 | 本轮新建 |
| `/results` | 菜谱结果页 | S1 已有；本轮改造为读取偏好参数发起决策 |

### 设置页（`/preferences`）

- **职责**：加载要素选项、维护勾选状态、保存方案（新建/编辑）、进入结果页
- **选项加载**：挂载时调用 `GET /api/elements?type=technique` 与 `GET /api/elements?type=time`，渲染手段 chips 与时间档位 chips（按 `sort_order` 排序）；选项含 `id`/`name`，勾选状态以 `element_id` 集合维护
- **勾选状态**：仅前端内存态，不持久化；每次进入默认**空勾选**，不自动应用默认方案
- **模式**：
  - **新建模式**：初始进入；「保存」→ 弹出方案名输入框 → `POST /api/preference-schemes`
  - **编辑模式**：从方案页「编辑」跳转（query 携带 `edit_scheme_id`）；挂载时从方案列表数据定位该方案，填充勾选 + 方案名预填；「保存」→ `PUT /api/preference-schemes`
- **调出模式**：从方案页「调出」跳转（query 携带 `scheme_id`）；挂载时填充该方案勾选（与编辑模式区别：保存为新建，不改原方案）
- **进入结果页**：「生成」→ 以 URL query 携带当前勾选 `element_ids`（如 `/results?element_ids=3,5`；0 勾选则省略）跳转
- **方案入口**：页面顶部方案入口（`scheme-entry`）→ 跳转 `/schemes`
- **0 成员**：页面不渲染成员区，无成员相关交互

### 方案管理页（`/schemes`）

- **职责**：方案列表展示与管理（默认开关 / 调出 / 编辑 / 删除）
- **数据**：挂载时调用 `GET /api/preference-schemes` 全量获取
- **交互**：
  - **默认开关**：切换 → `PUT /api/preference-schemes`（`is_default` 置 1/0；置 1 时服务端互斥）
  - **调出**：跳转 `/preferences?scheme_id={id}`（填充勾选，不直接生成）
  - **编辑**：跳转 `/preferences?edit_scheme_id={id}`（编辑模式）
  - **删除**：确认后 → `DELETE /api/preference-schemes` → 刷新列表
- **方案卡片摘要**：展示方案名 + 勾选要素名摘要（由 element_ids 反查要素选项，前端本地映射）
- **空列表**：展示空态提示（引导回设置页勾选保存）

### 结果页改造（`/results`）

- **读取偏好**：挂载时解析 query `element_ids` → 组装 `elements`（`{type, element_id, sentiment:1}`，type 从要素选项映射）；0 勾选时 `elements=[]`
- **首次生成**：携带组装后的 `elements` 调 `POST /api/decisions`（替换 S1 硬编码常量）
- **再来一道**：沿用内存中的 `elements` + 追加 `dedup_ids` 再次请求
- **状态处理**：沿用 S1（加载中 / 成功 / 无结果 / 错误重试）

### 要素选项共享

- 设置页与方案页均需要素 `id ↔ name` 映射；可由共享模块缓存一次 `GET /api/elements`（technique + time）结果，避免重复请求

## 接口服务模块（FastAPI）

### 要素查询接口

- **职责**：`GET /api/elements` 按 `type` 查询 `t_element`，按 `sort_order` 排序返回字典列表
- 只读，天然幂等

### 方案 CRUD

- **职责**：`t_preference_scheme` / `t_scheme_element` 的增删改查
  - 创建：写入方案行 + 批量写 `t_scheme_element`（事务）
  - 列表：方案行 + 各方案 element_ids（按 scheme_id 聚合）
  - 更新：更新名称/勾选项（先删后插 `t_scheme_element` 或增量同步，事务）；默认标记互斥（同一事务）
  - 删除：删方案行 + 级联删 `t_scheme_element`（事务）
- 勾选项一致性：`element_ids` 非空校验 + 要素存在性校验（`422`）

### 决策接口（契约更新）

- **职责**：接收 `elements`（含 `element_id`）→ 按 id 解析偏好要素 → 时间区间匹配 + 其余相等匹配 → 过滤菜谱 → 返回卡片（沿用 S1 组装逻辑，`time_estimate` 来源改为菜谱 `time` 要素）
- 要素解析：偏好 `element_id` 与菜谱 `t_recipe_element.element_id` 比对；`time` 类型取要素 `name` 数值做 `<=` 区间匹配
- Agent 未就绪：返回种子菜谱模拟结果（方案 B 不变）

## 数据模型变更（本轮）

- **项目级已更新**（见 `design/project/persistence.md`）：`t_recipe` 删除 `time_estimate`；时间改为 `t_element`（type=time，name 存纯数字分钟数）经 `t_recipe_element` 关联；方案时间偏好 = time 档位要素存 `t_scheme_element`
- 本轮沿用表结构：`t_preference_scheme` / `t_scheme_element` 无结构变更，不新增列

## 种子数据（本轮引入）

- `t_element` 新增 `technique` 要素：煎 / 炒 / 凉拌 / 油炸 / 蒸 / 炖 / 煮 / 烤（按 UI 8 个，含 `sort_order`）
- `t_element` 新增 `time` 档位要素：`"15"` / `"30"` / `"60"`
- 种子菜谱池：为支撑设置页选项与决策返回，种子菜谱需关联 `time` 要素（具体分钟数）与 `technique` 要素

## 与项目级设计关系

| 项目级设计 | 本轮关系 |
|---|---|
| `service-overview.md` 料理偏好方案 | 落地为方案 CRUD 接口 + 设置页/方案页 |
| `persistence.md` | 时间要素化已同步更新（time 档位 / 区间匹配） |
| `integrations.md` Agent 协议 | 契约保留，本轮仍模拟返回 |
| `api-conventions.md` | 路径约定更新为 id 参数传输 |