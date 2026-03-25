from sqlalchemy.ext.asyncio import AsyncSession
from app.settings import get_settings
from app.parser import make_request
from .utils import get_block_reward
from app.models import Transaction
from sqlalchemy import select
from app.errors import Abort
import typing


async def check_addresses(session: AsyncSession, addresses: list[str]):
    valid_addresses: list[str] = []

    for address in addresses:
        tx = await session.scalar(
            select(Transaction)
            .filter(Transaction.addresses.contains([address]))
            .limit(1)
        )

        if tx is not None:
            valid_addresses.append(address)

    return valid_addresses


async def get_wallet_info() -> dict[str, typing.Any]:
    settings = get_settings()
    endpoint = settings.blockchain.endpoint

    response = await make_request(
        endpoint, {"id": "info", "method": "getblockchaininfo", "params": []}
    )
    if not response["result"] or response["error"]:
        raise Abort("wallet", "inaccessible-node")

    blockchain_info: dict[str, typing.Any] = response["result"]

    response = await make_request(
        endpoint, {"id": "mempool", "method": "getmempoolinfo", "params": []}
    )
    if not response["result"] or response["error"]:
        raise Abort("wallet", "inaccessible-node")

    mempool_info = response["result"]

    response = await make_request(
        endpoint,
        {
            "id": "nethash",
            "method": "getnetworkhashps",
            "params": [120, blockchain_info["blocks"]],
        },
    )
    if not response["result"] or response["error"]:
        raise Abort("wallet", "inaccessible-node")

    nethash = int(response["result"])

    return {
        "chain": blockchain_info["chain"],
        "blocks": blockchain_info["blocks"],
        "headers": blockchain_info["headers"],
        "bestblockhash": blockchain_info["bestblockhash"],
        "difficulty": blockchain_info["difficulty"],
        "mediantime": blockchain_info["mediantime"],
        "chainwork": blockchain_info["chainwork"],
        "reward": get_block_reward(blockchain_info["blocks"]),
        "mempool": mempool_info["size"],
        "nethash": nethash,
    }
