from datetime import date
from decimal import Decimal

import pytest
from app.app import app
from app.config import get_config
from app.db import DatabaseConnection
from app.dependencies.services import ServiceContainer
from app.uow import UnitOfWork
from fastapi.testclient import TestClient


@pytest.fixture(scope="class")
def invoice_entity_from(test_app: TestClient, token):
    response = test_app.post(
        "/entities", json={"name": "Invoice From"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def invoice_entity_to(test_app: TestClient, token):
    response = test_app.post(
        "/entities", json={"name": "Invoice To"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def invoice_tag(test_app: TestClient, token):
    response = test_app.post(
        "/tags", json={"name": "invoice-test"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def invoice_tag_two(test_app: TestClient, token):
    response = test_app.post(
        "/tags", json={"name": "invoice-test-two"}, headers={"x-token": token}
    )
    assert response.status_code == 200
    return response.json()["id"]


def _create_invoice(test_app: TestClient, token, from_id, to_id, tag_ids=None):
    payload = {
        "from_entity_id": from_id,
        "to_entity_id": to_id,
        "amounts": [
            {"currency": "usd", "amount": "10.00"},
            {"currency": "gel", "amount": "27.00"},
        ],
    }
    if tag_ids is not None:
        payload["tag_ids"] = tag_ids
    response = test_app.post("/invoices", json=payload, headers={"x-token": token})
    assert response.status_code == 200
    return response


def _create_invoice_with_amounts(test_app: TestClient, token, from_id, to_id, amounts):
    payload = {
        "from_entity_id": from_id,
        "to_entity_id": to_id,
        "amounts": amounts,
    }
    response = test_app.post("/invoices", json=payload, headers={"x-token": token})
    assert response.status_code == 200
    return response


def _run_auto_pay_job() -> int:
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


class TestInvoiceEndpoints:
    def test_invoice_auto_paid_on_create_with_balance(
        self, test_app: TestClient, token
    ):
        funding_entity = test_app.post(
            "/entities", json={"name": "Invoice Funding"}, headers={"x-token": token}
        ).json()["id"]
        payer_entity = test_app.post(
            "/entities",
            json={"name": "Invoice AutoPay Payer"},
            headers={"x-token": token},
        ).json()["id"]
        payee_entity = test_app.post(
            "/entities",
            json={"name": "Invoice AutoPay Payee"},
            headers={"x-token": token},
        ).json()["id"]

        credit_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": funding_entity,
                "to_entity_id": payer_entity,
                "amount": "11.00",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert credit_response.status_code == 200

        invoice_response = test_app.post(
            "/invoices",
            json={
                "from_entity_id": payer_entity,
                "to_entity_id": payee_entity,
                "amounts": [
                    {"currency": "usd", "amount": "10.00"},
                    {"currency": "gel", "amount": "27.00"},
                ],
            },
            headers={"x-token": token},
        )
        assert invoice_response.status_code == 200
        invoice = invoice_response.json()
        assert invoice["status"] == "paid"
        assert invoice["transaction_id"] is not None

        tx_response = test_app.get(
            f"/transactions/{invoice['transaction_id']}", headers={"x-token": token}
        )
        assert tx_response.status_code == 200
        tx = tx_response.json()
        assert tx["currency"] == "usd"
        assert Decimal(tx["amount"]) == Decimal("10.00")

    def test_create_invoice(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        response = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        )
        data = response.json()
        assert data["from_entity_id"] == invoice_entity_from
        assert data["to_entity_id"] == invoice_entity_to
        amounts = {
            item["currency"]: Decimal(item["amount"]) for item in data["amounts"]
        }
        assert amounts["usd"] == Decimal("10.00")
        assert amounts["gel"] == Decimal("27.00")
        assert data["status"] == "pending"

    def test_create_invoice_with_tags(
        self,
        test_app: TestClient,
        token,
        invoice_entity_from,
        invoice_entity_to,
        invoice_tag,
    ):
        response = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to, [invoice_tag]
        )
        data = response.json()
        assert len(data["tags"]) == 1
        assert data["tags"][0]["id"] == invoice_tag

    def test_invoice_paid_on_completed_transaction(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200
        invoice_response = test_app.get(
            f"/invoices/{invoice['id']}", headers={"x-token": token}
        )
        assert invoice_response.status_code == 200
        assert invoice_response.json()["status"] == "paid"

    def test_invoice_paid_on_transaction_confirmation(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "27.00",
                "currency": "gel",
                "status": "draft",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200
        tx_id = tx_response.json()["id"]
        confirm_response = test_app.patch(
            f"/transactions/{tx_id}",
            json={"status": "completed"},
            headers={"x-token": token},
        )
        assert confirm_response.status_code == 200
        invoice_response = test_app.get(
            f"/invoices/{invoice['id']}", headers={"x-token": token}
        )
        assert invoice_response.status_code == 200
        assert invoice_response.json()["status"] == "paid"

    def test_invoice_rejects_wrong_currency(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "eur",
                "status": "completed",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 418

    def test_invoice_rejects_insufficient_amount(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "9.99",
                "currency": "usd",
                "status": "completed",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 418

    def test_invoice_rejects_second_transaction(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        first_tx = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert first_tx.status_code == 200
        second_tx = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert second_tx.status_code == 418

    def test_invoice_not_editable_after_paid(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200
        update_response = test_app.patch(
            f"/invoices/{invoice['id']}",
            json={"comment": "updated"},
            headers={"x-token": token},
        )
        assert update_response.status_code == 418

    def test_invoice_pending_edit_and_delete(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        update_response = test_app.patch(
            f"/invoices/{invoice['id']}",
            json={"comment": "pending edit"},
            headers={"x-token": token},
        )
        assert update_response.status_code == 200
        assert update_response.json()["comment"] == "pending edit"
        delete_response = test_app.delete(
            f"/invoices/{invoice['id']}", headers={"x-token": token}
        )
        assert delete_response.status_code == 200
        assert delete_response.json() == invoice["id"]

    def test_invoice_not_paid_when_transaction_draft(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "usd",
                "status": "draft",
                "invoice_id": invoice["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200
        invoice_response = test_app.get(
            f"/invoices/{invoice['id']}", headers={"x-token": token}
        )
        assert invoice_response.status_code == 200
        assert invoice_response.json()["status"] == "pending"

    def test_invoice_filtering_by_tags_status_entity(
        self,
        test_app: TestClient,
        token,
        invoice_entity_from,
        invoice_entity_to,
        invoice_tag,
        invoice_tag_two,
    ):
        pending_invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to, [invoice_tag]
        ).json()
        paid_invoice = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to, [invoice_tag_two]
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
                "invoice_id": paid_invoice["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200

        status_response = test_app.get(
            "/invoices",
            params={"status": "paid"},
            headers={"x-token": token},
        )
        assert status_response.status_code == 200
        status_items = status_response.json()["items"]
        assert any(item["id"] == paid_invoice["id"] for item in status_items)

        tag_response = test_app.get(
            "/invoices",
            params={"tags_ids": [invoice_tag]},
            headers={"x-token": token},
        )
        assert tag_response.status_code == 200
        tag_items = tag_response.json()["items"]
        assert any(item["id"] == pending_invoice["id"] for item in tag_items)

        entity_response = test_app.get(
            "/invoices",
            params={"entity_id": invoice_entity_from},
            headers={"x-token": token},
        )
        assert entity_response.status_code == 200
        entity_items = entity_response.json()["items"]
        assert any(item["id"] == pending_invoice["id"] for item in entity_items)


class TestInvoiceAutoPayTask:
    def test_auto_pay_oldest_invoices_max_per_entity(self, test_app: TestClient, token):
        funding_entity = test_app.post(
            "/entities", json={"name": "AutoPay Funding"}, headers={"x-token": token}
        ).json()["id"]
        payer_entity = test_app.post(
            "/entities", json={"name": "AutoPay Payer"}, headers={"x-token": token}
        ).json()["id"]
        payee_entity = test_app.post(
            "/entities", json={"name": "AutoPay Payee"}, headers={"x-token": token}
        ).json()["id"]

        invoice_one = _create_invoice_with_amounts(
            test_app,
            token,
            payer_entity,
            payee_entity,
            [{"currency": "usd", "amount": "10.00"}],
        ).json()
        invoice_two = _create_invoice_with_amounts(
            test_app,
            token,
            payer_entity,
            payee_entity,
            [{"currency": "usd", "amount": "15.00"}],
        ).json()
        invoice_three = _create_invoice_with_amounts(
            test_app,
            token,
            payer_entity,
            payee_entity,
            [{"currency": "usd", "amount": "20.00"}],
        ).json()

        credit_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": funding_entity,
                "to_entity_id": payer_entity,
                "amount": "25.00",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert credit_response.status_code == 200

        paid_count = _run_auto_pay_job()
        assert paid_count == 2

        invoice_one_response = test_app.get(
            f"/invoices/{invoice_one['id']}", headers={"x-token": token}
        )
        invoice_two_response = test_app.get(
            f"/invoices/{invoice_two['id']}", headers={"x-token": token}
        )
        invoice_three_response = test_app.get(
            f"/invoices/{invoice_three['id']}", headers={"x-token": token}
        )
        assert invoice_one_response.json()["status"] == "paid"
        assert invoice_two_response.json()["status"] == "paid"
        assert invoice_three_response.json()["status"] == "pending"

        invoice_one_tx = test_app.get(
            f"/transactions/{invoice_one_response.json()['transaction_id']}",
            headers={"x-token": token},
        ).json()
        invoice_two_tx = test_app.get(
            f"/transactions/{invoice_two_response.json()['transaction_id']}",
            headers={"x-token": token},
        ).json()
        assert Decimal(invoice_one_tx["amount"]) == Decimal("10.00")
        assert Decimal(invoice_two_tx["amount"]) == Decimal("15.00")

    def test_auto_pay_scoped_to_each_entity(self, test_app: TestClient, token):
        funding_entity = test_app.post(
            "/entities", json={"name": "AutoPay Funding 2"}, headers={"x-token": token}
        ).json()["id"]
        payer_one = test_app.post(
            "/entities", json={"name": "AutoPay Payer 2"}, headers={"x-token": token}
        ).json()["id"]
        payer_two = test_app.post(
            "/entities", json={"name": "AutoPay Payer 3"}, headers={"x-token": token}
        ).json()["id"]
        payee_entity = test_app.post(
            "/entities", json={"name": "AutoPay Payee 2"}, headers={"x-token": token}
        ).json()["id"]

        invoice_one = _create_invoice_with_amounts(
            test_app,
            token,
            payer_one,
            payee_entity,
            [{"currency": "usd", "amount": "10.00"}],
        ).json()
        invoice_two = _create_invoice_with_amounts(
            test_app,
            token,
            payer_two,
            payee_entity,
            [{"currency": "usd", "amount": "10.00"}],
        ).json()

        credit_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": funding_entity,
                "to_entity_id": payer_one,
                "amount": "10.00",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert credit_response.status_code == 200

        paid_count = _run_auto_pay_job()
        assert paid_count == 1

        invoice_one_response = test_app.get(
            f"/invoices/{invoice_one['id']}", headers={"x-token": token}
        )
        invoice_two_response = test_app.get(
            f"/invoices/{invoice_two['id']}", headers={"x-token": token}
        )
        assert invoice_one_response.json()["status"] == "paid"
        assert invoice_two_response.json()["status"] == "pending"

    def test_invoice_transaction_reassignment_disallowed(
        self, test_app: TestClient, token, invoice_entity_from, invoice_entity_to
    ):
        invoice_one = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        invoice_two = _create_invoice(
            test_app, token, invoice_entity_from, invoice_entity_to
        ).json()
        tx_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": invoice_entity_from,
                "to_entity_id": invoice_entity_to,
                "amount": "10.00",
                "currency": "usd",
                "status": "draft",
                "invoice_id": invoice_one["id"],
            },
            headers={"x-token": token},
        )
        assert tx_response.status_code == 200
        tx_id = tx_response.json()["id"]

        reassign_response = test_app.patch(
            f"/transactions/{tx_id}",
            json={"invoice_id": invoice_two["id"]},
            headers={"x-token": token},
        )
        assert reassign_response.status_code == 418

        clear_response = test_app.patch(
            f"/transactions/{tx_id}",
            json={"invoice_id": None},
            headers={"x-token": token},
        )
        assert clear_response.status_code == 418

    def test_issue_fee_invoices_auto_pay(self, test_app: TestClient, token):
        from app.seeding import fee_tag, resident_tag

        funding_entity = test_app.post(
            "/entities", json={"name": "Fee Funding"}, headers={"x-token": token}
        ).json()["id"]
        resident_entity = test_app.post(
            "/entities",
            json={"name": "Fee Resident", "tag_ids": [resident_tag.id]},
            headers={"x-token": token},
        ).json()["id"]

        credit_response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": funding_entity,
                "to_entity_id": resident_entity,
                "amount": "50.00",
                "currency": "usd",
                "status": "completed",
            },
            headers={"x-token": token},
        )
        assert credit_response.status_code == 200

        period = date.today().replace(day=1).isoformat()
        issue_response = test_app.post(
            "/fees/issue-invoices",
            json={"billing_period": period},
            headers={"x-token": token},
        )
        assert issue_response.status_code == 200

        invoices_response = test_app.get(
            "/invoices",
            params={"entity_id": resident_entity, "billing_period": period},
            headers={"x-token": token},
        )
        assert invoices_response.status_code == 200
        invoices = invoices_response.json()["items"]
        assert len(invoices) == 1

        invoice = invoices[0]
        assert invoice["status"] == "paid"
        assert invoice["transaction_id"] is not None
        assert any(tag["id"] == fee_tag.id for tag in invoice["tags"])
