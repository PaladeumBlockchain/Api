from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.schemas import CustomModel
from fastapi import Request
from pydantic import Field


class ErrorResponse(CustomModel):
    message: str = Field(examples=["Example error message"])
    code: str = Field(examples=["example:error"])


errors = {}


class Abort(Exception):
    def __init__(self, scope: str, message: str):
        self.scope = scope
        self.message = message


def build_error_code(scope: str, message: str):
    return scope.replace("-", "_") + ":" + message.replace("-", "_")


async def abort_handler(request: Request, exception: Abort):
    error_code = build_error_code(exception.scope, exception.message)

    try:
        error_message = errors[exception.scope][exception.message][0]
        status_code = errors[exception.scope][exception.message][1]
    except Exception:
        error_message = "Unknown error"
        status_code = 400

    return JSONResponse(
        status_code=status_code,
        content={
            "message": error_message,
            "code": error_code,
        },
    )


async def validation_handler(
    request: Request, exception: RequestValidationError
):
    error_message = str(exception).replace("\n", " ").replace("   ", " ")
    return JSONResponse(
        status_code=400,
        content={
            "code": "system:validation_error",
            "message": error_message,
        },
    )
