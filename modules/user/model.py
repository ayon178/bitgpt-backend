from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict
from mongoengine import Document, StringField, BooleanField, IntField, DateTimeField, DictField, ListField, PointField
from enum import Enum
from bson.objectid import ObjectId

# ✅ Base model for dynamic types
class BaseTypeResponse(BaseModel):
    id: str
    name: str


class UserType(str, Enum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"



class User(BaseModel):
    username: str
    name: Optional[str] = None
    hashed_password: Optional[str] = None
    role: UserType

    def to_orm(self):
        """
        Convert the Pydantic model to a MongoEngine Document, excluding None values.
        """
        data = self.model_dump(exclude_none=True)

        return UserDocument(**data)
    

class NewUser(BaseModel):
    username: str
    role: UserType

class NewUserByAdmin(BaseModel):
    username: str
    role: UserType
    name: str

class UserResponse(BaseModel):
    id: str
    username: str
    role: UserType



class UserDocument(Document):
    username = StringField(required=True, unique=True)
    name = StringField(required=False)
    hashed_password = StringField(required=False)
    role = StringField(required=True)
    meta = {
        'collection': 'users'
    }

    def to_response_model(self):
        data = self.to_mongo().to_dict()
        data["id"] = str(self.id)
        return UserResponse(**data)
    

class OtpVerifyRequest(BaseModel):
    username: str  # phone number
    otp: str


class UserUpdateRequest(BaseModel):
    """
    Model for updating user details.
    Username is NOT changeable.
    All other fields are optional.
    """

    name: Optional[str] = None
    role: Optional[UserType] = None