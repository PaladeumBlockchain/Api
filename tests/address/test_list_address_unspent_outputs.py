from app.utils import to_satoshi, utcnow, to_timestamp
from sqlalchemy.ext.asyncio import AsyncSession
from tests.client_requests import addresses
from datetime import timedelta
from app.models import Output
from tests import helpers


async def test_normal(client, address_utxo: Output, session: AsyncSession):
    # Create locked output
    await helpers.create_output(
        session,
        address=address_utxo.address,
        txid="address txid",
        amount=100,
        timelock=to_timestamp(utcnow() + timedelta(seconds=300)),
        shortcut="pecpecpec",
    )
    response = await addresses.get_unspent_address_outputs(
        client, address_utxo.address, "PLB"
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 1, "pages": 1, "page": 1}

    utxo = response.json()["list"][0]

    assert utxo["txid"] == address_utxo.txid
    assert utxo["currency"] == address_utxo.currency
    assert utxo["amount"] == to_satoshi(address_utxo.amount)  # type: ignore
    assert utxo["timelock"] == address_utxo.timelock
    assert utxo["type"] == address_utxo.type
    assert utxo["spent"] == address_utxo.spent
    assert utxo["index"] == address_utxo.index


async def test_none(client, address):
    response = await addresses.get_unspent_address_outputs(
        client, address.address, "PLB"
    )
    print(response.json())
    assert response.status_code == 200

    assert response.json()["pagination"] == {"total": 0, "pages": 0, "page": 1}
    assert response.json()["list"] == []
