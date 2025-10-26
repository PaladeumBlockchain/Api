from sqlalchemy import func, select, update, delete, desc, text
from app import constants
from app.parser import make_request, parse_block
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import sessionmanager
from app.settings import get_settings
from collections import defaultdict
from app.utils import token_type, utcnow
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

    transaction_currencies: dict[str, list[str]] = defaultdict(list)
    transaction_amounts: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: defaultdict(Decimal)
    )

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

        txid = output_data["txid"]
        currency = output_data["currency"]

        currencies = transaction_currencies[txid]
        if currency not in currencies:
            currencies.append(currency)

        transaction_amounts[txid][currency] += output_data["amount"]

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
                    "script": output_data["script"],
                    "asm": output_data["asm"],
                    "index": output_data["index"],
                    "meta": output_data["meta"],
                    "unlocked": output_data["timelock"] == 0,
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
                    "currencies": transaction_currencies[transaction_data["txid"]],
                    "height": block.height,
                    "coinbase": transaction_data["coinbase"],
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
    await session.execute(
        update(Output).filter(Output.shortcut.in_(input_shortcuts)).values(spent=True)
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
                    balance=Decimal(0.0),
                    locked=Decimal(0.0),
                    currency=currency,
                    address=address,
                )

                session.add(balance)

            balance.balance += Decimal(str(amount["amount"]))
            balance.locked += Decimal(str(amount["locked"]))

    locked_outputs = await session.scalars(
        select(Output)
        .filter(
            (Output.unlocked == False)
            & (
                (Output.timelock == block.height)
                | (
                    (Output.spent == False)
                    & (Output.timelock >= constants.TIMELOCK_TIMESTAMP_TRESHOLD)
                    & (Output.timelock <= int(block.created.timestamp()))
                )
            )
        )
        .order_by(Output.address, Output.currency)
    )

    # Do little caching :>

    # address: Address
    _addresses: dict[str, Address] = {}
    # (address, currency): AddressBalance
    _address_balances: dict[tuple[str, str], AddressBalance] = {}

    for output in locked_outputs:
        if output.address in _addresses:
            address = _addresses[output.address]
        else:
            address = await session.scalar(
                select(Address).filter(Address.address == output.address)
            )
            if address is None:
                continue

            _addresses[output.address] = address

        balance_key = (output.address, output.currency)
        if balance_key in _address_balances:
            address_balance = _address_balances[balance_key]
        else:
            address_balance = await session.scalar(
                select(AddressBalance).filter(
                    AddressBalance.address == address,
                    AddressBalance.currency == output.currency,
                )
            )
            if not address_balance:
                address_balance = AddressBalance(
                    address=address, balance=Decimal(), locked=Decimal()
                )
                session.add(address_balance)

            _address_balances[balance_key] = address_balance

        # Unlock balance and mark output as unlocked
        address_balance.balance += output.amount
        address_balance.locked -= output.amount
        output.unlocked = True

    return block


async def process_reorg(session: AsyncSession, block: Block):
    reorg_height = block.height
    movements = block.movements

    input_shortcuts = (
        await session.execute(
            delete(Input)
            .filter(Input.blockhash == block.blockhash)
            .returning(Input.shortcut)
        )
    ).scalars()

    await session.execute(
        update(Output).filter(Output.shortcut.in_(input_shortcuts)).values(spent=False)
    )

    locked_outputs = await session.execute(
        select(Output)
        .filter(
            (Output.unlocked == True)
            & (
                (Output.timelock == block.height)
                | (
                    (Output.spent == False)
                    & (Output.timelock >= constants.TIMELOCK_TIMESTAMP_TRESHOLD)
                    & (Output.timelock >= int(block.created.timestamp()))
                )
            )
        )
        .order_by(Output.address, Output.currency)
    )

    # Do little caching :>

    # address: Address
    _addresses: dict[str, Address] = {}
    # (address, currency): AddressBalance
    _address_balances: dict[tuple[str, str], AddressBalance] = {}

    for output in locked_outputs:
        if output.address in _addresses:
            address = _addresses[output.address]
        else:
            address = await session.scalar(
                select(Address).filter(Address.address == output.address)
            )
            if address is None:
                continue

            _addresses[output.address] = address

        balance_key = (output.address, output.currency)
        if balance_key in _address_balances:
            address_balance = _address_balances[balance_key]
        else:
            address_balance = await session.scalar(
                select(AddressBalance).filter(
                    AddressBalance.address == address,
                    AddressBalance.currency == output.currency,
                )
            )

            assert (
                address_balance is not None
            ), f"Expected balance for ({output.address=!r}, {output.currency=!r}), got None. Possible a bug inside synchronization code"

            _address_balances[balance_key] = address_balance

        # Re-lock balance and mark output as locked again
        address_balance.balance -= output.amount
        address_balance.locked += output.amount
        output.unlocked = False

    outputs = await session.scalars(
        select(Output)
        .filter(
            Output.blockhash == block.blockhash,
            Output.meta.op("->>")(text("'type'")).in_(["new_token", "reissue_token"]),
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
                await session.execute(delete(Token).filter(Token.name == meta["name"]))
                removed_currencies.append(meta["name"])
            case "reissue_token":
                token = await session.scalar(
                    select(Token).filter(Token.name == meta["name"])
                )
                token.amount -= Decimal(meta["amount"])
                token.units = meta["units"]
                token.reissuable = meta["reissuable"]

    await session.execute(
        delete(AddressBalance).filter(AddressBalance.currency.in_(removed_currencies))
    )

    await session.execute(delete(Output).filter(Output.blockhash == block.blockhash))

    await session.execute(
        delete(Transaction).filter(Transaction.blockhash == block.blockhash)
    )

    await session.execute(delete(Block).filter(Block.blockhash == block.blockhash))

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
            assert (
                balance is not None
            ), f"Expected balance for ({raw_address=!r}, {currency=!r}), got None. Possible a bug inside synchronization code"

            balance.balance -= Decimal(amount["amount"])
            balance.locked -= Decimal(amount["locked"])

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
