from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.database.db import get_db
from app.models.models import File, Folder, User


class FolderCreate(BaseModel):
    name: str
    parent_id: Optional[str] = None


class FileResponse(BaseModel):
    id: UUID
    name: str
    type: str = "file"

    class Config:
        from_attributes = True


class FolderRename(BaseModel):
    new_name: str
    folder_id: str


class FolderResponse(BaseModel):
    id: UUID
    name: str
    type: str = "folder"
    subfolders: List["FolderResponse"] = []
    files: List[FileResponse] = []

    class Config:
        from_attributes = True


folder_router = APIRouter()


@folder_router.post("/folder")
async def create_folder(
    folder: FolderCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        print(f"--->Creating folder: name={folder.name}, parent_id={folder.parent_id}")
        if folder.parent_id is not None:
            existing_folder = (
                db.query(Folder)
                .filter(
                    Folder.parent_id == folder.parent_id,
                    Folder.name == folder.name,
                    Folder.user_id == user.id,
                )
                .first()
            )
            print(f"Existing folder => {existing_folder}")
            # if folder with same name at same level already present
            if existing_folder:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": "Folder with this name already exists at this level"
                    },
                )
            else:
                # create folder at the level
                new_folder = Folder(
                    name=folder.name, parent_id=folder.parent_id, user_id=user.id
                )
                db.add(new_folder)
                print("Added Folder")
                db.commit()
                print("Commit successful")
                db.refresh(new_folder)
        else:
            # Check for root level folder with same name
            existing_folder = (
                db.query(Folder)
                .filter(
                    Folder.parent_id.is_(None),
                    Folder.name == folder.name,
                    Folder.user_id == user.id,
                )
                .first()
            )
            if existing_folder:
                return JSONResponse(
                    status_code=400,
                    content={
                        "message": "Folder with this name already exists at this level"
                    },
                )

            new_folder = Folder(name=folder.name, parent_id=None, user_id=user.id)
            db.add(new_folder)
            print("Added Folder")
            db.commit()
            print("Commit successful")
            db.refresh(new_folder)

            return JSONResponse(
                status_code=201,
                content={
                    "message": "Folder created successfully",
                    "folder": {
                        "id": str(new_folder.id),  # Convert UUID to string
                        "name": new_folder.name,
                        "parent_id": (
                            str(new_folder.parent_id) if new_folder.parent_id else None
                        ),
                    },
                },
            )
    except Exception as e:
        print(e)
        print("going to rollback------------------------")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@folder_router.get("/folder")
async def get_folders(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        # Get root folders
        root_folders = (
            db.query(Folder)
            .filter(Folder.user_id == user.id, Folder.parent_id.is_(None))
            .all()
        )

        def get_folder_structure(folder):
            # Get subfolders
            subfolders = db.query(Folder).filter(Folder.parent_id == folder.id).all()

            # Get files in this folder
            files = db.query(File).filter(File.folder_id == folder.id).all()

            return {
                "id": str(folder.id),
                "name": folder.name,
                "parent_id": str(folder.parent_id) if folder.parent_id else None,
                "subfolders": [
                    get_folder_structure(subfolder) for subfolder in subfolders
                ],
                "files": [
                    {"id": str(file.id), "video_id": file.video_id, "name": file.name,"content":file.content}
                    for file in files
                ],
            }

        folder_tree = [get_folder_structure(folder) for folder in root_folders]

        return JSONResponse(status_code=200, content={"folders": folder_tree})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@folder_router.put("/folder")
async def rename_folder(
    folder_data: FolderRename,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # check if new name is not already taken in the same level or is not same as parent folder name
    try:
        print(f"The new name of folder is {folder_data.new_name}")
        folder = (
            db.query(Folder)
            .filter(Folder.id == folder_data.folder_id, Folder.user_id == user.id)
            .first()
        )
        if not folder:
            return JSONResponse(
                status_code=404, content={"message": "FOlder not found"}
            )
        # check duplicate name at same level
        existing_folder = (
            db.query(Folder)
            .filter(
                Folder.parent_id == folder.parent_id,
                Folder.name == folder_data.new_name,
                Folder.id != folder.id,
                Folder.user_id == user.id,
            )
            .first()
        )
        if existing_folder:
            return JSONResponse(
                status_code=400,
                content={
                    "message": "Folder with this name already exist at this level"
                },
            )

        # update folder name
        folder.name = folder_data.new_name
        db.commit()
        return JSONResponse(
            status_code=200, content={"message": "Folder renamed successfully"}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@folder_router.delete("/folder/{folder_id}")
async def delete_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        existing_folder = (
            db.query(Folder)
            .filter(Folder.id == folder_id, Folder.user_id == user.id)
            .first()
        )
        if not existing_folder:
            return JSONResponse(
                status_code=404, content={"message": "Folder not found"}
            )
        # Delete all files in the folder and its subfolders
        db.delete(existing_folder)
        db.commit()

        return JSONResponse(
            status_code=200,
            content={"message": "Folder and contents deleted successfully"},
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
