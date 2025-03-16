from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

# Fixtures for entities (using the same mechanism as in transaction tests).


@pytest.fixture(scope="class")
def entity_one(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "User One"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def entity_two(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "User Two"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def participant_c(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "Participant C"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def participant_d(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "Participant D"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def participant_e(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "Participant E"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()["id"]


@pytest.fixture(scope="class")
def participant_f(test_app: TestClient, token):
    response = test_app.post(
        "/entities",
        json={"name": "Participant F"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()["id"]


# Fixtures to create splits.


@pytest.fixture(scope="class")
def split_100(test_app: TestClient, token, entity_two):
    """
    Create a split of 100.00 USD with recipient entity_two.
    """
    response = test_app.post(
        "/splits",
        json={"recipient_entity_id": entity_two, "amount": "100.00", "currency": "usd"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="class")
def split_200(test_app: TestClient, token, entity_two):
    """
    Create a split of 200.00 USD with recipient entity_two.
    """
    response = test_app.post(
        "/splits",
        json={"recipient_entity_id": entity_two, "amount": "200.00", "currency": "usd"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture(scope="class")
def split_small(test_app: TestClient, token, entity_two):
    """
    Create a split of 0.01 USD with recipient entity_two.
    """
    response = test_app.post(
        "/splits",
        json={"recipient_entity_id": entity_two, "amount": "0.01", "currency": "usd"},
        headers={"x-token": token},
    )
    assert response.status_code == 200
    return response.json()


class TestSplitEndpoints:
    def test_create_split(self, test_app: TestClient, token, entity_two):
        response = test_app.post(
            "/splits",
            json={
                "recipient_entity_id": entity_two,
                "amount": "50.00",
                "currency": "usd",
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["recipient_entity_id"] == entity_two
        assert Decimal(data["amount"]) == Decimal("50.00")
        assert data["currency"] == "usd"
        assert data["performed"] is False

    def test_read_split(self, test_app: TestClient, token, split_100):
        split_id = split_100["id"]
        response = test_app.get(f"/splits/{split_id}", headers={"x-token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == split_id

    def test_update_split(self, test_app: TestClient, token, split_100):
        # update to 75
        split_id = split_100["id"]
        response = test_app.patch(
            f"/splits/{split_id}",
            json={"amount": "75.00", "currency": "usd"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["amount"]) == Decimal("75.00")
        assert data["currency"] == "usd"
        # update back to 100
        split_id = split_100["id"]
        response = test_app.patch(
            f"/splits/{split_id}",
            json={"amount": "100.00", "currency": "usd"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert Decimal(data["amount"]) == Decimal("100.00")
        assert data["currency"] == "usd"

    def test_delete_split(self, test_app: TestClient, token, entity_two):
        # Create a new split to delete.
        create_resp = test_app.post(
            "/splits",
            json={
                "recipient_entity_id": entity_two,
                "amount": "30.00",
                "currency": "usd",
            },
            headers={"x-token": token},
        )
        assert create_resp.status_code == 200
        split_id = create_resp.json()["id"]
        delete_resp = test_app.delete(f"/splits/{split_id}", headers={"x-token": token})
        assert delete_resp.status_code == 200
        # Assuming the delete endpoint returns the deleted split's ID.
        assert delete_resp.json() == split_id

    def test_perform_split(
        self, test_app: TestClient, token, split_100, participant_c, participant_d
    ):
        """
        Test performing a split where 100.00 USD is divided among two participants.
        In this case, only Participant C and Participant D are added (actor is not automatically included).
        Each should receive 50.00.
        """
        split_id = split_100["id"]
        # Add two participants.
        resp1 = test_app.post(
            f"/splits/{split_id}/participants",
            params={"entity_id": participant_c},
            headers={"x-token": token},
        )
        resp2 = test_app.post(
            f"/splits/{split_id}/participants",
            params={"entity_id": participant_d},
            headers={"x-token": token},
        )
        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Perform the split.
        perform_resp = test_app.post(
            f"/splits/{split_id}/perform", headers={"x-token": token}
        )
        assert perform_resp.status_code == 200
        transactions = perform_resp.json()
        # Expect two transactions.
        assert len(transactions) == 2
        amounts = [Decimal(tx["amount"]) for tx in transactions]
        # Total must equal 100.00, and each transaction should be 50.00.
        assert sum(amounts) == Decimal("100.00")
        assert all(amount == Decimal("50.00") for amount in amounts)

    def test_perform_split_small_amount(
        self, test_app: TestClient, token, split_small, participant_e, participant_f
    ):
        """
        Test performing a split where 0.01 USD is divided among two participants.
        Here, Participant E and Participant F are added.
        The distribution should yield one transaction of 0.01 and one transaction of 0.00.
        """
        split_id = split_small["id"]
        resp_e = test_app.post(
            f"/splits/{split_id}/participants",
            params={"entity_id": participant_e},
            headers={"x-token": token},
        )
        resp_f = test_app.post(
            f"/splits/{split_id}/participants",
            params={"entity_id": participant_f},
            headers={"x-token": token},
        )
        assert resp_e.status_code == 200
        assert resp_f.status_code == 200

        perform_resp = test_app.post(
            f"/splits/{split_id}/perform", headers={"x-token": token}
        )
        assert perform_resp.status_code == 200
        transactions = perform_resp.json()
        # Expect two transactions.
        assert len(transactions) == 2
        amounts = [Decimal(tx["amount"]) for tx in transactions]
        assert sum(amounts) == Decimal("0.01")
        # Expect one transaction with 0.01 and one with 0.00.
        assert amounts.count(Decimal("0.01")) == 1
        assert amounts.count(Decimal("0.00")) == 1

    def test_perform_split_200(
        self,
        test_app: TestClient,
        token,
        entity_one,
        split_200,
        participant_c,
        participant_d,
    ):
        """
        Test performing a split where 200.00 USD is divided among three participants.
        Here, we explicitly add the actor (entity_one), Participant C, and Participant D.
        Calculation:
          - 200.00 / 3 = 66.6666...
          - Base share (rounded down) = 66.66, total = 199.98, remainder = 0.02,
          - Extra count = 2 => two participants get 66.66 + 0.01 (66.67) and one gets 66.66.
        Expected distribution: two transactions of 66.67 and one of 66.66.
        """
        split_id = split_200["id"]
        # Add the three participants.
        resp_actor = test_app.post(
            f"/splits/{split_id}/participants",
            params={"entity_id": entity_one},
            headers={"x-token": token},
        )
        resp_c = test_app.post(
            f"/splits/{split_id}/participants",
            params={"entity_id": participant_c},
            headers={"x-token": token},
        )
        resp_d = test_app.post(
            f"/splits/{split_id}/participants",
            params={"entity_id": participant_d},
            headers={"x-token": token},
        )
        assert resp_actor.status_code == 200
        assert resp_c.status_code == 200
        assert resp_d.status_code == 200

        perform_resp = test_app.post(
            f"/splits/{split_id}/perform", headers={"x-token": token}
        )
        assert perform_resp.status_code == 200
        transactions = perform_resp.json()
        # Expect three transactions.
        assert len(transactions) == 3
        amounts = [Decimal(tx["amount"]) for tx in transactions]
        # Ensure total equals 200.00.
        assert sum(amounts) == Decimal("200.00")
        # Check expected distribution: two transactions of 66.67 and one of 66.66.
        assert amounts.count(Decimal("66.67")) == 2
        assert amounts.count(Decimal("66.66")) == 1
