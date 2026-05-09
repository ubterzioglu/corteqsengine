"""
CorteQS Intelligence Engine - Backend Server
Corporate Memory & AI-Powered Decision Making Platform
Primary database: Supabase (PostgreSQL)
Real Integrations: Slack, GitHub, Google Drive, Neo4j, Elasticsearch
"""

import os
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Database
from database import init_supabase, get_supabase, serialize

# Services
from services.slack_service import slack_service
from services.github_service import github_service
from services.neo4j_service import neo4j_service
from services.elasticsearch_service import elasticsearch_service
from services.gdrive_service import gdrive_service
from services.data_sync_service import data_sync_service

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialise Supabase async client
    await init_supabase()

    # Initialise Neo4j and Elasticsearch
    await neo4j_service.connect()
    await elasticsearch_service.connect()

    yield

    await neo4j_service.close()
    await elasticsearch_service.close()


app = FastAPI(
    title="CorteQS Intelligence Engine",
    description="Corporate Memory & AI-Powered Decision Making Platform",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================= MODELS =======================

class User(BaseModel):
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str = "user"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SessionRequest(BaseModel):
    session_id: str


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class DataSourceCreate(BaseModel):
    source_type: str
    name: str
    config: Dict[str, Any] = {}


class KnowledgeNodeCreate(BaseModel):
    node_type: str
    title: str
    content: Optional[str] = None
    metadata: Dict[str, Any] = {}


class SearchRequest(BaseModel):
    query: str
    filters: Dict[str, Any] = {}
    limit: int = 20


# ======================= AUTH HELPERS =======================

async def get_current_user(request: Request) -> User:
    """Extract user from session token (cookie or bearer header)."""
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
    activity = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "activity_type": activity_type,
        "description": description,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb.from_("activities").insert(activity).execute()


# ======================= AUTH ENDPOINTS =======================

@app.post("/api/auth/session")
async def create_session(request: SessionRequest, response: Response):
    """Exchange session_id from OAuth for session token."""
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
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


@app.get("/api/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    return user.model_dump()


@app.post("/api/auth/logout")
async def logout(response: Response, user: User = Depends(get_current_user)):
    sb = get_supabase()
    await sb.from_("user_sessions").delete().eq("user_id", user.user_id).execute()
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}


# ======================= DATA SOURCES =======================

@app.get("/api/data-sources")
async def get_data_sources(user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("data_sources").select("*").eq("user_id", user.user_id).limit(100).execute()
    return res.data or []


@app.post("/api/data-sources")
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


@app.put("/api/data-sources/{source_id}/connect")
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


@app.put("/api/data-sources/{source_id}/disconnect")
async def disconnect_data_source(source_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("data_sources").update({"status": "disconnected"}) \
        .eq("source_id", source_id).eq("user_id", user.user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Data source not found")
    return res.data[0]


@app.delete("/api/data-sources/{source_id}")
async def delete_data_source(source_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("data_sources").delete() \
        .eq("source_id", source_id).eq("user_id", user.user_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Data source not found")
    return {"message": "Data source deleted"}


# ======================= KNOWLEDGE GRAPH =======================

@app.get("/api/knowledge/nodes")
async def get_knowledge_nodes(
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


@app.post("/api/knowledge/nodes")
async def create_knowledge_node(node: KnowledgeNodeCreate, user: User = Depends(get_current_user)):
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


@app.get("/api/knowledge/nodes/{node_id}")
async def get_knowledge_node(node_id: str, user: User = Depends(get_current_user)):
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


@app.post("/api/knowledge/nodes/{node_id}/connect/{target_node_id}")
async def connect_nodes(node_id: str, target_node_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()

    # Fetch both nodes
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
        await sb.from_("knowledge_nodes").update({"connections": src_conns}) \
            .eq("node_id", node_id).execute()
    if node_id not in tgt_conns:
        tgt_conns.append(node_id)
        await sb.from_("knowledge_nodes").update({"connections": tgt_conns}) \
            .eq("node_id", target_node_id).execute()

    await log_activity(user.user_id, "connection_made", f"Connected nodes: {node_id} <-> {target_node_id}")
    return {"message": "Nodes connected successfully"}


@app.get("/api/knowledge/graph")
async def get_knowledge_graph(user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("knowledge_nodes").select("*") \
        .eq("user_id", user.user_id).limit(500).execute()
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


# ======================= AI Q&A =======================

@app.post("/api/chat")
async def chat_with_ai(request: ChatRequest, user: User = Depends(get_current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    sb = get_supabase()

    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    user_message = {
        "message_id": user_msg_id,
        "user_id": user.user_id,
        "role": "user",
        "content": request.message,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb.from_("chat_messages").insert(user_message).execute()

    nodes_res = await sb.from_("knowledge_nodes") \
        .select("title, content, node_type") \
        .eq("user_id", user.user_id).limit(20).execute()
    knowledge_nodes = nodes_res.data or []

    knowledge_context = "\n".join([
        f"- [{n.get('node_type')}] {n.get('title')}: {(n.get('content') or '')[:200]}"
        for n in knowledge_nodes
    ])

    sources_res = await sb.from_("data_sources") \
        .select("name, source_type, status") \
        .eq("user_id", user.user_id).limit(10).execute()
    sources = sources_res.data or []

    sources_context = "\n".join([
        f"- {s.get('name', 'Unknown')} ({s.get('source_type', 'unknown')}): {s.get('status', 'unknown')}"
        for s in sources
    ])

    system_message = f"""You are CorteQS AI Assistant, an intelligent corporate memory assistant.
You help users query and understand their organization's knowledge base.

Current user: {user.name} ({user.email})

Connected Data Sources:
{sources_context if sources_context else "No data sources connected yet."}

Knowledge Base Summary:
{knowledge_context if knowledge_context else "Knowledge base is empty. Suggest connecting data sources."}

Guidelines:
- Be concise and helpful
- Reference specific knowledge nodes when relevant
- Suggest connecting data sources if knowledge base is limited
- Help users understand relationships between data
- Provide actionable insights when possible"""

    try:
        session_id = request.session_id or f"chat_{user.user_id}_{datetime.now().strftime('%Y%m%d')}"
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_message,
        ).with_model("gemini", "gemini-2.5-pro")
        response_text = await chat.send_message(UserMessage(text=request.message))
    except Exception as e:
        response_text = f"AI service temporarily unavailable. Error: {str(e)}"

    assistant_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    assistant_message = {
        "message_id": assistant_msg_id,
        "user_id": user.user_id,
        "role": "assistant",
        "content": response_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb.from_("chat_messages").insert(assistant_message).execute()
    await log_activity(user.user_id, "ai_query", f"AI query: {request.message[:50]}...")

    return {
        "user_message": user_message,
        "assistant_message": assistant_message,
    }


@app.get("/api/chat/history")
async def get_chat_history(limit: int = Query(default=50, le=100), user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("chat_messages").select("*") \
        .eq("user_id", user.user_id) \
        .order("created_at", desc=True).limit(limit).execute()
    return list(reversed(res.data or []))


@app.delete("/api/chat/history")
async def clear_chat_history(user: User = Depends(get_current_user)):
    sb = get_supabase()
    await sb.from_("chat_messages").delete().eq("user_id", user.user_id).execute()
    return {"message": "Chat history cleared"}


# ======================= SEARCH =======================

@app.post("/api/search")
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


# ======================= ANALYTICS =======================

@app.get("/api/analytics/overview")
async def get_analytics_overview(user: User = Depends(get_current_user)):
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


@app.get("/api/activities")
async def get_activities(limit: int = Query(default=20, le=100), user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("activities").select("*") \
        .eq("user_id", user.user_id) \
        .order("created_at", desc=True).limit(limit).execute()
    return res.data or []


# ======================= HEALTH =======================

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "CorteQS Intelligence Engine",
        "version": "2.1.0",
        "database": "supabase",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ======================= INTEGRATION STATUS =======================

@app.get("/api/integrations/status")
async def get_integrations_status(user: User = Depends(get_current_user)):
    return await data_sync_service.get_integration_status()


# ======================= SLACK =======================

@app.get("/api/integrations/slack/test")
async def test_slack_connection(user: User = Depends(get_current_user)):
    return slack_service.test_connection()


@app.get("/api/integrations/slack/channels")
async def get_slack_channels(user: User = Depends(get_current_user)):
    channels = slack_service.get_channels()
    return {"channels": channels, "count": len(channels)}


@app.get("/api/integrations/slack/users")
async def get_slack_users(user: User = Depends(get_current_user)):
    users = slack_service.get_users()
    return {"users": users, "count": len(users)}


@app.post("/api/integrations/slack/sync")
async def sync_slack_data(user: User = Depends(get_current_user)):
    sb = get_supabase()
    result = await data_sync_service.sync_slack_data(user.user_id)

    if result.get("success"):
        await log_activity(user.user_id, "slack_sync", f"Synced Slack data: {result.get('stats')}")
        source_id = f"src_slack_{user.user_id}"
        await sb.from_("data_sources").upsert({
            "source_id": source_id,
            "user_id": user.user_id,
            "source_type": "slack",
            "name": "Slack",
            "status": "connected",
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "config": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,source_type").execute()

    return result


# ======================= GITHUB =======================

@app.get("/api/integrations/github/test")
async def test_github_connection(user: User = Depends(get_current_user)):
    return github_service.test_connection()


@app.get("/api/integrations/github/repos")
async def get_github_repos(user: User = Depends(get_current_user)):
    repos = github_service.get_user_repos()
    return {"repositories": repos, "count": len(repos)}


@app.get("/api/integrations/github/repos/{owner}/{repo}")
async def get_github_repo_details(owner: str, repo: str, user: User = Depends(get_current_user)):
    repo_details = github_service.get_repo_details(f"{owner}/{repo}")
    if not repo_details:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo_details


@app.get("/api/integrations/github/repos/{owner}/{repo}/issues")
async def get_github_issues(owner: str, repo: str, state: str = "open", user: User = Depends(get_current_user)):
    issues = github_service.get_repo_issues(f"{owner}/{repo}", state=state)
    return {"issues": issues, "count": len(issues)}


@app.get("/api/integrations/github/repos/{owner}/{repo}/pulls")
async def get_github_pull_requests(owner: str, repo: str, state: str = "open", user: User = Depends(get_current_user)):
    prs = github_service.get_repo_pull_requests(f"{owner}/{repo}", state=state)
    return {"pull_requests": prs, "count": len(prs)}


@app.post("/api/integrations/github/sync")
async def sync_github_data(user: User = Depends(get_current_user)):
    sb = get_supabase()
    result = await data_sync_service.sync_github_data(user.user_id)

    if result.get("success"):
        await log_activity(user.user_id, "github_sync", f"Synced GitHub data: {result.get('stats')}")
        source_id = f"src_github_{user.user_id}"
        await sb.from_("data_sources").upsert({
            "source_id": source_id,
            "user_id": user.user_id,
            "source_type": "github",
            "name": "GitHub",
            "status": "connected",
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "config": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,source_type").execute()

    return result


# ======================= GOOGLE DRIVE =======================

@app.get("/api/integrations/gdrive/test")
async def test_gdrive_connection(user: User = Depends(get_current_user)):
    return gdrive_service.test_connection()


@app.get("/api/integrations/gdrive/files")
async def get_gdrive_files(folder_id: Optional[str] = None, user: User = Depends(get_current_user)):
    files = gdrive_service.list_files(folder_id=folder_id)
    return {"files": files, "count": len(files)}


@app.get("/api/integrations/gdrive/folders")
async def get_gdrive_folders(parent_id: Optional[str] = None, user: User = Depends(get_current_user)):
    folders = gdrive_service.list_folders(parent_id=parent_id)
    return {"folders": folders, "count": len(folders)}


@app.get("/api/integrations/gdrive/recent")
async def get_gdrive_recent_files(user: User = Depends(get_current_user)):
    files = gdrive_service.get_recent_files(limit=20)
    return {"files": files, "count": len(files)}


@app.get("/api/integrations/gdrive/search")
async def search_gdrive_files(q: str = Query(..., min_length=2), user: User = Depends(get_current_user)):
    files = gdrive_service.search_files(q)
    return {"files": files, "count": len(files), "query": q}


@app.post("/api/integrations/gdrive/sync")
async def sync_gdrive_data(
    folder_id: Optional[str] = None,
    recursive: bool = Query(default=True, description="Recursively sync subfolders"),
    max_depth: int = Query(default=5, ge=0, le=20, description="Max recursion depth (0 = current folder only)"),
    wait: bool = Query(default=False, description="If true, wait for sync to complete (may exceed proxy timeout)"),
    user: User = Depends(get_current_user),
):
    """Start a Google Drive sync. Returns immediately with status='started'
    unless `wait=true`. Recursive syncs of large folder trees can exceed the
    60s ingress timeout, so we run them as a background task by default.
    Poll `GET /api/data-sources` to see when `last_sync` gets updated."""
    sb = get_supabase()
    source_id = f"src_gdrive_{user.user_id}"
    started_at = datetime.now(timezone.utc).isoformat()

    # Mark source as syncing
    await sb.from_("data_sources").upsert({
        "source_id": source_id,
        "user_id": user.user_id,
        "source_type": "gdrive",
        "name": "Google Drive",
        "status": "syncing",
        "last_sync": started_at,
        "config": {
            "recursive": recursive,
            "max_depth": max_depth,
            "folder_id": folder_id,
            "started_at": started_at,
        },
        "created_at": started_at,
    }, on_conflict="user_id,source_type").execute()

    async def run_sync():
        result = await data_sync_service.sync_gdrive_data(
            user_id=user.user_id,
            folder_id=folder_id,
            recursive=recursive,
            max_depth=max_depth,
        )
        finished_at = datetime.now(timezone.utc).isoformat()
        config = {
            "recursive": recursive,
            "max_depth": max_depth,
            "folder_id": folder_id,
            "started_at": started_at,
            "finished_at": finished_at,
            "stats": result.get("stats"),
            "error": result.get("error"),
        }
        await sb.from_("data_sources").update({
            "status": "connected" if result.get("success") else "error",
            "last_sync": finished_at,
            "config": config,
        }).eq("source_id", source_id).execute()
        if result.get("success"):
            await log_activity(
                user.user_id, "gdrive_sync",
                f"Synced Google Drive (recursive={recursive}, depth={max_depth}): {result.get('stats')}",
            )
        return result

    if wait:
        result = await run_sync()
        return result

    # Fire-and-forget background task
    import asyncio
    asyncio.create_task(run_sync())
    return {
        "success": True,
        "status": "started",
        "message": "Sync running in background. Poll GET /api/data-sources to see progress.",
        "started_at": started_at,
        "config": {"recursive": recursive, "max_depth": max_depth, "folder_id": folder_id},
    }


# ======================= NEO4J =======================

@app.get("/api/neo4j/status")
async def get_neo4j_status(user: User = Depends(get_current_user)):
    return await neo4j_service.test_connection()


@app.get("/api/neo4j/graph")
async def get_neo4j_graph(user: User = Depends(get_current_user)):
    if not neo4j_service.driver:
        return await get_knowledge_graph(user)
    return await neo4j_service.get_graph_data(user.user_id)


@app.get("/api/neo4j/stats")
async def get_neo4j_stats(user: User = Depends(get_current_user)):
    if not neo4j_service.driver:
        return {"error": "Neo4j not connected"}
    return await neo4j_service.get_node_stats(user.user_id)


@app.post("/api/neo4j/nodes")
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


# ======================= ELASTICSEARCH =======================

@app.get("/api/elasticsearch/status")
async def get_elasticsearch_status(user: User = Depends(get_current_user)):
    return await elasticsearch_service.test_connection()


@app.post("/api/search/full")
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


@app.get("/api/search/autocomplete")
async def autocomplete_search(q: str = Query(..., min_length=2), user: User = Depends(get_current_user)):
    if elasticsearch_service.client:
        suggestions = await elasticsearch_service.autocomplete(user.user_id, q)
        return {"suggestions": suggestions}

    sb = get_supabase()
    res = await sb.from_("knowledge_nodes").select("title") \
        .eq("user_id", user.user_id).ilike("title", f"{q}%").limit(10).execute()
    return {"suggestions": [n["title"] for n in (res.data or [])]}


@app.get("/api/search/stats")
async def get_search_stats(user: User = Depends(get_current_user)):
    if elasticsearch_service.client:
        return await elasticsearch_service.get_stats(user.user_id)
    return {"error": "Elasticsearch not connected"}


# ======================= DOCUMENT UPLOAD =======================

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    sb = get_supabase()

    content = await file.read()
    file_size = len(content)

    supported_types = [".txt", ".md", ".pdf", ".docx", ".json", ".csv"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {supported_types}",
        )

    if file_ext in [".txt", ".md", ".json", ".csv"]:
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("latin-1")
    else:
        text_content = f"[Binary file: {file.filename}, size: {file_size} bytes]"

    document_id = f"doc_{uuid.uuid4().hex[:12]}"

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"extract_{document_id}",
            system_message="You are a document analysis assistant. Extract key topics, entities, and summary from documents.",
        ).with_model("gemini", "gemini-2.5-pro")
        extraction_prompt = f"""Analyze this document and extract:
1. A brief summary (2-3 sentences)
2. Key topics/themes (list 3-5)
3. Named entities (people, organizations, projects mentioned)
4. Key dates or events if any

Document content:
{text_content[:8000]}
"""
        extraction = await chat.send_message(UserMessage(text=extraction_prompt))
    except Exception as e:
        extraction = f"AI extraction failed: {str(e)}"

    document = {
        "document_id": document_id,
        "user_id": user.user_id,
        "filename": file.filename,
        "file_type": file_ext,
        "file_size": file_size,
        "content_preview": text_content[:1000],
        "ai_extraction": extraction,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb.from_("documents").insert(document).execute()

    node_id = f"node_{uuid.uuid4().hex[:12]}"

    if neo4j_service.driver:
        await neo4j_service.create_node(
            node_id=node_id,
            node_type="document",
            title=file.filename,
            content=text_content[:5000],
            metadata={"document_id": document_id, "file_type": file_ext},
            user_id=user.user_id,
        )

    if elasticsearch_service.client:
        await elasticsearch_service.index_node(
            node_id=node_id,
            user_id=user.user_id,
            node_type="document",
            title=file.filename,
            content=text_content[:10000],
            source_type="upload",
            tags=["uploaded", file_ext.replace(".", "")],
        )

    new_node = {
        "node_id": node_id,
        "user_id": user.user_id,
        "node_type": "document",
        "title": file.filename,
        "content": text_content[:5000],
        "source_id": document_id,
        "metadata": {"document_id": document_id, "file_type": file_ext},
        "connections": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await sb.from_("knowledge_nodes").insert(new_node).execute()
    await log_activity(user.user_id, "document_uploaded", f"Document uploaded: {file.filename}")

    return {
        "document": document,
        "knowledge_node_id": node_id,
        "ai_extraction": extraction,
    }


@app.get("/api/documents")
async def get_documents(limit: int = Query(default=20, le=100), user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("documents").select("*") \
        .eq("user_id", user.user_id) \
        .order("created_at", desc=True).limit(limit).execute()
    documents = res.data or []
    return {"documents": documents, "count": len(documents)}


@app.get("/api/documents/{document_id}")
async def get_document(document_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("documents").select("*") \
        .eq("document_id", document_id).eq("user_id", user.user_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return res.data[0]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
