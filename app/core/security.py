from datetime import datetime, timezone, timedelta
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.db import get_db
import os

from app.models.models import User
from app.schemas.schemas import OAuthUser

SECRET_KEY = os.getenv("AUTH_SECRET")
if not SECRET_KEY:
    raise ValueError("AUTH_SECRET environment variable is not set")
ALGORITHM = os.getenv("ALGORITHM")
if not ALGORITHM:
    raise ValueError("ALGORITHM environment variable is not set")
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 7*24*60 # 30 days
if not SECRET_KEY:
    raise ValueError("AUTH_SECRET environment variable is not set")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# Check if user is present or not in
async def authenticate_user(req: OAuthUser, db: Session):
    try:
        user_email = req.email
        print(f'--> Email = {user_email}')
        existing_user = db.query(User).filter(User.email == user_email).first()
        print(f'-->Existing User = {existing_user}')
        if not existing_user:
            new_user = User(
                name=req.name, email=req.email, image=req.image, google_id=req.google_id
            )
            print(f'--> New User = {new_user}')
            db.add(new_user)
            db.flush()
            user = {
                "name": new_user.name,
                "email": new_user.email,
                "image": new_user.image,
                "google_id": new_user.google_id,
            }
        else:
            user = {
                "name": existing_user.name,
                "email": existing_user.email,
                "image": existing_user.image,
                "google_id": existing_user.google_id,
            }
        print(f'--> Going to assingn tokens to user:{user}')
        # create tokens for the user
        access_token = create_token(user, expires_delta=ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token = create_token(user, expires_delta=REFRESH_TOKEN_EXPIRE_DAYS)
        db.commit()
        print(f'-->Access token created= acess_token:{access_token}, refresh_token:{refresh_token}')
        return {"access_token": access_token, "refresh_token": refresh_token}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def create_token(user: dict, expires_delta: int | None = None):
    to_encode = {
        "name": user["name"],
        "email": user["email"],
        "image": user["image"],
    }
    if expires_delta:
        expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta)
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  # type: ignore
    return encoded_jwt


def verify_token(token: str | None):
    try:
        print(token)
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  # type: ignore
        print(payload)
        return {
            "name": payload["name"],
            "email": payload["email"],
            "image": payload["image"],
        }
    except ExpiredSignatureError:
        print("Signature error")
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(request: Request, db: Session = Depends(get_db)):
    try:
        # Extract token from cookies instead of header
        access_token = request.cookies.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Missing access token")

        # Verify the token
        payload = verify_token(access_token)
        email = payload.get("email")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token")

        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return user

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
