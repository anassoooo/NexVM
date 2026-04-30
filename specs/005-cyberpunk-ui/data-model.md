# Design Model: Dark Cyberpunk UI

**Spec**: [spec.md](spec.md)
**Note**: No database schema changes. This document describes the frontend design token
system and component hierarchy.

---

## Token Hierarchy

```text
globals.css (:root CSS vars)
  └── tailwind.config.js (theme extensions referencing CSS vars)
        ├── bg, surface, border, accent, success, warning, text-muted, text-primary
        └── backdropBlur: { glass: '16px' }
```

Single source of truth: `globals.css` defines the values. Tailwind reads from the same
CSS variables — no duplication.

---

## Component Hierarchy

```text
layout.tsx
├── BackgroundLayer (fixed, z-0) — blobs + floating icons
└── <nav> (glassmorphism bar)
    ├── logo + nav links
    └── LogoutButton (gradient green pill)

Pages (z-10, relative):
├── /login, /signup
│   └── GlassCard
│       └── form (dark inputs, gradient button)
├── /ai
│   └── AIChat
│       ├── message list
│       │   ├── BotBubble (GlassCard variant)
│       │   └── UserBubble (green pill)
│       └── InputBar (dark input + send button)
├── /vms
│   └── VMList
│       └── VMCard (GlassCard + glow hover)
│           └── status label (colored text)
└── /admin
    ├── StatCard × N (GlassCard + accent value)
    └── /admin/vms
        └── AdminVMsClient (dark table)
```

---

## New Component Contracts

### `BackgroundLayer`

```tsx
// "use client"
// Props: none
// Renders a fixed full-screen div (z-0, pointer-events-none) containing:
//   - 2-3 SVG radial gradient blobs
//   - 3 SVG icons (lock, gear, cloud) aria-hidden, opacity-[0.08]
// Respects prefers-reduced-motion (disables CSS float animation)
```

### `GlassCard`

```tsx
// Props: { children, className? }
// Renders a div with glass-card CSS pattern
// className is merged with base styles (accepts Tailwind overrides)
```

---

## Tailwind Config Extensions (target)

```js
// tailwind.config.js
theme: {
  extend: {
    colors: {
      'cyber-bg':      '#0a0f0d',
      'cyber-surface': 'rgba(255,255,255,0.04)',
      'cyber-accent':  '#00e676',
      'cyber-success': '#00c853',
      'cyber-warning': '#ff6d00',
      'cyber-muted':   '#7a9e8a',
      'cyber-text':    '#e8f5e9',
    },
    backdropBlur: {
      glass: '16px',
    },
    boxShadow: {
      glow: '0 0 40px rgba(0,230,118,0.15)',
      'glow-sm': '0 0 20px rgba(0,230,118,0.10)',
    },
    fontFamily: {
      sans: ['Space Grotesk', 'Inter', 'system-ui', 'sans-serif'],
    },
  },
},
```
