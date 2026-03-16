from datetime import datetime
from decimal import Decimal
from pony import orm
import config

db = orm.Database(**config.db)

class Token(db.Entity):
    _table_ = "chain_tokens"

    amount = orm.Required(Decimal, precision=20, scale=8)
    name = orm.Required(str, index=True)
    reissuable = orm.Required(bool)
    units = orm.Required(int)
    type = orm.Required(int)

class Block(db.Entity):
    _table_ = "chain_blocks"

    reward = orm.Required(Decimal, precision=20, scale=8)
    signature = orm.Optional(str, nullable=True)
    blockhash = orm.Required(str, index=True)
    height = orm.Required(int, index=True)
    # nonce = orm.Required(int, size=64)
    nonce = orm.Required(str)
    created = orm.Required(datetime)
    merkleroot = orm.Required(str)
    chainwork = orm.Required(str)
    version = orm.Required(int)
    weight = orm.Required(int)
    stake = orm.Required(bool)
    size = orm.Required(int)
    bits = orm.Required(str)

    previous_block = orm.Optional("Block")
    transactions = orm.Set("Transaction")
    next_block = orm.Optional("Block")

class Transaction(db.Entity):
    _table_ = "chain_transactions"

    amount = orm.Required(Decimal, precision=20, scale=8)
    coinstake = orm.Required(bool, default=False)
    coinbase = orm.Required(bool, default=False)
    txid = orm.Required(str, index=True)
    created = orm.Required(datetime)
    locktime = orm.Required(int)
    size = orm.Required(int)

    block = orm.Required("Block")
    outputs = orm.Set("Output")
    inputs = orm.Set("Input")

    addresses = orm.Set("Address")

    def display(self):
        latest_blocks = Block.select().order_by(
            orm.desc(Block.height)
        ).first()

        output_amount = 0
        input_amount = 0
        outputs = []
        inputs = []

        for vin in self.inputs:
            inputs.append({
                "address": vin.vout.address.address,
                "currency": vin.vout.currency,
                "amount": float(vin.vout.amount),
                "id": vin.id,
            })

            if vin.vout.currency == "PLB":
                input_amount += vin.vout.amount

        inputs = sorted(inputs, key=lambda d: d["id"])
        inputs = [{key: val for key, val in sub.items() if key != "id"} for sub in inputs]

        for vout in self.outputs:
            outputs.append({
                "vin": vout.vin.transaction.txid if vout.vin else None,
                "address": vout.address.address,
                "currency": vout.currency,
                "timelock": vout.timelock,
                "amount": float(vout.amount),
                "category": vout.category,
                "spent": vout.spent,
                "index": vout.n
            })

            if vout.currency == "PLB":
                output_amount += vout.amount

        outputs = sorted(outputs, key=lambda d: d["index"])

        return {
            "confirmations": latest_blocks.height - self.block.height + 1,
            "fee": float(input_amount - output_amount),
            "timestamp": int(self.created.timestamp()),
            "amount": float(self.amount),
            "coinstake": self.coinstake,
            "height": self.block.height,
            "coinbase": self.coinbase,
            "txid": self.txid,
            "size": self.size,
            "outputs": outputs,
            "mempool": False,
            "inputs": inputs
        }

class Address(db.Entity):
    _table_ = "chain_addresses"

    address = orm.Required(str, index=True)
    outputs = orm.Set("Output")

    transactions = orm.Set(
        "Transaction", table="chain_address_transactions",
        reverse="addresses"
    )

    balances = orm.Set("Balance")

class Balance(db.Entity):
    _table_ = "chain_address_balance"

    balance = orm.Required(Decimal, precision=20, scale=8, default=0)
    address = orm.Required("Address")
    currency = orm.Required(str)

    orm.composite_index(address, currency)

class Input(db.Entity):
    _table_ = "chain_inputs"

    sequence = orm.Required(int, size=64)
    n = orm.Required(int)

    transaction = orm.Required("Transaction")
    vout = orm.Required("Output")

    def before_delete(self):
        balance = Balance.get(
            address=self.vout.address, currency=self.vout.currency
        )

        balance.balance += self.vout.amount

class Output(db.Entity):
    _table_ = "chain_outputs"

    amount = orm.Required(Decimal, precision=20, scale=8)
    currency = orm.Required(str, default="PLB", index=True)
    timelock = orm.Required(int, default=0)
    address = orm.Required("Address")
    category = orm.Optional(str)
    raw = orm.Optional(str)
    n = orm.Required(int)

    vin = orm.Optional("Input", cascade_delete=True)
    transaction = orm.Required("Transaction")
    address = orm.Optional("Address")

    @property
    def spent(self):
        return self.vin is not None

    def before_delete(self):
        balance = Balance.get(
            address=self.address, currency=self.currency
        )

        balance.balance -= self.amount

    orm.composite_index(transaction, n)


db.generate_mapping(create_tables=True)
