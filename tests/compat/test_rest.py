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


# --- /compat/balance/<address> ---


async def test_balance_empty(client):
    response = await compat.get_balance(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["balance"] == 0.0
    assert result["locked"] == 0.0
    assert result["tokens"] == []


async def test_balance_with_data(client, session, address):
    await helpers.create_address_balance(session, address, "PLB", 100)
    response = await compat.get_balance(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["balance"] == 100.0
    assert result["locked"] == 0.0
    assert result["total"] == 0  # no non-PLB tokens


async def test_balance_with_token(client, session, address):
    await helpers.create_address_balance(session, address, "PLB", 50)
    await helpers.create_address_balance(session, address, "MYTOKEN", 25)
    response = await compat.get_balance(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["balance"] == 50.0
    token_names = [t["tokenName"] for t in result["tokens"]]
    assert "MYTOKEN" in token_names


# --- /compat/history/<address> ---


async def test_history_empty(client):
    response = await compat.get_history(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["txcount"] == 0
    assert result["tx"] == []


async def test_history_with_transactions(client, session, address):
    tx = await helpers.create_transaction(session, addresses=[address.address])
    response = await compat.get_history(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["txcount"] == 1
    assert tx.txid in result["tx"]


# --- /compat/mempool/<address> ---


async def test_address_mempool_empty(client):
    response = await compat.get_address_mempool(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["txcount"] == 0
    assert result["tx"] == []


# --- /compat/unspent/<address> ---


async def test_unspent_empty(client):
    response = await compat.get_unspent(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_unspent_with_outputs(client, session, address):
    txid = secrets.token_hex(32)
    await helpers.create_output(
        session,
        currency="PLB",
        shortcut=f"{txid}:0",
        address=address.address,
        txid=txid,
        amount=10.0,
        spent=False,
        index=0,
    )
    response = await compat.get_unspent(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    assert result[0]["txid"] == txid
    assert result[0]["value"] == 1_000_000_000  # 10.0 PLB in satoshi
    assert result[0]["index"] == 0


async def test_unspent_spent_excluded(client, session, address):
    txid = secrets.token_hex(32)
    await helpers.create_output(
        session,
        shortcut=f"{txid}:0",
        address=address.address,
        txid=txid,
        spent=True,
        index=0,
    )
    response = await compat.get_unspent(client, address.address)
    data = assert_compat_ok(response)
    assert data["result"] == []


# --- /compat/height/<height> ---


async def test_block_by_height(client, block):
    response = await compat.get_block_by_height(client, block.height)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["hash"] == block.blockhash
    assert result["height"] == block.height
    assert result["time"] == block.timestamp


async def test_block_by_height_not_found(client):
    response = await compat.get_block_by_height(client, 999999)
    data = assert_compat_ok(response, 404)
    assert data["result"] is None
    assert data["error"] is not None


# --- /compat/hash/<height> ---


async def test_block_hash_by_height(client, block):
    response = await compat.get_block_hash(client, block.height)
    data = assert_compat_ok(response)
    assert data["result"] == block.blockhash


async def test_block_hash_not_found(client):
    response = await compat.get_block_hash(client, 999999)
    assert response.status_code == 404


# --- /compat/block/<bhash> ---


async def test_block_by_hash(client, block):
    response = await compat.get_block_by_hash(client, block.blockhash)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["hash"] == block.blockhash
    assert result["height"] == block.height


async def test_block_by_hash_not_found(client):
    response = await compat.get_block_by_hash(client, secrets.token_hex(32))
    assert response.status_code == 404


# --- /compat/range/<height> ---


async def test_block_range(client, session):
    blocks = [
        await helpers.create_block(session, height=i) for i in range(1, 6)
    ]
    response = await compat.get_block_range(client, 1)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) >= 1
    hashes = [b["hash"] for b in result]
    assert blocks[0].blockhash in hashes


async def test_block_range_empty(client):
    response = await compat.get_block_range(client, 999999)
    data = assert_compat_ok(response)
    assert data["result"] == []


# --- /compat/supply ---


async def test_supply(client, block):
    response = await compat.get_supply(client)
    data = assert_compat_ok(response)
    result = data["result"]
    assert isinstance(result["supply"], int)
    assert isinstance(result["halvings"], int)
    assert result["height"] == block.height


# --- /compat/mempool ---


async def test_mempool_empty(client):
    response = await compat.get_mempool(client)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["size"] == 0
    assert result["tx"] == []


# --- /compat/tokens ---


async def test_tokens_empty(client):
    response = await compat.get_tokens(client)
    data = assert_compat_ok(response)
    assert data["result"] == {}


# --- /compat/transaction/<thash> ---


async def test_transaction_not_found(client):
    response = await compat.get_transaction(client, secrets.token_hex(32))
    assert response.status_code == 404
    data = response.json()
    assert data["result"] is None
    assert data["error"] is not None
