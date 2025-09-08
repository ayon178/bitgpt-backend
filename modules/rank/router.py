from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime, timedelta
from decimal import Decimal
from ..user.model import User
from .model import (
    Rank, UserRank, RankAchievement, RankBonus, 
    RankLeaderboard, RankSettings, RankMilestone,
    RankRequirement, RankBenefit
)
from utils.response import success_response, error_response

router = APIRouter(prefix="/rank", tags=["Rank System"])

# Pydantic models for request/response
class RankUpdateRequest(BaseModel):
    user_id: str
    force_update: bool = False

class RankBonusRequest(BaseModel):
    user_id: str
    rank_number: int
    bonus_type: str
    amount: float
    currency: str

class RankSettingsRequest(BaseModel):
    rank_system_enabled: bool
    auto_rank_progression: bool
    manual_rank_verification: bool
    rank_bonus_enabled: bool
    daily_rank_income_enabled: bool
    commission_bonus_percentage: float

class RankMilestoneRequest(BaseModel):
    user_id: str
    milestone_type: str
    reward_value: float = 0.0

# API Endpoints

@router.get("/list")
async def get_all_ranks():
    """Get all 15 special ranks"""
    try:
        ranks = Rank.objects(is_active=True).order_by('rank_number').all()
        
        return success_response(
            data={
                "ranks": [
                    {
                        "rank_number": rank.rank_number,
                        "rank_name": rank.rank_name,
                        "rank_row": rank.rank_row,
                        "rank_description": rank.rank_description,
                        "requirements": [
                            {
                                "program": req.program,
                                "min_slots_activated": req.min_slots_activated,
                                "min_slot_level": req.min_slot_level,
                                "min_team_size": req.min_team_size,
                                "min_direct_partners": req.min_direct_partners,
                                "min_earnings": req.min_earnings,
                                "special_conditions": req.special_conditions
                            } for req in rank.requirements
                        ],
                        "benefits": [
                            {
                                "benefit_type": benefit.benefit_type,
                                "benefit_value": benefit.benefit_value,
                                "benefit_description": benefit.benefit_description,
                                "is_active": benefit.is_active
                            } for benefit in rank.benefits
                        ],
                        "is_achievable": rank.is_achievable,
                        "is_final_rank": rank.is_final_rank,
                        "rank_icon": rank.rank_icon,
                        "rank_color": rank.rank_color
                    } for rank in ranks
                ],
                "total_ranks": len(ranks)
            },
            message="All ranks retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/{rank_number}")
async def get_rank_details(rank_number: int):
    """Get specific rank details"""
    try:
        rank = Rank.objects(rank_number=rank_number, is_active=True).first()
        if not rank:
            raise HTTPException(status_code=404, detail="Rank not found")
        
        return success_response(
            data={
                "rank_number": rank.rank_number,
                "rank_name": rank.rank_name,
                "rank_row": rank.rank_row,
                "rank_description": rank.rank_description,
                "requirements": [
                    {
                        "program": req.program,
                        "min_slots_activated": req.min_slots_activated,
                        "min_slot_level": req.min_slot_level,
                        "min_team_size": req.min_team_size,
                        "min_direct_partners": req.min_direct_partners,
                        "min_earnings": req.min_earnings,
                        "special_conditions": req.special_conditions
                    } for req in rank.requirements
                ],
                "benefits": [
                    {
                        "benefit_type": benefit.benefit_type,
                        "benefit_value": benefit.benefit_value,
                        "benefit_description": benefit.benefit_description,
                        "is_active": benefit.is_active
                    } for benefit in rank.benefits
                ],
                "is_achievable": rank.is_achievable,
                "is_final_rank": rank.is_final_rank,
                "rank_icon": rank.rank_icon,
                "rank_color": rank.rank_color
            },
            message="Rank details retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/user/{user_id}")
