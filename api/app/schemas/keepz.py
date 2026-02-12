"""DTO for Keepz authentication."""

from pydantic import BaseModel, Field


class KeepzSendSmsSchema(BaseModel):
    phone: str
    country_code: str


class KeepzLoginSchema(BaseModel):
    phone: str
    country_code: str
    code: str
    user_type: str = Field(default="INDIVIDUAL")
    mobile_name: str = Field(default="iPhone 12 mini")
    mobile_os: str = Field(default="IOS")


class KeepzAuthStatusSchema(BaseModel):
    authenticated: bool
    user_id: str | None = None
    obtained_at: str | None = None
    expires_in: int | None = None
