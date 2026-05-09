-- ============================================================================
-- CorteQS Intelligence Engine - Supabase PostgreSQL Schema
-- ----------------------------------------------------------------------------
-- HOW TO RUN:
--   1. Open Supabase Dashboard → SQL Editor → New Query
--   2. Paste this entire file
--   3. Click "Run"
--
-- All tables use TEXT IDs (compatible with the existing app-generated UUIDs)
-- and JSONB for flexible metadata fields.
-- ============================================================================

-- Clean any pre-existing CorteQS tables that may conflict (safe — they are
-- empty until this app is used). Order matters because of FK dependencies.
DROP TABLE IF EXISTS documents       CASCADE;
DROP TABLE IF EXISTS activities      CASCADE;
DROP TABLE IF EXISTS chat_messages   CASCADE;
DROP TABLE IF EXISTS knowledge_nodes CASCADE;
DROP TABLE IF EXISTS data_sources    CASCADE;
DROP TABLE IF EXISTS user_sessions   CASCADE;
DROP TABLE IF EXISTS users           CASCADE;

-- Trigram extension for fuzzy LIKE/ILIKE search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ---------- USERS ----------
CREATE TABLE users (
    user_id      TEXT PRIMARY KEY,
    email        TEXT UNIQUE NOT NULL,
    name         TEXT NOT NULL,
    picture      TEXT,
    role         TEXT NOT NULL DEFAULT 'user',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_users_email ON users(email);

-- ---------- USER SESSIONS ----------
CREATE TABLE user_sessions (
    user_id        TEXT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    session_token  TEXT UNIQUE NOT NULL,
    expires_at     TIMESTAMPTZ NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);

-- ---------- DATA SOURCES ----------
CREATE TABLE data_sources (
    source_id     TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    source_type   TEXT NOT NULL,
    name          TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'disconnected',
    config        JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_sync     TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_data_sources_user ON data_sources(user_id);
CREATE UNIQUE INDEX uq_data_sources_user_type
    ON data_sources(user_id, source_type);

-- ---------- KNOWLEDGE NODES ----------
CREATE TABLE knowledge_nodes (
    node_id       TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    node_type     TEXT NOT NULL,
    title         TEXT NOT NULL,
    content       TEXT,
    source_id     TEXT,
    metadata      JSONB NOT NULL DEFAULT '{}'::jsonb,
    connections   JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_knowledge_nodes_user        ON knowledge_nodes(user_id);
CREATE INDEX idx_knowledge_nodes_user_type   ON knowledge_nodes(user_id, node_type);
CREATE INDEX idx_knowledge_nodes_created     ON knowledge_nodes(user_id, created_at DESC);
CREATE INDEX idx_knowledge_nodes_title_trgm  ON knowledge_nodes USING gin (title gin_trgm_ops);

-- ---------- CHAT MESSAGES ----------
CREATE TABLE chat_messages (
    message_id   TEXT PRIMARY KEY,
    user_id      TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role         TEXT NOT NULL,
    content      TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_chat_messages_user_time
    ON chat_messages(user_id, created_at DESC);

-- ---------- ACTIVITIES ----------
CREATE TABLE activities (
    activity_id     TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    activity_type   TEXT NOT NULL,
    description     TEXT NOT NULL,
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_activities_user_time
    ON activities(user_id, created_at DESC);

-- ---------- DOCUMENTS ----------
CREATE TABLE documents (
    document_id      TEXT PRIMARY KEY,
    user_id          TEXT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    filename         TEXT NOT NULL,
    file_type        TEXT,
    file_size        BIGINT,
    content_preview  TEXT,
    ai_extraction    TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_documents_user_time
    ON documents(user_id, created_at DESC);

-- Tell PostgREST to refresh its schema cache so the API picks up the new tables
NOTIFY pgrst, 'reload schema';

-- ============================================================================
-- DONE. You can now restart the backend and use the application.
-- ============================================================================
