"""Exercise the Keepz provider with the gateway's HTTP response formats."""

import json
from collections import deque
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlsplit

import jwt
import pytest
import requests
from app.app import app
from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.libs.keepz_cli import keepz_api
from app.models.entity import Entity
from app.seeding import f0_entity, keepz_deposit_provider
from app.uow import UnitOfWork

SHORT_URL = "https://tiny.keepz.me/test"
PAYMENT_URL = "https://app.keepz.me/pay?qrType=CUSTOM&productId=test"


def _access_token(token_id):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "exp": now + timedelta(minutes=10),
            "iat": now,
            "jti": token_id,
            "iss": "test-issuer",
            "aud": "test-account",
            "sub": "test-subject",
            "typ": "Bearer",
            "azp": "test-client",
            "session_state": "test-session",
            "allowed-origins": [],
            "realm_access": {},
            "resource_access": {},
            "scope": "profile",
            "sid": "test-sid",
            "email_verified": False,
        },
        "test-key",
        algorithm="HS256",
    )


@pytest.fixture
def gateway(monkeypatch):
    responses = deque()
    calls = []

    def request(session, method, url, **kwargs):
        expected_method, path, status, value = responses.popleft()
        assert (method, urlsplit(url).path) == (expected_method, path)
        calls.append((session.headers.copy(), kwargs))
        if isinstance(value, Exception):
            raise value
        response = requests.Response()
        response.status_code = status
        response.url = PAYMENT_URL if url == SHORT_URL else url
        response._content = json.dumps({"value": value}).encode()
        return response

    monkeypatch.setattr(requests.Session, "request", request)
    yield responses, calls
    assert not responses


@pytest.fixture
def keepz_db(test_app):
    db = DatabaseConnection(app.dependency_overrides[get_config]())
    yield db
    db.engine.dispose()


def _poll(db):
    with UnitOfWork(db.get_session()) as uow:
        config = app.dependency_overrides[get_config]()
        provider = ServiceContainer(uow, config).keepz_deposit_provider_service
        return provider.poll_pending_deposits()


