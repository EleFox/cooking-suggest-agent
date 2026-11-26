# 隐患清单（Risk / Pitfall Register）

> 记录 `cooking-agent-service` 当前已知/潜在的隐患与可行的解决方法，供迭代排期与
> 代码审查参考。本文档不改变任何接口契约；如与 `design/agreement/*` 冲突，以设计
> 约定为准。
>
> **维护约定**：新增隐患请分配 `R-xx` 编号并标注级别与状态；问题修复后在对应条目
> 记录解决方案与提交，不要直接删除条目。
>
> **级别**：高（阻断主链路 / 数据错误）/ 中（特定条件下出错或退化）/ 低（整洁性、可维护性）。
> **状态**：已实测 / 潜在 / 设计权衡 / 已缓解 / 待处理。

## 一、LLM / 模型

### R-01 思考模型不支持强制 `tool_choice`，决策链路直接失败（高，已实测）

- **现象**：以 `LLM_PROVIDER=custom`、模型 `deepseek-v4.1-flash` 运行时，决策节点
  `trustcall` 结构化抽取抛出
  `400 ... Thinking mode does not support this tool_choice`，接口最终 500。
- **位置**：`agent/graph/nodes.py` 的 `extractor = create_extractor(..., tool_choice="ResultRecipeList")`（约 38-42 行）。
- **影响**：`POST /api/recipes` 主链路不可用，属于发起决策即失败。
- **触发条件**：所选模型为思考（thinking/reasoning）模式，且不支持强制指定工具。
- **建议方案**：
  1. 选用支持 Function Calling 的非思考模型；
  2. 或更换供应方（`LLM_PROVIDER=deepseek` / `ollama`）并验证工具调用；
  3. 或在供应方侧关闭 thinking 模式 / 允许 `tool_choice`；
  4. 回归验证：运行 `python -m scripts.llm_business_eval -s few` 应通过。

### R-02 模型未返回 `tool_calls` 时决策节点越界（中，潜在）

- **现象**：`output["messages"][-1].tool_calls` 为空或缺失时，`tool_calls[0]` 抛
  `IndexError`/`KeyError`，异常向上抛出导致 500。
- **位置**：`agent/graph/nodes.py:177-178`。
- **触发条件**：模型拒答、返回纯文本、或工具调用被上游裁剪。
- **建议方案**：取 `tool_calls` 前判空；为空/解析失败时按“无结果”返回空数组并记录告警日志。

### R-03 食材弱偏好的随机性导致评估波动（中，设计权衡）

- **现象**：系统提示词规定 `ingredient` / `taste` 仅为约 20% 的随机倾向，导致偏好
  选取率类业务测试在轮次较少时结果波动。
- **位置**：`agent/prompts/system-get-recipes.md` 第 4.2 节；评估脚本 `scripts/llm_business_eval.py` 的
  `scenario_preference`。
- **影响**：不稳定性来自设计（避免口味/食材单一），非缺陷；但会让评估出现偶发失败。
- **建议方案**：评估时提高 `--runs`；或对硬偏好（`technique`/`time`/`difficulty`）做确定性断言，
  对弱偏好仅做趋势性观察。

## 二、Agent 工作流

### R-04 候选为空时 `page_size=0` 触发参数校验异常（高，已实测）

- **现象**：当排除已选后候选总量为 0（菜谱池为空，或全部被 `dedup` 排除）时，
  `PLAN` 走 `else` 分支将 `page_size` 置为 `total`（即 0），随后 `FETCH` 调用
  `fetch_recipe_summaries(1, 0)` 触发
  `ValidationError: page_size ... greater than or equal to 1`，工作流异常。
- **位置**：`agent/graph/nodes.py:99-100`（`page_size = total`、`pending_pages=[1]`）
  → `agent/graph/nodes.py:121` → `app/services/recipe_client.py:102`（`RecipeListRequest`）。
- **复现**：`invoke_agent(FakeRecipeService(recipes=[]), count=1)` 直接抛异常（无需 LLM）。
- **建议方案**：`total == 0` 时令 `pending_pages = []`（并保持 `page_size >= 1`），
  使 `dispatch_recipe_fetch` 直接进入 `DECISION`；`DECISION` 在候选为空时已返回空数组，
  从而正常返回 `200 + []`。同时补充针对空池的回归测试。

### R-05 多轮结果累积可能超量 / 重复（中，潜在）

- **现象**：`result_recipes` 使用 `operator.add` 跨轮累积，且：
  - `route_after_decision` 以累积长度判断是否终止，单轮返回可能使总数超过 `count`；
  - `DECISION` 的提示词只包含请求携带的 `select_recipes`，不含上一轮已产出的
    `result_recipes`；`PLAN`/`FETCH` 的 `exclude_recipe_ids` 同样只排除
    `select_recipes`，因此跨轮可能重复选中同一菜谱。
- **位置**：`agent/graph/state.py`（`result_recipes` 归约器）、`agent/graph/nodes.py:214-228`
  （`route_after_decision`）、`agent/graph/nodes.py:90-92`（排除集）。
