from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Optional, Dict, Any

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

    response_content = {
        "status": status,
        "message": message,
        "data": data,
        "status_code": status_code
    }

    if meta:
        response_content["meta"] = meta

    # Use jsonable_encoder to handle datetime, ObjectId, etc.
    return JSONResponse(
        content=jsonable_encoder(response_content),
        status_code=status_code
    )