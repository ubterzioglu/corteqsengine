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
                node_id = f"slack_user_{user['id']}"
                
                # Create in Neo4j
                if neo4j_service.driver:
                    await neo4j_service.create_node(
                        node_id=node_id,
                        node_type="person",
                        title=user.get("real_name") or user.get("name"),
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
                        title=user.get("real_name") or user.get("name"),
                        content=f"Slack user: {user.get('email', 'N/A')} - {user.get('title', '')}",
                        source_type="slack",
                        tags=["slack", "user", "person"]
                    )
                
                stats["users"] += 1
            
            # Sync channels
            slack_channels = slack_service.get_channels()
            for channel in slack_channels:
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
                            
                            # Link to user if available
                            if msg.get("user_id"):
                                await neo4j_service.create_relationship(
                                    f"slack_user_{msg['user_id']}", msg_node_id, "AUTHORED"
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
            
            return {"success": True, "stats": stats}
        
        except Exception as e:
            return {"success": False, "error": str(e), "stats": stats}
    
    async def sync_github_data(self, user_id: str, repos: List[str] = None) -> Dict[str, Any]:
        """Sync GitHub data to knowledge graph"""
        if not github_service.is_configured:
            return {"success": False, "error": "GitHub not configured"}
        
        stats = {"repos": 0, "issues": 0, "prs": 0, "contributors": 0}
        
        try:
            # Get repositories
            github_repos = github_service.get_user_repos()
            
            for repo in github_repos:
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
                            "url": repo["url"],
                            "language": repo.get("language"),
                            "stars": repo.get("stars"),
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
                        tags=["github", "repository", repo.get("language", "")]
                    )
                
                stats["repos"] += 1
                
                # Sync issues
                issues = github_service.get_repo_issues(repo["full_name"], limit=20)
                for issue in issues:
                    issue_node_id = f"github_issue_{repo['id']}_{issue['number']}"
                    
                    if neo4j_service.driver:
                        await neo4j_service.create_node(
                            node_id=issue_node_id,
                            node_type="document",
                            title=f"Issue #{issue['number']}: {issue['title']}",
                            content=issue.get("body", ""),
                            metadata={
                                "github_id": issue["id"],
                                "number": issue["number"],
                                "state": issue["state"],
                                "labels": issue.get("labels", [])
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
                            content=issue.get("body", ""),
                            source_type="github",
                            tags=["github", "issue"] + issue.get("labels", [])
                        )
                    
                    stats["issues"] += 1
                
                # Sync PRs
                prs = github_service.get_repo_pull_requests(repo["full_name"], limit=20)
                for pr in prs:
                    pr_node_id = f"github_pr_{repo['id']}_{pr['number']}"
                    
                    if neo4j_service.driver:
                        await neo4j_service.create_node(
                            node_id=pr_node_id,
                            node_type="document",
                            title=f"PR #{pr['number']}: {pr['title']}",
                            content=pr.get("body", ""),
                            metadata={
                                "github_id": pr["id"],
                                "number": pr["number"],
                                "state": pr["state"],
                                "draft": pr.get("draft"),
                                "merged": pr.get("merged")
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
                            content=pr.get("body", ""),
                            source_type="github",
                            tags=["github", "pull-request"]
                        )
                    
                    stats["prs"] += 1
                
                # Sync contributors
                contributors = github_service.get_repo_contributors(repo["full_name"], limit=10)
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
                                "login": contrib["login"],
                                "url": contrib["url"]
                            },
                            user_id=user_id
                        )
                        
                        await neo4j_service.create_relationship(
                            contrib_node_id, repo_node_id, "CONTRIBUTES_TO"
                        )
                    
                    stats["contributors"] += 1
            
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
        
        # Neo4j
        neo4j_test = await neo4j_service.test_connection()
        status["neo4j"] = neo4j_test
        
        # Elasticsearch
        es_test = await elasticsearch_service.test_connection()
        status["elasticsearch"] = es_test
        
        return status


# Singleton instance
data_sync_service = DataSyncService()
