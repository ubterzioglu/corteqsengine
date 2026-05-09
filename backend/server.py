"""
CorteQS Intelligence Engine - Backend Server (entry point).

Slim FastAPI app: lifespan, CORS, and router registration only.
All endpoints live under /app/backend/routes/.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env.local")
load_dotenv(ROOT_DIR / ".env", override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_supabase
from services.elasticsearch_service import elasticsearch_service
from services.neo4j_service import neo4j_service

from routes.analytics import router as analytics_router
from routes.auth import router as auth_router
from routes.chat import router as chat_router
from routes.data_sources import router as data_sources_router
from routes.documents import router as documents_router
from routes.graph import router as graph_router
from routes.health import router as health_router
from routes.integrations import router as integrations_router
from routes.knowledge import router as knowledge_router
from routes.search import router as search_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_supabase()
    await neo4j_service.connect()
    await elasticsearch_service.connect()
    yield
    await neo4j_service.close()
    await elasticsearch_service.close()


app = FastAPI(
    title="CorteQS Intelligence Engine",
    description="Corporate Memory & AI-Powered Decision Making Platform",
    version="2.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(data_sources_router)
app.include_router(knowledge_router)
app.include_router(chat_router)
app.include_router(search_router)
app.include_router(analytics_router)
app.include_router(integrations_router)
app.include_router(graph_router)
app.include_router(documents_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
