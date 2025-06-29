"""Tests for OIDC authentication"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.services.oidc import OIDCService
from app.models.entity import Entity


class TestOIDCService:
    """Test OIDC service functionality"""

    @patch('app.services.oidc.requests.get')
    def test_get_discovery_document_success(self, mock_get):
        """Test successful OIDC discovery document retrieval"""
        # Mock the discovery document response
        mock_response = Mock()
        mock_response.json.return_value = {
            "authorization_endpoint": "https://provider.com/auth",
            "token_endpoint": "https://provider.com/token",
            "userinfo_endpoint": "https://provider.com/userinfo"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Mock dependencies
        mock_db = Mock()
        mock_entity_service = Mock()
        mock_config = Mock()
        mock_config.oidc_discovery_url = "https://provider.com/.well-known/openid_configuration"
        
        service = OIDCService(db=mock_db, entity_service=mock_entity_service, config=mock_config)
        discovery = service._get_discovery_document()
        
        assert discovery["authorization_endpoint"] == "https://provider.com/auth"
        assert discovery["token_endpoint"] == "https://provider.com/token"
        assert discovery["userinfo_endpoint"] == "https://provider.com/userinfo"

    def test_find_or_link_entity_by_oidc_sub(self):
        """Test finding entity by OIDC subject"""
        # Mock dependencies
        mock_db = Mock()
        mock_entity_service = Mock()
        mock_config = Mock()
        
        # Mock entity with OIDC auth
        mock_entity = Mock(spec=Entity)
        mock_entity.id = 1
        mock_entity.name = "test_user"
        mock_entity.auth = {"oidc_sub": "12345", "oidc_email": "test@example.com"}
        
        mock_entity_service.get_by_oidc_sub.return_value = mock_entity
        
        service = OIDCService(db=mock_db, entity_service=mock_entity_service, config=mock_config)
        
        user_info = {"sub": "12345", "email": "test@example.com", "name": "Test User"}
        result = service.find_or_link_entity(user_info)
        
        assert result == mock_entity
        mock_entity_service.get_by_oidc_sub.assert_called_once_with("12345")

    def test_find_or_link_entity_by_email_fallback(self):
        """Test finding entity by email when OIDC sub not found"""
        # Mock dependencies
        mock_db = Mock()
        mock_entity_service = Mock()
        mock_config = Mock()
        
        # Mock entity found by email
        mock_entity = Mock(spec=Entity)
        mock_entity.id = 1
        mock_entity.name = "test_user"
        mock_entity.auth = {"telegram_id": "123456"}
        
        # First call (by OIDC sub) raises NotFoundError, second call (by email) succeeds
        from app.errors.common import NotFoundError
        mock_entity_service.get_by_oidc_sub.side_effect = NotFoundError("not found")
        mock_entity_service.get_by_oidc_email.return_value = mock_entity
        
        service = OIDCService(db=mock_db, entity_service=mock_entity_service, config=mock_config)
        
        user_info = {"sub": "12345", "email": "test@example.com", "name": "Test User"}
        result = service.find_or_link_entity(user_info)
        
        assert result == mock_entity
        # Check that OIDC info was added to the entity
        assert mock_entity.auth["oidc_sub"] == "12345"
        assert mock_entity.auth["oidc_email"] == "test@example.com"
        mock_db.commit.assert_called_once()

    def test_find_or_link_entity_not_found(self):
        """Test error when entity is not found"""
        # Mock dependencies
        mock_db = Mock()
        mock_entity_service = Mock()
        mock_config = Mock()
        
        from app.errors.common import NotFoundError
        from fastapi import HTTPException
        
        # Both lookups raise NotFoundError
        mock_entity_service.get_by_oidc_sub.side_effect = NotFoundError("not found")
        mock_entity_service.get_by_oidc_email.side_effect = NotFoundError("not found")
        
        service = OIDCService(db=mock_db, entity_service=mock_entity_service, config=mock_config)
        
        user_info = {"sub": "12345", "email": "test@example.com", "name": "Test User"}
        
        with pytest.raises(HTTPException) as exc_info:
            service.find_or_link_entity(user_info)
        
        assert exc_info.value.status_code == 404
        assert "No entity found for this OIDC account" in str(exc_info.value.detail)


class TestOIDCRoutes:
    """Test OIDC API routes"""

    @patch('app.routes.oidc.OIDCService')
    def test_oidc_login_url_generation(self, mock_oidc_service_class, test_app: TestClient):
        """Test OIDC login URL generation endpoint"""
        # Mock the service
        mock_service = Mock()
        mock_service.generate_auth_url.return_value = (
            "https://provider.com/auth?client_id=test&redirect_uri=callback", 
            "code_verifier_123"
        )
        mock_oidc_service_class.return_value = mock_service
        
        response = test_app.get("/auth/oidc/login")
        
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "state" in data
        assert data["auth_url"].startswith("https://provider.com/auth")

    def test_oidc_callback_missing_parameters(self, test_app: TestClient):
        """Test OIDC callback with missing parameters"""
        response = test_app.get("/auth/oidc/callback")
        
        # Should return 422 for missing required parameters
        assert response.status_code == 422


class TestEntityServiceOIDCMethods:
    """Test OIDC-related methods in EntityService"""

    def test_get_by_oidc_sub_success(self):
        """Test successful lookup by OIDC subject"""
        from app.services.entity import EntityService
        
        # This would need actual database setup in a full test
        # For now, just test that the method exists and has correct signature
        assert hasattr(EntityService, 'get_by_oidc_sub')
        assert hasattr(EntityService, 'get_by_oidc_email')