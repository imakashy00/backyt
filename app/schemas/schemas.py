from enum import Enum
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field
from typing import Any, Dict, List, Optional


class OAuthUser(BaseModel):
    email: EmailStr
    name: str
    image: Optional[str]
    google_id: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_at: int


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class File(BaseModel):
    id: str
    name: str


class Folder(BaseModel):
    id: str
    name: str
    folders: Optional[List["Folder"]] = []
    files: Optional[List[File]] = []


class Node(BaseModel):
    id: str
    name: str
    folders: Optional[List[Folder]] = []


# Required for Pydantic to support recursive models
Folder.model_rebuild()


class FolderCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: Optional[str] = None


class FolderRename(BaseModel):
    new_name: str
    folder_id: str


class FileResponse(BaseModel):
    id: str
    name: str
    video_id: Optional[str] = None

    class Config:
        from_attributes = True


class FolderResponse(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    subfolders: List["FolderResponse"] = []
    files: List[FileResponse] = []

    class Config:
        from_attributes = True


class FolderTreeResponse(BaseModel):
    folders: List[FolderResponse]


class FolderCreate(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None


class FolderCreateResponse(BaseModel):
    message: str
    folder: FolderCreate


class RenameFile(BaseModel):
    file_id: str
    new_file_name: str
    folder_id: str


class NoteDetail(BaseModel):
    folder_id: str
    youtube_url: str
    name: str


class ChatDetail(BaseModel):
    video_id: str
    question: str


class NoteResponse(BaseModel):
    id:str
    note: str
    folder_id: str
    video_id: str
    message: str


class MessageResponse(BaseModel):
    message: str

class NoteFetch(BaseModel):
    note_id:str
    folder_id:str