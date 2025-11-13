from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends


from .schemas import FullTokenResponse, TokenResponse
from app.utils import paginated_response, pagination
from .dependencies import require_full_token
from app.schemas import PaginatedResponse
from app.dependencies import get_page
from app.database import get_session
from app.models import Token
from . import service


router = APIRouter(prefix="/token", tags=["Tokens"])


@router.get("/list", response_model=PaginatedResponse[TokenResponse])
async def list_tokens(
    page: int = Depends(get_page), session: AsyncSession = Depends(get_session)
):
    limit, offset = pagination(page)

    total = await service.count_tokens(session)
    items = await service.list_tokens(session, offset, limit)

    return paginated_response(items, total, page, limit)


@router.get("/{name}", response_model=FullTokenResponse)
async def token_by_name(token: Token = Depends(require_full_token)):
    return token
