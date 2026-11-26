---
name: penpot-ui-export
description: "Export the current Penpot artboard to structured files (structure JSON + markup HTML + style CSS) under exports/ui/. Use when the user asks to export a UI/screen, generate structured output for the coding AI, or save Penpot UI design as files. Triggers: 'export', '导出', 'generate structured output', 'save the UI', '结构文件', '给编码AI'. Also validates textBounds and reports any un-rendered text."
disable-model-invocation: false
version: 1.0.0
audiences: [design-system, design-engineer, product-designer]
mode-default: suggest
---

# penpot-ui-export

Export the current Penpot artboard into a readable, machine-parseable folder for
the coding AI and future UI analysis. This skill standardizes how UI exports are
produced so every screen follows the same structure.

## 1. Trigger / When to use

Use whenever the user asks to:

- export / 导出 a Penpot screen to files,
- generate structured output (structure / markup / style) for a coding AI,
- save the current UI design into the project,
- prepare a screen for code implementation.

Do NOT use for token changes, component creation, or other design mutations.

## 2. Output location & naming

- Root export folder: `exports/ui/`
- Each screen gets its own sub-folder: `exports/ui/<screen-name>/`
- Screen name = the artboard's name (kebab-case), e.g. `results-screen`.
- Files (fixed names):
  - `<screen-name>-structure.json`
  - `<screen-name>-markup.html`
  - `<screen-name>-style.css`
  - Optional `README.md` inside the folder for screen-specific notes.

## 3. Procedure

### Step 1 — Locate the artboard

Identify the target artboard. Usually the active page's root has one board.

```js
const board = penpot.root.children.find(s => s.name === 'results-screen');
```

If unclear, ask the user which board to export, or read `penpotUtils.shapeStructure`.

### Step 2 — Generate the three artifacts

Run once and keep in `storage`:

```js
const board = penpot.root.children.find(s => s.name === '<screen-name>');
storage.exportData = {
  boardId: board.id,
  structure: penpotUtils.shapeStructure(board, 3),
  markup: penpot.generateMarkup([board], { withChildren: true }),
  style: penpot.generateStyle([board], { type: 'css', withChildren: true })
};
```

### Step 3 — Validate textBounds

Verify every text shape has a valid render bounds; report any that don't.

```js
const issues = board.children.filter(s => s.type === 'text')
  .filter(s => !s.characters || !s.textBounds || s.textBounds.width <= 0 || s.textBounds.height <= 0)
  .map(s => s.name);
```

If issues exist, report them; do not claim the export is visually complete.

### Step 4 — Write files to exports/ui/<screen-name>/

Save the three artifacts as files using the Write tool. The folder must exist
before writing (create it if needed).

### Step 5 — Report

Report: screen name, folder path, whether textBounds passed, and any
export/visualization limitations.

## 4. Notes

- `generateMarkup` includes element order = z-order; `data-x`/`data-y` are
  absolute coordinates.
- `generateStyle` output uses `position: absolute` and rgba/hex colors.
- Structure JSON uses semantic kebab-case names that map directly to components.
- The reading guide lives at `exports/ui/README.md` and must stay in sync with
  new exports.
- Keep the one-step-per-call rule: generating and writing are separate steps.