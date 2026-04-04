# Quickstart: Supabase Auth & Database Setup

**Branch**: `001-supabase-auth-db` | **Date**: 2026-04-04

This guide gets the auth and database layer running locally end-to-end. Complete all steps before starting the VM control or AI features.

---

## Prerequisites

- Supabase account (free tier works)
- Python 3.12
- Node.js 18+
- Git

---

## Step 1 — Create Supabase Project

1. Go to [supabase.com](https://supabase.com) → New Project
2. Choose a project name (e.g., `myvms`) and a strong database password
3. Select a region close to your location
4. Wait for provisioning (~2 minutes)

---

## Step 2 — Configure Supabase Auth Settings

In your Supabase dashboard → **Authentication** → **Settings**:

| Setting | Value |
|---|---|
| JWT expiry | `86400` (24 hours in seconds) |
| Minimum password length | `8` |
| Password strength | Enable "Must contain a number" |
| Rate limit (email sign-in) | `10` per `900` seconds (15 minutes) |
| Enable email confirmations | Optional for MVP — disable to simplify local testing |

---

## Step 3 — Run Database Migration

In your Supabase dashboard → **SQL Editor** → New Query:

Paste the contents of `specs/001-supabase-auth-db/contracts/schema.sql` and click **Run**.

Verify success:
- Tables `profiles`, `vms`, `logs`, `ai_usage` appear in **Table Editor**
- RLS is enabled on all four tables (shield icon visible)
- Trigger `on_auth_user_created` appears under **Database** → **Triggers**

---

## Step 4 — Collect Supabase Keys

In your Supabase dashboard → **Settings** → **API**:

| Key | Where to find |
|---|---|
| `SUPABASE_URL` | Project URL (e.g., `https://xyz.supabase.co`) |
| `SUPABASE_ANON_KEY` | `anon` / `public` key |
| `SUPABASE_SERVICE_KEY` | `service_role` key (keep secret) |
| `SUPABASE_JWT_SECRET` | **Settings** → **API** → JWT Settings → JWT Secret |

---

## Step 5 — Backend Setup

```bash
cd backend
python -m venv .venv
# Activate the virtual environment:
#   Windows: .venv\Scripts\Activate.ps1
#   macOS/Linux: source .venv/bin/activate
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET in .env

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Verify: `GET http://localhost:8000/api/v1/health` returns `{"status": "ok"}`.

---

## Step 6 — Frontend Setup

```bash
cd frontend
cp .env.example .env.local
# Fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_URL=http://localhost:8000

npm install
npm run dev
```

Verify: `http://localhost:3000` redirects to `/login`.

---

## Step 7 — Smoke Test

1. **Register**: Go to `/signup`, create an account with a valid email + password meeting policy (≥8 chars, ≥1 number)
2. **Profile created**: In Supabase SQL Editor, run `SELECT * FROM profiles;` — one row should appear
3. **Dashboard access**: After signup, you should land on `/dashboard`
4. **Logout**: Click logout → redirected to `/login`
5. **Login**: Re-enter credentials → back to `/dashboard`
6. **Protected route**: While logged out, navigate to `/dashboard` → redirected to `/login`
7. **Auth check**: Wait for session to appear expired (or manually expire via Supabase) → protected routes redirect to login

---

## Step 8 — Set Admin User (optional)

To test admin features:

```sql
-- Run in Supabase SQL Editor
UPDATE profiles SET is_admin = true WHERE id = '<your-user-uuid>';
```

Find your UUID: Supabase dashboard → **Authentication** → **Users**.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| `401 Invalid or expired token` from backend | Verify `SUPABASE_JWT_SECRET` in backend `.env` matches Supabase → Settings → API → JWT Secret |
| Profile not created after signup | Check Supabase → Database → Triggers for `on_auth_user_created`; re-run migration if missing |
| CORS error from frontend | Verify `FRONTEND_URL` in backend `.env` matches your frontend origin (`http://localhost:3000`) |
| RLS blocking queries | Confirm you are passing the JWT in `Authorization: Bearer` header; test with Supabase anon key first |
| Rate limit hit immediately | Supabase dashboard → Auth → Rate Limits — confirm the 10/15min setting was saved |
