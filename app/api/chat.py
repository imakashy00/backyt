from typing import List
from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.models.models import User

chat_router = APIRouter()

@chat_router.post('/chat')
async def chat(question:str,previous_chat:List[str],user:User = Depends(get_current_user)):
    pass