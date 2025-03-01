#  Handles YouTube API calls, video metadata extraction, and transcript downloading
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Text
import asyncio

from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.security import get_current_user
from app.database.db import get_db
from app.models.models import File, User, Note
from app.utils.helpers import (
    answer_question,
    create_embeddings,
    generate_notes,
    parse_url,
    extract_video_transcript,
    break_into_chunks,
    store_in_pinecone,
)
from app.utils.markdown_delta import markdown_to_quill_delta


class RenameFile(BaseModel):
    file_id: str
    new_file_name: str


class NoteDetail(BaseModel):
    folder_id: str
    youtube_url: str
    name: str


class ChatDetail(BaseModel):
    video_id: str
    question: str


note_router = APIRouter()


async def create_embedding_and_store(chunks: List[str], video_id: str):
    vectors = await create_embeddings(chunks)
    await store_in_pinecone(chunks, vectors, video_id)


@note_router.post("/note")
async def post_youtube_url(
    note_detail: NoteDetail,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    print(
        f"-->The {note_detail.folder_id},{note_detail.name},{note_detail.youtube_url}"
    )
    video_id = parse_url(note_detail.youtube_url)
    existing_video_note = db.query(Note).filter(Note.video_id == video_id).first()
    if not existing_video_note:
        transcript = extract_video_transcript(video_id).replace("\n", "").strip()
        # break the transcript in chunks
        chunks = break_into_chunks(transcript)
        print(len(chunks))
        print(chunks)
        # Run vector processing and note generation concurrently
        vector_task = asyncio.create_task(create_embedding_and_store(chunks, video_id))
        notes_task = asyncio.create_task(generate_notes(chunks))

        notes, _ = await asyncio.gather(notes_task, vector_task)
        print(f"--> Notes from ChatGpt=> {notes}")
        formated_notes = markdown_to_quill_delta(notes)
        try:
            # Start transaction
            new_note = Note(video_id=video_id, content=formated_notes)
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
                "notes": new_note.content,
                "video_id": new_note.video_id,
                "message": "Note generated and saved successfully",
            }

        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    try:
        new_file = File(
            user_id=user.id,
            video_id=video_id,
            folder_id=note_detail.folder_id,
            content=existing_video_note,
        )
        db.add(new_file)
        db.commit()
        db.refresh(new_file)
        return {
            "notes": new_file.content,
            "video_id": video_id,
            "message": "Note already exists and file added successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@note_router.get("/note")
async def get_note(
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
            raise HTTPException(status_code=404, detail="Note not found")
        return existing_note

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# @note_router.delete("/note/{note_id}")
# async def delete_note(
#     note_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
# ):
#     try:
#         existing_note = (
#             db.query(File)
#             .filter(File.user_id == user.id)
#             .filter(File.id == note_id)
#             .first()
#         )

#         db.delete(existing_note)
#         db.commit()
#         if not existing_note:
#             raise HTTPException(status_code=404, detail="Note not found")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


@note_router.put("/note")
async def update_note(
    note_id: str,
    note: Text,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        existing_note = (
            db.query(File)
            .filter(File.user_id == user.id)
            .filter(File.id == note_id)
            .first()
        )
        if not existing_note:
            raise HTTPException(status_code=404, detail="Note not found")

        existing_note.content = note
        db.commit()
        return {"message": "Note updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@note_router.put("/rename_file")
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
            raise HTTPException(status_code=404, detail="File not found")
        file.name = rename_file.new_file_name
        db.commit()
        return {"message": "File name changed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@note_router.post("/ask")
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
            raise HTTPException(status_code=404, detail="No notes found for this video")

        # Get answer from the transcript
        print("-->Going to get Answer:")
        answer = await answer_question(chat_detail.question, chat_detail.video_id)
        print(f"--> {answer}")
        return {
            "question": chat_detail.question,
            "answer": answer,
            "video_id": chat_detail.video_id,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@note_router.delete("/note/{note_id}")
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

        db.delete(existing_note)
        db.commit()
        if not existing_note:
            raise HTTPException(status_code=404, detail="Note not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
