from passlib.context import CryptContext
from datetime import datetime , timedelta, timezone
import os
from dotenv import load_dotenv
import jwt
import secrets
import uuid6

from core.exceptions import TokenError

load_dotenv()

ACCESS_SECRET_KEY = os.getenv("ACCESS_SECRET_KEY")
REFRESH_SECRET_KEY = os.getenv("REFRESH_SECRET_KEY")
HASHING_ALGO  = os.getenv("ALGORITHM")

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


def generate_access_token(user_public_id:uuid6.UUID) -> str:
    payload = {
    "sub": str(user_public_id), 
    "exp": datetime.now(timezone.utc) + timedelta(minutes=15)
    }
    return generate_jwt(payload, ACCESS_SECRET_KEY)

def generate_refresh_token(
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

def generate_refresh_token_data(user_public_id, useragent: str):
    created_at = datetime.now(timezone.utc)
    token_publi_id = uuid6.uuid7()
    return {
            "token_public_id": token_publi_id,
            "user_public_id": user_public_id,
            "created_at": created_at,
            "user_agent":useragent
            }

def decode_jwt(token:str, secret_key) -> dict:
    try:
        payload = jwt.decode(token, secret_key, algorithms=[HASHING_ALGO])
        return payload
    except jwt.InvalidTokenError:
        raise TokenError()


def decode_access_token(token: str) -> uuid6.UUID:
    payload = decode_jwt(token, ACCESS_SECRET_KEY)
    user_public_id = payload.get("sub")
    if not user_public_id:
        raise TokenError()
    return uuid6.UUID(user_public_id)

def decode_refresh_token(token: str) -> dict:
    payload = decode_jwt(token, REFRESH_SECRET_KEY)
    user_public_id = payload.get("sub")
    token_public_id = payload.get("jti")
    if not user_public_id or not token_public_id:
        raise TokenError()
    return {
        "user_public_id": uuid6.UUID(user_public_id),
        "token_public_id": uuid6.UUID(token_public_id)
    }

