from tests.client_requests import transactions


async def test_plb_none(client):
    response = await transactions.list_transactions(client, "plb")
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []


async def test_plb(client, transaction, session):
    response = await transactions.list_transactions(client, "plb")
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 1, "pages": 1, "page": 1}
    transaction_data = response.json()["list"][0]

    assert transaction_data["blockhash"] == transaction.blockhash
    assert transaction_data["amount"] == transaction.amount
    assert transaction_data["height"] == transaction.height
    assert transaction_data["txid"] == transaction.txid