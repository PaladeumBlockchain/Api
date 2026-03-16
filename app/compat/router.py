from fastapi import APIRouter

from .rest import router as rest_router
from .wallet import router as wallet_router
from .v2 import router as v2_router

router = APIRouter(prefix="/compat")

router.include_router(rest_router)
router.include_router(wallet_router)
router.include_router(v2_router)
