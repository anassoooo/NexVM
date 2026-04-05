from supabase import Client

supabase_client: Client | None = None


def get_supabase_client() -> Client:
    if supabase_client is None:
        raise RuntimeError("Supabase client not initialized — app lifespan not started")
    return supabase_client
