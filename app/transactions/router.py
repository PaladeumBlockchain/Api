from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends

from app.schemas import TransactionPaginatedResponse, TransactionResponse
from app.utils import pagination, paginated_response
from .dependencies import require_transaction
from app.dependencies import get_page
from app.database import get_session
from app.models import Transaction
from . import service

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/list/{token}", response_model=TransactionPaginatedResponse)
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


@router.get("/{txid}", response_model=TransactionResponse)
async def get_transaction_info(
    transaction: Transaction = Depends(require_transaction),
):
    return transaction


@router.post("/broadcast")
async def broadcast_transaction(
    raw: str,
):
    return await service.broadcast_transaction(raw)
