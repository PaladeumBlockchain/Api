from decimal import Decimal

from app.models import Transaction, Output, Input, Block, Token, MemPool
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
    session: AsyncSession,
    transaction: Transaction | None,
    latest_block: Block = None,
) -> Transaction | None:

    if transaction is None:
        return transaction

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

        if output.currency == "PLB":
            transaction.fee -= output.amount

    transaction.inputs = []
    for input_ in await session.scalars(
        select(Input).filter(Input.txid == transaction.txid)
    ):
        input_: Input

        output = await session.scalar(
            select(Output).filter(Output.shortcut == input_.shortcut)
        )

        input_.amount = output.amount
        input_.units = await get_token_units(session, output.currency)
        input_.currency = output.currency
        input_.address = output.address

        transaction.inputs.append(input_)

        if output.currency == "PLB":
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
            await load_tx_details(
                session, transaction, latest_block=latest_block
            )
        )

    return transactions


async def broadcast_transaction(raw: str):
    settings = get_settings()

    return await make_request(
        settings.blockchain.endpoint,
        {"id": "broadcast", "method": "sendrawtransaction", "params": [raw]},
    )


async def load_mempool_tx_details(
    session: AsyncSession, transaction: dict, mempool_outputs: dict[str, dict]
) -> dict | None:
    transaction["height"] = None
    transaction["confirmations"] = 0
    transaction["amount"] = {}
    transaction["fee"] = Decimal(0)

    for output in transaction["outputs"]:
        output["units"] = await get_token_units(session, output["currency"])

        transaction["amount"].setdefault(output["currency"], Decimal(0))
        transaction["amount"][output["currency"]] += Decimal(output["amount"])

        if output["currency"] == "PLB":
            transaction["fee"] -= Decimal(output["amount"])

    for input_ in transaction["inputs"]:
        if input_["shortcut"] in mempool_outputs:
            output = mempool_outputs[input_["shortcut"]]
            input_["amount"] = output["amount"]
            input_["units"] = await get_token_units(session, output["currency"])
            input_["currency"] = output["currency"]
            input_["address"] = output["address"]

            if output["currency"] == "PLB":
                transaction["fee"] += Decimal(output["amount"])

            continue

        output_: Output = await session.scalar(
            select(Output).filter(Output.shortcut == input_["shortcut"])
        )

        input_["amount"] = output_.amount
        input_["units"] = await get_token_units(session, output_.currency)
        input_["currency"] = output_.currency
        input_["address"] = output_.address

        if output_.currency == "PLB":
            transaction["fee"] += output_.amount

    return transaction


async def get_mempool_transactions(session: AsyncSession) -> list[dict]:
    mempool = await session.scalar(select(MemPool).limit(1))

    if mempool is None:
        return []

    return [
        await load_mempool_tx_details(
            session, transaction, mempool.raw["outputs"]
        )
        for transaction in mempool.raw["transactions"]
    ]
