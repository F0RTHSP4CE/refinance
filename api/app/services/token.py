"""Token service. Generates a token and sends it to Telegram. Verifies generated tokens."""

import logging
from datetime import datetime, timezone

import jwt
import requests
from app.config import Config, get_config
from app.db import get_db
from app.errors.common import NotFoundError
from app.errors.token import TokenInvalid
from app.models.entity import Entity
from app.schemas.token import TokenSendReportSchema
from app.services.entity import EntityService
from fastapi import Depends
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class TokenService:
    ALGORITHM = "HS256"

    def __init__(
        self,
        db: Session = Depends(get_db),
        entity_service: EntityService = Depends(),
        config: Config = Depends(get_config),
    ):
        self.db = db
        self.entity_service = entity_service
        self.config = config

    def _generate_new_token(self, entity_id: int) -> str:
        """Generate a new signed token with entity_id and current timestamp."""
        data = {
            "sub": entity_id,
            "iad": int(datetime.now(timezone.utc).timestamp()),
        }
        encoded_jwt = jwt.encode(data, self.config.secret_key, algorithm=self.ALGORITHM)
        return encoded_jwt

    def get_entity_from_token(self, token: str) -> Entity:
        """Verify the token and retrieve the associated entity."""
        try:
            payload: dict[str, int] = jwt.decode(
                token, self.config.secret_key, algorithms=[self.ALGORITHM]
            )
            entity_id = payload.get("sub")
            if entity_id is not None:
                return self.entity_service.get(entity_id)
            else:
                raise TokenInvalid
        except jwt.InvalidTokenError:
            raise TokenInvalid

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

            # Generate a login token
            token = self._generate_new_token(entity_id=entity.id)
            if token:
                report.token_generated = True

            # Build the login link message
            login_link = f"{self.config.ui_url}/auth/token/{token}"

            sent_count = 0

            # Send via Telegram if available
            if "telegram_id" in entity.auth:
                try:
                    response = requests.post(
                        f"https://api.telegram.org/bot{self.config.telegram_bot_api_token}/sendMessage",
                        data={
                            "chat_id": entity.auth["telegram_id"],
                            "text": login_link,
                        },
                        timeout=5,
                    )
                    if response.status_code == 200:
                        sent_count += 1
                    else:
                        logger.error(f"response: {response.text}")
                except Exception:
                    pass

            report.message_sent = sent_count > 0

        return report
