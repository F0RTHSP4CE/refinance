"""Tests for Entity"""

import pytest
from app.models.entity import Entity
from app.seeding import SEEDING
from fastapi import status
from fastapi.testclient import TestClient


class TestEntityEndpoints:
    """Test API endpoints for entities, accounting for a preloaded entity with id=1"""

    def test_create_entity(self, test_app: TestClient, token):
        # Create a new entity ("Resident One"); it should receive id 100 since
        # the predefined entity (id=1) is already in the DB and the autoincrement is bumped.
        response = test_app.post(
            "/entities",
            json={"name": "Resident One", "comment": "resident"},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 100
        assert data["name"] == "Resident One"
        assert data["comment"] == "resident"
        assert data["active"] is True

    def test_get_entity(self, test_app: TestClient, token):
        # Retrieve the newly created entity (id=100)
        response = test_app.get("/entities/100", headers={"x-token": token})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 100
        assert data["name"] == "Resident One"
        assert data["comment"] == "resident"
        assert data["active"] is True

    def test_patch_entity(self, test_app: TestClient, token):
        # Modify data for entity with id=100
        new_attrs = {
            "name": "Resident One Modified",
            "comment": "resident-one-modified",
            "active": False,
        }
        response_1 = test_app.patch(
            "/entities/100", json=new_attrs, headers={"x-token": token}
        )
        assert response_1.status_code == 200
        # Verify that the modified data is now returned
        response_2 = test_app.get("/entities/100", headers={"x-token": token})
        data = response_2.json()
        for k, new_value in new_attrs.items():
            assert data[k] == new_value

    def test_delete_entity_error(self, test_app: TestClient, token):
        # Attempting to delete the entity should return an error
        response = test_app.delete("/entities/100", headers={"x-token": token})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_get_non_existent_entity_error(self, test_app: TestClient, token):
        # Trying to retrieve a non-existent entity should return an error
        response = test_app.get("/entities/1111", headers={"x-token": token})
        assert response.status_code == 418
        data = response.json()
        assert data["error_code"] == 1404
        assert "not found" in data["error"].lower()


class TestEntityFilters:
    """Test filter logic for entities, accounting for the preloaded entity"""

    @pytest.fixture
    def entity_ordinary(self, test_app: TestClient, token):
        # Create an active entity; it will receive id=100 if this test runs in isolation
        test_app.post(
            "/entities",
            json=dict(name="Resident Ordinary", comment="resident"),
            headers={"x-token": token},
        )

    @pytest.fixture
    def entity_inactive(self, test_app: TestClient, token):
        # Create an entity and then mark it inactive; it will receive id=101 if run after the ordinary entity
        r = test_app.post(
            "/entities",
            json=dict(name="Resident Inactive", comment="resident"),
            headers={"x-token": token},
        )
        data = r.json()
        test_app.patch(
            f"/entities/{data['id']}",
            json=dict(active=False),
            headers={"x-token": token},
        )

    def test_entity_filters(
        self, test_app: TestClient, entity_ordinary, entity_inactive, token
    ):
        # The DB already contains 1 predefined entity (active) plus 2 created here.
        # Expecting:
        #   active=False: 1 (from entity_inactive)
        #   active=True: 1 (predefined) + 1 (entity_ordinary) = 2
        #   total: 1 (predefined) + 2 = 3
        response_inactive = test_app.get(
            "/entities", params=dict(active=False), headers={"x-token": token}
        ).json()
        response_active = test_app.get(
            "/entities", params=dict(active=True), headers={"x-token": token}
        ).json()
        response_total = test_app.get("/entities", headers={"x-token": token}).json()

        assert response_inactive["total"] == 1
        assert response_active["total"] == len(SEEDING[Entity]) + 1
        assert response_total["total"] == len(SEEDING[Entity]) + 2


class TestEntityBalanceSorting:
    def _create_entity(self, test_app: TestClient, token, name: str) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return response.json()["id"]

    def _create_transaction(
        self,
        test_app: TestClient,
        token: str,
        from_entity_id: int,
        to_entity_id: int,
        amount: str,
        currency: str = "usd",
        status: str = "completed",
    ) -> None:
        response = test_app.post(
            "/transactions",
            json={
                "from_entity_id": from_entity_id,
                "to_entity_id": to_entity_id,
                "amount": amount,
                "currency": currency,
                "status": status,
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200

    def test_entities_sorted_by_balance_desc_and_asc(
        self, test_app: TestClient, token_factory, token
    ):
        entity_a_id = self._create_entity(test_app, token, "BalanceSort A")
        entity_b_id = self._create_entity(test_app, token, "BalanceSort B")
        entity_c_id = self._create_entity(test_app, token, "BalanceSort C")

        token_a = token_factory(entity_a_id)
        token_b = token_factory(entity_b_id)
        token_c = token_factory(entity_c_id)

        self._create_transaction(
            test_app,
            token_a,
            from_entity_id=entity_a_id,
            to_entity_id=entity_b_id,
            amount="100.00",
        )
        self._create_transaction(
            test_app,
            token_b,
            from_entity_id=entity_b_id,
            to_entity_id=entity_c_id,
            amount="30.00",
        )
        self._create_transaction(
            test_app,
            token_c,
            from_entity_id=entity_c_id,
            to_entity_id=entity_a_id,
            amount="5.00",
        )

        response_desc = test_app.get(
            "/entities",
            params={
                "name": "BalanceSort",
                "balance_currency": "usd",
                "balance_status": "completed",
                "balance_order": "desc",
            },
            headers={"x-token": token},
        )
        assert response_desc.status_code == 200
        data_desc = response_desc.json()
        assert data_desc["total"] == 3
        ids_desc = [item["id"] for item in data_desc["items"]]
        assert ids_desc == [entity_b_id, entity_c_id, entity_a_id]

        response_asc = test_app.get(
            "/entities",
            params={
                "name": "BalanceSort",
                "balance_currency": "usd",
                "balance_status": "completed",
                "balance_order": "asc",
            },
            headers={"x-token": token},
        )
        assert response_asc.status_code == 200
        data_asc = response_asc.json()
        assert data_asc["total"] == 3
        ids_asc = [item["id"] for item in data_asc["items"]]
        assert ids_asc == [entity_a_id, entity_c_id, entity_b_id]

    def test_entities_sorted_by_balance_defaults_to_completed(
        self, test_app: TestClient, token_factory, token
    ):
        entity_a_id = self._create_entity(test_app, token, "BalanceSort D")
        entity_b_id = self._create_entity(test_app, token, "BalanceSort E")

        token_a = token_factory(entity_a_id)

        self._create_transaction(
            test_app,
            token_a,
            from_entity_id=entity_a_id,
            to_entity_id=entity_b_id,
            amount="42.00",
        )

        response = test_app.get(
            "/entities",
            params={
                "name": "BalanceSort D",
                "balance_currency": "usd",
                "balance_order": "asc",
            },
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == entity_a_id


class TestEntityTelegramIdFilter:
    """Tests for the auth_telegram_id filter, including BigInteger Telegram IDs
    and edge cases like empty-string telegram_id in auth JSON."""

    def _create_entity_with_telegram_id(
        self, test_app: TestClient, token: str, name: str, telegram_id: int | str | None
    ) -> int:
        response = test_app.post(
            "/entities",
            json={"name": name, "auth": {"telegram_id": telegram_id}},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        return response.json()["id"]

    def test_filter_by_telegram_id_returns_correct_entity(
        self, test_app: TestClient, token
    ):
        """Basic lookup: a single entity with a matching telegram_id is returned."""
        eid = self._create_entity_with_telegram_id(
            test_app, token, "TgFilter User", 123456789
        )

        response = test_app.get(
            "/entities",
            params={"auth_telegram_id": 123456789},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == eid

    def test_filter_by_telegram_id_no_match(self, test_app: TestClient, token):
        """Looking up a telegram_id that is not in the DB returns zero results."""
        response = test_app.get(
            "/entities",
            params={"auth_telegram_id": 999999999},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    def test_filter_by_large_telegram_id(self, test_app: TestClient, token):
        """Telegram IDs can exceed 32-bit INTEGER range (up to ~5.9B).
        The filter must not overflow and must find the entity correctly."""
        large_tid = 5_900_000_000  # > 2^31-1, would overflow a plain INTEGER
        eid = self._create_entity_with_telegram_id(
            test_app, token, "TgFilter LargeId", large_tid
        )

        response = test_app.get(
            "/entities",
            params={"auth_telegram_id": large_tid},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == eid

    def test_entity_with_empty_telegram_id_is_not_matched(
        self, test_app: TestClient, token
    ):
        """Entities with auth.telegram_id == "" must not match any numeric filter
        and must not cause a DB cast error."""
        self._create_entity_with_telegram_id(
            test_app, token, "TgFilter EmptyStr", ""
        )

        # Filtering by any numeric telegram_id must not return the empty-string entity
        response = test_app.get(
            "/entities",
            params={"auth_telegram_id": 1},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        # Only seeded system entities (id=1) could theoretically match — but their
        # auth.telegram_id is not "1", so total must be 0.
        for item in response.json()["items"]:
            assert (item.get("auth") or {}).get("telegram_id") != ""

    def test_entity_with_null_telegram_id_is_not_matched(
        self, test_app: TestClient, token
    ):
        """Entities with no auth or null telegram_id must not be returned."""
        test_app.post(
            "/entities",
            json={"name": "TgFilter NullAuth"},
            headers={"x-token": token},
        )

        response = test_app.get(
            "/entities",
            params={"auth_telegram_id": 42},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        for item in response.json()["items"]:
            assert (item.get("auth") or {}).get("telegram_id") == 42

    def test_filter_does_not_return_wrong_entity(self, test_app: TestClient, token):
        """Two entities with different telegram_ids — only the matching one is returned."""
        eid_a = self._create_entity_with_telegram_id(
            test_app, token, "TgFilter Alice", 111_000_111
        )
        _eid_b = self._create_entity_with_telegram_id(
            test_app, token, "TgFilter Bob", 222_000_222
        )

        response = test_app.get(
            "/entities",
            params={"auth_telegram_id": 111_000_111},
            headers={"x-token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == eid_a
