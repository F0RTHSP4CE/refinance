"""DTO for OIDC Authentication"""

from app.schemas.base import BaseSchema


class OIDCAuthUrlSchema(BaseSchema):
    auth_url: str
    state: str


class OIDCCallbackSchema(BaseSchema):
    code: str
    state: str


class OIDCTokenSchema(BaseSchema):
    access_token: str
    refresh_token: str | None = None
    expires_in: int | None = None


class OIDCLoginResponseSchema(BaseSchema):
    token: str  # JWT token for the application
    entity_id: int
    entity_name: str