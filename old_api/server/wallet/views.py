from ..methods.transaction import Transaction as NodeTransaction
from ..models import Transaction, Block
from ..services import TransactionService
from webargs.flaskparser import use_args
from ..services import AddressService
from ..services import OutputService
from ..services import BlockService
from ..services import TokenService
from flask import Blueprint
from ..tools import display
from .. import utils
from pony import orm
from . import args

wallet = Blueprint("wallet", __name__, url_prefix="/wallet/")

def display_tx(transaction):
    latest_blocks = Block.select().order_by(
        orm.desc(Block.height)
    ).first()

    output_amount = 0
    input_amount = 0
    outputs = []
    inputs = []

    for vin in transaction.inputs:
        units = TokenService.get_units(vin.vout.currency)

        inputs.append({
            "address": vin.vout.address.address,
            "currency": vin.vout.currency,
            "amount": utils.satoshis(vin.vout.amount),
            "units": units
        })

        if vin.vout.currency == "PLB":
            input_amount += utils.satoshis(vin.vout.amount)

    for vout in transaction.outputs:
        units = TokenService.get_units(vout.currency)

        outputs.append({
            "address": vout.address.address,
            "currency": vout.currency,
            "timelock": vout.timelock,
            "category": vout.category,
            "amount": utils.satoshis(vout.amount),
            "units": units,
            "spent": vout.spent
        })

        if vout.currency == "PLB":
            output_amount += utils.satoshis(vout.amount)

    return {
        "confirmations": latest_blocks.height - transaction.block.height + 1,
        "fee": input_amount - output_amount,
        "timestamp": int(transaction.created.timestamp()),
        "amount": utils.satoshis(transaction.amount),
        "coinstake": transaction.coinstake,
        "height": transaction.block.height,
        "coinbase": transaction.coinbase,
        "txid": transaction.txid,
        "size": transaction.size,
        "outputs": outputs,
        "mempool": False,
        "inputs": inputs
    }


@wallet.route("/balance/<string:address>", methods=["GET"])
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
            units = TokenService.get_units(balance.currency)

            if balance.balance == 0:
                continue

            result.append({
                "currency": balance.currency,
                "balance": utils.satoshis(unspent),
                "locked": utils.satoshis(locked),
                "units": units
            })

    return utils.response(result)

@wallet.route("/history", methods=["POST"])
@use_args(args.history_args, location="json")
@orm.db_session
def history(args):
    transactions = None
    addresses = []
    result = []

    for raw_address in args["addresses"]:
        if raw_address:
            address = AddressService.get_by_address(raw_address)
            if address:
                addresses.append(address)

    transactions = orm.left_join(
        transaction
        for transaction in Transaction for address in transaction.addresses
        if address in addresses
    ).order_by(
        orm.desc(Transaction.created)
    )

    if args["after"]:
        after = TransactionService.get_by_txid(args["after"])
        if after:
            transactions = transactions.filter(lambda t: t.created > after.created)

    if args["before"]:
        before = TransactionService.get_by_txid(args["before"])
        if before:
            transactions = transactions.filter(lambda t: t.created < before.created)

    transactions = transactions.limit(args["count"])

    for transaction in transactions:
        result.append(display_tx(transaction))

    return utils.response(result)

@wallet.route("/transaction/<string:txid>", methods=["GET"])
@orm.db_session
def transaction(txid):
    transaction = TransactionService.get_by_txid(txid)

    if transaction:
        return utils.response(display_tx(transaction))

    data = NodeTransaction.info(txid)
    if not data["error"]:
        result = display.tx_to_wallet(data)
        return utils.response(result)

    return utils.dead_response("Transaction not found"), 404

@wallet.route("/check", methods=["POST"])
@use_args(args.addresses_args, location="json")
@orm.db_session
def check(args):
    result = []

    for raw_address in args["addresses"]:
        if raw_address:
            address = AddressService.get_by_address(raw_address)
            if address:
                result.append(raw_address)

    return utils.response(result)

@wallet.route("/utxo", methods=["POST"])
@use_args(args.utxo_args, location="json")
@orm.db_session
def utxo(args):
    result = []

    for output in args["outputs"]:
        if "index" not in output or "txid" not in output:
            continue

        transaction = TransactionService.get_by_txid(output["txid"])
        if not transaction:
            continue

        vout = OutputService.get_by_prev(transaction, output["index"])
        if not vout:
            continue

        result.append({
            "txid": transaction.txid,
            "units": TokenService.get_units(vout.currency),
            "amount": utils.satoshis(vout.amount),
            "address": vout.address.address,
            "currency": vout.currency,
            "timelock": vout.timelock,
            "category": vout.category,
            "spent": vout.spent,
            "index": vout.n
        })

    return utils.response(result)

@wallet.route("/broadcast", methods=["POST"])
@use_args(args.broadcast_args, location="json")
def broadcast(args):
    return NodeTransaction.broadcast(args["raw"])

@wallet.route("/decode", methods=["POST"])
@use_args(args.broadcast_args, location="json")
def decode(args):
    data = NodeTransaction.decode(args["raw"])

    if data["error"] is None:
        for index, vin in enumerate(data["result"]["vin"]):
            if "txid" in vin:
                vin_data = utils.make_request(
                    "getrawtransaction", [vin["txid"], True]
                )

                if vin_data["error"] is None:
                    vout = vin_data["result"]["vout"][vin["vout"]]
                    script = vout["scriptPubKey"]
                    value = utils.satoshis(
                        vout["value"]
                    )

                    if "token" in script:
                        script["token"]["decimal"] = script["token"]["amount"]

                        script["token"]["amount"] = utils.satoshis(
                            script["token"]["amount"]
                        )

                    data["result"]["vin"][index]["scriptPubKey"] = script
                    data["result"]["vin"][index]["value"] = value

        for index, vout in enumerate(data["result"]["vout"]):
            data["result"]["vout"][index]["value"] = utils.satoshis(
                vout["value"]
            )

            script = vout["scriptPubKey"]

            if "token" in script:
                script["token"]["decimal"] = script["token"]["amount"]

                script["token"]["amount"] = utils.satoshis(
                    script["token"]["amount"]
                )

            data["result"]["vout"][index]["scriptPubKey"] = script

    return data
