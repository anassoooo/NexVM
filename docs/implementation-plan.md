# myVMS Implementation Plan

## 🧠 Global Execution Model

You will build 3 parallel tracks, but synchronized:

```
Database (foundation)
        ↓
Backend (logic + control)
        ↓
Frontend (interaction)
```

But execution is iterative (vertical slices):

```
Auth → VM Control → AI → Analytics
```

**Deployment model:** Single-tenant — one VirtualBox host, one user (or small team). No resource isolation or per-user VM limits required for MVP.

---

## 🧱 1. Database Implementation Plan (Supabase)

### 🎯 Objective

Create a minimal, structured, query-efficient schema that supports:

- Auth
- VM tracking
- AI usage
- Logs / analytics

### 📌 STEP 1 — Project Setup

- Create Supabase project
- Enable:
  - Email/password auth
- Get:
  - URL
  - anon key
  - service role key

### 📌 STEP 2 — Schema Design (MVP)

**Table: profiles**

| Column     | Type      | Notes                    |
|------------|-----------|--------------------------|
| id         | uuid      | pk, fk → auth.users      |
| is_admin   | boolean   | default false             |
| created_at | timestamp |                          |

**Table: vms**

| Column     | Type      | Notes               |
|------------|-----------|----------------------|
| id         | uuid      | pk                   |
| user_id    | uuid      | fk → auth.users      |
| name       | text      |                      |
| os         | text      |                      |
| ram        | int       |                      |
| status     | text      | stopped, starting, running, stopping, error |
| created_at | timestamp |                      |

**Table: logs**

| Column     | Type      | Notes               |
|------------|-----------|----------------------|
| id         | uuid      |                      |
| user_id    | uuid      |                      |
| action     | text      |                      |
| target     | text      | vm id or ai          |
| status     | text      | success/fail         |
| message    | text      |                      |
| created_at | timestamp |                      |

**Table: ai_usage**

| Column     | Type      | Notes               |
|------------|-----------|----------------------|
| id         | uuid      |                      |
| user_id    | uuid      |                      |
| prompt     | text      |                      |
| response   | text      |                      |
| tokens     | int       |                      |
| created_at | timestamp |                      |

### 📌 STEP 3 — Security (IMPORTANT)

- Enable Row Level Security (RLS)
- Policies:
  - Users can only access their own VMs
  - Admin (determined by `profiles.is_admin = true`) can access everything

### 📌 STEP 4 — Indexing

Add indexes:

- `user_id` on `vms`
- `user_id` on `logs`
- `user_id` on `ai_usage`

### 📌 STEP 5 — Test Data Flow

- Insert dummy VM
- Query from backend later

---

## 🧱 2. Backend Implementation Plan (FastAPI)

### 🎯 Objective

Build a secure execution engine for:

- VM control (VirtualBox)
- AI command processing
- Analytics tracking

### 📌 STEP 1 — Project Structure

```
backend/
 ├── app/
 │    ├── main.py
 │    ├── routes/
 │    ├── services/
 │    ├── core/
 │    ├── models/
 │    ├── utils/
```

### 📌 STEP 2 — Core Modules

#### 1. Auth Middleware

- Validate Supabase JWT
- Extract user_id

#### 2. VM Service (CRITICAL)

Functions:

- `create_vm(name, ram, os)`
- `start_vm(vm_id)`
- `stop_vm(vm_id)`
- `delete_vm(vm_id)`
- `list_vms(user_id)`

#### 3. VirtualBox Wrapper

Encapsulate ALL system calls:

```python
def run_vbox_command(cmd: list):
    subprocess.run(cmd, capture_output=True)
```

Example commands:

- `VBoxManage createvm --name <name>`
- `VBoxManage startvm <name>`
- `VBoxManage controlvm <name> poweroff`

#### 4. AI Service (Groq)

Pipeline:

```
User Prompt
   ↓
Groq API
   ↓
Structured JSON
   ↓
Validator
   ↓
VM Service
```

#### 5. AI Validator

Strict schema:

```json
{
  "action": "create_vm",
  "name": "string",
  "ram": "int"
}
```

