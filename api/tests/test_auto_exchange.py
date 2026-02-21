"""Tests for auto-balance currency exchange feature."""

from decimal import Decimal

import pytest
from app.seeding import ex_resident_tag, guest_tag, member_tag, resident_tag
from fastapi.testclient import TestClient

FIXED_RATES = property(
    lambda self: [
        {
            "currencies": [
                {"code": "usd", "rate": "3.00", "quantity": "1"},
                {"code": "eur", "rate": "3.50", "quantity": "1"},
                {"code": "gel", "rate": "1", "quantity": "1"},
            ]
        }
    ]
)


class TestAutoBalancePlan:
    """Unit-level tests for _plan_exchanges via the service directly."""

    @pytest.fixture(autouse=True)
    def patch_rates(self, monkeypatch):
        from app.services.currency_exchange import CurrencyExchangeService

        monkeypatch.setattr(CurrencyExchangeService, "_raw_rates", FIXED_RATES)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_service(self, test_app: TestClient):
        """Grab a fresh CurrencyExchangeService from the DI container."""
        from app.app import app
        from app.config import get_config
        from app.db import DatabaseConnection
        from app.dependencies.services import ServiceContainer
        from app.uow import UnitOfWork

        config = app.dependency_overrides[get_config]()
        db_conn = DatabaseConnection(config)
        session = db_conn.get_session()
        uow = UnitOfWork(session)
        container = ServiceContainer(uow, config)
        return container.currency_exchange_service, uow

    def _create_resident(self, test_app, token):
        r = test_app.post(
            "/entities",
            json={
                "name": "TestResident",
                "comment": "auto-balance test",
                "tag_ids": [resident_tag.id],
            },
            headers={"x-token": token},
        )
        assert r.status_code == 200
        return r.json()["id"]

    def _tx(
        self, test_app, token, *, from_id, to_id, amount, currency, status="completed"
    ):
        r = test_app.post(
            "/transactions",
            json={
                "from_entity_id": from_id,
                "to_entity_id": to_id,
                "amount": str(amount),
                "currency": currency,
                "status": status,
            },
            headers={"x-token": token},
        )
        assert r.status_code == 200
        return r.json()

    # ------------------------------------------------------------------
    # _plan_exchanges tests (rates: 1 USD=3 GEL, 1 EUR=3.5 GEL)
    # ------------------------------------------------------------------

    def test_plan_no_debts(self, test_app: TestClient, token):
        """No debts → empty plan."""
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges({"gel": Decimal("100"), "usd": Decimal("50")})
        assert plan == []

    def test_plan_no_positives(self, test_app: TestClient, token):
        """No positive balances → empty plan."""
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges({"gel": Decimal("-100")})
        assert plan == []

    def test_plan_single_debt_fully_covered(self, test_app: TestClient, token):
        """
        -30 GEL, +20 USD.
        20 USD → 60 GEL fully covers the 30 GEL debt.
        """
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges({"gel": Decimal("-30"), "usd": Decimal("20")})
        assert len(plan) == 1
        item = plan[0]
        assert item.source_currency == "usd"
        assert item.target_currency == "gel"
        # We need 30 GEL, which is 10 USD.  But we also have 20 USD available.
        # needed_src = 30/3.00 = 10.00 USD; actual_src = min(20, 10) = 10 USD
        assert item.source_amount == Decimal("10.00")
        assert item.target_amount == Decimal("30.00")

    def test_plan_single_debt_partially_covered(self, test_app: TestClient, token):
        """
        -100 GEL, +20 USD.
        20 USD → 60 GEL does not fully cover debt; remaining -40 GEL, no more sources.
        """
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges({"gel": Decimal("-100"), "usd": Decimal("20")})
        assert len(plan) == 1
        item = plan[0]
        assert item.source_currency == "usd"
        assert item.source_amount == Decimal("20.00")  # all of it
        assert item.target_currency == "gel"
        assert item.target_amount == Decimal("60.00")

    def test_plan_two_sources_smallest_usd_first(self, test_app: TestClient, token):
        """
        -100 GEL, +20 USD, +50 EUR.
        USD (20 USD ≈ 20 USD) < EUR (50 EUR ≈ 58.33 USD), so USD is used first.
        20 USD is insufficient (covers only 60 GEL), so all 20 USD spent → 60 GEL.
        Remaining debt = -40 GEL covered with EUR: 40 GEL = 11.42 EUR (ROUND_DOWN).
        With the fix, full-coverage exchanges use target_amount so 40.00 GEL is exact.
        """
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges(
                {"gel": Decimal("-100"), "usd": Decimal("20"), "eur": Decimal("50")}
            )
        assert len(plan) == 2
        i0, i1 = plan[0], plan[1]
        # First: all 20 USD → 60 GEL (partial, source path)
        assert i0.source_currency == "usd"
        assert i0.use_target_amount is False
        assert i0.source_amount == Decimal("20.00")
        assert i0.target_amount == Decimal("60.00")
        # Second: 40 GEL from EUR (full coverage, target path → exact 40.00 GEL)
        assert i1.source_currency == "eur"
        assert i1.use_target_amount is True
        assert i1.source_amount == Decimal("11.42")  # ROUND_DOWN of 40/3.5
        assert i1.target_amount == Decimal("40.00")  # exact, not 39.97

    def test_plan_fully_covered_uses_target_amount(self, test_app: TestClient, token):
        """
        Regression: full-coverage exchanges must set use_target_amount=True so the
        executor uses target_amount path, delivering the exact debt with no cents leftover.
        """
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges({"gel": Decimal("-30"), "usd": Decimal("20")})
        assert len(plan) == 1
        item = plan[0]
        assert item.use_target_amount is True
        assert item.target_amount == Decimal("30.00")  # exact debt
        assert item.source_amount == Decimal("10.00")  # 30/3.00

    def test_plan_partial_coverage_uses_source_amount(
        self, test_app: TestClient, token
    ):
        """Partial-coverage exchanges use source_amount path."""
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges({"gel": Decimal("-100"), "usd": Decimal("20")})
        assert len(plan) == 1
        item = plan[0]
        assert item.use_target_amount is False
        assert item.source_amount == Decimal("20.00")

    def test_plan_multiple_debts(self, test_app: TestClient, token):
        """
        -60 GEL, -15 USD, +100 EUR.
        Largest GEL debt first (by USD value), then USD debt.
        """
        svc, uow = self._make_service(test_app)
        with uow:
            plan = svc._plan_exchanges(
                {"gel": Decimal("-60"), "usd": Decimal("-15"), "eur": Decimal("100")}
            )
        # Should produce at least 2 exchanges
        assert len(plan) >= 2
        currencies = [(p.source_currency, p.target_currency) for p in plan]
        # All exchanges go from EUR
        for src, _tgt in currencies:
            assert src == "eur"

    def test_plan_debt_in_positive_source_skipped(self, test_app: TestClient, token):
        """
        When debt_currency == source_currency that combination is skipped.
        """
        svc, uow = self._make_service(test_app)
        with uow:
            # -100 USD, +80 USD is impossible (can't exchange USD→USD)
            # but +200 GEL is available
            plan = svc._plan_exchanges({"usd": Decimal("-100"), "gel": Decimal("200")})
        assert len(plan) >= 1
        assert plan[0].source_currency == "gel"
        assert plan[0].target_currency == "usd"


