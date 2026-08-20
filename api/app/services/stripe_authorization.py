"""Stripe authorization service and recurring charge orchestration."""

from __future__ import annotations

import datetime
import logging
from decimal import Decimal

from app.config import Config, get_config
from app.dependencies.services import (
    get_balance_service,
    get_currency_exchange_service,
    get_deposit_service,
    get_stripe_service,
)
from app.errors.common import NotFoundError
from app.errors.stripe import StripeRequestError
from app.models.deposit import DepositStatus
from app.models.entity import Entity
from app.models.invoice import Invoice, InvoiceStatus
from app.models.stripe_authorization import StripeAuthorization, StripeAuthorizationMode
from app.schemas.deposit import (
    DepositCreateSchema,
    DepositFiltersSchema,
    DepositUpdateSchema,
)
from app.schemas.stripe_authorization import StripeAuthorizationSetupSchema
from app.seeding import (
    automatic_tag,
    f0_entity,
    member_tag,
    resident_tag,
    stripe_deposit_provider,
    stripe_treasury,
)
from app.services.balance import BalanceService
from app.services.currency_exchange import CurrencyExchangeService
from app.services.deposit import DepositService
from app.services.entity_owed import (
    EntityOwedSummary,
    calculate_entity_owed,
    invoice_currency_options,
)
from app.services.stripe import (
    StripeCheckoutSessionData,
    StripeInvoiceData,
    StripeService,
)
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _resolved_static(
    mode: StripeAuthorizationMode,
    static_amount: Decimal,
    static_currency: str | None,
) -> tuple[Decimal, str | None]:
    """Return (amount, currency) for GUEST_STATIC, or (0, None) for ENTITY_DYNAMIC."""
    if mode == StripeAuthorizationMode.GUEST_STATIC:
        return static_amount, static_currency
    return Decimal("0.00"), None


def _metadata_recipient_id(metadata: dict) -> int | None:
    raw = metadata.get("donation_recipient_entity_id")
    try:
        return int(raw) if raw else None
    except (TypeError, ValueError):
        return None