async def get_user_rank(user_id: str):
    """Get user's current rank and progression"""
    try:
        user_rank = UserRank.objects(user_id=ObjectId(user_id)).first()
        if not user_rank:
            raise HTTPException(status_code=404, detail="User rank not found")
        
        # Get next rank details
        next_rank = Rank.objects(rank_number=user_rank.next_rank_number).first()
        
        return success_response(
            data={
                "user_id": user_id,
                "current_rank": {
                    "rank_number": user_rank.current_rank_number,
                    "rank_name": user_rank.current_rank_name,
                    "rank_achieved_at": user_rank.rank_achieved_at
                },
                "next_rank": {
                    "rank_number": user_rank.next_rank_number,
                    "rank_name": user_rank.next_rank_name,
                    "progress_percentage": user_rank.progress_percentage
                },
                "requirements_met": {
                    "binary_slots_activated": user_rank.binary_slots_activated,
                    "matrix_slots_activated": user_rank.matrix_slots_activated,
                    "global_slots_activated": user_rank.global_slots_activated,
                    "total_slots_activated": user_rank.total_slots_activated,
                    "total_team_size": user_rank.total_team_size,
                    "direct_partners_count": user_rank.direct_partners_count,
                    "total_earnings": user_rank.total_earnings
                },
                "special_qualifications": {
                    "royal_captain_eligible": user_rank.royal_captain_eligible,
                    "president_reward_eligible": user_rank.president_reward_eligible,
                    "top_leader_gift_eligible": user_rank.top_leader_gift_eligible,
                    "leadership_stipend_eligible": user_rank.leadership_stipend_eligible
                },
                "rank_history": user_rank.rank_history,
                "last_updated": user_rank.last_updated
            },
            message="User rank retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/update")
async def update_user_rank(request: RankUpdateRequest, background_tasks: BackgroundTasks):
    """Update user's rank based on current achievements"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Add to background task for rank update
        background_tasks.add_task(_update_user_rank_background, request.user_id, request.force_update)
        
        return success_response(
            data={
                "user_id": request.user_id,
                "force_update": request.force_update,
                "message": "Rank update queued for processing"
            },
            message="Rank update initiated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/achievements/{user_id}")
async def get_user_rank_achievements(user_id: str, limit: int = Query(50, le=100)):
    """Get user's rank achievements"""
    try:
        achievements = RankAchievement.objects(user_id=ObjectId(user_id)).order_by('-achieved_at').limit(limit)
        
        return success_response(
            data={
                "achievements": [
                    {
                        "id": str(achievement.id),
                        "rank_number": achievement.rank_number,
                        "rank_name": achievement.rank_name,
                        "achieved_at": achievement.achieved_at,
                        "achievement_type": achievement.achievement_type,
                        "requirements_at_achievement": {
                            "binary_slots": achievement.binary_slots_at_achievement,
                            "matrix_slots": achievement.matrix_slots_at_achievement,
                            "global_slots": achievement.global_slots_at_achievement,
                            "team_size": achievement.team_size_at_achievement,
                            "earnings": achievement.earnings_at_achievement
                        },
                        "benefits_activated": achievement.benefits_activated,
                        "is_active": achievement.is_active
                    } for achievement in achievements
                ]
            },
            message="Rank achievements retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/bonuses/{user_id}")
async def get_user_rank_bonuses(user_id: str, limit: int = Query(50, le=100)):
    """Get user's rank bonuses"""
    try:
        bonuses = RankBonus.objects(user_id=ObjectId(user_id)).order_by('-created_at').limit(limit)
        
        return success_response(
            data={
                "bonuses": [
                    {
                        "id": str(bonus.id),
                        "rank_number": bonus.rank_number,
                        "rank_name": bonus.rank_name,
                        "bonus_type": bonus.bonus_type,
                        "bonus_amount": bonus.bonus_amount,
                        "currency": bonus.currency,
                        "base_amount": bonus.base_amount,
                        "bonus_percentage": bonus.bonus_percentage,
                        "multiplier": bonus.multiplier,
                        "payment_status": bonus.payment_status,
                        "payment_method": bonus.payment_method,
                        "tx_hash": bonus.tx_hash,
                        "paid_at": bonus.paid_at,
                        "created_at": bonus.created_at
                    } for bonus in bonuses
                ]
            },
            message="Rank bonuses retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/bonus")
