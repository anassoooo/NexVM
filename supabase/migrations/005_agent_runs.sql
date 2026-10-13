-- NexVM — Autopilot agent runs (spec 013)

-- Plans refer to VMs by name, so a user's VM names must be unique.
CREATE UNIQUE INDEX IF NOT EXISTS vms_user_id_name_key ON public.vms (user_id, name);

CREATE TABLE IF NOT EXISTS public.agent_runs (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    conversation_id  uuid NOT NULL,
    prompt           text NOT NULL CHECK (char_length(prompt) <= 2000),
    status           text NOT NULL CHECK (status IN (
                         'answered', 'needs_approval', 'running',
                         'completed', 'failed', 'cancelled')),
    answer           text,
    plan             jsonb NOT NULL DEFAULT '[]'::jsonb,
    plan_version     integer NOT NULL DEFAULT 0,
    findings         jsonb NOT NULL DEFAULT '[]'::jsonb,
    trace            jsonb NOT NULL DEFAULT '[]'::jsonb,
    model            text,
    total_tokens     integer NOT NULL DEFAULT 0,
    latency_ms       integer NOT NULL DEFAULT 0,
    repairs          integer NOT NULL DEFAULT 0,
    error            text,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS agent_runs_user_created_idx ON public.agent_runs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS agent_runs_conversation_idx ON public.agent_runs (conversation_id, created_at);

ALTER TABLE public.agent_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_runs_user_own ON public.agent_runs
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY agent_runs_admin_all ON public.agent_runs
    FOR SELECT USING (public.is_admin());

-- Writes go through the backend (secret key); clients may only read their own runs (§VII).
REVOKE ALL ON public.agent_runs FROM anon, authenticated;
GRANT SELECT ON public.agent_runs TO authenticated;
