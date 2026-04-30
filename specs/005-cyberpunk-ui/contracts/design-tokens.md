# Design Token Contract: Dark Cyberpunk UI

**Spec**: [spec.md](../spec.md)
**Version**: 1.0.0
**Status**: Authoritative — implementation MUST match exactly

---

## Color Tokens

| Token Name | CSS Variable | Hex / Value | Usage |
|---|---|---|---|
| Background | `--bg` | `#0a0f0d` | Page background, body |
| Surface | `--surface` | `rgba(255,255,255,0.04)` | Cards, panels, dropdowns |
| Border | `--border` | `rgba(0,255,128,0.12)` | Card/panel border (1px solid) |
| Accent | `--accent` | `#00e676` | Primary neon green, focus rings, active states |
| Success | `--success` | `#00c853` | Running VM status, user chat bubble bg, button start |
| Warning | `--warning` | `#ff6d00` | Stopped/error VM status, error text |
| Text Muted | `--text-muted` | `#7a9e8a` | Secondary text, placeholders, nav links at rest |
| Text Primary | `--text` | `#e8f5e9` | Headings, primary body text, button labels |

### Glow

| Token | Value | Usage |
|---|---|---|
| Card glow (hover) | `box-shadow: 0 0 40px rgba(0,230,118,0.15)` | VM card hover, key element highlight |
| Ambient glow | `box-shadow: 0 0 60px rgba(0,230,118,0.08)` | Subtler background ambient on hero sections |

---

## Typography

| Property | Value |
|---|---|
| Primary font | `'Space Grotesk'` |
| Fallback font | `'Inter'`, `sans-serif` |
| Heading weight | `700` |
| Body weight | `400` |
| Heading color | `var(--text)` (`#e8f5e9`) |
| Body color | `var(--text-muted)` (`#7a9e8a`) |

---

## Glass Card Pattern

```css
.glass-card {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 255, 128, 0.12);
  border-radius: 12px;
}
```

---

## Button Patterns

### Primary (gradient green)
```css
.btn-primary {
  background: linear-gradient(135deg, #00c853, #00e676);
  color: #e8f5e9;
  font-weight: 700;
  border-radius: 9999px;
  padding: 10px 24px;
  border: none;
}
.btn-primary:hover {
  box-shadow: 0 0 20px rgba(0,230,118,0.3);
}
```

### Danger (stop/delete)
```css
.btn-danger {
  background: rgba(255, 109, 0, 0.15);
  color: #ff6d00;
  border: 1px solid rgba(255, 109, 0, 0.3);
  border-radius: 9999px;
  padding: 6px 16px;
}
```

---

## Input Pattern

```css
.input-dark {
  background: rgba(255, 255, 255, 0.03);
  border: none;
  border-bottom: 1px solid rgba(0,255,128,0.2);
  color: #e8f5e9;
  border-radius: 4px 4px 0 0;
  padding: 10px 12px;
  outline: none;
  transition: border-bottom-color 0.2s;
}
.input-dark:focus {
  border-bottom: 2px solid #00e676;
}
.input-dark::placeholder {
  color: #7a9e8a;
}
```

---

## Chat Bubble Patterns

### User bubble
```css
.bubble-user {
  background: #00c853;
  color: #e8f5e9;
  font-weight: 700;
  border-radius: 9999px;
  padding: 10px 18px;
  align-self: flex-end;
  max-width: 70%;
}
```

### Bot bubble
```css
/* Uses .glass-card pattern with additional padding */
.bubble-bot {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(0, 255, 128, 0.12);
  border-radius: 12px;
  padding: 14px 18px;
  align-self: flex-start;
  max-width: 80%;
  color: #e8f5e9;
}
```

---

## Status Label Colors

| VM Status | Color | Value |
|---|---|---|
| running | `var(--success)` | `#00c853` |
| stopped | `var(--warning)` | `#ff6d00` |
| error | `var(--warning)` | `#ff6d00` |
| creating | `var(--accent)` | `#00e676` |

No badges or chips — plain colored `<span>` text only.

---

## Background Layer

| Element | Value |
|---|---|
| Blob fill color | `#00e676` |
| Blob opacity | `0.04` – `0.06` |
| Blob count | 2–3 per page |
| Floating icon opacity | `0.08` |
| Floating icons | lock, gear, cloud (SVG inline) |
| Icon pointer-events | `none` |
| Icon aria | `aria-hidden="true"` |