Allowed actions (whitelist):

- `create_vm`
- `start_vm`
- `stop_vm`
- `delete_vm`

Reject:

- Unknown actions (anything outside the whitelist above)
- Missing fields

#### 6. Analytics Service

Track:

- VM events
- AI usage
- Errors

### 📌 STEP 3 — API Layer

**VM Endpoints**

- `POST /vm/create`
- `POST /vm/start`
- `POST /vm/status`
- `POST /vm/stop`
- `POST /vm/delete`
- `GET /vm`

**AI Endpoint**

- `POST /ai/command`

**Analytics Endpoint**

- `GET /analytics`

### 📌 STEP 4 — Execution Flow

```
Request → Auth → Route → Service → Validator → Executor → DB → Response
```

### 📌 STEP 5 — Logging System

On every action, insert into `logs`:

- user_id
- action
- status
- message

### 📌 STEP 6 — Error Handling

- Wrap all subprocess calls
- On VBoxManage failure: set VM status to `error`, store failure message in `logs` table, return HTTP error to client
- Return clean errors with actionable messages
- Log all failures with context (command attempted, exit code, stderr)

### 📌 STEP 7 — Deployment (Render)

- Dockerize OR simple deploy
- Add env vars:
  - Supabase keys
  - Groq API key

---

## 🧱 3. Frontend Implementation Plan (Next.js 14)

### 🎯 Objective

Build a clean, usable UI for:

- VM management
- AI interaction
- Admin analytics

### 📌 STEP 1 — Project Structure

```
frontend/
 ├── app/
 ├── components/
 ├── lib/
 ├── services/
```

### 📌 STEP 2 — Auth Flow

- Supabase client
- Login / Signup pages
- Store session

### 📌 STEP 3 — API Layer

Create wrapper:

```js
fetch('/api/vm')
fetch('/api/ai/command')
```

### 📌 STEP 4 — Pages

#### 1. Dashboard

- Summary: # VMs, status

#### 2. VM Page

- List VMs
- Buttons: Create, Start, Stop, Delete

#### 3. AI Assistant Page

- Chat UI
- Input → send prompt
- Display response

#### 4. Admin Dashboard

- Total users
- Total VMs
- Total AI requests

### 📌 STEP 5 — Components

- `VMCard`
- `VMList`
- `ChatBox`
- `Navbar`

### 📌 STEP 6 — State Management

- `useState` + `useEffect`
- No Redux (too heavy)

### 📌 STEP 7 — UX Essentials

- Loading indicators
- Error messages
- Disabled buttons during actions

### 📌 STEP 8 — Deployment (Vercel)

- Connect repo
- Add env:
  - Supabase URL
  - Backend API URL

---

## 🔗 Integration Plan (CRITICAL)

### Phase Order

1. **Auth works** — login/signup
2. **VM works (manual)** — create/start/stop
3. **AI works** — prompt → VM action
4. **Analytics works** — logs visible

---

## ⚠️ Risk Mitigation

### 1. VirtualBox issues

Test FIRST:

```bash
VBoxManage list vms
```

### 2. AI instability

Force:

- JSON-only output
- Hard validation

### 3. Time pressure

Rule: If blocked → simplify immediately

---

## Clarifications

### Session 2026-04-04

- Q: Which VM lifecycle model should the system use? → A: Intermediate states — `stopped`, `starting`, `running`, `stopping`, `error`
- Q: What scope should the AI command system have? → A: CRUD only — `create_vm`, `start_vm`, `stop_vm`, `delete_vm`
- Q: How should the backend handle VBoxManage failures? → A: Fail and flag — set VM status to `error`, log failure details, return HTTP error to client
- Q: How should admin roles be identified? → A: Profile flag — `profiles` table with `is_admin` boolean, referenced in RLS policies
- Q: What is the deployment model — single-tenant or multi-tenant? → A: Single-tenant — one VirtualBox host, one user/team, no resource isolation for MVP

---

## 👥 Final Role Split

### Person A (Backend)

- DB integration
- VM logic
- AI system
- APIs

### Person B (Frontend)

- Auth UI
- Dashboard
- AI chat
- API integration
