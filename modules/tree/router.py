from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from modules.tree.service import TreeService
from auth.service import authentication_service
from utils.response import ResponseModel
from pydantic import BaseModel

router = APIRouter(prefix="/tree", tags=["Tree Management"])


class CreateTreePlacementRequest(BaseModel):
    user_id: str
    referrer_id: str
    program: str = 'binary'
    slot_no: int = 1


@router.post("/placement")
async def create_tree_placement(
    request: CreateTreePlacementRequest,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Create tree placement with binary tree logic
    """
    try:
        result = await TreeService.create_tree_placement(
            user_id=request.user_id,
            referrer_id=request.referrer_id,
            program=request.program,
            slot_no=request.slot_no
        )
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/binary")
async def get_binary_tree_data(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Get binary tree data for a specific user
    Returns data in frontend-compatible format
    """
    try:
        # Check if user is authorized to view this data
        if str(current_user.get('_id')) != user_id:
            # Add admin check here if needed
            pass
        
        result = await TreeService.get_tree_data(user_id, 'binary')
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/matrix")
async def get_matrix_tree_data(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Get matrix tree data for a specific user
    Returns data in frontend-compatible format
    """
    try:
        # Check if user is authorized to view this data
        if str(current_user.get('_id')) != user_id:
            # Add admin check here if needed
            pass
        
        result = await TreeService.get_tree_data(user_id, 'matrix')
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/global")
async def get_global_tree_data(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Get global matrix tree data for a specific user
    Returns data in frontend-compatible format
    """
    try:
        # Check if user is authorized to view this data
        if str(current_user.get('_id')) != user_id:
            # Add admin check here if needed
            pass
        
        result = await TreeService.get_tree_data(user_id, 'global')
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/all")
async def get_all_tree_data(
    user_id: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Get all tree types (binary, matrix, global) for a specific user
    Returns data in frontend-compatible format
    """
    try:
        # Check if user is authorized to view this data
        if str(current_user.get('_id')) != user_id:
            # Add admin check here if needed
            pass
        
        result = await TreeService.get_all_trees_by_user(user_id)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/{program}")
async def get_tree_data_by_program(
    user_id: str,
    program: str,
    current_user: dict = Depends(authentication_service.verify_authentication)
):
    """
    Get tree data for a specific user and program type
    program can be: binary, matrix, global
    """
    try:
        # Validate program type
        valid_programs = ['binary', 'matrix', 'global']
        if program not in valid_programs:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid program type. Must be one of: {valid_programs}"
            )
        
        # Check if user is authorized to view this data
        if str(current_user.get('_id')) != user_id:
            # Add admin check here if needed
            pass
        
        result = await TreeService.get_tree_data(user_id, program)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
