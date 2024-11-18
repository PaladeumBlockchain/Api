from tests.client_requests import addresses

async def test_normal(client, address_transaction):
    response = await addresses.get_address_transactions(
        client=client,
        address=address_transaction.addresses[0],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 1, "pages": 1, "page": 1}

    transaction_data = response.json()["list"][0]

    assert transaction_data["blockhash"] == address_transaction.blockhash
    assert transaction_data["amount"] == address_transaction.amount
    assert transaction_data["height"] == address_transaction.height
    assert transaction_data["txid"] == address_transaction.txid


async def test_none(client, address):
    response = await addresses.get_address_transactions(
        client=client,
        address=address.address,
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []
