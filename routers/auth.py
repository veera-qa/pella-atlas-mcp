from fastapi import APIRouter, Request, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
import uuid
from services.oauth_service import OAuthService

router = APIRouter()

def get_oauth_service():
    # Import here to avoid circular import
    import main
    return main.get_oauth_service()

@router.get("/login")
async def login(request: Request, oauth_service: OAuthService = Depends(get_oauth_service)):
    """Initiate OAuth login"""
    try:
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

@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Handle OAuth callback"""
    try:
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

@router.get("/status")
async def auth_status(
    request: Request, 
    oauth_service: OAuthService = Depends(get_oauth_service)
):
    """Get authentication status for current user"""
    user_id = request.session.get("user_id")
    
    if not user_id:
        return {"authenticated": False, "user_id": None}
    
    is_authenticated = await oauth_service.is_user_authenticated(user_id)
    user_info = await oauth_service.get_user_info(user_id) if is_authenticated else None
    
    return {
        "authenticated": is_authenticated,
        "user_id": user_id,
        "user_info": user_info
    }

@router.post("/logout")
async def logout(request: Request):
    """Logout current user"""
    request.session.clear()
    return {"message": "Logged out successfully"}
