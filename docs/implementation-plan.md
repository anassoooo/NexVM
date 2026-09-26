# NexVM Implementation Plan

## Global Execution Model

Three parallel tracks, synchronized:

```
Database (foundation)
        ↓
Backend (logic + control)
        ↓
Frontend (interaction)
```

Execution is iterative (vertical slices):

```
Auth → VM Control → AI → Analytics
```

**Deployment model:** Single-tenant — one VirtualBox host, one user (or small team). No resource isolation or per-user VM limits required for MVP.

**API versioning:** All backend routes under `/api/v1/` prefix.

---

## Architecture

### System Overview

```
+-------------------+         +---------------------+         +-------------------+
|                   |  HTTPS  |                     |         |                   |
|   Next.js 14      |-------->|   FastAPI Backend    |-------->|   VirtualBox      |
|   (Vercel)        |<--------|   (Render)           |<--------|   (Local Host)    |
|                   |   JSON  |                     |  CLI    |                   |
+-------------------+         +---------------------+         +-------------------+
        |                         |           |
        |                         |           |
        v                         v           v
+-------------------+    +-------------+  +-------------+
|                   |    |             |  |             |
|   Supabase Auth   |    |  Supabase   |  |  Groq API   |
|   (JWT + Session) |    |  Postgres   |  |  (LLM)      |
|                   |    |             |  |             |
+-------------------+    +-------------+  +-------------+
```

### Component Diagrams

**Frontend (Next.js 14 — App Router):**

```
app/
 ├── middleware.ts ──── Auth gate (redirects unauthenticated users)
 │
 ├── (auth)/           Public routes
 │    ├── login/
 │    └── signup/
 │
 ├── dashboard/        Protected routes
 ├── vms/              ───────────────────┐
 ├── ai/                                  │
 └── admin/            Admin-only         │
                                          v
lib/                                  components/
 ├── supabase/                         ├── ui/ (shadcn)
 │    ├── client.ts                    ├── vm-card.tsx
 │    └── server.ts                    ├── vm-list.tsx
 ├── api.ts ────── Backend calls       ├── chat-box.tsx
 └── utils.ts                         └── navbar.tsx
```

**Backend (FastAPI):**

```
Request
  │
  v
┌─────────────────────────────────────────────────────┐
│  Auth Middleware (dependencies.py)                   │
│  Validate JWT → Extract user_id                     │
└──────────────────────┬──────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────┐
│  Route Layer (routes/)                              │
│  HTTP parsing only — no business logic              │
│                                                     │
│  vm.py  │  ai.py  │  analytics.py  │  health.py    │
└──────────────────────┬──────────────────────────────┘
                       │
                       v
┌─────────────────────────────────────────────────────┐
│  Service Layer (services/)                          │
│  All domain logic lives here                        │
│                                                     │
│  vm_service.py  │  ai_service.py  │  analytics.py   │
└──────────┬──────────────┬───────────────────────────┘
           │              │
           v              v
┌──────────────┐  ┌──────────────┐
│ vbox_wrapper │  │  AI Validator │
│ (subprocess) │  │  (Pydantic)   │
└──────┬───────┘  └──────┬───────┘
       │                 │
       v                 v
  VBoxManage         Groq API
```

### Data Flow Diagrams

**1. Authentication Flow:**

```
User                    Frontend              Supabase Auth         Backend
 │                         │                      │                    │
 │── email + password ────>│                      │                    │
 │                         │── signInWithPassword >│                    │
 │                         │<── JWT + session ─────│                    │
 │                         │                      │                    │
 │                         │── GET /api/v1/vm ────────────────────────>│
 │                         │   Authorization: Bearer <JWT>             │
 │                         │                      │                    │
 │                         │                      │<── verify JWT ─────│
 │                         │                      │── user_id ────────>│
 │                         │                      │                    │
 │                         │<── VM list (JSON) ───────────────────────│
 │<── render dashboard ────│                      │                    │
```

