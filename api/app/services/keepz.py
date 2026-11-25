"""Keepz API client and auth management."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.config import Config, get_config
from app.errors.common import NotFoundError
from app.errors.keepz import KeepzAuthFailed, KeepzAuthRequired
from app.libs.keepz_cli import keepz_api
from app.models.entity import Entity
from app.seeding import keepz_deposit_provider
from app.uow import get_uow
from fastapi import Depends
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session


def _load_bundle(auth: dict[str, Any] | None) -> keepz_api.TokenBundle | None:
    data = (auth or {}).get("keepz") or {}
    bundle_data = data.get("bundle")
    if bundle_data is None and "access_token" in data:
        bundle_data = data
    if isinstance(bundle_data, dict):
        return keepz_api.TokenBundle.from_json(bundle_data)
    return None


def _save_bundle(
    auth: dict[str, Any] | None,
    bundle: keepz_api.TokenBundle,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {**(auth or {}), "keepz": {**payload, "bundle": bundle.to_json()}}


class KeepzService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        config: Config = Depends(get_config),
    ) -> None:
        self.db = db
        self.config = config

    @staticmethod
    def _get_provider_entity(db: Session, *, lock: bool = False) -> Entity:
        query = db.query(Entity).filter(Entity.id == keepz_deposit_provider.id)
        if lock:
            query = query.with_for_update()
        entity = query.populate_existing().first()
        if not entity:
            raise NotFoundError("Keepz deposit provider entity missing")
        return entity

    def _client(self) -> keepz_api.KeepzClient:
        return keepz_api.KeepzClient(
            base_url=self.config.keepz_base_url or keepz_api.DEFAULT_BASE_URL,
            user_agent=self.config.keepz_user_agent or keepz_api.DEFAULT_USER_AGENT,
        )

    def auth_status(self) -> dict[str, Any]:
        bundle = _load_bundle(self._get_provider_entity(self.db).auth)
        authenticated = bool(bundle and bundle.access_token)
        expired = bundle.is_access_token_expired() if bundle else True
        return {
            "authenticated": bool(authenticated and not expired),
            "user_id": bundle.user_id if bundle else None,
            "obtained_at": bundle.obtained_at if bundle else None,
            "expires_in": bundle.expires_in if bundle else None,
        }

    def send_sms(self, phone: str, country_code: str) -> None:
        client = self._client()
        phone, country_code = phone.strip(), country_code.strip().removeprefix("+")
        try:
            client.auth_check(phone=phone, country_code=country_code)
            client.send_sms(phone=phone, country_code=country_code)
        except keepz_api.KeepzApiError as exc:
            raise KeepzAuthFailed from exc

    def login_with_sms(
        self,
        *,
        phone: str,
        country_code: str,
        code: str,
        user_type: str,
        mobile_name: str,
        mobile_os: str,
    ) -> dict[str, Any]:
        client = self._client()
        phone, country_code = phone.strip(), country_code.strip().removeprefix("+")
        try:
            user_sms_id = client.verify_sms(
                code=code.strip(), phone=phone, country_code=country_code
            )
            if not user_sms_id:
                raise KeepzAuthFailed
            login_payload = client.login(
                user_sms_id=user_sms_id,
                device_token=keepz_api.generate_device_token(),
                mobile_name=mobile_name,
                mobile_os=mobile_os,
                mobile_number=f"{country_code}{phone}",
                user_type=user_type,
            )
            if isinstance(login_payload, BaseModel):
                login_payload = login_payload.model_dump()
            if not isinstance(login_payload, dict) or not login_payload.get(
                "access_token"
            ):
                raise KeepzAuthFailed

            client.set_access_token(login_payload["access_token"])
            profile = client.profile_details()
            if isinstance(profile, BaseModel):
                profile = profile.model_dump()
            user_id = profile.get("userId") if isinstance(profile, dict) else None
            bundle = keepz_api.TokenBundle.from_login_payload(
                login_payload, user_id=user_id
            )
        except (keepz_api.KeepzApiError, ValidationError) as exc:
            raise KeepzAuthFailed from exc

        entity = self._get_provider_entity(self.db, lock=True)
        entity.auth = _save_bundle(
            entity.auth,
            bundle,
            {
                "phone": phone,
                "country_code": country_code,
                "user_type": user_type,
                "mobile_name": mobile_name,
                "mobile_os": mobile_os,
            },
        )
        return {
            "authenticated": True,
            "user_id": bundle.user_id,
            "obtained_at": bundle.obtained_at,
            "expires_in": bundle.expires_in,
        }

    def _refresh_bundle(self, stale: keepz_api.TokenBundle) -> keepz_api.TokenBundle:
        # A rotated refresh token must survive a rollback of the deposit operation.
        with Session(bind=self.db.get_bind()) as db, db.begin():
            entity = self._get_provider_entity(db, lock=True)
            bundle = _load_bundle(entity.auth)
            if not bundle:
                raise KeepzAuthRequired
            if bundle != stale and not bundle.is_access_token_expired():
                return bundle
            if not bundle.refresh_token:
                raise KeepzAuthRequired

            try:
                refreshed = self._client().refresh_login(bundle)
            except (
                keepz_api.KeepzApiError,
                ValidationError,
                KeyError,
                TypeError,
            ) as exc:
                raise KeepzAuthFailed from exc
            if not refreshed.access_token:
                raise KeepzAuthFailed
            if not refreshed.refresh_token:
                refreshed.refresh_token = bundle.refresh_token
            payload = (entity.auth or {}).get("keepz") or {}
            entity.auth = _save_bundle(entity.auth, refreshed, payload)
            return refreshed

    def _call_with_refresh[T](self, action: Callable[[keepz_api.KeepzClient], T]) -> T:
        bundle = _load_bundle(self._get_provider_entity(self.db).auth)
        if not bundle or not bundle.access_token:
            raise KeepzAuthRequired
        if bundle.is_access_token_expired():
            bundle = self._refresh_bundle(bundle)

        client = self._client()
        client.set_access_token(bundle.access_token)
        try:
            return action(client)
        except keepz_api.KeepzApiError as exc:
            if exc.status_code != 401:
                raise
            refreshed = self._refresh_bundle(bundle)
            client.set_access_token(refreshed.access_token)
            return action(client)

    def create_payment_link(
        self,
        *,
        amount: float,
        currency: str,
        commission_type: str,
        note: str | None,
    ) -> Any:
        return self._call_with_refresh(
            lambda client: client.create_payment_link(
                amount=amount,
                currency=currency,
                commission_type=commission_type,
                note=note,
            )
        )

    def list_transactions(self) -> list[keepz_api.Transaction]:
        response = self._call_with_refresh(lambda client: client.list_transactions())
        if response is None:
            return []
        page = keepz_api.TransactionsResponse.model_validate(response).transactionsPage
        return (page.content or []) if page else []

    def get_transaction(self, transaction_id: int) -> keepz_api.Transaction | None:
        try:
            response = self._call_with_refresh(
                lambda client: client.get_transaction(transaction_id)
            )
        except keepz_api.KeepzApiError as exc:
            if exc.status_code != 404:
                raise
            return None
        if response is None:
            return None
        return keepz_api.Transaction.model_validate(response)

    def resolve_payment_url(self, short_url: str) -> str:
        client = self._client()
        return client.resolve_payment_url(short_url)
