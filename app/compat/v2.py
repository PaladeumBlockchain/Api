from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.utils import pagination
from app.blocks import service as blocks_service
from app.address import service as address_service
from app.transactions import service as tx_service
from app.token import service as token_service
from app.holders import service as holders_service

from .schemas import compat_response, compat_error
from . import service as compat_service

router = APIRouter(prefix="/v2", tags=["Compat"])

_DEFAULT_PAGE_SIZE = 10
_DEFAULT_TOKEN = "PLB"


def _block_v2_shape(block) -> dict:
    return {
        "blockhash": block.blockhash,
        "height": block.height,
        "timestamp": float(block.timestamp),
        "tx": block.tx,
        "reward": float(block.reward),
        # fields not stored in new DB
        "merkleroot": None,
        "chainwork": None,
        "version": None,
        "weight": None,
        "stake": None,
        "nonce": None,
        "size": None,
        "bits": None,
        "signature": None,
    }


def _tx_v2_shape(tx) -> dict:
    outputs = [
        {
            "address": o.address,
            "currency": o.currency,
            "timelock": o.timelock,
            "amount": float(o.amount),
            "category": o.type,
            "spent": o.spent,
            "index": o.index,
            "vin": None,
        }
        for o in getattr(tx, "outputs", [])
    ]

    inputs = [
        {
            "address": getattr(i, "address", None),
            "currency": getattr(i, "currency", "PLB"),
            "amount": float(getattr(i, "amount", 0)),
        }
        for i in getattr(tx, "inputs", [])
    ]

    return {
        "txid": tx.txid,
        "blockhash": tx.blockhash,
        "height": tx.height,
        "confirmations": getattr(tx, "confirmations", 0),
        "timestamp": tx.timestamp,
        "fee": float(tx.fee),
        "amount": float(sum(tx.amount.values())) if tx.amount else 0.0,
        "coinstake": getattr(tx, "coinstake", False),
        "coinbase": tx.coinbase,
        "size": tx.size,
        "mempool": False,
        "outputs": outputs,
        "inputs": inputs,
    }


@router.get("/latest")
async def get_latest(session: AsyncSession = Depends(get_session)):
    block = await blocks_service.get_latest_block(session)
    if block is None:
        return compat_response(None)
    return compat_response(
        {
            "blockhash": block.blockhash,
            "height": block.height,
            "time": float(block.timestamp),
            "reward": float(block.reward),
            "chainwork": None,
        }
    )


@router.get("/transactions")
@router.get("/transactions/{token_name}")
async def get_transactions(
    token_name: str = _DEFAULT_TOKEN,
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = pagination(page, size=_DEFAULT_PAGE_SIZE)
    txs = await tx_service.get_transactions(session, token_name, offset, limit)
    return compat_response(
        [
            {
                "txhash": t.txid,
                "blockhash": t.blockhash,
                "height": t.height,
                "timestamp": float(t.timestamp),
                "amount": float(sum(t.amount.values())) if t.amount else 0.0,
            }
            for t in txs
        ]
    )


@router.get("/blocks")
async def get_blocks(
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = pagination(page, size=_DEFAULT_PAGE_SIZE)
    blocks_list = await blocks_service.get_blocks(session, offset, limit)
    return compat_response(
        [
            {
                "blockhash": b.blockhash,
                "height": b.height,
                "timestamp": float(b.timestamp),
                "tx": b.tx,
            }
            for b in blocks_list
        ]
    )


@router.get("/block/{bhash}")
async def get_block(
    bhash: str,
    session: AsyncSession = Depends(get_session),
):
    block = await blocks_service.get_block_by_hash(session, bhash)
    if block is None:
        return JSONResponse(status_code=404, content=compat_error("Block not found"))
    return compat_response(_block_v2_shape(block))


@router.get("/block/{bhash}/transactions")
async def get_block_transactions(
    bhash: str,
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
):
    block = await blocks_service.get_block_by_hash(session, bhash)
    if block is None:
        return JSONResponse(status_code=404, content=compat_error("Block not found"))
    limit, offset = pagination(page, size=_DEFAULT_PAGE_SIZE)
    txs = await blocks_service.get_block_transactions(session, bhash, offset, limit)
    return compat_response([_tx_v2_shape(t) for t in txs])


@router.get("/transaction/{txid}")
async def get_transaction(
    txid: str,
    session: AsyncSession = Depends(get_session),
):
    tx = await tx_service.get_transaction_by_txid(session, txid)
    if tx is None:
        return JSONResponse(
            status_code=404, content=compat_error("Transaction not found")
        )
    return compat_response(_tx_v2_shape(tx))


@router.get("/history/{address_str}")
async def get_history(
    address_str: str,
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = pagination(page, size=_DEFAULT_PAGE_SIZE)
    txs = await address_service.list_transactions(session, address_str, limit, offset)
    return compat_response([_tx_v2_shape(t) for t in txs])


@router.get("/stats/{address_str}")
async def get_stats(
    address_str: str,
    session: AsyncSession = Depends(get_session),
):
    stats = await compat_service.get_address_stats(session, address_str)
    return compat_response(stats)


@router.get("/richlist")
@router.get("/richlist/{token_name}")
async def get_richlist(
    token_name: str = _DEFAULT_TOKEN,
    page: int = Query(default=1, ge=1),
    session: AsyncSession = Depends(get_session),
):
    limit, offset = pagination(page, size=_DEFAULT_PAGE_SIZE)
    holders = await holders_service.list_holders_by_currency(
        session, token_name, offset, limit
    )
    return compat_response(
        [{"address": h["address"], "balance": float(h["balance"])} for h in holders]
    )


@router.get("/balance/{address_str}")
async def get_balance(
    address_str: str,
    session: AsyncSession = Depends(get_session),
):
    balances = await address_service.list_balances(session, address_str)
    return compat_response(
        [
            {
                "currency": b.currency,
                "balance": float(b.balance),
                "locked": float(b.locked),
            }
            for b in balances
        ]
    )


@router.get("/mempool")
async def get_mempool(session: AsyncSession = Depends(get_session)):
    txs = await tx_service.get_mempool_transactions(session)
    return compat_response(
        {
            "size": len(txs),
            "tx": [_tx_v2_shape(t) for t in txs],
            "loaded": None,
            "bytes": None,
            "usage": None,
            "maxmempool": None,
            "mempoolminfee": None,
            "minrelaytxfee": None,
        }
    )


@router.get("/token/{name}")
async def get_token(
    name: str,
    session: AsyncSession = Depends(get_session),
):
    tok = await token_service.get_full_token(session, name)
    if tok is None:
        return JSONResponse(status_code=404, content=compat_error("Token not found"))
    return compat_response(
        {
            "name": tok.name,
            "amount": str(tok.amount),
            "reissuable": tok.reissuable,
            "units": tok.units,
            "total": None,
        }
    )


@router.post("/broadcast")
async def broadcast(body: dict):
    raw = body.get("raw", "")
    result = await tx_service.broadcast_transaction(raw)
    return compat_response(result.get("result") if isinstance(result, dict) else result)