**2. VM CRUD Flow (Example: Start VM):**

```
User        Frontend           Backend              VBox Wrapper      Supabase DB
 │              │                  │                      │                │
 │── click ────>│                  │                      │                │
 │  "Start"     │                  │                      │                │
 │              │── POST           │                      │                │
 │              │   /api/v1/vm/    │                      │                │
 │              │   start ────────>│                      │                │
 │              │                  │                      │                │
 │              │                  │── UPDATE vms         │                │
 │              │                  │   status='starting' ─────────────────>│
 │              │                  │                      │                │
 │              │                  │── VBoxManage         │                │
 │              │                  │   startvm ──────────>│                │
 │              │                  │                      │── execute      │
 │              │                  │<── exit code ────────│                │
 │              │                  │                      │                │
 │              │                  │── UPDATE vms         │                │
 │              │                  │   status='running'   │                │
 │              │                  │   (or 'error') ──────────────────────>│
 │              │                  │                      │                │
 │              │                  │── INSERT logs ───────────────────────>│
 │              │                  │                      │                │
 │              │<── 200 OK ───────│                      │                │
 │<── update ───│                  │                      │                │
 │   UI state   │                  │                      │                │
```

**3. AI Command Flow:**

```
User        Frontend           Backend            AI Validator     Groq API     VM Service
 │              │                  │                   │               │             │
 │── "create   │                  │                   │               │             │
 │   a ubuntu  │                  │                   │               │             │
 │   vm with   │                  │                   │               │             │
 │   4GB RAM" ─>│                  │                   │               │             │
 │              │── POST           │                   │               │             │
 │              │   /api/v1/ai/    │                   │               │             │
 │              │   command ──────>│                   │               │             │
 │              │                  │── prompt ─────────────────────────>│             │
 │              │                  │<── JSON response ─────────────────│             │
 │              │                  │   {                │               │             │
 │              │                  │     "action":      │               │             │
 │              │                  │       "create_vm", │               │             │
 │              │                  │     "name":        │               │             │
 │              │                  │       "ubuntu-vm", │               │             │
 │              │                  │     "os": "Ubuntu",│               │             │
 │              │                  │     "ram": 4096    │               │             │
 │              │                  │   }                │               │             │
 │              │                  │                    │               │             │
 │              │                  │── validate ───────>│               │             │
 │              │                  │<── valid ──────────│               │             │
 │              │                  │                    │               │             │
 │              │                  │── create_vm(name, os, ram) ──────────────────────>│
 │              │                  │<── VM created ───────────────────────────────────│
 │              │                  │                    │               │             │
 │              │                  │── log to ai_usage + logs ──────────────> DB      │
 │              │                  │                    │               │             │
 │              │<── response ─────│                    │               │             │
 │<── display ──│                  │                    │               │             │
 │   result     │                  │                    │               │             │
```

### Database Schema (ER Diagram)

```
auth.users
    ├── id (uuid, pk)
    ├── email
    └── ...
         │
         │ 1:1
         v
    profiles
    ├── id (uuid, pk, fk → auth.users)
    ├── is_admin (boolean)
    └── created_at
         │
         │ 1:N
         v
    vms
    ├── id (uuid, pk)
    ├── user_id (uuid, fk → auth.users)
    ├── name (text)
    ├── os (text)
    ├── ram (int)
    ├── status (text)
    ├── error_message (text, nullable)
    ├── created_at
    └── updated_at
         │
    auth.users ──── 1:N ───> logs
                              ├── id (uuid, pk)
                              ├── user_id (uuid, fk)
                              ├── action (text)
                              ├── target (text)
                              ├── status (text)
                              ├── message (text)
                              └── created_at

    auth.users ──── 1:N ───> ai_usage
                              ├── id (uuid, pk)
                              ├── user_id (uuid, fk)
                              ├── prompt (text)
                              ├── response (text)
                              ├── tokens (int)
                              └── created_at
```

### VM State Machine

