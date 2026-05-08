"""
CorteQS Intelligence Engine - Backend Server
Corporate Memory & AI-Powered Decision Making Platform
"""

import os
import uuid
import httpx
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

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
    
    # Create indexes
    await db.users.create_index("user_id", unique=True)
    await db.users.create_index("email", unique=True)
    await db.user_sessions.create_index("session_token", unique=True)
    await db.data_sources.create_index("source_id", unique=True)
    await db.knowledge_nodes.create_index("node_id", unique=True)
    await db.chat_messages.create_index([("user_id", 1), ("created_at", -1)])
    await db.activities.create_index([("user_id", 1), ("created_at", -1)])
    
    yield
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
        f"- {s['name']} ({s['source_type']}): {s['status']}"
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
        "version": "1.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
