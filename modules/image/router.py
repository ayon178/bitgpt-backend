from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from utils.response import create_response
from auth.service import authentication_service
from modules.user.model import UserResponse
from PIL import Image
import os
import uuid
from io import BytesIO
from typing import Annotated

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=dict)
async def upload_image(
    current_user: Annotated[UserResponse, Depends(authentication_service.verify_authentication)],
    file: UploadFile = File(...),
):
    """
    Upload and convert any image to .webp format.
    Returns path to uploaded image.
    """

    if not file.content_type.startswith("image/"):
        return create_response(
            status="Error",
            status_code=400,
            message="Uploaded file is not an image"
        )

    try:
        file_ext = file.filename.split(".")[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        webp_filename = f"{uuid.uuid4()}.webp"

        # Convert image to WebP
        contents = await file.read()
        image = Image.open(BytesIO(contents))
        output_path = os.path.join(UPLOAD_DIR, webp_filename)

        image.convert("RGB").save(output_path, "webp")

    except Exception as e:
        return create_response(
            status="Error",
            status_code=500,
            message="Failed to process or save image",
            data={"error": str(e)}
        )

    return create_response(
        status="Ok",
        status_code=201,
        message="Image uploaded and converted successfully",
        data={
            "path": f"/uploads/{webp_filename}",
            "url": f"https://tutor.garagepotti.xyz/uploads/{webp_filename}"
        }
    )