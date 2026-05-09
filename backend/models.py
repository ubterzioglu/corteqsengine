"""Pydantic models shared across routers."""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


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
