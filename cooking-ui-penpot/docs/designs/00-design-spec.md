# Design Specification

> Updated: 2026-08-21

## 1. Design Goals

This specification defines a unified visual language and interaction guidelines for the mobile UI, to align the Penpot design file with the frontend implementation (shadcn/ui + Radix UI).

**Style keywords**: Minimal, restrained, warm, trustworthy. Avoid decorative redundancy; let "information and decision-making" take center stage.

---

## 2. Canvas & Responsiveness

- **Base artboard size**: 750px × 1334px (mobile, @2x visual mockup).
- **Content safe area**: 32px left/right margins (`space-8`); 44px reserved at the top for the status bar area; safe area reserved at the bottom.
- **Adaptive behavior**: Primarily single-column vertical flow layout; flexible-width components such as cards, buttons, and inputs should adapt smoothly within a width range of 320px–750px without leaving dead space.
- **Grid**: All dimensions and spacing follow a **4px grid** (4 / 8 / 12 / 16 / 24 / 32 / 48…).
- **Touch targets**: Primary actions (buttons, switches, tappable cards) must have a height ≥ 88px (44pt), and the tap area should not be smaller than this size.

---

## 3. Color

> Use semantic naming bound to design tokens; do **not** hardcode color values in shapes.

| Token                      | Usage                                 | Reference Hex |
| -------------------------- | ------------------------------------- | ------------- |
| `color.bg`                 | Page background                       | `#FAF7F2` (warm white, soft) |
| `color.surface`            | Card / input / component background   | `#FFFFFF`     |
| `color.primary`            | Primary actions, emphasis             | `#E86A3C`     |
| `color.primary.foreground` | Primary button text                   | `#FFFFFF`     |
| `color.primary.soft`       | Light background for selected state   | `#FCE9E0`     |
| `color.text`               | Body text                             | `#2D2A26`     |
| `color.text.muted`         | Secondary text / captions             | `#8A857E`     |
| `color.border`             | Dividers / borders                    | `#E8E2D8`     |
| `color.success`            | Success                               | `#4C9A5F`     |
| `color.warning`            | Warning / notice                      | `#D99A2B`     |
| `color.error`              | Error / conflict alert                | `#C94A3C`     |

**Contrast**: Body text (`#2D2A26`) on `#FAF7F2` achieves a contrast ratio of ≥ 7:1 (AAA); `text.muted` should only be used for non‑critical information and must not fall below 4.5:1. Error / hard‑constraint messages must always use the `error` color and must not be visually weakened.

---

## 4. Typography

- **Font family**: System sans‑serif (`PingFang SC` / `HarmonyOS Sans` / `Roboto`) to preserve a native mobile feel.
- **Type scale** (spacing and line‑height follow the 4px grid):

| Token              | Size | Line‑height | Weight | Usage                           |
| ------------------ | ---- | ----------- | ------ | ------------------------------- |
| `type.display`     | 32   | 40          | 700    | Page main title                 |
| `type.h1`          | 24   | 32          | 600    | Section title                   |
| `type.h2`          | 20   | 28          | 600    | Card title                      |
| `type.body`        | 16   | 24          | 400    | Body text                       |
| `type.body.strong` | 16   | 24          | 600    | Emphasized body text            |
| `type.caption`     | 13   | 20          | 400    | Helper text / label             |
| `type.label`       | 14   | 20          | 500    | Form label / button text        |

- Align baselines consistently in mixed Chinese/English text; use tabular numerals for digits and units to maintain alignment.

---

## 5. Spacing

Use a unified 4px grid: `space-1=4`, `space-2=8`, `space-3=12`, `space-4=16`, `space-6=24`, `space-8=32`, `space-10=40`, `space-12=48`.

- Page horizontal margins: `space-8` (32px).
- Gap between cards: `space-4` (16px).
- Card inner padding: `space-6` (24px).
- Spacing between adjacent sections: `space-8` or greater.
- Group title to its content: `space-4`.

---

## 6. Radius & Elevation

- **Border radius** (following shadcn/ui style):
  - `radius-sm`: 8px — tags / small controls
  - `radius-md`: 12px — inputs / buttons
  - `radius-lg`: 16px — cards
  - `radius-full`: 999px — pill buttons / quantity selectors / avatars
- **Shadows**: Use sparingly, only for floating layers (bottom sheets, overlays):
  - Cards default to no shadow; use `border` for separation.
  - Drawers / overlays use `0 -8px 24px rgba(45,42,38,0.12)`.

---

## 7. Component Specifications

> All components are based on shadcn/ui + Radix UI; icons from Lucide React. This spec defines their general appearance in the design file.

### 7.1 Button

- **Primary button**: `color.primary` background, white text, `radius-md`, height 88px, border‑radius 16px, full width (for primary form actions).
- **Secondary / Outline button**: White background + `color.border` stroke, primary text color.
- **Pill button**: Lightweight action, `radius-full`.
- **Icon button**: Icon only, touch area ≥ 88px.
- **States**: Default / Hover (darken by 5%) / Pressed (darken further) / Disabled (40% opacity, `text.muted`).

### 7.2 Switch

- For binary on/off choices. On = `color.primary`, Off = `color.border`; height 64px, width 104px (touch‑friendly).

### 7.3 Checkbox / Multi‑select (Chips)

- For multi‑selection, use **chip pills**: Unselected = white background + border; Selected = `color.primary.soft` background + primary text color + primary‑color border.
- Touch height ≥ 88px, spacing `space-3`.

### 7.4 Input / Textarea

- White background, `color.border` stroke, `radius-md`, inner padding `space-4`.
- Multi‑line use Textarea with placeholder hint.
- States: Default / Focus (primary‑color border + 2px primary glow) / Error (`error` border + error message text).

### 7.5 Stepper

- For quantity selection: left `-` / right `+` icon buttons + central number, pill‑shaped.

### 7.6 Bottom Sheet

- For secondary actions, slides up from the bottom, `radius-lg` top corners, with overlay.

### 7.7 Loading / Empty State

- **Loading**: Skeleton or primary‑colored spinner with message.
- **Empty state**: Centered icon (Lucide) + main text + secondary action button.

### 7.8 Info Card

- Single‑column information layout with consistent fields and clear hierarchy:
  - Title (`h2`)
  - Tag row (`caption` + light‑background chips)
  - List / body text (`body`)
  - Bottom metadata row (icon + text)
- Cards may include a primary action entry at the bottom of the list.

---

## 8. Interaction States

All interactive components must cover and design the following states:

- Default
- Hover
- Focus
- Active / Selected
- Disabled
- Loading
- Empty
- Error
- Success

---

## 9. Icons

- Use **Lucide React** icons exclusively. If a required icon is missing, raise the issue and wait for a decision before proceeding.
- Icons must be used semantically and correspond to the text and state they accompany. Do not rely on color alone to indicate selected states – use icons / strokes as additional cues.

---

## 10. Accessibility

- Body text to background contrast ratio ≥ 4.5:1 (body text reaches 7:1).
- Touch targets ≥ 88px (44pt).
- Do not use color as the sole means of conveying information (e.g., selected states must also use icons / strokes to differentiate).
- Form controls must have explicit labels and error messages.

---

## 11. Design Decision Log

- The specific color values and font sizes listed are v1 suggestions; they must be reviewed and confirmed before being applied as Penpot tokens.
- Future design decisions (e.g., new components, token adjustments) should be added back to this document and to the corresponding tokens.