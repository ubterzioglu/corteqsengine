"""Neo4j graph endpoints."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import KnowledgeNodeCreate, User
from services.elasticsearch_service import elasticsearch_service
from services.neo4j_service import neo4j_service
from routes.knowledge import get_graph as supabase_get_graph

router = APIRouter(prefix="/api/neo4j", tags=["neo4j"])


@router.get("/status")
async def neo4j_status(user: User = Depends(get_current_user)):
    return await neo4j_service.test_connection()


@router.get("/graph")
async def neo4j_graph(user: User = Depends(get_current_user)):
    if not neo4j_service.driver:
        return await supabase_get_graph(user)
    return await neo4j_service.get_graph_data(user.user_id)


@router.get("/stats")
async def neo4j_stats(user: User = Depends(get_current_user)):
    if not neo4j_service.driver:
        return {"error": "Neo4j not connected"}
    return await neo4j_service.get_node_stats(user.user_id)


@router.post("/nodes")
async def create_neo4j_node(node: KnowledgeNodeCreate, user: User = Depends(get_current_user)):
    sb = get_supabase()
    node_id = f"node_{uuid.uuid4().hex[:12]}"

    if neo4j_service.driver:
        await neo4j_service.create_node(
            node_id=node_id,
            node_type=node.node_type,
            title=node.title,
            content=node.content,
            metadata=node.metadata,
            user_id=user.user_id,
        )

    if elasticsearch_service.client:
        await elasticsearch_service.index_node(
            node_id=node_id,
            user_id=user.user_id,
            node_type=node.node_type,
            title=node.title,
            content=node.content,
            tags=node.metadata.get("tags", []),
        )

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
