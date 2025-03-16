from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# import secrets
import httpx
import os


from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    authenticate_user,
    create_token,
    get_current_user,
    verify_token,
)
from app.database.db import get_db
from app.models.models import User
from app.schemas.schemas import OAuthUser

load_dotenv()
auth_router = APIRouter()

IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "openid profile email"
FRONTEND_URL = os.getenv("FRONTEND_URL")


@asynccontextmanager
async def get_http_client():
    async with httpx.AsyncClient(timeout=10.0) as client:
        yield client


@auth_router.get("/google")
async def auth_google():

    #  redirect to google auth
    try:
        auth_url = (
            f"{AUTHORIZATION_URL}?response_type=code"
            f"&client_id={CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&scope={SCOPE}"
            # f"&state={state}"
        )
        return RedirectResponse(url=auth_url)

    except Exception as e:
        print(f"--> Error{e} while redirecting")
        raise HTTPException(
            status_code=status.HTTP_302_FOUND, detail="Auth Url or user found"
        )


# Callback route to handle the response from Google
@auth_router.get("/auth/google-callback")
async def callback(code: str, db: Session = Depends(get_db)):
    try:
        # Use connection pooling with async context manager
        async with get_http_client() as client:
            # Exchange the authorization code for an access token
            token_response = await client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "redirect_uri": REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
                timeout=15.0,  # Extended timeout for OAuth provider
            )

            if token_response.status_code != 200:
                print(
                    f"Token response error: {token_response.status_code}, {token_response.text}"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code",
                )

            tokens = token_response.json()
            access_token = tokens["access_token"]

            # Get user info with the access token
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0,
            )

            if userinfo_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch user info",
                )

            userinfo = userinfo_response.json()

        # Create OAuth user object
        user = OAuthUser(
            email=userinfo["email"],
            name=userinfo["name"],
            image=userinfo["picture"],
            google_id=userinfo["sub"],
        )

        # Authenticate user and get tokens
        res = await authenticate_user(user, db)

        # Create response with cookies
        response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")

        # Set cookie parameters based on environment
        response.set_cookie(
            key="access_token",
            value=res["access_token"],
            httponly=True,
            max_age=60 * 60 * 24,  # 24 hours (corrected from 60*60*60)
            secure=IS_PRODUCTION,
            samesite="none" if IS_PRODUCTION else "lax",
            domain=".ytnotes.co" if IS_PRODUCTION else None,
        )

        response.set_cookie(
            key="refresh_token",
            value=res["refresh_token"],
            httponly=True,
            max_age=7 * 24 * 60 * 60,  # 7 days
            secure=IS_PRODUCTION,
            samesite="none" if IS_PRODUCTION else "lax",
            domain=".ytnotes.co" if IS_PRODUCTION else None,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        print(f"Unexpected error in Google callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication error",
        )


@auth_router.get("/me")
async def get_me(req: Request):
    access_token = req.cookies.get("access_token")
    # print("--- Access Token ---")
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        user_detail = verify_token(access_token)
        return user_detail
    except Exception as e:
        print(f"Token verification error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )


@auth_router.get("/refresh")
async def refresh_token(req: Request, db: Session = Depends(get_db)):
    refresh_token = req.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token"
        )

    try:
        # Verify refresh token
        user_data = verify_token(refresh_token)

        # Verify user exists in database
        user = db.query(User).filter(User.email == user_data["email"]).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        # Generate new tokens
        new_access_token = create_token(
            user_data, expires_delta=ACCESS_TOKEN_EXPIRE_MINUTES
        )
        new_refresh_token = create_token(
            user_data, expires_delta=REFRESH_TOKEN_EXPIRE_DAYS
        )

        response = JSONResponse(content={"message": "Tokens refreshed"})

        # Set cookie parameters based on environment
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            max_age=60 * 60 * 24,  # 24 hours (corrected from 60*60*60)
            secure=IS_PRODUCTION,
            samesite="none" if IS_PRODUCTION else "lax",
            domain=".ytnotes.co" if IS_PRODUCTION else None,
        )

        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,  # 7 days
            secure=IS_PRODUCTION,
            samesite="none" if IS_PRODUCTION else "lax",
            domain=".ytnotes.co" if IS_PRODUCTION else None,
        )

        return response

    except Exception as e:
        print(f"Refresh token error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@auth_router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    response = JSONResponse(content={"message": "Logged out Successfully"})

    # Cookie parameters based on environment
    response.delete_cookie(
        "access_token",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax",
        domain=".ytnotes.co" if IS_PRODUCTION else None,
    )

    response.delete_cookie(
        "refresh_token",
        httponly=True,
        secure=IS_PRODUCTION,
        samesite="none" if IS_PRODUCTION else "lax",
        domain=".ytnotes.co" if IS_PRODUCTION else None,
    )

    return response
