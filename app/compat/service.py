from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Block, Output, Transaction


async def get_blocks_from_height(
    session: AsyncSession, height: int, offset: int, limit: int
) -> list[Block]:
    return list(
        await session.scalars(
            select(Block)
            .filter(Block.height >= height)
            .order_by(Block.height.asc())
            .offset(offset)
            .limit(limit)
        )
    )


async def get_outputs_by_shortcut(
    session: AsyncSession, shortcuts: list[str]
) -> list[Output]:
    return list(
        await session.scalars(
            select(Output).filter(Output.shortcut.in_(shortcuts))
        )
    )


async def get_address_stats(session: AsyncSession, address: str) -> dict:
    tx_count = (
        await session.scalar(
            select(func.count(Transaction.id)).filter(
                Transaction.addresses.contains([address])
            )
        )
        or 0
    )

    token_count = (
        await session.scalar(
            select(func.count(func.distinct(Transaction.currencies))).filter(
                Transaction.addresses.contains([address])
            )
        )
        or 0
    )

    return {"transactions": tx_count, "tokens": token_count}
