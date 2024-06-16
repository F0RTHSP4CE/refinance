"""Token service. Generates a token and sends it to Telegram. Verifies generated tokens."""

from datetime import datetime, timezone

from fastapi import Depends
import jwt
from sqlalchemy.orm import Session

from refinance.config import Config, get_config
from refinance.db import get_db
from refinance.errors.common import NotFoundError
from refinance.models.entity import Entity
from refinance.services.entity import EntityService
from refinance.errors.token import TokenInvalid
from refinance.schemas.token import TokenSendReportSchema


import requests
import logging

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
        """Generate a new signed token with entity_id and current timestamp in it. Internal method."""
        data = {
            "e": entity_id,
            "d": int(datetime.now(timezone.utc).timestamp()),
        }
        encoded_jwt = jwt.encode(data, self.config.secret_key, algorithm=self.ALGORITHM)
        return encoded_jwt

    def get_entity_from_token(self, token: str) -> Entity:
        """Verify the generated token and get entity_id from its contents"""
        try:
            payload: dict[str, int] = jwt.decode(
                token, self.config.secret_key, algorithms=[self.ALGORITHM]
            )
            entity_id = payload.get("e")
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
        Generate a new signed token and send it to Telegram chat.

        Performs a search over all Entities.
        Useful when user forgot their own details (Entity.name, Entity.id, Entity.telegram_id).

        Returns True on success.
        """
        # Create an empty report for user, indicating what steps were successful.
        report = TokenSendReportSchema(
            entity_found=False, token_generated=False, message_sent=False
        )

        # Initialize variable for Entity
        entity: Entity | None = None

        # Try to find the Entity with specified property, in priority order
        for criteria, search_function in (
            (entity_id, self.entity_service.get),
            (entity_telegram_id, self.entity_service.get_by_telegram_id),
            (entity_name, self.entity_service.get_by_name),
        ):
            if criteria is not None:
                try:
                    result = search_function(criteria)  # type: ignore
                except NotFoundError:
                    continue
                if result is not None and entity is None:
                    entity = result

        if entity is not None:
            # Update the report
            report.entity_found = True

            # Generate a token
            token = self._generate_new_token(entity_id=entity.id)
            # Update the report
            if token:
                report.token_generated = True

            # Try to send to Telegram chat
            response = requests.post(
                f"https://api.telegram.org/bot{self.config.telegram_bot_api_token}/sendMessage",
                data=dict(
                    chat_id=entity.telegram_id,
                    text=token,
                ),
                timeout=5,
            )
            if response.status_code == 200:
                # Update the report
                report.message_sent = True

        return report
