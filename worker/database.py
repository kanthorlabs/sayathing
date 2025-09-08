"""
Database models and configuration for the worker queue system.
"""

import json
from typing import Optional

from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .task import Task, TaskItem, TaskState


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models"""

    pass


class TaskModel(Base):
    """SQLAlchemy model for tasks table"""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_at: Mapped[int] = mapped_column(Integer, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    attempted_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attempted_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of error messages
    finalized_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    items: Mapped[str] = mapped_column(Text, nullable=False)  # JSON serialized TaskItem list
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False)

    # Indexes for performance
    __table_args__ = (
        Index("idx_tasks_state_schedule", "state", "schedule_at"),
        Index("idx_tasks_created", "created_at"),
    )

    def to_task(self, with_items: bool = True) -> Task:
        """Convert SQLAlchemy model to Pydantic Task"""
        # Parse items JSON if with_items else empty list
        items = []
        if with_items:
            items_data = json.loads(self.items) if self.items else []
            items = [TaskItem.model_validate(item) for item in items_data]

        # Parse attempted_error JSON
        attempted_error = json.loads(self.attempted_error) if self.attempted_error else []

        return Task(
            id=self.id,
            state=TaskState(self.state),
            schedule_at=self.schedule_at,
            attempt_count=self.attempt_count,
            attempted_at=self.attempted_at,
            attempted_error=attempted_error,
            finalized_at=self.finalized_at,
            items=items,
            item_count=self.item_count,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @classmethod
    def from_task(cls, task: Task) -> "TaskModel":
        """Convert Pydantic Task to SQLAlchemy model"""
        # Serialize items to JSON
        items_json = json.dumps([item.model_dump() for item in task.items])

        # Serialize attempted_error to JSON
        attempted_error_json = json.dumps(task.attempted_error) if task.attempted_error else None

        return cls(
            id=task.id,
            state=task.state.value,
            schedule_at=task.schedule_at,
            attempt_count=task.attempt_count,
            attempted_at=task.attempted_at,
            attempted_error=attempted_error_json,
            finalized_at=task.finalized_at,
            items=items_json,
            item_count=task.item_count,
            created_at=task.created_at,
            updated_at=task.updated_at,
        )


class DatabaseManager:
    """Manages database connections and session creation"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.async_engine = create_async_engine(database_url, echo=False)
        self.async_session_factory = async_sessionmaker(self.async_engine, class_=AsyncSession, expire_on_commit=False)

    async def create_tables(self):
        """Create all tables if they don't exist"""
        async with self.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def initialize(self):
        """Initialize the database by creating tables"""
        await self.create_tables()

    async def get_session(self) -> AsyncSession:
        """Get an async database session"""
        return self.async_session_factory()

    async def close(self):
        """Close the database connection"""
        await self.async_engine.dispose()
