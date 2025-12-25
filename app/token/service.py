from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AddressBalance, Token
from app.utils import get_token_icon


async def count_tokens(session: AsyncSession):
    return (
        await session.scalar(
            select(func.count(Token.id)).filter(Token.type.in_(("root", "sub")))
        )
        or 0
    )


async def list_tokens(session: AsyncSession, offset: int, limit: int):
    items = await session.scalars(
        select(Token)
        .filter(Token.type.in_(("root", "sub")))
        .offset(offset)
        .limit(limit)
        .order_by(Token.height.asc())
    )

    # Little shenanigan to set attribute in comprehension
    result: list[Token] = []
    for token in items:
        setattr(token, "icon", get_token_icon(token.name))

        holders = await session.scalar(
            select(func.count(AddressBalance.id)).filter(
                AddressBalance.currency == token.name, AddressBalance.balance > 0
            )
        )
        setattr(token, "holders", holders)
        result.append(token)

    return result


async def list_token_names(session: AsyncSession):
    items = await session.scalars(
        select(Token.name)
        .filter(Token.type.in_(("root", "sub")))
        .order_by(Token.height.asc())
    )

    return items.all()


async def get_full_token(session: AsyncSession, name: str):
    token = await session.scalar(select(Token).filter(Token.name == name))

    if token is None:
        return token

    holders = await session.scalar(
        select(func.count(AddressBalance.id)).filter(
            AddressBalance.currency == name, AddressBalance.balance > 0
        )
    )

    setattr(token, "icon", get_token_icon(token.name))
    setattr(token, "holders", holders)

    return token
