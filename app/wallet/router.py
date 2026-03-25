from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Body, Depends

from .schemas import WalletInfoResponse
from app.database import get_session
from . import service

router = APIRouter(prefix="/wallet", tags=["Wallet"])


@router.post("/check", summary="Check wallet addresses")
async def check_addresses(
    addresses: list[str] = Body(max_length=20),
    session: AsyncSession = Depends(get_session),
) -> list[str]:
    return await service.check_addresses(session, addresses)


@router.get("/info", response_model=WalletInfoResponse)
async def get_wallet_info():
    return await service.get_wallet_info()
