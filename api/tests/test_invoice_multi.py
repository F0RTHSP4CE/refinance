"""Tests for multi-recipient (multi-item) invoice feature."""

from decimal import Decimal

import pytest
from app.app import app
from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.uow import UnitOfWork
from fastapi.testclient import TestClient

# ── helpers ────────────────────────────────────────────────────────────────


def _entity(test_app, token, name):
    r = test_app.post("/entities", json={"name": name}, headers={"x-token": token})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _tag(test_app, token, name):
    r = test_app.post("/tags", json={"name": name}, headers={"x-token": token})
    assert r.status_code == 200, r.text
    return r.json()["id"]


def _add_tag(test_app, token, entity_id, tag_id):
    """Add a tag to an entity by merging with existing tags via PATCH."""
    entity = test_app.get(f"/entities/{entity_id}", headers={"x-token": token}).json()
    existing_tag_ids = [t["id"] for t in entity.get("tags", [])]
    if tag_id not in existing_tag_ids:
        existing_tag_ids.append(tag_id)
    r = test_app.patch(
        f"/entities/{entity_id}",
        json={"tag_ids": existing_tag_ids},
        headers={"x-token": token},
    )
    assert r.status_code == 200, r.text


def _fund(test_app, token, to_entity_id, amount, currency):
    import uuid

    bank = _entity(test_app, token, f"bank-{uuid.uuid4().hex[:6]}")
    r = test_app.post(
        "/transactions",
        json={
            "from_entity_id": bank,
            "to_entity_id": to_entity_id,
            "amount": amount,
            "currency": currency,
            "status": "completed",
        },
        headers={"x-token": token},
    )
    assert r.status_code == 200, r.text


def _create_multi_invoice(test_app, token, from_id, items):
    r = test_app.post(
        "/invoices",
        json={"from_entity_id": from_id, "items": items},
        headers={"x-token": token},
    )
    return r


def _run_auto_pay() -> int:
    config_provider = app.dependency_overrides.get(get_config, get_config)
    config = config_provider()
    db_conn = DatabaseConnection(config=config)
    session = db_conn.get_session()
    try:
        with UnitOfWork(session) as uow:
            container = ServiceContainer(uow, config)
            return container.invoice_service.auto_pay_oldest_invoices()
    finally:
        db_conn.engine.dispose()


# ── test classes ────────────────────────────────────────────────────────────


