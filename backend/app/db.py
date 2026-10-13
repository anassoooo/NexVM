from supabase import Client, ClientOptions, create_client

from app.config import settings

supabase_client: Client | None = None


def get_supabase_client() -> Client:
    if supabase_client is None:
        raise RuntimeError("Supabase client not initialized — app lifespan not started")
    return supabase_client


def new_auth_client() -> Client:
    """Short-lived client for sign-in/sign-up.

    Signing in on a supabase-py client switches its database requests to the
    user's JWT. Using a throwaway client keeps the shared client on the
    secret key and avoids sessions leaking between concurrent requests.
    """
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SECRET_KEY,
        options=ClientOptions(auto_refresh_token=False, persist_session=False),
    )
