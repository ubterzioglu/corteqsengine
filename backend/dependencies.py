"""Shared FastAPI dependencies: auth, activity logging."""
import uuid
from datetime import datetime, timezone
from typing import Dict

from fastapi import HTTPException, Request

from database import get_supabase
from models import User


async def get_current_user(request: Request) -> User:
    """Extract the user from a session_token cookie or Authorization header."""
    session_token = request.cookies.get("session_token")
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]

    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    sb = get_supabase()
    res = await sb.from_("user_sessions").select("*").eq("session_token", session_token).limit(1).execute()
    sessions = res.data or []
    if not sessions:
        raise HTTPException(status_code=401, detail="Invalid session")

    session = sessions[0]
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")

    user_res = await sb.from_("users").select("*").eq("user_id", session["user_id"]).limit(1).execute()
    users = user_res.data or []
    if not users:
        raise HTTPException(status_code=401, detail="User not found")

    return User(**users[0])


async def log_activity(user_id: str, activity_type: str, description: str, metadata: Dict = None):
    sb = get_supabase()
    await sb.from_("activities").insert({
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "activity_type": activity_type,
        "description": description,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
