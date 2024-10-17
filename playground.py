from pprint import pprint
from app import parser
import asyncio


async def test_request():
    data = await parser.parse_block(491263)
    # data = await parser.parse_transactions(
    #     [
    #         "73cb5ed09678fa8931fb9db0c1ef08d778a5b14bdbfb708caab8b9579b53ee76",  # Coinbase
    #         "bb41e29d6f8c4ca47a8c57f04e767d1b9c422abda6627f21c1fb54ef855271b4",  # New token
    #         "e236e82bb5cad2328d6e08e28e08c92929139af32dd9dd7437e308aaaddf1962",  # Reissue
    #         "25e395194481a45b055f31ffc29d6e7104246751c9097af607a107d6103d40c3",  # Transfer
    #     ]
    # )

    pprint(data)


if __name__ == "__main__":
    asyncio.run(test_request())
