from app.models import Transaction, Block, MemPool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.errors import Abort
import typing


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


async def get_wallet_info(session: AsyncSession) -> dict[str, typing.Any]:
    bestblock = await session.scalar(
        select(Block).order_by(Block.height.desc()).limit(1)
    )
    if not bestblock:
        raise Abort("wallet", "not-synchronized")

    mempool = await session.scalar(select(MemPool))

    mempool_size = 0
    if mempool is not None:
        mempool_size = len(mempool.raw["transactions"])

    return {
        "bestblockhash": bestblock.blockhash,
        "mediantime": bestblock.timestamp,
        "blocks": bestblock.height,
        "reward": int(bestblock.reward),
        "mempool": mempool_size,
    }
