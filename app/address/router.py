from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.params import Depends
from fastapi import APIRouter

from app.schemas import OutputPaginatedResponse, TransactionPaginatedResponse
from app.utils import pagination, paginated_response
from app.dependencies import get_page
from app.database import get_session
from app.address import service

router = APIRouter(prefix="/address", tags=["Addresses"])


@router.get(
    "/{address}/outputs/{currency}", response_model=OutputPaginatedResponse
)
async def get_outputs(
    address: str,
    currency: str,
    spent: bool = False,
    session: AsyncSession = Depends(get_session),
    page: int = Depends(get_page),
):
    limit, offset = pagination(page)

    total = await service.count_outputs(session, address, currency, spent)
    items = await service.list_outputs(
        session, address, currency, spent, limit, offset
    )

    return paginated_response(items.all(), total, page, limit)


@router.get(
    "/{address}/transactions", response_model=TransactionPaginatedResponse
)
async def get_transactions(
    address: str,
    session: AsyncSession = Depends(get_session),
    page: int = Depends(get_page),
):
    limit, offset = pagination(page)

    total = await service.count_transactions(session, address)
    items = await service.list_transactions(session, address, limit, offset)

    return paginated_response(items.all(), total, page, limit)
