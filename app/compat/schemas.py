from typing import Any


def compat_response(result: Any) -> dict:
    return {"error": None, "id": "api-server", "result": result}


def compat_error(message: str) -> dict:
    return {"error": message, "id": "api-server", "result": None}
