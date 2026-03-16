from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.parser import make_request
from app.settings import get_settings
from app.address import service as address_service
from app.transactions import service as tx_service
from app.wallet import service as wallet_service

from .schemas import compat_response, compat_error
from . import service as compat_service

router = APIRouter(prefix="/wallet", tags=["Compat"])


def _to_satoshi(amount) -> int:
    return int(float(amount) * 10**8)


def _tx_wallet_shape(tx) -> dict:
    outputs = [
        {
            "address": o.address,
            "currency": o.currency,
            "timelock": o.timelock,
            "amount": _to_satoshi(o.amount),
            "category": o.type,
            "units": getattr(o, "units", 8),
            "spent": o.spent,
            "index": o.index,
        }
        for o in getattr(tx, "outputs", [])
    ]

    inputs = [
        {
            "address": getattr(i, "address", None),
            "currency": getattr(i, "currency", "PLB"),
            "amount": _to_satoshi(getattr(i, "amount", 0)),
            "units": getattr(i, "units", 8),
        }
        for i in getattr(tx, "inputs", [])
    ]

    return {
        "txid": tx.txid,
        "height": tx.height,
        "confirmations": getattr(tx, "confirmations", 0),
        "timestamp": tx.timestamp,
        "fee": _to_satoshi(tx.fee),
        "amount": _to_satoshi(sum(tx.amount.values())),
        "coinstake": getattr(tx, "coinstake", False),
        "coinbase": tx.coinbase,
        "size": tx.size,
        "mempool": False,
        "outputs": outputs,
        "inputs": inputs,
    }


@router.get("/balance/{address_str}")
async def wallet_balance(
    address_str: str,
    session: AsyncSession = Depends(get_session),
):
    balances = await address_service.list_balances(session, address_str)
    return compat_response(
        [
            {
                "currency": b.currency,
                "balance": _to_satoshi(b.balance),
                "locked": _to_satoshi(b.locked),
                "units": getattr(b, "units", 8),
            }
            for b in balances
        ]
    )


@router.post("/history")
async def wallet_history(
    body: dict,
    session: AsyncSession = Depends(get_session),
):
    addresses = body.get("addresses", [])
    count = body.get("count", 10)

    seen = set()
    result = []
    for addr in addresses:
        txs = await address_service.list_transactions(session, addr, count, 0)
        for tx in txs:
            if tx.txid not in seen:
                seen.add(tx.txid)
                result.append(_tx_wallet_shape(tx))

    result.sort(key=lambda t: t["height"] or 0, reverse=True)
    return compat_response(result[:count])


@router.get("/transaction/{txid}")
async def wallet_transaction(
    txid: str,
    session: AsyncSession = Depends(get_session),
):
    tx = await tx_service.get_transaction_by_txid(session, txid)
    if tx is None:
        return JSONResponse(
            status_code=404, content=compat_error("Transaction not found")
        )
    return compat_response(_tx_wallet_shape(tx))


@router.post("/check")
async def wallet_check(
    body: dict,
    session: AsyncSession = Depends(get_session),
):
    addresses = body.get("addresses", [])[:20]
    valid = await wallet_service.check_addresses(session, addresses)
    return compat_response(valid)


@router.post("/utxo")
async def wallet_utxo(
    body: dict,
    session: AsyncSession = Depends(get_session),
):
    outputs_req = body.get("outputs", [])
    shortcuts = [f"{o['txid']}:{o['index']}" for o in outputs_req]
    outputs = await compat_service.get_outputs_by_shortcut(session, shortcuts)
    return compat_response(
        [
            {
                "txid": o.txid,
                "index": o.index,
                "address": o.address,
                "currency": o.currency,
                "amount": _to_satoshi(o.amount),
                "timelock": o.timelock,
                "category": o.type,
                "units": 8,
                "spent": o.spent,
            }
            for o in outputs
        ]
    )


@router.post("/broadcast")
async def wallet_broadcast(body: dict):
    raw = body.get("raw", "")
    result = await tx_service.broadcast_transaction(raw)
    return compat_response(result.get("result") if isinstance(result, dict) else result)


@router.post("/decode")
async def wallet_decode(body: dict):
    settings = get_settings()
    raw = body.get("raw", "")
    result = await make_request(
        settings.blockchain.endpoint,
        {"id": "decode", "method": "decoderawtransaction", "params": [raw]},
    )
    return compat_response(result.get("result"))
