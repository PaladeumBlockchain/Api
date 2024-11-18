from async_asgi_testclient import TestClient


async def get_unspent_address_outputs(
    client: TestClient, address: str, currency: str, page: int = 1
):
    return await client.get(
        f"/address/{address}/outputs/{currency}",
        query_string={"page": page},
    )


async def get_address_transactions(
    client: TestClient, address: str, page: int = 1
):
    return await client.get(
        f"/address/{address}/transactions", query_string={"page": page}
    )
