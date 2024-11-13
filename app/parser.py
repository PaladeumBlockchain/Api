from app.address.service import transactions_filters
from app.settings import get_settings
from datetime import datetime
from app import constants
import aiohttp
import json


async def make_request(endpoint: str, requests: list[dict] | dict = None):
    if requests is None:
        requests = []

    async with aiohttp.ClientSession() as session:
        headers = {"content-type": "application/json;"}
        data = json.dumps(requests)

        try:
            async with session.post(endpoint, headers=headers, data=data) as r:
                return await r.json()
        except Exception:
            raise


def parse_meta(spk):
    if spk["type"] in ["new_token", "reissue_token"]:
        return {
            "type": spk["type"],
            "amount": spk["token"]["amount"],
            "name": spk["token"]["name"],
            "units": (
                spk["token"]["units"] if "units" in spk["token"] else False
            ),
            "reissuable": (
                spk["token"]["reissuable"]
                if "reissuable" in spk["token"]
                else False
            ),
        }

    return {}


async def parse_outputs(transaction_data: dict):
    outputs = []

    for vout in transaction_data["vout"]:
        spk = vout["scriptPubKey"]

        if spk["type"] in ["nonstandard", "nulldata"]:
            continue

        if "token" in spk:
            timelock = spk["token"]["timelock"]
            currency = spk["token"]["name"]
            amount = spk["token"]["amount"]

        else:
            timelock = spk["timelock"] if "timelock" in spk else 0
            currency = constants.DEFAULT_CURRENCY
            amount = vout["value"]

        # Extract metadata like information about token issuance and etc
        meta = parse_meta(spk)

        outputs.append(
            {
                "shortcut": transaction_data["txid"] + ":" + str(vout["n"]),
                "blockhash": transaction_data["blockhash"],
                "txid": transaction_data["txid"],
                "address": spk["addresses"][0],
                "timelock": timelock,
                "currency": currency,
                "type": spk["type"],
                "index": vout["n"],
                "amount": amount,
                "spent": False,
                "meta": meta,
            }
        )

    return outputs


async def parse_inputs(transaction_data: dict):
    inputs = []

    for vin in transaction_data["vin"]:
        if "coinbase" in vin:
            continue

        inputs.append(
            {
                "shortcut": vin["txid"] + ":" + str(vin["vout"]),
                "blockhash": transaction_data["blockhash"],
                "index": vin["vout"],
                "txid": vin["txid"],
            }
        )

    return inputs


async def build_movements(settings, inputs, outputs):
    input_transactions_result = await make_request(
        settings.blockchain.endpoint,
        [
            {
                "id": f"input-tx-{txid}",
                "method": "getrawtransaction",
                "params": [txid, True],
            }
            for txid in list(set([vin["txid"] for vin in inputs]))
        ],
    )

    input_outputs = {}

    for transaction_result in input_transactions_result:
        transaction_data = transaction_result["result"]
        vin_vouts = await parse_outputs(transaction_data)

        for vout in vin_vouts:
            input_outputs[vout["shortcut"]] = vout

    movements = {}

    for output in outputs:
        currency_movement = movements.setdefault(output["currency"], {})
        address = output["address"]
        amount = output["amount"]

        currency_movement.setdefault(address, 0)
        currency_movement[address] += amount

    for input in inputs:  # noqa
        input_output = input_outputs[input["shortcut"]]
        currency = input_output["currency"]
        address = input_output["address"]
        amount = input_output["amount"]
        currency_movement = movements[currency]

        currency_movement.setdefault(address, 0)

        currency_movement[address] -= amount

    for currency in movements:
        movements[currency] = {
            key: value
            for key, value in movements[currency].items()
            if value != 0.0
        }

    return movements


async def parse_transactions(txids: list[str]):
    settings = get_settings()

    transactions_result = await make_request(
        settings.blockchain.endpoint,
        [
            {
                "id": f"tx-{txid}",
                "method": "getrawtransaction",
                "params": [txid, True],
            }
            for txid in txids
        ],
    )

    transactions = []
    outputs = []
    inputs = []

    for transaction_result in transactions_result:
        transaction_data = transaction_result["result"]

        addresses = list(
            set(
                address
                for vout in transaction_data["vout"]
                for address in vout["scriptPubKey"].get("addresses", [])
            )
        )

        transactions.append(
            {
                "created": datetime.fromtimestamp(transaction_data["time"]),
                "addresses": addresses,
                "blockhash": transaction_data["blockhash"],
                "locktime": transaction_data["locktime"],
                "version": transaction_data["version"],
                "timestamp": transaction_data["time"],
                "size": transaction_data["size"],
                "txid": transaction_data["txid"],
            }
        )

        outputs += await parse_outputs(transaction_data)

        inputs += await parse_inputs(transaction_data)

    movements = await build_movements(settings, inputs, outputs)

    return {
        "transactions": transactions,
        "movements": movements,
        "outputs": outputs,
        "inputs": inputs,
    }


async def parse_block(height: int):
    settings = get_settings()

    result = {}

    block_hash_result = await make_request(
        settings.blockchain.endpoint,
        {
            "id": f"blockhash-#{height}",
            "method": "getblockhash",
            "params": [height],
        },
    )

    block_hash = block_hash_result["result"]

    block_data_result = await make_request(
        settings.blockchain.endpoint,
        {
            "id": f"block-#{block_hash}",
            "method": "getblock",
            "params": [block_hash],
        },
    )

    block_data = block_data_result["result"]

    transactions_data = await parse_transactions(
        [] if height == 0 else block_data["tx"]
    )

    result["transactions"] = transactions_data["transactions"]
    result["outputs"] = transactions_data["outputs"]
    result["inputs"] = transactions_data["inputs"]
    result["block"] = {
        "prev_blockhash": block_data.get("previousblockhash", None),
        "created": datetime.fromtimestamp(block_data["time"]),
        "movements": transactions_data["movements"],
        "transactions": block_data["tx"],
        "blockhash": block_data["hash"],
        "timestamp": block_data["time"],
        "height": block_data["height"],
    }

    return result