```
                    ┌─────────┐
      ┌────────────>│ stopped │<────────────┐
      │             └────┬────┘             │
      │                  │                  │
      │            start │                  │
      │                  v                  │
      │           ┌──────────┐              │
      │           │ starting │──── fail ──> error
      │           └────┬─────┘              │
      │                │                    │
      │          success│                   │ retry
      │                v                    │ (start)
      │           ┌─────────┐              │
      │     stop  │ running │              │
      │    ┌──────┤         │              │
      │    │      └─────────┘              │
      │    v                               │
      │ ┌──────────┐                       │
      └─│ stopping │──── fail ────────────>│
        └──────────┘                ┌──────┴──────┐
                                    │    error    │
                                    │             │
                                    └─────────────┘
```

### Security Boundaries

```
┌──────────────────────────────────────────────────────────────┐
│  UNTRUSTED ZONE                                              │
│  User Browser                                                │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTPS + JWT
                           v
┌──────────────────────────────────────────────────────────────┐
│  AUTH BOUNDARY                                               │
│  middleware.ts (frontend) + Auth Middleware (backend)         │
└──────────────────────────┬───────────────────────────────────┘
                           │ Authenticated user_id
                           v
┌──────────────────────────────────────────────────────────────┐
│  APPLICATION ZONE                                            │
│  Route Layer → Service Layer                                 │
└──────────────────────────┬───────────────────────────────────┘
                           │ Validated commands only
                           v
┌──────────────────────────────────────────────────────────────┐
│  AI VALIDATION BOUNDARY                                      │
│  AI Validator (Pydantic schemas, action whitelist)           │
│  NO raw AI output passes this boundary                      │
└──────────────────────────┬───────────────────────────────────┘
                           │ Hardcoded command map
                           v
┌──────────────────────────────────────────────────────────────┐
│  EXECUTION ZONE                                              │
│  VBox Wrapper → VBoxManage CLI (subprocess with timeout)     │
└──────────────────────────────────────────────────────────────┘
```

---

## 1. Database Implementation Plan (Supabase)

### Objective

Create a minimal, structured, query-efficient schema that supports:

- Auth + profiles
- VM tracking with lifecycle states
- AI usage tracking
- Logs / analytics

### STEP 1 — Project Setup

- Create Supabase project
- Enable:
  - Email/password auth
- Get:
  - URL
  - anon key
  - service role key

### STEP 2 — Schema Design (MVP)

**Table: profiles**

| Column     | Type      | Default             | Notes                    |
|------------|-----------|---------------------|--------------------------|
| id         | uuid      | —                   | pk, fk → auth.users      |
| is_admin   | boolean   | false               | admin role flag           |
| created_at | timestamp | now()               |                          |

**Table: vms**

| Column        | Type      | Default              | Notes                                                |
|---------------|-----------|----------------------|------------------------------------------------------|
| id            | uuid      | gen_random_uuid()    | pk                                                   |
| user_id       | uuid      | —                    | fk → auth.users                                      |
| name          | text      | —                    | required                                             |
| os            | text      | —                    | required                                             |
| ram           | int       | —                    | in MB, range 512–16384                               |
| status        | text      | 'stopped'            | stopped, starting, running, stopping, error          |
| error_message | text      | null                 | populated when status = error                        |
| created_at    | timestamp | now()                |                                                      |
| updated_at    | timestamp | now()                | updated on every state change                        |

**Table: logs**

| Column     | Type      | Default           | Notes               |
|------------|-----------|-------------------|----------------------|
| id         | uuid      | gen_random_uuid() |                      |
| user_id    | uuid      | —                 | fk → auth.users      |
| action     | text      | —                 |                      |
| target     | text      | —                 | vm id or "ai"        |
| status     | text      | —                 | success/fail         |
| message    | text      | —                 |                      |
| created_at | timestamp | now()             |                      |

**Table: ai_usage**

