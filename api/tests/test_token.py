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

    def test_get_token_by_card_hash(self, test_app: TestClient, token):
        """Test getting token using card_hash"""
        # First, create a test entity
        response = test_app.post(
            "/entities",
            json={"name": "Test Entity", "comment": "test"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_id = response.json()["id"]

        # Add a card via the new endpoint
        card_hash = "test_card_hash_uniq_a"
        response = test_app.post(
            f"/entities/{entity_id}/cards",
            json={"comment": "test-card", "card_hash": card_hash},
            headers={"x-token": token},
        )
        assert response.status_code == 200

        # Now try to get token using card_hash
        response = test_app.post("/tokens/by-card-hash", json={"card_hash": card_hash})
        assert response.status_code == 200
        assert "token" in response.json()

        # Verify the token works
        token_from_card = response.json()["token"]
        response = test_app.get("/entities", headers={"x-token": token_from_card})
        assert response.status_code == 200

    def test_get_token_by_invalid_card_hash(self, test_app: TestClient):
        """Test getting token using invalid card_hash"""
        response = test_app.post(
            "/tokens/by-card-hash", json={"card_hash": "invalid_card_hash"}
        )
        assert response.status_code == 418  # NotFoundError returns 418

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

    def test_card_hash_not_exposed_in_api_response(self, test_app: TestClient, token):
        """Test that card_hash is NOT returned in entity API responses"""
        # Create an entity
        response = test_app.post(
            "/entities",
            json={
                "name": "Test Entity for Card Hash",
                "comment": "test entity",
                "auth": {"telegram_id": 987654321},
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_data = response.json()
        entity_id = entity_data["id"]

        # Add a card to the entity
        unique_hash = "test_card_hash_uniq_1"
        response = test_app.post(
            f"/entities/{entity_id}/cards",
            json={"comment": "test-card", "card_hash": unique_hash},
            headers={"x-token": token},
        )
        assert response.status_code == 200

        # Get the entity and verify card_hash is exposed as boolean
        response = test_app.get(f"/entities/{entity_id}", headers={"x-token": token})
        assert response.status_code == 200
        entity_data = response.json()

        # Verify auth still includes telegram_id, but no card_hash field
        assert entity_data["auth"]["telegram_id"] == 987654321
        assert "card_hash" not in entity_data["auth"]

        # Verify we can still get token by card_hash (internal functionality works)
        response = test_app.post(
            "/tokens/by-card-hash", json={"card_hash": unique_hash}
        )
        assert response.status_code == 200
        token_data = response.json()
        assert "token" in token_data

    def test_card_hash_field_removed_from_auth(self, test_app: TestClient, token):
        """Ensure auth.card_hash is ignored on input and not exposed on output"""
        # Create an entity with an extra auth.card_hash field (should be ignored by schema)
        response = test_app.post(
            "/entities",
            json={
                "name": "Test Entity No Card Hash",
                "comment": "test entity",
                # card_hash provided here should be ignored (card management is via /entities/{id}/cards)
                "auth": {"telegram_id": 123456789, "card_hash": "should_be_ignored"},
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_data = response.json()
        # Ensure the extra field is not present in the API response
        assert "card_hash" not in entity_data.get("auth", {})
