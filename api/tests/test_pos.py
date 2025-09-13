from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="class")
def card_entity(test_app: TestClient, token):
    r = test_app.post(
        "/entities",
        json={
            "name": "Card User",
            "auth": {"card_hash": "hash_123"},
        },
        headers={"x-token": token},
    )
    assert r.status_code == 200, r.text
    return r.json()["id"], "hash_123"


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
    test_app: TestClient, card_entity, merchant_entity
):
    payer_id, card_hash = card_entity

    # First charge 25.00
    r1 = test_app.post(
        "/pos/charge/by-card",
        json={
            "card_hash": card_hash,
            "amount": "25.00",
            "currency": "usd",
            "to_entity_id": merchant_entity,
            "comment": "coffee",
        },
    )
    assert r1.status_code == 200, r1.text
    data1 = r1.json()
    assert data1["entity"]["id"] == payer_id
    assert data1["balance"]["completed"]["usd"] == "-25.00"

    # Second charge 10.00 (cumulative should be -35.00)
    r2 = test_app.post(
        "/pos/charge/by-card",
        json={
            "card_hash": card_hash,
            "amount": "10.00",
            "currency": "usd",
            "to_entity_id": merchant_entity,
        },
    )
    assert r2.status_code == 200, r2.text
    data2 = r2.json()
    assert data2["balance"]["completed"]["usd"] == "-35.00"
