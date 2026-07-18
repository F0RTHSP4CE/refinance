from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from jinja2 import DictLoader, Environment


def _object(**values):
    return SimpleNamespace(**values)


def test_tagged_prefilled_recipient_remains_an_editable_selected_dropdown():
    templates = Path(__file__).parents[1] / "app" / "templates"
    environment = Environment(
        loader=DictLoader(
            {
                "invoice/detail.jinja2": (
                    templates / "invoice/detail.jinja2"
                ).read_text(),
                "base.jinja2": "{% block content %}{% endblock %}",
                "widgets/tag_inline.jinja2": (
                    "{% macro tag_inline(tag) %}<span>{{ tag.name }}</span>{% endmacro %}"
                ),
            }
        ),
        autoescape=True,
    )
    environment.globals.update(
        url_for=lambda endpoint, **values: f"/{endpoint}/{values.get('id', '')}",
        human_readable_date=lambda value: str(value),
    )

    room_tag = _object(id=19, name="room")
    f0 = _object(id=1, name="F0", active=True, tags=[])
    default_room = _object(
        id=60,
        name="Music studio",
        active=True,
        tags=[room_tag],
    )
    payer = _object(id=100, name="Payer", active=True, tags=[])
    invoice = _object(
        id=785,
        billing_period=date(2026, 7, 1),
        status="pending",
        from_entity_id=payer.id,
        from_entity=payer,
        actor_entity_id=1,
        actor_entity=f0,
        transaction_id=None,
        tags=[],
        comment=None,
        created_at="2026-07-18T10:00:00",
        items=[
            _object(
                id=501,
                to_entity_id=f0.id,
                to_entity=f0,
                to_tag_id=None,
                to_tag=None,
                amounts=[_object(currency="usd", amount="42.00")],
            ),
            _object(
                id=502,
                to_entity_id=default_room.id,
                to_entity=default_room,
                to_tag_id=room_tag.id,
                to_tag=room_tag,
                amounts=[_object(currency="usd", amount="8.00")],
            ),
        ],
    )

    rendered = environment.get_template("invoice/detail.jinja2").render(
        invoice=invoice,
        form=_object(hidden_tag=lambda: ""),
        item_transactions={},
        item_entity_choices={502: [(60, "Music studio"), (58, "Electronics lab")]},
        transaction=None,
    )

    assert 'name="item_502_entity_id"' in rendered
    assert re.search(r'<option value="60"\s+selected>Music studio</option>', rendered)
    assert re.search(r'<option value="58">Electronics lab</option>', rendered)
    assert rendered.count('name="item_502_entity_id"') == 1
