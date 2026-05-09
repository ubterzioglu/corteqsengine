"""
Backend regression tests for CorteQS — Supabase migration verification.
Tests cover: health, auth, knowledge graph, search, chat, data sources,
analytics, integrations (Slack/GitHub/GDrive), Neo4j, Elasticsearch, documents.
"""
import io
import os
import time
import uuid

import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env", override=False)
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
TOKEN = os.environ.get("TEST_SESSION_TOKEN", "test_session_corteqs")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
TIMEOUT = 30

# Shared state across tests
_state = {}


# -------- Health & Auth --------
def test_health():
    r = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["version"] == "2.2.0"
    assert data["database"] == "supabase"


def test_auth_me():
    r = requests.get(f"{BASE_URL}/api/auth/me", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["user_id"] == "user_test123456"
    assert data["email"] == "test@corteqs.com"


def test_auth_me_invalid_token():
    r = requests.get(f"{BASE_URL}/api/auth/me",
                     headers={"Authorization": "Bearer invalid_xxx"}, timeout=TIMEOUT)
    assert r.status_code == 401


# -------- Analytics --------
def test_analytics_overview():
    r = requests.get(f"{BASE_URL}/api/analytics/overview", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["statistics"], dict)
    assert isinstance(data["node_distribution"], dict)
    for k in ("total_nodes", "total_sources", "connected_sources", "total_messages"):
        assert k in data["statistics"]


# -------- Knowledge Graph --------
def test_create_knowledge_node():
    payload = {
        "node_type": "concept",
        "title": f"TEST_Node_{uuid.uuid4().hex[:6]}",
        "content": "Supabase migration verification node.",
        "metadata": {"tags": ["test", "supabase"]},
    }
    r = requests.post(f"{BASE_URL}/api/knowledge/nodes",
                      headers=HEADERS, json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == payload["title"]
    assert data["node_type"] == "concept"
    assert "node_id" in data
    _state["node_a"] = data["node_id"]


def test_create_second_node_for_connection():
    payload = {"node_type": "person", "title": f"TEST_Person_{uuid.uuid4().hex[:6]}",
               "content": "Person node.", "metadata": {}}
    r = requests.post(f"{BASE_URL}/api/knowledge/nodes",
                      headers=HEADERS, json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    _state["node_b"] = r.json()["node_id"]


def test_list_knowledge_nodes():
    r = requests.get(f"{BASE_URL}/api/knowledge/nodes", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    ids = [n["node_id"] for n in data]
    assert _state["node_a"] in ids


def test_get_single_node():
    r = requests.get(f"{BASE_URL}/api/knowledge/nodes/{_state['node_a']}",
                     headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["node_id"] == _state["node_a"]


def test_connect_nodes():
    a, b = _state["node_a"], _state["node_b"]
    r = requests.post(f"{BASE_URL}/api/knowledge/nodes/{a}/connect/{b}",
                      headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    # Verify persistence: GET node a and check connections
    r2 = requests.get(f"{BASE_URL}/api/knowledge/nodes/{a}", headers=HEADERS, timeout=TIMEOUT)
    assert r2.status_code == 200
    assert b in (r2.json().get("connections") or [])


def test_knowledge_graph():
    r = requests.get(f"{BASE_URL}/api/knowledge/graph", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data and "edges" in data
    edge_pairs = [tuple(sorted([e["source"], e["target"]])) for e in data["edges"]]
    assert tuple(sorted([_state["node_a"], _state["node_b"]])) in edge_pairs


# -------- Search --------
def test_search_knowledge():
    # node_a title starts with TEST_Node — search by 'TEST_Node'
    payload = {"query": "TEST_Node", "filters": {}, "limit": 20}
    r = requests.post(f"{BASE_URL}/api/search", headers=HEADERS, json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "TEST_Node"
    assert isinstance(data["results"], list)
    assert data["count"] >= 1


# -------- Chat --------
def test_clear_chat_history_first():
    r = requests.delete(f"{BASE_URL}/api/chat/history", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


def test_chat():
    payload = {"message": "Hello, list my knowledge nodes briefly."}
    r = requests.post(f"{BASE_URL}/api/chat", headers=HEADERS, json=payload, timeout=90)
    assert r.status_code == 200
    data = r.json()
    assert data["user_message"]["role"] == "user"
    assert data["assistant_message"]["role"] == "assistant"
    assert len(data["assistant_message"]["content"]) > 0


def test_chat_history():
    r = requests.get(f"{BASE_URL}/api/chat/history", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) >= 2
    # chronological order
    assert msgs[0]["role"] == "user"
    assert msgs[1]["role"] == "assistant"


# -------- Data Sources --------
def test_create_data_source():
    payload = {"source_type": "custom", "name": "TEST_DS", "config": {}}
    r = requests.post(f"{BASE_URL}/api/data-sources",
                      headers=HEADERS, json=payload, timeout=TIMEOUT)
    assert r.status_code == 200
    _state["source_id"] = r.json()["source_id"]


def test_list_data_sources():
    r = requests.get(f"{BASE_URL}/api/data-sources", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    assert any(s["source_id"] == _state["source_id"] for s in r.json())


def test_connect_data_source():
    r = requests.put(f"{BASE_URL}/api/data-sources/{_state['source_id']}/connect",
                     headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "connected"


def test_disconnect_data_source():
    r = requests.put(f"{BASE_URL}/api/data-sources/{_state['source_id']}/disconnect",
                     headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["status"] == "disconnected"


def test_delete_data_source():
    r = requests.delete(f"{BASE_URL}/api/data-sources/{_state['source_id']}",
                        headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


# -------- Integrations: Slack / GitHub / GDrive --------
def test_slack_test_endpoint():
    r = requests.get(f"{BASE_URL}/api/integrations/slack/test", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


def test_github_test_endpoint():
    r = requests.get(f"{BASE_URL}/api/integrations/github/test", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


def test_gdrive_test_endpoint():
    r = requests.get(f"{BASE_URL}/api/integrations/gdrive/test", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


def test_slack_sync_upserts_data_source():
    r = requests.post(f"{BASE_URL}/api/integrations/slack/sync",
                      headers=HEADERS, timeout=120)
    assert r.status_code == 200  # response may say success=False (scope), but endpoint must work


def test_gdrive_sync_upserts_data_source():
    r = requests.post(f"{BASE_URL}/api/integrations/gdrive/sync",
                      headers=HEADERS, timeout=180)
    assert r.status_code == 200


# -------- Neo4j --------
def test_neo4j_status():
    r = requests.get(f"{BASE_URL}/api/neo4j/status", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


def test_neo4j_stats():
    r = requests.get(f"{BASE_URL}/api/neo4j/stats", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


def test_neo4j_graph():
    r = requests.get(f"{BASE_URL}/api/neo4j/graph", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


# -------- Elasticsearch --------
def test_es_status():
    r = requests.get(f"{BASE_URL}/api/elasticsearch/status", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


def test_search_full():
    payload = {"query": "TEST", "filters": {}, "limit": 5}
    r = requests.post(f"{BASE_URL}/api/search/full",
                      headers=HEADERS, json=payload, timeout=TIMEOUT)
    assert r.status_code == 200


def test_search_autocomplete():
    r = requests.get(f"{BASE_URL}/api/search/autocomplete?q=TE",
                     headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    assert "suggestions" in r.json()


def test_search_stats():
    r = requests.get(f"{BASE_URL}/api/search/stats", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200


# -------- Activities --------
def test_activities():
    r = requests.get(f"{BASE_URL}/api/activities", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # We've created nodes & connected them, so activities should exist.
    assert len(data) >= 1


# -------- Document Upload --------
def test_document_upload():
    files = {"file": ("test_supabase.txt", io.BytesIO(b"CorteQS supabase migration test document. Topic: graph database. Person: Test User."), "text/plain")}
    headers_no_ct = {"Authorization": f"Bearer {TOKEN}"}
    r = requests.post(f"{BASE_URL}/api/documents/upload",
                      headers=headers_no_ct, files=files, timeout=120)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "document" in data
    assert "knowledge_node_id" in data
    assert "ai_extraction" in data
    _state["document_id"] = data["document"]["document_id"]


def test_documents_list():
    r = requests.get(f"{BASE_URL}/api/documents", headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    data = r.json()
    assert any(d["document_id"] == _state["document_id"] for d in data["documents"])


def test_document_get_one():
    r = requests.get(f"{BASE_URL}/api/documents/{_state['document_id']}",
                     headers=HEADERS, timeout=TIMEOUT)
    assert r.status_code == 200
    assert r.json()["document_id"] == _state["document_id"]
