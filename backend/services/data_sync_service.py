"""
Data Sync Service
Orchestrates data synchronization from external sources to Knowledge Graph
"""

import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from .slack_service import slack_service
from .github_service import github_service
from .neo4j_service import neo4j_service
from .elasticsearch_service import elasticsearch_service
from .gdrive_service import gdrive_service


class DataSyncService:
    """Coordinates data sync from external services to Neo4j and Elasticsearch"""
    
    async def sync_slack_data(self, user_id: str, channels: List[str] = None) -> Dict[str, Any]:
        """Sync Slack data to knowledge graph"""
        if not slack_service.is_configured:
            return {"success": False, "error": "Slack not configured"}
        
        stats = {"users": 0, "channels": 0, "messages": 0}
        
        try:
            # Sync users as Person nodes
            users = slack_service.get_users()
            for user in users:
                try:
                    node_id = f"slack_user_{user['id']}"
                    
                    # Create in Neo4j
                    if neo4j_service.driver:
                        await neo4j_service.create_node(
                            node_id=node_id,
                            node_type="person",
                            title=user.get("real_name") or user.get("name", "Unknown"),
                            content=f"Slack user: {user.get('email', 'N/A')} - {user.get('title', '')}",
                            metadata={"slack_id": user["id"], "email": user.get("email")},
                            user_id=user_id
                        )
                    
                    # Index in Elasticsearch
                    if elasticsearch_service.client:
                        await elasticsearch_service.index_node(
                            node_id=node_id,
                            user_id=user_id,
                            node_type="person",
                            title=user.get("real_name") or user.get("name", "Unknown"),
                            content=f"Slack user: {user.get('email', 'N/A')} - {user.get('title', '')}",
                            source_type="slack",
                            tags=["slack", "user", "person"]
                        )
                    
                    stats["users"] += 1
                except Exception as e:
                    print(f"Error syncing Slack user {user.get('id')}: {e}")
            
            # Sync channels
            slack_channels = slack_service.get_channels()
            for channel in slack_channels:
                try:
                    if channels and channel["id"] not in channels:
                        continue
                    
                    channel_node_id = f"slack_channel_{channel['id']}"
                    
                    # Create channel node
                    if neo4j_service.driver:
                        await neo4j_service.create_node(
                            node_id=channel_node_id,
                            node_type="topic",
                            title=f"#{channel['name']}",
                            content=channel.get("purpose") or channel.get("topic", ""),
                            metadata={"slack_id": channel["id"]},
                            user_id=user_id
                        )
                    
                    # Get and sync messages
                    messages = slack_service.get_channel_messages(channel["id"], limit=50)
                    for msg in messages:
                        if msg.get("text"):
                            msg_node_id = f"slack_msg_{channel['id']}_{msg['ts']}"
                            
                            if neo4j_service.driver:
                                await neo4j_service.create_node(
                                    node_id=msg_node_id,
                                    node_type="document",
                                    title=msg["text"][:100],
                                    content=msg["text"],
                                    metadata={
                                        "slack_ts": msg["ts"],
                                        "channel_id": channel["id"]
                                    },
                                    user_id=user_id
                                )
                                
                                # Link message to channel
                                await neo4j_service.create_relationship(
                                    msg_node_id, channel_node_id, "POSTED_IN"
                                )
                            
                            if elasticsearch_service.client:
                                await elasticsearch_service.index_node(
                                    node_id=msg_node_id,
                                    user_id=user_id,
                                    node_type="document",
                                    title=msg["text"][:100],
                                    content=msg["text"],
                                    source_type="slack",
                                    tags=["slack", "message", channel["name"]]
                                )
                            
                            stats["messages"] += 1
                    
                    stats["channels"] += 1
                except Exception as e:
                    print(f"Error syncing Slack channel {channel.get('id')}: {e}")
            
            return {"success": True, "stats": stats}
        
        except Exception as e:
            return {"success": False, "error": str(e), "stats": stats}
    
    async def sync_github_data(self, user_id: str, repos: List[str] = None) -> Dict[str, Any]:
        """Sync GitHub data to knowledge graph"""
        if not github_service.is_configured:
            return {"success": False, "error": "GitHub not configured"}
        
        stats = {"repos": 0, "issues": 0, "prs": 0, "contributors": 0}
        
        try:
            # Get repositories (limited for safety)
            github_repos = github_service.get_user_repos(limit=10)
            
            for repo in github_repos:
                try:
                    if repos and repo["full_name"] not in repos:
                        continue
                    
                    repo_node_id = f"github_repo_{repo['id']}"
                    
                    # Create repository node
                    if neo4j_service.driver:
                        await neo4j_service.create_node(
                            node_id=repo_node_id,
                            node_type="project",
                            title=repo["name"],
                            content=repo.get("description", "") or f"GitHub repository: {repo['full_name']}",
                            metadata={
                                "github_id": repo["id"],
                                "full_name": repo["full_name"],
                                "url": repo.get("url", ""),
                                "language": repo.get("language"),
                                "stars": repo.get("stars", 0),
                                "topics": repo.get("topics", [])
                            },
                            user_id=user_id
                        )
                    
                    if elasticsearch_service.client:
                        await elasticsearch_service.index_node(
                            node_id=repo_node_id,
                            user_id=user_id,
                            node_type="project",
                            title=repo["name"],
                            content=repo.get("description", "") or f"GitHub repository: {repo['full_name']}",
                            source_type="github",
                            tags=["github", "repository", repo.get("language") or ""]
                        )
                    
                    stats["repos"] += 1
                    
                    # Sync issues
                    try:
                        issues = github_service.get_repo_issues(repo["full_name"], limit=5)
                        for issue in issues:
                            issue_node_id = f"github_issue_{repo['id']}_{issue['number']}"
                            
                            if neo4j_service.driver:
                                await neo4j_service.create_node(
                                    node_id=issue_node_id,
                                    node_type="document",
                                    title=f"Issue #{issue['number']}: {issue['title']}",
                                    content=issue.get("body", "") or "",
                                    metadata={
                                        "github_id": issue["id"],
                                        "number": issue["number"],
                                        "state": issue["state"]
                                    },
                                    user_id=user_id
                                )
                                await neo4j_service.create_relationship(
                                    issue_node_id, repo_node_id, "BELONGS_TO"
                                )
                            
                            if elasticsearch_service.client:
                                await elasticsearch_service.index_node(
                                    node_id=issue_node_id,
                                    user_id=user_id,
                                    node_type="document",
                                    title=f"Issue #{issue['number']}: {issue['title']}",
                                    content=issue.get("body", "") or "",
                                    source_type="github",
                                    tags=["github", "issue"]
                                )
                            
                            stats["issues"] += 1
                    except Exception as e:
                        print(f"Error syncing issues for {repo['full_name']}: {e}")
                    
                    # Sync PRs
                    try:
                        prs = github_service.get_repo_pull_requests(repo["full_name"], limit=5)
                        for pr in prs:
                            pr_node_id = f"github_pr_{repo['id']}_{pr['number']}"
                            
                            if neo4j_service.driver:
                                await neo4j_service.create_node(
                                    node_id=pr_node_id,
                                    node_type="document",
                                    title=f"PR #{pr['number']}: {pr['title']}",
                                    content=pr.get("body", "") or "",
                                    metadata={
                                        "github_id": pr["id"],
                                        "number": pr["number"],
                                        "state": pr["state"]
                                    },
                                    user_id=user_id
                                )
                                await neo4j_service.create_relationship(
                                    pr_node_id, repo_node_id, "BELONGS_TO"
                                )
                            
                            if elasticsearch_service.client:
                                await elasticsearch_service.index_node(
                                    node_id=pr_node_id,
                                    user_id=user_id,
                                    node_type="document",
                                    title=f"PR #{pr['number']}: {pr['title']}",
                                    content=pr.get("body", "") or "",
                                    source_type="github",
                                    tags=["github", "pull-request"]
                                )
                            
                            stats["prs"] += 1
                    except Exception as e:
                        print(f"Error syncing PRs for {repo['full_name']}: {e}")
                    
                    # Sync contributors
                    try:
                        contributors = github_service.get_repo_contributors(repo["full_name"], limit=5)
                        for contrib in contributors:
                            contrib_node_id = f"github_user_{contrib['id']}"
                            
                            if neo4j_service.driver:
                                await neo4j_service.create_node(
                                    node_id=contrib_node_id,
                                    node_type="person",
                                    title=contrib.get("name") or contrib["login"],
                                    content=f"GitHub contributor: {contrib['login']}",
                                    metadata={
                                        "github_id": contrib["id"],
                                        "login": contrib["login"]
                                    },
                                    user_id=user_id
                                )
                                await neo4j_service.create_relationship(
                                    contrib_node_id, repo_node_id, "CONTRIBUTES_TO"
                                )
                            
                            stats["contributors"] += 1
                    except Exception as e:
                        print(f"Error syncing contributors for {repo['full_name']}: {e}")
                        
                except Exception as e:
                    print(f"Error syncing repo {repo.get('full_name', 'unknown')}: {e}")
                    continue
            
            return {"success": True, "stats": stats}
        
        except Exception as e:
            return {"success": False, "error": str(e), "stats": stats}
    
    async def get_integration_status(self) -> Dict[str, Any]:
        """Get status of all integrations"""
        status = {}
        
        # Slack
        slack_test = slack_service.test_connection()
        status["slack"] = slack_test
        
        # GitHub
        github_test = github_service.test_connection()
        status["github"] = github_test
        
        # Google Drive
        gdrive_test = gdrive_service.test_connection()
        status["gdrive"] = gdrive_test
        
        # Neo4j
        neo4j_test = await neo4j_service.test_connection()
        status["neo4j"] = neo4j_test
        
        # Elasticsearch
        es_test = await elasticsearch_service.test_connection()
        status["elasticsearch"] = es_test
        
        return status
    
    async def sync_gdrive_data(
        self,
        user_id: str,
        folder_id: str = None,
        recursive: bool = True,
        max_depth: int = 5,
        page_size: int = 100,
    ) -> Dict[str, Any]:
        """Sync Google Drive data to knowledge graph (optionally recursive into subfolders)."""
        if not gdrive_service.is_configured:
            return {"success": False, "error": "Google Drive not configured"}

        stats = {"files": 0, "folders": 0, "documents_extracted": 0, "max_depth_reached": 0}
        visited: set = set()

        try:
            await self._sync_gdrive_folder(
                user_id=user_id,
                folder_id=folder_id,
                parent_node_id=None,
                depth=0,
                max_depth=max_depth if recursive else 0,
                page_size=page_size,
                stats=stats,
                visited=visited,
            )
            return {"success": True, "stats": stats}
        except Exception as e:
            return {"success": False, "error": str(e), "stats": stats}

    async def _sync_gdrive_folder(
        self,
        user_id: str,
        folder_id: Optional[str],
        parent_node_id: Optional[str],
        depth: int,
        max_depth: int,
        page_size: int,
        stats: Dict[str, int],
        visited: set,
    ) -> None:
        """Sync all files in a single folder, recursing into subfolders up to max_depth."""
        if folder_id and folder_id in visited:
            return
        if folder_id:
            visited.add(folder_id)

        if depth > stats.get("max_depth_reached", 0):
            stats["max_depth_reached"] = depth

        files = gdrive_service.list_files(folder_id=folder_id, page_size=page_size)

        for file in files:
            try:
                file_node_id = f"gdrive_file_{file['id']}"
                is_folder = file["is_folder"]

                if is_folder:
                    node_type = "topic"
                    stats["folders"] += 1
                else:
                    node_type = "document"
                    stats["files"] += 1

                # Extract textual content for Google-native docs (skip folders & binaries)
                content = ""
                if not is_folder and file["mime_type"] in (
                    "application/vnd.google-apps.document",
                    "application/vnd.google-apps.spreadsheet",
                    "application/vnd.google-apps.presentation",
                ):
                    content = gdrive_service.get_file_content(file["id"], file["mime_type"]) or ""
                    if content:
                        stats["documents_extracted"] += 1

                if neo4j_service.driver:
                    await neo4j_service.create_node(
                        node_id=file_node_id,
                        node_type=node_type,
                        title=file["name"],
                        content=content[:5000] if content else f"Google Drive {'folder' if is_folder else 'file'}: {file['name']}",
                        metadata={
                            "gdrive_id": file["id"],
                            "mime_type": file["mime_type"],
                            "web_link": file.get("web_link"),
                            "owners": file.get("owners", []),
                            "modified_at": file.get("modified_at"),
                            "depth": depth,
                        },
                        user_id=user_id,
                    )
                    if parent_node_id:
                        await neo4j_service.create_relationship(
                            file_node_id, parent_node_id, "CONTAINED_IN"
                        )

                if elasticsearch_service.client:
                    await elasticsearch_service.index_node(
                        node_id=file_node_id,
                        user_id=user_id,
                        node_type=node_type,
                        title=file["name"],
                        content=content[:10000] if content else f"Google Drive {'folder' if is_folder else 'file'}: {file['name']}",
                        source_type="gdrive",
                        tags=["gdrive", "folder" if is_folder else (file["mime_type"].split(".")[-1] if "." in file["mime_type"] else "file")],
                    )

                # Recurse into subfolder
                if is_folder and depth < max_depth:
                    await self._sync_gdrive_folder(
                        user_id=user_id,
                        folder_id=file["id"],
                        parent_node_id=file_node_id,
                        depth=depth + 1,
                        max_depth=max_depth,
                        page_size=page_size,
                        stats=stats,
                        visited=visited,
                    )

            except Exception as e:
                print(f"Error syncing GDrive item {file.get('name')}: {e}")


# Singleton instance
data_sync_service = DataSyncService()
