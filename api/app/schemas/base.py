"""Base DTOs for API endpoints"""

from datetime import datetime
from decimal import Decimal
from typing import Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict


class CurrencyDecimal:
    """Displays Decimal with high scale (many digits) in a useful way.
    
    0.0000010000000 -> 0.000001
    10.001000000000 -> 10.001
    10.000000000000 -> 10.00
    """
    def __init__(self, value: Decimal):
        self.value = value

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, field=None):
        # If already our custom type, just return it.
        if isinstance(v, cls):
            return v
        # If it's a float, convert it to a string first to avoid precision issues.
        if isinstance(v, float):
            v = str(v)
        try:
            d = v if isinstance(v, Decimal) else Decimal(v)
        except Exception as e:
            raise ValueError("Invalid decimal value") from e
        return cls(d)

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema, handler):
        # Represent the custom type as a string in the OpenAPI schema.
        return {"type": "string", "title": "CurrencyDecimal", "example": "10.00001"}

    def __str__(self) -> str:
        d = self.value
        # If the value is integral, format with exactly 2 decimal places.
        if d == d.to_integral_value():
            return format(d, ".2f")
        # Otherwise, use fixed‑point notation and trim any trailing zeros.
        s = format(d, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s

    def __repr__(self):
        return str(self)


class BaseSchema(BaseModel):
    # needed for ORM
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
        json_encoders={CurrencyDecimal: lambda v: str(v)},
    )

    # default dump options to deserialize pydantic models
    def dump(self):
        return self.model_dump(exclude_none=True)


class BaseReadSchema(BaseSchema):
    id: int
    comment: Optional[str] = None
    created_at: datetime


class BaseUpdateSchema(BaseSchema):
    comment: Optional[str] = None


class BaseFilterSchema(BaseSchema):
    comment: str | None = None
    created_before: datetime | None = None
    created_after: datetime | None = None


M = TypeVar("M")


class PaginationSchema(BaseSchema, Generic[M]):
    items: list[M]
    total: int
    skip: int
    limit: int
