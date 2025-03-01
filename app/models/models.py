from datetime import datetime
from uuid import uuid4
from sqlalchemy import UUID
from typing import Optional, List
from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    Enum as SQLAlchemyEnum,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.db import Base

# from app.schemas.schemas import BillingCycle


# User Model
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    # email_verified: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    google_id: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    # Relationships
    # accounts: Mapped[List["Account"]] = relationship("Account", back_populates="user", cascade="all, delete-orphan",lazy="select")
    folders: Mapped[List["Folder"]] = relationship(
        "Folder", back_populates="user", cascade="all, delete-orphan"
    )
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )


# Account Model
# class Account(Base):
#     __tablename__ = 'accounts'

#     id: Mapped[str] = mapped_column(String(255), primary_key=True, default=lambda: str(uuid4()))
#     provider: Mapped[str] = mapped_column(String())
#     provider_account_id: Mapped[str] = mapped_column(String())
#     refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
#     expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
#     created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.current_timestamp())
#     updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False,server_default=func.current_timestamp(), onupdate=func.current_timestamp())
#     user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

#     user: Mapped["User"] = relationship("User", back_populates="accounts")


# Folder Model
class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # icon: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[Optional[UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    parent: Mapped[Optional["Folder"]] = relationship("Folder", remote_side=[id])
    subfolders: Mapped[List["Folder"]] = relationship(
        "Folder", back_populates="parent", cascade="all, delete-orphan"
    )
    user: Mapped["User"] = relationship("User", back_populates="folders")
    files: Mapped[List["File"]] = relationship("File", back_populates="folder")


# File Model
class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text)  # Maybe it will be json for Quill
    video_id:Mapped[str] = mapped_column(String)
    folder_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    folder: Mapped["Folder"] = relationship("Folder", back_populates="files")
    user: Mapped["User"] = relationship("User", back_populates="files")


# Subscription Model
class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    stripe_id: Mapped[str] = mapped_column(String(255), nullable=False)
    # billingCycle: Mapped[str] = mapped_column(SQLAlchemyEnum(BillingCycle), nullable=False)
    start_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")


# Transcripts
class Transcript(Base):
    __tablename__ = "transcripts"

    id: Mapped[str] = mapped_column(String(11), primary_key=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    note_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notes.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    note: Mapped["Note"] = relationship("Note", back_populates="transcript")


# Notes
class Note(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)  # May be json format
    video_id: Mapped[str] = mapped_column(String(11), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    transcript: Mapped["Transcript"] = relationship(
        "Transcript", back_populates="note", uselist=False
    )
