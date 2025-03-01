from enum import Enum
from pydantic import BaseModel, EmailStr
from typing import List, Optional

class OAuthUser(BaseModel):
    email: EmailStr
    name: str
    image: Optional[str]
    google_id:str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: int


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class File(BaseModel):
    id:str
    name:str

class Folder(BaseModel):
    id :str
    name:str
    folders:Optional[List['Folder']] = []
    files:Optional[List[File]] = []

class Node(BaseModel):
    id:str
    name:str
    folders:Optional[List[Folder]] = []

# Required for Pydantic to support recursive models
Folder.model_rebuild()
