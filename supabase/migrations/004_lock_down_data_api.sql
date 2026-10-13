-- NexVM — Lock down the Supabase Data API
-- The frontend only uses Supabase Auth; all data goes through the FastAPI
-- backend, which connects with the secret key and bypasses RLS. Clients
-- therefore need no write access to public tables. Before this migration,
-- the "*_user_own" FOR ALL policies let a signed-in user PATCH their own
-- profiles row and set is_admin = true.

-- 1. No direct table access for anonymous clients.
REVOKE ALL ON public.profiles, public.vms, public.logs, public.ai_usage,
              public.vm_snapshots, public.vm_schedules
  FROM anon;

-- 2. Signed-in clients may read their own rows (RLS still applies) but not write.
REVOKE ALL ON public.profiles, public.vms, public.logs, public.ai_usage,
              public.vm_snapshots, public.vm_schedules
  FROM authenticated;
GRANT SELECT ON public.profiles, public.vms, public.logs, public.ai_usage,
                public.vm_snapshots, public.vm_schedules
  TO authenticated;

-- 3. Tables created later in public do not get client grants automatically.
ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM anon, authenticated;

-- 4. Pin search_path on SECURITY DEFINER functions.
ALTER FUNCTION public.is_admin() SET search_path = '';
ALTER FUNCTION public.handle_new_user() SET search_path = '';

-- 5. handle_new_user only runs as the auth.users trigger; nobody calls it via RPC.
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM PUBLIC, anon, authenticated;

-- 6. is_admin() is used by RLS policies for signed-in users, so keep it for
--    authenticated but not for anonymous callers.
REVOKE EXECUTE ON FUNCTION public.is_admin() FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.is_admin() TO authenticated;
