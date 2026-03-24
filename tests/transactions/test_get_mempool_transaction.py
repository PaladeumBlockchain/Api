from tests.client_requests import transactions


async def test_normal(client, block, mempool_transaction):
    response = await transactions.get_transaction_info(
        client, mempool_transaction["txid"]
    )
    print(response.json())
    assert response.status_code == 200

    data = response.json()
    assert data["txid"] == mempool_transaction["txid"]
    assert data["height"] is None
    assert data["confirmations"] == 0
    assert data["coinbase"] is False
    assert data["coinstake"] is False


async def test_not_found(client, block):
    response = await transactions.get_transaction_info(
        client, "aabbccdd112233445566778899"
    )
    assert response.status_code == 404
    assert response.json()["code"] == "transactions:not_found"
