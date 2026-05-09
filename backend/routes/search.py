"""Search endpoints (Postgres ilike + Elasticsearch full-text)."""
from fastapi import APIRouter, Depends, Query

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import SearchRequest, User
from services.elasticsearch_service import elasticsearch_service

router = APIRouter(prefix="/api", tags=["search"])


@router.post("/search")
async def search_knowledge(request: SearchRequest, user: User = Depends(get_current_user)):
    sb = get_supabase()
    pattern = f"%{request.query}%"
    q = sb.from_("knowledge_nodes").select("*").eq("user_id", user.user_id) \
        .or_(f"title.ilike.{pattern},content.ilike.{pattern}")

    if request.filters.get("node_type"):
        q = q.eq("node_type", request.filters["node_type"])

    res = await q.limit(request.limit).execute()
    results = res.data or []
    await log_activity(user.user_id, "search", f"Search query: {request.query}")
    return {"query": request.query, "results": results, "count": len(results)}


@router.post("/search/full")
async def full_text_search(request: SearchRequest, user: User = Depends(get_current_user)):
    if elasticsearch_service.client:
        results = await elasticsearch_service.search(
            user_id=user.user_id,
            query=request.query,
            node_type=request.filters.get("node_type"),
            source_type=request.filters.get("source_type"),
            limit=request.limit,
        )
        await log_activity(user.user_id, "search", f"Full-text search: {request.query}")
        return results
    return await search_knowledge(request, user)


@router.get("/search/autocomplete")
async def autocomplete(q: str = Query(..., min_length=2), user: User = Depends(get_current_user)):
    if elasticsearch_service.client:
        suggestions = await elasticsearch_service.autocomplete(user.user_id, q)
        return {"suggestions": suggestions}

    sb = get_supabase()
    res = await sb.from_("knowledge_nodes").select("title") \
        .eq("user_id", user.user_id).ilike("title", f"{q}%").limit(10).execute()
    return {"suggestions": [n["title"] for n in (res.data or [])]}


@router.get("/search/stats")
async def search_stats(user: User = Depends(get_current_user)):
    if elasticsearch_service.client:
        return await elasticsearch_service.get_stats(user.user_id)
    return {"error": "Elasticsearch not connected"}


@router.get("/elasticsearch/status")
async def elasticsearch_status(user: User = Depends(get_current_user)):
    return await elasticsearch_service.test_connection()
