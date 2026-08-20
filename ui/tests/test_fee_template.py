import re
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from jinja2 import DictLoader, Environment


def _fee(group_tag_id: int, name: str):
    tag = SimpleNamespace(id=group_tag_id, name="group")
    entity = SimpleNamespace(id=group_tag_id, name=name, active=False, tags=[tag])
    month = SimpleNamespace(
        year=2026,
        month=8,
        amounts={},
        unpaid_invoice_id=None,
        paid_invoice_id=None,
        unpaid_invoice_amounts={},
    )
    return SimpleNamespace(entity=entity, fees=[month])


def test_former_resident_and_member_groups_start_hidden_under_spoilers():
    templates = Path(__file__).parents[1] / "app" / "templates"
    environment = Environment(
        loader=DictLoader(
            {
                "fee/index.jinja2": (templates / "fee/index.jinja2").read_text(),
                "base.jinja2": "{% block content %}{% endblock %}",
                "widgets/tag_inline.jinja2": (
                    "{% macro tag_inline(tag) %}<span>{{ tag.name }}</span>{% endmacro %}"
                ),
            }
        ),
        autoescape=True,
    )
    environment.globals["url_for"] = (
        lambda endpoint, **values: f"/{endpoint}/{values.get('id', '')}"
    )

    ex_resident = _fee(13, "Former resident")
    ex_member = _fee(18, "Former member")
    fee_rows = [
        {"fee": ex_resident, "group": "ex-resident", "index": 0, "unpaid_total": {}},
        {"fee": ex_member, "group": "ex-member", "index": 0, "unpaid_total": {}},
    ]

    rendered = environment.get_template("fee/index.jinja2").render(
        fees=[ex_resident, ex_member],
        fee_rows=fee_rows,
        group_unpaid_totals={
            "ex-resident": {"usd": Decimal("10")},
            "ex-member": {"usd": Decimal("20")},
        },
        current_month=8,
        current_year=2026,
    )

    assert re.search(
        r'class="fee-spoiler-toggle"\s+data-fee-group="ex-resident"\s+'
        r'aria-expanded="false"',
        rendered,
    )
    assert re.search(
        r'class="fee-spoiler-toggle"\s+data-fee-group="ex-member"\s+'
        r'aria-expanded="false"',
        rendered,
    )
    assert rendered.count('data-fee-group="ex-resident" hidden') == 4
    assert rendered.count('data-fee-group="ex-member" hidden') == 4
