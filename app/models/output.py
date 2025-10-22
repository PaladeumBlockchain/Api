from decimal import Decimal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy import Numeric
from sqlalchemy import String
from .base import Base


class Output(Base):
    __tablename__ = "service_outputs"

    currency: Mapped[str] = mapped_column(String(64), index=True)

    shortcut: Mapped[str] = mapped_column(String(70), index=True, unique=True)
    blockhash: Mapped[str] = mapped_column(String(64), index=True)
    address: Mapped[str] = mapped_column(String(70), index=True)
    txid: Mapped[str] = mapped_column(String(64), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(28, 8))
    timelock: Mapped[int]
    type: Mapped[str] = mapped_column(String(64), index=True)
    script: Mapped[str]
    asm: Mapped[str]
    spent: Mapped[bool]
    index: Mapped[int]

    meta: Mapped[dict] = mapped_column(JSONB)
