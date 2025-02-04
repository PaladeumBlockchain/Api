from sqlalchemy import select, update, delete, desc, text, Executable, insert
from app.parser import make_request, parse_block
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import sessionmanager
from app.settings import get_settings
from collections import defaultdict
from app.utils import token_type
from decimal import Decimal
import asyncio

from app.models import (
    AddressBalance,
    Transaction,
    Address,
    Output,
    Token,
    Input,
    Block,
)

LOCKS = defaultdict(asyncio.Lock)


async def process_block(
    session: AsyncSession,
    data: dict,
    execute_last: list[Executable] = None,
):

    # Add new block
    block = Block(**data["block"])
    session.add(block)

    transaction_currencies: dict[str, list[str]] = {}
    transaction_amounts: dict[str, dict[str, Decimal]] = {}

    # Add new outputs to the session
    for output_data in data["outputs"]:
        if output_data["meta"]:
            meta = output_data["meta"]

            async with LOCKS["token"]:
                match meta["type"]:
                    case "new_token":
                        token = Token(
                            type=token_type(meta["name"]),
                            name=meta["name"],
                            units=meta["units"],
                            reissuable=meta["reissuable"],
                            amount=Decimal(meta["amount"]),
                        )
                        session.add(token)
                    case "reissue_token":
                        token = await session.scalar(
                            select(Token).filter(Token.name == meta["name"])
                        )
                        token.amount += Decimal(meta["amount"])
                        token.units = meta["units"]
                        token.reissuable = meta["reissuable"]

        currencies = transaction_currencies.setdefault(output_data["txid"], [])

        if output_data["currency"] not in currencies:
            currencies.append(output_data["currency"])

        amounts = transaction_amounts.setdefault(output_data["txid"], {})
        amounts.setdefault(output_data["currency"], Decimal(0))
        amounts[output_data["currency"]] += Decimal(output_data["amount"])

        session.add(
            Output(
                **{
                    "currency": output_data["currency"],
                    "shortcut": output_data["shortcut"],
                    "blockhash": output_data["blockhash"],
                    "address": output_data["address"],
                    "txid": output_data["txid"],
                    "amount": output_data["amount"],
                    "timelock": output_data["timelock"],
                    "type": output_data["type"],
                    "spent": output_data["spent"],
                    "index": output_data["index"],
                    "meta": output_data["meta"],
                }
            )
        )

    # Add new transactions to the session
    session.add_all(
        [
            Transaction(
                **{
                    "created": transaction_data["created"],
                    "blockhash": transaction_data["blockhash"],
                    "locktime": transaction_data["locktime"],
                    "version": transaction_data["version"],
                    "timestamp": transaction_data["timestamp"],
                    "addresses": transaction_data["addresses"],
                    "size": transaction_data["size"],
                    "txid": transaction_data["txid"],
                    "currencies": transaction_currencies[
                        transaction_data["txid"]
                    ],
                    "height": block.height,
                    "amount": {
                        currency: float(amount)
                        for currency, amount in transaction_amounts[
                            transaction_data["txid"]
                        ].items()
                    },
                }
            )
            for transaction_data in data["transactions"]
        ]
    )

    # Add new inputs to the session and collect spent output shortcuts
    input_shortcuts = []
    for input_data in data["inputs"]:
        input_shortcuts.append(input_data["shortcut"])
        session.add(
            Input(
                **{
                    "shortcut": input_data["shortcut"],
                    "blockhash": input_data["blockhash"],
                    "index": input_data["index"],
                    "txid": input_data["txid"],
                    "source_txid": input_data["source_txid"],
                }
            )
        )

    # Mark outputs used in inputs as spent
    stmt = (
        update(Output)
        .filter(Output.shortcut.in_(input_shortcuts))
        .values(spent=True)
    )
    if execute_last:
        execute_last.append(stmt)
    else:
        await session.execute(stmt)

    return block


async def process_movements(
    session: AsyncSession, movements: dict[str, dict[str, float]]
):
    for currency, movement in movements.items():
        for raw_address, amount in movement.items():
            address = await session.scalar(
                select(Address).filter(Address.address == raw_address)
            )
            if address is None:
                address_id = await session.scalar(
                    insert(Address)
                    .values(address=raw_address)
                    .returning(Address.id)
                )

                await session.execute(
                    insert(AddressBalance).values(
                        balance=Decimal(amount),  # type: ignore
                        currency=currency,
                        address_id=address_id,
                    )
                )

            else:
                await session.execute(
                    update(
                        AddressBalance,
                    )
                    .values(balance=AddressBalance.balance + Decimal(amount))
                    .filter(
                        AddressBalance.currency == currency,
                        AddressBalance.address_id == address.id,
                    )
                )


