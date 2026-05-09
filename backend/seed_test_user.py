"""Seed a test user and session for backend testing."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env.local")
load_dotenv(ROOT_DIR / ".env", override=False)

import asyncio
from datetime import datetime, timezone, timedelta
from database import init_supabase, get_supabase

TEST_USER_ID = os.environ.get("TEST_USER_ID", "user_test123456")
TEST_EMAIL = os.environ.get("TEST_EMAIL", "test@corteqs.com")
TEST_TOKEN = os.environ.get("TEST_SESSION_TOKEN", "test_session_corteqs")


async def seed():
    await init_supabase()
    sb = get_supabase()

    await sb.from_("users").upsert({
        "user_id": TEST_USER_ID,
        "email": TEST_EMAIL,
        "name": "Test User",
        "picture": None,
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id").execute()

    await sb.from_("user_sessions").upsert({
        "user_id": TEST_USER_ID,
        "session_token": TEST_TOKEN,
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="user_id").execute()

    print(f"Seeded user {TEST_USER_ID} with token {TEST_TOKEN}")


if __name__ == "__main__":
    asyncio.run(seed())
