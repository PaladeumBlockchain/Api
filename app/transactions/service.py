from app.models import Transaction, Output, Input, Block, Token
from sqlalchemy.ext.asyncio import AsyncSession
from app.blocks.service import get_latest_block
from sqlalchemy import select, Select, func
from app.parser import make_request
from app import get_settings


async def get_token_units(session: AsyncSession, currency: str) -> int:
    if currency == "PLB":
        return 8

    token = await session.scalar(select(Token).filter(Token.name == currency))

    if not token:
        return 8

    return token.units


async def load_tx_details(
    session: AsyncSession, transaction: Transaction, latest_block: Block = None
):
    if latest_block is None:
        latest_block = await get_latest_block(session)

    transaction.confirmations = latest_block.height - transaction.height

    transaction.fee = 0

    output_shortcuts: dict[str, Output] = {}

    transaction.outputs = []
    for output in await session.scalars(
        select(Output)
        .filter(Output.txid == transaction.txid)
        .order_by(Output.index)
    ):
        output: Output
        output.units = await get_token_units(session, output.currency)

        output_shortcuts[output.shortcut] = output
        transaction.outputs.append(output)
        transaction.fee -= output.amount

    transaction.inputs = []
    for input_ in await session.scalars(
        select(Input).filter(Input.txid == transaction.txid)
    ):
        input_: Input

        output = output_shortcuts[input_.shortcut]

        input_.amount = output.amount
        input_.units = output.units
        input_.currency = output.currency
        input_.address = output.address

        transaction.inputs.append(input_)
        transaction.fee += output.amount

    return transaction


async def get_transaction_by_txid(
    session: AsyncSession, txid: str
) -> Transaction:
    return await load_tx_details(
        session,
        await session.scalar(
            select(Transaction).filter(Transaction.txid == txid)
        ),
    )


def transactions_filter(query: Select, currency: str) -> Select:
    return query.filter(Transaction.currencies.contains([currency.upper()]))


async def count_transactions(session: AsyncSession, currency: str) -> int:
    return await session.scalar(
        transactions_filter(select(func.count(Transaction.id)), currency)
    )


async def get_transactions(
    session: AsyncSession, currency: str, offset: int, limit: int
) -> list[Transaction]:
    latest_block = await get_latest_block(session)

    transactions = []
    for transaction in await session.scalars(
        transactions_filter(
            select(Transaction)
            .order_by(Transaction.height.desc())
            .offset(offset)
            .limit(limit),
            currency,
        )
    ):
        transactions.append(
            await load_tx_details(session, transaction, latest_block=latest_block)
        )

    return transactions


async def broadcast_transaction(raw: str):
    settings = get_settings()

    return await make_request(
        settings.blockchain.endpoint,
        {"id": "broadcast", "method": "sendrawtransaction", "params": [raw]},
    )
