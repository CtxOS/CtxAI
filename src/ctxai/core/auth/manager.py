import os
import time
import jwt
from typing import Optional, Dict
from datetime import datetime, timedelta, timezone

# Configuration
SECRET_KEY = os.getenv("A0_AUTH_SECRET", "super-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

class AuthManager:
    """
    Core Domain: Authentication & Authorization
    Standardizes JWT token issuance and validation.
    """
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def get_user_id(token: str) -> Optional[str]:
        payload = AuthManager.verify_token(token)
        return payload.get("sub") if payload else None

    @staticmethod
    def get_workspace_id(token: str) -> Optional[str]:
        payload = AuthManager.verify_token(token)
        return payload.get("workspace_id", "default") if payload else "default"
