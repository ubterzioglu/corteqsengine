"""Data source CRUD."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import DataSourceCreate, User

router = APIRouter(prefix="/api/data-sources", tags=["data-sources"])


@router.get("")
async def list_data_sources(user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("data_sources").select("*").eq("user_id", user.user_id).limit(100).execute()
    return res.data or []


@router.post("")
async def create_data_source(source: DataSourceCreate, user: User = Depends(get_current_user)):
    sb = get_supabase()
    source_id = f"src_{uuid.uuid4().hex[:12]}"
    new_source = {
        "source_id": source_id,
        "user_id": user.user_id,
        "source_type": source.source_type,
        "name": source.name,
        "status": "disconnected",
        "config": source.config,
        "last_sync": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb.from_("data_sources").insert(new_source).execute()
    await log_activity(user.user_id, "source_created", f"Data source created: {source.name}")
    return new_source


@router.put("/{source_id}/connect")
async def connect_data_source(source_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("data_sources").update({
        "status": "connected",
        "last_sync": datetime.now(timezone.utc).isoformat(),
    }).eq("source_id", source_id).eq("user_id", user.user_id).execute()

    if not res.data:
        raise HTTPException(status_code=404, detail="Data source not found")
    await log_activity(user.user_id, "source_connected", f"Data source connected: {source_id}")
    return res.data[0]


@router.put("/{source_id}/disconnect")
async def disconnect_data_source(source_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("data_sources").update({"status": "disconnected"}) \
        .eq("source_id", source_id).eq("user_id", user.user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Data source not found")
    return res.data[0]


@router.delete("/{source_id}")
async def delete_data_source(source_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("data_sources").delete() \
        .eq("source_id", source_id).eq("user_id", user.user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {"message": "Data source deleted"}
