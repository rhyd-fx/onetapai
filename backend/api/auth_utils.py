import os
import time
import json
import hmac
import hashlib
import base64

# Simple, highly secure, zero-dependency password hashing and JWT utility.
# Avoids any passlib/bcrypt binary build errors under React 19 / Python 3.12 environments.

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "onetapai-esports-radial-secret-key-1092")

def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a unique salt."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    salt_b64 = base64.b64encode(salt).decode('utf-8')
    key_b64 = base64.b64encode(key).decode('utf-8')
    return f"pbkdf2_sha256$100000${salt_b64}${key_b64}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a PBKDF2-HMAC-SHA256 hash."""
    try:
        parts = hashed.split('$')
        if len(parts) != 4:
            return False
        algorithm, iterations, salt_b64, key_b64 = parts
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        key = base64.b64decode(key_b64)
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(iterations))
        return hmac.compare_digest(new_key, key)
    except Exception:
        return False

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')

def base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)

def generate_jwt(payload: dict, expires_in_seconds: int = 86400) -> str:
    """Generate a signed JWT token (HS256) valid for a specific duration."""
    header = {"alg": "HS256", "typ": "JWT"}
    
    # Set expiration time
    token_payload = payload.copy()
    token_payload["exp"] = int(time.time() + expires_in_seconds)
    
    header_json = json.dumps(header, separators=(',', ':')).encode('utf-8')
    payload_json = json.dumps(token_payload, separators=(',', ':')).encode('utf-8')
    
    unsigned_token = f"{base64url_encode(header_json)}.{base64url_encode(payload_json)}"
    signature = hmac.new(SECRET_KEY.encode('utf-8'), unsigned_token.encode('utf-8'), hashlib.sha256).digest()
    
    return f"{unsigned_token}.{base64url_encode(signature)}"

def verify_jwt(token: str) -> dict | None:
    """Verify and decode a JWT token (HS256). Returns payload or None if invalid/expired."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        unsigned_token = f"{parts[0]}.{parts[1]}"
        signature = base64url_decode(parts[2])
        expected_signature = hmac.new(SECRET_KEY.encode('utf-8'), unsigned_token.encode('utf-8'), hashlib.sha256).digest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
            
        payload = json.loads(base64url_decode(parts[1]).decode('utf-8'))
        
        # Verify expiration
        if payload.get("exp", 0) < time.time():
            return None
            
        return payload
    except Exception:
        return None
