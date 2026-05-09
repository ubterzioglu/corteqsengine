"""Analytics + activity log."""
from typing import Dict

from fastapi import APIRouter, Depends, Query

from database import get_supabase
from dependencies import get_current_user
from models import User

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics/overview")
async def analytics_overview(user: User = Depends(get_current_user)):
    sb = get_supabase()

    nodes_res = await sb.from_("knowledge_nodes").select("node_id, node_type", count="exact") \
        .eq("user_id", user.user_id).execute()
    total_nodes = nodes_res.count or 0
    node_types: Dict[str, int] = {}
    for n in nodes_res.data or []:
        node_types[n["node_type"]] = node_types.get(n["node_type"], 0) + 1

    sources_res = await sb.from_("data_sources").select("status", count="exact") \
        .eq("user_id", user.user_id).execute()
    total_sources = sources_res.count or 0
    connected_sources = sum(1 for s in (sources_res.data or []) if s.get("status") == "connected")

    msgs_res = await sb.from_("chat_messages").select("message_id", count="exact") \
        .eq("user_id", user.user_id).execute()
    total_messages = msgs_res.count or 0

    activities_res = await sb.from_("activities").select("*") \
        .eq("user_id", user.user_id).order("created_at", desc=True).limit(10).execute()

    return {
        "statistics": {
            "total_nodes": total_nodes,
            "total_sources": total_sources,
            "connected_sources": connected_sources,
            "total_messages": total_messages,
        },
        "node_distribution": node_types,
        "recent_activities": activities_res.data or [],
    }


@router.get("/activities")
async def list_activities(limit: int = Query(default=20, le=100), user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("activities").select("*") \
        .eq("user_id", user.user_id) \
        .order("created_at", desc=True).limit(limit).execute()
    return res.data or []
