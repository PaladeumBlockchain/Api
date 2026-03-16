from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.parser import make_request
from app.settings import get_settings
from app.blocks import service as blocks_service
from app.address import service as address_service
from app.transactions import service as tx_service
from app.token import service as token_service

from .schemas import compat_response, compat_error
from . import service as compat_service

router = APIRouter(tags=["Compat"])


def _block_shape(block) -> dict:
    return {
        "hash": block.blockhash,
        "height": block.height,
        "time": block.timestamp,
        "prevblock": block.prev_blockhash,
        "tx": block.transactions,
        "txcount": block.tx,
        "reward": float(block.reward),
        # fields not stored in new DB
        "version": None,
        "merkleroot": None,
        "bits": None,
        "nonce": None,
        "stake": None,
    }


def _reward(height: int) -> int:
    halvings = height // 525960
    if halvings >= 10:
        return 0
    return int(4 * 10**8 // (2**halvings))


@router.get("/info")
async def get_info():
    settings = get_settings()
    endpoint = settings.blockchain.endpoint

    result = await make_request(
        endpoint, {"id": "info", "method": "getblockchaininfo", "params": []}
    )
    data = result.get("result") or {}

    for key in ("verificationprogress", "pruned", "softforks", "bip9_softforks", "warnings", "size_on_disk"):
        data.pop(key, None)

    height = data.get("blocks", 0)
    data["reward"] = _reward(height)
    data["mempool"] = 0
    data["nethash"] = None

    mempool_info = await make_request(
        endpoint, {"id": "mempool", "method": "getmempoolinfo", "params": []}
    )
    if not mempool_info.get("error"):
        data["mempool"] = mempool_info.get("result", {}).get("size", 0)

    nethash = await make_request(
        endpoint, {"id": "nethash", "method": "getnetworkhashps", "params": [120, height]}
    )
    if not nethash.get("error"):
        data["nethash"] = int(nethash.get("result", 0))

    return compat_response(data)


@router.get("/height/{height}")
async def get_block_by_height(
    height: int,
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    block = await blocks_service.get_block_by_height(session, height)
    if block is None:
        return JSONResponse(status_code=404, content=compat_error("Block not found"))
    shape = _block_shape(block)
    shape["tx"] = block.transactions[offset : offset + 10]
    return compat_response(shape)


@router.get("/hash/{height}")
async def get_block_hash(
    height: int,
    session: AsyncSession = Depends(get_session),
):
    block = await blocks_service.get_block_by_height(session, height)
    if block is None:
        return JSONResponse(status_code=404, content=compat_error("Block not found"))
    return compat_response(block.blockhash)


@router.get("/range/{height}")
async def get_block_range(
    height: int,
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    limit = min(100, 10)
    blocks_list = await compat_service.get_blocks_from_height(
        session, height, offset, limit
    )
    return compat_response([_block_shape(b) for b in blocks_list])


@router.get("/block/{bhash}")
async def get_block_by_hash(
    bhash: str,
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    block = await blocks_service.get_block_by_hash(session, bhash)
    if block is None:
        return JSONResponse(status_code=404, content=compat_error("Block not found"))
    shape = _block_shape(block)
    shape["tx"] = block.transactions[offset : offset + 10]
    return compat_response(shape)


@router.get("/header/{bhash}")
async def get_block_header(bhash: str):
    settings = get_settings()
    result = await make_request(
        settings.blockchain.endpoint,
        {"id": "header", "method": "getblockheader", "params": [bhash]},
    )
    return compat_response(result.get("result"))


@router.get("/transaction/{thash}")
async def get_transaction(
    thash: str,
    session: AsyncSession = Depends(get_session),
):
    tx = await tx_service.get_transaction_by_txid(session, thash)
    if tx is None:
        return JSONResponse(
            status_code=404, content=compat_error("Transaction not found")
        )
    return compat_response(_tx_shape(tx))


@router.get("/balance/{address_str}")
async def get_balance(
    address_str: str,
    session: AsyncSession = Depends(get_session),
):
    balances = await address_service.list_balances(session, address_str)
    plb = next((b for b in balances if b.currency == "PLB"), None)
    tokens = [
        {
            "tokenName": b.currency,
            "balance": float(b.balance),
            "locked": float(b.locked),
            "received": float(b.balance + b.locked),
        }
        for b in balances
        if b.currency != "PLB"
    ]
    return compat_response(
        {
            "received": float(plb.balance + plb.locked) if plb else 0.0,
            "balance": float(plb.balance) if plb else 0.0,
            "locked": float(plb.locked) if plb else 0.0,
            "tokens": tokens,
            "total": len(tokens),
        }
    )


@router.get("/history/{address_str}")
async def get_history(
    address_str: str,
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    limit = 10
    txs = await address_service.list_transactions(
        session, address_str, limit, offset
    )
    total = await address_service.count_transactions(session, address_str)
    return compat_response(
        {
            "tx": [t.txid for t in txs],
            "txcount": total,
        }
    )


@router.get("/mempool/{address_str}")
async def get_address_mempool(
    address_str: str,
    session: AsyncSession = Depends(get_session),
):
    txs = await address_service.list_address_mempool_transactions(
        session, address_str
    )
    return compat_response(
        {
            "tx": [
                {
                    "txid": t["txid"],
                    "value": float(t["amount"].get("PLB", 0)),
                    "timestamp": t.get("timestamp"),
                }
                for t in txs
            ],
            "txcount": len(txs),
        }
    )


@router.get("/unspent/{address_str}")
async def get_unspent(
    address_str: str,
    amount: float = Query(default=0),
    token_name: str = Query(default="PLB", alias="token"),
    session: AsyncSession = Depends(get_session),
):
    outputs = await address_service.list_unspent_outputs(
        session, address_str, token_name, 100, 0
    )
    return compat_response(
        [
            {
                "txid": o.txid,
                "index": o.index,
                "script": o.script,
                "value": int(o.amount * 10**8),
                "height": None,
            }
            for o in outputs
        ]
    )


@router.get("/mempool")
async def get_mempool(session: AsyncSession = Depends(get_session)):
    txs = await tx_service.get_mempool_transactions(session)
    return compat_response(
        {
            "size": len(txs),
            "tx": [t["txid"] for t in txs],
            # fields not available without RPC
            "loaded": None,
            "bytes": None,
            "usage": None,
            "maxmempool": None,
            "mempoolminfee": None,
            "minrelaytxfee": None,
        }
    )


@router.get("/decode/{raw}")
async def decode_transaction(raw: str):
    settings = get_settings()
    result = await make_request(
        settings.blockchain.endpoint,
        {"id": "decode", "method": "decoderawtransaction", "params": [raw]},
    )
    return compat_response(result.get("result"))


@router.get("/fee")
async def get_fee():
    return compat_response({"feerate": int(0.01 * 10**8), "blocks": 6})


def _supply(height: int) -> dict:
    reward = int(4 * 10**8)
    halvings_period = 525960
    halvings_count = 0
    supply = reward

    while height > halvings_period:
        supply += halvings_period * reward
        reward = reward // 2
        height -= halvings_period
        halvings_count += 1

    supply += height * reward
    return {"halvings": halvings_count, "supply": supply}


@router.get("/supply")
async def get_supply(session: AsyncSession = Depends(get_session)):
    latest = await blocks_service.get_latest_block(session)
    height = latest.height if latest else 0
    result = _supply(height)
    result["height"] = height
    return compat_response(result)


@router.get("/tokens")
async def get_tokens(
    offset: int = Query(default=0, ge=0),
    count: int = Query(default=10, ge=1, le=100),
    search: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
):
    items = await token_service.list_tokens(session, offset, count)
    return compat_response(
        {
            t.name: {
                "name": t.name,
                "amount": t.amount,
                "reissuable": t.reissuable,
                "units": t.units,
            }
            for t in items
        }
    )


@router.post("/broadcast")
async def broadcast(raw: str = Query(...)):
    result = await tx_service.broadcast_transaction(raw)
    return compat_response(result.get("result") if isinstance(result, dict) else result)


@router.post("/verify")
async def verify_message(body: dict):
    settings = get_settings()
    result = await make_request(
        settings.blockchain.endpoint,
        {
            "id": "verify",
            "method": "verifymessage",
            "params": [
                body.get("address"),
                body.get("signature"),
                body.get("message"),
            ],
        },
    )
    return compat_response(result.get("result"))


def _tx_shape(tx) -> dict:
    outputs = []
    for o in getattr(tx, "outputs", []):
        outputs.append(
            {
                "value": int(float(o.amount) * 10**8),
                "n": o.index,
                "scriptPubKey": {
                    "asm": o.asm,
                    "type": o.type,
                    "addresses": [o.address],
                    "timelock": o.timelock,
                },
            }
        )

    inputs = []
    for i in getattr(tx, "inputs", []):
        inputs.append(
            {
                "txid": i.source_txid,
                "vout": i.index,
                "value": int(float(getattr(i, "amount", 0)) * 10**8),
                "scriptPubKey": {
                    "addresses": [getattr(i, "address", None)],
                },
            }
        )

    return {
        "txid": tx.txid,
        "version": tx.version,
        "locktime": tx.locktime,
        "blockhash": tx.blockhash,
        "confirmations": getattr(tx, "confirmations", 0),
        "time": tx.timestamp,
        "blocktime": tx.timestamp,
        "height": tx.height,
        "size": tx.size,
        "amount": sum(int(float(v) * 10**8) for v in tx.amount.values()),
        "vin": inputs,
        "vout": outputs,
    }
