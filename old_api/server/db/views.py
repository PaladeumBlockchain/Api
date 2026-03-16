from ..methods.transaction import Transaction as NodeTransaction
from ..methods.general import General as NodeGeneral
from ..methods.token import Token as TokenGeneral
from ..services import TransactionService
from webargs.flaskparser import use_args
from ..services import AddressService
from ..services import OutputService
from ..services import BlockService
from ..models import Transaction
from .args import broadcast_args
from .args import page_args
from flask import Blueprint
from ..tools import display
from .. import utils
from pony import orm

db = Blueprint("db", __name__, url_prefix="/v2/")

@db.route("/latest", methods=["GET"])
@orm.db_session
def info():
    block = BlockService.latest_block()

    return utils.response({
        "time": block.created.timestamp(),
        "blockhash": block.blockhash,
        "height": block.height,
        "chainwork": block.chainwork,
        "reward": float(block.reward)
    })

@db.route("/transactions", defaults={"token": "PLB"}, methods=["GET"])
@db.route("/transactions/<string:token>", methods=["GET"])
@use_args(page_args, location="query")
@orm.db_session
def transactions(args, token):
    transactions = TransactionService.transactions(args["page"], token)
    result = []

    for entry in transactions:
        transaction = entry[0]
        amount = entry[1]

        result.append({
            "height": transaction.block.height,
            "blockhash": transaction.block.blockhash,
            "timestamp": transaction.block.created.timestamp(),
            "txhash": transaction.txid,
            "amount": float(amount)
        })

    return utils.response(result)

@db.route("/blocks", methods=["GET"])
@use_args(page_args, location="query")
@orm.db_session
def blocks(args):
    blocks = BlockService.blocks(args["page"])
    result = []

    for block in blocks:
        result.append({
            "height": block.height,
            "blockhash": block.blockhash,
            "timestamp": block.created.timestamp(),
            "tx": len(block.transactions)
        })

    return utils.response(result)

@db.route("/block/<string:bhash>", methods=["GET"])
@orm.db_session
def block(bhash):
    block = BlockService.get_by_hash(bhash)

    if block:
        return utils.response({
            "reward": float(block.reward),
            "signature": block.signature,
            "blockhash": block.blockhash,
            "height": block.height,
            "tx": len(block.transactions),
            "timestamp": block.created.timestamp(),
            "merkleroot": block.merkleroot,
            "chainwork": block.chainwork,
            "version": block.version,
            "weight": block.weight,
            "stake": block.stake,
            "nonce": int(block.nonce),
            "size": block.size,
            "bits": block.bits
        })

    return utils.dead_response("Block not found"), 404

@db.route("/block/<string:bhash>/transactions", methods=["GET"])
@use_args(page_args, location="query")
@orm.db_session
def block_transactions(args, bhash):
    block = BlockService.get_by_hash(bhash)

    if block:
        transactions = block.transactions.page(args["page"])
        result = []

        for transaction in transactions:
            result.append(transaction.display())

        return utils.response(result)

    return utils.dead_response("Block not found"), 404

@db.route("/transaction/<string:txid>", methods=["GET"])
@orm.db_session
def transaction(txid):
    transaction = TransactionService.get_by_txid(txid)

    if transaction:
        return utils.response(transaction.display())

    data = NodeTransaction.info(txid)
    if not data["error"]:
        result = display.tx_to_db(data)
        return utils.response(result)

    return utils.dead_response("Transaction not found"), 404

@db.route("/history/<string:address>", methods=["GET"])
@use_args(page_args, location="query")
@orm.db_session
def history(args, address):
    address = AddressService.get_by_address(address)
    result = []

    if address:
        transactions = address.transactions.order_by(
            orm.desc(Transaction.id)
        ).page(args["page"], pagesize=100)

        for transaction in transactions:
            result.append(transaction.display())

    return utils.response(result)

@db.route("/stats/<string:address>", methods=["GET"])
@orm.db_session
def count(address):
    address = AddressService.get_by_address(address)
    transactions = 0
    tokens = 0

    if address:
        transactions = len(address.transactions)
        for balance in address.balances:
            if balance.currency != "PLB" and balance.balance > 0:
                tokens += 1

    return utils.response({
        "transactions": transactions,
        "tokens": tokens
    })

@db.route("/richlist", defaults={"token": "PLB"}, methods=["GET"])
@db.route("/richlist/<string:token>", methods=["GET"])
@use_args(page_args, location="query")
@orm.db_session
def richlist(args, token):
    addresses = AddressService.richlist(args["page"], token)
    result = []

    for entry in addresses:
        result.append({
            "address": entry[0].address,
            "balance": float(entry[1])
        })

    return utils.response(result)

@db.route("/chart", methods=["GET"])
@orm.db_session
def chart():
    data = BlockService.chart()
    result = {}

    for entry in data:
        result[entry[0]] = entry[1]

    return utils.response(result)

@db.route("/balance/<string:address>", methods=["GET"])
@orm.db_session
def test(address):
    address = AddressService.get_by_address(address)
    block = BlockService.latest_block()
    result = []

    if address:
        for balance in address.balances:
            locked_time = OutputService.locked_time(address, block.created.timestamp(), balance.currency)
            locked_height = OutputService.locked_height(address, block.height, balance.currency)

            locked = locked_time + locked_height
            unspent = balance.balance - locked

            if balance.balance == 0:
                continue

            result.append({
                "currency": balance.currency,
                "balance": float(unspent),
                "locked": float(locked)
            })

    return utils.response(result)

@db.route("/mempool", methods=["GET"])
@orm.db_session
def mempool():
    data = NodeGeneral.mempool()

    if not data["error"]:
        mempool = data["result"]["tx"]
        new = []

        for txid in mempool:
            tx = NodeTransaction.info(txid)
            new.append(display.tx_to_db(tx))

        data["result"]["tx"] = new

    return data

@db.route("/token/<string:name>", methods=["GET"])
@orm.db_session
def token_data(name):
    data = TokenGeneral.data(name)

    if data["result"]:
        result = display.token_to_db(data)
        return utils.response(result)

    return utils.dead_response("Token not found"), 404

@db.route("/broadcast", methods=["POST"])
@use_args(broadcast_args, location="json")
def broadcast(args):
    return NodeTransaction.broadcast(args["raw"])
