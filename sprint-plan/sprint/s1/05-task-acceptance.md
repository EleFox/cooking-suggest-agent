# Acceptance / 任务验收标准（DRAFT）

## T-A1 双服务骨架
Given 项目初始化完成
When 执行 docker-compose 启动
Then 接口服务与 Agent 服务同时可运行，Agent 可通过反向调用通道访问接口服务

## T-A2 接口契约与数据模型
Given 接口契约文档
When 评审决策 API / 查询 API / 详情 API + 数据模型
Then 契约覆盖 Agent 反向调用、硬过滤/关键字/去重参数、MD 全文返回、固定格式结果，可冻结为开发基线

## T-C2 菜谱池种子数据
Given 种子菜谱池
When 加载并调用查询/详情 API
Then 每道菜含摘要字段 + MD 全文 + 手段/时间标签，可正常被查询与详情返回

## T-I1 菜谱查询/详情 API
Given Agent 携带条件（过滤/关键字/去重列表）调用查询 API
When 执行查询
Then 返回菜谱摘要列表，不含去重列表中的 id，硬过滤条件全部满足
Given 传入菜谱 id 调用详情 API
When 执行查询
Then 返回该菜谱 MD 全文；不存在的 id 返回明确错误

## T-I2 决策 API
Given 前端发起决策请求（决策输入 + 去重列表 + 数量 n=1）
When 接口服务处理
Then 决策输入透传 Agent；收到最终结果后组装固定格式 Markdown 返回前端；超时返回兜底错误

## T-Ag1 Agent 基座
Given Agent 服务运行
When 收到决策输入
Then 能通过反向调用通道访问查询/详情 API；同步超时有兜底；Agent 端自限时限生效

## T-Ag2 推荐方向规则化
Given 决策输入（料理偏好/时间）
When Agent 判断推荐方向
Then 生成查询条件（硬过滤 + 偏好条件），可被查询 API 接受

## T-Ag3 候选筛选迭代
Given 查询 API 返回候选摘要
When Agent 判断候选合适性
Then 需要时调用详情 API 取 MD 全文确认；反复查询直至合适或达到迭代上限，且查询次数受时限约束

## T-Ag4 最终排序与返回
Given Agent 完成候选筛选
When 排序并返回
Then 返回规则化排序结果；候选为空或迭代超限时返回"无结果"

## T-F2 料理偏好勾选
Given 决策页处于决策前状态
When 用户勾选料理手段/时间偏好
Then 选择被纳入决策输入，且当前选择在界面可见

## T-F5 结果 Markdown 渲染
Given 接口服务返回固定格式 Markdown
When 前端渲染结果
Then 按固定格式展示（菜名/食材/调料/做法/时间/手段/标签）字段齐全

## T-F6 再来一个
Given 页面已有生成结果
When 点击"再来一个"
Then 追加展示一道新菜；已展示菜谱 id 作为去重参数传递，不与已有结果重复

## T-F7 状态提示
Given 各交互状态
When 空/生成中/无结果/超时
Then 显示对应最小提示，流程不中断

## 迭代级验收（DoD 简版）

- 完整流程 ≤ 3 次点击可得到结果
- Agent 规则化决策闭环可用（推荐方向 → 查询候选 → 详情确认 → 排序 → 返回）
- 追加不重复（去重列表生效）、无结果/超时有兜底
- 结果按固定格式 Markdown 展示，字段齐全