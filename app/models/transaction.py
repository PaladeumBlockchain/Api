from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy import String
from datetime import datetime
from .base import Base


class Transaction(Base):
    __tablename__ = "service_transactions"

    txid: Mapped[str] = mapped_column(String(64), index=True, unique=True)
    blockhash: Mapped[str] = mapped_column(String(64), index=True)
    created: Mapped[datetime]
    timestamp: Mapped[int]
