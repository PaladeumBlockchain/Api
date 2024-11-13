from sqlalchemy import select, Select, func, ScalarResult
from sqlalchemy.ext.asyncio import AsyncSession

from app import get_settings
from app.models import Transaction
from app.parser import make_request


def transactions_filter(query: Select, currency: str) -> Select:
    return query.filter(Transaction.currencies.contains([currency.upper()]))


async def count_transactions(session: AsyncSession, currency: str) -> int:
    return await session.scalar(
        transactions_filter(select(func.count(Transaction.id)), currency)
    )


async def get_transactions(
    session: AsyncSession, currency: str, offset: int, limit: int
) -> ScalarResult[Transaction]:
    return await session.scalars(
        transactions_filter(
            select(Transaction)
            .order_by(Transaction.height.desc())
            .offset(offset)
            .limit(limit),
            currency,
        )
    )


async def broadcast_transaction(raw: str):
    settings = get_settings()

    return await make_request(
        settings.blockchain.endpoint,
        {"id": "broadcast", "method": "sendrawtransaction", "params": [raw]},
    )
