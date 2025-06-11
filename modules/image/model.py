from pydantic import BaseModel
from typing import Optional

class ImageUploadRequest(BaseModel):
    user_id: Optional[str] = None
    folder: Optional[str] = "default"