from tests.client_requests import addresses
from app.utils import to_satoshi
from tests import helpers
import secrets


async def test_normal(client, block, address_transaction):
    response = await addresses.post_address_transactions_multi(
        client=client,
        addresses=address_transaction.addresses,
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 1, "pages": 1, "page": 1}

    transaction_data = response.json()["list"][0]

    assert transaction_data["txid"] == address_transaction.txid
    assert transaction_data["blockhash"] == address_transaction.blockhash
    assert transaction_data["height"] == address_transaction.height
    assert transaction_data["amount"] == {
        token: to_satoshi(amount)
        for token, amount in address_transaction.amount.items()
    }


async def test_multiple_addresses(client, block, session):
    addr1 = secrets.token_hex(20)
    addr2 = secrets.token_hex(20)

    tx1 = await helpers.create_transaction(session, addresses=[addr1])
    tx2 = await helpers.create_transaction(session, addresses=[addr2])

    # Each address alone returns only its own transaction
    response1 = await addresses.post_address_transactions_multi(
        client=client, addresses=[addr1]
    )
    assert response1.json()["pagination"]["total"] == 1
    assert response1.json()["list"][0]["txid"] == tx1.txid

    response2 = await addresses.post_address_transactions_multi(
        client=client, addresses=[addr2]
    )
    assert response2.json()["pagination"]["total"] == 1
    assert response2.json()["list"][0]["txid"] == tx2.txid

    # Both addresses together return both transactions
    response = await addresses.post_address_transactions_multi(
        client=client, addresses=[addr1, addr2]
    )
    print(response.json())
    assert response.status_code == 200
    assert response.json()["pagination"] == {"total": 2, "pages": 1, "page": 1}

    txids = {tx["txid"] for tx in response.json()["list"]}
    assert tx1.txid in txids
    assert tx2.txid in txids


async def test_with_currency(client, block, address_transaction):
    response = await addresses.post_address_transactions_multi(
        client=client,
        addresses=address_transaction.addresses,
        currency=address_transaction.currencies[0],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 1, "pages": 1, "page": 1}
    assert response.json()["list"][0]["txid"] == address_transaction.txid


async def test_with_currency_not_match(client, block, address_transaction):
    response = await addresses.post_address_transactions_multi(
        client=client,
        addresses=address_transaction.addresses,
        currency="NONEXISTENT",
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []


async def test_no_matching_addresses(client, block):
    response = await addresses.post_address_transactions_multi(
        client=client,
        addresses=["nonexistent_address_1", "nonexistent_address_2"],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []


async def test_empty_addresses(client, block):
    response = await addresses.post_address_transactions_multi(
        client=client,
        addresses=[],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []
