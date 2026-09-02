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
ex_member_tag = Tag(id=18, name="ex-member", comment="former hackerspace member")
guest_tag = Tag(id=15, name="guest", comment="hackerspace guests")
pos_tag = Tag(id=16, name="pos", comment="point of sale (card payments)")
rent_tag = Tag(id=7, name="rent", comment="monthly rent for the physical place")
f0_tag = Tag(id=8, name="hackerspace", comment="F0RTHSPACE hackerspace")
deposit_tag = Tag(id=9, name="deposit", comment="money input into system")
withdrawal_tag = Tag(id=10, name="withdrawal", comment="money output from system")
currency_exchange_tag = Tag(
    id=12, name="exchange", comment="currency exchange (automatic)"
)
fee_tag = Tag(id=3, name="fee", comment="monthly fee")
donation_tag = Tag(
    id=5, name="donation", comment="free money from guests/residents (not a fee)"
)
automatic_tag = Tag(id=17, name="automatic", comment="automatically generated / paid")
room_tag = Tag(id=19, name="room", comment="hackerspace rooms")
fortune_tag = Tag(id=20, name="fortune", comment="verifiable lottery")
# commonly used treasuries
cash_treasury = Treasury(id=1, name="cash")
usdt_erc20_treasury = Treasury(id=51, name="usdt/erc20")
usdt_trc20_treasury = Treasury(id=52, name="usdt/trc20")
keepz_treasury = Treasury(id=53, name="keepz")
stripe_treasury = Treasury(id=54, name="stripe")

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
stripe_deposit_provider = Entity(
    id=54,
    name="stripe_in",
    comment="stripe.com deposit provider",
    tags=[deposit_tag],
)
anonymous_entity = Entity(
    id=14,
    name="anonymous",
    comment="anonymous guest donor",
    tags=[guest_tag],
)
fortune_entity = Entity(
    id=62,
    name="fortune",
    comment="verifiable lottery",
    tags=[fortune_tag],
)

SEEDING: dict[Type[BaseModel], list[BaseModel]] = {
    Tag: [
        sys_tag,
        resident_tag,
        fee_tag,
        utilities_tag,
        donation_tag,
        rent_tag,
        f0_tag,
        deposit_tag,
        withdrawal_tag,
        currency_exchange_tag,
        ex_resident_tag,
        member_tag,
        ex_member_tag,
        guest_tag,
        pos_tag,
        automatic_tag,
        room_tag,
        fortune_tag,
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
        stripe_deposit_provider,
        # guest donors
        anonymous_entity,
        # rooms
        Entity(id=55, name="basement workshop", tags=[room_tag]),
        Entity(id=56, name="open-space", tags=[room_tag]),
        Entity(id=57, name="resident room", tags=[room_tag]),
        Entity(id=58, name="electronics lab", tags=[room_tag]),
        Entity(id=59, name="kitchen", tags=[room_tag]),
        Entity(id=60, name="music studio", tags=[room_tag]),
        Entity(id=61, name="chill zone", tags=[room_tag]),
        fortune_entity,
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
        keepz_treasury,
        stripe_treasury,
        usdt_erc20_treasury,
        usdt_trc20_treasury,
    ],
}
