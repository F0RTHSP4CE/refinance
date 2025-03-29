from typing import Type

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.tag import Tag

# commonly used tags
sys_tag = Tag(id=1, name="system", comment="system")  # , color="999999"
utilities_tag = Tag(
    id=4, name="utilities", comment="gas, electricity, water, internet, etc"
)
resident_tag = Tag(id=2, name="resident", comment="hackerspace residents")
payprovider_tag = Tag(
    id=6, name="payprovider", comment="generic automatic money deposit"
)
rent_tag = Tag(id=7, name="rent")
f0_tag = Tag(id=8, name="hackerspace")
deposit_tag = Tag(id=9, name="deposit", comment="money input into system")
withdrawal_tag = Tag(id=10, name="withdrawal", comment="money output from system")
currency_exchange_tag = Tag(
    id=12, name="exchange", comment="currency exchange (automatic)"
)

# commonly used entities
currency_exchange_entity = Entity(
    id=11,
    name="exchange",
    comment="automatic money caster eur(gel(usd(float(binary(...)))))",
    tags=[currency_exchange_tag],
)

BOOTSTRAP: dict[Type[BaseModel], list[BaseModel]] = {
    Tag: [
        sys_tag,
        resident_tag,
        Tag(id=3, name="fee", comment="monthly resident's fee"),
        utilities_tag,
        Tag(
            id=5,
            name="donation",
            comment="free money from guests/residents (not a fee)",
        ),
        payprovider_tag,
        rent_tag,
        f0_tag,
        deposit_tag,
        withdrawal_tag,
        currency_exchange_tag,
    ],
    Entity: [
        # hackerspace
        Entity(id=1, name="F0", comment="F0RTHSPACE hackerspace", tags=[f0_tag]),
        # generic deposit/withdrawal
        Entity(
            id=2, name="cash_in", comment="classic money deposit", tags=[deposit_tag]
        ),
        Entity(
            id=3,
            name="cash_out",
            comment="classic money withdrawal",
            tags=[withdrawal_tag],
        ),
        Entity(
            id=4, name="bank_in", comment="bank transfer deposit", tags=[deposit_tag]
        ),
        Entity(
            id=5,
            name="bank_out",
            comment="bank transfer withdrawal",
            tags=[withdrawal_tag],
        ),
        # utilities
        Entity(id=6, name="gas", comment="gas bill (heating)", tags=[utilities_tag]),
        Entity(
            id=7,
            name="electricity",
            comment="electricity bill (light)",
            tags=[utilities_tag],
        ),
        Entity(id=8, name="water", comment="water bill", tags=[utilities_tag]),
        Entity(id=9, name="internet", comment="internet bill", tags=[utilities_tag]),
        Entity(id=10, name="rent", comment="rent bill", tags=[rent_tag]),
        currency_exchange_entity,
        # payment providers
        Entity(
            id=50,
            name="cryptapi_in",
            comment="cryptocurrency deposit",
            tags=[deposit_tag, payprovider_tag],
        ),
        # residents
        Entity(
            id=100, name="mike", auth={"telegram_id": 97702445}, tags=[resident_tag]
        ),
    ],
}
