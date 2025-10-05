"""
Mandatory Join Sequence Enforcement Service

This service enforces the critical business rule:
1. Binary Program (Required first) - Cannot join other programs without Binary
2. Matrix Program (Required second) - Cannot join Global without Matrix  
3. Global Program (Required third) - Final program in sequence

Based on PROJECT_DOCUMENTATION.md Section 5. PLATFORM REQUIREMENTS AND DEPLOYMENT
"""

from typing import Dict, Any, Tuple, Optional
from bson import ObjectId
from modules.user.model import User
from utils.response import create_response


class ProgramSequenceService:
    """Service to enforce mandatory program join sequence"""
    
    def __init__(self):
        self.required_sequence = ['binary', 'matrix', 'global']
    
    def validate_program_join_sequence(self, user_id: str, target_program: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if user can join the target program based on mandatory sequence
        
        Args:
            user_id: User ID to validate
            target_program: Program user wants to join ('binary', 'matrix', 'global')
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return False, "User not found"
            
            # Check if target program is valid
            if target_program not in self.required_sequence:
                return False, f"Invalid program: {target_program}. Must be one of: {', '.join(self.required_sequence)}"
            
            # Binary is always allowed (first in sequence)
            if target_program == 'binary':
                return True, None
            
            # Check if user has joined Binary (required for all other programs)
            if not user.binary_joined:
                return False, f"Must join Binary program first before joining {target_program.title()}"
            
            # For Matrix program
            if target_program == 'matrix':
                return True, None  # Binary is required and checked above
            
            # For Global program
            if target_program == 'global':
                if not user.matrix_joined:
                    return False, "Must join Matrix program first before joining Global program"
                return True, None
            
            return False, f"Unknown validation error for program: {target_program}"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_user_program_sequence_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's current program sequence status
        
        Returns:
            Dict containing program participation status and next allowed programs
        """
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            # Check current program participation
            program_status = {
                "binary": {
                    "joined": user.binary_joined,
                    "required": True,
                    "position": 1
                },
                "matrix": {
                    "joined": user.matrix_joined,
                    "required": True,
                    "position": 2
                },
                "global": {
                    "joined": user.global_joined,
                    "required": True,
                    "position": 3
                }
            }
            
            # Determine next allowed programs
            next_allowed = []
            if not user.binary_joined:
                next_allowed.append("binary")
            elif not user.matrix_joined:
                next_allowed.append("matrix")
            elif not user.global_joined:
                next_allowed.append("global")
            
            # Check if sequence is complete
            sequence_complete = user.binary_joined and user.matrix_joined and user.global_joined
            
            return {
                "success": True,
                "data": {
                    "user_id": str(user.id),
                    "uid": user.uid,
                    "program_status": program_status,
                    "next_allowed_programs": next_allowed,
                    "sequence_complete": sequence_complete,
                    "current_position": len([p for p in [user.binary_joined, user.matrix_joined, user.global_joined] if p])
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_program_sequence_info(self) -> Dict[str, Any]:
        """
        Get information about the mandatory program sequence
        
        Returns:
            Dict containing sequence information
        """
        return {
            "success": True,
            "data": {
                "sequence": self.required_sequence,
                "rules": {
                    "binary": {
                        "position": 1,
                        "required": True,
                        "description": "Must join Binary program first",
                        "cost": "0.0066 BNB",
                        "auto_activates": "Slots 1 and 2"
                    },
                    "matrix": {
                        "position": 2,
                        "required": True,
                        "description": "Can only join after Binary",
                        "cost": "$11 USDT",
                        "requires": "Binary program participation"
                    },
                    "global": {
                        "position": 3,
                        "required": True,
                        "description": "Can only join after Matrix",
                        "cost": "$33 USD",
                        "requires": "Matrix program participation"
                    }
                },
                "enforcement": {
                    "strict_sequence": True,
                    "no_skipping": True,
                    "referral_id_reuse": True,
                    "description": "Users must follow exact sequence: Binary → Matrix → Global"
                }
            }
        }
    
    def check_user_sequence_compliance(self, user_id: str) -> Dict[str, Any]:
        """
        Check if user's program participation follows the mandatory sequence
        
        Returns:
            Dict containing compliance status and any violations
        """
        try:
            # Get user
            user = User.objects(id=ObjectId(user_id)).first()
            if not user:
                return {
                    "success": False,
                    "error": "User not found"
                }
            
            violations = []
            is_compliant = True
            
            # Check sequence compliance
            if user.matrix_joined and not user.binary_joined:
                violations.append("Matrix joined without Binary participation")
                is_compliant = False
            
            if user.global_joined and not user.matrix_joined:
                violations.append("Global joined without Matrix participation")
                is_compliant = False
            
            if user.global_joined and not user.binary_joined:
                violations.append("Global joined without Binary participation")
                is_compliant = False
            
            return {
                "success": True,
                "data": {
                    "user_id": str(user.id),
                    "uid": user.uid,
                    "is_compliant": is_compliant,
                    "violations": violations,
                    "program_participation": {
                        "binary": user.binary_joined,
                        "matrix": user.matrix_joined,
                        "global": user.global_joined
                    }
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
