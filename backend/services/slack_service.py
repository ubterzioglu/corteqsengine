"""
Slack Integration Service
Fetches messages, channels, and users from Slack workspace
"""

import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")


class SlackService:
    def __init__(self):
        self.client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None
        self.is_configured = bool(SLACK_BOT_TOKEN and SLACK_BOT_TOKEN != "placeholder")
    
    def get_channels(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get list of channels the bot has access to"""
        if not self.is_configured:
            return []
        
        try:
            response = self.client.conversations_list(
                types="public_channel,private_channel",
                limit=limit
            )
            channels = []
            for channel in response.get("channels", []):
                channels.append({
                    "id": channel["id"],
                    "name": channel["name"],
                    "is_private": channel.get("is_private", False),
                    "num_members": channel.get("num_members", 0),
                    "topic": channel.get("topic", {}).get("value", ""),
                    "purpose": channel.get("purpose", {}).get("value", "")
                })
            return channels
        except SlackApiError as e:
            print(f"Slack API Error: {e.response['error']}")
            return []
    
    def get_channel_messages(
        self, 
        channel_id: str, 
        limit: int = 100,
        oldest: Optional[str] = None,
        latest: Optional[str] = None,
        auto_join: bool = True
    ) -> List[Dict[str, Any]]:
        """Get messages from a specific channel.

        If the bot is not in the channel and `auto_join` is True, it will try
        to join the channel automatically (requires `channels:join` scope).
        """
        if not self.is_configured:
            return []

        def _fetch():
            params = {"channel": channel_id, "limit": limit}
            if oldest:
                params["oldest"] = oldest
            if latest:
                params["latest"] = latest
            response = self.client.conversations_history(**params)
            messages = []
            for msg in response.get("messages", []):
                messages.append({
                    "ts": msg.get("ts"),
                    "user_id": msg.get("user"),
                    "text": msg.get("text", ""),
                    "type": msg.get("type"),
                    "thread_ts": msg.get("thread_ts"),
                    "reply_count": msg.get("reply_count", 0),
                    "reactions": msg.get("reactions", []),
                    "timestamp": datetime.fromtimestamp(
                        float(msg.get("ts", 0)),
                        tz=timezone.utc
                    ).isoformat()
                })
            return messages

        try:
            return _fetch()
        except SlackApiError as e:
            err = e.response.get("error")
            # Auto-join if the bot is not yet a member of the channel
            if err == "not_in_channel" and auto_join:
                try:
                    self.client.conversations_join(channel=channel_id)
                    return _fetch()
                except SlackApiError as join_err:
                    print(f"Slack auto-join failed for {channel_id}: {join_err.response.get('error')}")
                    return []
            print(f"Slack API Error ({channel_id}): {err}")
            return []
    
    def get_users(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Get list of workspace users"""
        if not self.is_configured:
            return []
        
        try:
            response = self.client.users_list(limit=limit)
            users = []
            
            for user in response.get("members", []):
                if not user.get("is_bot") and not user.get("deleted"):
                    profile = user.get("profile", {})
                    users.append({
                        "id": user["id"],
                        "name": user.get("name"),
                        "real_name": user.get("real_name") or profile.get("real_name"),
                        "email": profile.get("email"),
                        "title": profile.get("title"),
                        "avatar": profile.get("image_72"),
                        "status": profile.get("status_text"),
                        "is_admin": user.get("is_admin", False)
                    })
            
            return users
        except SlackApiError as e:
            print(f"Slack API Error: {e.response['error']}")
            return []
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed info for a specific user"""
        if not self.is_configured:
            return None
        
        try:
            response = self.client.users_info(user=user_id)
            user = response.get("user", {})
            profile = user.get("profile", {})
            
            return {
                "id": user["id"],
                "name": user.get("name"),
                "real_name": user.get("real_name") or profile.get("real_name"),
                "email": profile.get("email"),
                "title": profile.get("title"),
                "avatar": profile.get("image_192"),
                "status": profile.get("status_text"),
                "is_admin": user.get("is_admin", False)
            }
        except SlackApiError as e:
            print(f"Slack API Error: {e.response['error']}")
            return None
    
    def test_connection(self) -> Dict[str, Any]:
        """Test Slack connection and return workspace info"""
        if not self.is_configured:
            return {"connected": False, "error": "Slack token not configured"}
        
        try:
            response = self.client.auth_test()
            return {
                "connected": True,
                "team": response.get("team"),
                "team_id": response.get("team_id"),
                "user": response.get("user"),
                "bot_id": response.get("bot_id")
            }
        except SlackApiError as e:
            return {"connected": False, "error": e.response.get("error", str(e))}


# Singleton instance
slack_service = SlackService()
