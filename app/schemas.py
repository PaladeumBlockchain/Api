from typing import Annotated, TypeVar, Generic
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timedelta
from pydantic import PlainSerializer
from app import utils


# Custom Pydantic serializers
datetime_pd = Annotated[
    datetime,
    PlainSerializer(
        lambda x: utils.to_timestamp(x),
        return_type=int,
    ),
]

timedelta_pd = Annotated[
    timedelta,
    PlainSerializer(
        lambda x: int(x.total_seconds()),
        return_type=int,
    ),
]


class CustomModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True,
        from_attributes=True,
    )


class PaginationDataResponse(CustomModel):
    total: int
    pages: int
    page: int


T = TypeVar("T", bound=CustomModel)


class PaginatedResponse(CustomModel, Generic[T]):
    pagination: PaginationDataResponse
    list: list[T]


class TransactionResponse(CustomModel):
    height: int
    blockhash: str
    timestamp: int
    txid: str
    amount: dict[str, float]


TransactionPaginatedResponse = PaginatedResponse[TransactionResponse]

