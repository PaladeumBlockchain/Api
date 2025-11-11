from app.schemas import CustomModel, Satoshi, datetime_pd, PaginatedResponse


class BlockResponse(CustomModel):
    created: datetime_pd
    blockhash: str
    height: int
    tx: int
    reward: Satoshi


BlockPaginatedResponse = PaginatedResponse[BlockResponse]
