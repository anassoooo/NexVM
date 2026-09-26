from pathlib import Path

from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_SECRET_KEY: str
    GROQ_API_KEY: str
    FRONTEND_URL: str = "http://localhost:3000"
    VBOXMANAGE_PATH: str = ""
    VM_STORAGE_PATH: str = ""
    VM_QUOTA_PER_USER: int = 5
    VM_DISK_QUOTA_MB: int = 200000

    model_config = {
        "env_file": str(_BACKEND_DIR / ".env"),
        "env_file_encoding": "utf-8",
    }


settings = Settings()
