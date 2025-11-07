from fastapi.responses import PlainTextResponse
from fastapi import APIRouter

router = APIRouter(tags=["General"])

TOTAL_SUPPLY = 1000000000


@router.get("/plain/supply/total", response_class=PlainTextResponse)
async def total_supply():
    return TOTAL_SUPPLY


@router.get("/plain/supply/circulating", response_class=PlainTextResponse)
async def circulating_supply():
    return TOTAL_SUPPLY * 0.5
