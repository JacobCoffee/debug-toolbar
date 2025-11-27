"""Database models for the example application."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


class User(UUIDAuditBase):
    """User model."""

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    posts: Mapped[list[Post]] = relationship(back_populates="author", lazy="selectin")


class Post(UUIDAuditBase):
    """Blog post model."""

    __tablename__ = "posts"

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    author: Mapped[User] = relationship(back_populates="posts", lazy="joined")
    published_at: Mapped[datetime | None] = mapped_column(default=None)

    def publish(self) -> None:
        """Mark post as published."""
        self.published_at = datetime.now(tz=timezone.utc)
