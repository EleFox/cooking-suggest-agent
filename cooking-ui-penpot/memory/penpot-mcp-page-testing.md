# Penpot MCP Page Testing Lessons

## Scope

These notes document reusable safeguards for Penpot MCP workflows that create,
inspect, or export pages and artboards.

## Page Creation Does Not Imply Page Activation

### Symptom

After calling `createPage()`, creating an artboard and appending it through the
current root can place the artboard on the previously active page.

### Cause

The newly created page is not necessarily the active page in the plugin
context. `penpot.root` always refers to the current page's root.

### Prevention

1. Create the page and store its ID.
2. Switch to it with `openPage(pageId, false)`.
3. Confirm `penpot.currentPage.id` matches the target page ID.
4. Only then create and append page content through `penpot.root`.

Do not treat the return value of `createPage()` as proof that the page is
active.

## Page Switching May Be Asynchronous

### Symptom

An immediate read of `currentPage` after `openPage()` can still report the old
page.

### Prevention

Use the page ID rather than relying on an ambiguous object reference, wait for
the context to settle, and then verify `currentPage` before mutating content.
A short delay such as approximately 300 ms may be required in the MCP plugin
context.

## Validate Mounting Before Continuing

After creating an artboard, read the target page structure and verify all of
the following:

- The target page contains the expected artboard.
- The artboard has the intended width and height.
- The artboard has the expected child count.
- The original page has not received unintended content.

If content is mounted on the wrong page, remove it before creating a corrected
copy. Never leave test artifacts on unrelated pages.

## Export Is a Separate Validation Risk

### Symptom

`export_shape` may fail with a null export error even when page creation and
structure reads succeed.

### Prevention

Treat structural validation and export validation as separate checkpoints.
Verify the exact shape ID returned by a fresh structure read before exporting.
If PNG and SVG exports both fail, report the export limitation explicitly and
do not claim that visual inspection was completed.

## Text Shapes Can Exist Without Rendering

### Symptom

A text shape appears in the structure tree and contains the expected
characters, font, color, and bounds, but is not visible after refresh.

### Cause

The text object may not have completed font layout. A useful signal is a
missing or null `textBounds` value, even when the regular `bounds` value looks
valid. This can happen when text is created, styled, and persisted before the
font engine finishes resolving the text layout.

### Prevention

After creating or changing a text shape:

1. Apply a known available font with `font.applyToText()`.
2. Apply the font-size and color tokens.
3. Set `growType` to `auto-width` or `auto-height`.
4. Wait for font layout to settle.
5. Verify `textBounds` is non-null and has positive width and height.

If `textBounds` remains invalid, rebuild the text shape rather than relying on
the existing object. Recreate it with the same semantic name and content,
then reapply the font and tokens before continuing.

Transparent hit-area shapes are intentionally not visible; validate their
dimensions separately from the visible control.

## Recommended Verification Sequence

```text
Read current pages and tokens
Create the page
Open the page by ID
Wait for page activation
Verify currentPage.id
Create and size the artboard
Append it to penpot.root
Read the target and original page structures
Attempt export and report export status separately
```

For text-heavy screens, also validate every text shape's `textBounds` before
considering the screen visually complete.

## General Rule

Every mutating Penpot call must be followed by a read-back that verifies the
actual page, parent, dimensions, and child structure. Return values alone are
not sufficient evidence that the mutation occurred in the intended context.
