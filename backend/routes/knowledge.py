"""Knowledge graph endpoints (Supabase-backed)."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import KnowledgeNodeCreate, User

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/nodes")
async def list_nodes(
    node_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user),
):
    sb = get_supabase()
    q = sb.from_("knowledge_nodes").select("*").eq("user_id", user.user_id)
    if node_type:
        q = q.eq("node_type", node_type)
    res = await q.order("created_at", desc=True).limit(limit).execute()
    return res.data or []


@router.post("/nodes")
async def create_node(node: KnowledgeNodeCreate, user: User = Depends(get_current_user)):
    sb = get_supabase()
    node_id = f"node_{uuid.uuid4().hex[:12]}"
    new_node = {
        "node_id": node_id,
        "user_id": user.user_id,
        "node_type": node.node_type,
        "title": node.title,
        "content": node.content,
        "source_id": None,
        "metadata": node.metadata,
        "connections": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb.from_("knowledge_nodes").insert(new_node).execute()
    await log_activity(user.user_id, "node_created", f"Knowledge node created: {node.title}")
    return new_node


@router.get("/nodes/{node_id}")
async def get_node(node_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("knowledge_nodes").select("*") \
        .eq("node_id", node_id).eq("user_id", user.user_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Node not found")

    node = res.data[0]
    if node.get("connections"):
        conn_res = await sb.from_("knowledge_nodes").select("*") \
            .in_("node_id", node["connections"]).eq("user_id", user.user_id).execute()
        node["connected_nodes"] = conn_res.data or []
    return node


@router.post("/nodes/{node_id}/connect/{target_node_id}")
async def connect_nodes(node_id: str, target_node_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    src_res = await sb.from_("knowledge_nodes").select("*") \
        .eq("node_id", node_id).eq("user_id", user.user_id).limit(1).execute()
    tgt_res = await sb.from_("knowledge_nodes").select("*") \
        .eq("node_id", target_node_id).eq("user_id", user.user_id).limit(1).execute()

    if not src_res.data or not tgt_res.data:
        raise HTTPException(status_code=404, detail="Node not found")

    src_conns = list(src_res.data[0].get("connections") or [])
    tgt_conns = list(tgt_res.data[0].get("connections") or [])

    if target_node_id not in src_conns:
        src_conns.append(target_node_id)
        await sb.from_("knowledge_nodes").update({"connections": src_conns}).eq("node_id", node_id).execute()
    if node_id not in tgt_conns:
        tgt_conns.append(node_id)
        await sb.from_("knowledge_nodes").update({"connections": tgt_conns}).eq("node_id", target_node_id).execute()

    await log_activity(user.user_id, "connection_made", f"Connected nodes: {node_id} <-> {target_node_id}")
    return {"message": "Nodes connected successfully"}


@router.get("/graph")
async def get_graph(user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("knowledge_nodes").select("*").eq("user_id", user.user_id).limit(500).execute()
    nodes = res.data or []

    edges = []
    seen_edges = set()
    for node in nodes:
        for conn in node.get("connections") or []:
            edge_key = tuple(sorted([node["node_id"], conn]))
            if edge_key not in seen_edges:
                edges.append({"source": node["node_id"], "target": conn})
                seen_edges.add(edge_key)

    return {"nodes": nodes, "edges": edges}
