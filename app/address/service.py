import typing

from sqlalchemy import Select, select, func, ScalarResult, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Output, Transaction, AddressBalance, Address, MemPool
from app.blocks.service import get_latest_block

from app.transactions.service import (
    load_mempool_tx_details,
    load_tx_details,
    get_token_units,
)

S = typing.TypeVar("S", bound=tuple[typing.Any, ...])


def unspent_outputs_filters(query: Select, address: str, currency) -> Select:
    query = query.filter(
        Output.address == address,
        func.lower(Output.currency) == currency.lower(),
        ~Output.spent,
    )

    return query


async def count_unspent_outputs(
    session: AsyncSession, address: str, currency: str
) -> int:
    return await session.scalar(
        unspent_outputs_filters(
            select(func.count(Output.id)), address, currency
        )
    )


async def list_unspent_outputs(
    session: AsyncSession,
    address: str,
    currency: str,
    limit: int,
    offset: int,
) -> ScalarResult[Output]:
    return await session.scalars(
        unspent_outputs_filters(
            select(Output)
            .order_by(Output.amount.desc())
            .limit(limit)
            .offset(offset),
            address,
            currency,
        )
    )


def utxo_cte(address: str, currency: str):
    return (
        select(
            Output,
            func.sum(Output.amount)
            .over(order_by=Output.blockhash)
            .label("cumulative_amount"),
        )
        .filter(
            Output.address == address,
            Output.currency == currency,
            ~Output.spent,
        )
        .cte("cumulative_outputs")
    )


async def count_utxo(
    session: AsyncSession, address: str, currency: str, amount: float
) -> int:
    cte = utxo_cte(address, currency)
    query = (
        select(func.count(1))
        .select_from(cte)
        .where(cte.c.cumulative_amount < amount)
    )
    return await session.scalar(query) or 0


async def list_utxo(
    session: AsyncSession,
    address: str,
    currency: str,
    amount: float,
    limit: int,
    offset: int,
):
    cte = utxo_cte(address, currency)
    query = (
        select(cte)
        .select_from(cte)
        .where(cte.c.cumulative_amount < amount)
        .limit(limit)
        .offset(offset)
    )
    return await session.execute(query)


def transactions_filters(
    query: Select[S], address: str, currency: str | None = None
) -> Select[S]:
    query = query.filter(Transaction.addresses.contains([address]))

    if currency is not None:
        query = query.filter(Transaction.currencies.contains([currency]))

    return query


def transactions_filters_multi(
    query: Select[S], addresses: list[str], currency: str | None
) -> Select[S]:
    query = query.filter(Transaction.addresses.overlap(addresses))

    if currency is not None:
        query = query.filter(Transaction.currencies.contains([currency]))

    return query


async def count_transactions(
    session: AsyncSession, address: str, currency: str | None = None
):
    return await session.scalar(
        transactions_filters(
            select(func.count(Transaction.id)), address, currency
        )
    )


async def count_transactions_multi(
    session: AsyncSession, addresses: list[str], currency: str | None
) -> int:
    return await session.scalar(
        transactions_filters_multi(
            select(func.count(Transaction.id)), addresses, currency
        )
    )


async def count_transactions_multi_mempool(
    session: AsyncSession, addresses: list[str]
) -> int:
    return await session.scalar(
        text("""
        SELECT COUNT(1)
        FROM service_mempool,
            jsonb_array_elements(raw->'transactions') AS tx
        WHERE tx->'addresses' ?| :addresses
    """),
        {"addresses": addresses},
    )


async def list_transactions(
    session: AsyncSession,
    address: str,
    limit: int,
    offset: int,
    currency: str | None = None,
) -> list[Transaction]:
    latest_block = await get_latest_block(session)
    transactions = []
    for transaction in await session.scalars(
        transactions_filters(
            select(Transaction)
            .order_by(Transaction.created.desc())
            .limit(limit)
            .offset(offset),
            address,
            currency,
        )
    ):
        transactions.append(
            await load_tx_details(session, transaction, latest_block)
        )

    return transactions


async def list_transactions_multi(
    session: AsyncSession,
    addresses: list[str],
    currency: str | None,
    limit: int,
    offset: int,
) -> list[Transaction]:
    latest_block = await get_latest_block(session)
    transactions = []
    for transaction in await session.scalars(
        transactions_filters_multi(
            select(Transaction)
            .order_by(Transaction.created.desc())
            .limit(limit)
            .offset(offset),
            addresses,
            currency,
        )
    ):
        transactions.append(
            await load_tx_details(session, transaction, latest_block)
        )

    return transactions


async def list_transactions_multi_mempool(
    session: AsyncSession,
    addresses: list[str],
    limit: int,
    offset: int,
) -> list[dict[str, typing.Any]]:
    stmt = text("""
        SELECT tx
        FROM service_mempool,
            jsonb_array_elements(raw->'transactions') AS tx
        WHERE tx->'addresses' ?| :addresses
        ORDER BY (tx->>'created')::bigint DESC
        OFFSET :offset
        LIMIT :limit
    """)

    txs = await session.scalars(
        stmt, {"addresses": addresses, "limit": limit, "offset": offset}
    )
    outputs = await session.scalar(select(MemPool.raw.op("->")("outputs")))
    assert outputs is not None

    transactions: list[dict[str, typing.Any]] = [
        await load_mempool_tx_details(session, tx, outputs) for tx in txs
    ]

    return transactions


async def list_balances(
    session: AsyncSession, address: str
) -> list[AddressBalance]:
    balances = []
    for balance in await session.scalars(
        select(AddressBalance).filter(
            AddressBalance.address_id == Address.id, Address.address == address
        )
    ):
        balance.units = await get_token_units(session, balance.currency)  # ty:ignore[unresolved-attribute]

        balances.append(balance)

    return balances


async def list_address_mempool_transactions(
    session: AsyncSession, address: str
):
    mempool = await session.scalar(select(MemPool).limit(1))

    if mempool is None:
        return []

    return [
        await load_mempool_tx_details(
            session, transaction, mempool.raw["outputs"]
        )
        for transaction in mempool.raw["transactions"]
        if address in transaction["addresses"]
    ]
