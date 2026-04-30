# Implementation Plan: Dark Cyberpunk UI Redesign

**Branch**: `005-cyberpunk-ui` | **Date**: 2026-04-20 | **Spec**: [spec.md](spec.md)
**Depends on**: `004-analytics` fully complete — all pages and components stable.

---

## Summary

Pure frontend restyling — zero backend changes. Replace the current light UI with a dark
cyberpunk design system across every page and component. Deliver via CSS tokens, Tailwind
config extensions, and targeted component edits.

---

## Technical Context

**Language/Version**: TypeScript 5.x, Next.js 14, Tailwind CSS
**New Files**:
- `components/background-layer.tsx` — blob + floating icon decorations
- `components/glass-card.tsx` — reusable glassmorphism card wrapper
**Modified Files**: `globals.css`, `tailwind.config.js`, `layout.tsx`, all page/component files
**New Dependencies**: none (`next/font/google` for Space Grotesk — built-in)
**Backend Changes**: none

---

## Constitution Check

| Principle / Rule | Requirement | Status | Notes |
|---|---|---|---|
| §III — Dark Cyberpunk Design System | All tokens, components, pages MUST use design system | **IN SCOPE** | This spec defines and implements §III |
| §V — YAGNI | No new libraries, no animation frameworks | **PASS** | Tailwind + CSS only |
| §VIII — Frontend Conventions | TypeScript strict, App Router, `"use client"` where needed | **PASS** | No new pages; only restyling |
| §XIII — Compliance Gate | Constitution Check present | **PASS** | This table |
| §VI.3 — No Direct DB Writes | No backend/DB interaction | **PASS** | Pure UI spec |

**All gates pass. Proceeding to implementation.**

---

## Project Structure

### Documentation

```text
specs/005-cyberpunk-ui/
├── spec.md              ✅ Feature specification
├── plan.md              ✅ This file
├── research.md          ✅ Design research
├── data-model.md        ✅ Design token definitions
├── quickstart.md        ✅ Visual smoke test guide
├── tasks.md             ✅ Task breakdown
├── contracts/
│   └── design-tokens.md ✅ Token contract
└── checklists/
    ├── requirements.md  ✅ Spec quality gate
    └── implementation.md ✅ Pre/post implementation gate
```

### Source Code Changes

```text
frontend/
├── app/
│   ├── layout.tsx                        MODIFY — dark nav + BackgroundLayer
│   ├── globals.css                       MODIFY — CSS custom properties + font
│   ├── page.tsx                          MODIFY — dark landing page
│   ├── (auth)/
│   │   ├── login/page.tsx                MODIFY — cyberpunk login form
│   │   └── signup/page.tsx              MODIFY — cyberpunk signup form
│   ├── ai/page.tsx                       MODIFY — full-screen dark chat wrapper
│   ├── vms/page.tsx                      MODIFY — dark VMs page
│   ├── admin/page.tsx                    MODIFY — dark admin dashboard
│   ├── admin/vms/page.tsx                MODIFY — dark admin VM table
│   └── dashboard/logout-button.tsx       MODIFY — green gradient button style
├── components/
│   ├── background-layer.tsx              CREATE — blobs + floating icons
│   ├── glass-card.tsx                    CREATE — reusable glass card wrapper
│   ├── ai-chat.tsx                       MODIFY — dark bubbles + green input
│   ├── vm-card.tsx                       MODIFY — glass card + glow + text status
│   ├── vm-list.tsx                       MODIFY — dark list container
│   ├── vm-create-form.tsx                MODIFY — dark form inputs + gradient button
│   ├── admin-vms-client.tsx              MODIFY — dark table
│   └── vms-client.tsx                   MODIFY — dark wrapper
└── tailwind.config.js                    MODIFY — extend theme with design tokens
```

---

## Implementation Phases

### Phase 1 — Design Tokens & Foundation
Establish the token layer first. All subsequent phases depend on this.
- `globals.css` CSS custom properties
- Tailwind config extensions
- Space Grotesk font via `next/font/google`
- `BackgroundLayer` component (blobs + icons)
- `GlassCard` component

### Phase 2 — Auth Pages
- Login page
- Signup page
These are the first impression — highest visible priority.

### Phase 3 — Core Chat Interface
- AI chat page wrapper
- `ai-chat.tsx` component (bubbles + input)
The primary user surface after login.

### Phase 4 — VM Components
- `vm-card.tsx`
- `vm-list.tsx`
- `vm-create-form.tsx`
- `vms-client.tsx`
- `vms/page.tsx`

### Phase 5 — Admin & Layout
- `layout.tsx` nav bar
- `admin/page.tsx` metrics cards
- `admin/vms/page.tsx` table
- `admin-vms-client.tsx`
- `logout-button.tsx`
- `page.tsx` landing

### Phase 6 — QA & Polish
- TypeScript check
- Build check
- Visual smoke test all pages
- Accessibility check (contrast)
- Regression check (all features functional)
