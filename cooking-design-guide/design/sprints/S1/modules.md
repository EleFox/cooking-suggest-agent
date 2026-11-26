# modules.md — 模块设计（S1）

> S1 · 菜谱卡片列表页 + "再来一道"

## 前端模块（React + Vite）

### 结果列表页

- **职责**：页面挂载即自动发起首次生成请求并展示第一道菜；维护已展示菜谱 id 去重列表；渲染卡片列表；"再来一道"追加
- **进入条件**：无前置输入（决策参数硬编码，无决策输入区）

### 硬编码决策参数

- 前端定义常量（如 `decision-params.ts`）：
  ```ts
  export const HARDCODED_DECISION_PARAMS = {
    count: 1,
    elements: [
      { type: "technique", sentiment: 1 },
      { type: "time", sentiment: 1 },
    ],
  };
  ```
- 调用决策接口时合并去重列表：`{ ...HARDCODED_DECISION_PARAMS, dedup_ids }`
- 后续迭代引入决策勾选页时，本常量替换为动态来源

### 卡片列表组件

- 每张卡片展示：菜名、食材（ingredients）、所需时间（"约 X 分钟"）、烹饪难度
- **卡片点击**：本轮仅占位（无跳转），详情页后续迭代
- **卡片删除（×）**：本轮仅前端本地移除卡片，**无对应后端接口**；删除是否影响去重（`dedup_ids` 保留/移除该 id）由后续迭代确定

### 状态处理

| 状态 | 行为 |
|---|---|
| 加载中 | 请求期间禁用"再来一道"按钮，卡片区展示 loading（骨架/转圈） |
| 成功 | 首轮填充 / "再来一道"追加渲染新卡片 |
| 无结果 | `data.data` 为空 → 展示 `data.message` 提示，不新增卡片 |
| 错误 | 展示错误提示，保留"再来一道"按钮；点击即重试，不自动重试 |

## 接口服务模块（FastAPI）

### 决策接口

- **职责**：接收决策请求（`count` / `dedup_ids` / `elements`）→ 本轮返回固定/种子菜谱模拟结果（Agent 未就绪，方案 B）→ 组装卡片数据 → 按统一信封返回
- 后续：替换为透传 Agent（黑盒）→ 按返回菜谱 id 组装卡片，契约不变

### 卡片组装

- 依据返回的菜谱 id 集合，从菜谱表组装卡片字段：
  - `t_recipe`：id / name / time_estimate
  - `t_recipe_element` → `t_element`：ingredients（type=ingredient）、difficulty（type=difficulty）
- 返回卡片数组按 `count` 数量

### 去重过滤

- 依据请求 `dedup_ids` 过滤，保证返回菜谱不与已展示菜谱重复

## 数据模型变更（本迭代引入）

- **烹饪难度要素**：`t_element` 新增类型 `difficulty`，name 枚举（简单 / 一般 / 困难），经 `t_recipe_element` 关联菜谱，与食材等要素同构
- 属于对项目级 `design/project/persistence.md` 的数据模型扩展，需在项目级文档中同步（**待用户确认后更新**）
- 种子菜谱池：为支撑卡片展示与模拟返回，需准备含摘要字段（含难度要素关联）的种子菜谱若干道

## 与项目级设计关系

| 项目级设计 | 本轮关系 |
|---|---|
| `service-overview.md` 结果组装 | 本轮改为卡片 JSON 组装（固定格式 Markdown 属详情页，后续迭代） |
| `integrations.md` Agent 协议 | 契约保留，本轮不透传（模拟返回） |
| `persistence.md` | 新增 difficulty 要素类型，待确认更新 |