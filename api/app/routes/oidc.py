"""API routes for OIDC authentication"""

import secrets
from typing import Optional

from app.schemas.oidc import (
    OIDCAuthUrlSchema,
    OIDCCallbackSchema,
    OIDCLoginResponseSchema,
)
from app.services.oidc import OIDCService
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
import json
from urllib.parse import quote, unquote

oidc_router = APIRouter(prefix="/auth/oidc", tags=["OIDC Authentication"])


@oidc_router.get("/login", response_model=OIDCAuthUrlSchema)
def oidc_login_url(
    request: Request,
    response: Response,
    oidc_service: OIDCService = Depends(),
):
    """Generate OIDC authorization URL for login."""
    # Use the API callback URL for the redirect_uri
    base_url = str(request.base_url).rstrip('/')
    redirect_uri = f"{base_url}/auth/oidc/callback"
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    auth_url, code_verifier = oidc_service.generate_auth_url(redirect_uri, state)
    
    # Store code_verifier and state in a simple cookie for this demo
    # In production, use proper session management or Redis
    session_data = {
        "code_verifier": code_verifier,
        "state": state
    }
    
    # Set a secure httponly cookie with the session data
    response.set_cookie(
        key="oidc_session",
        value=quote(json.dumps(session_data)),
        max_age=600,  # 10 minutes
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax"
    )
    
    return OIDCAuthUrlSchema(
        auth_url=auth_url,
        state=state
    )


@oidc_router.get("/callback")
def oidc_callback(
    code: str,
    state: str,
    request: Request,
    oidc_service: OIDCService = Depends(),
):
    """Handle OIDC callback and authenticate user."""
    # Retrieve session data from cookie
    oidc_session_cookie = request.cookies.get("oidc_session")
    if not oidc_session_cookie:
        return RedirectResponse(
            url="/auth/login?error=oidc_session_missing",
            status_code=302
        )
    
    try:
        session_data = json.loads(unquote(oidc_session_cookie))
        stored_state = session_data.get("state")
        code_verifier = session_data.get("code_verifier")
    except (json.JSONDecodeError, KeyError):
        return RedirectResponse(
            url="/auth/login?error=oidc_session_invalid",
            status_code=302
        )
    
    # Validate state parameter
    if state != stored_state:
        return RedirectResponse(
            url="/auth/login?error=oidc_state_mismatch",
            status_code=302
        )
    
    redirect_uri = str(request.base_url).rstrip('/') + "/auth/oidc/callback"
    
    try:
        # Exchange code for tokens
        token_data = oidc_service.exchange_code_for_tokens(code, redirect_uri, code_verifier)
        
        # Get user info
        user_info = oidc_service.get_user_info(token_data['access_token'])
        
        # Find or link entity
        entity = oidc_service.find_or_link_entity(user_info)
        
        # Generate JWT token for the application
        jwt_token = oidc_service.generate_jwt_token_for_entity(entity)
        
        # Determine UI URL for redirect
        # Try to get the original UI URL from referrer or use default
        ui_base = request.headers.get('referer', 'http://localhost:9000')
        if '/auth' in ui_base:
            ui_base = ui_base.split('/auth')[0]
        
        # Clear the session cookie
        response = RedirectResponse(
            url=f"{ui_base}/auth/token/{jwt_token}",
            status_code=302
        )
        response.delete_cookie("oidc_session")
        return response
        
    except Exception as e:
        # Clear the session cookie and redirect to login with error
        response = RedirectResponse(
            url="/auth/login?error=oidc_auth_failed",
            status_code=302
        )
        response.delete_cookie("oidc_session")
        return response


@oidc_router.post("/callback", response_model=OIDCLoginResponseSchema)
def oidc_callback_api(
    callback_data: OIDCCallbackSchema,
    request: Request,
    oidc_service: OIDCService = Depends(),
):
    """API endpoint for OIDC callback (for API-based flows)."""
    # This is a simplified version for API clients
    # In practice, you'd also need proper state/code_verifier management
    redirect_uri = str(request.base_url).rstrip('/') + "/auth/oidc/callback"
    
    # For API-based flows, the client would need to provide the code_verifier
    # This is a simplified implementation
    code_verifier = secrets.token_urlsafe(32)  # This should come from client
    
    # Exchange code for tokens
    token_data = oidc_service.exchange_code_for_tokens(
        callback_data.code, redirect_uri, code_verifier
    )
    
    # Get user info
    user_info = oidc_service.get_user_info(token_data['access_token'])
    
    # Find or link entity
    entity = oidc_service.find_or_link_entity(user_info)
    
    # Generate JWT token for the application
    jwt_token = oidc_service.generate_jwt_token_for_entity(entity)
    
    return OIDCLoginResponseSchema(
        token=jwt_token,
        entity_id=entity.id,
        entity_name=entity.name
    )