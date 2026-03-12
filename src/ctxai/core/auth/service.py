import os
import secrets
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from ctxai.core.common.login import get_credentials_hash
from ctxai.shared import dotenv

class AuthService:
    """
    Standardized Authentication Service for Phase 8.
    Handles JWT generation, verification, and UserContext management.
    """
    
    SECRET_KEY = dotenv.get_dotenv_value("AUTH_JWT_SECRET") or os.environ.get("AUTH_JWT_SECRET")
    if not SECRET_KEY:
        # Generate a temporary secret if none provided (not recommended for production persistence)
        SECRET_KEY = secrets.token_urlsafe(32)
        
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 hours
    
    @classmethod
    def create_token(cls, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, cls.SECRET_KEY, algorithm=cls.ALGORITHM)
        return encoded_jwt

    @classmethod
    def decode_token(cls, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None

    @classmethod
    def login(cls, username: str, password_hash: str) -> Optional[str]:
        """
        Validates credentials against legacy hash or future user database.
        For now, we stick to the legacy .env credentials if defined.
        """
        expected_hash = get_credentials_hash()
        if expected_hash and password_hash == expected_hash:
            # Successful login
            return cls.create_token({
                "sub": username,
                "user_id": username, # For now username IS user_id
                "workspace_id": "default",
                "roles": ["admin"]
            })
        
        # If no credentials set, allow login if authenticated check is disabled
        from ctxai.core.common.login import is_login_required
        if not is_login_required():
            return cls.create_token({
                "sub": "anonymous",
                "user_id": "anonymous",
                "workspace_id": "default",
                "roles": ["guest"]
            })
            
        return None
