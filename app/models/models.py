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
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database.db import Base


# User Model
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(255), primary_key=True, default=lambda: str(uuid4())
    )
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
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
    folders: Mapped[List["Folder"]] = relationship(
        "Folder", back_populates="user", cascade="all, delete-orphan"
    )
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="user", cascade="all, delete-orphan"
    )
    subscriptions: Mapped["Subscription"] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )


# Folder Model
class Folder(Base):
    __tablename__ = "folders"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
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
    files: Mapped[List["File"]] = relationship(
        "File", back_populates="folder", cascade="all, delete-orphan"
    )


# File Model
class File(Base):
    __tablename__ = "files"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text)  # Maybe it will be json for Quill
    video_id: Mapped[str] = mapped_column(String)
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

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    paddle_subscription_id: Mapped[str] = mapped_column(
        String, unique=True, nullable=False
    )
    plan_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String, default="active"
    )  # active, cancelled, paused
    start_date: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    current_period_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


# Notes
class Note(Base):
    __tablename__ = "notes"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    video_id: Mapped[str] = mapped_column(String(11), nullable=False)
    transcript: Mapped["str"] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
