from app.schemas import CustomModel


class HolderResponse(CustomModel):
    address: str
    balance: float
    percentage: float
    txcount: int
