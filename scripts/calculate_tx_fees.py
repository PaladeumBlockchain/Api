import sys
import pathlib

# Shenanigan to be able to run just with python scripts/SCRIPTNAME.py
sys.path.append(str(pathlib.Path(__file__).parent.parent.absolute()))

import asyncio
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import constants
from app.settings import get_settings
from app.database import sessionmanager
from app.models import Input, Output, Transaction


async def script(session: AsyncSession):
    BATCH_SIZE = 100

    total = await session.scalar(select(func.count(Transaction.id))) or 0
    print("Working on", total, "transactions with batch size", BATCH_SIZE)

    offset = 0
    while total > offset:
        print(f"Progress: {offset}/{total}", end="\r")
        txs = await session.scalars(
            select(Transaction)
            .offset(offset)
            .limit(BATCH_SIZE)
            .order_by(Transaction.height.asc())
        )

        for tx in txs:
            tx.fee = Decimal(0)

            for output in await session.scalars(
                select(Output)
                .filter(
                    Output.txid == tx.txid,
                    Output.currency == constants.DEFAULT_CURRENCY,
                )
                .order_by(Output.index)
            ):
                tx.fee -= output.amount

            for input_ in await session.scalars(
                select(Input).filter(Input.txid == tx.txid)
            ):
                output = await session.scalar(
                    select(Output).filter(
                        Output.shortcut == input_.shortcut,
                        Output.currency == constants.DEFAULT_CURRENCY,
                    )
                )
                if output is None:
                    continue

                tx.fee += output.amount

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
