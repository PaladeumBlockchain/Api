from sqlalchemy.orm import mapped_column, relationship
from sqlalchemy.orm import Mapped
from sqlalchemy import Numeric, ForeignKey
from sqlalchemy import String
from .base import Base


class Address(Base):
    __tablename__ = "service_addresses"

    address: Mapped[str] = mapped_column(String(70), index=True, unique=True)

    balances: Mapped[list["AddressBalance"]] = relationship(
        back_populates="address"
    )


class AddressBalance(Base):
    __tablename__ = "service_address_balances"
    balance: Mapped[Numeric] = mapped_column(Numeric(28, 8))
    currency: Mapped[str] = mapped_column(String(64), index=True)

    address_id = mapped_column(
        ForeignKey("service_addresses.id"), primary_key=True
    )
    address: Mapped[Address] = relationship(
        foreign_keys=[address_id], back_populates="balances"
    )
