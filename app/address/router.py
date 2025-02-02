from app.utils import pagination, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_page
from app.database import get_session
from fastapi.params import Depends
from app.address import service
from fastapi import APIRouter

from app.schemas import (
    TransactionPaginatedResponse,
    OutputPaginatedResponse,
    BalanceResponse,
)

router = APIRouter(prefix="/address", tags=["Addresses"])


@router.get(
    "/{address}/outputs/{currency}", response_model=OutputPaginatedResponse
)
async def get_unspent_outputs(
    address: str,
    currency: str,
    session: AsyncSession = Depends(get_session),
    page: int = Depends(get_page),
):
    limit, offset = pagination(page)

    total = await service.count_unspent_outputs(session, address, currency)
    items = await service.list_unspent_outputs(
        session, address, currency, limit, offset
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

    return paginated_response(items, total, page, limit)


@router.get("/{address}/balances", response_model=list[BalanceResponse])
async def get_balances(
    address: str,
    session: AsyncSession = Depends(get_session),
):
    return await service.list_balances(session, address)