async def create_rank_bonus(request: RankBonusRequest):
    """Create a rank bonus for user"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Validate rank exists
        rank = Rank.objects(rank_number=request.rank_number).first()
        if not rank:
            raise HTTPException(status_code=404, detail="Rank not found")
        
        # Create rank bonus
        bonus = RankBonus(
            user_id=ObjectId(request.user_id),
            rank_number=request.rank_number,
            rank_name=rank.rank_name,
            bonus_type=request.bonus_type,
            bonus_amount=request.amount,
            currency=request.currency,
            base_amount=request.amount,
            payment_status='pending'
        )
        bonus.save()
        
        return success_response(
            data={
                "bonus_id": str(bonus.id),
                "user_id": request.user_id,
                "rank_number": request.rank_number,
                "rank_name": rank.rank_name,
                "bonus_type": request.bonus_type,
                "bonus_amount": request.amount,
                "currency": request.currency,
                "payment_status": "pending",
                "message": "Rank bonus created successfully"
            },
            message="Rank bonus created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/leaderboard")
async def get_rank_leaderboard(period: str = Query("all_time", regex="^(daily|weekly|monthly|all_time)$")):
    """Get rank leaderboard"""
    try:
        leaderboard = RankLeaderboard.objects(period=period, is_active=True).order_by('-last_updated').first()
        
        if not leaderboard:
            return success_response(
                data={
                    "period": period,
                    "leaderboard_data": [],
                    "total_participants": 0,
                    "message": "No leaderboard data available for this period"
                },
                message="Leaderboard retrieved"
            )
        
        return success_response(
            data={
                "period": leaderboard.period,
                "period_start": leaderboard.period_start,
                "period_end": leaderboard.period_end,
                "leaderboard_data": leaderboard.leaderboard_data,
                "total_participants": leaderboard.total_participants,
                "top_rank_achieved": leaderboard.top_rank_achieved,
                "average_rank": leaderboard.average_rank,
                "last_updated": leaderboard.last_updated
            },
            message="Leaderboard retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/milestones/{user_id}")
async def get_user_milestones(user_id: str):
    """Get user's rank milestones"""
    try:
        milestones = RankMilestone.objects(user_id=ObjectId(user_id)).order_by('-achieved_at').all()
        
        return success_response(
            data={
                "milestones": [
                    {
                        "id": str(milestone.id),
                        "milestone_type": milestone.milestone_type,
                        "milestone_name": milestone.milestone_name,
                        "milestone_description": milestone.milestone_description,
                        "achieved_at": milestone.achieved_at,
                        "requirements_met": milestone.requirements_met,
                        "reward_type": milestone.reward_type,
                        "reward_value": milestone.reward_value,
                        "reward_description": milestone.reward_description,
                        "is_claimed": milestone.is_claimed,
                        "claimed_at": milestone.claimed_at
                    } for milestone in milestones
                ]
            },
            message="Rank milestones retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/milestone")
