"""AI chat (Gemini) endpoints."""
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import ChatRequest, User

router = APIRouter(prefix="/api/chat", tags=["chat"])

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")


@router.post("")
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

    return {"user_message": user_message, "assistant_message": assistant_message}


@router.get("/history")
async def get_chat_history(limit: int = Query(default=50, le=100), user: User = Depends(get_current_user)):
    sb = get_supabase()
    res = await sb.from_("chat_messages").select("*") \
        .eq("user_id", user.user_id) \
        .order("created_at", desc=True).limit(limit).execute()
    return list(reversed(res.data or []))


@router.delete("/history")
async def clear_chat_history(user: User = Depends(get_current_user)):
    sb = get_supabase()
    await sb.from_("chat_messages").delete().eq("user_id", user.user_id).execute()
    return {"message": "Chat history cleared"}