- **影响**：返回数量可能多于 `count`，或出现重复 id（与 AC-US-08“按数量返回不重复”存在偏差）。
- **建议方案**：
  1. 决策产出后按剩余所需数量截断；
  2. 进入下一轮时把已产出 id 并入排除集合与提示词，“再来一道”语义的去重更准确；
  3. 最终返回前做一次去重。

### R-06 随机抽样页数可能超过实际页数（低，潜在）

- **现象**：`random.sample(range(1, page_total + 1), 4)` 在 `page_total < 4` 时抛
  `ValueError`。
- **位置**：`agent/graph/nodes.py:97`。
- **现状**：当前仅当 `total > 20` 且 `page_size=3` 时才触发，`page_total >= 7`，暂不会触发；
  一旦调整总量/页大小常量即可能暴露。
- **建议方案**：改为 `random.sample(..., k=min(4, page_total))`，增强对参数调整的健壮性。

### R-07 工具绑定无效与遗留死代码（低，待处理）

- **现象**：
  - `main_llm.bind_tools(recipes_tools)` 的返回值被丢弃，工具实际未绑定（`agent/graph/llm.py:66`）；
  - `agent/graph/nodes.py:52-54` 的 `get_recipes` 为早期“模型自行调工具查询”实现，
    当前图未引用；`agent/tools/recipes.py` 的工具在当前 PLAN/FETCH/DECISION 流程下亦未使用。
- **影响**：无运行时影响，但造成误导与维护成本。
- **建议方案**：确认后删除 `get_recipes`；评估是否需要保留工具模块——若保留则正确绑定
  （`main_llm = main_llm.bind_tools(...)`），否则移除并同步清理 `llm.py` 的引用。

### R-08 `fetched_pages` 仅记录未参与逻辑（低，待处理）

- **现象**：`fetched_pages` 累计但未被任何路由/判断使用（`agent/graph/state.py`）。
- **建议方案**：若用于调试保留即可；否则移除，避免状态冗余。

## 三、接口与契约

### R-09 校验错误与未捕获异常未套统一信封（中，潜在）

- **现象**：成功响应为统一信封，但 `422` 为 FastAPI 默认 `{"detail": ...}`、未捕获
  异常为默认 `500`，均不符合 `design/agreement/api-conventions.md`“业务接口统一信封”的约定。
- **位置**：`app/main.py:30`（未注册异常处理器）；`app/api/routes/recipes.py`。
- **现状**：调用方 `cooking-web-service` 的 `agent_client.get_recipe_ids` 使用
  `raise_for_status()`，仅解析 `200` 信封，因此当前不会因此出错；属契约一致性风险。
- **建议方案**：为 `RequestValidationError` / `HTTPException` / 兜底 `Exception` 注册处理器，
  统一包装为 `Envelope`；或经确认后在设计文档明确“参数校验沿用 FastAPI 默认结构”。

### R-10 上游菜谱接口的异常粒度（中，潜在）

- **现象**：`app/services/recipe_client.py` 将网络错误与非 200 信封统一抛
  `RecipeServiceError`，上层未做降级，直接导致决策失败。
- **建议方案**：按需求确认是否需要降级（如返回空结果并提示），并在 `agent/services/`
  记录可观测日志；当前按“决策核心不做规则降级”的设计可保持现状。

## 四、配置与安全

### R-11 密钥泄漏风险与 `.env` 变体未忽略（高，已缓解/需持续关注）

- **现象**：`.gitignore` 仅忽略 `.env`，不匹配 `.env copy`、`.env.bak` 等变体；
  开发过程中曾出现未跟踪的 `.env copy`（含自定义模型/密钥配置）。
- **位置**：`cooking-agent-service/.gitignore`。
- **影响**：一旦误提交，将泄漏 API Key。
- **建议方案**：将忽略规则改为 `.env*` 并例外 `!.env.example`；确认历史中未提交过任何
  真实密钥，必要时轮换密钥；密钥仅经 `Settings`/`.env` 注入。

### R-12 LLM 在导入期实例化，切换供应方需重启（低，设计权衡）

- **现象**：`main_llm = _build_llm(settings)` 在模块导入时执行，`LLM_PROVIDER` 变更后
  需重启进程；未配置密钥时导入期即报错。
- **位置**：`agent/graph/llm.py:64`。
- **建议方案**：如需运行时切换，改为惰性初始化并缓存；否则至少保证启动自检给出清晰
  错误（当前 `llm_business_eval` 已做配置校验，可参考）。

## 五、测试

### R-13 LLM 业务评估不纳入回归（低，设计权衡）

- **说明**：`scripts/llm_business_eval.py` 依赖真实大模型与网络，结果具随机性，
  **不纳入回归/常规提交测试**（pytest 仅收集 `tests/`）。其中“空池崩溃”（R-04）等
  确定性缺陷应另写纯单元测试纳入回归，不应依赖该脚本。
- **建议方案**：为 R-04、R-05、R-06 补充基于 mock 的确定性单元测试。

---

## 更新记录

| 日期 | 变更 |
|---|---|
| 2026-09-14 | 初版：整理 LLM 兼容性、空池崩溃、多轮累积、契约与配置等隐患 |