| Column     | Type      | Default           | Notes               |
|------------|-----------|-------------------|----------------------|
| id         | uuid      | gen_random_uuid() |                      |
| user_id    | uuid      | —                 | fk → auth.users      |
| prompt     | text      | —                 |                      |
| response   | text      | —                 |                      |
| tokens     | int       | —                 |                      |
| created_at | timestamp | now()             |                      |

### STEP 3 — Supabase Trigger

Auto-create profile on user signup:

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, is_admin)
  VALUES (NEW.id, false);
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

### STEP 4 — Security (RLS)

Enable Row Level Security on all tables.

**Policies for `vms`:**

```sql
-- Users see only their own VMs
CREATE POLICY "Users access own VMs" ON vms
  FOR ALL USING (auth.uid() = user_id);

-- Admins access everything
CREATE POLICY "Admins access all VMs" ON vms
  FOR ALL USING (
    EXISTS (SELECT 1 FROM profiles WHERE id = auth.uid() AND is_admin = true)
  );
```

Same pattern for `logs` and `ai_usage`:
- User policy: `auth.uid() = user_id`
- Admin policy: `profiles.is_admin = true`

### STEP 5 — Indexing

| Table    | Column   | Index Type |
|----------|----------|------------|
| vms      | user_id  | btree      |
| logs     | user_id  | btree      |
| ai_usage | user_id  | btree      |

### STEP 6 — Test Data Flow

- Insert dummy VM via Supabase SQL editor
- Query from backend to validate connection

---

## 2. Backend Implementation Plan (FastAPI)

### Objective

Build a secure execution engine for:

- VM control (VirtualBox)
- AI command processing
- Analytics tracking

### STEP 1 — Project Structure

```
backend/
 ├── app/
 │    ├── __init__.py
 │    ├── main.py              # FastAPI app, CORS, lifespan
 │    ├── config.py            # Settings via pydantic-settings
 │    ├── dependencies.py      # Auth dependency, Supabase client
 │    ├── routes/
 │    │    ├── vm.py
 │    │    ├── ai.py
 │    │    ├── analytics.py
 │    │    └── health.py
 │    ├── services/
 │    │    ├── vm_service.py
 │    │    ├── ai_service.py
 │    │    ├── analytics_service.py
 │    │    └── vbox_wrapper.py
 │    ├── models/
 │    │    ├── schemas.py      # Pydantic request/response models
 │    │    └── enums.py        # VMStatus, ActionType enums
 │    └── utils/
 │         └── logger.py
 ├── tests/
 │    ├── test_vm_service.py
 │    ├── test_ai_validator.py
 │    └── test_auth.py
 ├── requirements.txt
 ├── Dockerfile
 └── .env.example
```

### STEP 2 — Configuration

**Environment variables (`config.py` via pydantic-settings):**

| Variable             | Description                    | Default      |
|----------------------|--------------------------------|--------------|
| SUPABASE_URL         | Supabase project URL           | —            |
| SUPABASE_SECRET_KEY  | Supabase server secret key     | —            |
| GROQ_API_KEY         | Groq API key                   | —            |
| FRONTEND_URL         | Vercel frontend URL for CORS   | —            |
| VBOXMANAGE_PATH      | Path to VBoxManage binary      | VBoxManage   |

### STEP 3 — Core Modules

#### 1. Auth Middleware (`dependencies.py`)

- Validate Supabase JWT from `Authorization: Bearer <token>` header
- Extract `user_id` from token claims
- FastAPI `Depends()` for route injection

#### 2. VM Service (CRITICAL)

Functions:

- `create_vm(name, ram, os)` → creates VirtualBox VM + inserts DB record
- `start_vm(vm_id)` → sets status to `starting`, runs VBoxManage, sets `running` or `error`
- `stop_vm(vm_id)` → sets status to `stopping`, runs VBoxManage, sets `stopped` or `error`
- `delete_vm(vm_id)` → runs VBoxManage unregistervm, deletes DB record
- `get_vm_status(vm_id)` → returns current VM status from DB
- `list_vms(user_id)` → returns all VMs for user

