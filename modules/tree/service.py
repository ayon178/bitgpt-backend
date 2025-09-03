from typing import List, Dict, Any, Optional
from bson import ObjectId
from ..tree.model import TreePlacement
from ..user.model import User
from ..user.service import UserService
from ..utils.response import ResponseModel


class TreeService:
    
    @staticmethod
    async def get_tree_data(user_id: str, program: str = 'binary') -> ResponseModel:
        """
        Get tree data for a specific user and program type
        Transforms tree_placement data into frontend-compatible format
        """
        try:
            # Convert string user_id to ObjectId
            user_object_id = ObjectId(user_id)
            
            # Get all tree placements for this user and program
            tree_placements = TreePlacement.objects(
                user_id=user_object_id,
                program=program,
                is_active=True
            ).order_by('level', 'slot_no')
            
            if not tree_placements:
                return ResponseModel(
                    success=False,
                    message="No tree data found for this user",
                    data=[]
                )
            
            # Group placements by slot_no (each slot represents a tree)
            trees_data = {}
            
            for placement in tree_placements:
                slot_no = placement.slot_no
                
                if slot_no not in trees_data:
                    trees_data[slot_no] = {
                        'id': slot_no,
                        'price': await TreeService._get_tree_price(program, slot_no),
                        'userId': str(placement.user_id),
                        'recycle': await TreeService._get_recycle_count(user_object_id, slot_no, program),
                        'isCompleted': await TreeService._is_tree_completed(slot_no, program),
                        'isProcess': await TreeService._is_tree_processing(slot_no, program),
                        'isAutoUpgrade': await TreeService._is_auto_upgrade_enabled(user_object_id, slot_no, program),
                        'isManualUpgrade': await TreeService._is_manual_upgrade_enabled(user_object_id, slot_no, program),
                        'processPercent': await TreeService._get_process_percentage(slot_no, program),
                        'users': []
                    }
                
                # Add user to the tree
                user_info = await TreeService._get_user_info(placement)
                if user_info:
                    trees_data[slot_no]['users'].append(user_info)
            
            # Convert to list format expected by frontend
            result = list(trees_data.values())
            
            return ResponseModel(
                success=True,
                message="Tree data retrieved successfully",
                data=result
            )
            
        except Exception as e:
            return ResponseModel(
                success=False,
                message=f"Error retrieving tree data: {str(e)}",
                data=[]
            )
    
    @staticmethod
    async def get_all_trees_by_user(user_id: str) -> ResponseModel:
        """
        Get all tree types (binary, matrix, global) for a user
        """
        try:
            user_object_id = ObjectId(user_id)
            
            # Get all programs for this user
            programs = ['binary', 'matrix', 'global']
            all_trees = {}
            
            for program in programs:
                program_trees = await TreeService.get_tree_data(user_id, program)
                if program_trees.success:
                    all_trees[program] = program_trees.data
            
            return ResponseModel(
                success=True,
                message="All tree data retrieved successfully",
                data=all_trees
            )
            
        except Exception as e:
            return ResponseModel(
                success=False,
                message=f"Error retrieving all tree data: {str(e)}",
                data={}
            )
    
    @staticmethod
    async def _get_user_info(placement: TreePlacement) -> Optional[Dict[str, Any]]:
        """
        Get user information for a tree position
        """
        try:
            # Get user details
            user = User.objects(id=placement.user_id).first()
            if not user:
                return None
            
            # Determine user type based on position
            user_type = TreeService._determine_user_type(placement)
            
            # Calculate position ID based on level and position
            position_id = TreeService._calculate_position_id(placement.level, placement.position)
            
            return {
                'id': position_id,
                'type': user_type,
                'userId': str(placement.user_id)
            }
            
        except Exception as e:
            print(f"Error getting user info: {e}")
            return None
    
    @staticmethod
    def _determine_user_type(placement: TreePlacement) -> str:
        """
        Determine user type: self, downLine, upLine, overTaker
        """
        # This logic needs to be customized based on your business rules
        # For now, using a simple approach
        
        if placement.position == 'center':
            return 'self'
        elif placement.position == 'left':
            return 'downLine'
        elif placement.position == 'right':
            return 'upLine'
        else:
            return 'overTaker'
    
    @staticmethod
    def _calculate_position_id(level: int, position: str) -> int:
        """
        Calculate position ID based on binary tree structure
        """
        # Binary tree position calculation
        # Level 1: Position 1
        # Level 2: Positions 2, 3
        # Level 3: Positions 4, 5, 6, 7
        # etc.
        
        if level == 1:
            return 1
        
        # Calculate base position for this level
        base_position = 2 ** (level - 1)
        
        # Adjust based on position within level
        if position == 'left':
            return base_position
        elif position == 'right':
            return base_position + 1
        elif position == 'center':
            return base_position + 2
        else:
            return base_position
    
    @staticmethod
    async def _get_tree_price(program: str, slot_no: int) -> float:
        """
        Get tree price based on program and slot
        """
        # This should be fetched from your pricing configuration
        # For now, returning mock data
        base_prices = {
            'binary': 500,
            'matrix': 800,
            'global': 1200
        }
        
        return base_prices.get(program, 500) + (slot_no * 10)
    
    @staticmethod
    async def _get_recycle_count(user_id: ObjectId, slot_no: int, program: str) -> int:
        """
        Get recycle count for a tree
        """
        # This should be fetched from recycle logs
        # For now, returning mock data
        return 0
    
    @staticmethod
    async def _is_tree_completed(slot_no: int, program: str) -> bool:
        """
        Check if tree is completed (all positions filled)
        """
        # Count total positions in tree
        total_positions = TreeService._get_total_positions(program)
        
        # Count filled positions
        filled_positions = TreePlacement.objects(
            slot_no=slot_no,
            program=program,
            is_active=True
        ).count()
        
        return filled_positions >= total_positions
    
    @staticmethod
    async def _is_tree_processing(slot_no: int, program: str) -> bool:
        """
        Check if tree is currently being processed
        """
        # This should check processing status
        # For now, returning False
        return False
    
    @staticmethod
    async def _is_auto_upgrade_enabled(user_id: ObjectId, slot_no: int, program: str) -> bool:
        """
        Check if auto upgrade is enabled for this tree
        """
        # This should check user settings
        # For now, returning False
        return False
    
    @staticmethod
    async def _is_manual_upgrade_enabled(user_id: ObjectId, slot_no: int, program: str) -> bool:
        """
        Check if manual upgrade is enabled for this tree
        """
        # This should check user settings
        # For now, returning False
        return False
    
    @staticmethod
    async def _get_process_percentage(slot_no: int, program: str) -> int:
        """
        Get completion percentage of the tree
        """
        total_positions = TreeService._get_total_positions(program)
        filled_positions = TreePlacement.objects(
            slot_no=slot_no,
            program=program,
            is_active=True
        ).count()
        
        if total_positions == 0:
            return 0
        
        percentage = (filled_positions / total_positions) * 100
        return int(percentage)
    
    @staticmethod
    def _get_total_positions(program: str) -> int:
        """
        Get total number of positions in a tree based on program type
        """
        if program == 'binary':
            return 7  # 3 levels: 1 + 2 + 4
        elif program == 'matrix':
            return 13  # 3x3 matrix + extra positions
        elif program == 'global':
            return 9  # 3x3 matrix
        else:
            return 7
