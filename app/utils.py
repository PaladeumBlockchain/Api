from datetime import datetime, timezone, UTC
from typing import Sequence
import math

from app import constants


def utcnow():
    return datetime.now(UTC).replace(tzinfo=None)


# Convert datetime to timestamp
def to_timestamp(date: datetime | None) -> int | None:
    date = date.replace(tzinfo=timezone.utc) if date else date
    return int(date.timestamp()) if date else None


def token_type(name):
    if "#" in name:
        return "unique"
    if "/" in name:
        return "sub"
    if name[0] == "@":
        return "username"
    if name[0] == "!":
        return "owner"
    return "root"


# Helper function for pagination
def pagination(page, size=constants.DEFAULT_PAGINATION_SIZE):
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
    items: Sequence, total: int, page: int, limit: int
) -> dict:
    return {
        "pagination": pagination_dict(total, page, limit),
        "list": items,
    }
