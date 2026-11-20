from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

def now():
    return datetime.now(timezone.utc)

def ts(**kw):
    return mapped_column(DateTime(timezone=True), default=now, **kw)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(10))  # 'student' | 'admin'

class Request(Base):
    __tablename__ = "requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(String(120))
    category: Mapped[str] = mapped_column(String(20), index=True)
    priority: Mapped[str] = mapped_column(String(10), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    description: Mapped[str] = mapped_column(Text)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    assigned_to: Mapped[str | None] = mapped_column(String(100))
    archived: Mapped[bool] = mapped_column(Boolean, default=False)
    attachment_name: Mapped[str | None] = mapped_column(String(200))
    attachment_type: Mapped[str | None] = mapped_column(String(50))
    attachment_size: Mapped[int | None] = mapped_column(Integer)
    attachment_path: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = ts(index=True)
    updated_at: Mapped[datetime] = ts()
    student: Mapped[User] = relationship(lazy="joined")
    replies: Mapped[list["Reply"]] = relationship(cascade="all, delete-orphan", order_by="Reply.id")
    notes: Mapped[list["Note"]] = relationship(cascade="all, delete-orphan", order_by="Note.id")
    timeline: Mapped[list["Timeline"]] = relationship(cascade="all, delete-orphan", order_by="Timeline.id")

class Reply(Base):
    __tablename__ = "replies"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()

class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()

class Timeline(Base):
    __tablename__ = "timeline"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    by: Mapped[str] = mapped_column(String(100))
    at: Mapped[datetime] = ts()
