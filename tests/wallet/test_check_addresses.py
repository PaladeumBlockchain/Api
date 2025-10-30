from async_asgi_testclient import TestClient

from app.models import Transaction


async def test_plb(client: TestClient, transaction: Transaction):
    response = await client.post(
        "/wallet/check", json=[transaction.addresses[0], "Invalid-address"]
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json() == [transaction.addresses[0]]
