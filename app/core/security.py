from datetime import datetime, timezone, timedelta
from uuid import uuid4
from jose import jwt
from jose.exceptions import JWTError, ExpiredSignatureError
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database.db import get_db
import os

from app.models.models import Subscription, User
from app.schemas.schemas import OAuthUser

SECRET_KEY = os.getenv("AUTH_SECRET")
if not SECRET_KEY:
    raise ValueError("AUTH_SECRET environment variable is not set")
ALGORITHM = os.getenv("ALGORITHM")
if not ALGORITHM:
    raise ValueError("ALGORITHM environment variable is not set")
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 hour
REFRESH_TOKEN_EXPIRE_DAYS = 7 * 24 * 60  # 30 days
if not SECRET_KEY:
    raise ValueError("AUTH_SECRET environment variable is not set")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_trial_subscription(user_id: str, db: Session, trial_days: int = 15):
    """Create a free trial subscription for a new user"""
    try:
        # Calculate trial end date
        trial_end_date = datetime.now() + timedelta(days=trial_days)

        # Create trial subscription record
        trial_subscription = Subscription(
            user_id=user_id,
            paddle_subscription_id=f"trial_{str(uuid4())[:8]}",  # Unique identifier
            plan_id="trial",
            status="active",
            current_period_end=trial_end_date,
            cancel_at_period_end=True,  # Will automatically expire
        )

        db.add(trial_subscription)
        return trial_subscription
    except Exception as e:
        print(f"Error creating trial subscription: {e}")
        return None


# Check if user is present or not in
async def authenticate_user(req: OAuthUser, db: Session):
    try:
        user_email = req.email
        existing_user = db.query(User).filter(User.email == user_email).first()
        is_new_user = not existing_user

        if is_new_user:
            # Create new user
            new_user = User(
                name=req.name, email=req.email, image=req.image, google_id=req.google_id
            )
            db.add(new_user)
            db.flush()  # Get ID without committing transaction
            user = {
                "name": new_user.name,
                "email": new_user.email,
                "image": new_user.image,
                "google_id": new_user.google_id,
            }

            # Create a free trial subscription for new users
            create_trial_subscription(new_user.id, db, trial_days=15)

            # Mark as subscribed since they have a trial
            is_subscribed = True
        else:
            user = {
                "name": existing_user.name,
                "email": existing_user.email,
                "image": existing_user.image,
                "google_id": existing_user.google_id,
            }

            # Check if existing user has active subscription
            subscription = (
                db.query(Subscription)
                .filter(
                    Subscription.user_id == existing_user.id,
                    Subscription.status == "active",
                    Subscription.current_period_end > datetime.now(),
                )
                .first()
            )
            is_subscribed = subscription is not None

        # Create tokens with subscription status
        access_token = create_token(
            user, expires_delta=ACCESS_TOKEN_EXPIRE_MINUTES, subscribed=is_subscribed
        )
        refresh_token = create_token(
            user, expires_delta=REFRESH_TOKEN_EXPIRE_DAYS, subscribed=is_subscribed
        )

        db.commit()
        return {"access_token": access_token, "refresh_token": refresh_token}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


def create_token(
    user: dict, expires_delta: int | None = None, subscribed: bool = False
):
    to_encode = {
        "name": user["name"],
        "email": user["email"],
        "image": user["image"],
        "subscribed": subscribed,
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
            "subscribed": payload.get("subscribed", False),
        }
    except ExpiredSignatureError:
        # print("Signature error")
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

        user.is_subscribed = payload.get("subscribed", False)

        return user

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_subscribed_user(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Check if user is subscribed and return the user if they are"""
    if not current_user.is_subscribed:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "This feature requires an active subscription",
                "subscription_required": True,
            },
        )
    return current_user
