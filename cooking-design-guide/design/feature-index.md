# feature-index.md — 功能最新设计索引

本文件用于回答："某个功能当前最新的设计在哪里？"

它不是详细设计文档。每个功能只记录**当前最新有效设计**。

## 使用规则

- 处理"修改已有功能"时，先通过本表定位最新设计，再读取对应文档。
- 后续迭代修改历史功能时，**不修改历史设计文档**。
- 新迭代完成后，将该功能的最新设计指向当前迭代文档。
- 历史文档 = 历史设计记录；最新迭代 = 当前有效修改；本文件 = 功能最新设计索引。

## 功能索引

> 项目级设计初始化完成（2026-08-22）。迭代设计开始前，各功能最新设计指向 `project/` 文档；后续迭代修改历史功能时，将最新设计指向对应迭代文档。

| 功能 | 当前有效设计 | 最新设计文档 | 状态 |
|---|---|---|---|
| 成员偏好/禁忌管理 | S3 迭代设计 | `sprints/S3/api.md` + `modules.md` + `business.md`（成员 CRUD + 成员管理/表单页；要素统一 `{name,type}`/`{name,type,id,operate}` 数组契约 + resolve-or-create） | 已设计 |
| 成员启停（决策前） | S3 迭代设计 | `sprints/S3/business.md` + `modules.md`（设置页成员区，默认全启用，不持久化） | 已设计 |
| 料理偏好方案 | S2 迭代设计 | `sprints/S2/api.md` + `modules.md` + `business.md`（方案 CRUD + 设置页/方案页） | 已设计 |
| 菜谱池 | S3 迭代设计 | `sprints/S3/api.md` + `modules.md` + `business.md`（菜谱 CRUD 全池可管、物理删除、做法→MD 文件；要素统一数组契约；`GET /api/recipes` 列表 elements 数组 + `exclude_recipe_ids` 去重 + 批量详情 `GET /api/recipes/detail?ids=`；两者兼作 Agent 反向 API） | 已设计 |
| 决策对接（Agent） | 项目级设计 | `project/service-overview.md`（Agent 决策对接）+ `project/integrations.md`（协议） | 已设计 |
| 权重设置 | 项目级设计 | `project/service-overview.md`（权重设置）+ `project/persistence.md` | 已设计 |
| 结果组装（固定格式） | 项目级设计 | `project/service-overview.md`（结果组装） | 已设计 |
| 使用记录 | 项目级设计 | `project/service-overview.md`（使用记录）+ `project/persistence.md`（P2） | 已设计 |
| 决策接口（结果卡片） | S3 迭代设计 | `sprints/S3/api.md` + `modules.md` + `business.md`（`relation_type` 替代 sentiment；服务端 enrich elements + 将 dedup_ids 翻译为完整菜谱；响应 `data` 卡片数组，elements + has_detail） | 已设计 |
| 要素字典查询 | S2 迭代设计 | `sprints/S2/api.md`（`GET /api/elements`）+ `modules.md`；S3 扩展支持 difficulty 类型查询 | 已设计 |
