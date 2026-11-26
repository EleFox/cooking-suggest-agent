# persistence.md — 数据持久化设计

> 描述整体数据持久化设计。它描述**当前整体有效的数据设计**。
> 单用户本地应用，无账号体系；结构化数据用 SQLite，菜谱池用 Markdown 文件 + SQLite 派生索引。

## 设计总览

- **存储形态**：SQLite（结构化数据，**主数据**）+ 文件系统（菜谱池 MD 文件，**辅助数据**）
- **菜谱池**：`t_recipe` 为主数据（最重要），MD 文件为辅助详情；`file_path` 字段关联文件，文件可缺失（如用户仅填表数据未填详情）
- **原则**：表符合原子性，不使用数组类型，关联优先；要素统一入 `t_element`，其余表只存 `element_id`
- **边界**：本服务不管理时令 / 健康（nutrition）要素，相关标签不出现在数据模型中；Agent 通过 MD 文档理解并结合自有知识库处理

## 数据模型

核心数据流：成员偏好/禁忌 + 料理偏好方案（决策输入）→ 决策引擎（硬过滤 + 软排序）→ 候选菜谱（MD 文件）→ Agent 排序 → 结果展示 / 使用记录。

### 核心领域对象

- **element（烹饪要素）**：食材、料理手段、料理时间、过敏原、口味标签、烹饪难度，统一字典
- **member（成员）**：家庭成员，偏好/禁忌通过关联表挂接要素
- **preference_scheme（料理偏好方案）**：可复用的一套料理偏好组合（US-04）
- **recipe（菜谱）**：`t_recipe` 主数据 + 可选 MD 文件详情
- **weight_setting（权重设置）**：各决策因素权重（US-06）
- **usage_record（使用记录）**：决策日志（P2）

## 表 / 集合

| 表名 | 说明 | 类型 |
|---|---|---|
| `t_element` | 烹饪要素字典 | SQLite |
| `t_member` | 成员 | SQLite |
| `t_member_element` | 成员-要素关联（偏好/禁忌） | SQLite |
| `t_preference_scheme` | 料理偏好方案 | SQLite |
| `t_scheme_element` | 方案-要素关联 | SQLite |
| `t_recipe` | 菜谱主数据 | SQLite |
| `t_recipe_element` | 菜谱-要素关联 | SQLite |
| `t_weight_setting` | 决策因素权重 | SQLite |
| `t_usage_record` | 使用记录（P2） | SQLite |
| `t_usage_record_recipe` | 记录-菜谱关联（P2） | SQLite |
| `recipes/*.md` | 菜谱详情文件（辅助，可缺失） | 文件系统 |

## 字段

### t_element — 烹饪要素

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | 自增主键 |
| type | TEXT | 要素类型：`ingredient`食材 / `technique`料理手段 / `time`料理时间 / `allergen`过敏原 / `taste`口味 / `difficulty`烹饪难度 |
| name | TEXT | 要素名（如 蒸、清淡、鲈鱼、快手、简单） |
| sort_order | INTEGER | 展示排序 |

> 唯一约束：`UNIQUE(type, name)`。菜谱 front-matter 中的要素名靠此反查 id。
> `time` 类型要素的 `name` 存**纯数字分钟数**（TEXT）：菜谱侧为具体预估分钟（如 `"45"`），偏好侧为档位上限（`"15"` / `"30"` / `"60"`）。
> **时间匹配为数值区间匹配**：菜谱时间要素值 `<=` 偏好档位值（菜谱 45 分钟满足偏好 60、不满足 30）；其余要素为相等匹配。

### t_member — 成员

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | 成员名 |
| created_at | TEXT | |
| updated_at | TEXT | |

> 无 `enabled` 字段：决策前启停某成员在决策界面临时勾选，成员 id 作为接口参数传入后端，不持久化。

### t_member_element — 成员-要素关联（一体两面）

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| member_id | INTEGER FK→t_member | |
| element_id | INTEGER FK→t_element | |
| relation_type | TEXT | `preference`偏好 / `taboo`禁忌 |

