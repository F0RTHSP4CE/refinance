"""Tests for the guest donation feature."""

import uuid
from decimal import Decimal

import pytest
from app.app import app
from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.seeding import anonymous_entity, f0_entity
from app.uow import UnitOfWork
from fastapi.testclient import TestClient

FAKE_PAYMENT_URL = "https://keepz.me/pay/testtoken123"


def _patch_keepz(monkeypatch):
    from app.services.keepz import KeepzService

    monkeypatch.setattr(
        KeepzService,
        "create_payment_link",
        lambda self, *, amount, currency, commission_type, note: FAKE_PAYMENT_URL,
    )
    monkeypatch.setattr(
        KeepzService,
        "resolve_payment_url",
        lambda self, url: url,
    )


def _active_config():
    """Return the currently active Config (test override or default)."""
    provider = app.dependency_overrides.get(get_config, get_config)
    return provider()


def _complete_deposit(deposit_uuid_str: str, config) -> None:
    """Look up a deposit by UUID and mark it complete via the service layer."""
    db_conn = DatabaseConnection(config=config)
    session = db_conn.get_session()
    with UnitOfWork(session) as uow:
        container = ServiceContainer(uow, config)
        deposit = container.deposit_service.get_by_uuid(uuid.UUID(deposit_uuid_str))
        container.deposit_service.complete(deposit.id)


