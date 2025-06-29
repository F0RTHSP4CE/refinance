"""API routes for OIDC authentication"""

import secrets
from typing import Optional

from app.schemas.oidc import (
    OIDCAuthUrlSchema,
    OIDCCallbackSchema,
    OIDCLoginResponseSchema,
)
from app.services.oidc import OIDCService
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse

oidc_router = APIRouter(prefix="/auth/oidc", tags=["OIDC Authentication"])


@oidc_router.get("/login", response_model=OIDCAuthUrlSchema)
def oidc_login_url(
    request: Request,
    oidc_service: OIDCService = Depends(),
):
    """Generate OIDC authorization URL for login."""
    # Use the UI callback URL
    redirect_uri = str(request.base_url).rstrip('/') + "/auth/oidc/callback"
    
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    
    auth_url, code_verifier = oidc_service.generate_auth_url(redirect_uri, state)
    
    # In a real implementation, you'd store code_verifier and state in session/cache
    # For simplicity, we'll include them in the response (not recommended for production)
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
    # In production, you'd validate the state parameter against stored value
    
    redirect_uri = str(request.base_url).rstrip('/') + "/auth/oidc/callback"
    
    # For this minimal implementation, we'll use a dummy code_verifier
    # In production, this should be retrieved from session/cache
    code_verifier = secrets.token_urlsafe(32)
    
    try:
        # Exchange code for tokens
        token_data = oidc_service.exchange_code_for_tokens(code, redirect_uri, code_verifier)
        
        # Get user info
        user_info = oidc_service.get_user_info(token_data['access_token'])
        
        # Find or link entity
        entity = oidc_service.find_or_link_entity(user_info)
        
        # Generate JWT token for the application
        jwt_token = oidc_service.generate_jwt_token_for_entity(entity)
        
        # Redirect to UI with token
        ui_url = request.headers.get('referer', '/')
        ui_base = ui_url.split('/auth')[0] if '/auth' in ui_url else ui_url.rstrip('/')
        
        return RedirectResponse(
            url=f"{ui_base}/auth/token/{jwt_token}",
            status_code=302
        )
        
    except Exception as e:
        # Redirect to login with error
        ui_url = request.headers.get('referer', '/')
        ui_base = ui_url.split('/auth')[0] if '/auth' in ui_url else ui_url.rstrip('/')
        
        return RedirectResponse(
            url=f"{ui_base}/auth/login?error=oidc_auth_failed",
            status_code=302
        )


@oidc_router.post("/callback", response_model=OIDCLoginResponseSchema)
def oidc_callback_api(
    callback_data: OIDCCallbackSchema,
    request: Request,
    oidc_service: OIDCService = Depends(),
):
    """API endpoint for OIDC callback (for API-based flows)."""
    redirect_uri = str(request.base_url).rstrip('/') + "/auth/oidc/callback"
    
    # For this minimal implementation, we'll use a dummy code_verifier
    # In production, this should be retrieved from session/cache using the state
    code_verifier = secrets.token_urlsafe(32)
    
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