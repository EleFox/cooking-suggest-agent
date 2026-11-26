# data-create-agent — 模拟数据生成工作区

本目录用于为 cooking-suggest-agent 项目批量生成调试用模拟数据（当前主要是菜谱），
供 Agent 服务联调使用。**所有数据一律通过 web-service 的 HTTP 接口写入，禁止直接读写数据库文件。**

## 核心原则

1. **每次重新生成**：模拟数据每次都现场生成，不复用同一份固定数据集，不把上一批当作本批数据源。
2. **先审阅后插入**：每批数据先写入 `datas/recipes.json`（JSON 数组）供人工审阅，审阅通过后才执行插入；
   该文件只是本批待审稿件，不作为长期数据集。
3. **不做去重**：插入前**不**全量拉取已有菜名（避免大量请求与 token 浪费），重复风险由审阅环节把关。
4. **数量按任务声明**：每批条数由当次任务声明，不写死。
5. **批内唯一**：同一批 `recipes.json` 内菜名不得重复；生成完成后必须重新通读自审。
6. **真实准确**：菜谱必须真实存在，基于知识库生成，**禁止幻觉编造**；灵感枯竭或缺乏对应知识时，使用联网搜索获取后再生成。
7. **业务语义正确**：要素必须符合「数据要素业务语义」，杜绝类型错位与不存在的食材。
8. **detail 规范**：使用 Markdown 格式，全文 50~500 字。**必须包含「菜品简介」与「做法」两部分**；
   其他知识（营养提示 / 时令推荐 / 搭配建议 / 小贴士等）按需随机穿插，不强求每个文档格式统一。

## 参考文档

- 接口契约：`@design-docs` → `sprints/S3/api.md`（菜谱接口）
- 服务代码：`@service-code` → `backend/`（路由 / schema / service 实现）
- 持久化设计：`@design-docs` → `project/persistence.md`

## 目标服务

| 项       | 值                                                     |
| -------- | ------------------------------------------------------ |
| 基址     | `http://localhost:8000/api`                          |
| 新增菜谱 | `POST /api/recipes`                                  |
| 查询列表 | `GET /api/recipes?page=&page_size=`                  |
| 查询单条 | `GET /api/recipes/detail?id=`                        |
| 返回信封 | `{code, data, message}`，`code` 与 HTTP 状态码一致 |

## 前置条件（重要）

1. web-service 后端必须在 `localhost:8000` 运行。
2. 插入前先探测 `GET http://localhost:8000/api/recipes?page=1&page_size=1`。
3. **后端未启动时直接暂停任务**，提示用户启动，不自动拉起、不直连数据库绕过。

## 要素契约（请求体 `elements:[{name,type}]`）

合法 `type`：`ingredient` / `technique` / `time` / `taste` / `difficulty`。
后端按 `UNIQUE(type, name)` 做 resolve-or-create，要素只增不删。

硬约束（违反返回 `422`，整体失败）：

- `name` 非空。
- `time` 类型**至多 1 个**，且 `name` 为纯正整数分钟数字符串（如 `"45"`）。
- `difficulty` 类型**至多 1 个**。
- `technique` 复用现有种子：煎 / 炒 / 凉拌 / 油炸 / 蒸 / 炖 / 煮 / 烤。
- `difficulty` 复用现有种子：简单 / 一般 / 困难。
- `ingredient` / `taste` 为自由文本，按需使用。

## 数据要素业务语义（生成依据）

生成要素时必须符合各类型的业务含义，**禁止类型错位**（如把口味词写进 `ingredient`）与
**虚构不存在的内容**（如食材写成"石头"）。依据 `persistence.md`：要素类型为
`ingredient` 食材 / `technique` 料理手段 / `time` 料理时间 / `taste` 口味 / `difficulty` 烹饪难度。

