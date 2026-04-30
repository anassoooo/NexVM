# Feature Specification: Supabase Auth & Database Setup

**Feature Branch**: `001-supabase-auth-db`  
**Created**: 2026-04-04  
**Status**: Draft  
**Input**: User description: "Read docs/implementation-plan.md & according to GitHub best practices create the first spec"

---

## Overview

This is the **foundation layer** of myVMS. Before any VM control or AI features can work, the system needs a secure identity and data persistence layer. This spec covers user authentication, automatic profile creation on signup, and the complete database schema that all other features depend on.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Register and Access the System (Priority: P1)

A new user visits the application, creates an account with their email and password, and gains access to the AI chat interface. On successful registration, their profile is automatically created in the background — the user never has to set it up manually.

**Why this priority**: Every other feature in myVMS requires an authenticated identity. Without this, nothing else can be built or tested. It is the single blocking dependency for the entire project.

**Independent Test**: Can be fully tested by creating a new account, verifying the AI chat (`/ai`) becomes accessible, and confirming the profile record exists — all without any VM or AI functionality present.

**Acceptance Scenarios**:

1. **Given** a new visitor on the signup page, **When** they submit a valid email and password, **Then** they are logged in and redirected to `/ai` (regular user) or `/admin` (admin user), and a profile record is automatically created for them.
2. **Given** a user attempting to register, **When** they submit an email address already in use, **Then** they receive a clear error message and the form remains on the signup page.
3. **Given** a registered user on the login page, **When** they submit correct credentials, **Then** they are authenticated and redirected to `/ai` (regular user) or `/admin` (admin user).
4. **Given** a registered user on the login page, **When** they submit incorrect credentials, **Then** they receive an error and are not granted access.
5. **Given** an unauthenticated visitor, **When** they attempt to navigate directly to any protected page (e.g., `/ai`, `/admin`), **Then** they are redirected to the login page.

---

### User Story 2 - Session Persistence Across Page Reloads (Priority: P2)

A logged-in user closes the browser tab and returns later. They expect to still be logged in without re-entering credentials.

**Why this priority**: Without session persistence, every page refresh forces re-login, making the application unusable in practice. This is essential for baseline usability before any other feature is demonstrated.

**Independent Test**: Can be tested by logging in as a regular user, closing and reopening the browser, and verifying the user lands on `/ai` rather than the login page. For an admin user, verify they land on `/admin`.

**Acceptance Scenarios**:

1. **Given** a logged-in user, **When** they close and reopen the browser within the session window, **Then** they remain authenticated and can access protected pages without logging in again.
2. **Given** a logged-in user, **When** they click "Logout", **Then** their session is terminated and they are redirected to the login page, and protected pages become inaccessible.

---

### User Story 3 - Data Isolation Between Users (Priority: P3)

Each user can only see and interact with their own VMs, logs, and AI usage history. No user can access another user's data, even if they know the record IDs.

**Why this priority**: Data isolation is a security requirement that must be established before any VM or AI data is stored. It cannot be retrofitted after data exists.

**Independent Test**: Can be tested by creating two separate accounts, inserting VM records for each, and verifying that each user's data queries return only their own records — even when using record IDs belonging to the other user.

**Acceptance Scenarios**:

1. **Given** two registered users, each with their own VM records, **When** User A queries the VM list, **Then** only User A's VMs are returned — User B's VMs are never exposed.
2. **Given** User A who knows the UUID of User B's VM, **When** User A attempts to query that specific VM, **Then** the request returns no results (not an error that leaks existence).
3. **Given** an admin user, **When** they query VMs or logs, **Then** they can see records belonging to all users.

---

### User Story 4 - Admin Role Recognition (Priority: P4)

