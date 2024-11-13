from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.schemas import TransactionPaginatedResponse
from app.utils import pagination, paginated_response
from app.dependencies import get_page
from app.database import get_session
from app.transactions import service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/{token}", response_model=TransactionPaginatedResponse)
async def get_transactions(
    token: str = "PLB",
    page: int = Depends(get_page),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = pagination(page)

    total = await service.count_transactions(session, token)
    transactions = await service.get_transactions(session, token, offset, limit)

    return paginated_response(
        transactions.all(),
        total=total,
        page=page,
        limit=limit,
    )


@router.post("/broadcast")
async def broadcast_transaction(
    raw: str,
):
    return await service.broadcast_transaction(raw)
