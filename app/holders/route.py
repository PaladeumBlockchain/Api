from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.utils import paginated_response, pagination
from app.schemas import PaginatedResponse
from app.dependencies import get_page
from app.database import get_session
from .schemas import HolderResponse
from app.holders import service


router = APIRouter(prefix="/holders", tags=["Holders"])


@router.get("/{currency}", response_model=PaginatedResponse[HolderResponse])
async def holders_by_currency(
    currency: str,
    page: int = Depends(get_page),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = pagination(page)

    total = await service.count_holders_by_currency(session, currency)
    items = await service.list_holders_by_currency(session, currency, offset, limit)

    return paginated_response(items, total, page, limit)
