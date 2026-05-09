"""Health check."""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "CorteQS Intelligence Engine",
        "version": "2.2.0",
        "database": "supabase",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
