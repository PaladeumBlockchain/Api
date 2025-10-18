from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Block, Output, Transaction
from app.models.input import Input
from app.sync.chain import process_reorg
from app.utils import utcnow


async def test_default(session: AsyncSession):
    blockhash = "hash"
    txid = "txid"
    currency = "currency"
    now = utcnow()
    address = "address"
    amount = Decimal(10)
    block = Block(
        blockhash=blockhash,
        transactions=["txid"],
        height=1,
        movements={},
        created=now,
        timestamp=int(now.timestamp()),
        prev_blockhash=None,
    )

    output = Output(
        currency=currency,
        shortcut="txid:0",
        blockhash=blockhash,
        address=address,
        txid=txid,
        amount=amount,
        timelock=0,
        type="pec",
        script="pec",
        asm="pec",
        spent=True,
        index=0,
        meta={},
    )
    assert output.spent == True

    transaction = Transaction(
        currencies=[currency],
        txid=txid,
        blockhash=blockhash,
        addresses=[address],
        created=now,
        timestamp=int(now.timestamp()),
        size=0,
        height=1,
        locktime=0,
        version=666,
        amount={currency: float(amount)},
        coinbase=True,
    )
    session.add_all([output, transaction, block])

    await session.flush()
    blockhash = "hash1"
    txid = "txid1"
    currency = "currency"
    now = utcnow()
    address = "address1"
    amount = Decimal(10)
    block = Block(
        blockhash=blockhash,
        transactions=["txid"],
        height=1,
        movements={},
        created=now,
        timestamp=int(now.timestamp()),
        prev_blockhash=None,
    )

    input = Input(
        shortcut="txid:0", blockhash=blockhash, txid=txid, source_txid="txid", index=0
    )

    transaction = Transaction(
        currencies=[currency],
        txid=txid,
        blockhash=blockhash,
        addresses=["address", address],
        created=now,
        timestamp=int(now.timestamp()),
        size=0,
        height=1,
        locktime=0,
        version=666,
        amount={currency: float(amount)},
        coinbase=True,
    )

    session.add_all([input, transaction, block])
    await session.flush()

    await process_reorg(session, block)

    await session.refresh(output)

    assert output.spent == False
