"""Tests for token authentication"""

import hashlib
import hmac
import time

from app.config import get_config
from app.errors.entity import DuplicateEntityAuthBinding
from app.services.entity import EntityService
from fastapi.testclient import TestClient


def _build_telegram_payload(bot_token: str, **overrides):
    payload = {
        "id": 123456789,
        "first_name": "Alice",
        "username": "alice",
        "auth_date": int(time.time()),
    }
    payload.update(overrides)
    check_data = "\n".join(
        f"{key}={value}"
        for key, value in sorted(payload.items())
        if value is not None and key not in {"hash", "link_to_current_entity"}
    )
    secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
    payload["hash"] = hmac.new(
        secret_key, check_data.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return payload


def _set_telegram_bot_token(test_app: TestClient, bot_token: str) -> None:
    override = test_app.app.dependency_overrides[get_config]
    config = override()
    config.telegram_bot_api_token = bot_token


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
                "auth": {"telegram_id": 123456790, "signal_id": "sig-1"},
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_data = response.json()
        assert entity_data["auth"]["telegram_id"] == 123456790
        assert entity_data["auth"]["signal_id"] == "sig-1"

    def test_telegram_login_returns_token_for_linked_entity(
        self, test_app: TestClient, token
    ):
        response = test_app.post(
            "/entities",
            json={"name": "Telegram Login Entity", "auth": {"telegram_id": 123456789}},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_id = response.json()["id"]

        payload = _build_telegram_payload("telegram-test-token")
        _set_telegram_bot_token(test_app, "telegram-test-token")

        response = test_app.post("/tokens/telegram-login", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == entity_id
        assert data["linked"] is False
        assert data["token"]

    def test_telegram_login_rejects_duplicate_linked_entities(
        self, test_app: TestClient, monkeypatch
    ):
        _set_telegram_bot_token(test_app, "telegram-test-token")

        def _raise_duplicate(self, telegram_id: int):
            raise DuplicateEntityAuthBinding(f"telegram_id={telegram_id}")

        monkeypatch.setattr(EntityService, "get_by_telegram_id", _raise_duplicate)

        response = test_app.post(
            "/tokens/telegram-login",
            json=_build_telegram_payload("telegram-test-token"),
        )
        assert response.status_code == 409
        data = response.json()
        assert data["error_code"] == 4001
        assert "telegram_id=123456789" in data["error"]

    def test_telegram_config_reports_missing_username(self, test_app: TestClient):
        override = test_app.app.dependency_overrides[get_config]
        config = override()
        config.telegram_bot_api_token = "telegram-test-token"
        config.telegram_bot_username = ""

        response = test_app.get("/tokens/telegram-config")
        assert response.status_code == 200
        assert response.json() == {
            "enabled": False,
            "bot_username": None,
            "reason": "missing_bot_username",
        }

    def test_telegram_config_reports_missing_token(self, test_app: TestClient):
        override = test_app.app.dependency_overrides[get_config]
        config = override()
        config.telegram_bot_api_token = ""
        config.telegram_bot_username = "refinance_bot"

        response = test_app.get("/tokens/telegram-config")
        assert response.status_code == 200
        assert response.json() == {
            "enabled": False,
            "bot_username": "refinance_bot",
            "reason": "missing_bot_token",
        }

    def test_telegram_config_reports_enabled(self, test_app: TestClient):
        override = test_app.app.dependency_overrides[get_config]
        config = override()
        config.telegram_bot_api_token = "telegram-test-token"
        config.telegram_bot_username = "refinance_bot"

        response = test_app.get("/tokens/telegram-config")
        assert response.status_code == 200
        assert response.json() == {
            "enabled": True,
            "bot_username": "refinance_bot",
            "reason": None,
        }

    def test_telegram_login_rejects_invalid_hash(self, test_app: TestClient):
        _set_telegram_bot_token(test_app, "telegram-test-token")

        payload = _build_telegram_payload("telegram-test-token")
        payload["hash"] = "bad-hash"

        response = test_app.post("/tokens/telegram-login", json=payload)
        assert response.status_code == 403
        assert response.json()["detail"] == "Telegram auth signature is invalid."

    def test_telegram_login_rejects_expired_payload(self, test_app: TestClient):
        _set_telegram_bot_token(test_app, "telegram-test-token")

        payload = _build_telegram_payload(
            "telegram-test-token",
            auth_date=int(time.time()) - (60 * 60 * 24 + 120),
        )

        response = test_app.post("/tokens/telegram-login", json=payload)
        assert response.status_code == 403
        assert response.json()["detail"] == "Telegram auth payload has expired."

    def test_telegram_connect_links_current_entity(
        self, test_app: TestClient, token
    ):
        response = test_app.post(
            "/entities",
            json={"name": "Telegram Connect Entity"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        entity_id = response.json()["id"]

        entity_token = test_app.get(f"/tokens/{entity_id}").json()

        _set_telegram_bot_token(test_app, "telegram-test-token")

        payload = _build_telegram_payload(
            "telegram-test-token",
            id=555444333,
            link_to_current_entity=True,
        )

        response = test_app.post(
            "/tokens/telegram-login",
            json=payload,
            headers={"x-token": entity_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entity_id"] == entity_id
        assert data["linked"] is True

        entity_response = test_app.get(
            f"/entities/{entity_id}",
            headers={"x-token": entity_token},
        )
        assert entity_response.status_code == 200
        assert entity_response.json()["auth"]["telegram_id"] == 555444333
