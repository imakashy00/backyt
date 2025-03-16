from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from app.core.security import get_subscribed_user
from app.database.db import get_db
from app.models.models import File, Folder, User
from app.schemas.schemas import (
    FolderCreateRequest,
    FolderCreateResponse,
    FolderRename,
    FolderTreeResponse,
)


folder_router = APIRouter()


@folder_router.post(
    "/folder",
    response_model=FolderCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Folder already exists"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"},
    },
)
async def create_folder(
    folder_create: FolderCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_subscribed_user),
):
    try:
        print(
            f"--->Creating folder: name={folder_create.name}, parent_id={folder_create.parent_id}"
        )
        # Check if folder is 'root level' folder or not
        if folder_create.parent_id is not None:
            # Find existing folder in Folder table in database
            existing_folder = (
                db.query(Folder)
                .filter(
                    Folder.parent_id == folder_create.parent_id,
                    Folder.name == folder_create.name,
                    Folder.user_id == user.id,
                )
                .first()
            )
            print(f"Existing folder => {existing_folder}")
            # if folder with same name at same level already present
            if existing_folder:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Folder with this name exists at this level",
                )
            else:
                # create folder at the level
                new_folder = Folder(
                    name=folder_create.name,
                    parent_id=folder_create.parent_id,
                    user_id=user.id,
                )
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
                            "id": str(new_folder.id),  # Converted UUID to string
                            "name": new_folder.name,
                            "parent_id": (
                                str(new_folder.parent_id)
                                if new_folder.parent_id
                                else None
                            ),
                        },
                    },
                )
        else:
            # Here root folder creation will occur
            # Check for root level folder with same name
            existing_folder = (
                db.query(Folder)
                .filter(
                    Folder.parent_id.is_(None),
                    Folder.name == folder_create.name,
                    Folder.user_id == user.id,
                )
                .first()
            )
            if existing_folder:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Folder with this name exists at root level",
                )

            new_folder = Folder(
                name=folder_create.name, parent_id=None, user_id=user.id
            )
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
                        "id": str(new_folder.id),  # Converted UUID to string
                        "name": new_folder.name,
                        "parent_id": (
                            str(new_folder.parent_id) if new_folder.parent_id else None
                        ),
                    },
                },
            )
    except Exception as e:
        print(f"Error{e} while creating folder")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@folder_router.get("/folder", response_model=FolderTreeResponse)
async def get_folders(
    db: Session = Depends(get_db), user: User = Depends(get_subscribed_user)
):
    try:
        # Using a recursive CTE to get all folders with hierarchy information in one query
        cte_query = """WITH RECURSIVE folder_tree AS (
        --- Base Case: select root folders
        SELECT id, name, parent_id,0 as level
        FROM folders
        WHERE user_id =:user_id AND parent_id is NULL

        UNION ALL

        -- Recursive case: select children folders
        SELECT f.id,f.name,f.parent_id,ft.level+1
        FROM folders f
        JOIN folder_tree ft ON f.parent_id = ft.id
        WHERE f.user_id = :user_id
        )
        SELECT id,name,parent_id,level FROM folder_tree ORDER BY level, name
        """
        # Execute the query
        folder_result = db.execute(
            text(cte_query), {"user_id": str(user.id)}
        ).fetchall()
        # create folder dict
        folders_dict = {}
        for row in folder_result:
            folders_dict[str(row.id)] = {
                "id": str(row.id),
                "name": row.name,
                "parent_id": str(row.parent_id) if row.parent_id else None,
                "subfolders": [],
                "files": [],
            }

        # Fetch all relevant files in a single query (without content for performance)
        file_results = (
            db.query(File.id, File.name, File.folder_id, File.video_id)
            .filter(
                File.user_id == user.id,
                File.folder_id.in_([row.id for row in folder_result]),
            )
            .all()
        )
        print(file_results)
        # Add files to their respective folders
        for file in file_results:
            folder_id = str(file.folder_id)
            if folder_id in folders_dict:
                folders_dict[folder_id]["files"].append(
                    {
                        "id": str(file.id),
                        "name": file.name,
                        "video_id": file.video_id,
                        "folder_id": str(file.folder_id),
                    }
                )

        # Build the folder tree
        folder_tree = []
        for folder_id, folder_data in folders_dict.items():
            parent_id = folder_data["parent_id"]
            if not parent_id:
                folder_tree.append(folder_data)
            else:
                if parent_id in folders_dict:
                    folders_dict[parent_id]["subfolders"].append(folder_data)

        return {"folders": folder_tree}

    except Exception as e:
        print(f"Error fetching folders{e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@folder_router.put("/folder")
async def rename_folder(
    folder_data: FolderRename,
    db: Session = Depends(get_db),
    user: User = Depends(get_subscribed_user),
):
    # check if new name is not already taken in the same level or is not same as parent folder name
    try:
        print(f"The new name of folder is {folder_data.new_name}")
        existing_folder = (
            db.query(Folder)
            .filter(Folder.id == folder_data.folder_id, Folder.user_id == user.id)
            .first()
        )
        if not existing_folder:
            return HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found"
            )
        # check duplicate name at same level
        duplicate_folder = (
            db.query(Folder)
            .filter(
                Folder.parent_id == existing_folder.parent_id,
                Folder.name == folder_data.new_name,
                Folder.id != existing_folder.id,
                Folder.user_id == user.id,
            )
            .first()
        )
        if duplicate_folder:
            return HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Folder with this name already exist at this level",
            )

        # update folder name
        existing_folder.name = folder_data.new_name
        db.commit()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Folder renamed successfully"},
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@folder_router.delete("/folder/{folder_id}")
async def delete_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_subscribed_user),
):
    try:
        existing_folder = (
            db.query(Folder)
            .filter(Folder.id == folder_id, Folder.user_id == user.id)
            .first()
        )
        if not existing_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Folder does not exist"
            )
        # Delete all files in the folder and its subfolders
        db.delete(existing_folder)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Folder and contents deleted successfully"},
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
