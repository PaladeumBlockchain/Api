from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

from .schemas import ChartGeneralEntry, Resolution
from . import service


router = APIRouter(prefix="/chart", tags=["Chart"])


@router.get("/general", response_model=list[ChartGeneralEntry])
async def chart_general(
    resolution: Resolution = Query(default=Resolution.DAY),
    after: int | None = Query(default=None),
    before: int | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    return await service.get_general_chart(session, resolution, after, before)
