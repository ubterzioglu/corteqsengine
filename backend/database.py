"""
Supabase PostgreSQL client wrapper for CorteQS Intelligence Engine.

Uses the official `supabase` async Python SDK (PostgREST over HTTPS) with the
service_role key — bypassing RLS, which is what we want for backend usage.
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional

from supabase import acreate_client, AsyncClient

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError(
        "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in /app/backend/.env"
    )

# Lazily initialised — populated by init_supabase() during FastAPI lifespan.
_client: Optional[AsyncClient] = None


async def init_supabase() -> AsyncClient:
    """Create the singleton AsyncClient. Called from FastAPI lifespan."""
    global _client
    if _client is None:
        try:
            _client = await acreate_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        except Exception:
            _client = None
            raise
    return _client


def get_supabase() -> AsyncClient:
    """Return the initialised AsyncClient."""
    if _client is None:
        raise RuntimeError("Supabase client not initialised — call init_supabase() first.")
    return _client


def to_iso(value: Any) -> Any:
    """Convert datetime → ISO 8601 string for Supabase JSON payloads."""
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def serialize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively convert datetimes in a dict for JSON encoding."""
    return {k: to_iso(v) for k, v in payload.items()}
