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

# Routers will be included after services are defined

# Global services - lazy loaded to avoid circular imports
_oauth_service = None
_crew_service = None

# Make oauth_service available globally for routers
oauth_service = None

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

# Include routers after services are defined
from routers import auth, atlassian
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(atlassian.router, prefix="/atlassian", tags=["atlassian"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8080, 
        reload=True,
        log_level="info"
    )
