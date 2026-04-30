# Implementation Checklist: spec 005 — Dark Cyberpunk UI

## Pre-Implementation Gate

- [ ] Branch `005-cyberpunk-ui` created from clean base
- [ ] `npm run dev` starts without errors on base branch
- [ ] All existing pages load and function correctly before any changes
- [ ] `tsc --noEmit` passes with zero errors on base branch

## Token Foundation (T002–T003)

- [ ] `:root` CSS vars defined in `globals.css`
- [ ] Tailwind config extended with `cyber-*` color namespace
- [ ] `backdropBlur.glass` and `boxShadow.glow` added to tailwind config
- [ ] `Space Grotesk` loaded via `next/font/google` in layout
- [ ] `body` background set to `var(--bg)`, color to `var(--text)`

## New Components (T004–T005)

- [ ] `BackgroundLayer` renders fixed div with blobs + 3 SVG icons
- [ ] Icons are `aria-hidden="true"` and `pointer-events: none`
- [ ] `prefers-reduced-motion` disables float animation
- [ ] `GlassCard` applies glass pattern and accepts `className` prop

## Auth Pages (T006–T007)

- [ ] Login/signup background is `#0a0f0d`
- [ ] `<BackgroundLayer />` present
- [ ] Form wrapped in `<GlassCard />`
- [ ] Inputs: no border at rest, green bottom-border on focus
- [ ] Submit button: gradient green pill

## AI Chat (T008–T009)

- [ ] `/ai` is full-screen dark with `<BackgroundLayer />`
- [ ] User bubbles: right-aligned, `#00c853` bg, white bold text, pill shape
- [ ] Bot bubbles: left-aligned glass card, `var(--text)` color
- [ ] Input: dark, green `border-bottom` on focus
- [ ] Send button: gradient green pill

## VM Components (T010–T013)

- [ ] VM card uses `<GlassCard />`
- [ ] Running status: `#00c853` text label (no badge)
- [ ] Stopped/error status: `#ff6d00` text label (no badge)
- [ ] VM card hover: `box-shadow: 0 0 40px rgba(0,230,118,0.15)`
- [ ] Create form: dark inputs, gradient button

## Admin & Nav (T014–T018)

- [ ] Nav: dark bg, `backdrop-filter`, green border-bottom, link hover = accent
- [ ] Logout button: gradient green pill style
- [ ] Admin stat cards: `<GlassCard />` with `#00e676` metric values
- [ ] Admin VM table: dark with green border, hover highlight

## QA Gate (T019–T023)

- [ ] `tsc --noEmit` — zero errors
- [ ] `npm run build` — zero errors
- [ ] Visual smoke test all pages (see quickstart.md)
- [ ] Regression: login, logout, VM CRUD via AI, admin metrics all work
- [ ] Accessibility spot-check passed (contrast ratios per research.md)
