"""Authentication endpoints: OAuth session exchange, /me, logout."""
import os
import uuid
from datetime import datetime, timezone, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import SessionRequest, User

router = APIRouter(prefix="/api/auth", tags=["auth"])

EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"


@router.post("/session")
async def create_session(request: SessionRequest, response: Response):
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": request.session_id},
            )
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session ID")
            user_data = auth_response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=500, detail="Auth service unavailable")

    sb = get_supabase()
    existing = await sb.from_("users").select("*").eq("email", user_data["email"]).limit(1).execute()
    rows = existing.data or []

    if rows:
        user_id = rows[0]["user_id"]
        await sb.from_("users").update({
            "name": user_data["name"],
            "picture": user_data.get("picture"),
        }).eq("user_id", user_id).execute()
    else:
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        await sb.from_("users").insert({
            "user_id": user_id,
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "role": "user",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        await log_activity(user_id, "user_created", f"New user registered: {user_data['email']}")

    session_token = user_data.get("session_token", f"session_{uuid.uuid4().hex}")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    await sb.from_("user_sessions").upsert({
        "user_id": user_id,
        "session_token": session_token,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id").execute()

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/",
    )

    user_res = await sb.from_("users").select("*").eq("user_id", user_id).limit(1).execute()
    return (user_res.data or [{}])[0]


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return user.model_dump()


@router.post("/logout")
async def logout(response: Response, user: User = Depends(get_current_user)):
    sb = get_supabase()
    await sb.from_("user_sessions").delete().eq("user_id", user.user_id).execute()
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}
