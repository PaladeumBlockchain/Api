from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Transaction


async def check_addresses(session: AsyncSession, addresses: list[str]):
    valid_addresses: list[str] = []

    for address in addresses:
        tx = await session.scalar(
            select(Transaction)
            .filter(Transaction.addresses.contains([address]))
            .limit(1)
        )

        if tx is not None:
            valid_addresses.append(address)

    return valid_addresses
