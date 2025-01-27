from sqlalchemy import select, update, delete, desc, text
from app.parser import make_request, parse_block
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import sessionmanager
from app.settings import get_settings
from app.utils import token_type
from decimal import Decimal

from app.models import (
    AddressBalance,
    Transaction,
    Address,
    Output,
    Token,
    Input,
    Block,
)


async def process_block(session: AsyncSession, data: dict):
    # Add new block
    block = Block(**data["block"])
    session.add(block)

    transaction_currencies: dict[str, list[str]] = {}
    transaction_amounts: dict[str, dict[str, Decimal]] = {}

    # Add new outputs to the session
    for output_data in data["outputs"]:
        if output_data["meta"]:
            meta = output_data["meta"]
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
                }
            )
        )

    # Mark outputs used in inputs as spent
    await session.execute(
        update(Output)
        .filter(Output.shortcut.in_(input_shortcuts))
        .values(spent=True)
    )

    for currency, movement in data["block"]["movements"].items():
        for raw_address, amount in movement.items():
            if not (
                address := await session.scalar(
                    select(Address).filter(Address.address == raw_address)
                )
            ):
                address = Address(address=raw_address)
                session.add(address)

            if not (
                balance := await session.scalar(
                    select(AddressBalance).filter(
                        AddressBalance.currency == currency,
                        AddressBalance.address == address,
                    )
                )
            ):
                balance = AddressBalance(
                    balance=Decimal(0.0),  # type: ignore
                    currency=currency,
                    address=address,
                )

                session.add(balance)

            balance.balance += Decimal(amount)

    return block


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


async def sync_chain():
    settings = get_settings()

    async with sessionmanager.session() as session:
        latest = await session.scalar(
            select(Block).order_by(desc(Block.height)).limit(1)
        )

        if not latest:
            print("Adding genesis block to transactions")

            block_data = await parse_block(0)

            latest = await process_block(session, block_data)

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

        chain_blocks = chain_data["result"]["blocks"]
        display_log = (chain_blocks - latest.height) < 100

        for height in range(latest.height + 1, chain_blocks + 1):
            try:
                if display_log:
                    print(f"Processing block #{height}")
                else:
                    if height % 100 == 0:
                        print(f"Processing block #{height}")

                block_data = await parse_block(height)

                await process_block(session, block_data)

                await session.commit()

            except KeyboardInterrupt:
                print("Keyboard interrupt")
                break
