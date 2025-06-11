from mongoengine import *
from fastapi import  APIRouter, Depends, HTTPException, Query, BackgroundTasks
from auth.service import authentication_service
from auth.service import oauth2_scheme
from modules.user.model import *
from typing import Annotated, Optional, List, Dict
from auth.service import *
from modules.user.service import fetch_users
from utils.response import create_response
from helper.helper import generate_otp, send_otp
import logging
from auth.service import authentication_service

logger = logging.getLogger(__name__)



router = APIRouter()


@router.post("/create-by-admin", response_model=dict)
async def create_by_admin(
    user: NewUserByAdmin,
    current_user: Annotated[UserResponse, Depends(authentication_service.verify_authentication)],
):
    """
    Admin-only route to create a new user.
    Optimized to reduce DB and Pydantic overhead.
    """

    # ✅ Step 1: Early role check without exception generation
    if current_user.role != UserType.ADMIN:
        return create_response(
            status="Error",
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only admins can create users"
        )

    # ✅ Step 2: Check if user exists using `.only()` to reduce data loaded
    existing_user = UserDocument.objects(username=user.username).only("id").first()
    if existing_user:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Username already taken",
            data={"username": user.username}
        )

    try:
        # ✅ Step 3: Build user document directly from Pydantic
        db_user = UserDocument(
            username=user.username,
            role=user.role.value,
            name=user.name,
            is_verified=False,
            is_active=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
        ).save()

        # ✅ Step 4: Convert only relevant fields to dict (no heavy nested processing)
        user_data = {
            "id": str(db_user.id),
            "username": db_user.username,
            "role": db_user.role,
            "name": db_user.name
        }

        return create_response(
            status="Ok",
            status_code=201,
            message=f"User '{user.username}' created successfully by admin",
            data=user_data
        )

    except Exception as e:
        logger.error(f"❌ Error creating user by admin: {str(e)}")
        return create_response(
            status="Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create user",
            data={"error": str(e)}
        )




@router.post("/", response_model=dict)
async def create_user(user: NewUser):
    """
    Optimized: Create or update a user after sending OTP.
    """

    # ✅ Step 1: Prevent admin registration from here
    if user.role == UserType.ADMIN:
        return create_response(
            status="Error",
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only admin users can create other admin accounts"
        )

    # ✅ Step 2: Look up user fast, load minimal fields
    existing_user = UserDocument.objects(username=user.username).only(
        "id", "username", "hashed_password", "is_verified", "role"
    ).first()

    # ✅ Step 3: Exit early if user is already verified and has password
    if existing_user and existing_user.hashed_password and existing_user.is_verified:
        return create_response(
            status="Ok",
            status_code=400,
            message=f"Already registered as {existing_user.username} ({existing_user.role})",
            data={"username": user.username, "role": existing_user.role}
        )

    # ✅ Step 4: Generate OTP
    otp = generate_otp()

    # ✅ Step 5: Try sending OTP first (fail fast on real failure only)
    try:
        await send_otp(user.username, otp)
        logger.info(f"✅ OTP sent to {user.username}")
    except UnicodeEncodeError as ue:
        logger.warning(f"⚠️ Encoding warning while sending OTP: {str(ue)}")
    except Exception as e:
        logger.error(f"❌ OTP sending failed to {user.username}: {str(e)}")
        return create_response(
            status="Error",
            status_code=500,
            message="OTP delivery failed. User not created.",
            data={"error": str(e)}
        )

    # ✅ Step 6: Save or update user with OTP only
    if existing_user:
        existing_user.otp = otp

        # Fix: Ensure required field 'role' is present
        if not existing_user.role:
            existing_user.role = user.role.value

        existing_user.save()
        logger.info(f"🔁 Updated OTP for existing user: {user.username}")
    else:
        UserDocument(
            username=user.username,
            role=user.role.value,
            otp=otp,
            is_verified=False,
            is_active=False,
            is_deleted=False,
            created_at=datetime.utcnow(),
        ).save()
        logger.info(f"✅ Created new user: {user.username}")

    # ✅ Step 7: Return
    return create_response(
        status="Ok",
        status_code=200,
        message=f"OTP sent successfully to {user.username}",
        data={"username": user.username}
    )




@router.post("/verify-otp", response_model=dict)
def verify_otp(request: OtpVerifyRequest):
    """
    High-performance: Verify OTP and return JWT token.
    """

    # ✅ Step 1: Fast lookup with minimal fields
    user = UserDocument.objects(username=request.username).only("id", "username", "otp", "is_verified").first()

    if not user:
        return create_response(
            status="Error",
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )

    # ✅ Step 2: Fast OTP validation
    if not user.otp or user.otp != request.otp:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid OTP"
        )

    # ✅ Step 3: Update only relevant fields (avoid full doc re-write)
    UserDocument.objects(id=user.id).update(set__is_verified=True, set__otp=None)

    # ✅ Step 4: Generate access token
    token = authentication_service.create_access_token(data={"sub": user.username})

    # ✅ Step 5: Success response (skip create_response for speed if acceptable)
    return {
        "status": "Ok",
        "status_code": 200,
        "message": "OTP verified successfully",
        "access_token": token.access_token,
        "token_type": token.token_type
    }