| type           | 业务含义                                     | 允许值 / 示例                                                                                             | 典型反例                                                           |
| -------------- | -------------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| `ingredient` | 菜谱主要食材，**必须可食用且真实存在** | 番茄、牛腩、鲈鱼、土豆、鸡蛋、豆腐、西兰花、虾；跨荤 / 素 / 主食 / 汤；以常见食材为主，尽量不使用冷门食材 | "麻辣"（口味）、"炒"（手段）、"石头"（不可食）、"洗洁精"（非食材） |
| `technique`  | 料理手段，供偏好相等匹配                     | 仅限种子：煎 / 炒 / 凉拌 / 油炸 / 蒸 / 炖 / 煮 / 烤                                                       | "红烧"（非种子，应归为 炖 / 煮）、"焖"、"麻辣"                     |
| `time`       | 该菜谱预估耗时                               | 纯正整数分钟数字符串："5" / "10" / "45" / "90"                                                            | "30min"、"半小时"、"很快"、小数 / 负数                             |
| `difficulty` | 烹饪难度                                     | 仅限种子：简单 / 一般 / 困难                                                                              | "中等"、"新手"、"很难"                                             |
| `taste`      | 口味标签，供偏好匹配                         | 清淡、咸鲜、微辣、香辣、麻辣、酸甜、酸辣、甜、酱香                                                        | "牛肉"（食材）、"炖"（手段）                                       |

> 边界：本服务**不维护时令 / 健康（nutrition）要素**；`taste` 仅口味。

## 数据规则

- **批内唯一**：同一批 `recipes.json` 内菜名不得重复；生成后需重新通读自审确认。
- **真实准确**：菜名与做法均须真实存在、符合常识；不得编造不存在的菜式；知识不足时先联网搜索。
- **业务语义**：所有要素符合上节语义，无错位、无虚构食材。
- **数量**：当次任务声明；写入 `datas/recipes.json` 后由审阅环节确认。
- **detail**：Markdown 格式且全文 50~500 字；内容含「简介 + 做法」，其余知识（营养 / 时令 / 小贴士等）随机穿插，格式不统一；
  约 80% 菜谱带 detail（生成 `datas/recipes/r-{id}.md`，`has_detail=true`），
  约 20% 留空（`file_path=null`，`has_detail=false`），覆盖两条分支。
- **覆盖度**：尽量覆盖全部烹饪手段、多档时间、三种难度，食材跨荤素 / 主食 / 汤等；可穿插 `taste`。

## 目录与产物

```
data-create-agent/
├── AGENTS.md
├── datas/
│   └── recipes.json       # 本批待审阅菜谱数据（JSON 数组，可覆盖重写）
└── scripts/
    └── seed_recipes.py    # 读取 datas/recipes.json，经 POST /api/recipes 写入
```

`datas/recipes.json` 单条格式：

```json
{
  "name": "番茄牛腩煲",
  "elements": [
    { "name": "牛腩", "type": "ingredient" },
    { "name": "番茄", "type": "ingredient" },
    { "name": "炖", "type": "technique" },
    { "name": "45", "type": "time" },
    { "name": "一般", "type": "difficulty" }
  ],
  "detail": "## 做法\n1. 牛腩焯水……\n2. ……"
}
```

## 执行流程

1. Agent 按当次任务声明的条数现场生成全新菜谱，写入 `datas/recipes.json`。
2. 生成后通读自审：批内无重复、菜名真实、要素语义正确、硬约束满足、detail 为 Markdown 且在字数区间、JSON 合法。
3. **暂停并请用户审阅** `datas/recipes.json`；用户确认后才继续。
4. 探测后端存活；未启动则暂停并提示。
5. 执行 `python3 scripts/seed_recipes.py`，逐条 `POST /api/recipes`，打印每条结果。
6. 统计新增 / 失败；有失败则打印错误并返回非零退出码。
7. 用一次 `GET /api/recipes?page=1&page_size=1` 读取 `total` 做数量核对。

运行命令：

```bash
python3 scripts/seed_recipes.py --dry-run   # 仅本地校验，不写后端
python3 scripts/seed_recipes.py             # 读取 datas/recipes.json 并插入
```

## 禁止事项

- 禁止直接用 `sqlite3` 或任何方式读写 `cooking.db`。
- 禁止绕过接口直接写 `datas/recipes/` 下的 MD 文件。
- 禁止在后端未启动时自动启动服务或伪造数据。
- 禁止把上一批数据当作本批的数据源重复插入。
- 插入前禁止全量拉取菜名做去重（已明确省去该步骤）。
- 禁止生成不存在 / 不可食用 / 类型错位的要素。
