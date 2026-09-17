from decimal import Decimal
from pathlib import Path

import pytest
from app.controllers import donation as donation_controller
from flask import Flask

RECIPIENTS = [
    {"id": 1, "name": "F0RTHSP4CE", "general": True, "balance_usd": 100},
    {"id": 42, "name": "Music Studio", "general": False, "balance_usd": 25},
    {"id": 84, "name": "Community Projects", "general": False, "balance_usd": 17},
]


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class _API:
    def __init__(self, result=None):
        self.result = result or {}
        self.calls = []

    def http(self, method, endpoint, params=None, data=None):
        self.calls.append((method, endpoint, params, data))
        if endpoint == "donations/recipients":
            return _Response(RECIPIENTS)
        return _Response(self.result)


def _client(monkeypatch, api, *, stripe=False):
    monkeypatch.setattr(donation_controller, "RefinanceAPI", lambda token: api)
    monkeypatch.setattr(donation_controller.Config, "STRIPE_CONFIGURED", stripe)
    template_folder = Path(__file__).parents[1] / "app" / "templates"
    app = Flask(__name__, template_folder=template_folder)
    app.secret_key = "test"
    app.register_blueprint(donation_controller.donation_bp, url_prefix="/donate")
    return app.test_client()


def test_donate_renders_one_canonical_form_and_honors_room_deep_link(monkeypatch):
    response = _client(monkeypatch, _API()).get("/donate/?to=music-studio")
    page = response.get_data(as_text=True)
    form = page.split("</form>", 1)[0]

    assert response.status_code == 200
    for field in ("type", "amount", "currency", "comment", "recipient"):
        assert form.count(f'name="{field}"') == 1
    assert 'name="recipient" value="42"' in form
    assert "recurring_custom_amount" not in page
    assert "onetime_currency" not in page


def test_donate_renders_and_selects_custom_api_recipient(monkeypatch):
    response = _client(monkeypatch, _API()).get("/donate/?to=community-projects")
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="recipient" value="84"' in page
    assert 'data-label="Community Projects"' in page
    assert "$17" in page


def test_onetime_donation_posts_canonical_payload(monkeypatch):
    api = _API({"payment_url": "https://pay.example/donation"})
    response = _client(monkeypatch, api).post(
        "/donate/",
        data={
            "type": "onetime",
            "amount": "12,50",
            "currency": "gel",
            "comment": "Ada",
            "recipient": "42",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "https://pay.example/donation"
    assert api.calls[-1] == (
        "POST",
        "donations",
        None,
        {
            "amount": "12.50",
            "currency": "GEL",
            "comment": "Ada",
            "recipient_entity_id": 42,
        },
    )


def test_successful_submission_is_restored_on_next_visit(monkeypatch):
    api = _API({"checkout_session_url": "https://checkout.example/session"})
    client = _client(monkeypatch, api, stripe=True)

    submitted = client.post(
        "/donate/",
        data={
            "type": "recurring",
            "amount": "12,50",
            "currency": "EUR",
            "comment": "Ada",
            "recipient": "42",
        },
    )
    assert submitted.status_code == 302

    page = client.get("/donate/").get_data(as_text=True)
    assert 'name="type" value="recurring"' in page
    assert 'name="amount" value="12,50"' in page
    assert 'name="currency" value="EUR"' in page
    assert 'name="comment" value="Ada"' in page
    assert 'name="recipient" value="42"' in page


def test_deep_link_overrides_saved_form_values(monkeypatch):
    api = _API({"payment_url": "https://pay.example/donation"})
    client = _client(monkeypatch, api, stripe=True)
    client.post(
        "/donate/",
        data={
            "type": "onetime",
            "amount": "15",
            "currency": "GEL",
            "comment": "Grace",
            "recipient": "42",
        },
    )

    page = client.get(
        "/donate/",
        query_string={
            "to": "community-projects",
            "amount": "25.50",
            "currency": "usd",
            "type": "recurring",
        },
    ).get_data(as_text=True)
    assert 'name="type" value="recurring"' in page
    assert 'name="amount" value="25.50"' in page
    assert 'name="currency" value="USD"' in page
    assert 'name="comment" value="Grace"' in page
    assert 'name="recipient" value="84"' in page


def test_invalid_deep_link_values_are_ignored(monkeypatch):
    page = (
        _client(monkeypatch, _API())
        .get(
            "/donate/",
            query_string={
                "to": "unknown",
                "amount": "0",
                "currency": "BTC",
                "type": "recurring",
            },
        )
        .get_data(as_text=True)
    )

    assert 'name="type" value="onetime"' in page
    assert 'name="amount" value="10"' in page
    assert 'name="currency" value="USD"' in page
    assert 'name="recipient" value="1"' in page


def test_recurring_donation_adds_checkout_urls(monkeypatch):
    api = _API({"checkout_session_url": "https://checkout.example/session"})
    response = _client(monkeypatch, api, stripe=True).post(
        "/donate/",
        data={
            "type": "recurring",
            "amount": "20",
            "currency": "EUR",
            "comment": "Grace",
            "recipient": "1",
        },
    )

    assert response.status_code == 302
    method, endpoint, params, payload = api.calls[-1]
    assert (method, endpoint, params) == ("POST", "donations/subscribe", None)
    assert payload == {
        "amount": "20",
        "currency": "EUR",
        "comment": "Grace",
        "recipient_entity_id": 1,
        "success_url": (
            "http://localhost/donate/subscribed?stripe_session_id={CHECKOUT_SESSION_ID}"
        ),
        "cancel_url": "http://localhost/donate/",
    }


def test_amount_errors_preserve_large_integer_bounds(monkeypatch):
    monkeypatch.setattr(
        donation_controller.Config, "DONATION_MAX_AMOUNT", Decimal("3000")
    )

    with pytest.raises(ValueError) as error:
        donation_controller._parse_amount("3001")

    assert str(error.value) == "Donation amount must be at most 3000."
