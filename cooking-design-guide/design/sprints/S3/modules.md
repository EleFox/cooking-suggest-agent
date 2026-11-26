# modules.md — 模块设计（S3）

> S3 · 成员管理 + 成员启停 + 成员偏好联调决策 + 菜谱手动扩充/维护

## 前端模块（React + Vite）

### 页面路由

| 路由 | 页面 | 说明 |
|---|---|---|
| `/members` | 成员管理页 | 本轮新建（T1） |
| `/members/form` | 成员表单页 | 本轮新建；**新建/编辑共用同一页面**，query `id` 可选（无 = 新建模式，有 = 编辑模式） |
| `/recipes` | 菜谱管理页 | 本轮新建（T5；含搜索 + 新增入口） |
| `/recipes/form` | 菜谱表单页 | 本轮新建；**新建/编辑共用同一页面**，query `id` 可选（同上） |
| `/preferences` | 料理偏好设置页 | S2 已有；本轮新增成员启停区 + 生成数量接通 |
| `/results` | 菜谱结果页 | S1 已有；本轮扩展决策参数组装（成员展开 + count）+ 卡片删除入口接通 |
| `/schemes` | 方案管理页 | S2 已有，本轮无改动 |

> **表单页复用约束（重要）**：成员表单与菜谱表单各自**只有一个路由与一个页面组件**，通过 query `id` 区分新建/编辑模式（页面标题随模式切换，如「新增成员」/「编辑成员」）。**禁止拆分为独立的新建页与编辑页**——拆分会导致表单组件无法复用、双份维护；UI 画板（member-form-screen / recipe-form-screen）亦为单一表单，与本约束一致。

### 成员管理页（`/members`）

- **职责**：成员列表展示与管理（新增 / 编辑 / 删除）
- **数据**：挂载调用 `GET /api/members`（不分页，全量）
- **成员卡片**：姓名 + 偏好（食材 / 口味）+ 食材禁忌摘要（chips 展示 name）+ 「编辑」「删除」操作
- **空态**：0 成员展示引导文案 + 「新增成员」（对应 UI `member-management-screen-empty`）
- **底部固定**「新增成员」→ `/members/form`

### 成员表单页（`/members/form`，新建/编辑共用）

- **职责**：成员新增/编辑（**单一页面组件**，query `id` 可选：无 = 新建模式，有 = 编辑模式；编辑模式挂载时从成员列表数据按 `id` 定位回显；标题随模式切换）
- **字段**：
  - 姓名：文本输入，必填（为空禁用保存）
  - 偏好（食材 / 口味）：各自"输入框 + 确认"添加 → chips 列表（带 × 移除）；前端按分区去重
  - 食材禁忌：同上交互
- **保存**：按统一要素契约组装——新增时 `preferences` / `taboos` 为 `{name, type}` 数组 → `POST`；编辑时对回显快照做 diff，生成 `{name, type, id, operate}` 增量数组 → `PUT`（当前 UI 仅产生 add/remove；未变更项不传输）→ 返回列表页
- **编辑时成员已被删除**：按 id 定位失败 → 回退新建模式

### 设置页改造（`/preferences`）

- **成员区**（新增，位于生成数量与方案入口之间）：
  - 挂载时调用 `GET /api/members`；渲染成员行（姓名 + 开关）
  - 开关状态为**前端内存态**，默认全部启用；0 成员时成员区空置
  - 「管理成员」入口 → `/members`
- **生成数量步进器**：接通为内存态（默认 1），进入结果页时携带
- **进入结果页**：「查看菜谱」→ `/results?element_ids=...&member_ids=...&count=...`（member_ids 为启用成员 id；0 勾选/0 启用省略对应参数）
- **方案功能不变**：方案仅缓存手段/时间勾选，不含成员与数量

### 结果页改造（`/results`）

- **参数解析**：query 读取 `element_ids` / `member_ids` / `count`
- **elements 组装**：
  1. 设置页勾选（`element_ids`）→ `{type, element_id, relation_type: "preference"}`
  2. 从内存中的成员列表（`GET /api/members` 缓存）取 `member_ids` 对应成员 → 偏好展开 `relation_type="preference"`、禁忌展开 `relation_type="taboo"`
  3. 合并：成员偏好/禁忌各自并集按 `element_id` 去重；与设置页勾选同 id 冲突时以设置页勾选为准；偏好×禁忌交叉不处理
- **首次生成**：`POST /api/decisions`（`count` 取 query 值，默认 1）；响应 `data` 为卡片数组，卡片由 `elements` 按 type 推导渲染（食材/时间/难度）
- **再来一道**：沿用内存参数 + 追加 `dedup_ids`（前端仅传 id 数组，服务端翻译为完整菜谱）
- **卡片 × 删除**：确认 → `DELETE /api/recipes` → 从当前结果移除该卡片
- **「菜谱管理」入口** → `/recipes`

### 菜谱管理页（`/recipes`）

- **职责**：全池菜谱列表（分页）+ 搜索 + 新增/编辑/删除入口
- **数据**：挂载调用 `GET /api/recipes`（分页）；搜索栏输入 → `keyword` 重新查询
- **卡片**：与结果页一致的卡片样式（图占位 + 名称 + 食材 + 时间 + 难度）+ 右上 × 删除（热区）；卡片字段由 `elements` 按 `type` 推导（ingredient→食材、time→分钟数、difficulty→难度）
- **交互**：整卡点击 → `/recipes/form?id={id}`；× → 确认 → `DELETE` → 刷新；底部「新增菜谱」→ `/recipes/form`

### 菜谱表单页（`/recipes/form`，新建/编辑共用）

