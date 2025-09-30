"""Base DTOs for API endpoints"""

from datetime import datetime
from decimal import Decimal
from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic_core import core_schema


class CurrencyDecimal:
    """Displays Decimal with high scale (many digits) in a useful way.

    0.0000010000000 -> 0.000001
    10.001000000000 -> 10.001
    10.000000000000 -> 10.00
    """

    def __init__(self, value: Decimal):
        self.value = value

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.any_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(
                cls.serialize,
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )

    @classmethod
    def validate(cls, value: Any) -> "CurrencyDecimal":
        # If already our custom type, just return it.
        if isinstance(value, cls):
            return value
        # If it's a float, convert it to a string first to avoid precision issues.
        if isinstance(value, float):
            value = str(value)
        try:
            decimal_value = value if isinstance(value, Decimal) else Decimal(value)
        except Exception as e:
            raise ValueError("Invalid decimal value") from e
        return cls(decimal_value)

    @classmethod
    def __get_pydantic_json_schema__(
        cls, core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ):
        # Represent the custom type as a string in the OpenAPI schema.
        return {"type": "string", "title": "CurrencyDecimal", "example": "10.00001"}

    @staticmethod
    def serialize(value: "CurrencyDecimal") -> str:
        return str(value)

    def __str__(self) -> str:
        # d = self.value
        # # If the value is integral, format with exactly 2 decimal places.
        # if d == d.to_integral_value():
        #     return format(d, ".2f")
        # # Otherwise, use fixed‑point notation and trim any trailing zeros.
        # s = format(d, "f")
        # if "." in s:
        #     s = s.rstrip("0").rstrip(".")
        # return s
        return format(self.value, ".2f")

    def to_decimal(self) -> Decimal:
        return Decimal(self.value)

    def __repr__(self):
        return str(self)


class BaseSchema(BaseModel):
    # needed for ORM
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,
    )

    # default dump options to deserialize pydantic models
    def dump(self):
        return self.model_dump(exclude_none=True)


class BaseReadSchema(BaseSchema):
    id: int
    comment: Optional[str] = None
    created_at: datetime
    modified_at: datetime | None = None


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
