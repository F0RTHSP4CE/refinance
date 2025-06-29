"""OIDC authentication service using Authlib"""

import logging
from typing import Any, Dict, Optional
import httpx

from app.config import Config, get_config
from app.models.entity import Entity
from app.services.entity import EntityService
from app.services.token import TokenService
from authlib.integrations.httpx_client import OAuth2Client
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from app.uow import get_uow

logger = logging.getLogger(__name__)


class OIDCService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(),
        token_service: TokenService = Depends(),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.entity_service = entity_service
        self.token_service = token_service
        self.config = config
        self._client: Optional[OAuth2Client] = None
        self._server_metadata: Optional[Dict[str, Any]] = None

    def _get_client(self) -> OAuth2Client:
        """Get or create OIDC client"""
        if self._client is None:
            if not all([
                self.config.oidc_client_id,
                self.config.oidc_client_secret,
                self.config.oidc_server_metadata_url,
                self.config.oidc_redirect_uri
            ]):
                raise HTTPException(
                    status_code=500,
                    detail="OIDC configuration is incomplete"
                )
            
            self._client = OAuth2Client(
                client_id=self.config.oidc_client_id,
                client_secret=self.config.oidc_client_secret,
            )
        return self._client

    def _load_server_metadata(self) -> Dict[str, Any]:
        """Load OIDC server metadata"""
        if self._server_metadata is None:
            with httpx.Client() as client:
                response = client.get(self.config.oidc_server_metadata_url)
                response.raise_for_status()
                self._server_metadata = response.json()
        return self._server_metadata

    def get_authorization_url(self, state: str) -> str:
        """Generate OIDC authorization URL"""
        client = self._get_client()
        server_metadata = self._load_server_metadata()
        
        authorization_url, _ = client.create_authorization_url(
            server_metadata['authorization_endpoint'],
            redirect_uri=self.config.oidc_redirect_uri,
            state=state,
            scope='openid email profile'
        )
        return authorization_url

    def handle_callback(self, code: str, state: str) -> str:
        """Handle OIDC callback and return JWT token"""
        client = self._get_client()
        server_metadata = self._load_server_metadata()
        
        # Exchange code for token
        with httpx.Client() as http_client:
            token_response = client.fetch_token(
                server_metadata['token_endpoint'],
                code=code,
                redirect_uri=self.config.oidc_redirect_uri,
                client=http_client
            )
            
            # Get user info
            resp = http_client.get(
                server_metadata['userinfo_endpoint'],
                headers={'Authorization': f"Bearer {token_response['access_token']}"}
            )
            resp.raise_for_status()
            user_info = resp.json()
        
        # Map or create Entity
        entity = self._map_or_create_entity(user_info)
        
        # Generate JWT token using existing system
        jwt_token = self.token_service._generate_new_token(entity.id)
        
        return jwt_token

    def _map_or_create_entity(self, user_info: Dict[str, Any]) -> Entity:
        """Map OIDC user info to local Entity, creating if necessary"""
        oidc_subject = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name') or user_info.get('preferred_username') or email
        
        if not oidc_subject:
            raise HTTPException(
                status_code=400,
                detail="OIDC user info missing required 'sub' field"
            )
        
        # Try to find existing Entity by OIDC subject
        existing_entities = self.entity_service.get_all()
        for entity in existing_entities:
            if (isinstance(entity.auth, dict) and 
                entity.auth.get('oidc_subject') == oidc_subject):
                logger.info(f"Found existing Entity {entity.id} for OIDC subject {oidc_subject}")
                return entity
        
        # Try to find by email if available
        if email:
            for entity in existing_entities:
                if (isinstance(entity.auth, dict) and 
                    entity.auth.get('email') == email):
                    # Update with OIDC subject
                    entity.auth['oidc_subject'] = oidc_subject
                    self.db.commit()
                    logger.info(f"Mapped existing Entity {entity.id} to OIDC subject {oidc_subject}")
                    return entity
        
        # Create new Entity
        from app.schemas.entity import EntityCreateSchema, EntityAuthSchema
        
        auth_data = {
            'oidc_subject': oidc_subject
        }
        if email:
            auth_data['email'] = email
        
        entity_schema = EntityCreateSchema(
            name=name or f"User-{oidc_subject[:8]}",
            auth=auth_data
        )
        
        new_entity = self.entity_service.create(entity_schema)
        logger.info(f"Created new Entity {new_entity.id} for OIDC subject {oidc_subject}")
        
        return new_entity