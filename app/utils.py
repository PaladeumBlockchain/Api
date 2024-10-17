from app import get_settings
import aiohttp
import json


# Convert datetime to timestamp
def to_timestamp(date: datetime | None) -> int | None:
    date = date.replace(tzinfo=timezone.utc) if date else date
    return int(date.timestamp()) if date else None


def dead_response(message="Invalid Request"):
    return {"error": {"code": 404, "message": message}}


def response(result, error=None):
    return {"error": error, "result": result}


async def make_request(method, params=[]):
    async with aiohttp.ClientSession() as session:
        headers = {"content-type": "text/plain;"}
        data = json.dumps({"id": "sync", "method": method, "params": params})

        try:
            async with session.post(
                get_settings().blockchain.endpoint, headers=headers, data=data
            ) as r:
                data = await r.json()

                if data["error"]:
                    return data

                return data["result"]

        except Exception:
            return dead_response()
