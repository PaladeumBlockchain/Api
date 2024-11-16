from sqlalchemy import Select, select, func, ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Output, Transaction


def unspent_outputs_filters(
    query: Select, address: str, currency
) -> Select:
    query = query.filter(
        Output.address == address,
        func.lower(Output.currency) == currency.lower(),  # type: ignore
    )

    return query


async def count_unspent_outputs(
    session: AsyncSession, address: str, currency: str
) -> int:
    return await session.scalar(
        unspent_outputs_filters(select(func.count(Output.id)), address, currency)
    )


async def list_unspent_outputs(
    session: AsyncSession,
    address: str,
    currency: str,
    limit: int,
    offset: int,
) -> ScalarResult[Output]:
    return await session.scalars(
        unspent_outputs_filters(
            select(Output)
            .order_by(Output.amount.desc())
            .limit(limit)
            .offset(offset),
            address,
            currency,
        )
    )


def transactions_filters(query: Select, address: str) -> Select:
    query = query.filter(Transaction.addresses.contains([address]))

    return query


async def count_transactions(session: AsyncSession, address: str):
    return await session.scalar(
        transactions_filters(select(func.count(Transaction.id)), address)
    )


async def list_transactions(
    session: AsyncSession, address: str, limit: int, offset: int
):
    return await session.scalars(
        transactions_filters(
            select(Transaction)
            .order_by(Transaction.created.desc())
            .limit(limit)
            .offset(offset),
            address,
        )
    )
