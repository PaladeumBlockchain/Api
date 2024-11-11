from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from .schemas import BlockPaginatedResponse, BlockResponse
from app.schemas import TransactionPaginatedResponse
from app.utils import pagination, paginated_response
from app.dependencies import get_page
from app.database import get_session
from . import service

router = APIRouter(prefix="/blocks", tags=["Blocks"])


@router.get("/latest", response_model=BlockResponse)
async def latest_block(session: AsyncSession = Depends(get_session)):
    return await service.get_latest_block(session)


@router.get("/blocks", response_model=BlockPaginatedResponse)
async def get_blocks(
    page: int = Depends(get_page), session: AsyncSession = Depends(get_session)
):
    limit, offset = pagination(page)

    total = await service.count_blocks(session)
    blocks = await service.get_blocks(session, offset, limit)

    return paginated_response(
        blocks.all(),
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/blocks/{hash_}", response_model=BlockResponse)
async def get_block(
    hash_: str,
    session: AsyncSession = Depends(get_session),
):
    return await service.get_block_by_hash(session, hash_)


@router.get(
    "/blocks/{hash_}/transactions", response_model=TransactionPaginatedResponse
)
async def get_block_transactions(
    hash_: str,
    page: int = Depends(get_page),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = pagination(page)

    total = await service.count_block_transactions(session, hash_)
    transactions = await service.get_block_transactions(
        session, hash_, offset, limit
    )

    return paginated_response(
        transactions.all(),
        total=total,
        page=page,
        limit=limit,
    )
