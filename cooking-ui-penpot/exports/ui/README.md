# UI 导出阅读指南（通用）

> 本指南是阅读 `exports/ui/` 下所有 Penpot UI 导出的通用方法。
> 任何 UI 界面导出后都应遵循本指南的结构与命名约定。
> 当需要分析某个页面时，先阅读本文件，再根据目录定位对应页面的导出文件。

---

## 1. 目录结构约定

所有 Penpot UI 界面统一导出到 `exports/ui/`，每个界面一个子目录：

```
exports/ui/
  <screen-name>/
    <screen-name>-structure.json   # 画板层级树（推荐 AI 优先阅读）
    <screen-name>-markup.html      # HTML 结构（元素顺序 + 坐标）
    <screen-name>-style.css        # CSS 样式（尺寸/颜色/圆角/字体）
    README.md                      # 可选：该界面的说明/特殊约定
```

- 子目录名与画板名一致（kebab-case）。
- 三个导出文件由 `penpot-ui-export` skill 统一生成，命名固定。
- 若界面有多个画板，每个画板单独导出并放在同一子目录下。

---

## 2. 推荐阅读顺序

给 AI 阅读时的推荐顺序：

1. **先读本文件**（`exports/ui/README.md` 或本指南）——了解约定。
2. **读 `structure.json`**——了解画板层级、元素命名、类型，建立整体结构认知。
3. **读 `markup.html`**——了解元素在 DOM 中的顺序、包含关系、文本内容与绝对坐标。
4. **读 `style.css`**——获取尺寸、颜色、圆角、字体、定位等具体数值。
5. 如需视觉参照，查看该目录下的 PNG/SVG 导出（若可用）。

> 顺序原则：先结构、后内容、再样式，最后视觉确认。

---

## 3. 如何从文件理解 UI

### 3.1 structure.json（层级树）

- 顶层是 `board`（画板），`name` 即界面名。
- 每个节点含 `name`、`type`、`children`（可选）。
- `type` 取值：`board` / `rectangle` / `ellipse` / `text` / `path` / `group` 等。
- 命名采用语义化 kebab-case，例如：
  - `result-title` → 标题文字
  - `dish-01-card-clickable` → 可点击卡片（整卡交互）
  - `*-delete-hit-area` → 透明触控热区
  - `add-more-action` → 底部主操作

### 3.2 markup.html（结构与内容）

- `data-x` / `data-y` 是元素在画板内的绝对坐标（以画板左上为原点，px）。
- `<!-- text: xxx -->` 注释标记元素用途。
- `<div class="shape text ...">` 内含实际文本 `<span ...>文本</span>`。
- 空 `<div class="shape rect ...">` 表示矩形/占位，无内联内容，具体样式看 CSS。
- 元素在 HTML 中的先后顺序 = 画板内的 z 顺序（后渲染的在上层）。

### 3.3 style.css（样式）

- 每个元素一个 CSS 块，注释标明元素名。
- 关键字段：
  - `position: absolute` + `left/top` = 画板内定位。
  - `width/height` = 尺寸。
  - `background` = 填充色（含透明度，如 `#ffffffFF`）。
  - `border` = 描边（宽度/颜色）。
  - `border-*-radius` = 各角圆角。
  - 文本块内的 `font-size` / `font-weight` / `font-family` / `color` = 文字样式。
- 颜色可能以 `rgba(...)` 或 `#RRGGBBAA` 表示。

---

## 4. 命名约定（语义化）

- 通用前缀：`result-`（页面级）、`dish-01-`/`dish-02-`（卡片实例）。
- 结构后缀：`-card`（卡片容器）、`-label`（字段标签）、`-value`（字段值）、`-title`（标题）。
- 交互后缀：`-action`（主操作）、`-hit-area`（透明触控热区）、`-clickable`（整卡可点）。
- 组件命名：`<实例>-<用途>`，如 `add-more-action`、`dish-01-delete-corner`。

> 给编码 AI 的提示：语义化命名可以直接映射为组件/类名，无需额外推断。

---

## 5. 常见注意点

- **触控热区 vs 视觉尺寸**：`-hit-area` 的尺寸通常大于视觉元素（如视觉 66px、热区 88px），实现时以热区为点击区域。
- **透明元素**：`-hit-area` 无填充，结构上存在但不可见，属正常。
- **图标占位**：纯色圆角矩形/圆形常为图标或图片占位，可替换为真实图标/图片。
- **z 顺序**：HTML 顺序即层叠顺序，若元素被遮挡，检查是否被后渲染元素覆盖。
- **网格**：坐标和尺寸一般落在 4px 网格上，实现时不要随意引入非网格值。

---

## 6. 新增界面导出时

新增一个 UI 界面时：

1. 在 Penpot 中命名画板（语义化 kebab-case）。
2. 用 `penpot-ui-export` skill 导出三件套到 `exports/ui/<screen-name>/`。
3. 校验 `textBounds`（确保文字可见）。
4. 更新 `exports/ui/README.md` 的目录索引（可选）。
5. 如需特殊说明，在对应子目录添加 `README.md`。

---

## 7. 索引

> 各界面导出位置一览（按需维护）。

| 界面名 | 目录 | 说明 |
|--------|------|------|
| results-screen | `exports/ui/results-screen/` | 菜谱推荐结果页（REQ-04/REQ-05；2026-09-10 新增底部「菜谱管理」入口按钮，导出已重新生成） |
| preference-settings-screen | `exports/ui/preference-settings-screen/` | 料理偏好设置页（US-03 / REQ-02；S3 新增成员启停区，见 §14.6） |
| preference-schemes-screen | `exports/ui/preference-schemes-screen/` | 料理偏好方案管理页（US-04 / REQ-02） |
| member-management-screen | `exports/ui/member-management-screen/` | 成员管理列表页（S3 T1 / US-01；卡片=姓名+偏好(食材/口味)+食材禁忌，底部固定「新增成员」） |
| member-management-screen-empty | `exports/ui/member-management-screen-empty/` | 成员管理空态（AC-T1-4，0 成员引导） |
| member-form-screen | `exports/ui/member-form-screen/` | 成员表单页（新增/编辑共用；姓名 + 偏好食材/口味 + 食材禁忌，列表+输入+确认模式） |
| recipe-management-screen | `exports/ui/recipe-management-screen/` | 菜谱管理列表页（S3 T5 / US-11；搜索栏 + 与推荐页一致的卡片流 + 右上 × 删除 / 整卡点按编辑） |
| recipe-form-screen | `exports/ui/recipe-form-screen/` | 菜谱表单页（名称 / 食材列表+录入 / 料理手段 / 时间 / 难度 / 做法） |

> 注：S3 导出的 markup 已做平衡标签裁剪（仅保留首个完整嵌套树），较早期导出（results/preference-settings/preference-schemes）无重复段落；早期导出存在生成器导致的重复序列化片段，阅读时以首个完整嵌套树为准。