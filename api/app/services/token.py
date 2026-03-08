"""Token service. Generates a token and sends it to Telegram. Verifies generated tokens."""

import hashlib
import hmac
import json
import logging
import time
from datetime import timedelta

import jwt
import requests
from app.config import Config, get_config
from app.dependencies.services import get_entity_service
from app.errors.common import NotFoundError
from app.errors.token import TokenInvalid
from app.models.entity import Entity
from app.schemas.entity import EntityUpdateSchema
from app.schemas.token import (
    TelegramAuthConfigResponseSchema,
    TelegramAuthPayloadSchema,
    TelegramLoginResponseSchema,
    TokenSendReportSchema,
)
from app.services.entity import EntityService
from app.uow import get_uow
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TokenService:
    ALGORITHM = "HS256"
    TELEGRAM_AUTH_MAX_AGE_SECONDS = int(timedelta(hours=24).total_seconds())

    @staticmethod
    def decode_entity_id_from_token(token: str, secret_key: str) -> int:
        """Decode entity id from token without DB lookup."""
        try:
            payload = jwt.decode(token, secret_key, algorithms=[TokenService.ALGORITHM])
            return int(payload.get("sub") or 0)
        except Exception:
            raise TokenInvalid

    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(get_entity_service),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.entity_service = entity_service
        self.config = config

    def _generate_new_token(self, entity_id: int) -> str:
        """Generate a new signed token with entity_id and current timestamp."""
        data = {
            "sub": str(entity_id),
            "iat": int(time.time()),
            "exp": int(time.time() + timedelta(weeks=4).total_seconds()),
        }
        encoded_jwt = jwt.encode(data, self.config.secret_key, algorithm=self.ALGORITHM)
        return encoded_jwt

    def generate_new_token(self, entity_id: int) -> str:
        return self._generate_new_token(entity_id)

    def get_entity_from_token(self, token: str) -> Entity:
        """Verify the token, decode the entity id, then retrieve the associated entity via DB."""
        # Decode entity id and then load entity from DB
        entity_id = TokenService.decode_entity_id_from_token(
            token, self.config.secret_key or ""
        )
        return self.entity_service.get(entity_id)

    def _verify_telegram_auth(self, payload: TelegramAuthPayloadSchema) -> int:
        bot_token = (self.config.telegram_bot_api_token or "").strip()
        if not bot_token:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Telegram login is not configured.",
            )

        now = int(time.time())
        if payload.auth_date > now + 60:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Telegram auth timestamp is invalid.",
            )
        if now - payload.auth_date > self.TELEGRAM_AUTH_MAX_AGE_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Telegram auth payload has expired.",
            )

        secret_key = hashlib.sha256(bot_token.encode("utf-8")).digest()
        payload_data = payload.model_dump(exclude_none=True)
        provided_hash = payload_data.pop("hash", "")
        payload_data.pop("link_to_current_entity", None)
        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(payload_data.items())
        )
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(expected_hash, provided_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Telegram auth signature is invalid.",
            )

        return int(payload.id)

    def login_or_link_with_telegram(
        self,
        payload: TelegramAuthPayloadSchema,
        actor_entity: Entity | None = None,
    ) -> TelegramLoginResponseSchema:
        telegram_id = self._verify_telegram_auth(payload)

        if payload.link_to_current_entity:
            if actor_entity is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Log in first to connect Telegram.",
                )

            try:
                existing_entity = self.entity_service.get_by_telegram_id(telegram_id)
            except NotFoundError:
                existing_entity = None

            if existing_entity is not None and existing_entity.id != actor_entity.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This Telegram account is already linked to another entity.",
                )

            linked_entity = self.entity_service.update(
                actor_entity.id,
                EntityUpdateSchema(auth={"telegram_id": telegram_id}),
            )
            return TelegramLoginResponseSchema(
                token=self._generate_new_token(linked_entity.id),
                entity_id=linked_entity.id,
                linked=True,
            )

        try:
            entity = self.entity_service.get_by_telegram_id(telegram_id)
        except NotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Telegram account is not linked yet. "
                    "Sign in by username once and connect Telegram in Profile."
                ),
            ) from exc

        return TelegramLoginResponseSchema(
            token=self._generate_new_token(entity.id),
            entity_id=entity.id,
            linked=False,
        )

    def get_telegram_auth_config(self) -> TelegramAuthConfigResponseSchema:
        bot_username = (self.config.telegram_bot_username or "").strip() or None
        bot_token = (self.config.telegram_bot_api_token or "").strip()

        if not bot_username:
            return TelegramAuthConfigResponseSchema(
                enabled=False,
                bot_username=None,
                reason="missing_bot_username",
            )

        if not bot_token:
            return TelegramAuthConfigResponseSchema(
                enabled=False,
                bot_username=bot_username,
                reason="missing_bot_token",
            )

        return TelegramAuthConfigResponseSchema(
            enabled=True,
            bot_username=bot_username,
            reason=None,
        )

    def generate_and_send_new_token(self, entity_name: str) -> TokenSendReportSchema:
        """Generate a token for entity by name and send it via Telegram."""
        try:
            # Find entity by name
            entity = self.entity_service.get_by_name(entity_name)
            entity_found = True

            # Generate token
            token = self._generate_new_token(entity.id)
            token_generated = True

            # Try to send via Telegram if telegram_id exists
            message_sent = False
            if entity.auth and entity.auth.get("telegram_id"):
                try:
                    telegram_id_raw = entity.auth.get("telegram_id")
                    # Convert to int if it's a string
                    if isinstance(telegram_id_raw, str):
                        telegram_id = int(telegram_id_raw)
                    elif isinstance(telegram_id_raw, int):
                        telegram_id = telegram_id_raw
                    else:
                        raise ValueError(
                            f"Invalid telegram_id type: {type(telegram_id_raw)}"
                        )

                    message_sent = self._send_telegram_message(
                        telegram_id, token, entity
                    )
                except Exception as e:
                    telegram_id_str = str(entity.auth.get("telegram_id", "unknown"))
                    logger.error(
                        f"Failed to send Telegram message to {telegram_id_str}: {e}"
                    )
                    message_sent = False

            return TokenSendReportSchema(
                entity_found=entity_found,
                token_generated=token_generated,
                message_sent=message_sent,
            )

        except Exception:
            return TokenSendReportSchema(
                entity_found=False, token_generated=False, message_sent=False
            )

    def _send_telegram_message(
        self, telegram_id: int, token: str, entity: Entity
    ) -> bool:
        """Send a login token to a Telegram user."""
        if not self.config.telegram_bot_api_token:
            logger.warning("TokenService: Telegram bot token not configured")
            return False

        if not self.config.ui_url:
            logger.warning("TokenService: UI URL not configured")
            return False

        # Build the login link message
        login_link = f"{self.config.ui_url}/auth/token/{token}"

        # Try to send with inline keyboard first
        try:
            data = {
                "chat_id": telegram_id,
                "text": f"refinance login: <b>{entity.name}</b>",
                "reply_markup": json.dumps(
                    {
                        "inline_keyboard": [
                            [
                                {
                                    "text": f"Login as {entity.name}",
                                    "url": login_link,
                                }
                            ]
                        ]
                    }
                ),
                "parse_mode": "HTML",
            }

            response = requests.post(
                f"https://api.telegram.org/bot{self.config.telegram_bot_api_token}/sendMessage",
                data=data,
                timeout=5,
            )
            if response.status_code == 200:
                logger.info(
                    f"TokenService: Telegram message sent successfully to {telegram_id}"
                )
                return True
            else:
                logger.error(
                    "TokenService: telegram sendMessage failed status=%s body=%s",
                    response.status_code,
                    response.text,
                )

                # Fallback to simple text message
                fallback_response = requests.post(
                    f"https://api.telegram.org/bot{self.config.telegram_bot_api_token}/sendMessage",
                    data={
                        "chat_id": telegram_id,
                        "text": f"Login as {entity.name}: {login_link}",
                    },
                    timeout=5,
                )
                if fallback_response.status_code == 200:
                    logger.info(
                        f"TokenService: Fallback Telegram message sent successfully to {telegram_id}"
                    )
                    return True
                else:
                    logger.error(
                        "TokenService: fallback telegram sendMessage failed status=%s body=%s",
                        fallback_response.status_code,
                        fallback_response.text,
                    )
                    return False

        except Exception as e:
            logger.error(
                f"TokenService: Exception sending Telegram message to {telegram_id}: {e}"
            )
            return False
