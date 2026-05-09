"""Document upload + listing."""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import User
from services.elasticsearch_service import elasticsearch_service
from services.neo4j_service import neo4j_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")
SUPPORTED_TYPES = (".txt", ".md", ".pdf", ".docx", ".json", ".csv")


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user: User = Depends(get_current_user)):
    sb = get_supabase()

    content = await file.read()
    file_size = len(content)
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in SUPPORTED_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Supported: {list(SUPPORTED_TYPES)}",
        )

    if file_ext in (".txt", ".md", ".json", ".csv"):
        try:
            text_content = content.decode("utf-8")
        except UnicodeDecodeError:
            text_content = content.decode("latin-1")
    else:
        text_content = f"[Binary file: {file.filename}, size: {file_size} bytes]"

    document_id = f"doc_{uuid.uuid4().hex[:12]}"

    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"extract_{document_id}",
            system_message="You are a document analysis assistant. Extract key topics, entities, and summary from documents.",
        ).with_model("gemini", "gemini-2.5-pro")
        extraction = await chat.send_message(UserMessage(text=f"""Analyze this document and extract:
1. A brief summary (2-3 sentences)
2. Key topics/themes (list 3-5)
3. Named entities (people, organizations, projects mentioned)
4. Key dates or events if any

Document content:
{text_content[:8000]}
"""))
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

    await sb.from_("knowledge_nodes").insert({
        "node_id": node_id,
        "user_id": user.user_id,
        "node_type": "document",
        "title": file.filename,
        "content": text_content[:5000],
        "source_id": document_id,
        "metadata": {"document_id": document_id, "file_type": file_ext},
        "connections": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()
    await log_activity(user.user_id, "document_uploaded", f"Document uploaded: {file.filename}")

    return {"document": document, "knowledge_node_id": node_id, "ai_extraction": extraction}


@router.get("")
async def list_documents(limit: int = Query(default=20, le=100), user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("documents").select("*") \
        .eq("user_id", user.user_id) \
        .order("created_at", desc=True).limit(limit).execute()
    documents = res.data or []
    return {"documents": documents, "count": len(documents)}


@router.get("/{document_id}")
async def get_document(document_id: str, user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("documents").select("*") \
        .eq("document_id", document_id).eq("user_id", user.user_id).limit(1).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Document not found")
    return res.data[0]
