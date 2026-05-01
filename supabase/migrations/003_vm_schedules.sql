-- ============================================================
-- myVMS — VM Schedules table
-- Date: 2026-05-01
-- Stores cron-like start/stop schedules per VM
-- ============================================================

CREATE TABLE IF NOT EXISTS public.vm_schedules (
    id         uuid        NOT NULL DEFAULT gen_random_uuid(),
    user_id    uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    vm_id      uuid        NOT NULL REFERENCES public.vms(id) ON DELETE CASCADE,
    action     text        NOT NULL CHECK (action IN ('start', 'stop')),
    cron_expr  text        NOT NULL,
    enabled    boolean     NOT NULL DEFAULT true,
    last_run   timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT vm_schedules_pkey PRIMARY KEY (id)
);

CREATE INDEX IF NOT EXISTS vm_schedules_user_id_idx ON public.vm_schedules (user_id);
CREATE INDEX IF NOT EXISTS vm_schedules_vm_id_idx ON public.vm_schedules (vm_id);

ALTER TABLE public.vm_schedules ENABLE ROW LEVEL SECURITY;

CREATE POLICY "vm_schedules_user_own" ON public.vm_schedules
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "vm_schedules_admin_all" ON public.vm_schedules
    FOR ALL USING (public.is_admin());

-- Extend logs action check to include new actions
ALTER TABLE public.logs DROP CONSTRAINT IF EXISTS logs_action_check;
ALTER TABLE public.logs ADD CONSTRAINT logs_action_check CHECK (action IN (
    'create_vm', 'start_vm', 'stop_vm', 'delete_vm',
    'login', 'ai_command', 'force_reset_vm',
    'attach_iso', 'detach_iso', 'enable_vrde', 'disable_vrde',
    'modify_vm', 'pause_vm', 'resume_vm', 'save_state',
    'add_port_rule', 'remove_port_rule',
    'take_snapshot', 'restore_snapshot', 'delete_snapshot',
    'clone_vm', 'export_vm', 'import_vm', 'schedule_vm'
));
