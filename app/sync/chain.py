from sqlalchemy.orm import with_loader_criteria, joinedload
from sqlalchemy import select, update, delete, desc

from app.parser import make_request, parse_block
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import sessionmanager
from app.settings import get_settings
from decimal import Decimal

from app.models import (
    AddressBalance,
    Transaction,
    Address,
    Output,
    Input,
    Block,
)


async def process_block(session: AsyncSession, data: dict):
    # Add new block
    block = Block(**data["block"])
    session.add(block)

    # Add new outputs to the session
    session.add_all([Output(**output_data) for output_data in data["outputs"]])

    # Add new transactions to the session
    session.add_all(
        [
            Transaction(**transaction_data)
            for transaction_data in data["transactions"]
        ]
    )

    # Add new inputs to the session and collect spent output shortcuts
    input_shortcuts = []
    for input_data in data["inputs"]:
        input_shortcuts.append(input_data["shortcut"])
        session.add(Input(**input_data))

    # Mark outputs used in inputs as spent
    await session.execute(
        update(Output)
        .filter(Output.shortcut.in_(input_shortcuts))
        .values(spent=True)
    )

    for currency, movement in data["block"]["movements"].items():
        for raw_address, amount in movement.items():
            # Get address from database with loaded balance with required currency
            address = await session.scalar(
                select(Address)
                .filter(Address.address == raw_address)
                .options(
                    joinedload(Address.balances),
                    with_loader_criteria(
                        AddressBalance, AddressBalance.currency == currency
                    ),
                )
            )

            # If address not exists - create new one
            if not address:
                address = Address(
                    address=raw_address,
                    balances=[],
                )
                session.add(address)

            # If balance not exists - create new one
            if not address.balances:
                balance = AddressBalance(
                    balance=0.0,  # type: ignore
                    currency=currency,
                    address=address,
                )
                address.balances.append(balance)
                session.add(balance)

            address.balances[0].balance += amount

    return block


async def process_reorg(session: AsyncSession, block: Block):
    reorg_height = block.height
    movements = block.movements
    movement_addresses = list(movements.keys())

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

    # Get addresses from database
    cache = await session.scalars(
        select(Address).filter(Address.address.in_(movement_addresses))
    )

    addresses_cache = {entry.address: entry for entry in cache}

    for raw_address in movement_addresses:
        address = addresses_cache[raw_address]
        address.balance -= Decimal(movements[address.address])
        session.add(address)

    new_latest = await session.scalar(
        select(Block).filter(Block.height == reorg_height - 1)
    )

    return new_latest


async def sync_chain():
    settings = get_settings()

    sessionmanager.init(settings.database.endpoint)

    async with sessionmanager.session() as session:
        latest = await session.scalar(
            select(Block).order_by(desc(Block.height)).limit(1)
        )

        if not latest:
            print("Adding genesis block to db")

            block_data = await parse_block(0)

            latest = await process_block(session, block_data)

            await session.commit()

        while True:
            latest_hash_data = await make_request(
                settings.backend.node,
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
            settings.backend.node,
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

    await sessionmanager.close()
