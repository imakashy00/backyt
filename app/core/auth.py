from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import secrets
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

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "openid profile email"
FRONTEND_URL = os.getenv("FRONTEND_URL")


@auth_router.get("/google")
async def auth_google():
    state = secrets.token_urlsafe(32)
    print("hi")
    #  redirect to google auth
    try:
        auth_url = (
            f"{AUTHORIZATION_URL}?response_type=code"
            f"&client_id={CLIENT_ID}"
            f"&redirect_uri={REDIRECT_URI}"
            f"&scope={SCOPE}"
            f"&state={state}"
        )
        print(auth_url)
        response = RedirectResponse(url=auth_url)
        response.set_cookie("oauth_state", state, httponly=True, secure=False)
        return response

    except Exception as e:
        print(f'--> Error{e} while redirecting')
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT, detail=str(e)
        )


# Callback route to handle the response from Google
@auth_router.get("/auth/google-callback")
async def callback(
    code: str, state: str, request: Request, db: Session = Depends(get_db)
):
    # Verify state matches what we sent
    stored_state = request.cookies.get("oauth_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    print("calling auth")
    # Exchange the authorization code for an access token
    async with httpx.AsyncClient() as client:
        response = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
    print("--> Response=>")
    # Check if token response is successful
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens["access_token"]
        # You can use the access token to fetch user info from Google's API
        # Example: https://www.googleapis.com/oauth2/v3/userinfo
        async with httpx.AsyncClient() as client:
            userinfo_response = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if userinfo_response.status_code == 200:
            userinfo_response = userinfo_response.json()
            user = OAuthUser(
                email=userinfo_response["email"],
                name=userinfo_response["name"],
                image=userinfo_response["picture"],
                google_id=userinfo_response["sub"],
            )
            print("--> Authenticate user")
            res = await authenticate_user(user, db)
            print("--> Authentication Done")
            response = RedirectResponse(url=f"{FRONTEND_URL}/dashboard")
            response.set_cookie(
                key="access_token",
                value=res["access_token"],
                httponly=True,
                max_age=60 * 60,
                samesite="lax",  # type: ignore
                secure=False,
                path="/",
            )
            response.set_cookie(
                key="refresh_token",
                value=res["refresh_token"],
                httponly=True,
                max_age=60 * 60 * 24 * 30,  # 30 days
                samesite="lax",  # type: ignore
                secure=False,
                path="/",
            )

            return response

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user info",
            )


@auth_router.get("/me")
async def get_me(req: Request):
    access_token = req.cookies.get("access_token")
    print("--- Access Token ---")
    print(access_token)
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    user_detail = verify_token(access_token)
    return user_detail


@auth_router.get("/refresh")
async def refresh_token(req: Request, db: Session = Depends(get_db)):
    print("--- Refresh Token ---")
    refresh_token = req.cookies.get("refresh_token")
    print(refresh_token)
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token"
        )

    try:
        # Verify refresh token
        user_data = verify_token(refresh_token)
        print(user_data)
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

        # Set both tokens
        response.set_cookie(
            key="access_token",
            value=new_access_token,
            httponly=True,
            max_age=60 * 60,
            secure=True,
            samesite="lax",
        )
        response.set_cookie(
            key="refresh_token",
            value=new_refresh_token,
            httponly=True,
            max_age=7 * 24 * 60 * 60,
            secure=True,
            samesite="lax",
        )
        return response

    except Exception as e:
        print(f"Error{e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid refresh token"
        )


@auth_router.post("/logout")
async def logout(user: User = Depends(get_current_user)):
    response = JSONResponse(content={"message": "Logged out Successfully"})
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response