One specific user account can be designated as an admin. After login, the admin is redirected to `/admin` (system-wide analytics) and also has access to `/admin/vms` (all users' VM list) and `/ai` (AI chat with system-wide query capability). Regular users cannot access any `/admin/*` routes.

**Why this priority**: Admin access gates the analytics feature. It is a prerequisite for User Story 3 in the broader system but is lower priority than core auth since it requires a working base auth system first.

**Independent Test**: Can be tested by manually setting the `is_admin` flag on a profile record, then verifying the admin user can access `/admin` and `/admin/vms` while a regular user is redirected away from both.

**Acceptance Scenarios**:

1. **Given** a user with admin status, **When** they log in, **Then** they are redirected to `/admin` and can also navigate to `/admin/vms` and `/ai`.
2. **Given** a regular (non-admin) user, **When** they attempt to navigate to `/admin` or `/admin/vms`, **Then** they are redirected to `/ai`.
3. **Given** a non-admin user's JWT token, **When** it is used to call admin-scoped endpoints (e.g., `GET /api/v1/analytics/admin`), **Then** the request is rejected with HTTP 403 and no cross-user data is returned.

---

### Edge Cases

- **Authenticated non-admin accessing `/admin/*`**: A logged-in regular user navigating to `/admin` or `/admin/vms` MUST be redirected to `/ai` — not shown a 403 or an error page. The role check is a silent redirect, not an error state.
- What happens when a user registers but the automatic profile creation fails? On the next login attempt, the system detects the missing profile and creates it automatically before granting access. The auth account is never deleted as a result of a profile creation failure.
- What happens when a session token expires mid-session? The user should be cleanly redirected to login, not shown an obscure error.
- What happens when the database is unavailable at login time? The user should receive a clear "service unavailable" message rather than a crash.
- What happens when a RAM value outside the valid range (512–16384 MB) is stored directly in the database? The constraint should reject the insert.
- What happens when a VM status transitions to an unrecognized value? The constraint on the `status` column should reject it.
- What happens when a user hits the login attempt limit? After 10 consecutive failed attempts within 15 minutes, the account is locked and further attempts are rejected for 15 minutes with a user-facing message indicating when to retry.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow users to create an account using an email address and password.
- **FR-002**: System MUST validate that email addresses are unique — duplicate registrations must be rejected with a user-facing message.
- **FR-003**: System MUST automatically create a user profile record immediately after successful account registration, without requiring any additional user action. If profile creation fails at registration time, the system MUST detect the missing profile on the user's next login and create it automatically before granting access.
- **FR-004**: System MUST authenticate users via email and password and issue a session token on success.
- **FR-005**: System MUST maintain the user's authenticated session across page reloads and browser restarts for up to 24 hours from the time of login. Sessions MUST expire after 24 hours and require re-authentication.
- **FR-006**: System MUST invalidate the session immediately when the user logs out. Logging out from one device or browser MUST NOT invalidate sessions on other devices.
- **FR-006a**: System MUST allow the same user to maintain active sessions on multiple devices or browsers simultaneously.
- **FR-007**: System MUST redirect unauthenticated users to the login page when they attempt to access any protected route. On successful login, the system MUST apply a role-aware redirect: regular users → `/ai`, admin users → `/admin`.
- **FR-008**: System MUST enforce that each user can only read and modify their own VM records, logs, and AI usage history.
- **FR-009**: System MUST allow designated admin users to read records belonging to all users across all data tables.
- **FR-010**: System MUST persist VM records with the following attributes: name, operating system, RAM allocation, current lifecycle status, error message (when applicable), and timestamps for creation and last update.
- **FR-011**: System MUST persist log records capturing: the acting user, the action performed, the target (VM ID or AI), the outcome (success/failure), and a descriptive message.
- **FR-012**: System MUST persist AI usage records capturing: the acting user, the prompt sent, the response received, token count, and timestamp.
- **FR-013**: System MUST enforce valid status values for VMs — only `stopped`, `starting`, `running`, `stopping`, and `error` are permitted.
- **FR-014**: System MUST enforce that VM RAM values fall within the range of 512 MB to 16384 MB.
- **FR-015**: System MUST index VM, log, and AI usage records by user ID to support efficient per-user queries.
- **FR-016**: System MUST lock an account from further login attempts for 15 minutes after 10 consecutive failed login attempts. The user MUST be shown a clear message indicating the lockout and when they can retry.
- **FR-017**: System MUST enforce a minimum password length of 8 characters containing at least one number. Passwords that do not meet this policy MUST be rejected at registration with a descriptive error message.

### Key Entities

- **User**: An identity in the authentication system. Has a unique email address. Is the owner of all VMs, logs, and AI usage records associated with their account. Cannot be created directly — managed by the auth provider.
- **Profile**: An extension of the User record, created automatically on signup. Carries the `is_admin` flag that determines admin-level access. Has a 1:1 relationship with User.
- **VM**: Represents a virtual machine registered in the system. Belongs to one User. Tracks name, operating system type, RAM in MB, and a lifecycle status. Can carry an error message when in a failed state.
- **Log**: An immutable audit record of an action taken in the system. Records who did what, to which target, with what outcome. Belongs to one User. Append-only — never updated.
- **AI Usage**: A record of a single AI command interaction. Captures the input prompt, the structured response, and token consumption. Belongs to one User.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can complete registration and reach `/ai` in under 60 seconds from first visiting the signup page. An admin user reaches `/admin` after login.
- **SC-002**: 100% of signup events result in a corresponding profile record — there are zero users without a profile after registration.
- **SC-003**: A logged-in user's session survives browser close and reopen within a 24-hour window — 0 spurious logouts during active sessions. Sessions older than 24 hours require re-authentication.
- **SC-004**: A user querying their own VM list receives only their own records — 0 cross-user data leaks in any query, verified by integration test with two distinct accounts.
- **SC-005**: An attempt to insert a VM record with an invalid status value or out-of-range RAM is rejected by the data layer before reaching application logic — 100% enforcement rate.
- **SC-006**: All protected routes redirect unauthenticated visitors to the login page — 0 unprotected access paths to authenticated content.
- **SC-007**: Admin users can query aggregated data across all users; non-admin users cannot — access control is enforced at the data layer, not only in the UI.

---

## Assumptions

- Single-tenant deployment: there is one VirtualBox host and one user (or a very small team). No per-user resource quotas or rate limits are needed at the database level for MVP.
- Email/password authentication is the only login method for MVP. Social logins (Google, GitHub, etc.) are out of scope.
- The admin role is assigned manually by directly setting the `is_admin` flag on a profile record. There is no self-service admin promotion UI for MVP.
- Session tokens are managed by the authentication provider's SDK (cookie-based). The application does not implement custom token storage or rotation logic. Session lifetime is 24 hours from login. Concurrent sessions across multiple devices are permitted.
- The profiles table is the only source of truth for the admin role. There is no separate roles or permissions table for MVP.
- Data retention policy follows the authentication provider's defaults. No custom retention or deletion logic is required for MVP.
- All timestamps are stored in UTC.
- The `error_message` field on VMs is nullable — it is only populated when status equals `error`.

---

## Clarifications

### Session 2026-04-09

- Q: Post-login redirect — where do regular users and admins land after login? → A: Role-aware redirect: regular users → `/ai` (AI chat); admin users → `/admin` (admin panel). FR-007 updated; User Story 1 & 2, SC-001 updated. `/dashboard` and `/vms` references removed.
- Q: Do admins also have access to the AI chat (/ai)? → A: Yes — admins have access to both `/ai` and `/admin`. Landing page is `/admin` but AI chat is not restricted.
- Q: When an admin uses the AI chat, should it call `/api/v1/analytics/admin` for system-wide queries? → A: Yes — AI detects admin role and calls the admin analytics endpoint for system-wide questions; user-scoped endpoint for personal VM questions (specs 003 and 004 updated).
- Q: Should User Story 4 explicitly name admin routes? → A: Yes — updated to name `/admin` (analytics), `/admin/vms` (VM list), and `/ai` (AI chat with elevated queries). Acceptance scenarios updated.
- Q: Should there be an explicit edge case for authenticated non-admin users accessing `/admin/*`? → A: Yes — authenticated non-admin accessing `/admin/*` is silently redirected to `/ai` (not shown a 403). Edge case added.

### Session 2026-04-15

- Q: Does the "Choose Your Role" landing screen (User/Admin cards) represent a real auth flow change? → A: Visual redesign only — both cards lead to the same Supabase login form. No separate auth paths. Role is determined by `is_admin` in the JWT post-login. Auth logic unchanged.
- Q: Should the dark green prototype theme apply globally or per-page? → A: Global — dark background + green accent applied to all pages via `globals.css` and root `layout.tsx`. All routes (auth, admin, ai, vms) inherit the theme.

### Session 2026-04-04

- Q: What is the session expiry window? → A: 24-hour session — expires daily, user re-logs in each day.
- Q: What is the recovery strategy when auto-profile creation fails at signup? → A: Retry on next login — system detects missing profile at login time and creates it automatically before granting access.
- Q: Should login attempts be rate-limited to prevent brute-force attacks? → A: Yes — lockout after 10 consecutive failed attempts within 15 minutes, with a clear user-facing message.
- Q: What password strength policy should be enforced at registration? → A: Minimum 8 characters, at least one number required.
- Q: Should concurrent sessions on multiple devices be allowed? → A: Yes — multiple simultaneous sessions permitted; logout on one device does not affect others.