- **职责**：菜谱新增/编辑（**单一页面组件**，query `id` 可选区分模式；编辑模式挂载调 `GET /api/recipes/detail?ids={id}` 回显，取数组首项；标题随模式切换）
- **字段**：
  - 名称：文本输入，必填
  - 主要食材：输入 + 确认 → chips（带 ×），前端去重
  - 料理手段：chips 多选（选项来自 `GET /api/elements?type=technique`）
  - 预估时间：步进器（分钟，正整数）
  - 难度：chips 单选（选项来自 `GET /api/elements?type=difficulty`）
  - 做法：多行文本，可空
- **保存**：按统一要素契约组装 `elements` 数组——食材 `{name, type:"ingredient"}`、手段 `{name, type:"technique"}`、时间步进器 `{name: 分钟数字符串, type:"time"}`、难度单选 `{name, type:"difficulty"}`；新增 → `POST`；编辑时对回显快照 diff 生成 operate 增量 → `PUT` → 返回管理页

### 共享模块

- **要素选项缓存**：`GET /api/elements`（technique / time / difficulty）结果共享缓存，供设置页与菜谱表单复用
- **成员列表缓存**：设置页与结果页共享 `GET /api/members` 结果（结果页展开用）

## 接口服务模块（FastAPI）

### 成员 CRUD

- **职责**：`t_member` / `t_member_element` 增删改查
  - 列表：成员行 + 各成员偏好/禁忌要素（按 `member_id` + `relation_type` 聚合，关联 `t_element` 取 id/name/type）
  - 创建：要素 **resolve-or-create**（按 `UNIQUE(type, name)` 完全匹配，存在复用、不存在新建）→ 批量写 `t_member_element`，单事务
  - 更新：`name` 全量更新 + 要素**增量 operate 应用**（add=resolve-or-create 后插关联 / remove=删关联 / edit=改关联要素，幂等处理），单事务
  - 删除：成员行 + 级联关联行，单事务；不删 `t_element`
- 校验：`name` 非空；要素项 `name` 非空、`type` 合法、`operate` 合法

### 菜谱 CRUD

- **职责**：`t_recipe` / `t_recipe_element` 增删改查 + MD 详情文件联动
  - 列表：分页 + `keyword` 模糊匹配 name + `exclude_recipe_ids` 排除已选菜谱（分页基于排除后结果）；每项聚合全部关联要素为 `elements` 数组（`{id, type, name, sort_order}`）+ `has_detail`
  - 批量详情：按 `ids` 查询，返回数组，每项 `elements`（同上）+ `detail`（读 MD 正文；无则 null）；不存在的 id 忽略
  - 创建：`elements` 全部 resolve-or-create（`time` 按分钟数 name 匹配）；`time` / `difficulty` 单值约束校验；写 `t_recipe` + `t_recipe_element`
  - 更新：`name` / `detail` 全量 + `elements` 增量 operate 应用；应用后校验单值约束（违反回滚）
  - **MD 文件联动**：`detail` 非空 → 生成/更新 `recipes/*.md`（front-matter 由表单字段生成 + 正文 = detail），`file_path` 指向文件；`detail` 为空且原文件存在 → 删文件置 null；文件写失败回滚表数据
  - 删除：物理删除（表行 + 级联关联 + MD 文件），容忍文件已缺失
- **同时作为 Agent 反向调用的菜谱查询 API**（`GET /api/recipes`）与**详情 API**（`GET /api/recipes/detail?ids=`，契约见 `integrations.md`）；详情服务逻辑导出为函数供决策模块复用

### 决策接口（契约更新）

- 请求 `elements` 改 `{type, element_id, relation_type}`（`preference`/`taboo`）；服务端转发 Agent 前 enrich 要素完整信息（`{id, type, name, sort_order, relation_type}`）
- `dedup_ids` 复用批量详情服务函数翻译为完整菜谱（`{id, name, elements, detail}`，含正文）；菜谱不存在则忽略
- 响应 `data` 改为卡片数组（同列表项：`elements` + `has_detail`，无分页）
- 模拟返回（方案 B）：仅按 S2 偏好匹配逻辑（时间区间 + 手段相等），**不应用禁忌硬过滤**，响应结构同新格式

## 数据模型变更（本轮）

- **无表结构变更**：沿用项目级 `t_member` / `t_member_element` / `t_recipe` / `t_recipe_element` / `t_element`
- 数据层面变化：
  - `t_member` / `t_member_element` 开始有用户数据（成员 CRUD）
  - `t_element` 经 resolve-or-create 增长（自由文本食材/口味 + 菜谱时间分钟数）
  - `t_recipe` 由"种子只读"变为"全池可增删改"；`recipes/*.md` 由表单生成/更新/删除

## 种子数据（本轮）

- `t_element` 新增 `difficulty` 要素：简单 / 一般 / 困难（含 `sort_order`），供菜谱表单 chips
- 既有种子（technique / time 档位 / 种子菜谱）不变

## 与项目级设计关系

| 项目级设计 | 本轮关系 |
|---|---|
| `service-overview.md` 成员管理 | 落地为成员 CRUD 接口 + 成员管理/表单页 |
| `service-overview.md` 菜谱读取 | 扩展为菜谱 CRUD（全池可管）；读取能力保留 |
| `persistence.md` | 无表结构变更；resolve-or-create 与文件联动为既有生命周期规则的落地 |
| `integrations.md` 菜谱查询 API | `GET /api/recipes` 列表返回 `elements` 数组；详情 API 落地为 `GET /api/recipes/detail?ids=`（批量数组） |
| `integrations.md` 决策上下文 | 成员要素由前端展开进 `elements`；service 转发前 enrich 要素信息并将 `dedup_ids` 翻译为完整菜谱 |
| `api-conventions.md` | 沿用（信封 / 状态码 / 分页 / id 参数传输） |
