from async_asgi_testclient import TestClient
from decimal import Decimal

from app.models import AddressBalance


async def test_list_no_address(
    client: TestClient, currency: str, addresses_balances: list[AddressBalance]
):
    response = await client.get(f"/holders/{currency}")
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {
        "page": 1,
        "pages": 1,
        "total": len(addresses_balances),
    }
    assert response.json()["list"] != []

    index = {holder.address.address: holder for holder in addresses_balances}
    total_balance = Decimal(sum(b.balance for b in addresses_balances))

    for item in response.json()["list"]:
        assert item["percentage"] == float(
            Decimal(str(item["balance"])) / total_balance * 100
        )
        assert item["balance"] == index[item["address"]].balance
        assert item["txcount"] == 0
