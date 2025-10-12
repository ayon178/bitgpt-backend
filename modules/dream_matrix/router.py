from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from auth.service import authentication_service
from utils.response import success_response, error_response
from .service import DreamMatrixService
from ..user.model import User

router = APIRouter(prefix="/dream-matrix", tags=["Dream Matrix"])

@router.get("/earnings/{user_id}")
async def get_dream_matrix_earnings(
    user_id: str,
    slot_no: Optional[int] = None,
    recycle_no: Optional[int] = None,
    # current_user: dict = Depends(authentication_service.verify_authentication)
):
    """Get Dream Matrix earnings data matching frontend matrixData.js structure"""
    try:
        # Extract user ID from current_user with fallback options
        # authenticated_user_id = None
        # user_id_keys = ["user_id", "_id", "id", "uid"]

        # for key in user_id_keys:
        #     if current_user and current_user.get(key):
        #         authenticated_user_id = str(current_user[key])
        #         break
        
        # # Authorization check - users can only access their own data
        # if authenticated_user_id and authenticated_user_id != user_id:
        #     raise HTTPException(status_code=403, detail="Unauthorized to view this user's Dream Matrix earnings")

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

@router.get("/details")
async def get_dream_matrix_details(
    uid: str,
    tree_id: Optional[int] = None
):
    """
    Get Dream Matrix tree details by tree ID or last tree if tree_id not provided
    
    Examples:
    - /dream-matrix/details?uid=AUTO001 - Returns last tree for user
    - /dream-matrix/details?uid=AUTO001&tree_id=3 - Returns specific tree with ID 3
    """
    try:
        if not uid:
            raise HTTPException(status_code=400, detail="uid parameter is required")
        
        # Find user by uid
        user = User.objects(uid=uid).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_id = str(user.id)

        dream_matrix_service = DreamMatrixService()
        
        # If tree_id is provided, return specific tree
        if tree_id is not None:
            result = dream_matrix_service.get_dream_matrix_details(user_id, tree_id)
            
            if result["success"]:
                return success_response(result["data"])
            else:
                raise HTTPException(status_code=404, detail=result["error"])
        
        # If tree_id is not provided, return last tree from matrixTreeData
        else:
            result = dream_matrix_service.get_dream_matrix_earnings(user_id, None, None)
            
            if result["success"]:
                matrix_tree_data = result["data"].get("matrixTreeData", [])
                
                if not matrix_tree_data:
                    raise HTTPException(status_code=404, detail="No matrix data found for this user")
                
                # Return only the last tree object
                last_tree = matrix_tree_data[-1]
                return success_response(last_tree)
            else:
                raise HTTPException(status_code=400, detail=result["error"])

    except HTTPException:
        raise
    except Exception as e:
        return error_response(str(e))
