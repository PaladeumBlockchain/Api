from typing import Any


def compat_response(result: Any) -> dict:
    return {"error": None, "id": "1", "result": result}


def compat_error(message: str) -> dict:
    return {"error": message, "id": "1", "result": None}