# Set Password
class ChangePasswordRequest(BaseModel):
    password: str

class UpdatePasswordRequest(BaseModel):
    old_password: str
    new_password: str


@router.post("/change-password", response_model=dict)
def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[UserResponse, Depends(authentication_service.verify_authentication)]
):
    """
    High-performance: Change password for authenticated user.
    """

    # ✅ Step 1: Enforce password policy fast
    if len(request.password) < 6:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Password must be at least 6 characters"
        )

    # ✅ Step 2: Hash password quickly (avoid blocking in async)
    hashed = authentication_service.get_password_hash(request.password)

    # ✅ Step 3: Update DB using atomic Mongo query (skip loading full user)
    result = UserDocument.objects(username=current_user.username).update_one(
        set__hashed_password=hashed,
        set__is_active=True
    )

    if result == 0:
        return create_response(
            status="Error",
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found"
        )

    # ✅ Step 4: Response (skip re-fetch for perf; use current_user for return)
    return create_response(
        status="Ok",
        status_code=200,
        message="Password updated successfully",
        data=current_user.model_dump()
    )


@router.post("/update-password", response_model=dict)
async def change_password(
    request: UpdatePasswordRequest,
    current_user: Annotated[UserResponse, Depends(authentication_service.verify_authentication)],
):
    """
    Optimized: Change user password after verifying the old one.
    """

    try:
        # ✅ Step 1: Load user minimally for password check only
        user_doc = UserDocument.objects(username=current_user.username).only("hashed_password").first()
        if not user_doc:
            return create_response(
                status="Error",
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found"
            )

        # ✅ Step 2: Verify old password without extra branching
        is_valid, reason = authentication_service.verify_password(request.old_password, user_doc.hashed_password)
        if not is_valid:
            return create_response(
                status="Error",
                status_code=status.HTTP_400_BAD_REQUEST,
                message=reason or "Old password is incorrect"
            )

        # ✅ Step 3: Enforce minimum password length fast
        if len(request.new_password) < 6:
            return create_response(
                status="Error",
                status_code=status.HTTP_400_BAD_REQUEST,
                message="New password must be at least 6 characters"
            )

        # ✅ Step 4: Hash new password (sync, fast hash)
        new_hashed = authentication_service.get_password_hash(request.new_password)

        # ✅ Step 5: Atomic update without re-fetch
        update_result = UserDocument.objects(username=current_user.username).update_one(
            set__hashed_password=new_hashed
        )

        if update_result == 0:
            return create_response(
                status="Error",
                status_code=status.HTTP_404_NOT_FOUND,
                message="User not found during update"
            )

        logger.info(f"🔒 Password updated for user: {current_user.username}")

        return create_response(
            status="Ok",
            status_code=status.HTTP_200_OK,
            message="Password updated successfully"
        )

    except Exception as e:
        logger.error(f"❌ Password update failed: {str(e)}", exc_info=True)
        return create_response(
            status="Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to update password",
            data={"error": str(e)}
        )


    # First take the username and send the otp to the user
    # Then verify the otp 
    # Then update the password

@router.post("/forgot-password/request", response_model=dict)
async def forgot_password_request(request: ForgotPasswordRequest):
    """
    Optimized: Send OTP for forgot password only if user exists and OTP sent successfully.
    """

    # Step 1: Fetch user with minimal fields to reduce DB load
    user_doc = UserDocument.objects(username=request.username).only("username").first()
    if not user_doc:
        return create_response(
            status="Error",
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            data={"username": request.username}
        )

    # Step 2: Generate OTP once
    new_otp = generate_otp()

    try:
        # Step 3: Send OTP - fail fast if sending fails
        if not await send_otp(user_doc.username, new_otp):
            logger.warning(f"❌ OTP sending failed for {request.username}")
            return create_response(
                status="Error",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message="Failed to send OTP. Please try again."
            )

    except UnicodeEncodeError as uee:
        logger.error(f"Unicode error sending OTP to {request.username}: {uee}")
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid characters in phone number",
            data={"error": str(uee)}
        )
    except Exception as e:
        logger.error(f"❌ Exception sending OTP to {request.username}: {e}", exc_info=True)
        return create_response(
            status="Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error",
            data={"error": str(e)}
        )

    # Step 4: Update OTP atomically only if OTP was sent successfully
    update_count = UserDocument.objects(username=request.username).update_one(set__otp=new_otp)
    if update_count == 0:
        # This is rare but if user disappeared after fetch
        return create_response(
            status="Error",
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found during update"
        )

    logger.info(f"🔄 OTP sent and updated for user: {request.username}")

    return create_response(
        status="Ok",
        status_code=status.HTTP_200_OK,
        message="OTP sent successfully",
        data={"otp_sent": True}
    )



