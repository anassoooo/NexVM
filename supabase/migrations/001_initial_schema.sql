-- ============================================================
-- myVMS — Initial Schema Migration
-- Branch: 001-supabase-auth-db
-- Date:   2026-04-04
-- File:   supabase/migrations/001_initial_schema.sql
-- ============================================================
-- Run in Supabase SQL Editor or via Supabase CLI migration.
-- auth.users table is managed by Supabase — not created here.
-- ============================================================

-- ============================================================
-- HELPER FUNCTION: is_admin()
-- SECURITY DEFINER to avoid RLS recursion on profiles table.
-- Used by admin policies on all application tables.
-- ============================================================
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND is_admin = true
    );
$$ LANGUAGE sql SECURITY DEFINER STABLE;

-- ------------------------------------------------------------
-- TABLE: profiles
-- 1:1 extension of auth.users; auto-created on signup via trigger.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    is_admin   boolean     NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT profiles_pkey PRIMARY KEY (id)
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_user_own" ON public.profiles
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "profiles_admin_all" ON public.profiles
    FOR ALL USING (public.is_admin());

-- ------------------------------------------------------------
-- TABLE: vms
-- Tracks every virtual machine registered in the system.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.vms (
    id            uuid        NOT NULL DEFAULT gen_random_uuid(),
    user_id       uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name          text        NOT NULL,
    os            text        NOT NULL,
    ram           integer     NOT NULL,
    status        text        NOT NULL DEFAULT 'stopped',
    error_message text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT vms_pkey            PRIMARY KEY (id),
    CONSTRAINT vms_status_check    CHECK (status IN ('stopped', 'starting', 'running', 'stopping', 'error')),
    CONSTRAINT vms_ram_check       CHECK (ram >= 512 AND ram <= 16384)
);

CREATE INDEX IF NOT EXISTS vms_user_id_idx ON public.vms (user_id);

ALTER TABLE public.vms ENABLE ROW LEVEL SECURITY;

CREATE POLICY "vms_user_own" ON public.vms
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "vms_admin_all" ON public.vms
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND is_admin = true
        )
    );

-- ------------------------------------------------------------
-- TABLE: logs
-- Append-only audit trail. user_id SET NULL on user delete
-- to preserve audit records after account removal.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.logs (
    id         uuid        NOT NULL DEFAULT gen_random_uuid(),
    user_id    uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    action     text        NOT NULL,
    target     text        NOT NULL,
    status     text        NOT NULL,
    message    text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT logs_pkey          PRIMARY KEY (id),
    CONSTRAINT logs_status_check  CHECK (status IN ('success', 'failure')),
    CONSTRAINT logs_action_check  CHECK (action IN ('create_vm', 'start_vm', 'stop_vm', 'delete_vm', 'login', 'ai_command'))
);

CREATE INDEX IF NOT EXISTS logs_user_id_idx ON public.logs (user_id);

ALTER TABLE public.logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "logs_user_own" ON public.logs
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "logs_admin_all" ON public.logs
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND is_admin = true
        )
    );

-- ------------------------------------------------------------
-- TABLE: ai_usage
-- Records every AI command interaction.
-- user_id SET NULL on user delete to preserve analytics.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.ai_usage (
    id         uuid        NOT NULL DEFAULT gen_random_uuid(),
    user_id    uuid        REFERENCES auth.users(id) ON DELETE SET NULL,
    prompt     text        NOT NULL,
    response   text        NOT NULL,
    tokens     integer     NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ai_usage_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS ai_usage_user_id_idx ON public.ai_usage (user_id);

ALTER TABLE public.ai_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ai_usage_user_own" ON public.ai_usage
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "ai_usage_admin_all" ON public.ai_usage
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND is_admin = true
        )
    );

-- ------------------------------------------------------------
-- TRIGGER: auto-create profile on user signup
-- ON CONFLICT DO NOTHING makes it idempotent (safe if called twice).
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.profiles (id, is_admin)
    VALUES (NEW.id, false)
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================
-- RLS ISOLATION VERIFICATION (T030)
-- ============================================================
-- Run the following queries in Supabase SQL Editor to verify
-- that Row Level Security enforces data isolation correctly.
--
-- PREREQUISITES:
--   1. Create two test users (A and B) via Supabase Auth.
--   2. Create an admin user and set is_admin = true on their profile.
--   3. Insert VM records for each user:
--        INSERT INTO vms (user_id, name, os, ram) VALUES ('<user_A_id>', 'A-VM', 'Ubuntu', 1024);
--        INSERT INTO vms (user_id, name, os, ram) VALUES ('<user_B_id>', 'B-VM', 'Ubuntu', 1024);
--
-- TEST 1 — User isolation (run as user A):
--   SET request.jwt.claims = '{"sub": "<user_A_id>"}';
--   SELECT * FROM vms;
--   EXPECTED: Only rows where user_id = <user_A_id> are returned.
--
-- TEST 2 — Cross-user blocked (run as user A):
--   SET request.jwt.claims = '{"sub": "<user_A_id>"}';
--   SELECT * FROM vms WHERE user_id = '<user_B_id>';
--   EXPECTED: Empty result set.
--
-- TEST 3 — Admin sees all (run as admin user):
--   First: UPDATE profiles SET is_admin = true WHERE id = '<admin_id>';
--   SET request.jwt.claims = '{"sub": "<admin_id>"}';
--   SELECT * FROM vms;
--   EXPECTED: All VM rows returned regardless of user_id.
--
-- Repeat analogous tests for `logs` and `ai_usage` tables.
--
-- VERIFICATION STATUS: [ ] Passed  Date: ____
-- ============================================================