**State transition rules:**

```
stopped  → starting → running
running  → stopping → stopped
any      → error (on VBoxManage failure)
error    → starting (retry allowed)
```

#### 3. VirtualBox Wrapper (`vbox_wrapper.py`)

Encapsulate ALL system calls with timeout and error handling:

```python
import subprocess

def run_vbox_command(cmd: list, timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, capture_output=True, text=True, timeout=timeout
    )
```

**Hardcoded command map (constitution §5.1):**

| Action    | VBoxManage Command                                          |
|-----------|-------------------------------------------------------------|
| create    | `VBoxManage createvm --name <name> --register`              |
| start     | `VBoxManage startvm <name> --type headless`                 |
| stop      | `VBoxManage controlvm <name> poweroff`                      |
| delete    | `VBoxManage unregistervm <name> --delete`                   |
| status    | `VBoxManage showvminfo <name> --machinereadable`            |

No other VBoxManage subcommands are permitted at runtime.

#### 4. AI Service (Groq)

Pipeline:

```
User Prompt
   ↓
Groq API (JSON-only output, no streaming)
   ↓
Structured JSON
   ↓
Validator
   ↓
VM Service
```

#### 5. AI Validator

**Per-action schemas:**

```
create_vm: { action: "create_vm", name: str, os: str, ram: int (512-16384) }
start_vm:  { action: "start_vm",  vm_id: uuid }
stop_vm:   { action: "stop_vm",   vm_id: uuid }
delete_vm: { action: "delete_vm", vm_id: uuid }
```

**Allowed actions (whitelist):**

- `create_vm`
- `start_vm`
- `stop_vm`
- `delete_vm`

**Reject:**

- Unknown actions (anything outside the whitelist)
- Missing required fields
- Invalid field types or out-of-range values
- Non-JSON AI responses (treat as failure)

#### 6. Analytics Service

Track:

- VM events (create/start/stop/delete with outcome)
- AI usage (prompt, response, tokens, success/failure)
- Errors (all failures with context)

### STEP 4 — API Layer

**CORS configuration in `main.py`:**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

**Endpoints:**

| Method | Endpoint              | Description              | Auth |
|--------|-----------------------|--------------------------|------|
| GET    | /api/v1/health        | Health + VBox check      | No   |
| POST   | /api/v1/vm/create     | Create a new VM          | Yes  |
| POST   | /api/v1/vm/start      | Start a VM               | Yes  |
| POST   | /api/v1/vm/status     | Get VM status            | Yes  |
| POST   | /api/v1/vm/stop       | Stop a VM                | Yes  |
| POST   | /api/v1/vm/delete     | Delete a VM              | Yes  |
| GET    | /api/v1/vm            | List user's VMs          | Yes  |
| POST   | /api/v1/ai/command    | AI prompt → VM action    | Yes  |
| GET    | /api/v1/analytics     | Dashboard metrics        | Yes  |

**Rate limiting:** `POST /api/v1/ai/command` — 10 requests/min per user.

### STEP 5 — Execution Flow

```
Request → Auth Middleware → Route Handler → Service Layer → Validator → VBox Wrapper → DB Write → Response
```

Constitution §4.1: No skipping layers. Routes handle HTTP only; all logic in services.

### STEP 6 — Logging System

On every action, insert into `logs` table:

- `user_id` — from JWT
- `action` — operation performed
- `target` — VM id or "ai"
- `status` — success/fail
- `message` — details or error context

**Rule (constitution §12.1):** Log BEFORE returning response, so failures during serialization don't suppress entries.

### STEP 7 — Error Handling

- Wrap all subprocess calls in try/except
- On `VBoxManage` failure: set VM status to `error`, store stderr in `error_message`, log to `logs` table, return HTTP 500 with actionable message
- On `TimeoutExpired`: same as above with "Command timed out" message
- Return clean JSON error responses: `{ "detail": "..." }`
- Log all failures with context: command attempted, exit code, stderr

