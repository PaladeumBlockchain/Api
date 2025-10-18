from async_asgi_testclient.response import Response
from async_asgi_testclient import TestClient


async def get_unspent_address_outputs(
    client: TestClient, address: str, currency: str, page: int = 1
) -> Response:
    return await client.get(
        f"/address/{address}/outputs/{currency}",
        query_string={"page": page},
    )


async def get_address_utxo(
    client: TestClient, address: str, amount: float, currency: str, page: int = 1
):
    """Do not confuse get_unspent_address_outputs with this function (this may sound similar, but its not the same)"""
    return await client.get(
        f"/address/{address}/utxo/{currency}",
        query_string={"amount": amount, "page": page},
    )


async def get_address_transactions(
    client: TestClient, address: str, page: int = 1
) -> Response:
    return await client.get(
        f"/address/{address}/transactions", query_string={"page": page}
    )


async def list_address_transactions_ticker(
    client: TestClient, address: str, ticker: str, page: int = 1
) -> Response:
    return await client.get(
        f"/address/{address}/transactions/{ticker}", query_string={"page": page}
    )


async def get_address_balances(
    client: TestClient, address: str, page: int = 1
) -> Response:
    return await client.get(f"/address/{address}/balances", query_string={"page": page})
