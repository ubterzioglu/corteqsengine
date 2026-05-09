"""
GitHub Integration Service
Fetches repositories, issues, pull requests, and contributors from GitHub
"""

import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from github import Github, GithubException, Auth

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")


class GitHubService:
    def __init__(self):
        if GITHUB_TOKEN and GITHUB_TOKEN != "placeholder":
            auth = Auth.Token(GITHUB_TOKEN)
            self.client = Github(auth=auth)
            self.is_configured = True
        else:
            self.client = None
            self.is_configured = False
    
    def get_user_repos(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get repositories for authenticated user"""
        if not self.is_configured:
            return []
        
        try:
            repos = []
            for repo in self.client.get_user().get_repos()[:limit]:
                try:
                    topics = repo.get_topics()
                except GithubException:
                    topics = []
                
                repos.append({
                    "id": repo.id,
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "url": repo.html_url,
                    "private": repo.private,
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "open_issues": repo.open_issues_count,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    "topics": topics
                })
            return repos
        except GithubException as e:
            print(f"GitHub API Error: {e}")
            return []
    
    def get_repo_details(self, repo_full_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a specific repository"""
        if not self.is_configured:
            return None
        
        try:
            repo = self.client.get_repo(repo_full_name)
            return {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "url": repo.html_url,
                "private": repo.private,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
                "open_issues": repo.open_issues_count,
                "watchers": repo.watchers_count,
                "default_branch": repo.default_branch,
                "created_at": repo.created_at.isoformat() if repo.created_at else None,
                "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                "topics": repo.get_topics(),
                "readme": self._get_readme(repo)
            }
        except GithubException as e:
            print(f"GitHub API Error: {e}")
            return None
    
    def _get_readme(self, repo) -> Optional[str]:
        """Get README content"""
        try:
            readme = repo.get_readme()
            return readme.decoded_content.decode("utf-8")[:5000]  # Limit content
        except (GithubException, UnicodeDecodeError):
            return None
    
    def get_repo_issues(
        self, 
        repo_full_name: str, 
        state: str = "open",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get issues from a repository"""
        if not self.is_configured:
            return []
        
        try:
            repo = self.client.get_repo(repo_full_name)
            issues = []
            
            for issue in repo.get_issues(state=state)[:limit]:
                if issue.pull_request is None:  # Exclude PRs
                    issues.append({
                        "id": issue.id,
                        "number": issue.number,
                        "title": issue.title,
                        "body": issue.body[:1000] if issue.body else None,
                        "state": issue.state,
                        "url": issue.html_url,
                        "user": issue.user.login if issue.user else None,
                        "labels": [lbl.name for lbl in issue.labels],
                        "comments": issue.comments,
                        "created_at": issue.created_at.isoformat() if issue.created_at else None,
                        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None
                    })
            
            return issues
        except GithubException as e:
            print(f"GitHub API Error: {e}")
            return []
    
    def get_repo_pull_requests(
        self, 
        repo_full_name: str, 
        state: str = "open",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get pull requests from a repository"""
        if not self.is_configured:
            return []
        
        try:
            repo = self.client.get_repo(repo_full_name)
            prs = []
            
            for pr in repo.get_pulls(state=state)[:limit]:
                prs.append({
                    "id": pr.id,
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body[:1000] if pr.body else None,
                    "state": pr.state,
                    "url": pr.html_url,
                    "user": pr.user.login if pr.user else None,
                    "draft": pr.draft,
                    "merged": pr.merged,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None,
                    "updated_at": pr.updated_at.isoformat() if pr.updated_at else None
                })
            
            return prs
        except GithubException as e:
            print(f"GitHub API Error: {e}")
            return []
    
    def get_repo_contributors(
        self, 
        repo_full_name: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get contributors for a repository"""
        if not self.is_configured:
            return []
        
        try:
            repo = self.client.get_repo(repo_full_name)
            contributors = []
            
            for contrib in repo.get_contributors()[:limit]:
                contributors.append({
                    "id": contrib.id,
                    "login": contrib.login,
                    "name": contrib.name,
                    "avatar": contrib.avatar_url,
                    "url": contrib.html_url,
                    "contributions": contrib.contributions
                })
            
            return contributors
        except GithubException as e:
            print(f"GitHub API Error: {e}")
            return []
    
    def get_recent_commits(
        self, 
        repo_full_name: str,
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """Get recent commits from a repository"""
        if not self.is_configured:
            return []
        
        try:
            repo = self.client.get_repo(repo_full_name)
            commits = []
            
            for commit in repo.get_commits()[:limit]:
                commits.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name if commit.commit.author else None,
                    "author_email": commit.commit.author.email if commit.commit.author else None,
                    "date": commit.commit.author.date.isoformat() if commit.commit.author else None,
                    "url": commit.html_url,
                    "additions": commit.stats.additions if commit.stats else 0,
                    "deletions": commit.stats.deletions if commit.stats else 0
                })
            
            return commits
        except GithubException as e:
            print(f"GitHub API Error: {e}")
            return []
    
    def test_connection(self) -> Dict[str, Any]:
        """Test GitHub connection and return user info"""
        if not self.is_configured:
            return {"connected": False, "error": "GitHub token not configured"}
        
        try:
            user = self.client.get_user()
            return {
                "connected": True,
                "login": user.login,
                "name": user.name,
                "email": user.email,
                "avatar": user.avatar_url,
                "repos_count": (user.public_repos or 0) + (user.total_private_repos or 0)
            }
        except GithubException as e:
            return {"connected": False, "error": str(e)}


# Singleton instance
github_service = GitHubService()
