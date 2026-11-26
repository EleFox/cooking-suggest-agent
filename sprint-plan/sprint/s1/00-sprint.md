# Sprint

## Sprint ID

S1

## Sprint Name

S1 · 决策+结果页（Agent 规则化决策，MVP 核心闭环）

## One Line Goal

跑通"决策+结果"核心闭环：决策前输入（料理偏好）→ Agent 规则化决策（反向取数）→ 生成 1 道 → 固定格式 Markdown 展示 → 再来一个追加，验证"一次决策降低做饭纠结"。

## SPRINT_STATE

phase: 4
status: DRAFT

## Phase Definition

0 = 初始化
1 = 迭代目标
2 = 待办输入
3 = 容量
4 = 任务拆解
5 = 任务验收
6 = 工作量估算
7 = 依赖与顺序
8 = 优先级取舍
9 = 风险
10 = 迭代承诺
11 = DoD 与评审
12 = 完成

## Input Source

- requirements/08-requirements.md（需求清单 v2）
- requirements/09-user-stories.md（用户故事 v2）
- requirements/11-mvp.md（MVP 范围）
- sprint/s1_bak0822/（原 S1 备份：COMMITTED，2026-08-17）

## Last Updated

2026-08-22

## Notes

- CONFIRMED（2026-08-17 继承）：容量 = 2 周 / 1 人（单人独立开发）；范围模型 = 每轮迭代完成单个页面 + 对应功能；技术选型在骨架内验证后确定
- **架构变更（2026-08-22，SUPERSEDES 旧 S1 单体决策引擎）**：决策核心迁移至 Agent 服务；接口服务新增菜谱查询 API（硬过滤/关键字/去重）与菜谱详情 API（MD 全文）；Agent 反向调用接口服务自主取数；docker-compose 同机部署；同步交互 + 超时兜底；Agent 可能返回"无结果"；接口服务组装固定格式 Markdown
- **用户决策（2026-08-22，CONFIRMED）**：① Agent 决策核心 = 规则化 Agent（确定性规则，不接 LLM，LLM 增强延后 S2）；② 0 成员（跟随 S2 方向），禁忌过滤能力推迟，硬过滤验证改用料理偏好/时间条件
- 原 S1/S2 已备份至 sprint/s1_bak0822/、sprint/s2_bak0822/（2026-08-22）
- 本迭代不含：本地 LLM、成员/禁忌、P1 偏好配置页、方案缓存、权重设置、自由文本输入
- 页面拆分见 02-backlog-input.md；承诺见 10-commitment.md；DoD 见 11-dod.md