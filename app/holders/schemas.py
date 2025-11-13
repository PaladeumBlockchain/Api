from app.schemas import CustomModel, Satoshi


class HolderResponse(CustomModel):
    address: str
    balance: Satoshi
    percentage: float
    txcount: int
