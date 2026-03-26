from tests.client_requests import addresses
from tests import helpers
import secrets


async def test_normal(client, mempool_transaction):
    response = await addresses.post_address_transactions_multi_mempool(
        client=client,
        addresses=mempool_transaction["addresses"],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 1, "pages": 1, "page": 1}

    transaction_data = response.json()["list"][0]
    assert transaction_data["txid"] == mempool_transaction["txid"]
    assert transaction_data["height"] is None
    assert transaction_data["confirmations"] == 0


async def test_no_matching_addresses(client, mempool_transaction, session):
    # mempool_transaction ensures a MemPool record exists
    other_address = secrets.token_hex(20)

    response = await addresses.post_address_transactions_multi_mempool(
        client=client,
        addresses=[other_address],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []


async def test_multiple_addresses(client, session):
    addr1 = secrets.token_hex(20)
    addr2 = secrets.token_hex(20)

    _, tx1 = await helpers.create_mempool_transaction(session, address=addr1)
    _, tx2 = await helpers.create_mempool_transaction(session, address=addr2)

    # Each address alone returns only its own transaction
    response1 = await addresses.post_address_transactions_multi_mempool(
        client=client, addresses=[addr1]
    )
    assert response1.status_code == 200
    assert response1.json()["pagination"]["total"] == 1
    assert response1.json()["list"][0]["txid"] == tx1["txid"]

    response2 = await addresses.post_address_transactions_multi_mempool(
        client=client, addresses=[addr2]
    )
    assert response2.status_code == 200
    assert response2.json()["pagination"]["total"] == 1
    assert response2.json()["list"][0]["txid"] == tx2["txid"]

    # Both addresses together return both transactions
    response = await addresses.post_address_transactions_multi_mempool(
        client=client, addresses=[addr1, addr2]
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json()["pagination"] == {"total": 2, "pages": 1, "page": 1}

    txids = {tx["txid"] for tx in response.json()["list"]}
    assert tx1["txid"] in txids
    assert tx2["txid"] in txids


async def test_empty_addresses(client, mempool_transaction):
    # mempool_transaction ensures a MemPool record exists
    response = await addresses.post_address_transactions_multi_mempool(
        client=client,
        addresses=[],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []
