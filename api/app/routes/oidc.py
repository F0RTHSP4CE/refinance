"""OIDC authentication routes"""

import logging
import secrets
from typing import Optional

from app.services.oidc import OIDCService
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

logger = logging.getLogger(__name__)

oidc_router = APIRouter(prefix="/auth/oidc", tags=["OIDC Authentication"])


@oidc_router.get("/login")
def oidc_login(
    request: Request,
    response: Response,
    redirect_url: Optional[str] = None,
    oidc_service: OIDCService = Depends(),
):
    """Initiate OIDC login flow"""
    try:
        # Generate state parameter for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Store state and redirect URL in session/cookie
        # For simplicity, we'll encode both in the state parameter
        state_data = state
        if redirect_url:
            state_data = f"{state}:{redirect_url}"
        
        # Get authorization URL
        auth_url = oidc_service.get_authorization_url(state_data)
        
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        logger.error(f"OIDC login error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate OIDC login")


@oidc_router.get("/callback")
def oidc_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    oidc_service: OIDCService = Depends(),
):
    """Handle OIDC callback"""
    if error:
        logger.error(f"OIDC callback error: {error}")
        raise HTTPException(status_code=400, detail=f"OIDC authentication failed: {error}")
    
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing required parameters")
    
    try:
        # Parse state to get original state and redirect URL
        state_parts = state.split(':', 1)
        original_state = state_parts[0]
        redirect_url = state_parts[1] if len(state_parts) > 1 else None
        
        # Handle the callback and get JWT token
        jwt_token = oidc_service.handle_callback(code, original_state)
        
        # Determine redirect URL
        if redirect_url:
            final_redirect = redirect_url
        else:
            # Default redirect to UI with token
            from app.config import get_config
            config = get_config()
            final_redirect = f"{config.ui_url}/auth/token/{jwt_token}"
        
        return RedirectResponse(url=final_redirect, status_code=302)
        
    except Exception as e:
        logger.error(f"OIDC callback error: {e}")
        raise HTTPException(status_code=500, detail="Failed to complete OIDC authentication")