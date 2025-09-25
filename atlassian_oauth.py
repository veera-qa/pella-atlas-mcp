import os
import requests
from requests_oauthlib import OAuth2Session
from dotenv import load_dotenv
import json
from urllib.parse import urlencode
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse as urlparse

# Load environment variables
load_dotenv()

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.auth_code = None
        query = urlparse.parse_qs(urlparse.urlparse(self.path).query)
        if 'code' in query:
            self.server.auth_code = query['code'][0]
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authorization successful!</h1><p>You can close this window.</p></body></html>')
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authorization failed!</h1></body></html>')

class AtlassianOAuthClient:
    def __init__(self):
        self.client_id = os.getenv('ATLASSIAN_CLIENT_ID')
        self.client_secret = os.getenv('ATLASSIAN_CLIENT_SECRET')
        self.cloud_id = os.getenv('ATLASSIAN_CLOUD_ID')
        self.site_url = os.getenv('ATLASSIAN_SITE_URL')
        
        # Atlassian OAuth 2.1 endpoints
        self.auth_url = 'https://auth.atlassian.com/authorize'
        self.token_url = 'https://auth.atlassian.com/oauth/token'
        
        # Use SERVER_IP from environment for team access
        server_ip = os.getenv('SERVER_IP', 'localhost')
        server_port = os.getenv('SERVER_PORT', '8080')
        self.redirect_uri = f'http://{server_ip}:{server_port}/auth/callback'
        
        # Common scopes for Jira and Confluence
        self.scope = [
            'read:jira-user',
            'read:jira-work',
            'write:jira-work',
            'read:confluence-content.summary',
            'read:confluence-content.all',
            'write:confluence-content'
        ]
        
    def get_authorization_url(self):
        """Get the authorization URL for OAuth flow"""
        oauth = OAuth2Session(
            client_id=self.client_id,
            scope=self.scope,
            redirect_uri=self.redirect_uri
        )
        
        authorization_url, state = oauth.authorization_url(
            self.auth_url,
            audience='api.atlassian.com',
            prompt='consent'
        )
        
        return authorization_url, state, oauth
    
    def get_access_token(self, authorization_code, oauth_session):
        """Exchange authorization code for access token"""
        token = oauth_session.fetch_token(
            self.token_url,
            code=authorization_code,
            client_secret=self.client_secret
        )
        return token
    
    def perform_oauth_flow(self):
        """Perform complete OAuth 2.1 flow"""
        print("Starting OAuth 2.1 flow...")
        
        # Get authorization URL
        auth_url, state, oauth_session = self.get_authorization_url()
        
        print(f"Opening browser for authorization: {auth_url}")
        
        # Start local server for callback
        server = HTTPServer(('localhost', 8080), OAuthCallbackHandler)
        server.timeout = 120  # 2 minutes timeout
        
        # Open browser
        webbrowser.open(auth_url)
        
        print("Waiting for authorization callback...")
        server.handle_request()
        
        if hasattr(server, 'auth_code') and server.auth_code:
            print("Authorization code received!")
            
            # Exchange code for token
            token = self.get_access_token(server.auth_code, oauth_session)
            
            # Save token to file
            with open('atlassian_token.json', 'w') as f:
                json.dump(token, f, indent=2)
            
            print("Access token saved to atlassian_token.json")
            return token
        else:
            raise Exception("Failed to get authorization code")
    
    def load_token(self):
        """Load existing token from file"""
        try:
            with open('atlassian_token.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return None
    
    def refresh_token(self, token):
        """Refresh an expired token"""
        oauth = OAuth2Session(
            client_id=self.client_id,
            token=token
        )
        
        refreshed_token = oauth.refresh_token(
            self.token_url,
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        # Save refreshed token
        with open('atlassian_token.json', 'w') as f:
            json.dump(refreshed_token, f, indent=2)
        
        return refreshed_token
    
    def get_valid_token(self):
        """Get a valid access token (refresh if needed)"""
        token = self.load_token()
        
        if not token:
            print("No existing token found. Starting OAuth flow...")
            return self.perform_oauth_flow()
        
        # Check if token needs refresh (simplified check)
        # In production, you'd check the expires_at field
        try:
            # Test the token by making a simple API call
            headers = {'Authorization': f"Bearer {token['access_token']}"}
            response = requests.get(
                'https://api.atlassian.com/oauth/token/accessible-resources',
                headers=headers
            )
            
            if response.status_code == 401:
                print("Token expired. Refreshing...")
                return self.refresh_token(token)
            else:
                print("Using existing valid token")
                return token
        except Exception as e:
            print(f"Error validating token: {e}")
            print("Starting new OAuth flow...")
            return self.perform_oauth_flow()

if __name__ == "__main__":
    # Test the OAuth client
    oauth_client = AtlassianOAuthClient()
    token = oauth_client.get_valid_token()
    print("Token obtained successfully!")
    print(f"Access token: {token['access_token'][:20]}...")
