import sys
import pathlib

# Shenanigan to be able to run just with python scripts/SCRIPTNAME.py
sys.path.append(str(pathlib.Path(__file__).parent.parent.absolute()))

import asyncio
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import get_settings
from app.database import sessionmanager
from app.models import Block, Transaction


async def script(session: AsyncSession):
    BATCH_SIZE = 100

    total = await session.scalar(select(func.count(Block.id))) or 0
    print("Working on", total, "blocks with batch size", BATCH_SIZE)

    offset = 0
    while total > offset:
        print(f"Progress: {offset}/{total}", end="\r")
        blocs = await session.scalars(
            select(Block).offset(offset).limit(BATCH_SIZE).order_by(Block.height.asc())
        )

        for block in blocs:
            block.reward = Decimal(0)
            fees = (
                (
                    await session.execute(
                        select(Transaction.txid, Transaction.fee).filter(
                            Transaction.blockhash == block.blockhash
                        )
                    )
                )
                .tuples()
                .all()
            )

            if not fees:
                print("Unable to get fees for block:", block.blockhash)
                continue

            transaction_fees = {txid: fee for txid, fee in fees}

            # If it is stake - first tx won't be in transaction_fees
            first_tx = block.transactions[0]
            if first_tx in transaction_fees:
                base_reward = abs(transaction_fees[first_tx])
                tx_offset = 1
            else:
                base_reward = abs(transaction_fees[block.transactions[1]])
                tx_offset = 2

            rest_reward = Decimal()
            for txid in block.transactions[tx_offset:]:
                fee = transaction_fees[txid]
                if fee < 0:
                    continue

                rest_reward += fee

            block.reward = base_reward + rest_reward

        await session.commit()
        session.expunge_all()

        offset += BATCH_SIZE

    print()
    print("Done")


async def main():
    settings = get_settings()
    sessionmanager.init(settings.database.endpoint)
    async with sessionmanager.session() as session:
        await script(session)


if __name__ == "__main__":
    asyncio.run(main())
