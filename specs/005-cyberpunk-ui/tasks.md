# Tasks: Dark Cyberpunk UI Redesign

**Feature Branch**: `005-cyberpunk-ui`
**Depends on**: `004-analytics` complete — all pages stable
**Source**: [spec.md](spec.md), [plan.md](plan.md)

---

## Phase 1: Design Tokens & Foundation

- [ ] T001 Create branch `005-cyberpunk-ui` from `004-analytics` (or main after merge).
  Verify `npm run dev` starts without errors and all existing pages load.

- [ ] T002 Update `frontend/app/globals.css`:
  - Load `Space Grotesk` via `next/font/google` in `layout.tsx` (or `@import` in CSS).
  - Define `:root` CSS custom properties:
    `--bg:#0a0f0d`, `--surface:rgba(255,255,255,0.04)`, `--border:rgba(0,255,128,0.12)`,
    `--accent:#00e676`, `--success:#00c853`, `--warning:#ff6d00`,
    `--text-muted:#7a9e8a`, `--text:#e8f5e9`.
  - Set `body { background: var(--bg); color: var(--text); font-family: 'Space Grotesk', ... }`.

- [ ] T003 Update `frontend/tailwind.config.js`:
  Extend `theme.colors` with `bg`, `surface`, `accent`, `success`, `warning`, `muted`, `text-primary`
  mapped to the CSS var values. Extend `backdropBlur` with `glass: '16px'`.

- [ ] T004 Create `frontend/components/background-layer.tsx` (`"use client"`):
  Fixed full-screen `<div>` behind content. Contains:
  - 2–3 SVG radial gradient blobs (`#00e676` at opacity 0.04–0.06).
  - 3 floating SVG icons (lock, gear, cloud) at `opacity: 0.08`, `aria-hidden="true"`,
    `pointer-events: none`. Respects `prefers-reduced-motion` (disables float animation).

- [ ] T005 Create `frontend/components/glass-card.tsx`:
  Wrapper `<div>` with `background: var(--surface)`, `backdrop-filter: blur(16px)`,
  `border: 1px solid var(--border)`, `border-radius: 12px`. Accepts `className` prop.
  Use this wherever 3+ components need the glass pattern.

---

## Phase 2: Auth Pages

- [ ] T006 Redesign `frontend/app/(auth)/login/page.tsx`:
  - Full-screen dark background with `<BackgroundLayer />`.
  - Centered `<GlassCard>` containing the login form.
  - Heading: `Space Grotesk` bold, `var(--text)`.
  - Inputs: dark background, no border at rest; `border-bottom: 2px solid var(--accent)` on focus.
  - Submit button: gradient `var(--success) → var(--accent)`, pill, bold white.
  - Error text: `var(--warning)`.

- [ ] T007 Redesign `frontend/app/(auth)/signup/page.tsx`:
  Same pattern as T006 — glass card form, dark inputs, gradient button.

---

## Phase 3: AI Chat Interface

- [ ] T008 Redesign `frontend/app/ai/page.tsx`:
  Full-screen dark wrapper. `<BackgroundLayer />` behind content. Chat fills viewport height.

- [ ] T009 Redesign `frontend/components/ai-chat.tsx`:
  - Bot messages: left-aligned `<GlassCard>` bubble, `var(--text)` body text.
  - User messages: right-aligned green pill — `background: var(--success)`, white bold text,
    `border-radius: 9999px`, `padding: 10px 18px`.
  - Input area: dark background, single text input with `border-bottom: 2px solid var(--accent)`
    on focus, send button uses gradient style.
  - Loading indicator: pulsing green dot or `var(--accent)` spinner.

---

## Phase 4: VM Components

- [ ] T010 Redesign `frontend/components/vm-card.tsx`:
  - Use `<GlassCard>` as wrapper.
  - Status label: `var(--success)` for "running", `var(--warning)` for "stopped"/"error".
    Plain text — no badge/chip element.
  - Hover: add `box-shadow: 0 0 40px rgba(0,230,118,0.15)` transition.
  - Action buttons (start/stop/delete): pill-shaped, appropriate color per action.

