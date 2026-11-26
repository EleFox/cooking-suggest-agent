---
description: Summarize and persist current requirement state
---

# Summarize

读取：

- requirements/00-project.md
- 当前阶段文件
- requirements/99-summary.md

生成当前阶段总结。

必须区分：

FACT
ASSUMPTION
IDEA
QUESTION
CONFIRMED
DRAFT

不要新增用户没有表达过的事实。

更新：

1. 当前阶段文件
2. requirements/99-summary.md

不要改变 PROJECT_STATE，除非用户已经明确确认当前阶段。