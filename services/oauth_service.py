import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from atlassian_oauth import AtlassianOAuthClient

class OAuthService:
    def __init__(self):
        self.oauth_client = AtlassianOAuthClient()
        self.user_tokens: Dict[str, Dict[str, Any]] = {}
    
    async def get_authorization_url(self, user_id: str) -> tuple[str, str]:
        """Get authorization URL for a specific user"""
        auth_url, state, oauth_session = self.oauth_client.get_authorization_url()
        
        # Store OAuth session state for this user
        self.user_tokens[user_id] = {
            "oauth_session": oauth_session,
            "state": state,
            "auth_url": auth_url,
            "timestamp": datetime.now()
        }
        
        return auth_url, state
    
    async def handle_oauth_callback(self, user_id: str, code: str, state: str) -> Dict[str, Any]:
        """Handle OAuth callback and exchange code for token"""
        if user_id not in self.user_tokens:
            raise Exception("No OAuth session found for user")
        
        user_session = self.user_tokens[user_id]
        
        # State validation is handled by the router/main app
        # We'll just verify the session exists and exchange the code
        
        # Exchange code for token
        oauth_session = user_session["oauth_session"]
        token = await self.oauth_client.get_access_token(code, oauth_session)
        
        # Store token for user
        self.user_tokens[user_id] = {
            **user_session,
            "token": token,
            "token_timestamp": datetime.now()
        }
        
        return token
    
    async def get_valid_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get valid token for user (refresh if needed)"""
        if user_id not in self.user_tokens or "token" not in self.user_tokens[user_id]:
            return None
        
        user_session = self.user_tokens[user_id]
        token = user_session["token"]
        
        # Check if token needs refresh (simplified - you might want more sophisticated logic)
        token_age = datetime.now() - user_session.get("token_timestamp", datetime.now())
        
        if token_age > timedelta(hours=1):  # Refresh if token is older than 1 hour
            try:
                refreshed_token = self.oauth_client.refresh_token(token)
                self.user_tokens[user_id]["token"] = refreshed_token
                self.user_tokens[user_id]["token_timestamp"] = datetime.now()
                return refreshed_token
            except Exception as e:
                # Refresh failed, user needs to re-authenticate
                print(f"Token refresh failed for user {user_id}: {e}")
                return None
        
        return token
    
    async def is_user_authenticated(self, user_id: str) -> bool:
        """Check if user is authenticated"""
        token = await self.get_valid_token(user_id)
        return token is not None
    
    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get Atlassian user info"""
        token = await self.get_valid_token(user_id)
        if not token:
            return None
        
        # You can implement user info retrieval here
        # For now, return basic info
        return {
            "user_id": user_id,
            "authenticated": True,
            "token_expires_at": self.user_tokens[user_id].get("token_timestamp")
        }
    
    def cleanup_expired_sessions(self):
        """Clean up expired user sessions"""
        current_time = datetime.now()
        expired_users = []
        
        for user_id, session in self.user_tokens.items():
            session_age = current_time - session.get("timestamp", current_time)
            if session_age > timedelta(hours=24):  # Clean sessions older than 24 hours
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_tokens[user_id]
            print(f"Cleaned expired session for user: {user_id}")
