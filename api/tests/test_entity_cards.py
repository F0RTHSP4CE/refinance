"""Tests for Entity Card management via dedicated endpoints"""

import pytest
from fastapi.testclient import TestClient


class TestEntityCards:
    @pytest.fixture(scope="class")
    def entity(self, test_app: TestClient, token):
        r = test_app.post(
            "/entities",
            json={"name": "CardOwner", "comment": "has cards"},
            headers={"x-token": token},
        )
        assert r.status_code == 200, r.text
        return r.json()

    def test_list_cards_initially_empty(self, test_app: TestClient, token, entity):
        r = test_app.get(f"/entities/{entity['id']}/cards", headers={"x-token": token})
        assert r.status_code == 200, r.text
        assert isinstance(r.json(), list)
        assert r.json() == []

    def test_add_card_and_list(self, test_app: TestClient, token, entity):
        # Add a new card
        r = test_app.post(
            f"/entities/{entity['id']}/cards",
            json={"comment": "primary", "card_hash": "uniq_hash_1"},
            headers={"x-token": token},
        )
        assert r.status_code == 200, r.text
        card = r.json()
        assert "id" in card
        assert card["comment"] == "primary"
        assert "created_at" in card and "modified_at" in card
        # Ensure hash is not exposed in read model
        assert "card_hash" not in card

        # List should now contain the new card
        r2 = test_app.get(f"/entities/{entity['id']}/cards", headers={"x-token": token})
        assert r2.status_code == 200, r2.text
        cards = r2.json()
        assert len(cards) == 1
        assert cards[0]["id"] == card["id"]

    def test_add_second_card(self, test_app: TestClient, token, entity):
        r = test_app.post(
            f"/entities/{entity['id']}/cards",
            json={"comment": "backup", "card_hash": "uniq_hash_2"},
            headers={"x-token": token},
        )
        assert r.status_code == 200, r.text
        # List should now show two cards
        r2 = test_app.get(f"/entities/{entity['id']}/cards", headers={"x-token": token})
        assert r2.status_code == 200, r2.text
        assert len(r2.json()) == 2

    def test_duplicate_card_hash_rejected(self, test_app: TestClient, token, entity):
        # Try to add a card with an existing hash
        r = test_app.post(
            f"/entities/{entity['id']}/cards",
            json={"comment": "dupe", "card_hash": "uniq_hash_1"},
            headers={"x-token": token},
        )
        # Unique constraint violation is handled by generic SQLAlchemy handler -> HTTP 418
        assert r.status_code == 418, r.text
        body = r.json()
        assert body["error_code"] == 1500
        assert "UNIQUE" in body["error"].upper() or body["error_code"] == 1500

    def test_remove_card(self, test_app: TestClient, token, entity):
        # Get cards list
        r_list = test_app.get(
            f"/entities/{entity['id']}/cards", headers={"x-token": token}
        )
        assert r_list.status_code == 200, r_list.text
        cards = r_list.json()
        assert len(cards) >= 1
        card_id = cards[0]["id"]

        # Remove first card
        r_del = test_app.delete(
            f"/entities/{entity['id']}/cards/{card_id}", headers={"x-token": token}
        )
        assert r_del.status_code == 200, r_del.text

        # Verify it no longer appears in list
        r_list2 = test_app.get(
            f"/entities/{entity['id']}/cards", headers={"x-token": token}
        )
        assert r_list2.status_code == 200, r_list2.text
        card_ids = [c["id"] for c in r_list2.json()]
        assert card_id not in card_ids

    def test_remove_nonexistent_card_404(self, test_app: TestClient, token, entity):
        # Removing a non-existent or not-owned card should return 418 (NotFoundError)
        r = test_app.delete(
            f"/entities/{entity['id']}/cards/999999", headers={"x-token": token}
        )
        assert r.status_code == 418, r.text
        body = r.json()
        assert body["error_code"] == 1404

    def test_token_retrieval_by_card_hash(self, test_app: TestClient, token, entity):
        # Ensure at least one card exists and retrieve its hash (we know uniq_hash_2 exists)
        # Try to get token by existing card hash
        r = test_app.post("/tokens/by-card-hash", json={"card_hash": "uniq_hash_2"})
        assert r.status_code == 200, r.text
        token_data = r.json()
        assert "token" in token_data

        # After removing that card, token retrieval should fail
        # First, find the card id by listing and matching comment
        r_list = test_app.get(
            f"/entities/{entity['id']}/cards", headers={"x-token": token}
        )
        assert r_list.status_code == 200
        cards = r_list.json()
        # pick card with comment 'backup' or fallback to first
        backup = next((c for c in cards if c.get("comment") == "backup"), cards[0])
        r_del = test_app.delete(
            f"/entities/{entity['id']}/cards/{backup['id']}",
            headers={"x-token": token},
        )
        assert r_del.status_code == 200

        r2 = test_app.post("/tokens/by-card-hash", json={"card_hash": "uniq_hash_2"})
        assert r2.status_code == 418, r2.text
