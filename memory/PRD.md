# CorteQS Intelligence Engine - PRD

## Original Problem Statement
Build CorteQS Intelligence Engine - A comprehensive Corporate Memory and AI-powered decision-making platform. The system integrates data from multiple sources (WhatsApp, Slack, GitHub, Email, Google Drive), builds a Knowledge Graph, provides AI Q&A capabilities with natural language querying, content recommendation engine, and analytical dashboards.

## User Choices
- **Scope**: Full-scale development with all modules
- **AI/LLM**: Gemini 3 Pro (using Emergent LLM Key)
- **Primary Database**: Supabase (PostgreSQL) — migrated from MongoDB on 2026-02-09
- **Knowledge Graph DB**: Neo4j Aura (cloud)
- **Search Index**: Elasticsearch Cloud
- **Authentication**: Google OAuth via Emergent Auth
- **Real Integrations**: Slack, GitHub, Google Drive (LIVE)

## Architecture v2.0
```
Frontend (React + Tailwind)
    │
    ├── Login (Google OAuth)
    ├── Dashboard (Overview + Stats)
    ├── Data Sources (Live Integrations Panel)
    │   ├── Slack (LIVE - connected)
    │   ├── GitHub (LIVE - connected)
    │   ├── Neo4j Status
    │   └── Elasticsearch Status
    ├── Knowledge Graph (Neo4j visualization)
    ├── AI Chat (Gemini-powered Q&A)
    ├── Analytics (Metrics + Distribution)
    └── Document Upload (AI extraction)
    │
Backend (FastAPI + Supabase async client)
    │
    ├── Auth APIs (/api/auth/*)
    ├── Data Source APIs (/api/data-sources/*)
    ├── Knowledge APIs (/api/knowledge/*)
    ├── Chat APIs (/api/chat/*)
    ├── Search APIs (/api/search/*)
    ├── Analytics APIs (/api/analytics/*)
    ├── Integration APIs (/api/integrations/*)
    │   ├── Slack sync
    │   ├── GitHub sync
    │   ├── Google Drive sync
    │   └── Status checks
    ├── Neo4j APIs (/api/neo4j/*)
    ├── Elasticsearch APIs (/api/elasticsearch/*)
    └── Document APIs (/api/documents/*)
    │
Databases
    │
    ├── Supabase (PostgreSQL): users, user_sessions, data_sources, knowledge_nodes, chat_messages, activities, documents
    ├── Neo4j Aura: Knowledge Graph nodes & edges
    └── Elasticsearch Cloud: Full-text search
```

## What's Been Implemented

**Date: 2026-05-08 (v1.0)**
- Full backend API with 16 endpoints
- Complete frontend with 5 main pages
- Google OAuth authentication
- Data source connector system
- Knowledge graph with MongoDB
- AI chat powered by Gemini 2.5 Pro
- Analytics dashboard

**Date: 2026-05-09 (v2.0)**
- ✅ Real Slack API integration (channels, users, messages)
- ✅ Real GitHub API integration (repos, issues, PRs, contributors)
- ✅ Neo4j Aura cloud database for Knowledge Graph
- ✅ Elasticsearch Cloud full-text search
- ✅ Google Drive service account integration
- ✅ Data sync from Slack/GitHub/GDrive to Neo4j + Elasticsearch
- ✅ Document upload with AI-powered extraction
- ✅ Live integrations panel in frontend
- ✅ Detailed user manual at /manual.html

**Date: 2026-02-09 (v2.1) — Supabase Migration**
- ✅ Replaced MongoDB with Supabase (PostgreSQL) as the primary database
- ✅ New `/app/backend/database.py` async Supabase client wrapper
- ✅ Schema file `/app/backend/sql/schema.sql` with 7 tables, indexes & pg_trgm extension
- ✅ Removed motor/pymongo from requirements.txt and codebase entirely
- ✅ All endpoints rewritten with supabase-py async API (eq, ilike, or_, upsert, JSONB ops)
- ✅ Test seed script at `/app/backend/seed_test_user.py`
- ✅ 35/35 backend regression tests passed (iteration_5.json)
- ✅ Health endpoint reports `database=supabase`, `version=2.1.0`

**Date: 2026-02-09 (v2.2) — Google Drive Recursive Sync**
- ✅ `data_sync_service.sync_gdrive_data` now traverses subfolders recursively (configurable `max_depth`, default 5)
- ✅ Creates `CONTAINED_IN` Neo4j relationships between files and parent folders
- ✅ Endpoint `POST /api/integrations/gdrive/sync` runs as background task by default to bypass 60s ingress timeout (use `?wait=true` to block until done)
- ✅ Sync state + stats persisted to `data_sources.config` so frontend can poll `GET /api/data-sources` for progress
- ✅ Status transitions: `syncing` → `connected` (or `error`) with finished_at timestamp
- ✅ Live test: 195 files + 85 folders synced at depth=2 (vs 57+43 at root only)
- ✅ Neo4j: 204 total nodes (10 projects, 144 documents, 7 persons, 43 topics)

## Prioritized Backlog

### P0 - Critical (Next Sprint)
- [x] Real Slack API integration
- [x] Real GitHub API integration
- [x] Neo4j graph database
- [x] Elasticsearch full-text search
- [x] Google Drive integration
- [x] Migrate MongoDB → Supabase

### P1 - High Priority
- [x] Recursive sync for Google Drive subfolders
- [ ] Sync Slack channel messages (needs channels:history scope)
- [ ] Real-time webhooks for Slack/GitHub
- [ ] Advanced graph algorithms (PageRank)
- [ ] Vector embeddings for semantic search
- [ ] Split server.py (~955 lines) into routers/* modules
- [ ] Replace knowledge_nodes.connections JSONB read-modify-write with separate edges table or RPC for atomicity

### P2 - Medium Priority
- [ ] Extract Google Docs content directly into Knowledge Graph
- [ ] Recommendation engine
- [ ] Custom report generation
- [ ] RBAC (role-based access control)
- [ ] Multi-device sessions (current upsert keeps one per user)
- [ ] Replace CORS allow_origins=['*'] with frontend URL when allow_credentials=True

## Connected Services
| Service | Status | Details |
|---------|--------|---------|
| Slack | ✅ Connected | CorteQS workspace |
| GitHub | ✅ Connected | @ubterzioglu (67 repos) |
| Google Drive | ✅ Connected | Service account active |
| Neo4j | ✅ Connected | Aura cloud - 21 nodes, 14 edges |
| Elasticsearch | ✅ Connected | Cloud - 11 documents indexed |

## Data Synced
- **Neo4j**: 21 nodes (10 projects, 7 persons, 4 documents), 14 edges
- **Elasticsearch**: 11 documents indexed (GitHub repos + issues)
- **Full-text Search**: Working with fuzzy matching
- **Google Drive**: Ready (share files to service account to sync)
