from __future__ import annotations

import datetime

from app.app import app
from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.models.invoice import Invoice
from app.seeding import f0_entity, fee_tag, resident_tag, room_tag, utilities_tag
from app.uow import UnitOfWork
from fastapi.testclient import TestClient


def _config():
    return app.dependency_overrides[get_config]()


def _run_auto_pay() -> int:
    config = _config()
    connection = DatabaseConnection(config)
    try:
        with UnitOfWork(connection.get_session()) as uow:
            return ServiceContainer(
                uow.db, config
            ).invoice_service.auto_pay_oldest_invoices()
    finally:
        connection.engine.dispose()


def _reconcile(*, apply: bool) -> list[dict]:
    config = _config()
    connection = DatabaseConnection(config)
    try:
        with UnitOfWork(connection.get_session()) as uow:
            return ServiceContainer(
                uow.db, config
            ).invoice_service.reconcile_recipient_rotations(apply=apply)
    finally:
        connection.engine.dispose()


class TestInvoiceRecipientRotation:
    def test_bulk_fee_rotation_and_explicit_recipient(
        self, test_app: TestClient, token: str
    ):
        payer = test_app.post(
            "/entities",
            json={"name": "rotation payer", "tag_ids": [resident_tag.id]},
            headers={"x-token": token},
        ).json()["id"]

        def issue(period: str, room_entity_id: int | None = None) -> dict:
            room_item = {
                "to_tag_id": room_tag.id,
                "amounts": [{"currency": "usd", "amount": "8"}],
            }
            if room_entity_id is not None:
                room_item["to_entity_id"] = room_entity_id
            response = test_app.post(
                "/invoices/bulk",
                json={
                    "from_entity_ids": [payer],
                    "from_tag_ids": [resident_tag.id],
                    "billing_period": period,
                    "tag_ids": [fee_tag.id],
                    "items": [
                        {
                            "to_entity_id": f0_entity.id,
                            "amounts": [{"currency": "usd", "amount": "42"}],
                        },
                        room_item,
                    ],
                },
                headers={"x-token": token},
            )
            assert response.status_code == 200, response.text
            invoice_id = response.json()["invoice_ids"][0]
            return test_app.get(
                f"/invoices/{invoice_id}", headers={"x-token": token}
            ).json()

        july = issue("2026-07-01")
        august = issue("2026-08-01")
        december = issue("2026-12-01")
        january = issue("2027-01-01")
        wrapped = issue("2027-02-01")
        explicit = issue("2026-09-01", room_entity_id=61)

        def room_recipient(invoice: dict) -> int:
            return next(
                item["to_entity_id"]
                for item in invoice["items"]
                if item["to_tag_id"] == room_tag.id
            )

        assert room_recipient(july) == 60
        assert room_recipient(august) == 58
        assert room_recipient(december) == 59
        assert room_recipient(january) == 61
        assert room_recipient(wrapped) == 60
        assert room_recipient(explicit) == 61

    def test_invalid_rotated_entity_rejects_fee_issuance(
        self, test_app: TestClient, token: str
    ):
        config = _config()
        original = config.invoice_recipient_rotations_raw
        config.invoice_recipient_rotations_raw = (
            '[{"tag_id":19,"anchor_period":"2026-07","entity_ids":[999999]}]'
        )
        try:
            response = test_app.post(
                "/invoices/bulk",
                json={
                    "from_entity_ids": [f0_entity.id],
                    "from_tag_ids": [resident_tag.id],
                    "billing_period": "2026-07-01",
                    "tag_ids": [fee_tag.id],
                    "items": [
                        {
                            "to_tag_id": room_tag.id,
                            "amounts": [{"currency": "usd", "amount": "8"}],
                        }
                    ],
                },
                headers={"x-token": token},
            )
        finally:
            config.invoice_recipient_rotations_raw = original

        assert response.status_code == 418
        assert response.json()["error_code"] == 8029

    def test_reconcile_is_dry_run_and_idempotent(
        self, test_app: TestClient, token: str
    ):
        response = test_app.post(
            "/invoices",
            json={
                "from_entity_id": f0_entity.id,
                "billing_period": "2026-07-01",
                "tag_ids": [fee_tag.id],
                "items": [
                    {
                        # Legacy fee invoices used utilities as the selectable
                        # constraint; reconciliation migrates it to room.
                        "to_tag_id": utilities_tag.id,
                        "amounts": [{"currency": "usd", "amount": "8"}],
                    }
                ],
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200, response.text
        invoice_id = response.json()["id"]

        preview = _reconcile(apply=False)
        assert any(change["invoice_id"] == invoice_id for change in preview)
        change = next(
            change for change in preview if change["invoice_id"] == invoice_id
        )
        assert change["previous_to_tag_id"] == utilities_tag.id
        assert change["to_tag_id"] == room_tag.id
        unchanged = test_app.get(
            f"/invoices/{invoice_id}", headers={"x-token": token}
        ).json()
        assert unchanged["items"][0]["to_entity_id"] is None
        assert unchanged["items"][0]["to_tag_id"] == utilities_tag.id

        applied = _reconcile(apply=True)
        assert any(change["invoice_id"] == invoice_id for change in applied)
        updated = test_app.get(
            f"/invoices/{invoice_id}", headers={"x-token": token}
        ).json()
        assert updated["items"][0]["to_entity_id"] == 60
        assert updated["items"][0]["to_tag_id"] == room_tag.id
        assert _reconcile(apply=True) == []


class TestInvoiceAutoPayGrace:
    def test_all_invoices_wait_until_grace_period(
        self, test_app: TestClient, token: str
    ):
        config = _config()
        original_grace = config.invoice_auto_pay_grace_days
        config.invoice_auto_pay_grace_days = 7
        try:
            payer = test_app.post(
                "/entities",
                json={"name": "grace payer"},
                headers={"x-token": token},
            ).json()["id"]
            source = test_app.post(
                "/entities",
                json={"name": "grace source"},
                headers={"x-token": token},
            ).json()["id"]
            test_app.post(
                "/transactions",
                json={
                    "from_entity_id": source,
                    "to_entity_id": payer,
                    "amount": "100",
                    "currency": "usd",
                    "status": "completed",
                },
                headers={"x-token": token},
            )
            invoice = test_app.post(
                "/invoices",
                json={
                    "from_entity_id": payer,
                    "to_entity_id": f0_entity.id,
                    "amounts": [{"currency": "usd", "amount": "42"}],
                },
                headers={"x-token": token},
            ).json()
            multi_invoice = test_app.post(
                "/invoices",
                json={
                    "from_entity_id": payer,
                    "items": [
                        {
                            "to_entity_id": f0_entity.id,
                            "amounts": [{"currency": "usd", "amount": "8"}],
                        }
                    ],
                },
                headers={"x-token": token},
            ).json()

            assert _run_auto_pay() == 0
            for invoice_id in (invoice["id"], multi_invoice["id"]):
                assert (
                    test_app.get(
                        f"/invoices/{invoice_id}", headers={"x-token": token}
                    ).json()["status"]
                    == "pending"
                )

            connection = DatabaseConnection(config)
            try:
                with UnitOfWork(connection.get_session()) as uow:
                    uow.db.query(Invoice).filter(
                        Invoice.id.in_([invoice["id"], multi_invoice["id"]])
                    ).update(
                        {
                            Invoice.created_at: datetime.datetime.now()
                            - datetime.timedelta(days=7)
                            + datetime.timedelta(seconds=1)
                        },
                        synchronize_session=False,
                    )
            finally:
                connection.engine.dispose()

            assert _run_auto_pay() == 0

            connection = DatabaseConnection(config)
            try:
                with UnitOfWork(connection.get_session()) as uow:
                    uow.db.query(Invoice).filter(
                        Invoice.id.in_([invoice["id"], multi_invoice["id"]])
                    ).update(
                        {
                            Invoice.created_at: datetime.datetime.now()
                            - datetime.timedelta(days=7)
                        },
                        synchronize_session=False,
                    )
            finally:
                connection.engine.dispose()

            assert _run_auto_pay() == 2
            for invoice_id in (invoice["id"], multi_invoice["id"]):
                assert (
                    test_app.get(
                        f"/invoices/{invoice_id}", headers={"x-token": token}
                    ).json()["status"]
                    == "paid"
                )
        finally:
            config.invoice_auto_pay_grace_days = original_grace
