from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import mapped_column
from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped
from datetime import datetime
from decimal import Decimal
from .base import Base
import typing


class Block(Base):
    __tablename__ = "service_blocks"

    blockhash: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    transactions: Mapped[list[str]] = mapped_column(ARRAY(String))
    height: Mapped[int] = mapped_column(index=True)
    movements: Mapped[dict[str, typing.Any]] = mapped_column(JSONB)
    created: Mapped[datetime]
    timestamp: Mapped[int]
    prev_blockhash: Mapped[str] = mapped_column(String(64), index=True, nullable=True)

    reward: Mapped[Decimal] = mapped_column(Numeric(28, 8), server_default="0")

    @property
    def tx(self) -> int:
        return len(self.transactions)
