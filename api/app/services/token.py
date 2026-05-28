"""Token service. Generates a token and sends it via all available channels. Verifies generated tokens."""

import hashlib
import hmac as hmac_lib
import json
import logging
import time
from datetime import datetime, timedelta, timezone

import jwt
from app.config import Config, get_config
from app.dependencies.services import get_entity_service, get_notification_service
from app.errors.token import TelegramAuthInvalid, TokenInvalid
from app.models.entity import Entity
from app.schemas.token import TelegramAuthSchema, TokenSendReportSchema
from app.services.entity import EntityService
from app.services.notification import NotificationService
from app.uow import get_uow
from fastapi import Depends
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TokenService:
    ALGORITHM = "HS256"

    @staticmethod
    def decode_entity_id_from_token(token: str, secret_key: str) -> int:
        """Decode entity id from token without DB lookup."""
        try:
            payload = jwt.decode(token, secret_key, algorithms=[TokenService.ALGORITHM])
            return int(payload.get("sub") or 0)
        except Exception as e:
            raise TokenInvalid

    def __init__(
        self,
        db: Session = Depends(get_uow),
        entity_service: EntityService = Depends(get_entity_service),
        notification_service: NotificationService = Depends(get_notification_service),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.entity_service = entity_service
        self.notification_service = notification_service
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

    def get_entity_from_token(self, token: str) -> Entity:
        """Verify the token, decode the entity id, then retrieve the associated entity via DB."""
        # Decode entity id and then load entity from DB
        entity_id = TokenService.decode_entity_id_from_token(
            token, self.config.secret_key or ""
        )
        return self.entity_service.get(entity_id)

    def generate_and_send_new_token(self, entity_name: str) -> TokenSendReportSchema:
        """Generate a token for entity by name and send it via all available channels."""
        try:
            entity = self.entity_service.get_by_name(entity_name)
            entity_found = True

            token = self._generate_new_token(entity.id)
            token_generated = True

            message_sent = False
            if entity.auth:
                if not self.config.ui_url:
                    logger.warning("TokenService: UI URL not configured")
                else:
                    login_link = f"{self.config.ui_url}/auth/token/{token}"
                    reply_markup = json.dumps(
                        {
                            "inline_keyboard": [
                                [{"text": f"Login as {entity.name}", "url": login_link}]
                            ]
                        }
                    )
                    results = self.notification_service.send(
                        entity,
                        f"refinance login: <b>{entity.name}</b>",
                        telegram_reply_markup=reply_markup,
                    )
                    message_sent = any(results.values())

            return TokenSendReportSchema(
                entity_found=entity_found,
                token_generated=token_generated,
                message_sent=message_sent,
            )

        except Exception:
            return TokenSendReportSchema(
                entity_found=False, token_generated=False, message_sent=False
            )

    def login_via_telegram(self, auth_data: TelegramAuthSchema) -> str:
        """Verify Telegram Login Widget data, find entity by telegram_id, return a JWT."""
        if not self.config.telegram_bot_api_token:
            raise TelegramAuthInvalid()

        # Build the data-check string: sorted key=value pairs (excluding hash), joined by \n
        fields = auth_data.model_dump(exclude_none=True)
        check_hash = fields.pop("hash")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))

        secret_key = hashlib.sha256(
            self.config.telegram_bot_api_token.encode()
        ).digest()
        computed_hash = hmac_lib.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac_lib.compare_digest(computed_hash, check_hash):
            raise TelegramAuthInvalid()

        if time.time() - auth_data.auth_date > 86400:
            raise TelegramAuthInvalid()

        entity = self.entity_service.get_by_telegram_id(auth_data.id)
        return self._generate_new_token(entity.id)
