from typing import List, Dict, Any, Optional
from bson import ObjectId
from ..tree.model import TreePlacement
from ..user.model import User
from utils.response import ResponseModel


class TreeService:
    
    @staticmethod
    async def create_tree_placement(
        user_id: str,
        referrer_id: str,
        program: str = 'binary',
        slot_no: int = 1
    ) -> ResponseModel:
        """
        Create tree placement with binary tree logic
        Scenario 1: Direct referral - check if referrer has 2 positions filled
        Scenario 2: Indirect referral - find lowest level available position
        """
        try:
            user_object_id = ObjectId(user_id)
            referrer_object_id = ObjectId(referrer_id)
            
            # Check if user already has placement in this program and slot
            existing_placement = TreePlacement.objects(
                user_id=user_object_id,
                program=program,
                slot_no=slot_no,
                is_active=True
            ).first()
            
            if existing_placement:
                return ResponseModel(
                    success=False,
                    message="User already has placement in this program and slot",
                    data=None
                )
            
            # Scenario 1: Direct referral placement
            placement_result = await TreeService._handle_direct_referral_placement(
                user_object_id, referrer_object_id, program, slot_no
            )
            
            if placement_result:
                return ResponseModel(
                    success=True,
                    message="Tree placement created successfully (direct referral)",
                    data=placement_result
                )
            
            # Scenario 2: Indirect referral placement (spillover)
            placement_result = await TreeService._handle_indirect_referral_placement(
                user_object_id, referrer_object_id, program, slot_no
            )
            
            if placement_result:
                return ResponseModel(
                    success=True,
                    message="Tree placement created successfully (indirect referral)",
                    data=placement_result
                )
            
            return ResponseModel(
                success=False,
                message="No available position found in the tree",
                data=None
            )
            
        except Exception as e:
            print(f"Error creating tree placement: {e}")
            return ResponseModel(
                success=False,
                message=f"Error creating tree placement: {str(e)}",
                data=None
            )
    
    @staticmethod
    async def _handle_direct_referral_placement(
        user_id: ObjectId,
        referrer_id: ObjectId,
        program: str,
        slot_no: int
    ) -> Optional[TreePlacement]:
        """
        Handle direct referral placement logic
        Check if referrer has less than 2 positions filled
        """
        # Get referrer's existing placements in this program and slot
        referrer_placements = TreePlacement.objects(
            parent_id=referrer_id,
            program=program,
            slot_no=slot_no,
            is_active=True
        ).order_by('position')
        
        # Count existing children
        left_child = referrer_placements.filter(position='left').first()
        right_child = referrer_placements.filter(position='right').first()
        
        # Determine position
        if not left_child:
            # First position available - place on left
            position = 'left'
            level = await TreeService._calculate_level(referrer_id, program, slot_no) + 1
        elif not right_child:
            # Second position available - place on right
            position = 'right'
            level = await TreeService._calculate_level(referrer_id, program, slot_no) + 1
        else:
            # Both positions filled - cannot place directly under referrer
            return None
        
        # Create placement
        placement = TreePlacement(
            user_id=user_id,
            program=program,
            parent_id=referrer_id,
            position=position,
            level=level,
            slot_no=slot_no,
            is_active=True
        )
        placement.save()
        
        return placement
    
    @staticmethod
    async def _handle_indirect_referral_placement(
        user_id: ObjectId,
        referrer_id: ObjectId,
        program: str,
        slot_no: int
    ) -> Optional[TreePlacement]:
        """
        Handle indirect referral placement logic (spillover)
        Find lowest level available position
        """
        # Get all placements in this program and slot
        all_placements = TreePlacement.objects(
            program=program,
            slot_no=slot_no,
            is_active=True
        ).order_by('level', 'position')
        
        # Find the lowest level
        max_level = 0
        if all_placements:
            max_level = all_placements.aggregate([
                {'$group': {'_id': None, 'max_level': {'$max': '$level'}}}
            ]).next()['max_level']
        
        # Find available position at lowest level
        for level in range(1, max_level + 2):  # +2 to include next level
            level_placements = all_placements.filter(level=level)
            
            # Check first position (left)
            left_position = level_placements.filter(position='left').first()
            if not left_position:
                # Find parent for this position
                parent = await TreeService._find_parent_for_position(level, 'left', program, slot_no)
                if parent:
                    placement = TreePlacement(
                        user_id=user_id,
                        program=program,
                        parent_id=parent,
                        position='left',
                        level=level,
                        slot_no=slot_no,
                        is_active=True
                    )
                    placement.save()
                    return placement
            
            # Check last position (right)
            right_position = level_placements.filter(position='right').first()
            if not right_position:
                # Find parent for this position
                parent = await TreeService._find_parent_for_position(level, 'right', program, slot_no)
                if parent:
                    placement = TreePlacement(
                        user_id=user_id,
                        program=program,
                        parent_id=parent,
                        position='right',
                        level=level,
                        slot_no=slot_no,
                        is_active=True
                    )
                    placement.save()
                    return placement
        
        return None
    
    @staticmethod
    async def _calculate_level(parent_id: ObjectId, program: str, slot_no: int) -> int:
        """
        Calculate level based on parent's level
        """
        parent_placement = TreePlacement.objects(
            user_id=parent_id,
            program=program,
            slot_no=slot_no,
            is_active=True
        ).first()
        
        if parent_placement:
            return parent_placement.level
        return 1  # Default level if no parent found
    
    @staticmethod
    async def _find_parent_for_position(level: int, position: str, program: str, slot_no: int) -> Optional[ObjectId]:
        """
        Find parent for a specific position at a given level
        """
        if level == 1:
            # Root level - no parent needed
            return None
        
        # Calculate parent level
        parent_level = level - 1
        
        # Get all parents at parent level
        parent_placements = TreePlacement.objects(
            program=program,
            slot_no=slot_no,
            level=parent_level,
            is_active=True
        )
        
        # Find parent that doesn't have this position filled
        for parent in parent_placements:
            existing_child = TreePlacement.objects(
                parent_id=parent.user_id,
                program=program,
                slot_no=slot_no,
                position=position,
                is_active=True
            ).first()
            
            if not existing_child:
                return parent.user_id
        
        return None
    
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
