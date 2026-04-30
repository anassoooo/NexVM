# Quickstart: Visual Smoke Test Guide

**Spec**: [spec.md](spec.md)
**Purpose**: Step-by-step visual verification after implementing spec 005.

---

## Prerequisites

1. Backend running: `cd backend && python -m uvicorn app.main:app --reload`
2. Frontend running: `cd frontend && npm run dev`
3. At least one user account in Supabase with 1–2 VMs of mixed status.

---

## Page-by-Page Checklist

### /login

```
[ ] Background is #0a0f0d (near-black with green tint) — no white
[ ] Floating icons visible at low opacity (lock, gear, cloud)
[ ] Login card has frosted glass look (slightly lighter than bg, blurred)
[ ] Card has subtle green border glow
[ ] Email/password inputs are dark with NO visible border at rest
[ ] Clicking into an input shows green bottom border
[ ] "Sign in" button has gradient green (dark → bright) pill shape
[ ] Error message (wrong password) shows in orange/warning color
```

### /signup

```
[ ] Same dark glassmorphism aesthetic as /login
[ ] All input focus states show green bottom border
[ ] Submit button matches gradient green pill style
```

### /ai (after login)

```
[ ] Full-screen dark background with decorations visible
[ ] AI greeting message appears as a left-aligned glass card bubble
[ ] Greeting contains VM status summary (total, running, stopped, error)
[ ] User message appears as RIGHT-ALIGNED green pill with white bold text
[ ] Input field at bottom: dark, green bottom-border on focus
[ ] Send button: green gradient pill
[ ] "list my vms" → AI response in glass card bubble showing VM names
```

### /vms

```
[ ] Dark page background with decorations
[ ] Each VM card has glass surface + subtle green border
[ ] Hovering a VM card triggers green glow
[ ] "running" status label is green text (NOT a badge chip)
[ ] "stopped" status label is orange text (NOT a badge chip)
[ ] Action buttons (start/stop/delete) are pill-shaped
[ ] Empty state (no VMs): gray/muted text message, no crash
```

### /admin (admin account required)

```
[ ] Dark page with decorations
[ ] Stat cards (Total Users, Total VMs, etc.) are glass cards
[ ] Metric values are bright neon green (#00e676)
[ ] Metric labels are muted gray text
```

### /admin/vms (admin account required)

```
[ ] Dark table with subtle green border
[ ] Table row hover: slight green tint highlight
[ ] Status column: colored text labels (no chips)
[ ] Action buttons are pill-shaped
```

### Global Nav (all pages)

```
[ ] Nav bar is dark with bottom green border
[ ] "myVMS" logo is bold white
[ ] Nav links are gray at rest, green on hover
[ ] Logout button is green gradient pill (not a plain gray button)
```

---

## Regression Quick-Checks

| Action | Expected Result |
|---|---|
| Login with valid credentials | Redirects to `/ai` |
| Login with wrong password | Orange error message, stays on `/login` |
| Logout | Redirects to `/login` |
| AI: "create vm test-01 ubuntu 1024" | VM created confirmation in glass card bubble |
| AI: "list my vms" | Named VM list in glass card bubble |
| AI: "stop the running vm" | Correct VM stopped, confirmation in bubble |
| Admin `/admin` loads | Correct user/VM/command counts displayed |
| Non-admin visits `/admin` | Redirected to `/ai` |

---

## Known Non-Issues

- `backdrop-filter` may not apply if the browser dev tools has "paint flashing" enabled.
- On very old Safari (< 9), backdrop-filter falls back gracefully to a semi-opaque panel —
  still readable, just without blur.