class TestMultiItemInvoiceCreate:
    def test_create_multi_item_invoice(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-create")
        to1 = _entity(test_app, token, "mi-to1-create")
        to2 = _entity(test_app, token, "mi-to2-create")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                },
                {
                    "to_entity_id": to2,
                    "amounts": [{"currency": "usd", "amount": "20.00"}],
                },
            ],
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["status"] == "pending"
        assert data["to_entity_id"] is None
        assert len(data["items"]) == 2
        item_to_ids = {item["to_entity_id"] for item in data["items"]}
        assert to1 in item_to_ids
        assert to2 in item_to_ids

    def test_create_multi_item_with_tag_filter(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-tag")
        tag = _tag(test_app, token, "mi-recipient-tag")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_tag_id": tag,
                    "amounts": [{"currency": "usd", "amount": "5.00"}],
                }
            ],
        )
        assert r.status_code == 200, r.text
        item = r.json()["items"][0]
        assert item["to_entity_id"] is None
        assert item["to_tag_id"] == tag

    def test_cannot_mix_items_and_simple(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-mix")
        to1 = _entity(test_app, token, "mi-to1-mix")
        r = test_app.post(
            "/invoices",
            json={
                "from_entity_id": payer,
                "to_entity_id": to1,
                "amounts": [{"currency": "usd", "amount": "10.00"}],
                "items": [
                    {
                        "to_entity_id": to1,
                        "amounts": [{"currency": "usd", "amount": "5.00"}],
                    }
                ],
            },
            headers={"x-token": token},
        )
        assert r.status_code == 422

    def test_item_must_have_amounts(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-noamt")
        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [{"to_entity_id": payer, "amounts": []}],
        )
        assert r.status_code == 422


class TestMultiItemInvoicePay:
    def test_pay_all_items_atomically(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-pay")
        to1 = _entity(test_app, token, "mi-to1-pay")
        to2 = _entity(test_app, token, "mi-to2-pay")
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                },
                {
                    "to_entity_id": to2,
                    "amounts": [{"currency": "usd", "amount": "20.00"}],
                },
            ],
        )
        assert r.status_code == 200
        invoice = r.json()
        items = invoice["items"]

        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": items[0]["id"],
                        "to_entity_id": items[0]["to_entity_id"],
                        "currency": "usd",
                        "amount": "10.00",
                    },
                    {
                        "item_id": items[1]["id"],
                        "to_entity_id": items[1]["to_entity_id"],
                        "currency": "usd",
                        "amount": "20.00",
                    },
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code == 200, pay_r.text
        assert pay_r.json()["status"] == "paid"

        # Each item has a transaction
        updated = test_app.get(
            f"/invoices/{invoice['id']}", headers={"x-token": token}
        ).json()
        assert updated["status"] == "paid"
        for item in updated["items"]:
            assert item["transaction_id"] is not None

    def test_auto_currency_selection_uses_affordable_total(
        self, test_app: TestClient, token
    ):
        payer = _entity(test_app, token, "mi-payer-affordable-currency")
        to1 = _entity(test_app, token, "mi-to1-affordable-currency")
        to2 = _entity(test_app, token, "mi-to2-affordable-currency")
        _fund(test_app, token, payer, "62.25", "gel")
        _fund(test_app, token, payer, "42.00", "usd")
        invoice = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [
                        {"currency": "gel", "amount": "55.00"},
                        {"currency": "usd", "amount": "20.00"},
                    ],
                },
                {
                    "to_entity_id": to2,
                    "amounts": [
                        {"currency": "gel", "amount": "60.00"},
                        {"currency": "usd", "amount": "22.00"},
                    ],
                },
            ],
        ).json()

        response = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item["id"],
                        "to_entity_id": item["to_entity_id"],
                    }
                    for item in invoice["items"]
                ]
            },
            headers={"x-token": token},
        )

        assert response.status_code == 200, response.text
        assert response.json()["status"] == "paid"
        transaction_ids = [item["transaction_id"] for item in response.json()["items"]]
        transactions = [
            test_app.get(
                f"/transactions/{transaction_id}", headers={"x-token": token}
            ).json()
            for transaction_id in transaction_ids
        ]
        assert {transaction["currency"] for transaction in transactions} == {"usd"}

    def test_pay_partial_items_rejected(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-partial")
        to1 = _entity(test_app, token, "mi-to1-partial")
        to2 = _entity(test_app, token, "mi-to2-partial")
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                },
                {
                    "to_entity_id": to2,
                    "amounts": [{"currency": "usd", "amount": "20.00"}],
                },
            ],
        )
        invoice = r.json()
        item_ids = [i["id"] for i in invoice["items"]]

        # Only submit one of the two items
        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item_ids[0],
                        "to_entity_id": invoice["items"][0]["to_entity_id"],
                        "currency": "usd",
                        "amount": "10.00",
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code != 200
        assert pay_r.json()["error_code"] == 8028  # InvoicePayItemsMismatch

    def test_pay_with_wrong_entity_for_tag(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-wrong-tag")
        tag = _tag(test_app, token, "mi-wrong-tag-filter")
        bad_entity = _entity(test_app, token, "mi-bad-entity")
        # bad_entity does NOT have the tag
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [{"to_tag_id": tag, "amounts": [{"currency": "usd", "amount": "5.00"}]}],
        )
        invoice = r.json()
        item_id = invoice["items"][0]["id"]

        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item_id,
                        "to_entity_id": bad_entity,
                        "currency": "usd",
                        "amount": "5.00",
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code != 200
        assert pay_r.json()["error_code"] == 8024  # InvoiceItemInvalidEntityTag

    def test_pay_with_correct_entity_for_tag(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-correct-tag")
        tag = _tag(test_app, token, "mi-correct-tag-filter")
        good_entity = _entity(test_app, token, "mi-good-entity")
        _add_tag(test_app, token, good_entity, tag)
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [{"to_tag_id": tag, "amounts": [{"currency": "usd", "amount": "5.00"}]}],
        )
        invoice = r.json()
        item_id = invoice["items"][0]["id"]

        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item_id,
                        "to_entity_id": good_entity,
                        "currency": "usd",
                        "amount": "5.00",
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code == 200, pay_r.text
        assert pay_r.json()["status"] == "paid"

    def test_currency_validation(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-curr")
        to1 = _entity(test_app, token, "mi-to1-curr")
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                }
            ],
        )
        invoice = r.json()
        item_id = invoice["items"][0]["id"]

        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item_id,
                        "to_entity_id": to1,
                        "currency": "gel",  # wrong currency
                        "amount": "10.00",
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code != 200
        assert pay_r.json()["error_code"] == 8025  # InvoiceItemCurrencyNotAllowed

    def test_amount_insufficient(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-insuf-amt")
        to1 = _entity(test_app, token, "mi-to1-insuf-amt")
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                }
            ],
        )
        invoice = r.json()
        item_id = invoice["items"][0]["id"]

        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item_id,
                        "to_entity_id": to1,
                        "currency": "usd",
                        "amount": "1.00",  # too little
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code != 200
        assert pay_r.json()["error_code"] == 8026  # InvoiceItemAmountInsufficient

    def test_insufficient_balance(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-insuf-bal")
        to1 = _entity(test_app, token, "mi-to1-insuf-bal")
        _fund(test_app, token, payer, "5.00", "usd")  # not enough

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                }
            ],
        )
        invoice = r.json()
        item_id = invoice["items"][0]["id"]

        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item_id,
                        "to_entity_id": to1,
                        "currency": "usd",
                        "amount": "10.00",
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code != 200
        assert pay_r.json()["error_code"] == 8012  # InvoiceInsufficientBalance

    def test_pay_items_on_simple_invoice_rejected(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-simple-rej")
        to1 = _entity(test_app, token, "mi-to1-simple-rej")

        r = test_app.post(
            "/invoices",
            json={
                "from_entity_id": payer,
                "to_entity_id": to1,
                "amounts": [{"currency": "usd", "amount": "10.00"}],
            },
            headers={"x-token": token},
        )
        assert r.status_code == 200
        invoice_id = r.json()["id"]

        pay_r = test_app.post(
            f"/invoices/{invoice_id}/pay-items",
            json={
                "items": [
                    {
                        "item_id": 99999,
                        "to_entity_id": to1,
                        "currency": "usd",
                        "amount": "10.00",
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code != 200
        assert pay_r.json()["error_code"] == 8021  # InvoiceIsNotMultiItem

    def test_simple_invoice_rejects_multi_item_endpoint(
        self, test_app: TestClient, token
    ):
        """Using invoice_id on a multi-item invoice via /transactions raises InvoiceIsMultiItem."""
        payer = _entity(test_app, token, "mi-payer-tx-reject")
        to1 = _entity(test_app, token, "mi-to1-tx-reject")
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                }
            ],
        )
        invoice_id = r.json()["id"]

        # Try creating a transaction with invoice_id (wrong path for multi-item)
        tx_r = test_app.post(
            "/transactions",
            json={
                "from_entity_id": payer,
                "to_entity_id": to1,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
                "invoice_id": invoice_id,
            },
            headers={"x-token": token},
        )
        assert tx_r.status_code != 200
        assert tx_r.json()["error_code"] == 8020  # InvoiceIsMultiItem


class TestMultiItemInvoiceAutoPayAndLifecycle:
    def test_auto_pay_multi_item_all_prefilled(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-autopay")
        to1 = _entity(test_app, token, "mi-to1-autopay")
        to2 = _entity(test_app, token, "mi-to2-autopay")
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                },
                {
                    "to_entity_id": to2,
                    "amounts": [{"currency": "usd", "amount": "15.00"}],
                },
            ],
        )
        assert r.status_code == 200
        invoice_id = r.json()["id"]

        paid_count = _run_auto_pay()
        assert paid_count >= 1

        updated = test_app.get(
            f"/invoices/{invoice_id}", headers={"x-token": token}
        ).json()
        assert updated["status"] == "paid"

    def test_auto_pay_skips_multi_item_with_missing_entity(
        self, test_app: TestClient, token
    ):
        payer = _entity(test_app, token, "mi-payer-skip")
        to1 = _entity(test_app, token, "mi-to1-skip")
        tag = _tag(test_app, token, "mi-skip-tag")
        _fund(test_app, token, payer, "50.00", "usd")

        # One item has no to_entity_id (only tag filter) — auto_pay must skip it
        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": to1,
                    "amounts": [{"currency": "usd", "amount": "10.00"}],
                },
                {"to_tag_id": tag, "amounts": [{"currency": "usd", "amount": "5.00"}]},
            ],
        )
        invoice_id = r.json()["id"]

        _run_auto_pay()

        updated = test_app.get(
            f"/invoices/{invoice_id}", headers={"x-token": token}
        ).json()
        assert updated["status"] == "pending"  # should NOT be paid

    def test_delete_multi_item_invoice(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-del")
        to1 = _entity(test_app, token, "mi-to1-del")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [{"to_entity_id": to1, "amounts": [{"currency": "usd", "amount": "5.00"}]}],
        )
        invoice_id = r.json()["id"]

        del_r = test_app.delete(f"/invoices/{invoice_id}", headers={"x-token": token})
        assert del_r.status_code == 200

        get_r = test_app.get(f"/invoices/{invoice_id}", headers={"x-token": token})
        assert get_r.status_code != 200  # gone

    def test_update_multi_item_invoice_items(self, test_app: TestClient, token):
        payer = _entity(test_app, token, "mi-payer-upd")
        to1 = _entity(test_app, token, "mi-to1-upd")
        to2 = _entity(test_app, token, "mi-to2-upd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [{"to_entity_id": to1, "amounts": [{"currency": "usd", "amount": "5.00"}]}],
        )
        invoice_id = r.json()["id"]

        # Replace items with a new set
        upd_r = test_app.patch(
            f"/invoices/{invoice_id}",
            json={
                "items": [
                    {
                        "to_entity_id": to2,
                        "amounts": [{"currency": "usd", "amount": "8.00"}],
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert upd_r.status_code == 200, upd_r.text
        updated = upd_r.json()
        assert len(updated["items"]) == 1
        assert updated["items"][0]["to_entity_id"] == to2

    def test_prefilled_entity_alterable_within_tag_constraint(
        self, test_app: TestClient, token
    ):
        """Pre-filled to_entity_id can be overridden at pay time to another entity with the required tag."""
        payer = _entity(test_app, token, "mi-payer-override")
        tag = _tag(test_app, token, "mi-override-tag")
        pre_entity = _entity(test_app, token, "mi-pre-entity")
        other_entity = _entity(test_app, token, "mi-other-entity")
        _add_tag(test_app, token, pre_entity, tag)
        _add_tag(test_app, token, other_entity, tag)
        _fund(test_app, token, payer, "50.00", "usd")

        r = _create_multi_invoice(
            test_app,
            token,
            payer,
            [
                {
                    "to_entity_id": pre_entity,
                    "to_tag_id": tag,
                    "amounts": [{"currency": "usd", "amount": "5.00"}],
                }
            ],
        )
        invoice = r.json()
        item_id = invoice["items"][0]["id"]

        # Pay using a different entity (other_entity also has the tag)
        pay_r = test_app.post(
            f"/invoices/{invoice['id']}/pay-items",
            json={
                "items": [
                    {
                        "item_id": item_id,
                        "to_entity_id": other_entity,
                        "currency": "usd",
                        "amount": "5.00",
                    }
                ]
            },
            headers={"x-token": token},
        )
        assert pay_r.status_code == 200, pay_r.text
        assert pay_r.json()["status"] == "paid"
