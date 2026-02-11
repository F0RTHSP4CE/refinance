"""Service dependency providers."""

from app.config import Config, get_config
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


class ServiceContainer:
    """Request-scoped service container."""

    def __init__(self, db: Session, config: Config):
        self.db = db
        self.config = config
        self._tag_service = None
        self._entity_service = None
        self._balance_service = None
        self._treasury_service = None
        self._invoice_service = None
        self._transaction_service = None
        self._split_service = None
        self._deposit_service = None
        self._cryptapi_deposit_provider_service = None
        self._keepz_service = None
        self._keepz_deposit_provider_service = None
        self._pos_service = None
        self._currency_exchange_service = None
        self._fee_service = None
        self._stats_service = None
        self._token_service = None

    @property
    def tag_service(self):
        if self._tag_service is None:
            from app.services.tag import TagService

            self._tag_service = TagService(db=self.db)
        return self._tag_service

    @property
    def entity_service(self):
        if self._entity_service is None:
            from app.services.entity import EntityService

            self._entity_service = EntityService(
                db=self.db, tag_service=self.tag_service
            )
        return self._entity_service

    @property
    def balance_service(self):
        if self._balance_service is None:
            from app.services.balance import BalanceService

            self._balance_service = BalanceService(
                db=self.db, entity_service=self.entity_service
            )
        return self._balance_service

    @property
    def treasury_service(self):
        if self._treasury_service is None:
            from app.services.treasury import TreasuryService

            self._treasury_service = TreasuryService(
                db=self.db, balance_service=self.balance_service
            )
        return self._treasury_service

    @property
    def transaction_service(self):
        self._ensure_invoice_transaction_services()
        return self._transaction_service

    @property
    def invoice_service(self):
        self._ensure_invoice_transaction_services()
        return self._invoice_service

    def _ensure_invoice_transaction_services(self) -> None:
        if self._transaction_service is None:
            from app.services.transaction import TransactionService

            self._transaction_service = TransactionService(
                db=self.db,
                balance_service=self.balance_service,
                tag_service=self.tag_service,
                treasury_service=self.treasury_service,
                invoice_service=None,
            )
        if self._invoice_service is None:
            from app.services.invoice import InvoiceService

            self._invoice_service = InvoiceService(
                db=self.db,
                tag_service=self.tag_service,
                balance_service=self.balance_service,
                transaction_service=self._transaction_service,
            )
        self._transaction_service.set_invoice_service(self._invoice_service)

    @property
    def split_service(self):
        if self._split_service is None:
            from app.services.split import SplitService

            self._split_service = SplitService(
                db=self.db,
                transaction_service=self.transaction_service,
                entity_service=self.entity_service,
                tag_service=self.tag_service,
            )
        return self._split_service

    @property
    def deposit_service(self):
        if self._deposit_service is None:
            from app.services.deposit import DepositService

            self._deposit_service = DepositService(
                db=self.db,
                transaction_service=self.transaction_service,
                tag_service=self.tag_service,
            )
        return self._deposit_service

    @property
    def cryptapi_deposit_provider_service(self):
        if self._cryptapi_deposit_provider_service is None:
            from app.services.deposit_providers.cryptapi import (
                CryptAPIDepositProviderService,
            )

            self._cryptapi_deposit_provider_service = CryptAPIDepositProviderService(
                db=self.db,
                deposit_service=self.deposit_service,
                config=self.config,
            )
        return self._cryptapi_deposit_provider_service

    @property
    def keepz_service(self):
        if self._keepz_service is None:
            from app.services.keepz import KeepzService

            self._keepz_service = KeepzService(db=self.db, config=self.config)
        return self._keepz_service

    @property
    def keepz_deposit_provider_service(self):
        if self._keepz_deposit_provider_service is None:
            from app.services.deposit_providers.keepz import (
                KeepzDepositProviderService,
            )

            self._keepz_deposit_provider_service = KeepzDepositProviderService(
                db=self.db,
                deposit_service=self.deposit_service,
                keepz_service=self.keepz_service,
                config=self.config,
            )
        return self._keepz_deposit_provider_service

    @property
    def pos_service(self):
        if self._pos_service is None:
            from app.services.pos import POSService

            self._pos_service = POSService(
                entity_service=self.entity_service,
                transaction_service=self.transaction_service,
                balance_service=self.balance_service,
            )
        return self._pos_service

    @property
    def currency_exchange_service(self):
        if self._currency_exchange_service is None:
            from app.services.currency_exchange import CurrencyExchangeService

            self._currency_exchange_service = CurrencyExchangeService(
                db=self.db,
                transaction_service=self.transaction_service,
                entity_service=self.entity_service,
            )
        return self._currency_exchange_service

    @property
    def fee_service(self):
        if self._fee_service is None:
            from app.services.fee import FeeService

            self._fee_service = FeeService(
                db=self.db,
                entity_service=self.entity_service,
                currency_exchange_service=self.currency_exchange_service,
                invoice_service=self.invoice_service,
                config=self.config,
            )
        return self._fee_service

    @property
    def stats_service(self):
        if self._stats_service is None:
            from app.services.stats import StatsService

            self._stats_service = StatsService(
                db=self.db,
                fee_service=self.fee_service,
                balance_service=self.balance_service,
                entity_service=self.entity_service,
                currency_exchange_service=self.currency_exchange_service,
            )
        return self._stats_service

    @property
    def token_service(self):
        if self._token_service is None:
            from app.services.token import TokenService

            self._token_service = TokenService(
                db=self.db,
                entity_service=self.entity_service,
                config=self.config,
            )
        return self._token_service


def get_container(
    db: Session = Depends(get_uow),
    config: Config = Depends(get_config),
) -> ServiceContainer:
    return ServiceContainer(db, config)


def get_tag_service(container: ServiceContainer = Depends(get_container)):
    return container.tag_service


def get_entity_service(container: ServiceContainer = Depends(get_container)):
    return container.entity_service


def get_balance_service(container: ServiceContainer = Depends(get_container)):
    return container.balance_service


def get_treasury_service(container: ServiceContainer = Depends(get_container)):
    return container.treasury_service


def get_invoice_service(container: ServiceContainer = Depends(get_container)):
    return container.invoice_service


def get_transaction_service(container: ServiceContainer = Depends(get_container)):
    return container.transaction_service


def get_split_service(container: ServiceContainer = Depends(get_container)):
    return container.split_service


def get_deposit_service(container: ServiceContainer = Depends(get_container)):
    return container.deposit_service


def get_cryptapi_deposit_provider_service(
    container: ServiceContainer = Depends(get_container),
):
    return container.cryptapi_deposit_provider_service


def get_keepz_service(container: ServiceContainer = Depends(get_container)):
    return container.keepz_service


def get_keepz_deposit_provider_service(
    container: ServiceContainer = Depends(get_container),
):
    return container.keepz_deposit_provider_service


def get_pos_service(container: ServiceContainer = Depends(get_container)):
    return container.pos_service


def get_currency_exchange_service(container: ServiceContainer = Depends(get_container)):
    return container.currency_exchange_service


def get_fee_service(container: ServiceContainer = Depends(get_container)):
    return container.fee_service


def get_stats_service(container: ServiceContainer = Depends(get_container)):
    return container.stats_service


def get_token_service(container: ServiceContainer = Depends(get_container)):
    return container.token_service