### STEP 8 — Dependencies

**requirements.txt:**

```
fastapi
uvicorn[standard]
supabase
httpx
python-jose[cryptography]
pydantic-settings
groq
```

**Dev dependencies:**

```
pytest
pytest-asyncio
```

### STEP 9 — Deployment (Render)

**Dockerfile:**

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Environment variables on Render:**

- `SUPABASE_URL`
- `SUPABASE_SECRET_KEY`
- `GROQ_API_KEY`
- `FRONTEND_URL`
- `VBOXMANAGE_PATH`

---

## 3. Frontend Implementation Plan (Next.js 14)

### Objective

Build a clean, usable UI for:

- VM management
- AI interaction
- Admin analytics

**Stack:** Next.js 14 (App Router), Tailwind CSS, shadcn/ui, Zod, Supabase SSR

### STEP 1 — Project Structure

```
frontend/
 ├── app/
 │    ├── layout.tsx              # Root layout, providers
 │    ├── page.tsx                # Landing / redirect
 │    ├── (auth)/
 │    │    ├── login/page.tsx
 │    │    └── signup/page.tsx
 │    ├── dashboard/
 │    │    └── page.tsx
 │    ├── vms/
 │    │    └── page.tsx
 │    ├── ai/
 │    │    └── page.tsx
 │    └── admin/
 │         └── page.tsx
 ├── components/
 │    ├── ui/                     # shadcn/ui components
 │    ├── vm-card.tsx
 │    ├── vm-list.tsx
 │    ├── chat-box.tsx
 │    └── navbar.tsx
 ├── lib/
 │    ├── supabase/
 │    │    ├── client.ts          # Browser Supabase client
 │    │    └── server.ts          # Server Supabase client
 │    ├── api.ts                  # Backend API wrapper
 │    └── utils.ts
 ├── hooks/
 │    └── use-auth.ts
 ├── types/
 │    └── index.ts                # VM, Log, AIUsage TypeScript types
 ├── middleware.ts                 # Auth route protection
 ├── .env.example
 ├── tailwind.config.ts
 └── package.json
```

### STEP 2 — Auth Flow

- Supabase client (`@supabase/ssr` for App Router)
- Login / Signup pages under `(auth)` route group
- `middleware.ts`: redirect unauthenticated users to `/login` for all routes except `(auth)/*`
- Store session via Supabase cookie-based auth

### STEP 3 — API Layer

Centralized API wrapper (`lib/api.ts`):

- Inject `Authorization: Bearer <token>` on every request
- Base URL from `NEXT_PUBLIC_API_URL` env var
- Typed responses matching backend schemas
- Error parsing: extract `detail` from error responses, surface to UI

### STEP 4 — Form Validation

Use `zod` for client-side validation:

- VM creation: `name` (required, 1-50 chars), `os` (required), `ram` (required, 512-16384)

### STEP 5 — Pages

#### 1. Dashboard (`/dashboard`)

- Summary: total VMs, running count, stopped count, error count

#### 2. VM Page (`/vms`)

- List VMs with status badges (color-coded per state)
- Action buttons: Create, Start, Stop, Delete
- Buttons disabled during transitional states (`starting`, `stopping`)
- Create VM modal/form with validation

#### 3. AI Assistant Page (`/ai`)

- Chat UI
- Input → send prompt to `POST /api/v1/ai/command`
- Display AI response + executed action result

#### 4. Admin Dashboard (`/admin`)

- Route guard: check `profiles.is_admin`, redirect non-admins
- Total users
- Total VMs (all users)
- Total AI requests

### STEP 6 — Components

- `VMCard` — displays VM info + status badge + action buttons
- `VMList` — grid/list of VMCards with loading skeleton
- `ChatBox` — message list + input form
- `Navbar` — navigation + user menu + logout

### STEP 7 — State Management

- `useState` + `useEffect` for local state
- No Redux (too heavy for MVP)
- Refetch data after mutations via API wrapper

