from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Body, Depends

from . import service
from app.database import get_session

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post("/check", summary="Check wallet addresses")
async def check_addresses(
    addresses: list[str] = Body(max_length=20),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    return await service.check_addresses(session, addresses)