- [ ] T011 Redesign `frontend/components/vm-list.tsx`:
  Dark container. Empty state message in `var(--text-muted)`.

- [ ] T012 Redesign `frontend/components/vm-create-form.tsx`:
  Glass card form. Dark inputs with green focus border-bottom. Gradient submit button.

- [ ] T013 Redesign `frontend/components/vms-client.tsx` and `frontend/app/vms/page.tsx`:
  Dark page wrapper with `<BackgroundLayer />`.

---

## Phase 5: Admin, Nav & Landing

- [ ] T014 Redesign `frontend/app/layout.tsx` nav:
  - Nav bar: `background: rgba(10,15,13,0.9)`, `backdrop-filter: blur(8px)`,
    `border-bottom: 1px solid var(--border)`.
  - Links: `var(--text-muted)` at rest, `var(--accent)` on hover.
  - Logo "myVMS": bold, `var(--text)`.

- [ ] T015 Update `frontend/app/dashboard/logout-button.tsx`:
  Button: gradient `var(--success) → var(--accent)`, pill, bold white. Match primary button style.

- [ ] T016 Redesign `frontend/app/admin/page.tsx`:
  - Dark page with `<BackgroundLayer />`.
  - Stat cards: `<GlassCard>` with metric value in `var(--accent)` and label in `var(--text-muted)`.
  - Section headings: bold `var(--text)`.

- [ ] T017 Redesign `frontend/app/admin/vms/page.tsx` and `frontend/components/admin-vms-client.tsx`:
  Dark table: `background: var(--surface)`, `border: 1px solid var(--border)`.
  Row hover: subtle `rgba(0,255,128,0.04)` highlight.
  Status column: colored text labels (same rules as T010).

- [ ] T018 Redesign `frontend/app/page.tsx` (landing/root):
  Dark hero section. `<BackgroundLayer />`. CTA button: gradient green pill.
  If unauthenticated root redirects to login, ensure the redirect still works post-restyling.

---

## Phase 6: QA & Polish

- [ ] T019 Run `tsc --noEmit` in `frontend/` — zero TypeScript errors.

- [ ] T020 Run `npm run build` in `frontend/` — zero build errors.

- [ ] T021 Visual smoke test — open each page in browser, verify:
  - `/login`, `/signup` — dark, glass card, gradient button, floating decorations
  - `/ai` — dark chat, green user bubble, glass bot bubble, green input focus
  - `/vms` — glass VM cards, colored text status, glow on hover
  - `/admin` — glass stat cards with `var(--accent)` values
  - `/admin/vms` — dark table with colored status labels

- [ ] T022 Regression check — verify all features still work:
  - Login/logout flow
  - VM create, start, stop, delete via AI chat
  - Admin metrics display correct counts
  - AI greeting on session start

- [ ] T023 Accessibility spot-check: confirm text contrast ratio ≥ 4.5:1 for
  `var(--text)` `#e8f5e9` on `var(--bg)` `#0a0f0d` (ratio: ~15:1 ✅).
  Confirm `var(--text-muted)` `#7a9e8a` on `#0a0f0d` (ratio: ~4.6:1 ✅).

---

## Dependencies

```text
T001 (branch)
  → T002, T003 [P]        (tokens — parallel)
  → T004, T005 [P]        (components — parallel, depend on T002)
  → T006, T007 [P]        (auth pages — parallel, depend on T004/T005)
  → T008, T009 [P]        (AI chat — parallel)
  → T010–T013 [P]         (VM components — parallel)
  → T014–T018 [P]         (admin + nav + landing — parallel)
  → T019, T020 [P]        (type check + build — parallel)
  → T021–T023             (QA — sequential visual checks)
```

**Total: 23 tasks** across 6 phases.
