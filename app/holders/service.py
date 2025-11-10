from app.models import AddressBalance, Transaction
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy import func, select
from decimal import Decimal
import typing


async def count_holders_by_currency(session: AsyncSession, currency: str):
    return (
        await session.scalar(
            select(func.count(AddressBalance.id)).filter(
                AddressBalance.currency == currency, AddressBalance.balance > 0
            )
        )
        or 0
    )


async def list_holders_by_currency(
    session: AsyncSession, currency: str, offset: int, limit: int
):
    filter = (AddressBalance.currency == currency, AddressBalance.balance > 0)

    total_balance = (
        await session.scalar(select(func.sum(AddressBalance.balance)).filter(*filter))
        or Decimal()
    )

    holders = await session.scalars(
        select(AddressBalance)
        .filter(*filter)
        .options(joinedload(AddressBalance.address))
        .order_by(AddressBalance.balance.desc())
        .offset(offset)
        .limit(limit)
    )

    result: list[dict[str, typing.Any]] = []

    for holder in holders:
        txcount = (
            await session.scalar(
                select(func.count(Transaction.id)).filter(
                    Transaction.addresses.contains([holder.address.address])
                )
            )
            or 0
        )
        result.append(
            {
                "address": holder.address.address,
                "balance": holder.balance,
                "percentage": (holder.balance / total_balance) * 100,
                "txcount": txcount,
            }
        )

    return result
