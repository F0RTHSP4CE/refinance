from app.controllers import fortune as fortune_controller
from flask import Flask


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _API:
    def __init__(self, game):
        self.game = game
        self.calls = []

    def http(self, method, endpoint, params=None, data=None):
        self.calls.append(
            {
                "method": method,
                "endpoint": endpoint,
                "params": params,
                "data": data,
            }
        )
        if method == "POST" and endpoint == "fortune/games":
            return _Response({"id": self.game["id"]})
        if method == "GET":
            return _Response(self.game)
        if method == "POST" and endpoint.endswith("/play"):
            return _Response({**self.game, "status": "settled"})
        raise AssertionError(f"Unexpected request: {method} {endpoint}")


def _open_game():
    return {
        "id": 42,
        "status": "open",
        "rules": {
            "total_tiles": 100,
            "currency": "usd",
            "currencies": ["usd", "gel", "eur"],
            "min_stake": "1.00",
            "max_stake": "25.00",
            "stake_presets": ["1.00", "5.00", "10.00", "25.00"],
            "player_tile_count": 10,
            "boosted_player_tile_count": 12,
        },
    }


def _client():
    app = Flask(__name__)
    app.secret_key = "test"
    app.config["WTF_CSRF_ENABLED"] = False
    app.register_blueprint(fortune_controller.fortune_bp, url_prefix="/fortune")
    client = app.test_client()
    with client.session_transaction() as session:
        session["token"] = "test-token"
    return client


def test_start_creates_game_and_redirects(monkeypatch):
    api = _API(_open_game())
    monkeypatch.setattr(fortune_controller, "get_refinance_api_client", lambda: api)

    response = _client().get("/fortune/")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/fortune/42")
    assert [(call["method"], call["endpoint"]) for call in api.calls] == [
        ("POST", "fortune/games")
    ]


def test_play_submits_stake_boost_and_tiles_then_redirects(monkeypatch):
    api = _API(_open_game())
    monkeypatch.setattr(fortune_controller, "get_refinance_api_client", lambda: api)
    selected = [str(tile) for tile in range(1, 11)]

    response = _client().post(
        "/fortune/42",
        data={
            "stake": "10.00",
            "currency": "gel",
            "selected_tiles": selected,
            "submit": "Reveal fortune",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/fortune/42")
    play_call = api.calls[-1]
    assert play_call["method"] == "POST"
    assert play_call["endpoint"] == "fortune/games/42/play"
    assert play_call["data"] == {
        "stake": "10.00",
        "currency": "gel",
        "boosted": False,
        "selected_tiles": list(range(1, 11)),
    }
