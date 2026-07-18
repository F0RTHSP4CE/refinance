from decimal import Decimal

import requests
from app.services.currency_exchange import CurrencyExchangeService


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self.payload


def test_frankfurter_is_used_when_nbg_is_unavailable(monkeypatch):
    calls: list[str] = []

    def get(url, **kwargs):
        calls.append(url)
        if url == CurrencyExchangeService.nbg_rates_url:
            raise requests.ConnectionError("NBG DNS unavailable")
        return _Response(
            [
                {
                    "date": "2026-07-18",
                    "base": "GEL",
                    "quote": "USD",
                    "rate": 0.4,
                },
                {
                    "date": "2026-07-18",
                    "base": "GEL",
                    "quote": "EUR",
                    "rate": 0.32,
                },
            ]
        )

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(CurrencyExchangeService, "_rates_cache", None)
    monkeypatch.setattr(CurrencyExchangeService, "_rates_cached_at", 0.0)
    service = CurrencyExchangeService.__new__(CurrencyExchangeService)

    source, target, _ = service.calculate_conversion(
        source_amount=Decimal("1"),
        target_amount=None,
        source_currency="usd",
        target_currency="gel",
    )

    assert calls == [
        CurrencyExchangeService.nbg_rates_url,
        CurrencyExchangeService.frankfurter_rates_url,
    ]
    assert source == Decimal("1.00")
    assert target == Decimal("2.50")
    assert service._raw_rates[0]["source"] == "frankfurter"


def test_nbg_remains_primary_when_available(monkeypatch):
    calls: list[str] = []
    nbg_payload = [
        {
            "date": "2026-07-18",
            "currencies": [{"code": "USD", "quantity": 1, "rate": 2.7}],
        }
    ]

    def get(url, **kwargs):
        calls.append(url)
        return _Response(nbg_payload)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(CurrencyExchangeService, "_rates_cache", None)
    monkeypatch.setattr(CurrencyExchangeService, "_rates_cached_at", 0.0)
    service = CurrencyExchangeService.__new__(CurrencyExchangeService)

    assert service._raw_rates == nbg_payload
    assert calls == [CurrencyExchangeService.nbg_rates_url]


def test_stale_cache_is_used_only_after_both_providers_fail(monkeypatch):
    calls: list[str] = []
    stale_rates = [
        {
            "date": "2026-07-17",
            "currencies": [{"code": "USD", "quantity": 1, "rate": 2.71}],
        }
    ]

    def get(url, **kwargs):
        calls.append(url)
        raise requests.ConnectionError("provider unavailable")

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(CurrencyExchangeService, "_rates_cache", stale_rates)
    monkeypatch.setattr(CurrencyExchangeService, "_rates_cached_at", 0.0)
    service = CurrencyExchangeService.__new__(CurrencyExchangeService)

    assert service._raw_rates == stale_rates
    assert calls == [
        CurrencyExchangeService.nbg_rates_url,
        CurrencyExchangeService.frankfurter_rates_url,
    ]
