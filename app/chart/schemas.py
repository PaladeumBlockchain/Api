from enum import Enum

from app.schemas import CustomModel, Satoshi


class Resolution(str, Enum):
    DAY = "1D"
    WEEK = "1W"
    MONTH = "1M"
    YEAR = "1Y"


class ChartGeneralEntry(CustomModel):
    timestamp: int
    resolution: Resolution
    transactions: int
    addresses: int
    tokens: int
    volume: Satoshi
    volume_per_token: dict[str, Satoshi]
    blocks: int
