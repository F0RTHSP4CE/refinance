"""Token service. Generates a token and sends it to Telegram. Verifies generated tokens."""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import jwt
import requests
from app.config import Config, get_config
from app.dependencies.services import get_entity_service
from app.errors.token import TokenInvalid
from app.models.entity import Entity
from app.schemas.token import TokenSendReportSchema
from app.services.entity import EntityService
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

    def get_entity_from_token(self, token: str) -> Entity:
        """Verify the token, decode the entity id, then retrieve the associated entity via DB."""
        # Decode entity id and then load entity from DB
        entity_id = TokenService.decode_entity_id_from_token(
            token, self.config.secret_key or ""
        )
        return self.entity_service.get(entity_id)

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