@router.get("/", summary="Get Users", description="Fetch users with filtering, searching, sorting, and pagination.")
async def get_users(
    search_term: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1),
    sort_by: Optional[str] = "created_at",
    sort_order: Optional[str] = "desc",
    tutor_type: Optional[List[str]] = Query(None),
    class_type: Optional[List[str]] = Query(None),
    subject_type: Optional[List[str]] = Query(None),
    versity_type: Optional[List[str]] = Query(None),
    gender: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    price_min: Optional[int] = Query(None),
    price_max: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_public: Optional[bool] = Query(None),
    latitude: Optional[float] = Query(None, description="Latitude of user's location"),
    longitude: Optional[float] = Query(None, description="Longitude of user's location"),
    max_distance_km: float = Query(5.0, description="Max search radius in kilometers"),
):
    try:
        filters = {
            "tutor_type": tutor_type,
            "class_type": class_type,
            "subject_type": subject_type,
            "versity_type": versity_type,
            "gender": gender,
            "role": role,
            "is_active": is_active,
            "is_public": is_public,
            "price_min": price_min,
            "price_max": price_max,
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "max_distance_km": max_distance_km
            } if latitude is not None and longitude is not None else None
        }

        result = fetch_users(
            search_term=search_term,
            page=page,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters
        )

        return create_response(
            status="Ok",
            status_code=200,
            message="Users fetched successfully.",
            data=result["data"],
            meta=result["meta"]
        )

    except ValueError as ve:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(ve),
            data=None
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_users endpoint: {e}", exc_info=True)
        return create_response(
            status="Error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Internal server error while fetching users.",
            data=None
        )
    

@router.put("/{user_id}")
def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_user: Annotated[UserResponse, Depends(authentication_service.verify_authentication)],
):
    """
    Update user details.
    - Only user or admin can update
    - Fields are optional; only provided fields will be updated
    """

    # Authorization: Only self or admin
    if str(current_user.id) != user_id and current_user.role != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    update_data = request.model_dump(exclude_unset=True)
    logger.info(f"Update Data (before location transform): {update_data}")

    # Handle location separately - convert {latitude, longitude} to GeoJSON Point
    loc = update_data.get("location")
   
    if loc:
        # Expect loc = {"latitude": ..., "longitude": ...}
        if "latitude" in loc and "longitude" in loc:
            update_data["location"] = {
                "type": "Point",
                "coordinates": [loc["longitude"], loc["latitude"]],  # GeoJSON expects [lng, lat]
            }
        else:
            # Invalid location format, reject request
            return create_response(
                status="Error",
                status_code=400,
                message="Invalid location format: must include latitude and longitude",
                data=None,
            )

    if not update_data:
        return create_response(
            status="Error",
            status_code=400,
            message="No update fields provided",
            data=None,
        )

    # Build update dict for MongoEngine update_one()
    update_dict = {"set__" + k: v for k, v in update_data.items()}

    updated = UserDocument.objects(id=user_id).update_one(upsert=False, **update_dict)

    if updated == 0:
        # No document updated → user not found
        return create_response(
            status="Error",
            status_code=404,
            message="User not found",
            data=None,
        )

    return create_response(
        status="Ok",
        status_code=200,
        message="User updated successfully",
        data={},
    )



# Get User by id
@router.get("/{user_id}")
def get_user_by_id(user_id: str):
    try:
        user_doc = UserDocument.objects(id=ObjectId(user_id)).first()
    except Exception:
        return create_response(
            status="Error",
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Invalid user ID",
            data=None,
        )

    if not user_doc:
        return create_response(
            status="Error",
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            data=None,
        )

    # Use the to_response_model() to get a fully populated user dictionary
    user_data = user_doc.to_response_model().dict()

    return create_response(
        status="Ok",
        status_code=200,
        message="User fetched successfully",
        data=user_data
    )


@router.delete("/{username}", response_model=dict)
def delete_user_by_username(
    username: str,
    current_user: Annotated[UserResponse, Depends(authentication_service.verify_authentication)],
):
    if current_user.role != UserType.ADMIN:
        return create_response(
            status="Error",
            status_code=status.HTTP_403_FORBIDDEN,
            message="You are not allowed to delete users",
        )

    delete_count = UserDocument.objects(username=username).delete()

    if delete_count == 0:
        return create_response(
            status="Error",
            status_code=status.HTTP_404_NOT_FOUND,
            message="User not found",
            data={"username": username},
        )

    logger.info(f"🗑️ User {username} deleted successfully")

    return create_response(
        status="Ok",
        status_code=200,
        message="User deleted successfully",
        data={"deleted_username": username},
    )
