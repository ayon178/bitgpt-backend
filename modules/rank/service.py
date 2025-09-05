from typing import List, Optional, Dict, Any, Tuple
from bson import ObjectId
from decimal import Decimal
from datetime import datetime, timedelta
from ..user.model import User
from ..slot.model import SlotActivation
from ..tree.model import TreePlacement
from .model import (
    Rank, UserRank, RankAchievement, RankBonus, 
    RankLeaderboard, RankSettings, RankMilestone,
    RankRequirement, RankBenefit
)

class RankService:
    """Rank System Business Logic Service"""
    
    def __init__(self):
        pass
    
    def initialize_ranks(self) -> Dict[str, Any]:
        """Initialize all 15 special ranks with their requirements and benefits"""
        try:
            # Define all 15 ranks based on PROJECT_DOCUMENTATION.md
            ranks_data = [
                # Row 1 (Ranks 1-5)
                {"number": 1, "name": "Bitron", "row": 1, "description": "Entry level rank - First step in BitGPT journey"},
                {"number": 2, "name": "Cryzen", "row": 1, "description": "Early achiever - Shows initial progress"},
                {"number": 3, "name": "Neura", "row": 1, "description": "Growing member - Building momentum"},
                {"number": 4, "name": "Glint", "row": 1, "description": "Shining performer - Consistent growth"},
                {"number": 5, "name": "Stellar", "row": 1, "description": "Star performer - Exceptional achievement"},
                
                # Row 2 (Ranks 6-10)
                {"number": 6, "name": "Ignis", "row": 2, "description": "Fire starter - Igniting team growth"},
                {"number": 7, "name": "Quanta", "row": 2, "description": "Quantum leap - Major advancement"},
                {"number": 8, "name": "Lumix", "row": 2, "description": "Light bringer - Illuminating path for others"},
                {"number": 9, "name": "Arion", "row": 2, "description": "Swift achiever - Rapid progress"},
                {"number": 10, "name": "Nexus", "row": 2, "description": "Connection master - Building networks"},
                
                # Row 3 (Ranks 11-15)
                {"number": 11, "name": "Fyre", "row": 3, "description": "Burning passion - Intense dedication"},
                {"number": 12, "name": "Axion", "row": 3, "description": "Core leader - Central to success"},
                {"number": 13, "name": "Trion", "row": 3, "description": "Triple master - Excellence in all areas"},
                {"number": 14, "name": "Spectra", "row": 3, "description": "Full spectrum - Complete mastery"},
                {"number": 15, "name": "Omega", "row": 3, "description": "Ultimate achiever - Highest rank possible"}
            ]
            
            created_count = 0
            updated_count = 0
            
            for rank_data in ranks_data:
                rank = Rank.objects(rank_number=rank_data["number"]).first()
                
                if not rank:
                    # Create new rank
                    rank = Rank(
                        rank_number=rank_data["number"],
                        rank_name=rank_data["name"],
                        rank_row=rank_data["row"],
                        rank_description=rank_data["description"],
                        is_final_rank=(rank_data["number"] == 15)
                    )
                    
                    # Add requirements based on rank number
                    self._add_rank_requirements(rank)
                    
                    # Add benefits based on rank number
                    self._add_rank_benefits(rank)
                    
                    rank.save()
                    created_count += 1
                else:
                    # Update existing rank
                    rank.rank_name = rank_data["name"]
                    rank.rank_row = rank_data["row"]
                    rank.rank_description = rank_data["description"]
                    rank.is_final_rank = (rank_data["number"] == 15)
                    rank.updated_at = datetime.utcnow()
                    rank.save()
                    updated_count += 1
            
            return {
                "success": True,
                "created_count": created_count,
                "updated_count": updated_count,
                "total_ranks": len(ranks_data),
                "message": f"Initialized {created_count} new ranks, updated {updated_count} existing ranks"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def update_user_rank(self, user_id: str, force_update: bool = False) -> Dict[str, Any]:
        """Update user's rank based on current achievements"""
        try:
            # Get user's current rank
            user_rank = UserRank.objects(user_id=ObjectId(user_id)).first()
            if not user_rank:
                # Create initial user rank
                user_rank = self._create_initial_user_rank(user_id)
            
            # Get user's current achievements
            achievements = self._get_user_achievements(user_id)
            
            # Determine new rank based on achievements
            new_rank_number = self._calculate_user_rank(achievements)
            
            # Check if rank should be updated
            if new_rank_number > user_rank.current_rank_number or force_update:
                # Update user rank
                old_rank_number = user_rank.current_rank_number
                old_rank_name = user_rank.current_rank_name
                
                # Get new rank details
                new_rank = Rank.objects(rank_number=new_rank_number).first()
                if not new_rank:
                    return {"success": False, "error": f"Rank {new_rank_number} not found"}
                
                # Update user rank
                user_rank.current_rank_number = new_rank_number
                user_rank.current_rank_name = new_rank.rank_name
                user_rank.rank_achieved_at = datetime.utcnow()
                
                # Add to rank history
                user_rank.rank_history.append({
                    "rank_number": old_rank_number,
                    "rank_name": old_rank_name,
                    "achieved_at": user_rank.rank_achieved_at
                })
                
                # Update next rank
                if new_rank_number < 15:
                    user_rank.next_rank_number = new_rank_number + 1
                    next_rank = Rank.objects(rank_number=user_rank.next_rank_number).first()
                    user_rank.next_rank_name = next_rank.rank_name if next_rank else "Unknown"
                else:
                    user_rank.next_rank_number = 15
                    user_rank.next_rank_name = "Omega"
                
                # Update achievements
                user_rank.binary_slots_activated = achievements['binary_slots']
                user_rank.matrix_slots_activated = achievements['matrix_slots']
                user_rank.global_slots_activated = achievements['global_slots']
                user_rank.total_slots_activated = achievements['total_slots']
                user_rank.total_team_size = achievements['team_size']
                user_rank.direct_partners_count = achievements['direct_partners']
                user_rank.total_earnings = achievements['total_earnings']
                
                # Update special qualifications
                user_rank.royal_captain_eligible = new_rank_number >= 5
                user_rank.president_reward_eligible = new_rank_number >= 10
                user_rank.top_leader_gift_eligible = new_rank_number >= 15
                user_rank.leadership_stipend_eligible = new_rank_number >= 10
                
                # Calculate progress percentage
                user_rank.progress_percentage = self._calculate_progress_percentage(user_rank)
                
                user_rank.last_updated = datetime.utcnow()
                user_rank.save()
                
                # Create rank achievement record
                self._create_rank_achievement(user_id, new_rank_number, new_rank.rank_name, achievements)
                
                # Check for milestones
                self._check_and_create_milestones(user_id, new_rank_number)
                
                return {
                    "success": True,
                    "old_rank": {"number": old_rank_number, "name": old_rank_name},
                    "new_rank": {"number": new_rank_number, "name": new_rank.rank_name},
                    "achievements": achievements,
                    "special_qualifications": {
                        "royal_captain_eligible": user_rank.royal_captain_eligible,
                        "president_reward_eligible": user_rank.president_reward_eligible,
                        "top_leader_gift_eligible": user_rank.top_leader_gift_eligible,
                        "leadership_stipend_eligible": user_rank.leadership_stipend_eligible
                    },
                    "message": f"Rank updated from {old_rank_name} to {new_rank.rank_name}"
                }
            else:
                return {
                    "success": True,
                    "current_rank": {"number": user_rank.current_rank_number, "name": user_rank.current_rank_name},
                    "message": "No rank update needed"
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def calculate_rank_bonus(self, user_id: str, bonus_type: str) -> Dict[str, Any]:
        """Calculate rank-based bonus for user"""
        try:
            user_rank = UserRank.objects(user_id=ObjectId(user_id)).first()
            if not user_rank:
                return {"success": False, "error": "User rank not found"}
            
            # Get rank details
            rank = Rank.objects(rank_number=user_rank.current_rank_number).first()
            if not rank:
                return {"success": False, "error": "Rank not found"}
            
            # Calculate bonus based on rank and type
            bonus_amount = 0.0
            currency = "BNB"  # Default currency
            
            if bonus_type == "commission_bonus":
                # Commission bonus based on rank
                base_commission = 100.0  # Base commission amount
                bonus_percentage = user_rank.current_rank_number * 5.0  # 5% per rank
                bonus_amount = base_commission * (bonus_percentage / 100)
                currency = "BNB"
                
            elif bonus_type == "daily_income":
                # Daily income based on rank
                base_daily = 10.0  # Base daily income
                bonus_amount = base_daily * user_rank.current_rank_number
                currency = "USDT"
                
            elif bonus_type == "special_bonus":
                # Special bonus for higher ranks
                if user_rank.current_rank_number >= 10:
                    bonus_amount = 500.0
                    currency = "USD"
                elif user_rank.current_rank_number >= 5:
                    bonus_amount = 100.0
                    currency = "USDT"
                else:
                    bonus_amount = 50.0
                    currency = "BNB"
            
            return {
                "success": True,
                "user_id": user_id,
                "current_rank": user_rank.current_rank_number,
                "rank_name": user_rank.current_rank_name,
                "bonus_type": bonus_type,
                "bonus_amount": bonus_amount,
                "currency": currency,
                "message": f"Rank bonus calculated: {bonus_amount} {currency}"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_rank_leaderboard(self, period: str = "all_time") -> Dict[str, Any]:
        """Get rank leaderboard for specified period"""
        try:
            # Calculate period dates
            now = datetime.utcnow()
            if period == "daily":
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(days=1)
            elif period == "weekly":
                start_date = now - timedelta(days=now.weekday())
                start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_date = start_date + timedelta(weeks=1)
            elif period == "monthly":
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                if start_date.month == 12:
                    end_date = start_date.replace(year=start_date.year + 1, month=1)
                else:
                    end_date = start_date.replace(month=start_date.month + 1)
            else:  # all_time
                start_date = datetime(2024, 1, 1)
                end_date = now
            
            # Get all user ranks
            user_ranks = UserRank.objects(is_active=True).all()
            
            # Create leaderboard data
            leaderboard_data = []
            for user_rank in user_ranks:
                # Calculate score based on rank and achievements
                score = self._calculate_rank_score(user_rank)
                
                leaderboard_data.append({
                    "user_id": str(user_rank.user_id),
                    "rank_number": user_rank.current_rank_number,
                    "rank_name": user_rank.current_rank_name,
                    "score": score,
                    "total_slots": user_rank.total_slots_activated,
                    "team_size": user_rank.total_team_size,
                    "earnings": user_rank.total_earnings
                })
            
            # Sort by score (descending)
            leaderboard_data.sort(key=lambda x: x["score"], reverse=True)
            
            # Create or update leaderboard
            leaderboard = RankLeaderboard.objects(period=period).first()
            if not leaderboard:
                leaderboard = RankLeaderboard(period=period)
            
            leaderboard.period_start = start_date
            leaderboard.period_end = end_date
            leaderboard.leaderboard_data = leaderboard_data
            leaderboard.total_participants = len(leaderboard_data)
            leaderboard.top_rank_achieved = leaderboard_data[0]["rank_number"] if leaderboard_data else 1
            leaderboard.average_rank = sum(item["rank_number"] for item in leaderboard_data) / len(leaderboard_data) if leaderboard_data else 1
            leaderboard.last_updated = datetime.utcnow()
            leaderboard.save()
            
            return {
                "success": True,
                "period": period,
                "period_start": start_date,
                "period_end": end_date,
                "leaderboard_data": leaderboard_data[:100],  # Top 100
                "total_participants": leaderboard.total_participants,
                "top_rank_achieved": leaderboard.top_rank_achieved,
                "average_rank": leaderboard.average_rank,
                "last_updated": leaderboard.last_updated
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _add_rank_requirements(self, rank: Rank):
        """Add requirements for a rank"""
        rank_number = rank.rank_number
        
        # Base requirements - each rank needs more slots activated
        min_slots = rank_number * 2  # Progressive requirement
        
        # Binary requirements
        binary_req = RankRequirement(
            program="binary",
            min_slots_activated=max(1, min_slots // 2),
            min_slot_level=min(rank_number, 16),
            min_team_size=max(2, rank_number * 2),
            min_direct_partners=max(1, rank_number // 2)
        )
        rank.requirements.append(binary_req)
        
        # Matrix requirements (for ranks 3+)
        if rank_number >= 3:
            matrix_req = RankRequirement(
                program="matrix",
                min_slots_activated=max(1, min_slots // 3),
                min_slot_level=min(rank_number - 2, 5),
                min_team_size=max(3, rank_number * 3),
                min_direct_partners=max(1, rank_number // 3)
            )
            rank.requirements.append(matrix_req)
        
        # Global requirements (for ranks 5+)
        if rank_number >= 5:
            global_req = RankRequirement(
                program="global",
                min_slots_activated=max(1, min_slots // 4),
                min_slot_level=min(rank_number - 4, 16),
                min_team_size=max(4, rank_number * 4),
                min_direct_partners=max(1, rank_number // 4)
            )
            rank.requirements.append(global_req)
    
    def _add_rank_benefits(self, rank: Rank):
        """Add benefits for a rank"""
        rank_number = rank.rank_number
        
        # Commission bonus benefit
        commission_bonus = RankBenefit(
            benefit_type="commission_bonus",
            benefit_value=rank_number * 5.0,  # 5% per rank
            benefit_description=f"{rank_number * 5}% commission bonus",
            is_active=True
        )
        rank.benefits.append(commission_bonus)
        
        # Daily income benefit (for ranks 5+)
        if rank_number >= 5:
            daily_income = RankBenefit(
                benefit_type="daily_income",
                benefit_value=rank_number * 10.0,  # $10 per rank
                benefit_description=f"${rank_number * 10} daily income",
                is_active=True
            )
            rank.benefits.append(daily_income)
        
        # Special bonuses for higher ranks
        if rank_number >= 10:
            special_bonus = RankBenefit(
                benefit_type="special_bonus",
                benefit_value=500.0,
                benefit_description="Special bonus privileges",
                is_active=True
            )
            rank.benefits.append(special_bonus)
        
        # Royal Captain eligibility (ranks 5+)
        if rank_number >= 5:
            royal_captain = RankBenefit(
                benefit_type="royal_captain_eligible",
                benefit_value=0.0,
                benefit_description="Eligible for Royal Captain Bonus",
                is_active=True
            )
            rank.benefits.append(royal_captain)
        
        # President Reward eligibility (ranks 10+)
        if rank_number >= 10:
            president_reward = RankBenefit(
                benefit_type="president_reward_eligible",
                benefit_value=0.0,
                benefit_description="Eligible for President Reward",
                is_active=True
            )
            rank.benefits.append(president_reward)
        
        # Top Leader Gift eligibility (rank 15)
        if rank_number == 15:
            top_leader_gift = RankBenefit(
                benefit_type="top_leader_gift_eligible",
                benefit_value=0.0,
                benefit_description="Eligible for Top Leader Gift",
                is_active=True
            )
            rank.benefits.append(top_leader_gift)
    
    def _create_initial_user_rank(self, user_id: str) -> UserRank:
        """Create initial user rank (Bitron)"""
        user_rank = UserRank(
            user_id=ObjectId(user_id),
            current_rank_number=1,
            current_rank_name="Bitron",
            next_rank_number=2,
            next_rank_name="Cryzen",
            progress_percentage=0.0,
            rank_achieved_at=datetime.utcnow()
        )
        user_rank.save()
        return user_rank
    
    def _get_user_achievements(self, user_id: str) -> Dict[str, Any]:
        """Get user's current achievements"""
        try:
            # Get slot activations
            binary_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program="binary",
                status="completed"
            ).count()
            
            matrix_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program="matrix",
                status="completed"
            ).count()
            
            global_activations = SlotActivation.objects(
                user_id=ObjectId(user_id),
                program="global",
                status="completed"
            ).count()
            
            # Get team statistics
            team_size = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                is_active=True
            ).count()
            
            direct_partners = TreePlacement.objects(
                parent_id=ObjectId(user_id),
                is_active=True
            ).count()
            
            # Get total earnings (simplified)
            total_earnings = (binary_activations * 10.0 + 
                            matrix_activations * 50.0 + 
                            global_activations * 100.0)
            
            return {
                "binary_slots": binary_activations,
                "matrix_slots": matrix_activations,
                "global_slots": global_activations,
                "total_slots": binary_activations + matrix_activations + global_activations,
                "team_size": team_size,
                "direct_partners": direct_partners,
                "total_earnings": total_earnings
            }
            
        except Exception:
            return {
                "binary_slots": 0,
                "matrix_slots": 0,
                "global_slots": 0,
                "total_slots": 0,
                "team_size": 0,
                "direct_partners": 0,
                "total_earnings": 0.0
            }
    
    def _calculate_user_rank(self, achievements: Dict[str, Any]) -> int:
        """Calculate user's rank based on achievements"""
        total_slots = achievements["total_slots"]
        
        # Progressive rank calculation
        if total_slots >= 30:
            return 15  # Omega
        elif total_slots >= 25:
            return 14  # Spectra
        elif total_slots >= 20:
            return 13  # Trion
        elif total_slots >= 18:
            return 12  # Axion
        elif total_slots >= 16:
            return 11  # Fyre
        elif total_slots >= 14:
            return 10  # Nexus
        elif total_slots >= 12:
            return 9   # Arion
        elif total_slots >= 10:
            return 8   # Lumix
        elif total_slots >= 8:
            return 7   # Quanta
        elif total_slots >= 6:
            return 6   # Ignis
        elif total_slots >= 5:
            return 5   # Stellar
        elif total_slots >= 4:
            return 4   # Glint
        elif total_slots >= 3:
            return 3   # Neura
        elif total_slots >= 2:
            return 2   # Cryzen
        else:
            return 1   # Bitron
    
    def _calculate_progress_percentage(self, user_rank: UserRank) -> float:
        """Calculate progress percentage towards next rank"""
        current_rank = user_rank.current_rank_number
        next_rank = user_rank.next_rank_number
        
        if current_rank >= 15:
            return 100.0
        
        # Calculate progress based on slots activated
        current_slots = user_rank.total_slots_activated
        required_slots = next_rank * 2  # Next rank requirement
        
        if required_slots <= current_slots:
            return 100.0
        
        progress = (current_slots / required_slots) * 100
        return min(progress, 100.0)
    
    def _create_rank_achievement(self, user_id: str, rank_number: int, rank_name: str, achievements: Dict[str, Any]):
        """Create rank achievement record"""
        achievement = RankAchievement(
            user_id=ObjectId(user_id),
            rank_number=rank_number,
            rank_name=rank_name,
            binary_slots_at_achievement=achievements["binary_slots"],
            matrix_slots_at_achievement=achievements["matrix_slots"],
            global_slots_at_achievement=achievements["global_slots"],
            team_size_at_achievement=achievements["team_size"],
            earnings_at_achievement=achievements["total_earnings"]
        )
        achievement.save()
    
    def _check_and_create_milestones(self, user_id: str, rank_number: int):
        """Check and create milestones for user"""
        milestones_to_check = [
            {"type": "first_rank", "rank": 1},
            {"type": "rank_5_achieved", "rank": 5},
            {"type": "rank_10_achieved", "rank": 10},
            {"type": "rank_15_achieved", "rank": 15}
        ]
        
        for milestone in milestones_to_check:
            if rank_number == milestone["rank"]:
                # Check if milestone already exists
                existing = RankMilestone.objects(
                    user_id=ObjectId(user_id),
                    milestone_type=milestone["type"]
                ).first()
                
                if not existing:
                    milestone_obj = RankMilestone(
                        user_id=ObjectId(user_id),
                        milestone_type=milestone["type"],
                        milestone_name=f"Achieved Rank {milestone['rank']}",
                        milestone_description=f"User achieved rank {milestone['rank']}",
                        reward_value=milestone["rank"] * 100.0,
                        reward_type="bonus"
                    )
                    milestone_obj.save()
    
    def _calculate_rank_score(self, user_rank: UserRank) -> float:
        """Calculate rank score for leaderboard"""
        # Score based on rank number, slots activated, and team size
        rank_score = user_rank.current_rank_number * 100
        slots_score = user_rank.total_slots_activated * 10
        team_score = user_rank.total_team_size * 5
        earnings_score = user_rank.total_earnings * 0.1
        
        return rank_score + slots_score + team_score + earnings_score
