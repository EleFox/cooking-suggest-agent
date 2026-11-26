---
name: sprint-planning
description: Guide users from confirmed requirements/user stories to a committed, executable sprint backlog through staged questioning and planning.
---

# Sprint Planning Skill

## Purpose

帮助用户把已确认的需求 / 用户故事，转化为可执行的迭代任务清单。

不是直接生成排期表。

而是通过：

观察
→ 提问
→ 总结
→ 拆解
→ 估算
→ 验证
→ 承诺

逐步形成迭代任务。

输入默认来自 requirements/ 中的已确认内容（产品待办）。

---

# Phase 0 Init

目标：

初始化迭代规划工作区。

检查：

- sprint/00-sprint.md 是否存在
- requirements/ 中是否已有可用的用户故事 / 需求
- 当前 SPRINT_STATE

如果 sprint/00-sprint.md 不存在，则创建模板并初始化。

---

# Phase 1 Sprint Goal

目标：

定义本次迭代的目标。

问题：

WHY？

这次迭代要交付什么结果？

完成这次迭代后，用户/业务获得了什么？

好的目标：

- 一句话
- 可衡量
- 属于"结果"，不是"任务列表"

不要直接罗列功能。

---

# Phase 2 Backlog Input

目标：

从产品待办中选取本次迭代要做的内容。

依次考虑：

WHAT？

有哪些候选的用户故事 / 需求？

哪些是本迭代必须做的？

哪些可以留到下一迭代？

依据（来自 requirements/）：

- 优先级（P0 / P1 / P2）
- 依赖关系
- 目标相关性

不要自己发明需求。

---

# Phase 3 Capacity

目标：

明确迭代容量。

问题：

WHO？WHEN？

迭代时长多长？

团队 / 人力有谁、可用度如何？

历史速度（Velocity）是多少？

是否存在固定日程占用？

容量不是无限。容量不够时必须显式说明。

---

# Phase 4 Task Breakdown

目标：

把选中的用户故事拆解为可执行任务。

拆解原则：

- 每个任务可独立执行
- 每个任务可独立验证
- 每个任务描述动作（动词开头）
- 不拆分到过度粒度（以"一天内可完成"为经验参考）

模板：

作为故事 [US-xx]，需要执行：……

---

# Phase 5 Task Acceptance

目标：

为每个任务定义验收标准。

使用：

Given
When
Then

或任务级 DoD。

避免模糊词：

- 合理
- 智能
- 快速
- 简单
- 好用
- 完整

验收标准先于承诺。

---

# Phase 6 Estimation

目标：

估算工作量。

使用相对估算：

故事点：1 / 2 / 3 / 5 / 8

超出 8 的任务：需要继续拆解。

建议标记：

- 每任务点数
- 每故事点数
- 汇总点数

对比：

估算总量 vs 迭代容量

超出容量 → 返回 Phase 8 做取舍，不要硬塞。

所有估算标记为 ASSUMPTION，直到用户确认。

---

# Phase 7 Dependency & Order

目标：

梳理依赖关系与执行顺序。

依次考虑：

- 任务之间的依赖（A 完成后才能做 B）
- 用户故事之间的依赖
- 外部依赖（设计稿 / 接口 / 其他团队）
- 顺序建议

输出：

执行顺序列表

标出关键路径（Critical Path）。

阻塞项单独列出。

---

# Phase 8 Priority

目标：

在容量范围内做优先级取舍。

使用 MoSCoW：

Must
Should
Could
Won't（本迭代）

问题：

如果容量不够，砍掉什么？

哪些可以先做垂直切片，再横向扩展？

取舍必须显式记录（REJECTED / SUPERSEDED）。

---

# Phase 9 Risk

目标：

识别风险与阻塞项。

依次考虑：

- 需求不确定性
- 技术不确定性
- 依赖未就绪
- 容量过高
- 关键人员不可用

对每个风险：

- 影响
- 可能性
- 缓解措施
- 是否需要缓冲

---

# Phase 10 Commitment

目标：

冻结 Sprint Backlog，形成迭代承诺。

承诺包含：

- 迭代目标
- 入选的用户故事清单（含点数）
- 任务清单
- 明确排除项

承诺必须是用户明确确认的。

确认后标记为 COMMITTED。

---

# Phase 11 DoD & Review

目标：

定义迭代级 Definition of Done。

检查项示例：

- 代码完成并合入
- 验收标准全部通过
- 无已知 P0 缺陷
- 文档 / 测试更新
- 演示就绪

同时定义迭代结束时的评审方式：

- 向谁演示什么
- 衡量目标是否达成

---

# Phase 12 Complete

目标：

检查迭代任务清单是否已可执行。

检查：

- Goal
- Backlog Input
- Capacity
- Task Breakdown
- Acceptance
- Estimation
- Dependency & Order
- Priority
- Risk
- Commitment
- DoD

是否已经基本明确。

未解决问题可以存在。

不要求 100% 确定。

---

# Conversation Rules

每次：

1. 读取 sprint/ 相关文件
2. 判断当前阶段
3. 简短总结
4. 找一个最大未知点
5. 提一个问题
6. 等待

最多两个问题。

不要长篇教学。

---

# Thinking Rules

永远区分：

用户说的
AI 推断的
AI 建议的

推荐输出：

"你刚才说的是……"

"我理解成……"

"这里我有一个假设……"

"这里还有一个问题……"

不要把 AI 推断写成事实。
