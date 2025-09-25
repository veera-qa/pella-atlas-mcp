from fastapi import APIRouter, Request, Depends, HTTPException, Form
from fastapi.responses import JSONResponse
from typing import Optional
from services.oauth_service import OAuthService
from services.crew_service import CrewService

router = APIRouter()

def get_oauth_service():
    from main import oauth_service
    return oauth_service

def get_crew_service():
    from main import crew_service
    return crew_service

def get_current_user(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id

@router.post("/query")
async def execute_query(
    request: Request,
    query: str = Form(...),
    user_id: str = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
    crew_service: CrewService = Depends(get_crew_service)
):
    """Execute Atlassian query"""
    try:
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

@router.get("/history")
async def get_query_history(
    request: Request,
    limit: int = 20,
    user_id: str = Depends(get_current_user),
    crew_service: CrewService = Depends(get_crew_service)
):
    """Get user's query history"""
    try:
        history = crew_service.get_user_history(user_id, limit)
        return {"history": history}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")

@router.delete("/history")
async def clear_query_history(
    request: Request,
    user_id: str = Depends(get_current_user),
    crew_service: CrewService = Depends(get_crew_service)
):
    """Clear user's query history"""
    try:
        success = crew_service.clear_user_history(user_id)
        return {"success": success, "message": "History cleared" if success else "No history found"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")

@router.get("/tools")
async def get_available_tools(
    request: Request,
    user_id: str = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service),
    crew_service: CrewService = Depends(get_crew_service)
):
    """Get available MCP tools for authenticated user"""
    try:
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

@router.get("/user-info")
async def get_atlassian_user_info(
    request: Request,
    user_id: str = Depends(get_current_user),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Get Atlassian user information"""
    try:
        user_info = await oauth_service.get_user_info(user_id)
        if not user_info:
            raise HTTPException(status_code=401, detail="User not authenticated")
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")

@router.get("/stats")
async def get_service_stats(
    request: Request,
    user_id: str = Depends(get_current_user),
    crew_service: CrewService = Depends(get_crew_service)
):
    """Get service statistics (for admin users)"""
    try:
        stats = crew_service.get_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
