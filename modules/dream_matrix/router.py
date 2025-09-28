from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from auth.service import authentication_service
from utils.response import success_response, error_response
from .service import DreamMatrixService

router = APIRouter(prefix="/dream-matrix", tags=["Dream Matrix"])

@router.get("/earnings/{user_id}")
async def get_dream_matrix_earnings(
    user_id: str,
    slot_no: Optional[int] = None,
    recycle_no: Optional[int] = None,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Dream Matrix earnings data matching frontend matrixData.js structure"""
    try:
        # Extract user ID from current_user with fallback options
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]

        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break
        
        # Authorization check - users can only access their own data
        if authenticated_user_id and authenticated_user_id != user_id:
            raise HTTPException(status_code=403, detail="Unauthorized to view this user's Dream Matrix earnings")

        dream_matrix_service = DreamMatrixService()
        result = dream_matrix_service.get_dream_matrix_earnings(user_id, slot_no, recycle_no)

        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))

@router.get("/details/{tree_id}")
async def get_dream_matrix_details(
    tree_id: int,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get specific Dream Matrix tree details by tree ID"""
    try:
        # Extract user ID from current_user with fallback options
        authenticated_user_id = None
        user_id_keys = ["user_id", "_id", "id", "uid"]

        for key in user_id_keys:
            if current_user and current_user.get(key):
                authenticated_user_id = str(current_user[key])
                break
        
        if not authenticated_user_id:
            raise HTTPException(status_code=401, detail="Authentication required")

        dream_matrix_service = DreamMatrixService()
        result = dream_matrix_service.get_dream_matrix_details(authenticated_user_id, tree_id)

        if result["success"]:
            return success_response(result["data"])
        else:
            raise HTTPException(status_code=404, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))
