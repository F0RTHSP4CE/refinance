import random
from decimal import Decimal
from typing import Type

from app.models.base import BaseModel
from app.models.entity import Entity
from app.models.tag import Tag
from app.models.treasury import Treasury

# commonly used tags
sys_tag = Tag(id=1, name="system", comment="[internal machinery]")  # , color="999999"
utilities_tag = Tag(
    id=4, name="utilities", comment="gas, electricity, water, internet, etc"
)
resident_tag = Tag(id=2, name="resident", comment="hackerspace residents")
ex_resident_tag = Tag(id=13, name="ex-resident", comment="former hackerspace resident")
member_tag = Tag(id=14, name="member", comment="hackerspace members")
guest_tag = Tag(id=15, name="guest", comment="hackerspace guests")
pos_tag = Tag(id=16, name="pos", comment="point of sale (card payments)")
rent_tag = Tag(id=7, name="rent", comment="monthly rent for the physical place")
f0_tag = Tag(id=8, name="hackerspace", comment="F0RTHSPACE hackerspace")
deposit_tag = Tag(id=9, name="deposit", comment="money input into system")
withdrawal_tag = Tag(id=10, name="withdrawal", comment="money output from system")
currency_exchange_tag = Tag(
    id=12, name="exchange", comment="currency exchange (automatic)"
)
fee_tag = Tag(id=3, name="fee", comment="monthly resident's fee")
automatic_tag = Tag(id=17, name="automatic", comment="automatically generated / paid")
# commonly used treasuries
cash_treasury = Treasury(id=1, name="cash")
usdt_erc20_treasury = Treasury(id=51, name="usdt/erc20")
usdt_trc20_treasury = Treasury(id=52, name="usdt/trc20")

# commonly used entities
f0_entity = Entity(
    id=1,
    name="F0",
    comment="F0RTHSPACE hackerspace",
    tags=[f0_tag],
    auth={"telegram_id": 97702445},
)

# entities used by other modules for creating transactions from/to
currency_exchange_entity = Entity(
    id=11,
    name="exchange",
    comment="internal currency exchange",
    tags=[currency_exchange_tag],
)
cryptapi_deposit_provider = Entity(
    id=50,
    name="cryptapi_in",
    comment="crypatapi.io deposit provider",
    tags=[deposit_tag],
)
keepz_deposit_provider = Entity(
    id=53,
    name="keepz_in",
    comment="keepz.me deposit provider",
    tags=[deposit_tag],
)

SEEDING: dict[Type[BaseModel], list[BaseModel]] = {
    Tag: [
        sys_tag,
        resident_tag,
        fee_tag,
        utilities_tag,
        Tag(
            id=5,
            name="donation",
            comment="free money from guests/residents (not a fee)",
        ),
        rent_tag,
        f0_tag,
        deposit_tag,
        withdrawal_tag,
        currency_exchange_tag,
        ex_resident_tag,
        member_tag,
        guest_tag,
        pos_tag,
        automatic_tag,
    ],
    Entity: [
        # hackerspace
        f0_entity,
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
        Entity(id=12, name="crypto_in", comment="crypto deposit", tags=[deposit_tag]),
        Entity(
            id=13, name="crypto_out", comment="crypto withdrawal", tags=[withdrawal_tag]
        ),
        # payment providers
        cryptapi_deposit_provider,
        keepz_deposit_provider,
        # residents
        #
        # Entity(
        #     id=200, name="mike", auth={"telegram_id": 97702445}, tags=[resident_tag]
        # ),
    ],
    # example transactions
    #
    # Transaction: [
    #     Transaction(
    #         actor_entity_id=random.randint(1, 10),
    #         from_entity_id=random.randint(1, 5),
    #         to_entity_id=random.randint(6, 10),
    #         amount=Decimal(random.random() * 100),
    #         currency=random.choice(["GEL", "USD", "EUR"]),
    #     )
    #     for _ in range(300)
    # ],
    Treasury: [
        cash_treasury,
        usdt_erc20_treasury,
        usdt_trc20_treasury,
    ],
}
