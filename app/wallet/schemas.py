from app.schemas import CustomModel


class WalletInfoResponse(CustomModel):
    bestblockhash: str
    difficulty: int
    mediantime: int
    chainwork: str
    nethash: int
    headers: int
    mempool: int
    reward: int
    blocks: int
    chain: str
