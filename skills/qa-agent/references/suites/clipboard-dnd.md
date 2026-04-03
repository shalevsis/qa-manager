# Clipboard & Drag-and-Drop Test Suite

## When to apply
Use when the feature involves copy/paste interactions or drag-and-drop reordering, moving, or transferring of items. Applies to both programmatic clipboard access and native DnD APIs.

## What to test
- Copy action writes the expected text/data to the clipboard
- Paste action reads from the clipboard and inserts the correct value into the target
- Drag source gains a visual dragging state (opacity, outline, cursor change) on drag start
- Drop target visually indicates acceptance when a valid item is dragged over it
- Drop target rejects invalid item types without crashing (e.g. dragging wrong data type)
- Dropping an item reorders the list in the correct position
- Invalid drop (wrong type, wrong zone) leaves the list unchanged
- Keyboard alternative exists for every drag action (e.g. cut/paste or arrow-key reorder)
- `navigator.clipboard` unavailable: fallback to `document.execCommand('copy'/'paste')` works
- Cross-origin or secure context restrictions are handled gracefully (no unhandled rejection)

## Key patterns

**Clipboard write and read**
```
// Write
await navigator.clipboard.writeText(value)
// Verify: read back immediately
const result = await navigator.clipboard.readText()
assert result === value
```

**execCommand fallback**
```
// When navigator.clipboard is undefined (older browsers, non-HTTPS)
const textarea = document.createElement('textarea')
textarea.value = text
document.body.appendChild(textarea)
textarea.select()
document.execCommand('copy')
document.body.removeChild(textarea)
```

**DnD drop position**
```
// Simulate drag start on item[2], drop between item[0] and item[1]
dragStart(items[2])
dragOver(dropZone, { position: 'before', target: items[1] })
drop()
assert list === [item0, item2, item1, item3]
```

**Keyboard reorder alternative**
```
// Select item, move up/down with keyboard shortcut
focus(item)
keyDown('ArrowUp')   // or Ctrl+Up / platform equivalent
assert item moved to previous index
```

## Common gaps
- Only testing `navigator.clipboard` — not verifying the `execCommand` fallback path
- Drag state class/style not removed after a failed drop or drag-cancel (ghost state stuck)
- No assertion that the drop target rejects the wrong data type (dragover `preventDefault` not conditional)
- Keyboard alternative is absent or only works via an undocumented shortcut (a11y failure)
- `dataTransfer.setData` type mismatch — writing as `text/plain` but reading as `text/uri-list`
- Not testing that cancelling a drag mid-flight (Escape key) restores the original order
- Clipboard permissions not requested before writing in browsers that require explicit permission
