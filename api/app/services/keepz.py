"""Keepz API client and auth management."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.config import Config, get_config
from app.errors.common import NotFoundError
from app.errors.keepz import KeepzAuthFailed, KeepzAuthRequired
from app.libs.keepz_cli import keepz_api
from app.models.entity import Entity
from app.seeding import keepz_deposit_provider
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session


def _load_bundle(auth: dict[str, Any] | None) -> Any | None:
    data = (auth or {}).get("keepz") or {}
    bundle_data = data.get("bundle")
    if bundle_data is None and "access_token" in data:
        bundle_data = data
    if isinstance(bundle_data, dict):
        return keepz_api.TokenBundle.from_json(bundle_data)
    return None


def _save_bundle(
    auth: dict[str, Any] | None, bundle: Any, payload: dict[str, Any]
) -> dict[str, Any]:
    auth = auth or {}
    auth["keepz"] = {**payload, "bundle": bundle.to_json()}
    return auth


class KeepzService:
    def __init__(
        self,
        db: Session = Depends(get_uow),
        config: Config = Depends(get_config),
    ) -> None:
        self.db = db
        self.config = config

    def _get_provider_entity(self) -> Entity:
        entity = (
            self.db.query(Entity).filter(Entity.id == keepz_deposit_provider.id).first()
        )
        if not entity:
            raise NotFoundError("Keepz deposit provider entity missing")
        return entity

    def _get_bundle(self) -> Any | None:
        entity = self._get_provider_entity()
        return _load_bundle(entity.auth)

    def _save_auth_payload(self, bundle: Any, payload: dict[str, Any]) -> None:
        entity = self._get_provider_entity()
        entity.auth = _save_bundle(entity.auth, bundle, payload)
        self.db.flush()
        self.db.refresh(entity)

    def _client(self) -> Any:
        return keepz_api.KeepzClient(
            base_url=self.config.keepz_base_url or keepz_api.DEFAULT_BASE_URL,
            user_agent=self.config.keepz_user_agent or keepz_api.DEFAULT_USER_AGENT,
        )

    def auth_status(self) -> dict[str, Any]:
        bundle = self._get_bundle()
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
        client.auth_check(phone=phone, country_code=country_code)
        client.send_sms(phone=phone, country_code=country_code)

    def login_with_sms(
        self,
        *,
        phone: str,
        country_code: str,
        code: str,
        user_type: str,
        device_token: str,
        mobile_name: str,
        mobile_os: str,
    ) -> dict[str, Any]:
        client = self._client()
        user_sms_id = client.verify_sms(
            code=code, phone=phone, country_code=country_code
        )
        login_payload = client.login(
            user_sms_id=user_sms_id,
            device_token=device_token,
            mobile_name=mobile_name,
            mobile_os=mobile_os,
            mobile_number=f"{country_code}{phone}",
            user_type=user_type,
        )
        if not isinstance(login_payload, dict) or not login_payload.get("access_token"):
            raise KeepzAuthFailed

        client.set_access_token(str(login_payload.get("access_token")))
        profile = client.profile_details()
        user_id = None
        if isinstance(profile, dict):
            user_id = profile.get("userId")

        bundle = keepz_api.TokenBundle.from_login_payload(
            login_payload, user_id=user_id
        )
        self._save_auth_payload(
            bundle,
            {
                "phone": phone,
                "country_code": country_code,
                "user_type": user_type,
                "device_token": device_token,
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

    def _refresh_bundle(self, bundle: Any, payload: dict[str, Any]) -> Any:
        if not bundle or not bundle.refresh_token:
            raise KeepzAuthRequired
        client = self._client()
        refreshed = client.refresh_login(bundle)
        if not refreshed or not refreshed.access_token:
            raise KeepzAuthFailed
        self._save_auth_payload(refreshed, payload)
        return refreshed

    def _call_with_refresh(self, action: Any) -> Any:
        entity = self._get_provider_entity()
        payload = (entity.auth or {}).get("keepz") or {}
        bundle = _load_bundle(entity.auth)
        if not bundle or not bundle.access_token:
            raise KeepzAuthRequired
        if bundle.is_access_token_expired():
            bundle = self._refresh_bundle(bundle, payload)

        client = self._client()
        client.set_access_token(bundle.access_token or "")
        try:
            return action(client)
        except Exception as exc:
            if isinstance(exc, keepz_api.KeepzApiError) and "status 401" in str(exc):
                refreshed = self._refresh_bundle(bundle, payload)
                client.set_access_token(refreshed.access_token or "")
                return action(client)
            raise

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

    def list_transactions(self) -> Any:
        return self._call_with_refresh(lambda client: client.list_transactions())

    def get_transaction(self, transaction_id: int) -> Any:
        return self._call_with_refresh(
            lambda client: client.get_transaction(transaction_id)
        )

    def resolve_payment_url(self, short_url: str) -> str:
        client = self._client()
        return client.resolve_payment_url(short_url)
