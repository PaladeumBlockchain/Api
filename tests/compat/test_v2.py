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


# --- /compat/v2/latest ---


async def test_v2_latest_no_blocks(client):
    response = await compat.v2_latest(client)
    data = assert_compat_ok(response)
    assert data["result"] is None


async def test_v2_latest_with_block(client, block):
    response = await compat.v2_latest(client)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["blockhash"] == block.blockhash
    assert result["height"] == block.height
    assert result["reward"] == float(block.reward)


# --- /compat/v2/blocks ---


async def test_v2_blocks_empty(client):
    response = await compat.v2_blocks(client)
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_v2_blocks_list(client, session):
    b1 = await helpers.create_block(session, height=1)
    b2 = await helpers.create_block(session, height=2)
    response = await compat.v2_blocks(client)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 2
    hashes = [b["blockhash"] for b in result]
    assert b1.blockhash in hashes
    assert b2.blockhash in hashes


async def test_v2_blocks_shape(client, block):
    response = await compat.v2_blocks(client)
    data = assert_compat_ok(response)
    b = data["result"][0]
    assert "blockhash" in b
    assert "height" in b
    assert "timestamp" in b
    assert "tx" in b


# --- /compat/v2/block/<bhash> ---


async def test_v2_block_by_hash(client, block):
    response = await compat.v2_block(client, block.blockhash)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["blockhash"] == block.blockhash
    assert result["height"] == block.height
    assert result["reward"] == float(block.reward)


async def test_v2_block_not_found(client):
    response = await compat.v2_block(client, secrets.token_hex(32))
    assert response.status_code == 404
    data = response.json()
    assert data["result"] is None


# --- /compat/v2/block/<bhash>/transactions ---


async def test_v2_block_transactions_empty(client, block):
    response = await compat.v2_block_transactions(client, block.blockhash)
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_v2_block_transactions(client, block_transaction, block):
    response = await compat.v2_block_transactions(client, block.blockhash)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    assert result[0]["txid"] == block_transaction.txid


async def test_v2_block_transactions_block_not_found(client):
    response = await compat.v2_block_transactions(client, secrets.token_hex(32))
    assert response.status_code == 404


# --- /compat/v2/transaction/<txid> ---


async def test_v2_transaction_not_found(client):
    response = await compat.v2_transaction(client, secrets.token_hex(32))
    assert response.status_code == 404
    data = response.json()
    assert data["result"] is None


async def test_v2_transaction_found(client, session):
    tx = await helpers.create_transaction(session)
    response = await compat.v2_transaction(client, tx.txid)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["txid"] == tx.txid
    assert result["blockhash"] == tx.blockhash
    assert "outputs" in result
    assert "inputs" in result
    assert "fee" in result
    assert result["mempool"] is False


async def test_v2_transaction_shape(client, session):
    tx = await helpers.create_transaction(session, amount={"PLB": 7.5})
    response = await compat.v2_transaction(client, tx.txid)
    data = assert_compat_ok(response)
    result = data["result"]
    # v2 amounts are floats, not satoshi
    assert isinstance(result["fee"], float)
    assert isinstance(result["amount"], float)


# --- /compat/v2/transactions ---


async def test_v2_transactions_empty(client):
    response = await compat.v2_transactions(client)
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_v2_transactions_list(client, session):
    tx = await helpers.create_transaction(session, currencies=["PLB"])
    response = await compat.v2_transactions(client)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    assert result[0]["txhash"] == tx.txid
    assert "blockhash" in result[0]
    assert "height" in result[0]
    assert "timestamp" in result[0]
    assert "amount" in result[0]


async def test_v2_transactions_by_token(client, session):
    await helpers.create_transaction(session, currencies=["PLB"])
    await helpers.create_transaction(session, currencies=["MYTOKEN"])
    response = await compat.v2_transactions(client, token="MYTOKEN")
    data = assert_compat_ok(response)
    assert len(data["result"]) == 1


# --- /compat/v2/history/<address> ---


async def test_v2_history_empty(client):
    response = await compat.v2_history(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_v2_history_with_transaction(client, session, address):
    tx = await helpers.create_transaction(session, addresses=[address.address])
    response = await compat.v2_history(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    assert result[0]["txid"] == tx.txid


# --- /compat/v2/stats/<address> ---


async def test_v2_stats_empty(client):
    response = await compat.v2_stats(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["transactions"] == 0
    assert "tokens" in result


async def test_v2_stats_with_transactions(client, session, address):
    await helpers.create_transaction(
        session, addresses=[address.address], currencies=["PLB"]
    )
    await helpers.create_transaction(
        session, addresses=[address.address], currencies=["TOKEN1"]
    )
    response = await compat.v2_stats(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["transactions"] == 2


# --- /compat/v2/balance/<address> ---


async def test_v2_balance_empty(client):
    response = await compat.v2_balance(client, secrets.token_hex(32))
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_v2_balance_with_data(client, session, address):
    await helpers.create_address_balance(session, address, "PLB", 100)
    response = await compat.v2_balance(client, address.address)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) == 1
    assert result[0]["currency"] == "PLB"
    # v2 uses floats
    assert result[0]["balance"] == 100.0
    assert result[0]["locked"] == 0.0


# --- /compat/v2/richlist ---


async def test_v2_richlist_empty(client):
    response = await compat.v2_richlist(client)
    data = assert_compat_ok(response)
    assert data["result"] == []


async def test_v2_richlist_sorted(client, addresses_balances):
    response = await compat.v2_richlist(client)
    data = assert_compat_ok(response)
    result = data["result"]
    assert len(result) > 0
    balances = [r["balance"] for r in result]
    assert balances == sorted(balances, reverse=True)
    assert "address" in result[0]
    assert "balance" in result[0]


# --- /compat/v2/mempool ---


async def test_v2_mempool_empty(client):
    response = await compat.v2_mempool(client)
    data = assert_compat_ok(response)
    result = data["result"]
    assert result["size"] == 0
    assert result["tx"] == []


# --- /compat/v2/token/<name> ---


async def test_v2_token_not_found(client):
    response = await compat.v2_token(client, "DOESNOTEXIST")
    assert response.status_code == 404
    data = response.json()
    assert data["result"] is None