> 唯一约束：`UNIQUE(member_id, element_id, relation_type)`。偏好与禁忌共用一张关联表。

### t_preference_scheme — 料理偏好方案

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| name | TEXT | 方案名（如"家常快手"） |
| is_default | INTEGER | 是否默认方案，决策页勾选初始值，默认 0 |
| created_at | TEXT | |
| updated_at | TEXT | |

### t_scheme_element — 方案-要素关联

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| scheme_id | INTEGER FK→t_preference_scheme | |
| element_id | INTEGER FK→t_element | |

> 唯一约束：`UNIQUE(scheme_id, element_id)`。
> 方案时间偏好即 `time` 类型档位要素（`"15"` / `"30"` / `"60"`），与其他偏好同为 `element_id` 存储。

### t_recipe — 菜谱主数据

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | 自增主键（菜谱唯一标识） |
| name | TEXT | 菜名 |
| file_path | TEXT | 关联的 MD 详情文件路径（`recipes/r-0123.md`）；**可空**——用户仅填表数据未填详情时无文件 |
| created_at | TEXT | |
| updated_at | TEXT | |

> 本表是菜谱**主数据**（最重要）。MD 文件仅为辅助详情，可不存、可缺。
> 菜谱的预估时间经 `t_recipe_element` 关联 `time` 类型要素表达（name 存具体分钟数），不再设独立字段。

### t_recipe_element — 菜谱-要素关联

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| recipe_id | INTEGER FK→t_recipe | |
| element_id | INTEGER FK→t_element | |

> 唯一约束：`UNIQUE(recipe_id, element_id)`。
> 要素关联索引可用于按禁忌要素反查菜谱（硬过滤的潜在数据层能力）；当前硬过滤由 Agent 端基于查询结果自行处理，本系统接口未暴露该过滤入参。
> 菜谱时间经此关联 `time` 类型要素（name 存具体分钟数），卡片"约 X 分钟"与时间偏好匹配均据此读取。

### t_weight_setting — 决策因素权重

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| factor | TEXT UNIQUE | 决策因素：`member_preference` / `technique` / `time` / `free_text` |
| value | REAL | 权重值，默认 1.0 |

### t_usage_record — 使用记录（P2）

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| created_at | TEXT | |
| decision_input | TEXT | 决策输入快照（JSON，物化历史） |
| generation_count | INTEGER | 生成数量 |

> 例外说明：`decision_input` 使用 JSON 快照。本表是日志性质，历史输入不应随之后的方案/成员变更漂移；严格原子化会导致历史镜像过度设计。

### t_usage_record_recipe — 记录-菜谱关联（P2）

| 字段 | 类型 | 注释 |
|---|---|---|
| id | INTEGER PK | |
| record_id | INTEGER FK→t_usage_record | |
| recipe_id | TEXT FK→t_recipe | |
| position | INTEGER | 结果顺序 |

### recipes/*.md — 菜谱详情文件（辅助，可缺失）

```md
---
id: r-0123
name: 清蒸鲈鱼
time: 20min
ingredients: [鲈鱼, 姜, 葱]
techniques: [蒸]
allergens: [鱼]
tastes: [清淡]
---
正文：食材、调料、做法步骤（自由长短，供 Agent 阅读理解）
```

> 文件是菜谱的**辅助详情**，非事实源。`t_recipe` 表中的行是主数据；文件可缺失（仅表数据、未填详情时）。文件与 `t_recipe` 通过 `file_path` 关联，同一菜谱保持 id 一致（文件名 = 菜谱标识）。MD 的 `time` 字段抽取为 `time` 类型要素（分钟数，如 `20min` → `"20"`），与 front-matter 要素标签同构。本服务仅抽取要素类标签用于索引与硬过滤；时令 / 健康等标签**不维护、不解析**，由 Agent 基于 MD 内容结合自有知识库理解。

## 主键

