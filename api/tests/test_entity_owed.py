from decimal import Decimal

from app.services.entity_owed import calculate_entity_owed


def _stub_converter_factory(usd_per_unit: dict[str, Decimal]):
    def _convert(
        amount: Decimal, source_currency: str, target_currency: str
    ) -> Decimal:
        source = str(source_currency).lower()
        target = str(target_currency).lower()
        value = Decimal(str(amount))
        if source == target:
            return value
        usd_value = value * usd_per_unit[source]
        target_value = usd_value / usd_per_unit[target]
        return target_value

    return _convert


class TestEntityOwedCalculator:
    def test_cross_currency_credit_cancels_equivalent_debt(self):
        # USD +100 should cancel GEL -270 (= 100 USD) via conversion.
        convert = _stub_converter_factory(
            {
                "usd": Decimal("1"),
                "gel": Decimal("100") / Decimal("270"),
                "eur": Decimal("1.2"),
            }
        )

        summary = calculate_entity_owed(
            pending_invoice_totals={},
            completed_balances={"usd": Decimal("100"), "gel": Decimal("-270")},
            convert_amount=convert,
        )

        assert summary.net_owed_usd == Decimal("0.00")
        assert summary.minimum_topup_currency is None
        assert summary.minimum_topup_amount is None

    def test_includes_pending_and_negative_balance_in_owed(self):
        convert = _stub_converter_factory(
            {
                "usd": Decimal("1"),
                "gel": Decimal("0.37"),
                "eur": Decimal("1.2"),
            }
        )

        summary = calculate_entity_owed(
            pending_invoice_totals={"usd": Decimal("40")},
            completed_balances={"usd": Decimal("-10")},
            convert_amount=convert,
        )

        assert summary.owed_by_currency["usd"] == Decimal("50")
        assert summary.net_owed_usd == Decimal("50.00")
        assert summary.minimum_topup_currency == "usd"
        assert summary.minimum_topup_amount == Decimal("50.00")

    def test_recommends_smallest_nominal_topup_currency(self):
        convert = _stub_converter_factory(
            {
                "usd": Decimal("1"),
                "gel": Decimal("0.37"),
                "eur": Decimal("1.2"),
            }
        )

        summary = calculate_entity_owed(
            pending_invoice_totals={"usd": Decimal("300")},
            completed_balances={"usd": Decimal("20"), "eur": Decimal("20")},
            convert_amount=convert,
        )

        # Net owed in USD: 300 - 20 USD - 24 USD (20 EUR × 1.2) = 256
        assert summary.net_owed_usd == Decimal("256.00")
        # Candidates = debt currencies only = {usd}; EUR balance is not a charge target
        assert summary.minimum_topup_currency == "usd"
        assert summary.minimum_topup_amount == Decimal("256.00")

    def test_cross_currency_positive_balance_cancels_foreign_invoice(self):
        # USD +100 should cancel a GEL invoice worth 100 USD via conversion.
        convert = _stub_converter_factory(
            {
                "usd": Decimal("1"),
                "gel": Decimal("100") / Decimal("270"),
                "eur": Decimal("1.2"),
            }
        )

        summary = calculate_entity_owed(
            pending_invoice_totals={"gel": Decimal("270")},
            completed_balances={"usd": Decimal("100")},
            convert_amount=convert,
        )

        assert summary.total_owed_usd.quantize(Decimal("0.01")) == Decimal("100.00")
        assert summary.available_credit_usd == Decimal("100.00")
        assert summary.net_owed_usd == Decimal("0.00")
        assert summary.minimum_topup_currency is None
        assert summary.minimum_topup_amount is None

    def test_positive_gel_cancels_negative_eur_via_conversion(self):
        # 76 GEL ≈ 28 USD should cancel 7 EUR = 7 USD debt → no Stripe charge.
        convert = _stub_converter_factory(
            {
                "usd": Decimal("1"),
                "gel": Decimal("100") / Decimal("270"),
                "eur": Decimal("1"),
            }
        )

        summary = calculate_entity_owed(
            pending_invoice_totals={},
            completed_balances={
                "eur": Decimal("-7"),
                "usd": Decimal("0"),
                "gel": Decimal("76"),
            },
            convert_amount=convert,
        )

        assert summary.owed_by_currency == {"eur": Decimal("7")}
        assert summary.total_owed_usd == Decimal("7.00")
        assert summary.available_credit_usd > summary.total_owed_usd  # 76 GEL ≈ 28 USD
        assert summary.net_owed_usd == Decimal("0.00")
        assert summary.minimum_topup_currency is None
        assert summary.minimum_topup_amount is None

    def test_handles_empty_candidates_with_usd_fallback(self):
        convert = _stub_converter_factory(
            {
                "usd": Decimal("1"),
                "gel": Decimal("0.37"),
                "eur": Decimal("1.2"),
            }
        )

        summary = calculate_entity_owed(
            pending_invoice_totals={"usd": Decimal("12")},
            completed_balances={},
            convert_amount=convert,
            currency_candidates=[],
        )

        assert summary.minimum_topup_currency == "usd"
        assert summary.minimum_topup_amount == Decimal("12.00")
