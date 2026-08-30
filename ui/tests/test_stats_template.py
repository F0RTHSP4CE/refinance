from pathlib import Path

from jinja2 import DictLoader, Environment


def test_fee_transaction_chart_uses_separate_f0_and_room_series():
    templates = Path(__file__).parents[1] / "app" / "templates"
    environment = Environment(
        loader=DictLoader(
            {
                "stats/index.jinja2": (templates / "stats/index.jinja2").read_text(),
                "base.jinja2": "{% block content %}{% endblock %}",
            }
        ),
        autoescape=True,
    )

    rendered = environment.get_template("stats/index.jinja2").render(
        monthly_fee_sum=[],
        fee_transactions_by_month=[],
        donations_by_month=[],
        system_balance_history=[],
    )

    assert "Fees to F0 (USD)" in rendered
    assert "item.f0_fee_total_usd" in rendered
    assert "Fees to rooms (USD)" in rendered
    assert "item.room_fee_total_usd" in rendered
    assert "item.fee_total_usd" not in rendered