| 表 | 主键 |
|---|---|
| t_element / t_member / t_member_element / t_preference_scheme / t_scheme_element / t_recipe / t_recipe_element / t_weight_setting / t_usage_record / t_usage_record_recipe | 自增 `id`（INTEGER） |

## 外键 / 关联

- `t_member_element.member_id` → `t_member.id`；`t_member_element.element_id` → `t_element.id`
- `t_scheme_element.scheme_id` → `t_preference_scheme.id`；`t_scheme_element.element_id` → `t_element.id`
- `t_recipe_element.recipe_id` → `t_recipe.id`；`t_recipe_element.element_id` → `t_element.id`
- `t_usage_record_recipe.record_id` → `t_usage_record.id`；`t_usage_record_recipe.recipe_id` → `t_recipe.id`
- 文件关联：`t_recipe.file_path` ↔ `recipes/{file}.md`（辅助详情，可空）

## 索引

- `t_element`：`UNIQUE(type, name)`
- `t_member_element`：`UNIQUE(member_id, element_id, relation_type)`；查询性索引 `(member_id, relation_type)`
- `t_scheme_element`：`UNIQUE(scheme_id, element_id)`；查询性索引 `(element_id)`（反查含某要素的方案）
- `t_recipe_element`：`UNIQUE(recipe_id, element_id)`；查询性索引 `(element_id)`（潜在能力：给定禁忌要素集反查菜谱；当前接口未暴露，硬过滤由 Agent 端处理）
- `t_weight_setting`：`UNIQUE(factor)`
- `t_usage_record`：`(created_at)`

## 数据生命周期

- **element**：由种子数据初始化 + 新增菜谱时自动创建（出现未知要素名 → 自动入表），不主动删除
- **member / preference_scheme**：由用户创建，可编辑、可删除；删除 member 级联删除其关联行
- **recipe**：`t_recipe` 为主数据，由用户创建（录入表单）或从内置种子导入；MD 文件为辅助详情，可后补、可缺失；修改/删除以表数据为准，文件随动
- **weight_setting**：初始化写入默认值，用户可调
- **usage_record**：每次决策追加（P2），仅查看，可清理

## 数据一致性要求

- **`t_recipe` 为主数据**：菜谱的增删改以表为准；MD 文件是辅助详情，不反向决定菜谱存在性
- **文件与表联动**：写表时若有详情则同步写/更新 MD 文件，`file_path` 指向文件；文件缺失不视为脏数据（用户未填详情）
- 决策硬过滤（100% 排除启用成员禁忌要素）由 **Agent 端**达成；本系统查询 API 不提供要素过滤入参，数据层仅保存要素关联供 Agent 查询后自行判断

## 事务边界

- 单用户本地、低并发，事务粒度小
- **索引重建**（扫描 → 清空/比对 → 重插 `t_recipe` + `t_recipe_element`）应在单个事务内完成，避免中间态
- **member 删除**（删 member + 删 member_element）在一个事务内
- 决策生成为只读查询 + Agent 调用，无持久化事务（usage_record 写入独立成事务）

## 数据删除 / 归档策略

- **菜谱文件**：删除菜谱以 `t_recipe` 行为准；若存在对应 MD 文件，一并移除
- **element**：默认只增不删；若某要素不再被任何引用，可清理（保守策略：保留，避免误删）
- **usage_record**（P2）：日志性质，支持按时间清理，无归档要求
- 文件与表：`file_path` 指向的文件被误删时，菜谱表数据不丢失，仅详情缺失（可重新录入详情）

## 重要持久化约束

1. `t_recipe` 是菜谱**主数据**，MD 文件为辅助详情（可缺失），文件不反向决定菜谱存在性
2. 表符合原子性：**不使用数组字段**，关联优先（`usage_record.decision_input` JSON 快照为唯一例外，日志性质）
3. 所有要素统一入 `t_element`，其余表只存 `element_id`，不冗余要素名
4. 本服务**不存储/不解析时令与健康要素**，由 Agent 基于 MD 内容结合自有知识库处理
5. 单用户无账号体系，不设计用户/租户维度