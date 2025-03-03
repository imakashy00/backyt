#  Handles YouTube API calls, video metadata extraction, and transcript downloading
from fastapi import APIRouter, Depends, HTTPException, status
from typing import Text
import asyncio

from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.database.db import get_db
from app.models.models import File, User, Note
from app.schemas.schemas import (
    ChatDetail,
    MessageResponse,
    NoteDetail,
    NoteResponse,
    RenameFile,
)
from app.utils.helpers import (
    answer_question,
    create_embedding_and_store,
    generate_notes,
    parse_url,
    extract_video_transcript,
    break_into_chunks,
)
from app.utils.markdown_delta import markdown_to_quill_delta


note_router = APIRouter()


@note_router.post("/note", response_model=NoteResponse)
async def post_youtube_url(
    note_detail: NoteDetail,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    print(
        f"-->The {note_detail.folder_id},{note_detail.name},{note_detail.youtube_url}"
    )
    try:
        # Check if duplicate already exists
        existing_file = (
            db.query(File)
            .filter(
                File.folder_id == note_detail.folder_id,
                File.name == note_detail.name,
                File.user_id == user.id,  # Important security check
            )
            .first()
        )

        if existing_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File with this name already exists in the folder",
            )
    except Exception as e:
        print(f"Error {e } while searching for existing file")
    # Extract video id
    video_id = parse_url(note_detail.youtube_url)
    if video_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video idInvalid YouTube URL or video ID can't be extracted",
        )
    # Check if video's note already exists
    existing_video_note = db.query(Note).filter(Note.video_id == video_id).first()

    if not existing_video_note:
        # Get transcript from the videos
        transcript = extract_video_transcript(video_id)
        if transcript is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Transcript not found"
            )
        transcript = transcript.replace("\n", "").strip()
        # Break the transcript in chunks
        chunks = break_into_chunks(transcript)
        # Run vector processing and note generation concurrently
        vector_task = asyncio.create_task(create_embedding_and_store(chunks, video_id))
        notes_task = asyncio.create_task(generate_notes(chunks))

        notes, _ = await asyncio.gather(notes_task, vector_task)
        print(f"--> Notes from ChatGpt=> {notes}")
        formated_notes = markdown_to_quill_delta(notes)
        try:
            # Start transaction
            new_note = Note(
                video_id=video_id, content=formated_notes, transcript=transcript
            )
            db.add(new_note)

            new_file = File(
                user_id=user.id,
                video_id=video_id,
                folder_id=note_detail.folder_id,
                content=formated_notes,
                name=note_detail.name,
            )
            db.add(new_file)

            # Commit both operations
            db.commit()

            # Refresh both objects
            db.refresh(new_note)
            db.refresh(new_file)

            return {
                "id": str(new_file.id),
                "note": new_note.content,
                "folder_id": note_detail.folder_id,
                "video_id": new_note.video_id,
                "message": "Note generated",
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Something went wrong",
            )
    # Note of video already exists in database
    try:
        print(f"-->Creating new file for already existing note of videoId{video_id}")
        new_file = File(
            user_id=user.id,
            video_id=video_id,
            folder_id=note_detail.folder_id,
            content=existing_video_note.content,
            name=note_detail.name,
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        return {
            "id": str(new_file.id),
            "note": new_file.content,
            "folder_id": note_detail.folder_id,
            "video_id": new_file.video_id,
            "message": "Note generated",
        }

    except Exception as e:
        db.rollback()
        print(f"--> Error {e} while creating file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create note",
        )


@note_router.get("/note", response_model=NoteResponse)
async def get_note(
    note_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        # Search if file is present or not
        existing_note = (
            db.query(File)
            .filter(File.user_id == user.id)
            .filter(File.id == note_id)
            .first()
        )
        if not existing_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
            )
        return {
            "id": str(existing_note.id),
            "note": existing_note.content,
            "folder_id": existing_note.folder_id,
            "video_id": existing_note.video_id,
            "message": "Note fetched",
        }

    except Exception as e:
        db.rollback()
        print(f"Error {e} while fetching file")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Something went wrong",
        )


@note_router.put("/note", response_model=MessageResponse)
async def update_note(
    note_id: str,
    note: Text,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Check if file exists
        existing_note = (
            db.query(File)
            .filter(File.user_id == user.id)
            .filter(File.id == note_id)
            .first()
        )
        if not existing_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
            )

        existing_note.content = note
        db.commit()
        return {"message": "FIle updated successfully"}

    except Exception as e:
        print(f"Error{e} while updating note")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to update note")


@note_router.put("/rename_file", response_model=MessageResponse)
async def rename_note(
    rename_file: RenameFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        file = (
            db.query(File)
            .filter(File.id == rename_file.file_id)
            .filter(File.user_id == user.id)
            .first()
        )
        if not file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # Skip update if name hasn't changed
        if file.name == rename_file.new_file_name:
            return {"message": "File name unchanged"}

        # check if new_name is already exists
        duplicate_named_file = (
            db.query(File)
            .filter(File.name == rename_file.new_file_name)
            .filter(File.folder_id == rename_file.folder_id)
            .filter(File.user_id == user.id)
            .first()
        )
        if duplicate_named_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File with this name already exists",
            )

        file.name = rename_file.new_file_name
        db.commit()
        return {"message": "File name changed"}
    except Exception as e:
        print(f"Error {e} while updating filename")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to change filename")


@note_router.post("/note/ask")
async def ask_question(
    chat_detail: ChatDetail,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        # Check if the video exists in the user's notes
        existing_file = (
            db.query(File)
            .filter(File.video_id == chat_detail.video_id, File.user_id == user.id)
            .first()
        )

        if not existing_file:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No notes found for this video",
            )

        # Get answer from the transcript
        print("-->Getting Answer:")
        answer = await answer_question(chat_detail.question, chat_detail.video_id)
        print(f"-->Answer=> {answer}")
        return JSONResponse(
            {
                "question": chat_detail.question,
                "answer": answer,
                "video_id": chat_detail.video_id,
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@note_router.delete("/note/{note_id}", response_model=MessageResponse)
async def delete_note(
    note_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        existing_note = (
            db.query(File)
            .filter(File.user_id == user.id)
            .filter(File.id == note_id)
            .first()
        )
        if not existing_note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
            )
        db.delete(existing_note)
        db.commit()
        return {"message": "File deleted"}

    except Exception as e:
        print(f"Error {e} while deleting file")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete note",
        )
