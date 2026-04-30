-- Migration: Spec 008 — VM P2 Lifecycle
-- Apply via Supabase SQL editor (3 steps in order)

-- Step 1: Extend vms_status_check to include 'paused'
ALTER TABLE public.vms DROP CONSTRAINT IF EXISTS vms_status_check;
ALTER TABLE public.vms ADD CONSTRAINT vms_status_check
  CHECK (status IN ('stopped', 'starting', 'running', 'stopping', 'error', 'paused'));

-- Step 2: Add nat_rules JSONB column
ALTER TABLE public.vms
  ADD COLUMN IF NOT EXISTS nat_rules jsonb NOT NULL DEFAULT '[]';

-- Step 3: Create vm_snapshots table with RLS
CREATE TABLE IF NOT EXISTS public.vm_snapshots (
    id          uuid        NOT NULL DEFAULT gen_random_uuid(),
    vm_id       uuid        NOT NULL REFERENCES public.vms(id) ON DELETE CASCADE,
    name        text        NOT NULL,
    description text,
    created_at  timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT vm_snapshots_pkey       PRIMARY KEY (id),
    CONSTRAINT vm_snapshots_vm_name_uq UNIQUE (vm_id, name)
);

ALTER TABLE public.vm_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "snapshots_user_own" ON public.vm_snapshots
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.vms WHERE id = vm_id AND user_id = auth.uid())
  );

CREATE POLICY "snapshots_admin_all" ON public.vm_snapshots
  FOR ALL USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND is_admin = true)
  );
