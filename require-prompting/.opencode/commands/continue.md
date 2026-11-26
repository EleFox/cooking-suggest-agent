---
description: Continue requirement thinking from current state
---

# Continue

执行以下步骤。

## Step 1

读取：

requirements/00-project.md
requirements/99-summary.md

## Step 2

读取当前 phase 对应的详细文件。

## Step 3

判断当前状态：

NOT_STARTED
DRAFT
WAITING_CONFIRMATION
CONFIRMED

## Step 4

如果状态为 WAITING_CONFIRMATION：

只询问用户：

"以上总结是否准确？需要修改什么？"

不要继续分析。

## Step 5

如果状态为 DRAFT：

执行当前 Phase 的引导任务。

## Step 6

如果当前 Phase 已经足够明确：

输出：

### 当前理解
...

### 已确认
...

### 仍然不确定
...

### 建议下一步
...

然后询问用户是否确认。

## Step 7

用户确认后：

- 将当前 Phase 标记 CONFIRMED
- 更新对应文件
- 更新 99-summary.md
- PROJECT_STATE.phase + 1

## 重要限制

每次只推进一个 Phase。

每轮最多两个问题。

不要跳跃多个 Phase。