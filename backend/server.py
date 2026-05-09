"""
CorteQS Intelligence Engine - Backend Server
Corporate Memory & AI-Powered Decision Making Platform
With Real Integrations: Slack, GitHub, Neo4j, Elasticsearch
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
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# Import services
from services.slack_service import slack_service
from services.github_service import github_service
from services.neo4j_service import neo4j_service
from services.elasticsearch_service import elasticsearch_service
from services.data_sync_service import data_sync_service

# Database setup
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "corteqs_engine")
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# Global database client
db_client: AsyncIOMotorClient = None
db = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_client, db
    db_client = AsyncIOMotorClient(MONGO_URL)
    db = db_client[DB_NAME]
    
    # Create MongoDB indexes
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.data_sources.create_index("source_id", unique=True)
    await db.knowledge_nodes.create_index("node_id", unique=True)
    await db.chat_messages.create_index([("user_id", 1), ("created_at", -1)])
    await db.activities.create_index([("user_id", 1), ("created_at", -1)])
    await db.documents.create_index("document_id", unique=True)
    
    # Initialize Neo4j connection
    await neo4j_service.connect()
    
    # Initialize Elasticsearch connection
    await elasticsearch_service.connect()
    
    yield
    
    # Cleanup
    await neo4j_service.close()
    await elasticsearch_service.close()
    db_client.close()

app = FastAPI(
    title="CorteQS Intelligence Engine",
    description="Corporate Memory & AI-Powered Decision Making Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
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

class DataSource(BaseModel):
    source_id: str
    user_id: str
    source_type: str  # slack, github, whatsapp, email, gdrive
    name: str
    status: str = "disconnected"  # connected, disconnected, syncing, error
    config: Dict[str, Any] = {}
    last_sync: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class KnowledgeNode(BaseModel):
    node_id: str
    user_id: str
    node_type: str  # person, project, document, event, topic
    title: str
    content: Optional[str] = None
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = {}
    connections: List[str] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class KnowledgeEdge(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    relation_type: str  # works_on, created_by, related_to, mentions
    weight: float = 1.0

class ChatMessage(BaseModel):
    message_id: str
    user_id: str
    role: str  # user, assistant
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Activity(BaseModel):
    activity_id: str
    user_id: str
    activity_type: str  # data_sync, query, node_created, connection_made
    description: str
    metadata: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Request/Response Models
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
    """Extract user from session token (cookie or header)"""
    session_token = request.cookies.get("session_token")
    
    if not session_token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_token = auth_header[7:]
    
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    session = await db.user_sessions.find_one(
        {"session_token": session_token},
        {"_id": 0}
    )
    
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    # Check expiry
    expires_at = session.get("expires_at")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    
    user = await db.users.find_one(
        {"user_id": session["user_id"]},
        {"_id": 0}
    )
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return User(**user)

async def log_activity(user_id: str, activity_type: str, description: str, metadata: Dict = None):
    """Log user activity"""
    activity = {
        "activity_id": f"act_{uuid.uuid4().hex[:12]}",
        "user_id": user_id,
        "activity_type": activity_type,
        "description": description,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc)
    }
    await db.activities.insert_one(activity)

# ======================= AUTH ENDPOINTS =======================

@app.post("/api/auth/session")
async def create_session(request: SessionRequest, response: Response):
    """Exchange session_id from OAuth for session token"""
    try:
        async with httpx.AsyncClient() as client:
            auth_response = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": request.session_id}
            )
            
            if auth_response.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session ID")
            
            user_data = auth_response.json()
    except httpx.RequestError:
        raise HTTPException(status_code=500, detail="Auth service unavailable")
    
    # Check if user exists
    existing_user = await db.users.find_one(
        {"email": user_data["email"]},
        {"_id": 0}
    )
    
    if existing_user:
        user_id = existing_user["user_id"]
        # Update user info
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "name": user_data["name"],
                "picture": user_data.get("picture")
            }}
        )
    else:
        # Create new user
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        new_user = {
            "user_id": user_id,
            "email": user_data["email"],
            "name": user_data["name"],
            "picture": user_data.get("picture"),
            "role": "user",
            "created_at": datetime.now(timezone.utc)
        }
        await db.users.insert_one(new_user)
        await log_activity(user_id, "user_created", f"New user registered: {user_data['email']}")
    
    # Create session
    session_token = user_data.get("session_token", f"session_{uuid.uuid4().hex}")
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    
    await db.user_sessions.update_one(
        {"user_id": user_id},
        {"$set": {
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=7 * 24 * 60 * 60,
        path="/"
    )
    
    user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
    return user

@app.get("/api/auth/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current authenticated user"""
    return user.model_dump()