async def create_milestone(request: RankMilestoneRequest):
    """Create a rank milestone for user"""
    try:
        # Validate user exists
        user = User.objects(id=ObjectId(request.user_id)).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Create milestone
        milestone = RankMilestone(
            user_id=ObjectId(request.user_id),
            milestone_type=request.milestone_type,
            milestone_name=f"Milestone: {request.milestone_type}",
            milestone_description=f"User achieved {request.milestone_type}",
            reward_value=request.reward_value,
            reward_type="bonus"
        )
        milestone.save()
        
        return success_response(
            data={
                "milestone_id": str(milestone.id),
                "user_id": request.user_id,
                "milestone_type": request.milestone_type,
                "milestone_name": milestone.milestone_name,
                "reward_value": request.reward_value,
                "message": "Milestone created successfully"
            },
            message="Rank milestone created"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/settings")
async def get_rank_settings():
    """Get rank system settings"""
    try:
        settings = RankSettings.objects(is_active=True).first()
        if not settings:
            # Create default settings if none exist
            settings = RankSettings()
            settings.save()
        
        return success_response(
            data={
                "rank_system_enabled": settings.rank_system_enabled,
                "auto_rank_progression": settings.auto_rank_progression,
                "manual_rank_verification": settings.manual_rank_verification,
                "min_slots_for_rank_2": settings.min_slots_for_rank_2,
                "min_slots_for_rank_3": settings.min_slots_for_rank_3,
                "rank_progression_multiplier": settings.rank_progression_multiplier,
                "rank_bonus_enabled": settings.rank_bonus_enabled,
                "daily_rank_income_enabled": settings.daily_rank_income_enabled,
                "commission_bonus_percentage": settings.commission_bonus_percentage,
                "royal_captain_min_rank": settings.royal_captain_min_rank,
                "president_reward_min_rank": settings.president_reward_min_rank,
                "top_leader_gift_min_rank": settings.top_leader_gift_min_rank,
                "last_updated": settings.last_updated
            },
            message="Rank settings retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.post("/settings")
async def update_rank_settings(request: RankSettingsRequest):
    """Update rank system settings"""
    try:
        settings = RankSettings.objects(is_active=True).first()
        if not settings:
            settings = RankSettings()
        
        settings.rank_system_enabled = request.rank_system_enabled
        settings.auto_rank_progression = request.auto_rank_progression
        settings.manual_rank_verification = request.manual_rank_verification
        settings.rank_bonus_enabled = request.rank_bonus_enabled
        settings.daily_rank_income_enabled = request.daily_rank_income_enabled
        settings.commission_bonus_percentage = request.commission_bonus_percentage
        settings.last_updated = datetime.utcnow()
        settings.save()
        
        return success_response(
            data={
                "settings_id": str(settings.id),
                "rank_system_enabled": settings.rank_system_enabled,
                "auto_rank_progression": settings.auto_rank_progression,
                "manual_rank_verification": settings.manual_rank_verification,
                "rank_bonus_enabled": settings.rank_bonus_enabled,
                "daily_rank_income_enabled": settings.daily_rank_income_enabled,
                "commission_bonus_percentage": settings.commission_bonus_percentage,
                "last_updated": settings.last_updated,
                "message": "Settings updated successfully"
            },
            message="Rank settings updated"
        )
        
    except Exception as e:
        return error_response(str(e))

@router.get("/progress/{user_id}")
async def get_rank_progress(user_id: str):
    """Get detailed rank progress for user"""
    try:
        user_rank = UserRank.objects(user_id=ObjectId(user_id)).first()
        if not user_rank:
            raise HTTPException(status_code=404, detail="User rank not found")
        
        # Get next rank requirements
        next_rank = Rank.objects(rank_number=user_rank.next_rank_number).first()
        
        progress_data = {
            "current_rank": {
                "rank_number": user_rank.current_rank_number,
                "rank_name": user_rank.current_rank_name
            },
            "next_rank": {
                "rank_number": user_rank.next_rank_number,
                "rank_name": user_rank.next_rank_name,
                "requirements": [
                    {
                        "program": req.program,
                        "min_slots_activated": req.min_slots_activated,
                        "min_slot_level": req.min_slot_level,
                        "min_team_size": req.min_team_size,
                        "min_direct_partners": req.min_direct_partners,
                        "min_earnings": req.min_earnings,
                        "special_conditions": req.special_conditions
                    } for req in next_rank.requirements
                ] if next_rank else []
            },
            "current_progress": {
                "binary_slots_activated": user_rank.binary_slots_activated,
                "matrix_slots_activated": user_rank.matrix_slots_activated,
                "global_slots_activated": user_rank.global_slots_activated,
                "total_slots_activated": user_rank.total_slots_activated,
                "total_team_size": user_rank.total_team_size,
                "direct_partners_count": user_rank.direct_partners_count,
                "total_earnings": user_rank.total_earnings
            },
            "progress_percentage": user_rank.progress_percentage
        }
        
        return success_response(
            data=progress_data,
            message="Rank progress retrieved successfully"
        )
        
    except Exception as e:
        return error_response(str(e))

# Helper functions
async def _update_user_rank_background(user_id: str, force_update: bool):
    """Background task to update user rank"""
    # Implementation for background rank update
    pass
