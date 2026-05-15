import typing

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import DEFAULT_CURRENCY

from .schemas import Resolution


RESOLUTION_TO_TRUNC = {
    Resolution.DAY: "day",
    Resolution.WEEK: "week",
    Resolution.MONTH: "month",
    Resolution.YEAR: "year",
}


def _timestamp_filter(
    after: int | None, before: int | None
) -> tuple[str, dict[str, typing.Any]]:
    parts: list[str] = []
    params: dict[str, typing.Any] = {}

    if after is not None:
        parts.append("timestamp >= :after")
        params["after"] = after

    if before is not None:
        parts.append("timestamp < :before")
        params["before"] = before

    where_sql = ("WHERE " + " AND ".join(parts)) if parts else ""
    return where_sql, params


def _bucket_expr(trunc: str) -> str:
    return (
        f"cast(extract(epoch from date_trunc('{trunc}', "
        f"to_timestamp(timestamp))) as bigint)"
    )


def _empty_entry(bucket: int, resolution: Resolution) -> dict[str, typing.Any]:
    return {
        "timestamp": bucket,
        "resolution": resolution,
        "transactions": 0,
        "addresses": 0,
        "tokens": 0,
        "volume": 0.0,
        "volume_per_token": {},
        "blocks": 0,
    }


async def get_general_chart(
    session: AsyncSession,
    resolution: Resolution,
    after: int | None,
    before: int | None,
) -> list[dict[str, typing.Any]]:
    trunc = RESOLUTION_TO_TRUNC[resolution]
    bucket_expr = _bucket_expr(trunc)
    where_sql, params = _timestamp_filter(after, before)

    tx_rows = await session.execute(
        text(f"""
            SELECT
                {bucket_expr} AS bucket,
                COUNT(*) AS transactions,
                COALESCE(SUM((amount->>:plb)::float), 0) AS volume
            FROM service_transactions
            {where_sql}
            GROUP BY bucket
        """),
        {**params, "plb": DEFAULT_CURRENCY},
    )

    addr_rows = await session.execute(
        text(f"""
            SELECT bucket, COUNT(DISTINCT addr) AS count
            FROM (
                SELECT {bucket_expr} AS bucket, unnest(addresses) AS addr
                FROM service_transactions
                {where_sql}
            ) AS sub
            GROUP BY bucket
        """),
        params,
    )

    tok_rows = await session.execute(
        text(f"""
            SELECT bucket, COUNT(DISTINCT currency) AS count
            FROM (
                SELECT {bucket_expr} AS bucket, unnest(currencies) AS currency
                FROM service_transactions
                {where_sql}
            ) AS sub
            WHERE currency != :plb
            GROUP BY bucket
        """),
        {**params, "plb": DEFAULT_CURRENCY},
    )

    vpt_rows = await session.execute(
        text(f"""
            SELECT bucket, currency, SUM(amt) AS volume
            FROM (
                SELECT
                    {bucket_expr} AS bucket,
                    kv.key AS currency,
                    kv.value::float AS amt
                FROM service_transactions,
                    jsonb_each_text(amount) AS kv(key, value)
                {where_sql}
            ) AS sub
            WHERE currency != :plb
            GROUP BY bucket, currency
        """),
        {**params, "plb": DEFAULT_CURRENCY},
    )

    block_rows = await session.execute(
        text(f"""
            SELECT {bucket_expr} AS bucket, COUNT(*) AS count
            FROM service_blocks
            {where_sql}
            GROUP BY bucket
        """),
        params,
    )

    buckets: dict[int, dict[str, typing.Any]] = {}

    def ensure(bucket: int) -> dict[str, typing.Any]:
        if bucket not in buckets:
            buckets[bucket] = _empty_entry(bucket, resolution)
        return buckets[bucket]

    for row in tx_rows:
        entry = ensure(row.bucket)
        entry["transactions"] = row.transactions
        entry["volume"] = row.volume

    for row in addr_rows:
        ensure(row.bucket)["addresses"] = row.count

    for row in tok_rows:
        ensure(row.bucket)["tokens"] = row.count

    for row in vpt_rows:
        ensure(row.bucket)["volume_per_token"][row.currency] = row.volume

    for row in block_rows:
        ensure(row.bucket)["blocks"] = row.count

    return [buckets[bucket] for bucket in sorted(buckets, reverse=True)]
