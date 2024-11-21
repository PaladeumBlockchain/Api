from app.parser import make_request, parse_block
from pprint import pprint
import asyncio


async def test():
    data = await parse_block(39)
    pprint(data)


if __name__ == "__main__":
    asyncio.run(test())
