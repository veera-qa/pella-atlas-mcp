from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Atlassian MCP Team Server",
    description="OAuth 2.1 enabled Atlassian MCP server for team collaboration",
    version="1.0.0"
)

# Add session middleware
app.add_middleware(
    SessionMiddleware, 
    secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-this-in-production")
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Global services - lazy loaded to avoid circular imports
_oauth_service = None
_crew_service = None

def get_oauth_service():
    global _oauth_service
    if _oauth_service is None:
        from services.oauth_service import OAuthService
        _oauth_service = OAuthService()
    return _oauth_service

def get_crew_service():
    global _crew_service
    if _crew_service is None:
        from services.crew_service import CrewService
        _crew_service = CrewService()
    return _crew_service

# Dependency to get current user session
def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id

# Add authentication routes directly to avoid circular imports
@app.get("/auth/login")
async def login(request: Request):
    """Initiate OAuth login"""
    try:
        oauth_service = get_oauth_service()
        # Generate or get user ID
        user_id = request.session.get("user_id")
        if not user_id:
            user_id = str(uuid.uuid4())
            request.session["user_id"] = user_id
        
        # Get authorization URL
        auth_url, state = await oauth_service.get_authorization_url(user_id)
        
        # Store state in session for verification
        request.session["oauth_state"] = state
        
        # Redirect to Atlassian OAuth
        return RedirectResponse(url=auth_url)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth initiation failed: {str(e)}")

@app.get("/callback")
async def oauth_callback(request: Request, code: str, state: str):
    """Handle OAuth callback"""
    try:
        oauth_service = get_oauth_service()
        user_id = request.session.get("user_id")
        stored_state = request.session.get("oauth_state")
        
        if not user_id:
            raise HTTPException(status_code=400, detail="No user session found")
        
        if not stored_state or stored_state != state:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        # Exchange code for token
        token = await oauth_service.handle_oauth_callback(user_id, code, state)
        
        # Clear OAuth state from session
        request.session.pop("oauth_state", None)
        
        # Mark user as authenticated
        request.session["authenticated"] = True
        
        # Redirect to dashboard
        return RedirectResponse(url="/", status_code=303)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")

@app.post("/atlassian/query")
async def execute_query(request: Request, query: str = Form(...)):
    """Execute Atlassian query"""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        oauth_service = get_oauth_service()
        crew_service = get_crew_service()
        
        # Check if user is authenticated
        is_authenticated = await oauth_service.is_user_authenticated(user_id)
        if not is_authenticated:
            raise HTTPException(status_code=401, detail="User not authenticated with Atlassian")
        
        # Get valid token
        token = await oauth_service.get_valid_token(user_id)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Execute query
        result = await crew_service.execute_query(
            user_id=user_id,
            query=query,
            access_token=token['access_token']
        )
        
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Query execution failed: {str(e)}",
                "query": query
            }
        )

@app.get("/auth/callback")
async def oauth_callback_auth(request: Request, code: str, state: str):
    """Handle OAuth callback (auth route alias)"""
    return await oauth_callback(request, code, state)

@app.get("/oauth/callback")
async def oauth_callback_oauth(request: Request, code: str, state: str):
    """Handle OAuth callback (oauth route alias)"""
    return await oauth_callback(request, code, state)

@app.get("/auth/status")
async def auth_status(request: Request):
    """Get authentication status for current user"""
    user_id = request.session.get("user_id")
    
    if not user_id:
        return {"authenticated": False, "user_id": None}
    
    oauth_service = get_oauth_service()
    is_authenticated = await oauth_service.is_user_authenticated(user_id)
    user_info = await oauth_service.get_user_info(user_id) if is_authenticated else None
    
    return {
        "authenticated": is_authenticated,
        "user_id": user_id,
        "user_info": user_info
    }

@app.get("/atlassian/tools")
async def get_available_tools(request: Request):
    """Get available MCP tools for authenticated user"""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        oauth_service = get_oauth_service()
        crew_service = get_crew_service()
        
        # Check authentication
        is_authenticated = await oauth_service.is_user_authenticated(user_id)
        if not is_authenticated:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        # Get token
        token = await oauth_service.get_valid_token(user_id)
        if not token:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get tools
        tools = await crew_service.get_mcp_tools(token['access_token'])
        tool_names = [tool.name for tool in tools] if tools else []
        
        return {
            "tools": tool_names,
            "count": len(tool_names)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get tools: {str(e)}")

@app.get("/atlassian/history")
async def get_query_history(request: Request, limit: int = 20):
    """Get user's query history"""
    try:
        user_id = request.session.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Not authenticated")
            
        crew_service = get_crew_service()
        history = crew_service.get_user_history(user_id, limit)
        return {"history": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - shows login or dashboard based on auth status"""
    user_id = request.session.get("user_id")
    
    if user_id:
        # User is authenticated, show dashboard
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user_id": user_id
        })
    else:
        # User not authenticated, show login page
        return templates.TemplateResponse("index.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "atlassian-mcp-server"}

@app.post("/logout")
async def logout(request: Request):
    """Logout current user"""
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8080, 
        reload=True,
        log_level="info"
    )
