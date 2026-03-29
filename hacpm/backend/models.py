import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey,
    Enum as SAEnum, JSON, Table
)
from sqlalchemy.orm import relationship, backref
import enum

from .database import Base


class UserRole(str, enum.Enum):
    PARENT = "parent"
    KID = "kid"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class Priority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecurrenceMode(str, enum.Enum):
    DUE_DATE = "due_date"
    COMPLETION_DATE = "completion_date"


class RotationType(str, enum.Enum):
    ROUND_ROBIN = "round_robin"
    FEWEST_COMPLETED = "fewest_completed"
    RANDOM = "random"


# Association table for task labels
task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", Integer, ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True),
)

# Association table for task assignees (multiple assignees possible)
task_assignees = Table(
    "task_assignees",
    Base.metadata,
    Column("task_id", Integer, ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

# Association table for rotation participants
rotation_participants = Table(
    "rotation_participants",
    Base.metadata,
    Column("rotation_id", Integer, ForeignKey("assignee_rotations.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    display_name = Column(String(100), nullable=True)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.KID)
    avatar = Column(String(255), nullable=True)
    pin = Column(String(10), nullable=True)  # Simple PIN for kid accounts
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    created_tasks = relationship("Task", back_populates="creator", foreign_keys="Task.created_by")
    assigned_tasks = relationship("Task", secondary=task_assignees, back_populates="assignees")
    completion_history = relationship("CompletionRecord", back_populates="user")
    time_sessions = relationship("TimeSession", back_populates="user")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(SAEnum(Priority), default=Priority.MEDIUM)

    # Points
    points = Column(Integer, nullable=True)  # None = use priority default

    # Scheduling
    due_date = Column(DateTime, nullable=True)
    recurrence_rule = Column(String(500), nullable=True)  # iCal RRULE format
    recurrence_mode = Column(SAEnum(RecurrenceMode), nullable=True)
    completion_restriction_hours = Column(Integer, nullable=True)  # Hours before due date when completable

    # Hierarchy (subtasks / nesting)
    parent_task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)

    # Ownership
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[created_by])
    assignees = relationship("User", secondary=task_assignees, back_populates="assigned_tasks")
    labels = relationship("Label", secondary=task_labels, back_populates="tasks")
    subtasks = relationship(
        "Task",
        backref=backref("parent_task", remote_side="Task.id"),
        cascade="all, delete-orphan",
    )
    photos = relationship("TaskPhoto", back_populates="task", cascade="all, delete-orphan")
    completion_records = relationship("CompletionRecord", back_populates="task", cascade="all, delete-orphan")
    time_sessions = relationship("TimeSession", back_populates="task", cascade="all, delete-orphan")
    rotation = relationship("AssigneeRotation", back_populates="task", uselist=False, cascade="all, delete-orphan")


class Label(Base):
    __tablename__ = "labels"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    color = Column(String(7), default="#3B82F6")  # Hex color
    icon = Column(String(50), nullable=True)  # MDI icon name
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    tasks = relationship("Task", secondary=task_labels, back_populates="labels")


class TaskPhoto(Base):
    __tablename__ = "task_photos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(500), nullable=False)
    filename = Column(String(255), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    task = relationship("Task", back_populates="photos")


class CompletionRecord(Base):
    __tablename__ = "completion_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(DateTime, default=datetime.datetime.utcnow)
    points_earned = Column(Integer, default=0)
    notes = Column(Text, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="completion_records")
    user = relationship("User", back_populates="completion_history")


class TimeSession(Base):
    __tablename__ = "time_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Integer, nullable=True)  # Computed on end

    # Relationships
    task = relationship("Task", back_populates="time_sessions")
    user = relationship("User", back_populates="time_sessions")


class AssigneeRotation(Base):
    __tablename__ = "assignee_rotations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    rotation_type = Column(SAEnum(RotationType), nullable=False, default=RotationType.ROUND_ROBIN)
    current_index = Column(Integer, default=0)

    # Relationships
    task = relationship("Task", back_populates="rotation")
    participants = relationship("User", secondary=rotation_participants)
