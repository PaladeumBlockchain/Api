from app.schemas import CustomModel


class AddressTransactionsMultiArgs(CustomModel):
    addresses: list[str]
    currency: str | None = None


class AddressTransactionsMultiMempoolArgs(CustomModel):
    addresses: list[str]
