import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")


_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
            raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SECRET_KEY in env")
        _supabase = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
    return _supabase