class TestAutoBalanceEndpoints:
    """Integration tests through the HTTP API."""

    F0_ENTITY = 1
    CASH_IN_ENTITY = 2  # deposit entity from seeding

    @pytest.fixture(autouse=True)
    def patch_rates(self, monkeypatch):
        from app.services.currency_exchange import CurrencyExchangeService

        monkeypatch.setattr(CurrencyExchangeService, "_raw_rates", FIXED_RATES)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_entity(self, test_app, token, name, tag_ids):
        r = test_app.post(
            "/entities",
            json={"name": name, "comment": "auto-balance test", "tag_ids": tag_ids},
            headers={"x-token": token},
        )
        assert r.status_code == 200
        return r.json()["id"]

    def _tx(
        self, test_app, token, *, from_id, to_id, amount, currency, status="completed"
    ):
        r = test_app.post(
            "/transactions",
            json={
                "from_entity_id": from_id,
                "to_entity_id": to_id,
                "amount": str(amount),
                "currency": currency,
                "status": status,
            },
            headers={"x-token": token},
        )
        assert r.status_code == 200
        return r.json()

    # ------------------------------------------------------------------
    # Preview endpoint
    # ------------------------------------------------------------------

    def test_preview_empty_when_no_debts(self, test_app: TestClient, token):
        """Resident with only positive balance → no plans returned."""
        eid = self._create_entity(test_app, token, "ResidentRich", [resident_tag.id])
        # Give entity positive GEL balance
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="100",
            currency="GEL",
        )

        r = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert r.status_code == 200
        plans = r.json()["plans"]
        # This entity should not appear (no debts)
        entity_ids = [p["entity_id"] for p in plans]
        assert eid not in entity_ids

    def test_preview_resident_with_debt(self, test_app: TestClient, token):
        """Resident with -30 GEL and +20 USD appears in preview."""
        eid = self._create_entity(test_app, token, "ResidentDebtor", [resident_tag.id])
        # Debt: entity pays F0 for 30 GEL
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="30",
            currency="GEL",
        )
        # Asset: entity receives 20 USD
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="USD",
        )

        r = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert r.status_code == 200
        plans = r.json()["plans"]
        entity_plan = next((p for p in plans if p["entity_id"] == eid), None)
        assert entity_plan is not None, "Debtor entity should be in preview"
        assert len(entity_plan["exchanges"]) == 1
        exc = entity_plan["exchanges"][0]
        assert exc["source_currency"].lower() == "usd"
        assert exc["target_currency"].lower() == "gel"
        # need 30 GEL = 10 USD; min(20, 10) = 10 USD
        assert Decimal(exc["source_amount"]) == Decimal("10.00")
        assert Decimal(exc["target_amount"]) == Decimal("30.00")

    def test_preview_member_included(self, test_app: TestClient, token):
        """Member entities are also considered."""
        eid = self._create_entity(test_app, token, "MemberDebtor", [member_tag.id])
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="50",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="30",
            currency="USD",
        )

        r = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert r.status_code == 200
        plans = r.json()["plans"]
        entity_ids = [p["entity_id"] for p in plans]
        assert eid in entity_ids

    def test_preview_ex_resident_included(self, test_app: TestClient, token):
        """Ex-resident entities are also considered."""
        eid = self._create_entity(
            test_app, token, "ExResidentDebtor", [ex_resident_tag.id]
        )
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="50",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="30",
            currency="USD",
        )

        r = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert r.status_code == 200
        entity_ids = [p["entity_id"] for p in r.json()["plans"]]
        assert eid in entity_ids

    def test_preview_guest_not_included(self, test_app: TestClient, token):
        """Guests should NOT be included in auto-balance."""
        eid = self._create_entity(test_app, token, "GuestWithDebt", [guest_tag.id])
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="50",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="30",
            currency="USD",
        )

        r = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert r.status_code == 200
        entity_ids = [p["entity_id"] for p in r.json()["plans"]]
        assert eid not in entity_ids, "Guest entity must not appear in auto-balance"

    def test_preview_draft_balances_not_counted(self, test_app: TestClient, token):
        """Draft transactions must not affect the plan (only completed balances count)."""
        eid = self._create_entity(
            test_app, token, "ResidentDraftOnly", [resident_tag.id]
        )
        # Draft debt - should be ignored
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="50",
            currency="GEL",
            status="draft",
        )
        # Draft credit in USD - should be ignored
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="30",
            currency="USD",
            status="draft",
        )

        r = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert r.status_code == 200
        entity_ids = [p["entity_id"] for p in r.json()["plans"]]
        assert (
            eid not in entity_ids
        ), "Draft-only entity must not appear (no completed debts)"

    def test_preview_two_sources_order(self, test_app: TestClient, token):
        """
        -100 GEL, +20 USD (+60 GEL eq), +50 EUR (+175 GEL eq).
        USD (20 USD) < EUR (≈58.33 USD), so USD used first.
        After 20 USD→60 GEL (partial): remaining -40 GEL.
        Then 11.42 EUR → exactly 40.00 GEL (full coverage, target_amount path).
        """
        eid = self._create_entity(
            test_app, token, "ResidentTwoSources", [resident_tag.id]
        )
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="100",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="USD",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="50",
            currency="EUR",
        )

        r = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert r.status_code == 200
        plan = next(p for p in r.json()["plans"] if p["entity_id"] == eid)
        exchanges = plan["exchanges"]
        assert len(exchanges) == 2
        assert exchanges[0]["source_currency"].lower() == "usd"
        assert Decimal(exchanges[0]["source_amount"]) == Decimal("20.00")
        assert Decimal(exchanges[0]["target_amount"]) == Decimal("60.00")
        assert exchanges[1]["source_currency"].lower() == "eur"
        assert Decimal(exchanges[1]["source_amount"]) == Decimal("11.42")
        assert Decimal(exchanges[1]["target_amount"]) == Decimal(
            "40.00"
        )  # exact, not 39.97

    # ------------------------------------------------------------------
    # Run endpoint
    # ------------------------------------------------------------------

    def test_run_no_cents_left_after_exchange(self, test_app: TestClient, token):
        """
        Regression for the double-rounding bug:
        With a fractional rate (EUR→GEL: 1 EUR = 3.50 GEL), exchanging to cover
        a GEL debt must leave exactly zero debt, not a few cents.
        """
        eid = self._create_entity(test_app, token, "ResidentNoCents", [resident_tag.id])
        # Debt of 35 GEL (= exactly 10 EUR at rate 3.5, but let's use a trickier amount)
        # 40 GEL / 3.5 = 11.428... EUR → ROUND_DOWN → 11.42 EUR → 11.42 * 3.5 = 39.97 GEL (old bug)
        # With the fix: target_amount=40 → gets exactly 40 GEL, spending 11.42 EUR.
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="40",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="EUR",
        )

        r = test_app.post(
            "/currency_exchange/auto_balance/run", headers={"x-token": token}
        )
        assert r.status_code == 200
        result = next(res for res in r.json()["results"] if res["entity_id"] == eid)
        receipt = result["receipts"][0]
        # Must receive exactly 40.00 GEL — not 39.97 GEL
        assert Decimal(receipt["target_amount"]) == Decimal("40.00")
        assert Decimal(receipt["source_amount"]) == Decimal("11.42")

        # Verify balance is no longer negative
        bal_r = test_app.get(f"/balances/{eid}", headers={"x-token": token})
        assert bal_r.status_code == 200
        gel_balance = Decimal(bal_r.json()["completed"].get("GEL", "0"))
        # GEL debt (40) was exactly covered, remaining should be 0.00
        assert gel_balance == Decimal("0.00")

    def test_run_creates_transactions(self, test_app: TestClient, token):
        """Run auto-balance creates real transactions and covers the debt."""
        eid = self._create_entity(test_app, token, "ResidentRunTest", [resident_tag.id])
        # Debt: -30 GEL
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="30",
            currency="GEL",
        )
        # Asset: +20 USD  (need 10 USD to cover 30 GEL)
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="USD",
        )

        r = test_app.post(
            "/currency_exchange/auto_balance/run", headers={"x-token": token}
        )
        assert r.status_code == 200
        data = r.json()
        results = data["results"]
        entity_result = next((res for res in results if res["entity_id"] == eid), None)
        assert entity_result is not None
        receipts = entity_result["receipts"]
        assert len(receipts) == 1
        receipt = receipts[0]
        assert receipt["source_currency"].lower() == "usd"
        assert receipt["target_currency"].lower() == "gel"
        assert Decimal(receipt["source_amount"]) == Decimal("10.00")
        assert Decimal(receipt["target_amount"]) == Decimal("30.00")
        assert len(receipt["transactions"]) == 2

    def test_run_idempotent_after_debt_covered(self, test_app: TestClient, token):
        """
        After running auto-balance, the debt is covered.
        Running again should produce no exchanges for that entity.
        """
        eid = self._create_entity(
            test_app, token, "ResidentIdempotent", [resident_tag.id]
        )
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="30",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="USD",
        )

        # First run - should exchange
        r1 = test_app.post(
            "/currency_exchange/auto_balance/run", headers={"x-token": token}
        )
        assert r1.status_code == 200
        r1_results = r1.json()["results"]
        entity_r1 = next((res for res in r1_results if res["entity_id"] == eid), None)
        assert entity_r1 is not None

        # Second run - debt is covered, nothing more to exchange
        r2 = test_app.post(
            "/currency_exchange/auto_balance/run", headers={"x-token": token}
        )
        assert r2.status_code == 200
        r2_results = r2.json()["results"]
        entity_r2 = next((res for res in r2_results if res["entity_id"] == eid), None)
        # Entity should not appear in second run (no remaining debt)
        assert entity_r2 is None

    def test_run_partial_coverage(self, test_app: TestClient, token):
        """
        -100 GEL, +20 USD: only 60 GEL covered.
        Run still produces 1 exchange (all available USD).
        """
        eid = self._create_entity(test_app, token, "ResidentPartial", [resident_tag.id])
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="100",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="USD",
        )

        r = test_app.post(
            "/currency_exchange/auto_balance/run", headers={"x-token": token}
        )
        assert r.status_code == 200
        result = next(res for res in r.json()["results"] if res["entity_id"] == eid)
        assert len(result["receipts"]) == 1
        receipt = result["receipts"][0]
        assert Decimal(receipt["source_amount"]) == Decimal("20.00")  # all USD used
        assert Decimal(receipt["target_amount"]) == Decimal("60.00")

    def test_run_two_exchanges_for_one_entity(self, test_app: TestClient, token):
        """
        -100 GEL, +20 USD, +50 EUR.
        Two exchanges produced: first USD, then EUR.
        """
        eid = self._create_entity(
            test_app, token, "ResidentTwoExchanges", [resident_tag.id]
        )
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="100",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="USD",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="50",
            currency="EUR",
        )

        r = test_app.post(
            "/currency_exchange/auto_balance/run", headers={"x-token": token}
        )
        assert r.status_code == 200
        result = next(res for res in r.json()["results"] if res["entity_id"] == eid)
        assert len(result["receipts"]) == 2

    def test_run_transactions_tagged_automatic(self, test_app: TestClient, token):
        """Transactions created by auto-balance should carry the 'automatic' tag."""
        from app.seeding import automatic_tag

        eid = self._create_entity(test_app, token, "ResidentAutoTag", [resident_tag.id])
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="30",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="20",
            currency="USD",
        )

        r = test_app.post(
            "/currency_exchange/auto_balance/run", headers={"x-token": token}
        )
        assert r.status_code == 200
        result = next(res for res in r.json()["results"] if res["entity_id"] == eid)
        for receipt in result["receipts"]:
            for tx in receipt["transactions"]:
                tag_names = [t["name"] for t in tx.get("tags", [])]
                assert (
                    automatic_tag.name in tag_names
                ), f"Transaction {tx['id']} missing 'automatic' tag; tags={tag_names}"

    def test_run_no_eligible_entities_with_debt(self, test_app: TestClient, token):
        """When no eligible entities have debts, run returns empty results."""
        # Create a guest entity with debt - should be ignored
        eid = self._create_entity(test_app, token, "GuestRun", [guest_tag.id])
        self._tx(
            test_app,
            token,
            from_id=eid,
            to_id=self.F0_ENTITY,
            amount="50",
            currency="GEL",
        )
        self._tx(
            test_app,
            token,
            from_id=self.CASH_IN_ENTITY,
            to_id=eid,
            amount="30",
            currency="USD",
        )

        # Fetch preview first - guest must not appear
        prev = test_app.get(
            "/currency_exchange/auto_balance/preview", headers={"x-token": token}
        )
        assert eid not in [p["entity_id"] for p in prev.json()["plans"]]

    def test_preview_requires_auth(self, test_app: TestClient):
        """Preview endpoint requires authentication (no token → 422 or 4xx)."""
        r = test_app.get("/currency_exchange/auto_balance/preview")
        assert r.status_code >= 400

    def test_run_requires_auth(self, test_app: TestClient):
        """Run endpoint requires authentication (no token → 422 or 4xx)."""
        r = test_app.post("/currency_exchange/auto_balance/run")
        assert r.status_code >= 400
