from async_asgi_testclient import TestClient


# REST group


async def get_info(client: TestClient):
    return await client.get("/compat/info")


async def get_block_by_height(client: TestClient, height: int, offset: int = 0):
    return await client.get(
        f"/compat/height/{height}", query_string={"offset": offset}
    )


async def get_block_hash(client: TestClient, height: int):
    return await client.get(f"/compat/hash/{height}")


async def get_block_range(client: TestClient, height: int, offset: int = 0):
    return await client.get(
        f"/compat/range/{height}", query_string={"offset": offset}
    )


async def get_block_by_hash(client: TestClient, bhash: str, offset: int = 0):
    return await client.get(
        f"/compat/block/{bhash}", query_string={"offset": offset}
    )


async def get_block_header(client: TestClient, bhash: str):
    return await client.get(f"/compat/header/{bhash}")


async def get_transaction(client: TestClient, thash: str):
    return await client.get(f"/compat/transaction/{thash}")


async def get_balance(client: TestClient, address: str):
    return await client.get(f"/compat/balance/{address}")


async def get_history(client: TestClient, address: str, offset: int = 0):
    return await client.get(
        f"/compat/history/{address}", query_string={"offset": offset}
    )


async def get_address_mempool(client: TestClient, address: str):
    return await client.get(f"/compat/mempool/{address}")


async def get_unspent(client: TestClient, address: str, token: str = "PLB"):
    return await client.get(
        f"/compat/unspent/{address}", query_string={"token": token}
    )


async def get_mempool(client: TestClient):
    return await client.get("/compat/mempool")


async def get_supply(client: TestClient):
    return await client.get("/compat/supply")


async def get_tokens(client: TestClient, offset: int = 0, count: int = 10):
    return await client.get(
        "/compat/tokens", query_string={"offset": offset, "count": count}
    )


async def get_fee(client: TestClient):
    return await client.get("/compat/fee")


async def broadcast(client: TestClient, raw: str):
    return await client.post("/compat/broadcast", query_string={"raw": raw})


async def verify(client: TestClient, address: str, signature: str, message: str):
    return await client.post(
        "/compat/verify",
        json={"address": address, "signature": signature, "message": message},
    )


# Wallet group


async def wallet_balance(client: TestClient, address: str):
    return await client.get(f"/compat/wallet/balance/{address}")


async def wallet_history(
    client: TestClient,
    addresses: list[str],
    count: int = 10,
):
    return await client.post(
        "/compat/wallet/history",
        json={"addresses": addresses, "count": count},
    )


async def wallet_transaction(client: TestClient, txid: str):
    return await client.get(f"/compat/wallet/transaction/{txid}")


async def wallet_check(client: TestClient, addresses: list[str]):
    return await client.post("/compat/wallet/check", json={"addresses": addresses})


async def wallet_utxo(client: TestClient, outputs: list[dict]):
    return await client.post("/compat/wallet/utxo", json={"outputs": outputs})


async def wallet_broadcast(client: TestClient, raw: str):
    return await client.post("/compat/wallet/broadcast", json={"raw": raw})


# V2 group


async def v2_latest(client: TestClient):
    return await client.get("/compat/v2/latest")


async def v2_transactions(client: TestClient, token: str = "PLB", page: int = 1):
    path = f"/compat/v2/transactions/{token}" if token != "PLB" else "/compat/v2/transactions"
    return await client.get(path, query_string={"page": page})


async def v2_blocks(client: TestClient, page: int = 1):
    return await client.get("/compat/v2/blocks", query_string={"page": page})


async def v2_block(client: TestClient, bhash: str):
    return await client.get(f"/compat/v2/block/{bhash}")


async def v2_block_transactions(client: TestClient, bhash: str, page: int = 1):
    return await client.get(
        f"/compat/v2/block/{bhash}/transactions", query_string={"page": page}
    )


async def v2_transaction(client: TestClient, txid: str):
    return await client.get(f"/compat/v2/transaction/{txid}")


async def v2_history(client: TestClient, address: str, page: int = 1):
    return await client.get(
        f"/compat/v2/history/{address}", query_string={"page": page}
    )


async def v2_stats(client: TestClient, address: str):
    return await client.get(f"/compat/v2/stats/{address}")


async def v2_richlist(client: TestClient, token: str = "PLB", page: int = 1):
    path = f"/compat/v2/richlist/{token}" if token != "PLB" else "/compat/v2/richlist"
    return await client.get(path, query_string={"page": page})


async def v2_balance(client: TestClient, address: str):
    return await client.get(f"/compat/v2/balance/{address}")


async def v2_mempool(client: TestClient):
    return await client.get("/compat/v2/mempool")


async def v2_token(client: TestClient, name: str):
    return await client.get(f"/compat/v2/token/{name}")


async def v2_broadcast(client: TestClient, raw: str):
    return await client.post("/compat/v2/broadcast", json={"raw": raw})
