from app.schemas import CustomModel


class WalletInfoResponse(CustomModel):
    bestblockhash: str
    mediantime: int
    mempool: int
    reward: int
    blocks: int
