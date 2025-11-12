from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.errors import Abort
from app.token.service import get_full_token


async def require_full_token(name: str, session: AsyncSession = Depends(get_session)):
    token = await get_full_token(session, name)

    if token is None:
        raise Abort("token", "not-found")

    return token
