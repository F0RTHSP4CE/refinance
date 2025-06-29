"""OIDC service for handling OpenID Connect authentication flows."""

import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
import requests
from app.config import Config, get_config
from app.errors.common import NotFoundError
from app.errors.token import TokenInvalid
from app.models.entity import Entity
from app.services.entity import EntityService
from app.uow import get_uow
from authlib.integrations.requests_client import OAuth2Session
from authlib.oidc.core import CodeIDToken
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class OIDCService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.entity_service = entity_service
        self.config = config
        self._discovery_cache: Optional[Dict[str, Any]] = None
        self._discovery_cache_time: Optional[float] = None

    def _get_discovery_document(self) -> Dict[str, Any]:
        """Get OIDC discovery document, with caching."""
        current_time = time.time()
        
        # Cache for 1 hour
        if (self._discovery_cache and self._discovery_cache_time and 
            current_time - self._discovery_cache_time < 3600):
            return self._discovery_cache

        if not self.config.oidc_discovery_url:
            raise HTTPException(status_code=500, detail="OIDC not configured")

        try:
            response = requests.get(self.config.oidc_discovery_url, timeout=10)
            response.raise_for_status()
            self._discovery_cache = response.json()
            self._discovery_cache_time = current_time
            return self._discovery_cache
        except Exception as e:
            logger.error(f"Failed to fetch OIDC discovery document: {e}")
            raise HTTPException(status_code=500, detail="OIDC configuration error")

    def generate_auth_url(self, redirect_uri: str, state: Optional[str] = None) -> tuple[str, str]:
        """Generate OIDC authorization URL and code verifier for PKCE."""
        discovery = self._get_discovery_document()
        
        if not self.config.oidc_client_id:
            raise HTTPException(status_code=500, detail="OIDC client ID not configured")

        # Generate PKCE code verifier and challenge
        code_verifier = secrets.token_urlsafe(32)
        
        client = OAuth2Session(
            client_id=self.config.oidc_client_id,
            redirect_uri=redirect_uri,
            scope=self.config.oidc_scopes.split(),
            code_challenge_method='S256'
        )
        
        authorization_url, state = client.create_authorization_url(
            discovery['authorization_endpoint'],
            state=state
        )
        
        return authorization_url, code_verifier

    def exchange_code_for_tokens(
        self, 
        code: str, 
        redirect_uri: str, 
        code_verifier: str
    ) -> Dict[str, Any]:
        """Exchange authorization code for tokens."""
        discovery = self._get_discovery_document()
        
        if not self.config.oidc_client_id or not self.config.oidc_client_secret:
            raise HTTPException(status_code=500, detail="OIDC credentials not configured")

        client = OAuth2Session(
            client_id=self.config.oidc_client_id,
            redirect_uri=redirect_uri,
            code_verifier=code_verifier
        )
        
        try:
            token_data = client.fetch_token(
                discovery['token_endpoint'],
                code=code,
                client_secret=self.config.oidc_client_secret
            )
            return token_data
        except Exception as e:
            logger.error(f"Failed to exchange code for tokens: {e}")
            raise HTTPException(status_code=400, detail="Invalid authorization code")

    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from OIDC provider."""
        discovery = self._get_discovery_document()
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(
                discovery['userinfo_endpoint'], 
                headers=headers, 
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            raise HTTPException(status_code=400, detail="Failed to get user information")

    def find_or_link_entity(self, user_info: Dict[str, Any]) -> Entity:
        """Find existing entity by OIDC info or create linking opportunity."""
        oidc_sub = user_info.get('sub')
        oidc_email = user_info.get('email')
        
        if not oidc_sub:
            raise HTTPException(status_code=400, detail="Invalid user information: missing subject")

        # Try to find entity by OIDC subject
        try:
            entity = self.entity_service.get_by_oidc_sub(oidc_sub)
            return entity
        except NotFoundError:
            pass

        # Try to find entity by email if available
        if oidc_email:
            try:
                entity = self.entity_service.get_by_oidc_email(oidc_email)
                # Link the OIDC subject to existing entity
                if entity.auth is None:
                    entity.auth = {}
                entity.auth['oidc_sub'] = oidc_sub
                entity.auth['oidc_email'] = oidc_email
                self.db.commit()
                return entity
            except NotFoundError:
                pass

        # If no entity found, this might be a new user that needs to be created
        # or linked manually. For now, raise an error as per minimal change approach
        raise HTTPException(
            status_code=404, 
            detail="No entity found for this OIDC account. Please contact an administrator to link your account."
        )

    def generate_jwt_token_for_entity(self, entity: Entity) -> str:
        """Generate JWT token for authenticated entity (reuse existing token logic)."""
        if not self.config.secret_key:
            raise HTTPException(status_code=500, detail="JWT secret not configured")

        payload = {
            "entity_id": entity.id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(days=30),  # 30 day expiry
        }
        
        return jwt.encode(payload, self.config.secret_key, algorithm="HS256")