class StripeAuthorizationService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        stripe_service: StripeService = Depends(get_stripe_service),
        currency_exchange_service: CurrencyExchangeService = Depends(
            get_currency_exchange_service
        ),
        deposit_service: DepositService = Depends(get_deposit_service),
        balance_service: BalanceService = Depends(get_balance_service),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.stripe_service = stripe_service
        self.currency_exchange_service = currency_exchange_service
        self.deposit_service = deposit_service
        self.balance_service = balance_service
        self.config = config

    # ── Queries ────────────────────────────────────────────────────────────

    def list_for_entity(self, entity_id: int) -> list[StripeAuthorization]:
        return (
            self.db.query(StripeAuthorization)
            .filter(StripeAuthorization.entity_id == entity_id)
            .order_by(StripeAuthorization.priority.asc(), StripeAuthorization.id.asc())
            .all()
        )

    def get_for_entity(
        self, authorization_id: int, entity_id: int
    ) -> StripeAuthorization:
        auth = self.get(authorization_id)
        if auth.entity_id != entity_id:
            raise NotFoundError(
                f"StripeAuthorization id={authorization_id} entity_id={entity_id}"
            )
        return auth

    def get(self, authorization_id: int) -> StripeAuthorization:
        auth = (
            self.db.query(StripeAuthorization)
            .filter(StripeAuthorization.id == authorization_id)
            .first()
        )
        if auth is None:
            raise NotFoundError(f"StripeAuthorization id={authorization_id}")
        return auth

    # ── Setup Session ──────────────────────────────────────────────────────

    def create_setup_session(
        self,
        schema: StripeAuthorizationSetupSchema,
        actor_entity: Entity,
    ) -> tuple[str, str | None]:
        target_entity_id = schema.entity_id or actor_entity.id
        mode = StripeAuthorizationMode(schema.mode)
        static_amount = (
            Decimal(str(schema.static_amount)).quantize(Decimal("0.01"))
            if schema.static_amount is not None
            else Decimal("0.00")
        )
        static_currency = (schema.static_currency or "").upper().strip() or None

        if mode == StripeAuthorizationMode.GUEST_STATIC:
            recipient_id = schema.donation_recipient_entity_id
            recipient_name = None
            if recipient_id and recipient_id != f0_entity.id:
                recipient = (
                    self.db.query(Entity).filter(Entity.id == recipient_id).first()
                )
                recipient_name = recipient.name if recipient else None
            session = self.stripe_service.create_subscription_checkout_session(
                entity_id=target_entity_id,
                amount=static_amount,
                currency=static_currency or "",
                donation_comment=schema.donation_comment or None,
                donation_recipient_entity_id=recipient_id,
                donation_recipient_name=recipient_name,
                success_url=self._resolve_setup_success_url(
                    schema.success_url, target_entity_id
                ),
                cancel_url=self._resolve_setup_cancel_url(
                    schema.cancel_url, target_entity_id
                ),
            )
        else:
            session = self.stripe_service.create_setup_session(
                entity_id=target_entity_id,
                mode=mode.value,
                static_amount=static_amount,
                static_currency=static_currency,
                success_url=self._resolve_setup_success_url(
                    schema.success_url, target_entity_id
                ),
                cancel_url=self._resolve_setup_cancel_url(
                    schema.cancel_url, target_entity_id
                ),
                donation_comment=schema.donation_comment or None,
            )
        return session.id, session.url

    def handle_setup_session_completed(
        self,
        session_obj: dict | StripeCheckoutSessionData,
        fallback_entity_id: int | None = None,
    ) -> StripeAuthorization | None:
        session_data = (
            session_obj
            if isinstance(session_obj, StripeCheckoutSessionData)
            else self.stripe_service.normalize_checkout_session(session_obj)
        )

        if session_data.mode == "subscription":
            return self._handle_subscription_session_completed(session_data)

        if session_data.mode != "setup":
            return None

        setup_intent_id = session_data.setup_intent_id
        if not setup_intent_id:
            return None

        setup_intent = self.stripe_service.retrieve_setup_intent(str(setup_intent_id))
        setup_intent_data = self.stripe_service.normalize_setup_intent(setup_intent)

        metadata = dict(session_data.metadata) or dict(setup_intent_data.metadata)

        entity_id_raw = metadata.get("entity_id")
        if not entity_id_raw and fallback_entity_id is not None:
            entity_id_raw = str(fallback_entity_id)
            metadata.setdefault("mode", StripeAuthorizationMode.ENTITY_DYNAMIC.value)
            metadata.setdefault("static_amount", "0.00")
            metadata.setdefault("static_currency", "")
        if not entity_id_raw:
            return None

        payment_method_id = setup_intent_data.payment_method_id
        if not payment_method_id:
            return None

        pm_data = self.stripe_service.normalize_payment_method(
            self.stripe_service.retrieve_payment_method(payment_method_id)
        )
        customer_id = setup_intent_data.customer_id or pm_data.customer_id
        if not customer_id:
            return None

        mode = StripeAuthorizationMode(str(metadata.get("mode") or "entity_dynamic"))
        static_amount = Decimal(str(metadata.get("static_amount") or "0")).quantize(
            Decimal("0.01")
        )
        static_currency = metadata.get("static_currency")
        if static_currency:
            static_currency = str(static_currency).upper().strip()

        entity_id = int(entity_id_raw)
        resolved_amount, resolved_currency = _resolved_static(
            mode, static_amount, static_currency
        )
        card_fields = dict(
            card_brand=pm_data.card_brand,
            card_last4=pm_data.card_last4,
            card_exp_month=pm_data.card_exp_month,
            card_exp_year=pm_data.card_exp_year,
        )

        auth = (
            self.db.query(StripeAuthorization)
            .filter(
                StripeAuthorization.entity_id == entity_id,
                StripeAuthorization.stripe_payment_method_id == payment_method_id,
            )
            .first()
        )

        now = datetime.datetime.now()
        donation_comment = metadata.get("donation_comment") or None
        donation_recipient_id = _metadata_recipient_id(metadata)
        if auth is None:
            auth = StripeAuthorization(
                entity_id=entity_id,
                stripe_customer_id=customer_id,
                stripe_payment_method_id=payment_method_id,
                mode=mode,
                static_amount=resolved_amount,
                static_currency=resolved_currency,
                active=True,
                priority=self._next_priority(entity_id),
                consecutive_error_count=0,
                last_error=None,
                last_success_at=None,
                last_attempt_at=now,
                comment=donation_comment or None,
                donation_recipient_entity_id=donation_recipient_id,
                **card_fields,
            )
            self.db.add(auth)
        else:
            auth.stripe_customer_id = customer_id
            auth.mode = mode
            auth.static_amount = resolved_amount
            auth.static_currency = resolved_currency
            auth.active = True
            auth.consecutive_error_count = 0
            auth.last_error = None
            auth.last_success_at = now
            auth.last_attempt_at = now
            auth.modified_at = now
            if donation_comment:
                auth.comment = donation_comment
            if donation_recipient_id is not None:
                auth.donation_recipient_entity_id = donation_recipient_id
            for k, v in card_fields.items():
                setattr(auth, k, v)

        self.db.flush()
        self.db.refresh(auth)
        return auth

    def sync_setup_session(
        self,
        checkout_session_id: str,
        actor_entity: Entity,
        fallback_entity_id: int | None = None,
    ) -> StripeAuthorization | None:
        session = self.stripe_service.retrieve_checkout_session(
            checkout_session_id, expand_setup_intent=True
        )
        session_data = self.stripe_service.normalize_checkout_session(session)
        if session_data.mode == "subscription":
            auth = self._handle_subscription_session_completed(session_data)
            if auth is None:
                raise StripeRequestError(
                    "Stripe subscription session could not be synchronized: "
                    "missing subscription ID, entity metadata, or customer"
                )
            return auth
        auth = self.handle_setup_session_completed(
            session_data, fallback_entity_id=fallback_entity_id
        )
        if auth is None:
            raise StripeRequestError(
                "Stripe setup session could not be synchronized: missing setup intent, "
                "entity metadata, customer, or payment method"
            )
        return auth

    def _handle_subscription_session_completed(
        self,
        session_data: StripeCheckoutSessionData,
    ) -> StripeAuthorization | None:
        subscription_id = session_data.subscription_id
        customer_id = session_data.customer_id
        if not subscription_id or not customer_id:
            return None

        metadata = dict(session_data.metadata)
        entity_id_raw = metadata.get("entity_id")
        if not entity_id_raw:
            return None

        entity_id = int(entity_id_raw)
        mode = StripeAuthorizationMode(str(metadata.get("mode") or "guest_static"))
        static_amount = Decimal(str(metadata.get("static_amount") or "0")).quantize(
            Decimal("0.01")
        )
        static_currency = metadata.get("static_currency")
        if static_currency:
            static_currency = str(static_currency).upper().strip()
        donation_comment = metadata.get("donation_comment") or None
        donation_recipient_id = _metadata_recipient_id(metadata)

        # Retrieve subscription to get the default payment method for card details.
        card_fields: dict = {}
        pm_id: str | None = None
        try:
            sub_raw = self.stripe_service.retrieve_subscription(subscription_id)
            sub_dict = self.stripe_service._as_dict(sub_raw, "subscription")
            pm_id = self.stripe_service._extract_object_id(
                sub_dict.get("default_payment_method")
            )
            if pm_id:
                pm_data = self.stripe_service.normalize_payment_method(
                    self.stripe_service.retrieve_payment_method(pm_id)
                )
                card_fields = dict(
                    card_brand=pm_data.card_brand,
                    card_last4=pm_data.card_last4,
                    card_exp_month=pm_data.card_exp_month,
                    card_exp_year=pm_data.card_exp_year,
                )
        except Exception:
            logger.warning(
                "Could not retrieve subscription payment method details for sub %s",
                subscription_id,
                exc_info=True,
            )

        # stripe_payment_method_id is non-nullable; use a stable synthetic value when
        # the real PM is unavailable (subscription ID is unique enough).
        synthetic_pm_id = pm_id or f"sub_{subscription_id}"

        resolved_amount, resolved_currency = _resolved_static(
            mode, static_amount, static_currency
        )
        now = datetime.datetime.now()

        auth = (
            self.db.query(StripeAuthorization)
            .filter(StripeAuthorization.stripe_subscription_id == subscription_id)
            .first()
        )

        if auth is None:
            auth = StripeAuthorization(
                entity_id=entity_id,
                stripe_customer_id=customer_id,
                stripe_payment_method_id=synthetic_pm_id,
                stripe_subscription_id=subscription_id,
                mode=mode,
                static_amount=resolved_amount,
                static_currency=resolved_currency,
                active=True,
                priority=self._next_priority(entity_id),
                consecutive_error_count=0,
                last_error=None,
                last_success_at=None,
                last_attempt_at=now,
                comment=donation_comment or None,
                donation_recipient_entity_id=donation_recipient_id,
                **card_fields,
            )
            self.db.add(auth)
        else:
            auth.stripe_customer_id = customer_id
            if pm_id:
                auth.stripe_payment_method_id = pm_id
            auth.mode = mode
            auth.static_amount = resolved_amount
            auth.static_currency = resolved_currency
            auth.active = True
            auth.consecutive_error_count = 0
            auth.last_error = None
            auth.modified_at = now
            if donation_comment:
                auth.comment = donation_comment
            if donation_recipient_id is not None:
                auth.donation_recipient_entity_id = donation_recipient_id
            for k, v in card_fields.items():
                setattr(auth, k, v)

        self.db.flush()
        self.db.refresh(auth)
        return auth

    def handle_subscription_invoice_paid(self, invoice: StripeInvoiceData) -> bool:
        """Record a deposit when Stripe successfully charges a subscription invoice.
        Returns True if a new deposit was created, False if skipped."""
        if not invoice.subscription_id:
            logger.warning(
                "invoice.paid skipped: no subscription_id (invoice_id=%r)", invoice.id
            )
            return False

        if not invoice.id or invoice.amount_paid <= 0 or not invoice.currency:
            logger.warning(
                "invoice.paid skipped: missing fields invoice_id=%r amount_paid=%d currency=%r",
                invoice.id,
                invoice.amount_paid,
                invoice.currency,
            )
            return False

        cycle_key = f"invoice:{invoice.id}"
        if self._cycle_exists(cycle_key):
            return False

        auth = (
            self.db.query(StripeAuthorization)
            .filter(
                StripeAuthorization.stripe_subscription_id == invoice.subscription_id
            )
            .first()
        )
        if auth is None:
            logger.warning(
                "invoice.paid for unknown subscription %s (invoice %s) — no auth found",
                invoice.subscription_id,
                invoice.id,
            )
            return False

        amount = (Decimal(str(invoice.amount_paid)) / Decimal("100")).quantize(
            Decimal("0.01")
        )
        deposit = self._create_pending_charge_deposit(
            target_entity_id=auth.entity_id,
            amount=amount,
            currency=invoice.currency,
            details={
                "donation_comment": auth.comment or None,
                "donation_recipient_id": auth.donation_recipient_entity_id,
                "stripe": {
                    "mode": "subscription_invoice",
                    "subscription_id": invoice.subscription_id,
                    "invoice_id": invoice.id,
                    "cycle_key": cycle_key,
                    "billing_reason": invoice.billing_reason,
                    "authorization_id": auth.id,
                },
            },
            comment=cycle_key,
            actor_entity_id=auth.entity_id,
        )
        self._record_charge_success(auth)
        self.deposit_service.complete(deposit.id)
        logger.info(
            "Subscription invoice deposit created: invoice=%s sub=%s amount=%s %s",
            invoice.id,
            invoice.subscription_id,
            amount,
            invoice.currency.upper(),
        )
        return True

    def poll_subscription_invoice_deposits(self) -> int:
        """Recovery poller: fetch recent paid Stripe invoices for each active subscription
        and record any that were missed by the webhook."""
        auths = [
            a
            for a in self._list_active_authorizations(
                mode=StripeAuthorizationMode.GUEST_STATIC
            )
            if a.stripe_subscription_id
        ]
        processed = 0
        for auth in auths:
            try:
                invoices = self.stripe_service.list_invoices_for_subscription(
                    auth.stripe_subscription_id, limit=5
                )
            except StripeRequestError as exc:
                if "no such subscription" in str(exc).lower():
                    logger.warning(
                        "Subscription %s not found in Stripe, disabling authorization %d",
                        auth.stripe_subscription_id,
                        auth.id,
                    )
                    auth.active = False
                    auth.modified_at = datetime.datetime.now()
                    self.db.flush()
                else:
                    logger.warning(
                        "Failed to list invoices for subscription %s",
                        auth.stripe_subscription_id,
                        exc_info=True,
                    )
                continue
            except Exception:
                logger.warning(
                    "Failed to list invoices for subscription %s",
                    auth.stripe_subscription_id,
                    exc_info=True,
                )
                continue
            logger.debug(
                "Subscription %s: %d paid invoice(s) from Stripe",
                auth.stripe_subscription_id,
                len(invoices),
            )
            for invoice in invoices:
                try:
                    if self.handle_subscription_invoice_paid(invoice):
                        processed += 1
                except Exception:
                    logger.exception(
                        "Failed to record deposit for invoice %s (sub %s)",
                        invoice.id,
                        auth.stripe_subscription_id,
                    )
        return processed

    def handle_subscription_deleted(self, subscription_obj) -> None:
        """Deactivate the StripeAuthorization when its Stripe subscription is cancelled."""
        subscription_id = self.stripe_service._extract_object_id(subscription_obj)
        if not subscription_id:
            return
        auth = (
            self.db.query(StripeAuthorization)
            .filter(StripeAuthorization.stripe_subscription_id == subscription_id)
            .first()
        )
        if auth and auth.active:
            auth.active = False
            auth.modified_at = datetime.datetime.now()
            self.db.flush()

    def get_customer_portal_url(
        self,
        checkout_session_id: str,
        return_url: str,
    ) -> str:
        """Create a Stripe Customer Portal session URL for the customer of a checkout session."""
        session = self.stripe_service.retrieve_checkout_session(checkout_session_id)
        session_data = self.stripe_service.normalize_checkout_session(session)
        customer_id = session_data.customer_id
        if not customer_id:
            raise StripeRequestError(
                "No customer associated with this checkout session"
            )
        portal = self.stripe_service.create_billing_portal_session(
            customer_id=customer_id,
            return_url=return_url,
        )
        portal_dict = self.stripe_service._as_dict(portal, "billing portal session")
        url = str(portal_dict.get("url") or "")
        if not url:
            raise StripeRequestError("Stripe did not return a billing portal URL")
        return url

    # ── CRUD ───────────────────────────────────────────────────────────────

    def set_active(
        self, authorization_id: int, actor_entity: Entity, active: bool
    ) -> StripeAuthorization:
        auth = self.get(authorization_id)
        auth.active = active
        if active:
            auth.consecutive_error_count = 0
            auth.last_error = None
        auth.modified_at = datetime.datetime.now()
        self.db.flush()
        self.db.refresh(auth)
        return auth

    def set_priority(
        self, authorization_id: int, actor_entity: Entity, priority: int
    ) -> StripeAuthorization:
        auth = self.get(authorization_id)
        auth.priority = max(int(priority), 1)
        auth.modified_at = datetime.datetime.now()
        self.db.flush()
        self.db.refresh(auth)
        return auth

    def delete(self, authorization_id: int, actor_entity: Entity) -> int:
        auth = self.get(authorization_id)
        try:
            self.stripe_service.detach_payment_method(auth.stripe_payment_method_id)
        except Exception:
            pass  # Best-effort detach; local deletion is authoritative.
        self.db.delete(auth)
        self.db.flush()
        return authorization_id

    # ── Recurring Charges ──────────────────────────────────────────────────

    def run_weekly_entity_dynamic_charges(self) -> int:
        now = datetime.datetime.now()
        week_key = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
        authorizations = self._list_active_authorizations(
            mode=StripeAuthorizationMode.ENTITY_DYNAMIC
        )
        entity_ids = sorted({a.entity_id for a in authorizations})
        if not entity_ids:
            return 0

        eligible = set(self._list_resident_or_member_entity_ids(entity_ids))
        processed = 0
        for entity_id in entity_ids:
            if entity_id not in eligible:
                continue
            try:
                charges = self._compute_entity_dynamic_charges(entity_id)
            except Exception:
                logger.error(
                    "entity_dynamic charge: skipping entity_id=%s due to error",
                    entity_id,
                    exc_info=True,
                )
                continue
            for currency, amount in charges.items():
                if amount > 0 and self._charge_entity_cycle(
                    entity_id, currency, amount, week_key
                ):
                    processed += 1
        return processed

    def preview_weekly_entity_dynamic_charges(self) -> list[dict]:
        authorizations = self._list_active_authorizations(
            mode=StripeAuthorizationMode.ENTITY_DYNAMIC
        )
        return [
            self.debug_entity_dynamic_charge(entity_id)
            for entity_id in sorted({a.entity_id for a in authorizations})
        ]

    def charge_new_guest_static(self, auth: StripeAuthorization) -> bool:
        """Immediately charge a newly subscribed guest_static authorization (first charge)."""
        if auth.stripe_subscription_id:
            # Stripe handles billing automatically for subscription-mode auths.
            return False
        now = datetime.datetime.now()
        day_key = now.strftime("%Y-%m-%d")
        amount = Decimal(auth.static_amount).quantize(Decimal("0.01"))
        currency = (auth.static_currency or "").lower().strip()
        if amount > 0 and currency:
            return self._charge_guest_authorization(auth, amount, currency, day_key)
        return False

    # ── Charge Execution ───────────────────────────────────────────────────

    def charge_on_demand(
        self,
        entity_id: int,
        amount: Decimal,
        currency: str,
    ):
        """Immediately charge the highest-priority active entity_dynamic card."""
        authorizations = self._list_active_authorizations(
            entity_id=entity_id, mode=StripeAuthorizationMode.ENTITY_DYNAMIC
        )
        if not authorizations:
            raise NotFoundError(f"No active Stripe card for entity {entity_id}")

        currency = currency.lower().strip()
        amount = amount.quantize(Decimal("0.01"))

        deposit = self._create_pending_charge_deposit(
            target_entity_id=entity_id,
            amount=amount,
            currency=currency,
            details={
                "stripe": {
                    "mode": "authorization_charge",
                    "charge_mode": "on_demand",
                    "attempts": [],
                }
            },
            comment="on-demand top-up",
        )

        attempts: list[dict] = []
        for auth in authorizations:
            try:
                pi_raw = self.stripe_service.create_off_session_payment_intent(
                    amount=amount,
                    currency=currency,
                    customer_id=auth.stripe_customer_id,
                    payment_method_id=auth.stripe_payment_method_id,
                    idempotency_key=f"ondemand:{deposit.id}:auth:{auth.id}",
                    metadata={
                        "entity_id": str(entity_id),
                        "authorization_id": str(auth.id),
                    },
                )
                pi = self.stripe_service.normalize_payment_intent(pi_raw)
                attempts.append(
                    {
                        "authorization_id": auth.id,
                        "result": "success",
                        "payment_intent_id": pi.id,
                        "status": pi.status,
                    }
                )
                self._record_charge_success(auth)
                self._update_deposit_details(
                    deposit,
                    attempts,
                    extra={
                        "payment_intent_id": pi.id,
                        "payment_intent_status": pi.status,
                        "authorization_id": auth.id,
                    },
                )
                self.deposit_service.complete(deposit.id)
                return self.deposit_service.get(deposit.id)
            except Exception as exc:
                message = str(exc)
                self._record_charge_failure(auth, message)
                attempts.append(
                    {"authorization_id": auth.id, "result": "failed", "error": message}
                )

        self._update_deposit_details(deposit, attempts)
        self.deposit_service.update(
            deposit.id, DepositUpdateSchema(status=DepositStatus.FAILED)
        )
        last_error = next(
            (a["error"] for a in reversed(attempts) if a.get("result") == "failed"),
            None,
        )
        detail = f": {last_error}" if last_error else "."
        raise StripeRequestError(f"All Stripe card attempts failed{detail}")

    def _charge_entity_cycle(
        self,
        entity_id: int,
        currency: str,
        amount: Decimal,
        week_key: str,
    ) -> bool:
        cycle_key = f"entity:{entity_id}:{currency.lower()}:{week_key}"
        if self._cycle_exists(cycle_key):
            return False

        deposit = self._create_pending_charge_deposit(
            target_entity_id=entity_id,
            amount=amount,
            currency=currency,
            details={
                "stripe": {
                    "mode": "authorization_charge",
                    "charge_mode": StripeAuthorizationMode.ENTITY_DYNAMIC.value,
                    "cycle_key": cycle_key,
                    "attempts": [],
                }
            },
            comment=f"weekly authorization charge {cycle_key}",
        )

        authorizations = self._list_active_authorizations(
            entity_id=entity_id, mode=StripeAuthorizationMode.ENTITY_DYNAMIC
        )
        attempts: list[dict] = []

        for auth in authorizations:
            try:
                pi_raw = self.stripe_service.create_off_session_payment_intent(
                    amount=amount,
                    currency=currency,
                    customer_id=auth.stripe_customer_id,
                    payment_method_id=auth.stripe_payment_method_id,
                    idempotency_key=f"{cycle_key}:auth:{auth.id}",
                    metadata={
                        "entity_id": str(entity_id),
                        "authorization_id": str(auth.id),
                        "cycle_key": cycle_key,
                    },
                )
                pi = self.stripe_service.normalize_payment_intent(pi_raw)
                attempts.append(
                    {
                        "authorization_id": auth.id,
                        "result": "success",
                        "payment_intent_id": pi.id,
                        "status": pi.status,
                    }
                )
                self._record_charge_success(auth)
                self._update_deposit_details(
                    deposit,
                    attempts,
                    extra={
                        "payment_intent_id": pi.id,
                        "payment_intent_status": pi.status,
                        "authorization_id": auth.id,
                    },
                )
                self.deposit_service.complete(deposit.id)
                return True
            except Exception as exc:
                message = str(exc)
                self._record_charge_failure(auth, message)
                attempts.append(
                    {"authorization_id": auth.id, "result": "failed", "error": message}
                )

        self._update_deposit_details(deposit, attempts)
        self.deposit_service.update(
            deposit.id, DepositUpdateSchema(status=DepositStatus.FAILED)
        )
        return True

    def _charge_guest_authorization(
        self,
        auth: StripeAuthorization,
        amount: Decimal,
        currency: str,
        day_key: str,
    ) -> bool:
        cycle_key = f"guest:{auth.id}:{currency.lower()}:{day_key}"
        if self._cycle_exists(cycle_key):
            return False

        deposit = self._create_pending_charge_deposit(
            target_entity_id=auth.entity_id,
            amount=amount,
            currency=currency,
            details={
                "donation_comment": auth.comment or None,
                "donation_recipient_id": auth.donation_recipient_entity_id,
                "stripe": {
                    "mode": "authorization_charge",
                    "charge_mode": StripeAuthorizationMode.GUEST_STATIC.value,
                    "cycle_key": cycle_key,
                    "attempts": [],
                    "authorization_id": auth.id,
                },
            },
            comment=f"monthly guest static charge {cycle_key}",
            actor_entity_id=auth.entity_id,
        )

        try:
            pi_raw = self.stripe_service.create_off_session_payment_intent(
                amount=amount,
                currency=currency,
                customer_id=auth.stripe_customer_id,
                payment_method_id=auth.stripe_payment_method_id,
                idempotency_key=f"{cycle_key}:auth:{auth.id}",
                metadata={
                    "entity_id": str(auth.entity_id),
                    "authorization_id": str(auth.id),
                    "cycle_key": cycle_key,
                },
            )
            pi = self.stripe_service.normalize_payment_intent(pi_raw)
            self._record_charge_success(auth)
            self._update_deposit_details(
                deposit,
                [
                    {
                        "authorization_id": auth.id,
                        "result": "success",
                        "payment_intent_id": pi.id,
                        "status": pi.status,
                    }
                ],
            )
            self.deposit_service.complete(deposit.id)
        except Exception as exc:
            self._record_charge_failure(auth, str(exc))
            self._update_deposit_details(
                deposit,
                [
                    {
                        "authorization_id": auth.id,
                        "result": "failed",
                        "error": str(exc),
                    }
                ],
            )
            self.deposit_service.update(
                deposit.id, DepositUpdateSchema(status=DepositStatus.FAILED)
            )
        return True

    def _update_deposit_details(
        self,
        deposit,
        attempts: list[dict],
        *,
        extra: dict | None = None,
    ) -> None:
        details = dict(deposit.details or {})
        stripe_details = dict(details.get("stripe") or {})
        stripe_details["attempts"] = attempts
        if extra:
            stripe_details.update(extra)
        details["stripe"] = stripe_details
        self.deposit_service.update(deposit.id, DepositUpdateSchema(details=details))

    # ── Deposit Factory ────────────────────────────────────────────────────

    def _create_pending_charge_deposit(
        self,
        *,
        target_entity_id: int,
        amount: Decimal,
        currency: str,
        details: dict,
        comment: str,
        actor_entity_id: int | None = None,
    ):
        return self.deposit_service.create(
            DepositCreateSchema(
                from_entity_id=stripe_deposit_provider.id,
                to_entity_id=target_entity_id,
                amount=amount,
                currency=currency,
                provider="stripe",
                details=details,
                to_treasury_id=stripe_treasury.id,
                tag_ids=[automatic_tag.id],
                comment=comment,
            ),
            overrides={"actor_entity_id": actor_entity_id or target_entity_id},
        )

    # ── Auth Record Tracking ───────────────────────────────────────────────

    def _record_charge_failure(self, auth: StripeAuthorization, message: str) -> None:
        now = datetime.datetime.now()
        auth.consecutive_error_count = int(auth.consecutive_error_count or 0) + 1
        auth.last_error = message[:1000]
        auth.last_attempt_at = now
        auth.modified_at = now
        if auth.consecutive_error_count >= max(
            int(self.config.stripe_authorization_max_consecutive_errors), 1
        ):
            auth.active = False
        self.db.flush()

    def _record_charge_success(self, auth: StripeAuthorization) -> None:
        now = datetime.datetime.now()
        auth.consecutive_error_count = 0
        auth.last_error = None
        auth.last_attempt_at = now
        auth.last_success_at = now
        auth.active = True
        auth.modified_at = now
        self.db.flush()

    # ── Charge Calculation ─────────────────────────────────────────────────

    def _compute_entity_dynamic_charges(self, entity_id: int) -> dict[str, Decimal]:
        summary = self._calculate_entity_owed_summary(entity_id)
        if not summary.minimum_topup_currency or not summary.minimum_topup_amount:
            return {}
        return {
            summary.minimum_topup_currency: summary.minimum_topup_amount.quantize(
                Decimal("0.01")
            )
        }

    def debug_entity_dynamic_charge(self, entity_id: int) -> dict:
        now = datetime.datetime.now()
        week_key = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"

        authorizations = self._list_active_authorizations(
            entity_id=entity_id, mode=StripeAuthorizationMode.ENTITY_DYNAMIC
        )
        has_active_authorization = bool(authorizations)
        eligible_entity = (
            entity_id in set(self._list_resident_or_member_entity_ids([entity_id]))
            if has_active_authorization
            else False
        )

        summary = self._calculate_entity_owed_summary(entity_id)
        minimum_currency = summary.minimum_topup_currency
        minimum_amount = summary.minimum_topup_amount

        cycle_key = None
        cycle_already_exists = False
        if minimum_currency and minimum_amount and minimum_amount > 0:
            cycle_key = f"entity:{entity_id}:{minimum_currency.lower()}:{week_key}"
            cycle_already_exists = self._cycle_exists(cycle_key)

        will_charge = (
            has_active_authorization
            and eligible_entity
            and minimum_currency is not None
            and minimum_amount is not None
            and minimum_amount > 0
            and not cycle_already_exists
        )

        if not has_active_authorization:
            reason = "No active entity_dynamic Stripe authorizations"
        elif not eligible_entity:
            reason = "Entity must be active and tagged resident/member"
        elif minimum_currency is None or minimum_amount is None or minimum_amount <= 0:
            reason = "No net owed amount after invoices and balances are offset"
        elif cycle_already_exists:
            reason = "Charge for this entity/currency/week already exists"
        else:
            reason = "Entity is chargeable"

        return {
            "entity_id": entity_id,
            "active_authorization_ids": [a.id for a in authorizations],
            "has_active_authorization": has_active_authorization,
            "eligible_entity": eligible_entity,
            "week_key": week_key,
            "owed_by_currency": {
                c: str(a.quantize(Decimal("0.01")))
                for c, a in sorted(summary.owed_by_currency.items())
            },
            "total_owed_usd": str(summary.total_owed_usd.quantize(Decimal("0.01"))),
            "available_credit_usd": str(
                summary.available_credit_usd.quantize(Decimal("0.01"))
            ),
            "net_owed_usd": str(summary.net_owed_usd.quantize(Decimal("0.01"))),
            "minimum_topup_currency": minimum_currency,
            "minimum_topup_amount": (
                str(minimum_amount.quantize(Decimal("0.01")))
                if minimum_amount is not None
                else None
            ),
            "cycle_key": cycle_key,
            "cycle_already_exists": cycle_already_exists,
            "will_charge": will_charge,
            "reason": reason,
        }

    # ── Financial Helpers ──────────────────────────────────────────────────

    def _calculate_entity_owed_summary(self, entity_id: int) -> EntityOwedSummary:
        pending_invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.from_entity_id == entity_id,
                Invoice.status == InvoiceStatus.PENDING,
            )
            .all()
        )
        invoice_list: list[dict[str, Decimal]] = []
        for inv in pending_invoices:
            options = invoice_currency_options(inv)
            if options:
                invoice_list.append(options)

        balances = self.balance_service.get_balances(entity_id)
        completed_totals: dict[str, Decimal] = {
            str(c or "").lower().strip(): Decimal(str(a or "0"))
            for c, a in (balances.completed or {}).items()
            if str(c or "").strip()
        }

        return calculate_entity_owed(
            pending_invoices=invoice_list,
            completed_balances=completed_totals,
            convert_amount=self._convert_amount,
        )

    def _convert_amount(
        self, amount: Decimal, source_currency: str, target_currency: str
    ) -> Decimal:
        source = str(source_currency or "").lower().strip()
        target = str(target_currency or "").lower().strip()
        decimal_amount = Decimal(str(amount or "0"))
        if decimal_amount == 0:
            return Decimal("0")
        if source == target:
            return decimal_amount
        try:
            _, target_amount, _ = self.currency_exchange_service.calculate_conversion(
                source_amount=decimal_amount,
                target_amount=None,
                source_currency=source,
                target_currency=target,
            )
            return Decimal(str(target_amount))
        except Exception:
            logger.error(
                "Currency conversion failed: %s %s -> %s",
                decimal_amount,
                source,
                target,
                exc_info=True,
            )
            raise

    # ── DB Helpers ─────────────────────────────────────────────────────────

    def _list_active_authorizations(
        self,
        *,
        entity_id: int | None = None,
        mode: StripeAuthorizationMode | None = None,
    ) -> list[StripeAuthorization]:
        query = self.db.query(StripeAuthorization).filter(
            StripeAuthorization.active.is_(True)
        )
        if entity_id is not None:
            query = query.filter(StripeAuthorization.entity_id == entity_id)
        if mode is not None:
            query = query.filter(StripeAuthorization.mode == mode)
        return query.order_by(
            StripeAuthorization.priority.asc(), StripeAuthorization.id.asc()
        ).all()

    def _list_resident_or_member_entity_ids(self, entity_ids: list[int]) -> list[int]:
        rows = (
            self.db.query(Entity.id)
            .filter(Entity.id.in_(entity_ids), Entity.active.is_(True))
            .filter(
                or_(
                    Entity.tags.any(id=resident_tag.id),
                    Entity.tags.any(id=member_tag.id),
                )
            )
            .all()
        )
        return [row[0] for row in rows]

    def _cycle_exists(self, cycle_key: str) -> bool:
        return bool(
            self.deposit_service.get_all(
                DepositFiltersSchema(provider="stripe", comment=cycle_key, tags_ids=[]),
                skip=0,
                limit=1,
            ).items
        )

    def _next_priority(self, entity_id: int) -> int:
        row = (
            self.db.query(StripeAuthorization.priority)
            .filter(StripeAuthorization.entity_id == entity_id)
            .order_by(
                StripeAuthorization.priority.desc(), StripeAuthorization.id.desc()
            )
            .first()
        )
        return int(row[0]) + 1 if row else 1

    # ── URL Helpers ────────────────────────────────────────────────────────

    def _resolve_setup_success_url(self, override: str | None, entity_id: int) -> str:
        if override:
            return self._with_checkout_session_placeholder(override)
        if self.config.stripe_success_url:
            return self._with_checkout_session_placeholder(
                self.config.stripe_success_url
            )
        base = (self.config.ui_url or "").rstrip("/")
        if not base:
            return "https://example.com"
        return (
            f"{base}/deposits/stripe/authorizations"
            f"?entity_id={entity_id}&stripe_session_id={{CHECKOUT_SESSION_ID}}"
        )

    def _resolve_setup_cancel_url(self, override: str | None, entity_id: int) -> str:
        if override:
            return override
        if self.config.stripe_cancel_url:
            return self.config.stripe_cancel_url
        base = (self.config.ui_url or "").rstrip("/")
        return (
            f"{base}/deposits/stripe/authorizations?entity_id={entity_id}"
            if base
            else "https://example.com"
        )

    @staticmethod
    def _with_checkout_session_placeholder(url: str) -> str:
        if "{CHECKOUT_SESSION_ID}" in url or "stripe_session_id=" in url:
            return url
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}stripe_session_id={{CHECKOUT_SESSION_ID}}"
