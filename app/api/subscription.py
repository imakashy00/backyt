from fastapi import APIRouter, Depends, Request, HTTPException, status
import httpx
from sqlalchemy.orm import Session
from app.database.db import get_db
from app.models.models import User, Subscription
from app.core.security import get_current_user, get_subscribed_user
from typing import Dict, Any
import hmac
import hashlib
import json
from datetime import datetime, timezone
import os

subscription_router = APIRouter()

PADDLE_API_KEY = os.getenv("PADDLE_API_KEY")
PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET")


# verify webhook signature for security
def verify_webhook(request_data: Dict[Any, Any], signature: str) -> bool:
    """Verify the Paddle webhook signature"""
    # For test environment, you might want to skip verification during development
    if os.getenv("ENVIRONMENT", "development") == "development":
        return True

    if not PADDLE_WEBHOOK_SECRET:
        print("Warning: PADDLE_WEBHOOK_SECRET is not set")
        return False
    # verify using signature system
    serialized_data = json.dumps(request_data, separators=(",", ":"))
    signature_verified = False

    try:
        computed_hash = hmac.new(
            PADDLE_WEBHOOK_SECRET.encode("utf-8"),
            serialized_data.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        signature_verified = hmac.compare_digest(computed_hash, signature)
    except Exception as e:
        print(f"Error verifying signature:{e}")
        return False
    return signature_verified


@subscription_router.post("/webhook/paddle")
async def paddle_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Paddle webhook events for subscription lifecycle"""
    body = await request.json()
    print(body)
    signature = request.headers.get("Paddle-Signature")
    print(f"Signature==>{signature}")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing webhook signature",
        )
    # verify webhook signature to ensure its's from Paddle
    if not verify_webhook(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )
    # Extract webhook data
    event_type = body.get("event_type", "")
    print(f"Event type==>{event_type}")
    data = body.get("data", {})
    try:
        if event_type == "subscription.created":
            await handle_subscription_created(data, db)
        elif event_type == "subscription.canceled":
            await handle_subscription_canceled(data, db)
        return {"status": "success"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        # Still return 200 to prevent Paddle from retrying
        return {"status": "error", "message": str(e)}


async def handle_subscription_created(data: Dict, db: Session):
    """Handle subscription.created event"""
    print("_____ Keys are ______")
    print(data.get("custom_data"))

    custom_data = data.get("custom_data")
    if not custom_data:
        raise ValueError("Custom data not provided")
    customer_email = custom_data.get("email")

    if not customer_email:
        raise ValueError("Customer email not provided")
    print(f"Customer email=?{customer_email}")
    # Find the user
    user = db.query(User).filter(User.email == customer_email).first()
    if not user:
        raise ValueError(f"User with email {customer_email} not found")

    scheduled_change = data.get("scheduled_change")
    is_cancelling = False
    if scheduled_change is not None:
        is_cancelling = scheduled_change.get("action") == "cancel"
    
    # Create new subscription record
    subscription = Subscription(
        user_id=user.id,
        paddle_subscription_id=data.get("id"),
        status=data.get("status", "active"),
        plan_id=data.get("items", [{}])[0].get("price", {}).get("id"),
        current_period_end=datetime.fromisoformat(
            data.get("current_billing_period", {}).get("ends_at").replace("Z", "+00:00")
        ),
        cancel_at_period_end=is_cancelling,
    )
    print("---Model created---")  #  4242 4242 4242 4242
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    print(f"Created subscription for user ==> {user.id}")


async def handle_subscription_canceled(data: Dict, db: Session):
    """Handle subscription.canceled event"""
    subscription_id = data.get("id")
    subscription = (
        db.query(Subscription)
        .filter(Subscription.paddle_subscription_id == subscription_id)
        .first()
    )

    if not subscription:
        raise ValueError(f"Subscription {subscription_id} not found")

    # Update subscription status
    subscription.status = "canceled"
    subscription.canceled_at = datetime.now(timezone.utc)
    db.commit()
    print(f"Canceled subscription {subscription_id}")


# Add these endpoints to your subscriptions.py file


@subscription_router.post("/subscription/cancel")
async def cancel_subscription(
    db: Session = Depends(get_db), user: User = Depends(get_subscribed_user)
):
    """Cancel the user's subscription through Paddle API"""
    # Get the user's active subscription
    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No active subscription found"
        )
    try:
        # Call Paddle API to cancel subscription
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://sandbox-api.paddle.com/subscriptions/{subscription.paddle_subscription_id}/cancel",
                headers={
                    "Authorization": f"Bearer {PADDLE_API_KEY}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to cancel subscription: {response.text}",
                )

            # Update local subscription record
            subscription.cancel_at_period_end = True
            db.commit()

            return {
                "status": "success",
                "message": "Subscription will be canceled at the end of billing period",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error canceling subscription: {str(e)}",
        )


@subscription_router.get("/status")
async def get_subscription_status(
    db: Session = Depends(get_db), user: User = Depends(get_subscribed_user)
):
    """Get the current user's subscription status"""
    subscription = (
        db.query(Subscription)
        .filter(Subscription.user_id == user.id, Subscription.status == "active")
        .order_by(Subscription.created_at.desc())
        .first()
    )

    if not subscription:
        return {
            "plan": None,
            "current_period_end": None,
        }

    # Determine plan type from plan_id
    plan_type = "yearly" if "year" in subscription.plan_id.lower() else "monthly"

    return {
        "plan": plan_type,
        "current_period_end": (
            subscription.current_period_end.isoformat()
            if subscription.current_period_end
            else None
        ),
    }


async def get_subscribed_user(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Check if user has an active subscription and return the user"""

    # Check if user has an active subscription
    subscription = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.status == "active",
            Subscription.current_period_end > datetime.now(),
        )
        .first()
    )

    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": "This feature requires an active subscription",
                "subscription_required": True,
            },
        )

    return current_user
