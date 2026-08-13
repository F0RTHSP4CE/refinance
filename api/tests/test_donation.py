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

    def test_create_donation_rejects_below_min_amount(
        self, test_app: TestClient, monkeypatch
    ):
        """Amount below donation_min_amount is rejected."""
        config = _active_config()
        monkeypatch.setattr(config, "donation_min_amount", Decimal("5"))
        response = test_app.post(
            "/donations",
            json={"amount": "4.99", "currency": "GEL"},
        )
        assert response.status_code == 422

    def test_create_donation_rejects_above_max_amount(
        self, test_app: TestClient, monkeypatch
    ):
        """Amount above donation_max_amount is rejected."""
        config = _active_config()
        monkeypatch.setattr(config, "donation_max_amount", Decimal("100"))
        response = test_app.post(
            "/donations",
            json={"amount": "100.01", "currency": "GEL"},
        )
        assert response.status_code == 422

    def test_create_donation_rejects_oversized_comment(self, test_app: TestClient):
        """Comments longer than 500 characters are rejected."""
        response = test_app.post(
            "/donations",
            json={"amount": "10.00", "currency": "GEL", "comment": "x" * 501},
        )
        assert response.status_code == 422

    def test_create_donation_rejects_invalid_currency(self, test_app: TestClient):
        """Currency longer than 10 characters is rejected."""
        response = test_app.post(
            "/donations",
            json={"amount": "10.00", "currency": "A" * 11},
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


class TestDonationRecipients:
    """Tests for routing donations to rooms (public recipient selection)."""

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

    @staticmethod
    def _room(test_app: TestClient, name: str = "music studio") -> dict:
        recipients = test_app.get("/donations/recipients").json()
        return next(r for r in recipients if r["name"] == name)

    def test_list_recipients_requires_no_auth(self, test_app: TestClient):
        """GET /donations/recipients returns F0 first, then all room entities."""
        response = test_app.get("/donations/recipients")
        assert response.status_code == 200
        data = response.json()
        assert data[0] == {"id": f0_entity.id, "name": "F0", "general": True}
        room_names = [r["name"] for r in data[1:]]
        assert "music studio" in room_names
        assert "kitchen" in room_names
        assert all(r["general"] is False for r in data[1:])

    def test_recipients_exclude_inactive_rooms(self, test_app: TestClient, token):
        room = self._room(test_app, "chill zone")
        response = test_app.patch(
            f"/entities/{room['id']}",
            json={"active": False},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        names = [r["name"] for r in test_app.get("/donations/recipients").json()]
        assert room["name"] not in names

        # restore for the rest of the class (the DB is shared within a test class)
        response = test_app.patch(
            f"/entities/{room['id']}",
            json={"active": True},
            headers={"x-token": token},
        )
        assert response.status_code == 200

    def test_create_donation_with_room_recipient(self, test_app: TestClient):
        """Recipient is stored on the deposit and echoed back by the API."""
        room = self._room(test_app)
        response = test_app.post(
            "/donations",
            json={
                "amount": "10.00",
                "currency": "GEL",
                "recipient_entity_id": room["id"],
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["recipient_name"] == room["name"]

        fetched = test_app.get(f"/donations/{data['deposit_uuid']}").json()
        assert fetched["recipient_name"] == room["name"]

    def test_create_donation_defaults_to_f0(self, test_app: TestClient):
        response = test_app.post(
            "/donations", json={"amount": "10.00", "currency": "GEL"}
        )
        assert response.status_code == 200
        assert response.json()["recipient_name"] == "F0"

    def test_create_donation_rejects_non_room_recipient(self, test_app: TestClient):
        """Seeded entity 2 (cash_in) is not a room, so it cannot receive donations."""
        response = test_app.post(
            "/donations",
            json={"amount": "10.00", "currency": "GEL", "recipient_entity_id": 2},
        )
        assert response.status_code == 422

    def test_create_donation_rejects_unknown_recipient(self, test_app: TestClient):
        response = test_app.post(
            "/donations",
            json={"amount": "10.00", "currency": "GEL", "recipient_entity_id": 999999},
        )
        assert response.status_code == 422

    def test_completion_routes_transfer_to_room(
        self, test_app: TestClient, token, monkeypatch
    ):
        """Completing a room donation transfers anonymous→room and notifies with the room name."""
        room = self._room(test_app)
        create = test_app.post(
            "/donations",
            json={
                "amount": "12.00",
                "currency": "GEL",
                "comment": "for the drums",
                "recipient_entity_id": room["id"],
            },
        )
        assert create.status_code == 200
        deposit_uuid = create.json()["deposit_uuid"]

        config = _active_config()
        monkeypatch.setattr(config, "donation_notification_chat_id", 99999)
        _complete_deposit(deposit_uuid, config)

        tx_resp = test_app.get(
            "/transactions",
            params={
                "from_entity_id": anonymous_entity.id,
                "to_entity_id": room["id"],
            },
            headers={"x-token": token},
        )
        assert tx_resp.status_code == 200
        items = tx_resp.json()["items"]
        assert len(items) == 1
        assert Decimal(items[0]["amount"]) == Decimal("12.00")
        assert "donation" in [t["name"] for t in items[0]["tags"]]

        assert len(self.sent_notifications) == 1
        message = self.sent_notifications[0]["message"]
        assert room["name"] in message
        assert "for the drums" in message

    def test_subscription_invoice_routes_to_room(
        self, test_app: TestClient, token, monkeypatch
    ):
        """Recipient survives the Stripe subscription round-trip: checkout metadata →
        StripeAuthorization → monthly invoice deposit → anonymous→room transfer."""
        from app.errors.stripe import StripeRequestError
        from app.models.stripe_authorization import StripeAuthorization
        from app.services.stripe import StripeInvoiceData, StripeService

        # a room not used by other tests in this class (the DB is shared within it)
        room = self._room(test_app, "electronics lab")
        fake_session = {
            "id": "cs_test_room",
            "mode": "subscription",
            "subscription": "sub_test_room",
            "customer": "cus_test_room",
            "metadata": {
                "entity_id": str(anonymous_entity.id),
                "mode": "guest_static",
                "static_amount": "10.00",
                "static_currency": "GEL",
                "donation_comment": "monthly for music",
                "donation_recipient_entity_id": str(room["id"]),
            },
        }
        monkeypatch.setattr(
            StripeService,
            "retrieve_checkout_session",
            lambda self, session_id, expand_setup_intent=False: fake_session,
        )

        def _no_subscription(self, subscription_id):
            raise StripeRequestError("not available in tests")

        monkeypatch.setattr(StripeService, "retrieve_subscription", _no_subscription)

        sync = test_app.post(
            "/donations/subscribe/sync",
            params={"checkout_session_id": "cs_test_room"},
        )
        assert sync.status_code == 200, sync.text

        config = _active_config()
        db_conn = DatabaseConnection(config=config)
        session = db_conn.get_session()
        try:
            auth = (
                session.query(StripeAuthorization)
                .filter_by(stripe_subscription_id="sub_test_room")
                .one()
            )
            assert auth.donation_recipient_entity_id == room["id"]
        finally:
            session.close()

        monkeypatch.setattr(config, "donation_notification_chat_id", 99999)
        invoice = StripeInvoiceData(
            id="in_test_room",
            subscription_id="sub_test_room",
            amount_paid=1000,
            currency="gel",
            billing_reason="subscription_cycle",
        )
        session = db_conn.get_session()
        with UnitOfWork(session) as uow:
            container = ServiceContainer(uow, config)
            created = (
                container.stripe_authorization_service.handle_subscription_invoice_paid(
                    invoice
                )
            )
        assert created is True

        tx_resp = test_app.get(
            "/transactions",
            params={
                "from_entity_id": anonymous_entity.id,
                "to_entity_id": room["id"],
            },
            headers={"x-token": token},
        )
        items = tx_resp.json()["items"]
        assert len(items) == 1
        assert Decimal(items[0]["amount"]) == Decimal("10.00")

        assert len(self.sent_notifications) == 1
        message = self.sent_notifications[0]["message"]
        assert "Subscription donation" in message
        assert room["name"] in message
