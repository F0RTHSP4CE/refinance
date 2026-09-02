from pathlib import Path

from jinja2 import DictLoader, Environment
from markupsafe import Markup


class _Field:
    def __init__(self, field_id, data=None):
        self.id = field_id
        self.data = data

    def __call__(self, **kwargs):
        attrs = " ".join(f'{key}="{value}"' for key, value in kwargs.items())
        return Markup(f'<input id="{self.id}" {attrs}>')


class _CurrencyField(_Field):
    def __call__(self, **kwargs):
        return Markup(
            '<select id="currency" name="currency">'
            '<option value="usd">USD</option>'
            '<option value="gel">GEL</option>'
            '<option value="eur">EUR</option>'
            "</select>"
        )


class _Form:
    csrf_token = Markup('<input name="csrf_token" value="test">')
    stake = _Field("stake")
    currency = _CurrencyField("currency")
    boosted = _Field("boosted")
    selected_tiles = _Field("selected_tiles", [])
    submit = _Field("submit")


def _environment():
    templates = Path(__file__).parents[1] / "app" / "templates"
    environment = Environment(
        loader=DictLoader(
            {
                "fortune/detail.jinja2": (
                    templates / "fortune/detail.jinja2"
                ).read_text(),
                "base.jinja2": "{% block content %}{% endblock %}",
            }
        ),
        autoescape=True,
    )
    environment.globals["url_for"] = (
        lambda endpoint, **values: f"/{endpoint}/{values.get('id', '')}"
    )
    environment.globals["human_readable_date"] = lambda value: value
    return environment


def _rules():
    return {
        "model_version": 1,
        "total_tiles": 100,
        "currency": "usd",
        "currencies": ["usd", "gel", "eur"],
        "min_stake": "1.00",
        "max_stake": "25.00",
        "stake_presets": ["1.00", "5.00", "10.00", "25.00"],
        "player_tile_count": 10,
        "boosted_player_tile_count": 12,
        "server_tile_count": 1,
        "prize_multiplier": "5",
        "boost_cost_multiplier": "1.25",
        "base_win_probability": "0.1",
        "boosted_win_probability": "0.12",
        "relative_probability_increase": "0.2",
    }


def test_open_fortune_renders_compact_bet_summary_and_100_tiles():
    game = {
        "id": 9,
        "status": "open",
        "created_at": "2026-09-02T12:00:00",
        "commitment_sha256": "a" * 64,
        "rules": _rules(),
    }

    rendered = (
        _environment()
        .get_template("fortune/detail.jinja2")
        .render(game=game, form=_Form())
    )

    assert 'class="fortune-game-card"' in rendered
    assert "1 server tile · any match wins" in rendered
    assert ">Stake<" in rendered
    assert ">Prize<" in rendered
    assert '<option value="usd">USD</option>' in rendered
    assert '<option value="gel">GEL</option>' in rendered
    assert '<option value="eur">EUR</option>' in rendered
    assert "Boost my odds" in rendered
    assert "12 picks · 12% chance" in rendered
    assert "Provably fair" in rendered
    assert "SHA-256 committed" in rendered
    assert "Rules committed before your pick" not in rendered
    assert 'class="fortune-rules"' not in rendered
    assert rendered.count('class="fortune-tile-input"') == 100
    assert 'value="100"' in rendered
    assert 'class="fortune-submit-progress"' in rendered
    assert "Win up to 5.00 USD" in rendered
    assert rendered.index('class="fortune-board"') < rendered.index(
        'class="fortune-left-footer"'
    )
    assert rendered.index('class="fortune-bet-summary"') < rendered.index(
        'class="fortune-loss-copy"'
    )
    assert rendered.index('class="fortune-loss-copy"') < rendered.index(
        'class="fortune-fairness"'
    )


def test_settled_fortune_renders_gross_prize_reveal_and_verifier_hooks():
    source = '{"nonce":"abc","rules":{},"server_tiles":[7]}'
    game = {
        "id": 10,
        "status": "settled",
        "won": True,
        "net_change": "37.50",
        "total_cost": "12.50",
        "gross_prize": "50.00",
        "currency": "gel",
        "selected_tiles": list(range(1, 13)),
        "server_tiles": [7],
        "commitment_sha256": "b" * 64,
        "commitment_source": source,
        "transaction": {"id": 88},
        "rules": _rules(),
    }

    rendered = (
        _environment()
        .get_template("fortune/detail.jinja2")
        .render(game=game, form=None)
    )

    assert "50.00 GEL" in rendered
    assert "Gross prize · 12.50 GEL stake already deducted" in rendered
    assert "+37.50 GEL" not in rendered
    assert "Server tile" in rendered
    assert "Verify fair draw" in rendered
    assert 'id="fortune-commitment-hash"' in rendered
    assert 'id="fortune-commitment-source"' in rendered
    assert source.replace('"', "&#34;") in rendered
    assert rendered.count('class="fortune-result-tile') == 100
    assert "data-fortune-win-popup" in rendered
    assert "YOU WON!" in rendered
    assert 'class="fortune-win-amount-track"' in rendered
    assert rendered.count("50.00 GEL</span>") == 12
    assert 'class="fortune-win-play-again"' in rendered
    assert 'class="fortune-win-see-result"' in rendered


def test_losing_fortune_does_not_render_win_popup():
    game = {
        "id": 11,
        "status": "settled",
        "won": False,
        "net_change": "-10.00",
        "total_cost": "10.00",
        "currency": "eur",
        "selected_tiles": list(range(1, 11)),
        "server_tiles": [100],
        "commitment_sha256": "c" * 64,
        "commitment_source": '{"server_tiles":[100]}',
        "transaction": {"id": 89},
        "rules": _rules(),
    }

    rendered = (
        _environment()
        .get_template("fortune/detail.jinja2")
        .render(game=game, form=None)
    )

    assert "No match" in rendered
    assert "data-fortune-win-popup" not in rendered
