# 迭代设计工作流

每次迭代设计遵循以下阶段。本文件定义每个阶段的目标与交付物。

## 阶段总览

```
Prepare → Analyze → Discuss → Draft → Review → Confirm → Finalize
```

## 1. Prepare（建立上下文）

按顺序阅读：

1. `design/README.md`（设计入口）
2. `design/feature-index.md`（功能最新设计索引）
3. `design/project/` 下相关项目级设计（service-overview / persistence / integrations）
4. 当前迭代需求文档（`docs/iterations/<Sx>.md` 或类似）
5. 当前迭代已有设计文档（`design/iterations/<Sx>/`，若存在）
6. 仅在上述内容存在不理解、矛盾、信息不足时，才追溯完整需求文档 `docs/requirements/`
7. 若当前迭代涉及 UI，读取对应 `docs/ui/` Penpot 结构化数据

不默认读取历史迭代全部设计文档。

## 2. Analyze（分析影响范围）

- 分析已有设计、当前需求、UI 三者。
- 识别本次迭代涉及的功能、模块、API、数据。
- 通过 `design/feature-index.md` 判断是否涉及对历史功能的修改。
- 找出可能的设计冲突、信息缺失、职责边界不清。

## 3. Discuss（对话式设计）

- 一次只围绕当前**最重要**的一个设计疑点讨论。
- 根据用户回答继续推导，不一次抛出大量问题。
- 主动检查：异常流程、边界条件、状态流转、并发、幂等、一致性、权限、职责边界、数据模型与业务匹配、API 与业务匹配、UI 与 API/业务匹配、设计冲突、信息缺失。
- 当设计无关键疑点、剩余问题不影响实现、或用户明确足够时结束讨论。

## 4. Draft（生成文档）

在 `design/iterations/<Sx>/` 下创建/更新：

- `api.md`：接口设计（新增/修改、参数、返回、错误、鉴权、权限、幂等、分页/排序、状态码、与业务逻辑关系）
- `modules.md`：模块设计（新增/修改、职责、依赖、类/服务职责、核心方法、边界、与现有模块关系）
- `business.md`：业务设计（正常/分支/异常流程、状态转换、业务规则、边界条件、并发、幂等、一致性、权限、数据处理顺序）

只写本次迭代相关的内容。若需修改历史功能，在当**前**迭代中描述新设计。

## 5. Review（检查）

检查完整性、一致性、边界条件与设计冲突：

- UI → API → Business → Persistence 是否形成完整链路
- 状态流转是否完整
- 异常与边界是否覆盖
- 是否与项目级设计冲突
- 是否与 `feature-index.md` 记录一致

## 6. Confirm（用户确认）

将最终设计呈现给用户，获得明确确认。

## 7. Finalize（锁定与更新索引）

- 锁定当前迭代设计（进入只读）。
- 更新 `design/feature-index.md`，将涉及功能的最新设计指向当前迭代文档。
- 若项目级设计需变更，须先获得用户确认后再更新 `design/project/`。
