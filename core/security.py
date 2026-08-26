from fastapi import Response
from passlib.context import CryptContext
from datetime import datetime , timedelta, timezone
import os
from dotenv import load_dotenv
import jwt
import uuid6

from core.exceptions import AuthFailedError

load_dotenv()

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
RESTORE_SECRET_KEY = os.getenv("RESTORE_SECRET_KEY")
HASHING_ALGO  = os.getenv("ALGORITHM")
IS_PRODUCTION = os.getenv("ENV") == "production"

#hashing logic
hashing = CryptContext(schemes=["bcrypt"])

def hash_data(data:str) -> str:
    return hashing.hash(data)

def verify_hashes(input_data, db_data) -> bool:
    return hashing.verify(input_data, db_data)

#tokens logic

def generate_jwt(
    token_payload_data:dict,
    secret_key: str
    ) -> str:
    return jwt.encode(token_payload_data, secret_key, HASHING_ALGO)


def generate_access_jwt(
    user_public_id:uuid6.UUID, 
    token_family_id: uuid6.UUID
    ) -> str:
    payload = {
    "sub": str(user_public_id),
    "sid": str(token_family_id),
    "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    return generate_jwt(payload, ACCESS_SECRET_KEY)

def generate_refresh_jwt(
                            user_public_id:uuid6.UUID,
                            token_public_id:uuid6.UUID,
                            ):
    payload = {
        "sub": str(user_public_id),
        "jti": str(token_public_id),
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=14)
    }
    return generate_jwt(payload, REFRESH_SECRET_KEY)

def generate_restore_jwt(user_public_id: uuid6.UUID) -> str:
    payload = {
        "sub": str(user_public_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10)
    }
    return generate_jwt(payload, RESTORE_SECRET_KEY)

def generate_refresh_token_data(user_public_id, useragent: str, family_id=None):
    created_at = datetime.now(timezone.utc)
    expires_at = datetime.now(timezone.utc) + timedelta(days=14)
    token_public_id = uuid6.uuid7()
    token_family_id = family_id if family_id else uuid6.uuid8()
    return {
            "token_public_id": token_public_id,
            "user_public_id": user_public_id,
            "created_at": created_at,
            "expired_at": expires_at,
            "family_id": token_family_id,
            'session_started_at': created_at,
            "user_agent": useragent,
            "is_used": False
            }

def decode_jwt(token:str, secret_key) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[HASHING_ALGO])
        return payload
    except jwt.InvalidTokenError:
        raise AuthFailedError()


def decode_access_token(token: str) -> uuid6.UUID:
    payload = decode_jwt(token, ACCESS_SECRET_KEY)
    user_public_id = payload.get("sub")
    token_exp = payload.get("exp")
    token_family_id = payload.get("sid")
    if not user_public_id or not token_family_id:
        raise AuthFailedError()
    return {
        "user_public_id": uuid6.UUID(user_public_id),
        "token_family_id": uuid6.UUID(token_family_id),
        "token_expiration": token_exp
    }

def decode_refresh_token(token: str) -> dict:
    payload = decode_jwt(token, REFRESH_SECRET_KEY)
    user_public_id = payload.get("sub")
    token_public_id = payload.get("jti")
    if not user_public_id or not token_public_id:
        raise AuthFailedError()
    return {
        "user_public_id": uuid6.UUID(user_public_id),
        "token_public_id": uuid6.UUID(token_public_id)
    }

def decode_restore_token(token:str) -> str:
    payload = decode_jwt(token, RESTORE_SECRET_KEY)
    user_public_id = payload.get("sub")
    if not user_public_id:
        raise AuthFailedError()
    return user_public_id

# Cookies set/delete for tokens

def set_cookies(
                response: Response,
                cookie_key: str,
                cookies_values: str,
                cookie_ttl: int
                ):
    response.set_cookie(
        key=cookie_key,
        value=cookies_values,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax",
        max_age=cookie_ttl
    )

def delete_cookies(
                    response: Response,
                    cookie_key: str,
                    ):
    response.delete_cookie(
        key=cookie_key,
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="lax"
        )

def set_tokens_to_cookies(
                            response: Response, 
                            access_token: str, 
                            refresh_token: str
                         ) -> None:
    set_cookies(response, 'access_token', access_token, 900)
    set_cookies(response, 'refresh_token', refresh_token, 1209600)
    
def delete_tokens_from_cookies(response: Response) -> None:
    delete_cookies(response, 'access_token')
    delete_cookies(response, 'refresh_token')
