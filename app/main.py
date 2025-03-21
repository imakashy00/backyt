from fastapi import FastAPI
import uvicorn
import os
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.subscription import subscription_router
from app.api.folder import folder_router
from app.core.auth import auth_router
from app.api.notes import note_router

# from app.middlewares.middleware import rate_limit_middleware

load_dotenv()
app = FastAPI()
port = os.getenv("PORT")


# app.middleware("http")(rate_limit_middleware)
app.include_router(auth_router, tags=["Auth router"])
app.include_router(note_router, tags=["Note router"])
app.include_router(folder_router, tags=["Folder router"])
app.include_router(subscription_router, tags=["subscriptions"])
# cors middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.ytnotes.co",
        "https://ytnotes.co",  # Add without www too
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,  # for production Comment this line
    )
