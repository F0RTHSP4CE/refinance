"""Basic OIDC integration tests"""

from fastapi.testclient import TestClient


class TestOIDCBasic:
    """Basic OIDC integration tests"""

    def test_oidc_routes_exist(self, test_app: TestClient):
        """Test that OIDC routes are registered"""
        # Test login endpoint exists
        response = test_app.get("/auth/oidc/login")
        # Should fail with 500 due to missing config, but not 404
        assert response.status_code == 500
        
        # Test callback endpoint exists  
        response = test_app.get("/auth/oidc/callback")
        # Should fail with 400 due to missing params, but not 404
        assert response.status_code == 400

    def test_existing_telegram_auth_still_works(self, test_app: TestClient, token_factory):
        """Test that existing Telegram auth functionality is unaffected"""
        token = token_factory(1)
        
        # Test token request endpoint still works
        response = test_app.post("/tokens/request", json={
            "entity_name": "test-entity"
        })
        # Should work (though may not send since no Telegram config in test)
        assert response.status_code == 200
        
        # Test protected endpoint still works with tokens
        response = test_app.get("/entities", headers={"x-token": token})
        assert response.status_code == 200

    def test_entity_schema_supports_oidc_fields(self, test_app: TestClient, token_factory):
        """Test that Entity schema accepts OIDC auth fields"""
        test_app.headers = {"x-token": token_factory(1)}
        
        # Create entity with OIDC fields
        entity_data = {
            "name": "OIDC User",
            "auth": {
                "oidc_subject": "oidc-sub-123",
                "email": "user@example.com",
                "telegram_id": 12345  # Mix with existing fields
            }
        }
        
        response = test_app.post("/entities", json=entity_data)
        assert response.status_code in [200, 201]
        
        created_entity = response.json()
        assert created_entity["name"] == "OIDC User"
        assert created_entity["auth"]["oidc_subject"] == "oidc-sub-123"
        assert created_entity["auth"]["email"] == "user@example.com"
        assert created_entity["auth"]["telegram_id"] == 12345