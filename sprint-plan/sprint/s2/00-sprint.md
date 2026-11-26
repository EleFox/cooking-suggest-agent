# Sprint

## Sprint ID

S2

## Sprint Name

S2 · 料理偏好设置 + 方案缓存 + 决策接口对接

## One Line Goal

（待定）

## SPRINT_STATE

phase: 12
status: COMMITTED

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
- requirements/10-acceptance.md（验收标准）
- requirements/11-mvp.md（MVP 范围）
- design/project/persistence.md（数据模型：t_preference_scheme / t_scheme_element）
- design/project/service-overview.md（料理偏好方案模块）
- design/sprints/S1/api.md（决策接口契约）

## Last Updated

2026-09-05

## Notes

- **本轮约定（CONFIRMED，2026-09-05）**：
  - 仅讨论 web + service 端；Agent 端内容由其他团队负责，本迭代不涉及
  - 不参考 S1 完成情况（S1 因 Agent 实现重大需求变更已不能反映现实）
  - 范围：料理偏好设置（US-03）+ 料理偏好方案缓存（US-04）+ 对接料理决策接口
  - 明确排除：成员管理（0 成员，成员区对接下一步）、决策权重配置（US-06）、根据偏好表单设置进行菜谱推荐（S1 已开发，本轮只对接接口）
- 方案缓存存储：后端 SQLite + 方案 CRUD API（CONFIRMED，2026-09-05）
- 偏好设置页形态：独立页面，先进设置再进结果（CONFIRMED，2026-09-05）
- **决策接口对接（CONFIRMED，2026-09-05）**：料理偏好→决策的传参逻辑已由 S1 实现（封装在 `/api/decisions` 中），本轮 service 只需把参数传入该接口；**功能实现细节不纳入迭代讨论**
- 页面拆分见 02-backlog-input.md；目标见 01-goal.md