class TestDonationEndpoints:
    """Tests for the public /donations HTTP endpoints."""

    @pytest.fixture(autouse=True)
    def patch_keepz(self, monkeypatch):
        _patch_keepz(monkeypatch)

    def test_create_donation_requires_no_auth(self, test_app: TestClient):
        """POST /donations works without an x-token header."""
        response = test_app.post(
            "/donations",
            json={"amount": "20.00", "currency": "GEL", "comment": "test donation"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending"
        assert data["currency"] == "GEL"
        assert Decimal(data["amount"]) == Decimal("20.00")
        assert "deposit_uuid" in data
        assert data["payment_url"] == FAKE_PAYMENT_URL

    def test_create_donation_comment_is_optional(self, test_app: TestClient):
        """Omitting comment still creates a donation successfully."""
        response = test_app.post(
            "/donations",
            json={"amount": "5.00", "currency": "GEL"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_create_donation_rejects_zero_amount(self, test_app: TestClient):
        response = test_app.post(
            "/donations",
            json={"amount": "0", "currency": "GEL"},
        )
        assert response.status_code == 422

    def test_create_donation_rejects_negative_amount(self, test_app: TestClient):
        response = test_app.post(
            "/donations",
            json={"amount": "-1.00", "currency": "GEL"},
        )
        assert response.status_code == 422

    def test_get_donation_by_uuid_requires_no_auth(self, test_app: TestClient):
        """GET /donations/{uuid} returns deposit info without auth."""
        create = test_app.post(
            "/donations",
            json={"amount": "10.00", "currency": "GEL", "comment": "hi"},
        )
        assert create.status_code == 200
        deposit_uuid = create.json()["deposit_uuid"]

        response = test_app.get(f"/donations/{deposit_uuid}")
        assert response.status_code == 200
        data = response.json()
        assert data["deposit_uuid"] == deposit_uuid
        assert data["status"] == "pending"
        assert Decimal(data["amount"]) == Decimal("10.00")
        assert data["payment_url"] == FAKE_PAYMENT_URL

    def test_get_donation_unknown_uuid_returns_404(self, test_app: TestClient):
        response = test_app.get("/donations/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    def test_get_donation_blocks_non_anonymous_deposit(
        self, test_app: TestClient, token
    ):
        """UUID of a deposit belonging to a non-anonymous entity returns 404."""
        create = test_app.post(
            "/deposits/providers/keepz",
            params={"to_entity_id": f0_entity.id, "amount": "10.00", "currency": "GEL"},
            headers={"x-token": token},
        )
        assert create.status_code == 200
        deposit_id = create.json()["id"]

        # Resolve the UUID via the service layer (not exposed by the HTTP API)
        config = _active_config()
        db_conn = DatabaseConnection(config=config)
        session = db_conn.get_session()
        try:
            container = ServiceContainer(session, config)
            deposit = container.deposit_service.get(deposit_id)
            regular_uuid = str(deposit.uuid)
        finally:
            session.close()

        response = test_app.get(f"/donations/{regular_uuid}")
        assert response.status_code == 404


class TestDonationCompletion:
    """Tests that completing a donation deposit triggers the correct downstream logic."""

    @pytest.fixture(autouse=True)
    def patch_keepz(self, monkeypatch):
        _patch_keepz(monkeypatch)

    @pytest.fixture(autouse=True)
    def capture_notifications(self, monkeypatch):
        self.sent_notifications = []
        from app.services.notification import NotificationService

        def _fake_send_to_chat(svc, chat_id, message, *, topic_id=None):
            self.sent_notifications.append(
                {"chat_id": chat_id, "message": message, "topic_id": topic_id}
            )
            return True

        monkeypatch.setattr(NotificationService, "send_to_chat", _fake_send_to_chat)

    def test_completion_creates_donation_transfer(
        self, test_app: TestClient, token, monkeypatch
    ):
        """Completing a donation deposit creates an anonymous→F0 transfer tagged 'donation'."""
        create = test_app.post(
            "/donations",
            json={"amount": "15.00", "currency": "GEL", "comment": "keep it up!"},
        )
        assert create.status_code == 200
        deposit_uuid = create.json()["deposit_uuid"]

        config = _active_config()
        monkeypatch.setattr(config, "donation_notification_chat_id", None)
        _complete_deposit(deposit_uuid, config)

        tx_resp = test_app.get(
            "/transactions",
            params={
                "from_entity_id": anonymous_entity.id,
                "to_entity_id": f0_entity.id,
                "amount_min": "14.99",
                "amount_max": "15.01",
            },
            headers={"x-token": token},
        )
        assert tx_resp.status_code == 200
        items = tx_resp.json()["items"]
        assert len(items) == 1
        tx = items[0]
        assert Decimal(tx["amount"]) == Decimal("15.00")
        assert tx["currency"].lower() == "gel"
        assert tx["comment"] == "keep it up!"
        tag_names = [t["name"] for t in tx["tags"]]
        assert "donation" in tag_names

    def test_completion_sends_telegram_notification(
        self, test_app: TestClient, monkeypatch
    ):
        """Notification is sent when donation_notification_chat_id is configured."""
        create = test_app.post(
            "/donations",
            json={"amount": "25.00", "currency": "GEL", "comment": "nice work"},
        )
        assert create.status_code == 200
        deposit_uuid = create.json()["deposit_uuid"]

        config = _active_config()
        monkeypatch.setattr(config, "donation_notification_chat_id", 99999)
        _complete_deposit(deposit_uuid, config)

        assert len(self.sent_notifications) == 1
        notif = self.sent_notifications[0]
        assert notif["chat_id"] == 99999
        assert "25" in notif["message"]
        assert "nice work" in notif["message"]

    def test_completion_no_notification_when_chat_not_configured(
        self, test_app: TestClient, monkeypatch
    ):
        """No notification is sent when donation_notification_chat_id is None."""
        create = test_app.post(
            "/donations",
            json={"amount": "5.00", "currency": "GEL"},
        )
        assert create.status_code == 200
        deposit_uuid = create.json()["deposit_uuid"]

        config = _active_config()
        monkeypatch.setattr(config, "donation_notification_chat_id", None)
        _complete_deposit(deposit_uuid, config)

        assert self.sent_notifications == []

    def test_regular_deposit_does_not_trigger_donation_flow(
        self, test_app: TestClient, token, monkeypatch
    ):
        """Completing a regular deposit to a non-anonymous entity creates no donation transfer."""
        create = test_app.post(
            "/deposits/providers/keepz",
            params={"to_entity_id": f0_entity.id, "amount": "10.00", "currency": "GEL"},
            headers={"x-token": token},
        )
        assert create.status_code == 200
        deposit_id = create.json()["id"]

        config = _active_config()
        monkeypatch.setattr(config, "donation_notification_chat_id", 99999)
        db_conn = DatabaseConnection(config=config)
        session = db_conn.get_session()
        with UnitOfWork(session) as uow:
            container = ServiceContainer(uow, config)
            container.deposit_service.complete(deposit_id)

        # No notification should fire for a non-anonymous deposit
        assert self.sent_notifications == []
