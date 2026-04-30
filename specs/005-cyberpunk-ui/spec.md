# Feature Specification: Dark Cyberpunk UI Redesign

**Feature Branch**: `005-cyberpunk-ui`
**Created**: 2026-04-20
**Status**: In Progress
**Depends on**: `004-analytics` complete — all pages and components stable

---

## Overview

This spec replaces the current plain white/gray UI with a premium dark cyberpunk design system.
No backend changes. No new routes. Pure frontend — CSS tokens, Tailwind config, and component
restyling across every user-facing page and component.

The target mood: futuristic ops dashboard, monitoring feel, premium dark web app.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Login Page (Priority: P1)

A user arrives at `/login` and sees a full-screen dark page with a glassmorphism login card,
neon green accent, floating background decorations, and a gradient sign-in button.

**Acceptance Scenarios**:

1. **Given** any visitor at `/login`, **When** the page loads, **Then** the background is
   `#0a0f0d`, the card has `backdrop-filter: blur(16px)` + green border, and the button
   shows the green gradient.
2. **Given** the user focuses the email input, **When** they type, **Then** a
   `border-bottom: 2px solid #00e676` appears on the field.
3. **Given** a login error, **When** the error shows, **Then** it uses `#ff6d00` (warning color).

---

### User Story 2 — AI Chat Interface (Priority: P1)

A logged-in user opens `/ai` and sees a full-screen dark chat. The AI's opening message
appears in a glass card bubble. The user's messages appear as green pills on the right.

**Acceptance Scenarios**:

1. **Given** the chat loads, **When** the AI greeting appears, **Then** it renders as a
   left-aligned glass card with `backdrop-filter: blur(16px)`.
2. **Given** the user sends a message, **When** it renders, **Then** it appears as a
   right-aligned green pill (`#00c853` background, white bold text).
3. **Given** the user focuses the input, **When** they type, **Then** a green
   `border-bottom` glow appears on the input field.

---

### User Story 3 — VM Card (Priority: P1)

A VM card renders with glassmorphism, a colored status label (no badge), and a glow on hover.

**Acceptance Scenarios**:

1. **Given** a running VM card, **When** it renders, **Then** the status shows as
   `#00c853` text label "running" — no badge or chip element.
2. **Given** a stopped VM card, **When** it renders, **Then** the status shows as
   `#ff6d00` text label "stopped".
3. **Given** the user hovers over a VM card, **When** the hover state activates, **Then**
   a `box-shadow: 0 0 40px rgba(0,230,118,0.15)` glow appears.

---

### User Story 4 — Admin Dashboard (Priority: P2)

An admin visiting `/admin` sees system metrics on dark glass stat cards with neon green
accent values, on a dark background with ambient decorations.

**Acceptance Scenarios**:

1. **Given** an admin loads `/admin`, **When** the metrics render, **Then** each stat card
   uses the glass surface with green border and the metric value is `#00e676`.
2. **Given** the nav bar, **When** any page loads, **Then** the nav shows dark background
   with green-bordered bottom and the logout button uses the green gradient style.

---

### Edge Cases

- **No VMs**: VM list shows an empty state message in `var(--text-muted)` — no crash.
- **Long VM names**: VM card truncates with `text-overflow: ellipsis` — no layout break.
- **Mobile**: All glassmorphism cards remain readable on viewport < 768px (responsive).
- **Reduced motion**: Floating background decorations respect `prefers-reduced-motion`.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The design system tokens (colors, font, blur, glow) MUST be defined as CSS custom
  properties in `globals.css` and as Tailwind config extensions.
- **FR-002**: The font MUST be `Space Grotesk` loaded from Google Fonts, with `Inter` as fallback.
- **FR-003**: Every page background MUST be `#0a0f0d` — no white or light backgrounds remain.
- **FR-004**: All card/panel surfaces MUST use glassmorphism:
  `background: rgba(255,255,255,0.04)`, `backdrop-filter: blur(16px)`,
  `border: 1px solid rgba(0,255,128,0.12)`.
- **FR-005**: Primary buttons MUST use gradient `#00c853 → #00e676`, pill shape, bold white text.
- **FR-006**: User chat bubbles MUST be right-aligned green pills (`#00c853`).
- **FR-007**: Bot chat bubbles MUST be left-aligned glass cards.
- **FR-008**: All text inputs MUST show `border-bottom: 2px solid #00e676` on focus — no full border.
- **FR-009**: VM status indicators MUST be colored text labels — no badges or chips.
  Running = `#00c853`, Stopped/Error = `#ff6d00`.
- **FR-010**: Every full-page background MUST include floating decorative SVG icons
  (lock, gear, cloud) at `opacity: 0.08`, `aria-hidden="true"`, `pointer-events: none`.
- **FR-011**: Background depth MUST be added via SVG blob shapes or CSS radial gradients
  in `#00e676` at very low opacity.
- **FR-012**: VM cards MUST show `box-shadow: 0 0 40px rgba(0,230,118,0.15)` on hover.
- **FR-013**: No existing functionality MUST break — all actions (login, VM CRUD, AI chat,
  admin metrics) MUST continue to work after the redesign.

### Key Entities

- **Design Token**: A CSS custom property defined in `:root` in `globals.css` and mirrored
  in `tailwind.config.js` as a theme extension. Single source of truth for the color system.
- **Glass Card**: Reusable visual pattern — `rgba(255,255,255,0.04)` background,
  `blur(16px)`, `1px solid rgba(0,255,128,0.12)` border.
- **Background Layer**: A fixed/absolute `<div>` rendered in `layout.tsx` behind all content,
  containing blob SVGs + floating icon SVGs.

---

## Success Criteria *(mandatory)*

- **SC-001**: Loading `/login` shows `#0a0f0d` background, glassmorphism card, gradient button,
  and floating decorations — verified visually.
- **SC-002**: Sending a message in `/ai` renders user bubble as right-aligned green pill and
  bot response as left-aligned glass card.
- **SC-003**: VM card hover triggers green glow. Status labels are colored text (not badges).
- **SC-004**: `tsc --noEmit` reports zero TypeScript errors after all changes.
- **SC-005**: `npm run build` completes with no errors.
- **SC-006**: All existing functionality verified: login, logout, VM create/start/stop/delete,
  AI chat commands, admin metrics — no regressions.
- **SC-007**: Lighthouse accessibility score does not drop below 80 (color contrast maintained
  via `#e8f5e9` text on dark backgrounds).

---

## Assumptions

- No new npm packages are required — Tailwind CSS is already installed and configured.
- Google Fonts can be loaded via Next.js `next/font/google` — no CDN link required.
- `backdrop-filter` is supported in all target browsers (Chrome 76+, Firefox 103+, Safari 9+).
- The floating background decorations are purely cosmetic — no accessibility implications
  beyond `aria-hidden="true"`.
- No backend changes are required — this spec is 100% frontend.
- The `dashboard/logout-button.tsx` component will be updated to match the new button style.

---

## Clarifications

### Session 2026-04-20

- Q: Should a shared `GlassCard` component be extracted? → A: Yes, if used in 3+ places —
  extract to `components/glass-card.tsx`. Otherwise inline.
- Q: Should the background decoration layer be a client component? → A: Yes — it uses
  `useEffect` for reduced-motion check. Mark `"use client"`.
- Q: Should Tailwind `darkMode` config be set? → A: No — the entire app is dark-only.
  No light mode toggle. `darkMode` config not needed.
- Q: Should the redesign cover the admin VMs table page? → A: Yes — all user-facing
  pages are in scope (FR-003).
