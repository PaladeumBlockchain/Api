from datetime import datetime, timezone, UTC
from typing import Sequence
import typing
import math

from app import constants


def utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


# Convert datetime to timestamp
def to_timestamp(date: datetime | None) -> int | None:
    date = date.replace(tzinfo=timezone.utc) if date else date
    return int(date.timestamp()) if date else None


def token_type(name: str):
    if "#" in name:
        return "unique"
    if "/" in name:
        return "sub"
    if name[0] == "@":
        return "username"
    if name[-1] == "!":
        return "owner"
    return "root"


# Helper function for pagination
def pagination(page: int, size: int = constants.DEFAULT_PAGINATION_SIZE):
    """limit, offset = pagination(:page, :page_size)"""
    offset = (size * page) - size

    return size, offset


# Helper function to make pagination dict for api
def pagination_dict(total, page, limit):
    return {
        "pages": math.ceil(total / limit),
        "total": total,
        "page": page,
    }


def paginated_response(
    items: Sequence[typing.Any], total: int, page: int, limit: int
) -> dict[str, typing.Any]:
    return {
        "pagination": pagination_dict(total, page, limit),
        "list": items,
    }


def to_satoshi(x: float) -> int:
    return int(x * math.pow(10, 8))


def get_token_icon(name: str):
    cache_fix = 8

    match name:
        case "USDT":
            return f"https://apiv2.paladeum.io/static/USDT.svg?{cache_fix}"

        case "USD":
            return f"https://apiv2.paladeum.io/static/USD.svg?{cache_fix}"

        case "JPY":
            return f"https://apiv2.paladeum.io/static/JPY.svg?{cache_fix}"

        case "KRW":
            return f"https://apiv2.paladeum.io/static/KRW.svg?{cache_fix}"

        case "PNC":
            return f"https://apiv2.paladeum.io/static/PNC.png?{cache_fix}"

        case "RCT":
            return f"https://apiv2.paladeum.io/static/RCT.png?{cache_fix}"

        case _:
            return None
