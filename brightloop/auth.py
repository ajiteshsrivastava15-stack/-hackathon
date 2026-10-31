"""Authentication, Password Security & RBAC for Brightloop Software."""

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

# In-memory active session tokens mapping token -> user_dict
SESSIONS: Dict[str, Dict[str, Any]] = {}

def validate_password_complexity(password: str) -> Tuple[bool, str]:
    """
    Validates password against Brightloop requirements:
    - More than 8 characters (>8)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one special character
    """
    if not password:
        return False, "Password cannot be empty."
    
    if len(password) <= 8:
        return False, "Password must be more than 8 characters long."
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
        
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
        
    if not re.search(r'[^A-Za-z0-9]', password):
        return False, "Password must contain at least one special character (e.g. !@#$%^&*)."
        
    return True, ""


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Hashes a password with PBKDF2-HMAC-SHA256 and a 16-byte random salt."""
    if not salt:
        salt = secrets.token_hex(16)
    
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return key.hex(), salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """Verifies a plain password against the stored hash and salt."""
    computed_hash, _ = hash_password(password, salt)
    return hmac.compare_digest(computed_hash, hashed)


def create_session(user: Dict[str, Any]) -> str:
    """Creates a secure session token and caches user details."""
    token = secrets.token_urlsafe(32)
    session_data = {
        'id': user['id'],
        'email': user['email'],
        'full_name': user.get('full_name', ''),
        'company_name': user.get('company_name', ''),
        'role': user['role'],
        'created_at': datetime.now().isoformat()
    }
    SESSIONS[token] = session_data
    return token


def get_session_user(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retrieves session user if token is valid."""
    if not token:
        return None
    return SESSIONS.get(token)


def destroy_session(token: str) -> bool:
    """Logs out by removing the session."""
    if token in SESSIONS:
        del SESSIONS[token]
        return True
    return False


def generate_reset_token() -> Tuple[str, str]:
    """Generates a secure reset token valid for 1 hour."""
    token = secrets.token_urlsafe(24)
    expiry = (datetime.now() + timedelta(hours=1)).isoformat()
    return token, expiry