async def process_reorg(session: AsyncSession, block: Block):
    reorg_height = block.height
    movements = block.movements

    outputs = await session.scalars(
        select(Output)
        .filter(
            Output.blockhash == block.blockhash,
            Output.meta.op("->>")(text("'type'")).in_(
                ["new_token", "reissue_token"]
            ),
        )
        .order_by(Output.index.asc())
    )
    removed_currencies = []

    for output in outputs:
        if not output.meta:
            continue

        meta = output.meta
        match meta["type"]:
            case "new_token":
                await session.execute(
                    delete(Token).filter(Token.name == meta["name"])
                )
                removed_currencies.append(meta["name"])
            case "reissue_token":
                token = await session.scalar(
                    select(Token).filter(Token.name == meta["name"])
                )
                token.amount -= Decimal(meta["amount"])
                token.units = meta["units"]
                token.reissuable = meta["reissuable"]

    await session.execute(
        delete(AddressBalance).filter(
            AddressBalance.currency.in_(removed_currencies)
        )
    )

    await session.execute(
        delete(Output).filter(Output.blockhash == block.blockhash)
    )

    await session.execute(
        delete(Input).filter(Input.blockhash == block.blockhash)
    )

    await session.execute(
        delete(Transaction).filter(Transaction.blockhash == block.blockhash)
    )

    await session.execute(
        delete(Block).filter(Block.blockhash == block.blockhash)
    )

    for currency, movement in movements.items():
        for raw_address, amount in movement.items():
            if currency in removed_currencies:
                continue

            balance = await session.scalar(
                select(AddressBalance).filter(
                    AddressBalance.currency == currency,
                    AddressBalance.address_id == Address.id,
                    Address.address == raw_address,
                )
            )

            balance.balance -= Decimal(amount)

    new_latest = await session.scalar(
        select(Block).filter(Block.height == reorg_height - 1)
    )

    return new_latest


async def process_height(
    session,
    height,
    execute_after: list[Executable],
    log: bool = False,
):
    if log:
        print(f"Processing block #{height}")

    block_data = await parse_block(height)

    await process_block(session, block_data, execute_after)

    async with LOCKS["movements"]:
        await process_movements(session, block_data["block"]["movements"])


async def sync_chain():
    settings = get_settings()

    async with sessionmanager.session() as session:
        session: AsyncSession
        latest = await session.scalar(
            select(Block).order_by(desc(Block.height)).limit(1)
        )

        if not latest:
            print("Adding genesis block to transactions")

            block_data = await parse_block(0)

            latest = await process_block(session, block_data, None)
            await session.commit()

        while True:
            latest_hash_data = await make_request(
                settings.blockchain.endpoint,
                {
                    "id": "info",
                    "method": "getblockhash",
                    "params": [latest.height],
                },
            )

            if latest.blockhash == latest_hash_data["result"]:
                break

            print(f"Found reorg at height #{latest.height}")

            latest = await process_reorg(session, latest)
            await session.commit()

    chain_data = await make_request(
        settings.blockchain.endpoint,
        {"id": "info", "method": "getblockchaininfo", "params": []},
    )

    tasks_batch = 16  # Greater values require to increase -rpcworkqueue parameter in node daemon

    chain_blocks = chain_data["result"]["blocks"]
    display_log = (chain_blocks - latest.height) < 100

    # Ensure that all blocks will be processed without repeating inner loops
    end = chain_blocks
    if chain_blocks % tasks_batch != 0:
        end += chain_blocks % tasks_batch

    # Clean session to be sure that none objects has dirty state on start
    async with sessionmanager.session(auto_flush=False) as session:
        for base_height in range(latest.height + 1, end + 1, tasks_batch):
            # Statements which required to be executed after all changes was made
            execute_last = []
            tasks = []
            # Make tasks batch
            for height in range(
                base_height, min(base_height + tasks_batch, chain_blocks + 1)
            ):
                tasks.append(
                    process_height(
                        session,
                        height,
                        execute_last,
                        log=display_log or height % 100 == 0,
                    )
                )

            # Run all tasks asynchronously
            await asyncio.gather(*tasks)

            # Flush all objects to database
            await session.flush()

            # Execute statements produced by tasks
            for stmt in execute_last:
                await session.execute(stmt)

            # Commit this batch changes
            await session.commit()
