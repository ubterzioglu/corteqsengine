"""External integrations: Slack, GitHub, Google Drive."""
import asyncio
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from database import get_supabase
from dependencies import get_current_user, log_activity
from models import User
from services.data_sync_service import data_sync_service
from services.gdrive_service import gdrive_service
from services.github_service import github_service
from services.slack_service import slack_service

router = APIRouter(prefix="/api/integrations", tags=["integrations"])


@router.get("/status")
async def integrations_status(user: User = Depends(get_current_user)):
    return await data_sync_service.get_integration_status()


# -------- SLACK --------
@router.get("/slack/test")
async def slack_test(user: User = Depends(get_current_user)):
    return slack_service.test_connection()


@router.get("/slack/channels")
async def slack_channels(user: User = Depends(get_current_user)):
    channels = slack_service.get_channels()
    return {"channels": channels, "count": len(channels)}


@router.get("/slack/users")
async def slack_users(user: User = Depends(get_current_user)):
    users = slack_service.get_users()
    return {"users": users, "count": len(users)}


@router.post("/slack/sync")
async def slack_sync(user: User = Depends(get_current_user)):
    sb = get_supabase()
    result = await data_sync_service.sync_slack_data(user.user_id)
    if result.get("success"):
        await log_activity(user.user_id, "slack_sync", f"Synced Slack data: {result.get('stats')}")
        await sb.from_("data_sources").upsert({
            "source_id": f"src_slack_{user.user_id}",
            "user_id": user.user_id,
            "source_type": "slack",
            "name": "Slack",
            "status": "connected",
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "config": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,source_type").execute()
    return result


# -------- GITHUB --------
@router.get("/github/test")
async def github_test(user: User = Depends(get_current_user)):
    return github_service.test_connection()


@router.get("/github/repos")
async def github_repos(user: User = Depends(get_current_user)):
    repos = github_service.get_user_repos()
    return {"repositories": repos, "count": len(repos)}


@router.get("/github/repos/{owner}/{repo}")
async def github_repo_details(owner: str, repo: str, user: User = Depends(get_current_user)):
    details = github_service.get_repo_details(f"{owner}/{repo}")
    if not details:
        raise HTTPException(status_code=404, detail="Repository not found")
    return details


@router.get("/github/repos/{owner}/{repo}/issues")
async def github_issues(owner: str, repo: str, state: str = "open", user: User = Depends(get_current_user)):
    issues = github_service.get_repo_issues(f"{owner}/{repo}", state=state)
    return {"issues": issues, "count": len(issues)}


@router.get("/github/repos/{owner}/{repo}/pulls")
async def github_pulls(owner: str, repo: str, state: str = "open", user: User = Depends(get_current_user)):
    prs = github_service.get_repo_pull_requests(f"{owner}/{repo}", state=state)
    return {"pull_requests": prs, "count": len(prs)}


@router.post("/github/sync")
async def github_sync(user: User = Depends(get_current_user)):
    sb = get_supabase()
    result = await data_sync_service.sync_github_data(user.user_id)
    if result.get("success"):
        await log_activity(user.user_id, "github_sync", f"Synced GitHub data: {result.get('stats')}")
        await sb.from_("data_sources").upsert({
            "source_id": f"src_github_{user.user_id}",
            "user_id": user.user_id,
            "source_type": "github",
            "name": "GitHub",
            "status": "connected",
            "last_sync": datetime.now(timezone.utc).isoformat(),
            "config": {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="user_id,source_type").execute()
    return result


# -------- GOOGLE DRIVE --------
@router.get("/gdrive/test")
async def gdrive_test(user: User = Depends(get_current_user)):
    return gdrive_service.test_connection()


@router.get("/gdrive/files")
async def gdrive_files(folder_id: Optional[str] = None, user: User = Depends(get_current_user)):
    files = gdrive_service.list_files(folder_id=folder_id)
    return {"files": files, "count": len(files)}


@router.get("/gdrive/folders")
async def gdrive_folders(parent_id: Optional[str] = None, user: User = Depends(get_current_user)):
    folders = gdrive_service.list_folders(parent_id=parent_id)
    return {"folders": folders, "count": len(folders)}


@router.get("/gdrive/recent")
async def gdrive_recent(user: User = Depends(get_current_user)):
    files = gdrive_service.get_recent_files(limit=20)
    return {"files": files, "count": len(files)}


@router.get("/gdrive/search")
async def gdrive_search(q: str = Query(..., min_length=2), user: User = Depends(get_current_user)):
    files = gdrive_service.search_files(q)
    return {"files": files, "count": len(files), "query": q}


@router.post("/gdrive/sync")
async def gdrive_sync(
    folder_id: Optional[str] = None,
    recursive: bool = Query(default=True, description="Recursively sync subfolders"),
    max_depth: int = Query(default=5, ge=0, le=20, description="Max recursion depth (0 = current folder only)"),
    wait: bool = Query(default=False, description="If true, block until sync completes (may exceed proxy timeout)"),
    user: User = Depends(get_current_user),
):
    """Start a Google Drive sync. Returns immediately with status='started'
    unless `wait=true`. Long recursive syncs are run as a background task to
    avoid the 60s ingress timeout."""
    sb = get_supabase()
    source_id = f"src_gdrive_{user.user_id}"
    started_at = datetime.now(timezone.utc).isoformat()

    await sb.from_("data_sources").upsert({
        "source_id": source_id,
        "user_id": user.user_id,
        "source_type": "gdrive",
        "name": "Google Drive",
        "status": "syncing",
        "last_sync": started_at,
        "config": {
            "recursive": recursive,
            "max_depth": max_depth,
            "folder_id": folder_id,
            "started_at": started_at,
        },
        "created_at": started_at,
    }, on_conflict="user_id,source_type").execute()

    async def run_sync():
        result = await data_sync_service.sync_gdrive_data(
            user_id=user.user_id,
            folder_id=folder_id,
            recursive=recursive,
            max_depth=max_depth,
        )
        finished_at = datetime.now(timezone.utc).isoformat()
        await sb.from_("data_sources").update({
            "status": "connected" if result.get("success") else "error",
            "last_sync": finished_at,
            "config": {
                "recursive": recursive,
                "max_depth": max_depth,
                "folder_id": folder_id,
                "started_at": started_at,
                "finished_at": finished_at,
                "stats": result.get("stats"),
                "error": result.get("error"),
            },
        }).eq("source_id", source_id).execute()
        if result.get("success"):
            await log_activity(
                user.user_id, "gdrive_sync",
                f"Synced Google Drive (recursive={recursive}, depth={max_depth}): {result.get('stats')}",
            )
        return result

    if wait:
        return await run_sync()

    asyncio.create_task(run_sync())
    return {
        "success": True,
        "status": "started",
        "message": "Sync running in background. Poll GET /api/data-sources to see progress.",
        "started_at": started_at,
        "config": {"recursive": recursive, "max_depth": max_depth, "folder_id": folder_id},
    }
