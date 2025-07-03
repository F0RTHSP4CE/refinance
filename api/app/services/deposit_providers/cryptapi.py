"""Entity service"""

from decimal import Decimal
from uuid import UUID

import requests
from app.seeding import (
    cryptapi_deposit_provider,
    usdt_erc20_treasury,
    usdt_trc20_treasury,
)
from app.config import Config, get_config
from app.errors.deposit import DepositAmountIncorrect
from app.models.entity import Entity
from app.schemas.deposit import DepositCreateSchema
from app.schemas.deposit_providers.cryptapi import (
    CryptAPICallbackSchema,
    CryptAPIDepositCreateSchema,
)
from app.services.base import BaseService
from app.services.deposit import DepositService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


class CryptAPIDepositProviderService(BaseService[Entity]):
    def __init__(
        self,
        db: Session = Depends(get_uow),
        deposit_service: DepositService = Depends(),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.deposit_service = deposit_service
        self.config = config

    def create_deposit(self, schema: CryptAPIDepositCreateSchema, actor_entity: Entity):
        # check minimum amount accepted by cryptapi
        check = requests.get(f"http://api.cryptapi.io/{schema.coin}/info/").json()
        if schema.amount < (m := Decimal(check["minimum_transaction_coin"])):
            raise DepositAmountIncorrect(f"minimum amount for this coin is {m}")

        # we need some record in databass, create it
        treasury = {
            "trc20/usdt": usdt_trc20_treasury,
            "erc20/usdt": usdt_erc20_treasury,
        }
        d = self.deposit_service.create(
            DepositCreateSchema(
                from_entity_id=cryptapi_deposit_provider.id,
                to_entity_id=schema.to_entity_id,
                amount=schema.amount,
                currency="USD",
                provider="cryptapi",
                details={},
                to_treasury_id=treasury[schema.coin].id,
            ),
            overrides={"actor_entity_id": actor_entity.id},
        )
        addresses = {
            "trc20/usdt": self.config.cryptapi_address_trc20_usdt,
            "erc20/usdt": self.config.cryptapi_address_erc20_usdt,
        }
        confirmations = {"trc20/usdt": 1, "erc20/usdt": 15}
        # create address via crypatpi
        r = requests.get(
            f"https://api.cryptapi.io/{schema.coin}/create/",
            params={
                "callback": f"{self.config.api_url}/callbacks/cryptapi/{d.uuid}",
                "address": addresses[schema.coin],
                "confirmations": confirmations[schema.coin],
            },
        )
        return r.json()

    def complete_deposit(
        self, deposit_uuid: UUID, cryptapi_callback: CryptAPICallbackSchema
    ):
        # it exists?
        d = self.deposit_service.get_by_uuid(deposit_uuid)
        assert d
        # basic check hehe, much validation
        assert cryptapi_callback.value_coin == d.amount
        # confirmed. take your money.
        return self.deposit_service.complete(d.id)
