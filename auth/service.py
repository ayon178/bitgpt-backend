
from fastapi import HTTPException, status, Depends, Request
from jose import JWTError, jwt
from core.config import SECRET_KEY
from pydantic import BaseModel
from datetime import datetime, timedelta
import os
import requests
from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from typing import Annotated
from mongoengine.queryset.visitor import Q
from ..modules.user.model import User

load_dotenv()

class Token(BaseModel):
    access_token: str
    token_type: str


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/request_authentication")

class AuthenticationService(object):
    
    def __init__(self) -> None:
        self.SECRET_KEY = SECRET_KEY
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = 300
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
    
    def verify_password(self, plain_password, hashed_password):
        """
        Verifies a plain password against its hash.
        Returns (is_valid: bool, error: str | None)
        """
        if not plain_password or not hashed_password:
            return False, "Missing password or hash"

        try:
            result = self.pwd_context.verify(plain_password, hashed_password)
            print(f"Password match: {result}")
            return result, None
        except Exception as e:
            print(f"Error during password verification: {e}")
            return False, "Invalid password format"

    def get_password_hash(self,password):
        return self.pwd_context.hash(password)

    def get_user(self, username: str):
        # In this project, we use uid as the username subject
        user = User.objects(uid=username).first()
        return user
    
    def get_user_by_id(self, id: str):
        user = User.objects(id=id).first()
        return user

    def get_user_by_wallet(self, wallet_address: str):
        if not wallet_address:
            return None
        return User.objects(wallet_address=wallet_address).first()

    def get_user_by_email(self, email: str):
        if not email:
            return None
        return User.objects(email=email).first()
            
    def authenticate_user(self, username: str, password: str):
        """
        Unified authentication to support PROJECT rules:
        - Normal user: wallet-only login (no password)
        - Admin/shareholder: wallet (or uid/email) + password
        The OAuth2 form provides `username`; we treat it as wallet_address first,
        then fallback to uid lookup for compatibility.
        """
        # Try wallet first, then uid
        user = self.get_user_by_wallet(username)
        if not user:
            user = self.get_user(username=username)

        if not user:
            return None, "Wrong credentials"

        # Role: user → wallet-only login (no password required)
        if user.role == 'user':
            token = self.create_access_token({"sub": user.uid, "user_id": str(user.id)})
            return token, "SUCCESS"

        # Role: admin/shareholder → must provide and verify password
        if user.role in ["admin", "shareholder"]:
            if not password:
                return None, "Password required"
            if not user.password:
                return None, "Your account is not active please set your password"
            is_valid, error_msg = self.verify_password(password, user.password)
            if not is_valid:
                return None, error_msg or "Wrong credentials"
            token = self.create_access_token({"sub": user.uid, "user_id": str(user.id)})
            return token, "SUCCESS"

        # Fallback for other roles: require password if present
        if not user.password:
            return None, "Your account is not active please set your password"
        is_valid, error_msg = self.verify_password(password, user.password)
        if not is_valid:
            return None, error_msg or "Wrong credentials"
        return self.create_access_token({"sub": user.uid, "user_id": str(user.id)}), "SUCCESS"

    def create_access_token(self, data: dict):
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.SECRET_KEY, algorithm=self.ALGORITHM)
        token = Token(access_token=encoded_jwt, token_type="bearer")
        return token


    async def verify_authentication(
        self,
        request: Request,
        token: Annotated[str, Depends(oauth2_scheme)]
    ):
        # ✅ 1. Skip authentication for CORS preflight
        if request.method == "OPTIONS":
            return None  # Let the request pass

        try:
            payload = jwt.decode(token, self.SECRET_KEY, algorithms=[self.ALGORITHM])
            # Prefer user_id if present; fallback to uid in `sub`
            user_id_claim = payload.get("user_id")
            username: str = payload.get("sub")

            if not user_id_claim and not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No username found in token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="JWT Error",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Resolve user: by id claim when available, else by uid (sub)
        user = None
        if user_id_claim:
            user = self.get_user_by_id(user_id_claim)
        if not user and username:
            user = self.get_user(username=username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Return minimal user info
        return {
            "_id": str(user.id),
            "uid": user.uid,
            "name": user.name,
            "wallet_address": user.wallet_address,
            "role": user.role,
            "email": user.email,
            "status": user.status,
        }

    def login_with_rules(self, wallet_address: str | None, email: str | None, password: str | None):
        """
        Login rules:
        - role == 'user': wallet-only login (no password)
        - role in ['admin','shareholder']: must provide password and (email or wallet)
        Returns (result_dict, error_message)
        result_dict contains { user: {...without password...}, token: Token }
        """
        user = None
        # Prefer wallet lookup; fallback to email
        if wallet_address:
            user = self.get_user_by_wallet(wallet_address)
        if not user and email:
            user = self.get_user_by_email(email)

        if not user:
            return None, "User not found"

        if user.role == 'user':
            # Wallet must match if provided
            if wallet_address and user.wallet_address != wallet_address:
                return None, "Wallet mismatch"
            token = self.create_access_token({"sub": user.uid, "user_id": str(user.id)} )
            return {
                "user": {
                    "_id": str(user.id),
                    "uid": user.uid,
                    "name": user.name,
                    "wallet_address": user.wallet_address,
                    "role": user.role,
                    "email": user.email,
                    "status": user.status,
                },
                "token": {
                    "access_token": token.access_token,
                    "token_type": token.token_type,
                }
            }, None

        # Admin/shareholder: require password
        if user.role in ["admin", "shareholder"]:
            if not password:
                return None, "Password required"
            is_valid, error_msg = self.verify_password(password, user.password)
            if not is_valid:
                return None, error_msg or "Wrong credentials"
            token = self.create_access_token({"sub": user.uid, "user_id": str(user.id)} )
            return {
                "user": {
                    "_id": str(user.id),
                    "uid": user.uid,
                    "name": user.name,
                    "wallet_address": user.wallet_address,
                    "role": user.role,
                    "email": user.email,
                    "status": user.status,
                },
                "token": {
                    "access_token": token.access_token,
                    "token_type": token.token_type,
                }
            }, None

        return None, "Unsupported role"

authentication_service = AuthenticationService()