### STEP 8 — UX Essentials

- Loading skeletons on data fetch
- Toast notifications for success/error (shadcn/ui toast)
- Disabled buttons during transitional VM states
- Empty states for no VMs / no AI history

### STEP 9 — Dependencies

```
next@14
react@18
@supabase/supabase-js
@supabase/ssr
tailwindcss
zod
lucide-react
```

Plus shadcn/ui components (installed via CLI).

### STEP 10 — Deployment (Vercel)

- Connect repo
- Environment variables:

| Variable              | Description              |
|-----------------------|--------------------------|
| NEXT_PUBLIC_API_URL   | Backend API base URL     |
| NEXT_PUBLIC_SUPABASE_URL | Supabase project URL  |
| NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY | Supabase publishable key |

---

## Integration Plan (CRITICAL)

### Phase Order

1. **Auth works** — login/signup, JWT validation, profile auto-creation
2. **VM works (manual)** — create/start/stop/delete via UI buttons
3. **AI works** — prompt → validated JSON → VM action
4. **Analytics works** — logs visible in admin dashboard

### Environment Variable Checklist

| Service   | Variables                                                    |
|-----------|--------------------------------------------------------------|
| Supabase  | URL, publishable key, secret key                              |
| Render    | SUPABASE_URL, SUPABASE_SECRET_KEY, GROQ_API_KEY, FRONTEND_URL, VBOXMANAGE_PATH |
| Vercel    | NEXT_PUBLIC_API_URL, NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY |

### CORS

Backend (`main.py`) must whitelist the Vercel frontend URL via `FRONTEND_URL` env var.

### Local Development Setup

1. **Supabase:** Create project, run SQL migrations, copy keys to `.env`
2. **Backend:** `cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload`
3. **Frontend:** `cd frontend && npm install && npm run dev`
4. **VirtualBox:** Verify `VBoxManage list vms` works on local machine

---

## Testing Strategy (Minimal — Critical Paths)

### Backend (pytest)

| Test file               | Coverage                                                          |
|-------------------------|-------------------------------------------------------------------|
| `test_ai_validator.py`  | Valid/invalid JSON, unknown actions, missing fields, OOB RAM      |
| `test_vm_service.py`    | Mock VBoxManage subprocess, verify state transitions + DB writes  |
| `test_auth.py`          | Valid JWT passes, expired JWT rejected, missing JWT rejected      |

### Frontend (Manual for MVP)

- [ ] Auth flow: login → dashboard → logout → redirect to login
- [ ] VM CRUD: create → appears in list → start → status updates → stop → delete
- [ ] AI prompt: type command → response displayed → action executed
- [ ] Admin: non-admin user cannot access `/admin`

---

## Risk Mitigation

### 1. VirtualBox issues

Test FIRST:

```bash
VBoxManage list vms
VBoxManage --version
```

### 2. AI instability

Force:

- JSON-only output via system prompt
- Hard validation with per-action Pydantic schemas
- Reject non-JSON responses as failures

### 3. Time pressure

Rule: If blocked → simplify immediately.

### 4. Subprocess failures

- 30-second timeout on all VBoxManage calls
- Fail-and-flag: set VM to `error` state with message, log, return HTTP error

---

## Clarifications

### Session 2026-04-04

- Q: Which VM lifecycle model should the system use? → A: Intermediate states — `stopped`, `starting`, `running`, `stopping`, `error`
- Q: What scope should the AI command system have? → A: CRUD only — `create_vm`, `start_vm`, `stop_vm`, `delete_vm`
- Q: How should the backend handle VBoxManage failures? → A: Fail and flag — set VM status to `error`, log failure details, return HTTP error to client
- Q: How should admin roles be identified? → A: Profile flag — `profiles` table with `is_admin` boolean, referenced in RLS policies
- Q: What is the deployment model — single-tenant or multi-tenant? → A: Single-tenant — one VirtualBox host, one user/team, no resource isolation for MVP
