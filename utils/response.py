from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Optional, Dict, Any
from decimal import Decimal
try:
    # bson is available in this project; used across modules
    from bson import ObjectId  # type: ignore
except Exception:  # pragma: no cover - fallback if bson missing in some envs
    class ObjectId(str):  # minimal fallback to avoid runtime import error
        pass

class ResponseModel:
    def __init__(self, success: bool, message: str, data: Any = None):
        self.success = success
        self.message = message
        self.data = data

def create_response(
    status: str,
    status_code: int,
    message: str,
    data: dict | list | None = None,
    meta: Optional[Dict[str, Any]] = None
):
    """
    Utility function to create a standardized JSON response.
    Uses jsonable_encoder to ensure all values are JSON-serializable.
    
    :param status: Status of the response (e.g., "Ok", "Error").
    :param status_code: HTTP status code (e.g., 200, 400, 500).
    :param message: Message describing the result.
    :param data: Data to include in the response (can be a dictionary, list, or None).
    :param meta: Additional metadata like pagination info.
    :return: A JSONResponse object.
    """

    # Derive a simple boolean success flag expected by some tests
    is_success = 200 <= status_code < 400

    response_content = {
        "status": status,
        "message": message,
        "data": data,
        "status_code": status_code,
        "success": is_success,
    }

    if meta:
        response_content["meta"] = meta

    # Use jsonable_encoder with custom encoders to handle bson.ObjectId, Decimal, etc.
    # - ObjectId → str
    # - Decimal → float (fallback to str if not finite)
    def _encode_decimal(value: Decimal) -> float | str:
        try:
            return float(value)
        except Exception:
            return str(value)

    encoded = jsonable_encoder(
        response_content,
        custom_encoder={
            ObjectId: str,
            Decimal: _encode_decimal,
        },
    )
    return JSONResponse(content=encoded, status_code=status_code)


# Convenience wrappers so routers can call success_response / error_response
def success_response(
    data: dict | list | None = None,
    message: str = "Ok",
    status_code: int = 200,
    meta: Optional[Dict[str, Any]] = None,
):
    return create_response(
        status="Ok",
        status_code=status_code,
        message=message,
        data=data,
        meta=meta,
    )


def error_response(
    message: str = "Error",
    status_code: int = 500,
    data: dict | list | None = None,
    meta: Optional[Dict[str, Any]] = None,
):
    return create_response(
        status="Error",
        status_code=status_code,
        message=message,
        data=data,
        meta=meta,
    )