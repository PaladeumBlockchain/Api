from decimal import Decimal

from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy import Numeric, String

from .base import Base

class Token(Base):
    __tablename__ = "service_tokens"

    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=8))
    name: Mapped[str] = mapped_column(index=True)
    reissuable: Mapped[bool]
    units: Mapped[int]
    type: Mapped[str] = mapped_column(String(64), index=True)