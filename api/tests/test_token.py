"""Tests for token authentication"""

from fastapi.testclient import TestClient


class TestTokenAuth:
    """Test security of protected API endpoints"""

    def test_access_protected_route_with_valid_token(self, test_app: TestClient, token):
        test_app.headers = {}
        response = test_app.get("/entities", headers={"x-token": token})
        assert response.status_code == 200

    def test_access_protected_route_with_invalid_token(self, test_app: TestClient):
        test_app.headers = {}
        response = test_app.get("/entities", headers={"x-token": "invalid-token-123"})
        assert response.status_code == 403

    def test_access_protected_route_without_token(self, test_app: TestClient):
        test_app.headers = {}
        response = test_app.get("/entities")
        assert response.status_code == 422

    def test_send_token_by_entity_name(self, test_app: TestClient, token):
        """Test sending token using entity name"""
        # First, create a test entity with telegram_id
        response = test_app.post(
            "/entities",
            json={"name": "Token Test Entity", "comment": "test for token sending"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_id = response.json()["id"]

        # Add telegram_id to the entity for token sending
        response = test_app.patch(
            f"/entities/{entity_id}",
            json={"auth": {"telegram_id": 12345678}},
            headers={"x-token": token},
        )
        assert response.status_code == 200

        # Now try to send token using entity name
        response = test_app.post(
            "/tokens/send", json={"entity_name": "Token Test Entity"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["entity_found"] is True
        assert result["token_generated"] is True
        # Note: message_sent will be False in test environment due to Telegram API failure
        assert (
            result["message_sent"] is False
        )  # Expected to be False in test environment

    def test_send_token_by_invalid_entity_name(self, test_app: TestClient):
        """Test sending token using invalid entity name"""
        response = test_app.post(
            "/tokens/send", json={"entity_name": "NonExistentEntity"}
        )
        assert response.status_code == 200
        result = response.json()
        assert result["entity_found"] is False
        assert result["token_generated"] is False
        assert result["message_sent"] is False

    def test_entity_auth_contains_supported_fields_only(
        self, test_app: TestClient, token
    ):
        response = test_app.post(
            "/entities",
            json={
                "name": "Test Entity Auth Fields",
                "comment": "test entity",
                "auth": {"telegram_id": 123456789, "signal_id": "sig-1"},
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_data = response.json()
        assert entity_data["auth"]["telegram_id"] == 123456789
        assert entity_data["auth"]["signal_id"] == "sig-1"
