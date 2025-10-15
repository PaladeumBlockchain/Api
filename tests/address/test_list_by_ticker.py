from app.models.transaction import Transaction
from tests.client_requests import addresses
from app.utils import to_satoshi


async def test_normal(client, block, address_transaction: Transaction):
    response = await addresses.list_address_transactions_ticker(
        client=client,
        address=address_transaction.addresses[0],
        ticker=address_transaction.currencies[0],
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 1, "pages": 1, "page": 1}

    transaction_data = response.json()["list"][0]

    assert transaction_data["blockhash"] == address_transaction.blockhash
    assert transaction_data["amount"] == {
        token: to_satoshi(amount)
        for token, amount in address_transaction.amount.items()
    }
    assert transaction_data["height"] == address_transaction.height
    assert transaction_data["txid"] == address_transaction.txid


async def test_not_exist(client, block, address_transaction):
    response = await addresses.list_address_transactions_ticker(
        client=client,
        address=address_transaction.addresses[0],
        ticker="non existent ticker",
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}

    assert response.json()["list"] == []
