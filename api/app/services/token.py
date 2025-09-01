"""Token service. Generates a token and sends it to Telegram. Verifies generated tokens."""

import json
import logging
import time
from datetime import datetime, timedelta, timezone

import jwt
import requests
from app.config import Config, get_config
from app.errors.common import NotFoundError
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
        entity_service: EntityService = Depends(),
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

    def generate_and_send_new_token(
        self,
        entity_id: int | None = None,
        entity_name: str | None = None,
        entity_telegram_id: int | None = None,
    ) -> TokenSendReportSchema:
        """
        Generate a new signed token and send it to all available auth providers for the entity.

        Search is performed using the following criteria (in order):
          - Primary entity_id
          - Telegram ID, Signal ID, WhatsApp Number, Email
          - Entity name

        Once the entity is found, a login link is generated and sent via all providers
        found in the entity's JSON `auth` field.
        """
        # Log input received for tracing
        logger.info(
            "TokenService.generate_and_send_new_token inputs: entity_id=%s, entity_name=%s, entity_telegram_id=%s",
            entity_id,
            entity_name,
            entity_telegram_id,
        )

        # Create an empty report for tracking progress
        report = TokenSendReportSchema(
            entity_found=False, token_generated=False, message_sent=False
        )
        entity: Entity | None = None

        # Define search criteria as tuples: (value, search_function)
        search_criteria = [
            (entity_id, self.entity_service.get),
            (entity_telegram_id, self.entity_service.get_by_telegram_id),
            (entity_name, self.entity_service.get_by_name),
        ]

        # Look for the entity using the provided criteria
        for criteria, search_function in search_criteria:
            if criteria is not None:
                try:
                    result = search_function(criteria)
                except NotFoundError:
                    continue
                if result is not None:
                    entity = result
                    break  # Stop at the first found entity

        if entity is not None:
            report.entity_found = True
            logger.info(
                "TokenService: entity found id=%s name=%s auth_keys=%s",
                entity.id,
                entity.name,
                list(entity.auth.keys()) if isinstance(entity.auth, dict) else None,
            )

            # Generate a login token
            token = self._generate_new_token(entity_id=entity.id)
            if token:
                report.token_generated = True
                logger.info("TokenService: token generated for entity_id=%s", entity.id)

            # Build the login link message
            login_link = f"{self.config.ui_url}/auth/token/{token}"

            sent_count = 0

            if isinstance(entity.auth, dict):
                # Send via Telegram if available
                if "telegram_id" in entity.auth:
                    try:
                        data = {
                            "chat_id": entity.auth["telegram_id"],
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
                            sent_count += 1
                        else:
                            logger.error(
                                "TokenService: telegram sendMessage failed status=%s body=%s",
                                response.status_code,
                                response.text,
                            )
                            response = requests.post(
                                f"https://api.telegram.org/bot{self.config.telegram_bot_api_token}/sendMessage",
                                data={
                                    "chat_id": entity.auth["telegram_id"],
                                    "text": f"Login as {entity.name}: {login_link}",
                                },
                            )
                            if response.status_code == 200:
                                sent_count += 1
                            else:
                                logger.error(
                                    "TokenService: fallback telegram sendMessage failed status=%s body=%s",
                                    response.status_code,
                                    response.text,
                                )
                    except Exception as exc:
                        logger.exception(
                            "TokenService: exception during telegram send for entity_id=%s: %s",
                            entity.id,
                            exc,
                        )
                else:
                    logger.info(
                        "TokenService: entity_id=%s has no telegram_id in auth. auth_keys=%s",
                        entity.id,
                        list(entity.auth.keys()),
                    )
            else:
                logger.info(
                    "TokenService: entity_id=%s has no auth providers configured (auth is %s)",
                    entity.id,
                    type(entity.auth).__name__,
                )

            report.message_sent = sent_count > 0
            if not report.message_sent:
                logger.warning(
                    "TokenService: message not sent for entity_id=%s. Check telegram_id presence and bot token/chat access.",
                    entity.id,
                )

        return report
