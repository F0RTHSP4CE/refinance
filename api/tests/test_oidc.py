"""Tests for OIDC authentication"""

import json
from unittest.mock import Mock, patch

import pytest
from app.models.entity import Entity
from app.services.oidc import OIDCService
from fastapi.testclient import TestClient


class TestOIDCAuth:
    """Test OIDC authentication flow"""

    def test_oidc_login_redirect(self, test_app: TestClient):
        """Test OIDC login initiates redirect to provider"""
        with patch('app.services.oidc.httpx.Client') as mock_client:
            # Mock server metadata response
            mock_response = Mock()
            mock_response.json.return_value = {
                'authorization_endpoint': 'https://provider.example.com/auth',
                'token_endpoint': 'https://provider.example.com/token',
                'userinfo_endpoint': 'https://provider.example.com/userinfo'
            }
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            
            # Mock config to have OIDC settings
            from app.config import Config, get_config
            from app.app import app
            
            test_config = Config(
                app_name="refinance-test",
                oidc_client_id="test-client-id",
                oidc_client_secret="test-client-secret", 
                oidc_server_metadata_url="https://provider.example.com/.well-known/openid_configuration",
                oidc_redirect_uri="http://localhost:8000/auth/oidc/callback"
            )
            app.dependency_overrides[get_config] = lambda: test_config

            response = test_app.get("/auth/oidc/login", follow_redirects=False)
            
            assert response.status_code == 302
            assert "https://provider.example.com/auth" in response.headers["location"]
            assert "client_id=test-client-id" in response.headers["location"]
            assert "redirect_uri=" in response.headers["location"]
            assert "state=" in response.headers["location"]

    def test_oidc_login_missing_config(self, test_app: TestClient):
        """Test OIDC login fails with incomplete config"""
        from app.config import Config, get_config
        from app.app import app
        
        # Config without OIDC settings
        test_config = Config(app_name="refinance-test")
        app.dependency_overrides[get_config] = lambda: test_config

        response = test_app.get("/auth/oidc/login")
        assert response.status_code == 500
        # The error is wrapped, so check for the general error message
        assert "Failed to initiate OIDC login" in response.json()["detail"]

    def test_oidc_callback_success_existing_user(self, test_app: TestClient, token_factory):
        """Test OIDC callback with existing user (matched by OIDC subject)"""
        # First create an entity with OIDC subject
        test_app.headers = {"x-token": token_factory(1)}
        
        entity_data = {
            "name": "Test OIDC User",
            "auth": {
                "oidc_subject": "test-subject-123",
                "email": "test@example.com"
            }
        }
        create_response = test_app.post("/entities", json=entity_data)
        assert create_response.status_code in [200, 201]  # Accept both for compatibility
        
        with patch('app.services.oidc.httpx.Client') as mock_client:
            # Mock server metadata
            mock_metadata_response = Mock()
            mock_metadata_response.json.return_value = {
                'authorization_endpoint': 'https://provider.example.com/auth',
                'token_endpoint': 'https://provider.example.com/token',
                'userinfo_endpoint': 'https://provider.example.com/userinfo'
            }
            mock_metadata_response.raise_for_status.return_value = None
            
            # Mock token exchange and userinfo responses
            mock_token_response = Mock()
            mock_userinfo_response = Mock()
            mock_userinfo_response.json.return_value = {
                'sub': 'test-subject-123',
                'email': 'test@example.com',
                'name': 'Test OIDC User'
            }
            mock_userinfo_response.raise_for_status.return_value = None
            
            mock_client_instance = Mock()
            mock_client_instance.get.side_effect = [mock_metadata_response, mock_userinfo_response]
            mock_client.return_value.__enter__.return_value = mock_client_instance
            
            # Mock OAuth2Client for token exchange
            with patch('app.services.oidc.OAuth2Client') as mock_oauth_client:
                mock_oauth_instance = Mock()
                mock_oauth_instance.fetch_token.return_value = {
                    'access_token': 'test-access-token',
                    'token_type': 'Bearer'
                }
                mock_oauth_client.return_value = mock_oauth_instance
                
                # Set up OIDC config
                from app.config import Config, get_config
                from app.app import app
                
                test_config = Config(
                    app_name="refinance-test",
                    oidc_client_id="test-client-id",
                    oidc_client_secret="test-client-secret",
                    oidc_server_metadata_url="https://provider.example.com/.well-known/openid_configuration",
                    oidc_redirect_uri="http://localhost:8000/auth/oidc/callback",
                    ui_url="http://localhost:3000"
                )
                app.dependency_overrides[get_config] = lambda: test_config

                response = test_app.get(
                    "/auth/oidc/callback?code=test-code&state=test-state",
                    follow_redirects=False
                )

                assert response.status_code == 302
                # Should redirect to UI with token
                assert "http://localhost:3000/auth/token/" in response.headers["location"]

    def test_oidc_callback_success_new_user(self, test_app: TestClient):
        """Test OIDC callback creating new user"""
        with patch('app.services.oidc.httpx.Client') as mock_client:
            # Mock server metadata
            mock_metadata_response = Mock()
            mock_metadata_response.json.return_value = {
                'authorization_endpoint': 'https://provider.example.com/auth',
                'token_endpoint': 'https://provider.example.com/token',
                'userinfo_endpoint': 'https://provider.example.com/userinfo'
            }
            mock_metadata_response.raise_for_status.return_value = None
            
            # Mock userinfo response for new user
            mock_userinfo_response = Mock()
            mock_userinfo_response.json.return_value = {
                'sub': 'new-subject-456',
                'email': 'newuser@example.com',
                'name': 'New OIDC User'
            }
            mock_userinfo_response.raise_for_status.return_value = None
            
            mock_client_instance = Mock()
            mock_client_instance.get.side_effect = [mock_metadata_response, mock_userinfo_response]
            mock_client.return_value.__enter__.return_value = mock_client_instance
            
            # Mock OAuth2Client for token exchange
            with patch('app.services.oidc.OAuth2Client') as mock_oauth_client:
                mock_oauth_instance = Mock()
                mock_oauth_instance.fetch_token.return_value = {
                    'access_token': 'test-access-token',
                    'token_type': 'Bearer'
                }
                mock_oauth_client.return_value = mock_oauth_instance
                
                # Set up OIDC config
                from app.config import Config, get_config
                from app.app import app
                
                test_config = Config(
                    app_name="refinance-test",
                    oidc_client_id="test-client-id",
                    oidc_client_secret="test-client-secret",
                    oidc_server_metadata_url="https://provider.example.com/.well-known/openid_configuration",
                    oidc_redirect_uri="http://localhost:8000/auth/oidc/callback",
                    ui_url="http://localhost:3000"
                )
                app.dependency_overrides[get_config] = lambda: test_config

                response = test_app.get(
                    "/auth/oidc/callback?code=test-code&state=test-state",
                    follow_redirects=False
                )

                assert response.status_code == 302
                # Should redirect to UI with token
                assert "http://localhost:3000/auth/token/" in response.headers["location"]

    def test_oidc_callback_error(self, test_app: TestClient):
        """Test OIDC callback with error parameter"""
        response = test_app.get("/auth/oidc/callback?error=access_denied&error_description=User%20denied%20access")
        assert response.status_code == 400
        assert "access_denied" in response.json()["detail"]

    def test_oidc_callback_missing_params(self, test_app: TestClient):
        """Test OIDC callback with missing required parameters"""
        response = test_app.get("/auth/oidc/callback")
        assert response.status_code == 400
        assert "Missing required parameters" in response.json()["detail"]

    def test_oidc_service_map_entity_by_email(self, test_app: TestClient, token_factory):
        """Test OIDC service maps existing entity by email"""
        # Create entity with email but no OIDC subject
        test_app.headers = {"x-token": token_factory(1)}
        
        entity_data = {
            "name": "Email User",
            "auth": {
                "email": "user@example.com"
            }
        }
        create_response = test_app.post("/entities", json=entity_data)
        assert create_response.status_code in [200, 201]  # Accept both for compatibility
        
        # Clear headers for service test
        test_app.headers = {}
        
        # Use the test app's dependencies directly
        from app.app import app
        from app.services.oidc import OIDCService
        from app.config import Config, get_config
        
        # Create a proper OIDC service instance with test config
        test_config = Config(
            app_name="refinance-test",
            oidc_client_id="test-client",
            oidc_client_secret="test-secret",
            oidc_server_metadata_url="http://test.com/.well-known",
            oidc_redirect_uri="http://test.com/callback"
        )
        
        # Override dependencies
        app.dependency_overrides[get_config] = lambda: test_config
        
        with app.dependency_overrides:
            with test_app as client:
                # Get a properly configured service
                from app.services.entity import EntityService
                from app.services.token import TokenService
                from app.uow import get_uow
                
                # Create fresh instances 
                def get_test_oidc_service():
                    db = next(get_uow())
                    entity_service = EntityService(db=db)
                    token_service = TokenService(db=db, entity_service=entity_service, config=test_config)
                    return OIDCService(
                        db=db,
                        entity_service=entity_service,
                        token_service=token_service,
                        config=test_config
                    )
                
                oidc_service = get_test_oidc_service()
                
                user_info = {
                    'sub': 'oidc-subject-789',
                    'email': 'user@example.com',
                    'name': 'Email User'
                }
                
                entity = oidc_service._map_or_create_entity(user_info)
                
                # Should find existing entity and add OIDC subject
                assert entity.name == "Email User"
                assert entity.auth['email'] == 'user@example.com'
                assert entity.auth['oidc_subject'] == 'oidc-subject-789'

    def test_token_auth_with_oidc_created_entity(self, test_app: TestClient):
        """Test that OIDC-created entities work with existing token auth"""
        # Create entity via OIDC-like process using API
        test_app.headers = {}
        
        # Use a system token to create the entity
        system_token = test_app.get("/tokens/1").json()
        test_app.headers = {"x-token": system_token}
        
        entity_data = {
            "name": "OIDC Test User",
            "auth": {"oidc_subject": "test-oidc-sub", "email": "oidc@test.com"}
        }
        
        response = test_app.post("/entities", json=entity_data)
        assert response.status_code in [200, 201]
        entity = response.json()
        
        # Generate token for this entity using the private test endpoint
        token = test_app.get(f"/tokens/{entity['id']}").json()
        
        # Test that this token works with existing protected endpoints
        test_app.headers = {"x-token": token}
        response = test_app.get("/entities")
        assert response.status_code == 200