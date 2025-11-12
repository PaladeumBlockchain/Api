from app.schemas import CustomModel, Satoshi


class TokenResponse(CustomModel):
    reissuable: bool
    amount: Satoshi
    units: int
    name: str
    type: str

    icon: str | None

    blockhash: str
    height: int


class FullTokenResponse(TokenResponse):
    holders: int
