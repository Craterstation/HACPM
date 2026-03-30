from __future__ import annotations
import datetime
from pydantic import BaseModel, Field
from typing import Optional
from .models import UserRole, TaskStatus, Priority, RecurrenceMode, RotationType


# ── User Schemas ──

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.KID
    avatar: Optional[str] = None
    pin: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[UserRole] = None
    avatar: Optional[str] = None
    pin: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: int
    name: str
    role: UserRole
    avatar: Optional[str]
    is_active: bool
    total_points: int = 0
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ── Label Schemas ──

class LabelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = "#3B82F6"
    icon: Optional[str] = None


class LabelUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class LabelResponse(BaseModel):
    id: int
    name: str
    color: str
    icon: Optional[str]
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


# ── Rotation Schemas ──

class RotationCreate(BaseModel):
    rotation_type: RotationType = RotationType.ROUND_ROBIN
    participant_ids: list[int] = []


class RotationResponse(BaseModel):
    id: int
    rotation_type: RotationType
    current_index: int
    participant_ids: list[int] = []

    model_config = {"from_attributes": True}


# ── Task Schemas ──

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    points: Optional[int] = None
    due_date: Optional[datetime.datetime] = None
    recurrence_rule: Optional[str] = None
    recurrence_mode: Optional[RecurrenceMode] = None
    completion_restriction_hours: Optional[int] = None
    parent_task_id: Optional[int] = None
    created_by: Optional[int] = None
    assignee_ids: list[int] = []
    label_ids: list[int] = []
    rotation: Optional[RotationCreate] = None


class TaskNLPCreate(BaseModel):
    text: str = Field(..., min_length=1, description="Natural language task description")
    created_by: Optional[int] = None
    assignee_ids: list[int] = []
    label_ids: list[int] = []


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[Priority] = None
    points: Optional[int] = None
    due_date: Optional[datetime.datetime] = None
    recurrence_rule: Optional[str] = None
    recurrence_mode: Optional[RecurrenceMode] = None
    completion_restriction_hours: Optional[int] = None
    assignee_ids: Optional[list[int]] = None
    label_ids: Optional[list[int]] = None


class SubtaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: Priority
    points: Optional[int]
    due_date: Optional[datetime.datetime]
    completed_at: Optional[datetime.datetime]
    subtasks: list[SubtaskResponse] = []

    model_config = {"from_attributes": True}


class PhotoResponse(BaseModel):
    id: int
    filename: str
    has_thumbnail: bool = False
    uploaded_at: datetime.datetime

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: Priority
    points: Optional[int]
    effective_points: int = 0
    due_date: Optional[datetime.datetime]
    recurrence_rule: Optional[str]
    recurrence_mode: Optional[RecurrenceMode]
    completion_restriction_hours: Optional[int]
    parent_task_id: Optional[int]
    created_by: Optional[int]
    assignees: list[UserResponse] = []
    labels: list[LabelResponse] = []
    subtasks: list[SubtaskResponse] = []
    photos: list[PhotoResponse] = []
    rotation: Optional[RotationResponse] = None
    total_time_seconds: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime
    completed_at: Optional[datetime.datetime]
    can_complete: bool = True

    model_config = {"from_attributes": True}


# ── Time Session Schemas ──

class TimeSessionStart(BaseModel):
    task_id: int
    user_id: int


class TimeSessionEnd(BaseModel):
    session_id: int


class TimeSessionResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    started_at: datetime.datetime
    ended_at: Optional[datetime.datetime]
    duration_seconds: Optional[int]

    model_config = {"from_attributes": True}


# ── Completion Schemas ──

class TaskCompleteRequest(BaseModel):
    user_id: int
    notes: Optional[str] = None


class CompletionResponse(BaseModel):
    id: int
    task_id: int
    user_id: int
    completed_at: datetime.datetime
    points_earned: int
    notes: Optional[str]

    model_config = {"from_attributes": True}


# ── Analytics Schemas ──

class UserStats(BaseModel):
    user_id: int
    user_name: str
    total_points: int
    tasks_completed: int
    tasks_pending: int
    total_time_seconds: int
    completions_by_label: dict[str, int] = {}


class OverviewStats(BaseModel):
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    overdue_tasks: int
    tasks_by_priority: dict[str, int] = {}
    tasks_by_label: dict[str, int] = {}
    tasks_by_status: dict[str, int] = {}
    completion_rate: float = 0.0


class NLPParseResult(BaseModel):
    title: str
    due_date: Optional[datetime.datetime] = None
    recurrence_rule: Optional[str] = None
    recurrence_description: Optional[str] = None
    confidence: float = 0.0