@app.post("/api/auth/logout")
async def logout(response: Response, user: User = Depends(get_current_user)):
    """Logout user"""
    await db.user_sessions.delete_one({"user_id": user.user_id})
    response.delete_cookie("session_token", path="/")
    return {"message": "Logged out successfully"}

# ======================= DATA SOURCES ENDPOINTS =======================

@app.get("/api/data-sources")
async def get_data_sources(user: User = Depends(get_current_user)):
    """Get all data sources for user"""
    sources = await db.data_sources.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).to_list(100)
    return sources

@app.post("/api/data-sources")
async def create_data_source(
    source: DataSourceCreate,
    user: User = Depends(get_current_user)
):
    """Create a new data source connection"""
    source_id = f"src_{uuid.uuid4().hex[:12]}"
    
    new_source = {
        "source_id": source_id,
        "user_id": user.user_id,
        "source_type": source.source_type,
        "name": source.name,
        "status": "disconnected",
        "config": source.config,
        "last_sync": None,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.data_sources.insert_one(new_source)
    await log_activity(user.user_id, "source_created", f"Data source created: {source.name}")
    
    del new_source["_id"]
    return new_source

@app.put("/api/data-sources/{source_id}/connect")
async def connect_data_source(
    source_id: str,
    user: User = Depends(get_current_user)
):
    """Connect/activate a data source"""
    result = await db.data_sources.update_one(
        {"source_id": source_id, "user_id": user.user_id},
        {"$set": {"status": "connected", "last_sync": datetime.now(timezone.utc)}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    await log_activity(user.user_id, "source_connected", f"Data source connected: {source_id}")
    
    source = await db.data_sources.find_one({"source_id": source_id}, {"_id": 0})
    return source

@app.put("/api/data-sources/{source_id}/disconnect")
async def disconnect_data_source(
    source_id: str,
    user: User = Depends(get_current_user)
):
    """Disconnect a data source"""
    result = await db.data_sources.update_one(
        {"source_id": source_id, "user_id": user.user_id},
        {"$set": {"status": "disconnected"}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    source = await db.data_sources.find_one({"source_id": source_id}, {"_id": 0})
    return source

@app.delete("/api/data-sources/{source_id}")
async def delete_data_source(
    source_id: str,
    user: User = Depends(get_current_user)
):
    """Delete a data source"""
    result = await db.data_sources.delete_one(
        {"source_id": source_id, "user_id": user.user_id}
    )
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Data source not found")
    
    return {"message": "Data source deleted"}

# ======================= KNOWLEDGE GRAPH ENDPOINTS =======================

@app.get("/api/knowledge/nodes")
async def get_knowledge_nodes(
    node_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    user: User = Depends(get_current_user)
):
    """Get knowledge graph nodes"""
    query = {"user_id": user.user_id}
    if node_type:
        query["node_type"] = node_type
    
    nodes = await db.knowledge_nodes.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return nodes

@app.post("/api/knowledge/nodes")
async def create_knowledge_node(
    node: KnowledgeNodeCreate,
    user: User = Depends(get_current_user)
):
    """Create a knowledge graph node"""
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
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.knowledge_nodes.insert_one(new_node)
    await log_activity(user.user_id, "node_created", f"Knowledge node created: {node.title}")
    
    del new_node["_id"]
    return new_node

@app.get("/api/knowledge/nodes/{node_id}")
async def get_knowledge_node(
    node_id: str,
    user: User = Depends(get_current_user)
):
    """Get a specific knowledge node with connections"""
    node = await db.knowledge_nodes.find_one(
        {"node_id": node_id, "user_id": user.user_id},
        {"_id": 0}
    )
    
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Get connected nodes
    if node.get("connections"):
        connected = await db.knowledge_nodes.find(
            {"node_id": {"$in": node["connections"]}, "user_id": user.user_id},
            {"_id": 0}
        ).to_list(100)
        node["connected_nodes"] = connected
    
    return node

@app.post("/api/knowledge/nodes/{node_id}/connect/{target_node_id}")
async def connect_nodes(
    node_id: str,
    target_node_id: str,
    user: User = Depends(get_current_user)
):
    """Connect two knowledge nodes"""
    # Verify both nodes exist
    source_node = await db.knowledge_nodes.find_one(
        {"node_id": node_id, "user_id": user.user_id}
    )
    target_node = await db.knowledge_nodes.find_one(
        {"node_id": target_node_id, "user_id": user.user_id}
    )
    
    if not source_node or not target_node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Add bidirectional connection
    await db.knowledge_nodes.update_one(
        {"node_id": node_id},
        {"$addToSet": {"connections": target_node_id}}
    )
    await db.knowledge_nodes.update_one(
        {"node_id": target_node_id},
        {"$addToSet": {"connections": node_id}}
    )
    
    await log_activity(user.user_id, "connection_made", f"Connected nodes: {node_id} <-> {target_node_id}")
    
    return {"message": "Nodes connected successfully"}

@app.get("/api/knowledge/graph")
async def get_knowledge_graph(
    user: User = Depends(get_current_user)
):
    """Get full knowledge graph for visualization"""
    nodes = await db.knowledge_nodes.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).to_list(500)
    
    # Build edges from connections
    edges = []
    seen_edges = set()
    
    for node in nodes:
        for conn in node.get("connections", []):
            edge_key = tuple(sorted([node["node_id"], conn]))
            if edge_key not in seen_edges:
                edges.append({
                    "source": node["node_id"],
                    "target": conn
                })
                seen_edges.add(edge_key)
    
    return {
        "nodes": nodes,
        "edges": edges
    }

# ======================= AI Q&A ENDPOINTS =======================

@app.post("/api/chat")
async def chat_with_ai(
    request: ChatRequest,
    user: User = Depends(get_current_user)
):
    """Send message to AI and get response"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    # Save user message
    user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    user_message = {
        "message_id": user_msg_id,
        "user_id": user.user_id,
        "role": "user",
        "content": request.message,
        "created_at": datetime.now(timezone.utc)
    }
    await db.chat_messages.insert_one(user_message)
    
    # Get knowledge context
    knowledge_nodes = await db.knowledge_nodes.find(
        {"user_id": user.user_id},
        {"_id": 0, "title": 1, "content": 1, "node_type": 1}
    ).limit(20).to_list(20)
    
    knowledge_context = "\n".join([
        f"- [{n['node_type']}] {n['title']}: {n.get('content', '')[:200]}"
        for n in knowledge_nodes
    ])
    
    # Get data sources status
    sources = await db.data_sources.find(
        {"user_id": user.user_id},
        {"_id": 0, "name": 1, "source_type": 1, "status": 1}
    ).to_list(10)
    
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
            system_message=system_message
        ).with_model("gemini", "gemini-2.5-pro")
        
        llm_message = UserMessage(text=request.message)
        response_text = await chat.send_message(llm_message)
        
    except Exception as e:
        response_text = f"AI service temporarily unavailable. Error: {str(e)}"
    
    # Save assistant message
    assistant_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
    assistant_message = {
        "message_id": assistant_msg_id,
        "user_id": user.user_id,
        "role": "assistant",
        "content": response_text,
        "created_at": datetime.now(timezone.utc)
    }
    await db.chat_messages.insert_one(assistant_message)
    
    await log_activity(user.user_id, "ai_query", f"AI query: {request.message[:50]}...")
    
    return {
        "user_message": {**user_message, "_id": None},
        "assistant_message": {**assistant_message, "_id": None}
    }

@app.get("/api/chat/history")
async def get_chat_history(
    limit: int = Query(default=50, le=100),
    user: User = Depends(get_current_user)
):
    """Get chat history"""
    messages = await db.chat_messages.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return list(reversed(messages))

@app.delete("/api/chat/history")
async def clear_chat_history(user: User = Depends(get_current_user)):
    """Clear chat history"""
    await db.chat_messages.delete_many({"user_id": user.user_id})
    return {"message": "Chat history cleared"}

# ======================= SEARCH ENDPOINTS =======================

@app.post("/api/search")
async def search_knowledge(
    request: SearchRequest,
    user: User = Depends(get_current_user)
):
    """Search across knowledge base"""
    query = {
        "user_id": user.user_id,
        "$or": [
            {"title": {"$regex": request.query, "$options": "i"}},
            {"content": {"$regex": request.query, "$options": "i"}}
        ]
    }
    
    if request.filters.get("node_type"):
        query["node_type"] = request.filters["node_type"]
    
    results = await db.knowledge_nodes.find(
        query,
        {"_id": 0}
    ).limit(request.limit).to_list(request.limit)
    
    await log_activity(user.user_id, "search", f"Search query: {request.query}")
    
    return {
        "query": request.query,
        "results": results,
        "count": len(results)
    }

# ======================= ANALYTICS ENDPOINTS =======================

@app.get("/api/analytics/overview")
async def get_analytics_overview(user: User = Depends(get_current_user)):
    """Get analytics overview"""
    # Count statistics
    total_nodes = await db.knowledge_nodes.count_documents({"user_id": user.user_id})
    total_sources = await db.data_sources.count_documents({"user_id": user.user_id})
    connected_sources = await db.data_sources.count_documents(
        {"user_id": user.user_id, "status": "connected"}
    )
    total_messages = await db.chat_messages.count_documents({"user_id": user.user_id})
    
    # Node type distribution
    node_types = await db.knowledge_nodes.aggregate([
        {"$match": {"user_id": user.user_id}},
        {"$group": {"_id": "$node_type", "count": {"$sum": 1}}}
    ]).to_list(20)
    
    # Recent activity
    recent_activities = await db.activities.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    return {
        "statistics": {
            "total_nodes": total_nodes,
            "total_sources": total_sources,
            "connected_sources": connected_sources,
            "total_messages": total_messages
        },
        "node_distribution": {item["_id"]: item["count"] for item in node_types},
        "recent_activities": recent_activities
    }

@app.get("/api/activities")
async def get_activities(
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user)
):
    """Get user activities"""
    activities = await db.activities.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return activities

# ======================= HEALTH CHECK =======================

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "CorteQS Intelligence Engine",
        "version": "2.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ======================= INTEGRATION STATUS =======================

@app.get("/api/integrations/status")
async def get_integrations_status(user: User = Depends(get_current_user)):
    """Get status of all external integrations"""
    status = await data_sync_service.get_integration_status()
    return status

# ======================= SLACK ENDPOINTS =======================

@app.get("/api/integrations/slack/test")
async def test_slack_connection(user: User = Depends(get_current_user)):
    """Test Slack connection"""
    return slack_service.test_connection()

@app.get("/api/integrations/slack/channels")
async def get_slack_channels(user: User = Depends(get_current_user)):
    """Get Slack channels"""
    channels = slack_service.get_channels()
    return {"channels": channels, "count": len(channels)}

@app.get("/api/integrations/slack/users")
async def get_slack_users(user: User = Depends(get_current_user)):
    """Get Slack workspace users"""
    users = slack_service.get_users()
    return {"users": users, "count": len(users)}

@app.post("/api/integrations/slack/sync")
async def sync_slack_data(user: User = Depends(get_current_user)):
    """Sync all Slack data to knowledge graph"""
    result = await data_sync_service.sync_slack_data(user.user_id)
    
    if result["success"]:
        await log_activity(user.user_id, "slack_sync", f"Synced Slack data: {result['stats']}")
        
        # Update data source status
        await db.data_sources.update_one(
            {"user_id": user.user_id, "source_type": "slack"},
            {"$set": {"status": "connected", "last_sync": datetime.now(timezone.utc)}},
            upsert=True
        )
    
    return result

# ======================= GITHUB ENDPOINTS =======================

@app.get("/api/integrations/github/test")
async def test_github_connection(user: User = Depends(get_current_user)):
    """Test GitHub connection"""
    return github_service.test_connection()

@app.get("/api/integrations/github/repos")
async def get_github_repos(user: User = Depends(get_current_user)):
    """Get GitHub repositories"""
    repos = github_service.get_user_repos()
    return {"repositories": repos, "count": len(repos)}

@app.get("/api/integrations/github/repos/{owner}/{repo}")
async def get_github_repo_details(
    owner: str, 
    repo: str,
    user: User = Depends(get_current_user)
):
    """Get detailed info for a specific repository"""
    repo_details = github_service.get_repo_details(f"{owner}/{repo}")
    if not repo_details:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo_details

@app.get("/api/integrations/github/repos/{owner}/{repo}/issues")
async def get_github_issues(
    owner: str, 
    repo: str,
    state: str = "open",
    user: User = Depends(get_current_user)
):
    """Get issues from a repository"""
    issues = github_service.get_repo_issues(f"{owner}/{repo}", state=state)
    return {"issues": issues, "count": len(issues)}

@app.get("/api/integrations/github/repos/{owner}/{repo}/pulls")
async def get_github_pull_requests(
    owner: str, 
    repo: str,
    state: str = "open",
    user: User = Depends(get_current_user)
):
    """Get pull requests from a repository"""
    prs = github_service.get_repo_pull_requests(f"{owner}/{repo}", state=state)
    return {"pull_requests": prs, "count": len(prs)}

@app.post("/api/integrations/github/sync")
async def sync_github_data(user: User = Depends(get_current_user)):
    """Sync all GitHub data to knowledge graph"""
    result = await data_sync_service.sync_github_data(user.user_id)
    
    if result["success"]:
        await log_activity(user.user_id, "github_sync", f"Synced GitHub data: {result['stats']}")
        
        # Update data source status
        await db.data_sources.update_one(
            {"user_id": user.user_id, "source_type": "github"},
            {"$set": {"status": "connected", "last_sync": datetime.now(timezone.utc)}},
            upsert=True
        )
    
    return result

# ======================= NEO4J KNOWLEDGE GRAPH ENDPOINTS =======================

@app.get("/api/neo4j/status")
async def get_neo4j_status(user: User = Depends(get_current_user)):
    """Check Neo4j connection status"""
    return await neo4j_service.test_connection()

@app.get("/api/neo4j/graph")
async def get_neo4j_graph(user: User = Depends(get_current_user)):
    """Get full knowledge graph from Neo4j"""
    if not neo4j_service.driver:
        # Fallback to MongoDB
        return await get_knowledge_graph(user)
    
    graph_data = await neo4j_service.get_graph_data(user.user_id)
    return graph_data

@app.get("/api/neo4j/stats")
async def get_neo4j_stats(user: User = Depends(get_current_user)):
    """Get Neo4j graph statistics"""
    if not neo4j_service.driver:
        return {"error": "Neo4j not connected"}
    
    return await neo4j_service.get_node_stats(user.user_id)

@app.post("/api/neo4j/nodes")
async def create_neo4j_node(
    node: KnowledgeNodeCreate,
    user: User = Depends(get_current_user)
):
    """Create a node directly in Neo4j"""
    node_id = f"node_{uuid.uuid4().hex[:12]}"
    
    # Create in Neo4j
    if neo4j_service.driver:
        await neo4j_service.create_node(
            node_id=node_id,
            node_type=node.node_type,
            title=node.title,
            content=node.content,
            metadata=node.metadata,
            user_id=user.user_id
        )
    
    # Also index in Elasticsearch
    if elasticsearch_service.client:
        await elasticsearch_service.index_node(
            node_id=node_id,
            user_id=user.user_id,
            node_type=node.node_type,
            title=node.title,
            content=node.content,
            tags=node.metadata.get("tags", [])
        )
    
    # Store in MongoDB as backup
    new_node = {
        "node_id": node_id,
        "user_id": user.user_id,
        "node_type": node.node_type,
        "title": node.title,
        "content": node.content,
        "source_id": None,
        "metadata": node.metadata,
        "connections": [],
        "created_at": datetime.now(timezone.utc)
    }
    await db.knowledge_nodes.insert_one(new_node)
    
    await log_activity(user.user_id, "node_created", f"Knowledge node created: {node.title}")
    
    del new_node["_id"]
    return new_node

# ======================= ELASTICSEARCH SEARCH ENDPOINTS =======================

@app.get("/api/elasticsearch/status")
async def get_elasticsearch_status(user: User = Depends(get_current_user)):
    """Check Elasticsearch connection status"""
    return await elasticsearch_service.test_connection()

@app.post("/api/search/full")
async def full_text_search(
    request: SearchRequest,
    user: User = Depends(get_current_user)
):
    """Full-text search using Elasticsearch"""
    if elasticsearch_service.client:
        results = await elasticsearch_service.search(
            user_id=user.user_id,
            query=request.query,
            node_type=request.filters.get("node_type"),
            source_type=request.filters.get("source_type"),
            limit=request.limit
        )
        await log_activity(user.user_id, "search", f"Full-text search: {request.query}")
        return results
    
    # Fallback to MongoDB search
    return await search_knowledge(request, user)

@app.get("/api/search/autocomplete")
async def autocomplete_search(
    q: str = Query(..., min_length=2),
    user: User = Depends(get_current_user)
):
    """Autocomplete suggestions"""
    if elasticsearch_service.client:
        suggestions = await elasticsearch_service.autocomplete(user.user_id, q)
        return {"suggestions": suggestions}
    
    # Fallback to MongoDB
    nodes = await db.knowledge_nodes.find(
        {
            "user_id": user.user_id,
            "title": {"$regex": f"^{q}", "$options": "i"}
        },
        {"_id": 0, "title": 1}
    ).limit(10).to_list(10)
    
    return {"suggestions": [n["title"] for n in nodes]}

@app.get("/api/search/stats")
async def get_search_stats(user: User = Depends(get_current_user)):
    """Get search index statistics"""
    if elasticsearch_service.client:
        return await elasticsearch_service.get_stats(user.user_id)
    return {"error": "Elasticsearch not connected"}

# ======================= DOCUMENT UPLOAD & EXTRACTION =======================

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user)
):
    """Upload a document for AI extraction"""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Supported types
    supported_types = [".txt", ".md", ".pdf", ".docx", ".json", ".csv"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in supported_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Supported: {supported_types}"
        )
    
    # For text files, decode directly
    if file_ext in [".txt", ".md", ".json", ".csv"]:
        try:
            text_content = content.decode("utf-8")
        except:
            text_content = content.decode("latin-1")
    else:
        # For binary files (PDF, DOCX), we'd need specialized libraries
        # For now, store metadata and indicate processing needed
        text_content = f"[Binary file: {file.filename}, size: {file_size} bytes]"
    
    document_id = f"doc_{uuid.uuid4().hex[:12]}"
    
    # Extract key information using AI
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"extract_{document_id}",
            system_message="You are a document analysis assistant. Extract key topics, entities, and summary from documents."
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
    
    # Store document metadata
    document = {
        "document_id": document_id,
        "user_id": user.user_id,
        "filename": file.filename,
        "file_type": file_ext,
        "file_size": file_size,
        "content_preview": text_content[:1000],
        "ai_extraction": extraction,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.documents.insert_one(document)
    
    # Create knowledge node from document
    node_id = f"node_{uuid.uuid4().hex[:12]}"
    
    if neo4j_service.driver:
        await neo4j_service.create_node(
            node_id=node_id,
            node_type="document",
            title=file.filename,
            content=text_content[:5000],
            metadata={"document_id": document_id, "file_type": file_ext},
            user_id=user.user_id
        )
    
    if elasticsearch_service.client:
        await elasticsearch_service.index_node(
            node_id=node_id,
            user_id=user.user_id,
            node_type="document",
            title=file.filename,
            content=text_content[:10000],
            source_type="upload",
            tags=["uploaded", file_ext.replace(".", "")]
        )
    
    # Store in MongoDB
    new_node = {
        "node_id": node_id,
        "user_id": user.user_id,
        "node_type": "document",
        "title": file.filename,
        "content": text_content[:5000],
        "source_id": document_id,
        "metadata": {"document_id": document_id, "file_type": file_ext},
        "connections": [],
        "created_at": datetime.now(timezone.utc)
    }
    await db.knowledge_nodes.insert_one(new_node)
    
    await log_activity(user.user_id, "document_uploaded", f"Document uploaded: {file.filename}")
    
    del document["_id"]
    return {
        "document": document,
        "knowledge_node_id": node_id,
        "ai_extraction": extraction
    }

@app.get("/api/documents")
async def get_documents(
    limit: int = Query(default=20, le=100),
    user: User = Depends(get_current_user)
):
    """Get uploaded documents"""
    documents = await db.documents.find(
        {"user_id": user.user_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return {"documents": documents, "count": len(documents)}

@app.get("/api/documents/{document_id}")
async def get_document(
    document_id: str,
    user: User = Depends(get_current_user)
):
    """Get a specific document"""
    document = await db.documents.find_one(
        {"document_id": document_id, "user_id": user.user_id},
        {"_id": 0}
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
