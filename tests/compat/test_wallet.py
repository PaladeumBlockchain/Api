import secrets
from tests.client_requests import compat
from tests import helpers


def assert_compat_ok(response, status_code=200):
    assert response.status_code == status_code
    data = response.json()
    assert "error" in data
    assert "id" in data
    assert "result" in data
    return data


# --- /compat/wallet/balance/<address> ---


async def test_wallet_balance_empty(client):
    response = await compat.wallet_balance(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_wallet_balance_with_data(client, session, address):
    await helpers.create_address_balance(session, address, "PLB", 100)
    response = await compat.wallet_balance(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    assert result[0]["currency"] == "PLB"
    # 100 coins in satoshi
    assert result[0]["balance"] == 10_000_000_000
    assert result[0]["locked"] == 0
    assert "units" in result[0]


async def test_wallet_balance_multiple_currencies(client, session, address):
    await helpers.create_address_balance(session, address, "PLB", 50)
    await helpers.create_address_balance(session, address, "TOKEN1", 10)
    response = await compat.wallet_balance(client, address.address)
    data = assert_compat_ok(response)
    currencies = [b["currency"] for b in data["result"]]
    assert "PLB" in currencies
    assert "TOKEN1" in currencies


# --- /compat/wallet/check ---


async def test_wallet_check_no_matches(client):
    response = await compat.wallet_check(
        client, [secrets.token_hex(32), secrets.token_hex(32)]
    )
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_wallet_check_with_match(client, session, address):
    tx = await helpers.create_transaction(session, addresses=[address.address])
    unknown = secrets.token_hex(32)
    response = await compat.wallet_check(client, [address.address, unknown])
    data = assert_compat_ok(response)
    assert address.address in data["result"]
    assert unknown not in data["result"]


# --- /compat/wallet/history ---


async def test_wallet_history_empty(client):
    response = await compat.wallet_history(client, [secrets.token_hex(32)])
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_wallet_history_with_transaction(client, session, address):
    await helpers.create_transaction(session, addresses=[address.address])
    response = await compat.wallet_history(client, [address.address])
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    tx = result[0]
    assert "txid" in tx
    assert "outputs" in tx
    assert "inputs" in tx
    assert "timestamp" in tx
    assert "fee" in tx
    assert "amount" in tx
    assert tx["mempool"] is False


async def test_wallet_history_satoshi_amounts(client, session, address):
    await helpers.create_transaction(
        session, addresses=[address.address], amount={"PLB": 5.0}
    )
    response = await compat.wallet_history(client, [address.address])
    data = assert_compat_ok(response)
    tx = data["result"][0]
    # amount should be satoshi integer, not float
    assert isinstance(tx["amount"], int)


# --- /compat/wallet/transaction/<txid> ---


async def test_wallet_transaction_not_found(client):
    response = await compat.wallet_transaction(client, secrets.token_hex(32))
    assert response.status_code == 404
    data = response.json()
    assert data["result"] is None
    assert data["error"] is not None


async def test_wallet_transaction_found(client, session):
    tx = await helpers.create_transaction(session)
    response = await compat.wallet_transaction(client, tx.txid)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["txid"] == tx.txid
    assert "outputs" in result
    assert "inputs" in result


# --- /compat/wallet/utxo ---


async def test_wallet_utxo_empty(client):
    response = await compat.wallet_utxo(
        client, [{"txid": secrets.token_hex(32), "index": 0}]
    )
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_wallet_utxo_found(client, session, address):
    txid = secrets.token_hex(32)
    await helpers.create_output(
        session,
        currency="PLB",
        shortcut=f"{txid}:0",
        address=address.address,
        txid=txid,
        amount=5.0,
        spent=False,
        index=0,
    )
    response = await compat.wallet_utxo(client, [{"txid": txid, "index": 0}])
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    assert result[0]["txid"] == txid
    assert result[0]["amount"] == 500_000_000  # 5.0 in satoshi
    assert result[0]["currency"] == "PLB"
    assert result[0]["spent"] is False