class TestKeepzProvider:
    def test_sms_login_payment_link_and_status(
        self, test_app, token, gateway, keepz_db
    ):
        responses, calls = gateway
        access_token = _access_token("login")
        login = {
            "access_token": access_token,
            "refresh_token": "refresh",
            "expires_in": 600,
        }
        responses.extend(
            [
                ("POST", "/common-service/api/v1/auth/check", 200, {}),
                ("POST", "/common-service/api/v1/auth/send-sms", 200, None),
                ("POST", "/common-service/api/v1/auth/verify-sms", 202, "sms-id"),
                ("POST", "/common-service/api/v1/auth/login", 200, login),
                (
                    "GET",
                    "/common-service/api/v1/profile/details",
                    200,
                    {"userId": "keepz-user"},
                ),
                ("POST", "/payment-service/api/merchant/product", 200, SHORT_URL),
                ("GET", "/test", 200, None),
            ]
        )
        headers = {"x-token": token}
        phone = {"phone": "555123456", "country_code": "+995"}
        assert (
            test_app.post(
                "/keepz/auth/send-sms", json=phone, headers=headers
            ).status_code
            == 200
        )
        response = test_app.post(
            "/keepz/auth/login", json={**phone, "code": "123456"}, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["user_id"] == "keepz-user"
        assert (
            test_app.get("/keepz/auth/status", headers=headers).json()
            == response.json()
        )
        assert calls[0][0]["user-agent"] == keepz_api.DEFAULT_USER_AGENT
        assert calls[0][1]["json"]["phone"] == "995555123456"
        assert calls[1][1]["json"]["countryCode"] == "995"
        assert calls[2][1]["json"]["countryCode"] == "995"
        login_request = calls[3][1]["json"]
        assert login_request["deviceToken"]
        assert login_request["version"] == keepz_api.DEFAULT_APP_VERSION
        assert login_request["mobileNumber"] == "995555123456"
        assert login_request["userSMSId"] == "sms-id"

        response = test_app.post(
            "/deposits/providers/keepz",
            params={
                "to_entity_id": f0_entity.id,
                "amount": "12.34",
                "note": "match-me",
            },
            headers=headers,
        )
        assert response.status_code == 200
        deposit = response.json()
        assert deposit["details"]["keepz"]["payment_url"] == PAYMENT_URL
        assert calls[5][0]["authorization"] == f"Bearer {access_token}"
        assert calls[5][1]["params"]["note"] == "match-me"
        assert "authorization" not in calls[6][0]

        deposit_path = f"/deposits/{deposit['id']}"
        tx = {"id": 123, "note": "match-me", "amount": 12.00, "currencyCode": "GEL"}
        responses.append(
            (
                "POST",
                "/payment-service/api/v1/generic-transaction/filter",
                200,
                {
                    "transactionsPage": {
                        "sort": [],
                        "content": [{**tx, "status": "PENDING"}],
                    }
                },
            )
        )
        assert _poll(keepz_db) == 0
        pending = test_app.get(deposit_path, headers=headers).json()
        assert pending["status"] == "pending"
        assert pending["details"]["keepz"]["transaction_id"] == 123

        responses.append(
            (
                "GET",
                "/payment-service/api/v1/generic-transaction/123",
                200,
                {**tx, "note": None, "status": "SUCCESS"},
            )
        )
        assert _poll(keepz_db) == 1
        completed = test_app.get(deposit_path, headers=headers).json()
        assert completed["status"] == "completed"
        assert Decimal(completed["amount"]) == Decimal("12.00")
        assert completed["details"]["keepz"]["transaction"]["status"] == "SUCCESS"
        assert _poll(keepz_db) == 0

    def test_rotated_credentials_persist_when_create_fails(
        self, test_app, token, gateway, keepz_db
    ):
        responses, calls = gateway
        access_token = _access_token("before-rotation")
        refreshed_token = _access_token("after-rotation")
        with keepz_db.get_session() as db, db.begin():
            db.get(Entity, keepz_deposit_provider.id).auth = {
                "keepz": {
                    "access_token": access_token,
                    "refresh_token": "old-refresh",
                    "obtained_at": datetime.now(timezone.utc).isoformat(),
                    "user_id": "legacy-user",
                },
            }
        responses.extend(
            [
                ("POST", "/payment-service/api/merchant/product", 401, None),
                (
                    "POST",
                    "/common-service/api/v1/auth/refresh-login",
                    200,
                    {"access_token": refreshed_token, "refresh_token": "new-refresh"},
                ),
                ("POST", "/payment-service/api/merchant/product", 200, None),
                (
                    "POST",
                    "/payment-service/api/merchant/product",
                    200,
                    {"shortUrl": SHORT_URL},
                ),
                ("GET", "/test", 0, requests.ConnectionError("redirect unavailable")),
            ]
        )
        params = {
            "to_entity_id": f0_entity.id,
            "amount": "10.00",
            "note": "refresh-test",
        }
        headers = {"x-token": token}
        response = test_app.post(
            "/deposits/providers/keepz", params=params, headers=headers
        )
        assert response.status_code == 502
        response = test_app.post(
            "/deposits/providers/keepz", params=params, headers=headers
        )
        assert response.status_code == 200
        assert response.json()["details"]["keepz"]["payment_url"] == SHORT_URL
        assert calls[1][1]["json"] == {"refresh_token": "old-refresh"}
        assert calls[2][0]["authorization"] == f"Bearer {refreshed_token}"
        assert calls[3][0]["authorization"] == f"Bearer {refreshed_token}"
        with keepz_db.get_session() as db:
            bundle = db.get(Entity, keepz_deposit_provider.id).auth["keepz"]["bundle"]
            assert bundle["refresh_token"] == "new-refresh"
            assert bundle["user_id"] == "legacy-user"
