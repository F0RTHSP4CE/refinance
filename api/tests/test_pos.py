import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="class")
def pos_headers():
    return {"x-pos-secret": "test-pos-secret"}


@pytest.fixture(scope="class")
def payer_entity(test_app: TestClient, token):
    r = test_app.post(
        "/entities",
        json={
            "name": "POS Payer",
        },
        headers={"x-token": token},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"], "POS Payer"


@pytest.fixture(scope="class")
def merchant_entity(test_app: TestClient, token):
    r = test_app.post(
        "/entities",
        json={
            "name": "Merchant",
        },
        headers={"x-token": token},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_pos_charges_accumulate_balance(
    test_app: TestClient, payer_entity, merchant_entity, pos_headers
):
    payer_id, payer_name = payer_entity

    # First charge 25.00
    r1 = test_app.post(
        "/pos/charge",
        json={
            "entity_name": payer_name,
            "amount": "25.00",
            "currency": "usd",
            "to_entity_id": merchant_entity,
            "comment": "coffee",
        },
        headers=pos_headers,
    )
    assert r1.status_code == 200, r1.text
    data1 = r1.json()
    assert data1["entity"]["id"] == payer_id
    assert data1["balance"]["completed"]["usd"] == "-25.00"

    # Second charge 10.00 (cumulative should be -35.00)
    r2 = test_app.post(
        "/pos/charge",
        json={
            "entity_name": payer_name,
            "amount": "10.00",
            "currency": "usd",
            "to_entity_id": merchant_entity,
        },
        headers=pos_headers,
    )
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert data2["balance"]["completed"]["usd"] == "-35.00"


def test_pos_charge_requires_pos_secret(
    test_app: TestClient, payer_entity, merchant_entity
):
    _, payer_name = payer_entity
    response = test_app.post(
        "/pos/charge",
        json={
            "entity_name": payer_name,
            "amount": "1.00",
            "currency": "usd",
            "to_entity_id": merchant_entity,
        },
    )
    assert response.status_code == 422
