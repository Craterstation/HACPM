"""Task management routes — the core of HACPM."""

import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger("hacpm")

from ..database import get_db
from ..models import (
    Task, User, Label, TaskStatus, RecurrenceMode, AssigneeRotation,
    CompletionRecord, TimeSession, task_assignees, task_labels,
)
from ..schemas import (
    TaskCreate, TaskNLPCreate, TaskUpdate, TaskResponse, TaskCompleteRequest,
    CompletionResponse, TimeSessionStart, TimeSessionEnd, TimeSessionResponse,
    NLPParseResult, SubtaskResponse, RotationCreate,
)
from ..services.nlp import parse_task_text
from ..services.scheduler import (
    compute_next_due_date, can_complete_task, is_task_overdue, describe_rrule,
)
from ..services.points import get_effective_points
from ..services.rotation import advance_rotation
from ..services import sync
from ..services.notifications import notify_task_completed, notify_task_assigned

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# ── Eager-load options for task queries ──
TASK_LOAD_OPTIONS = [
    selectinload(Task.assignees),
    selectinload(Task.labels),
    selectinload(Task.subtasks).selectinload(Task.subtasks),  # 2 levels of nesting
    selectinload(Task.photos),
    selectinload(Task.rotation).selectinload(AssigneeRotation.participants),
    selectinload(Task.time_sessions),
    selectinload(Task.creator),
]


def _build_task_response(task: Task) -> dict:
    """Build a TaskResponse-compatible dict from a Task model."""
    effective_pts = get_effective_points(task)
    total_time = sum(
        (s.duration_seconds or 0) for s in task.time_sessions
    )
    completable = can_complete_task(task.due_date, task.completion_restriction_hours)

    rotation_data = None
    if task.rotation:
        rotation_data = {
            "id": task.rotation.id,
            "rotation_type": task.rotation.rotation_type.value,
            "current_index": task.rotation.current_index,
            "participant_ids": [u.id for u in task.rotation.participants],
        }

    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "points": task.points,
        "effective_points": effective_pts,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "recurrence_rule": task.recurrence_rule,
        "recurrence_mode": task.recurrence_mode.value if task.recurrence_mode else None,
        "completion_restriction_hours": task.completion_restriction_hours,
        "parent_task_id": task.parent_task_id,
        "created_by": task.created_by,
        "assignees": [
            {"id": u.id, "name": u.name,
             "role": u.role.value, "avatar": u.avatar, "is_active": u.is_active,
             "total_points": 0, "created_at": u.created_at.isoformat()}
            for u in task.assignees
        ],
        "labels": [
            {"id": l.id, "name": l.name, "color": l.color, "icon": l.icon,
             "created_at": l.created_at.isoformat()}
            for l in task.labels
        ],
        "subtasks": _build_subtasks(task.subtasks),
        "photos": [
            {"id": p.id, "filename": p.filename,
             "has_thumbnail": bool(p.thumbnail_path),
             "uploaded_at": p.uploaded_at.isoformat()}
            for p in task.photos
        ],
        "rotation": rotation_data,
        "total_time_seconds": total_time,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "can_complete": completable,
    }


def _build_subtasks(subtasks: list) -> list[dict]:
    """Recursively build subtask data."""
    result = []
    for st in subtasks:
        result.append({
            "id": st.id,
            "title": st.title,
            "description": st.description,
            "status": st.status.value,
            "priority": st.priority.value,
            "points": st.points,
            "due_date": st.due_date.isoformat() if st.due_date else None,
            "completed_at": st.completed_at.isoformat() if st.completed_at else None,
            "subtasks": _build_subtasks(st.subtasks) if hasattr(st, "subtasks") and st.subtasks else [],
        })
    return result


# ── Task CRUD ──

@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    status: TaskStatus | None = None,
    assignee_id: int | None = None,
    label_id: int | None = None,
    parent_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List tasks with optional filters."""
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).order_by(Task.due_date.asc().nullslast(), Task.created_at.desc())

    if parent_only:
        stmt = stmt.where(Task.parent_task_id.is_(None))
    if status:
        stmt = stmt.where(Task.status == status)
    if assignee_id:
        stmt = stmt.where(Task.assignees.any(User.id == assignee_id))
    if label_id:
        stmt = stmt.where(Task.labels.any(Label.id == label_id))

    result = await db.execute(stmt)
    tasks = result.scalars().unique().all()

    # Update overdue status
    for task in tasks:
        if task.status != TaskStatus.COMPLETED and is_task_overdue(task.due_date):
            task.status = TaskStatus.OVERDUE

    return [_build_task_response(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single task with all details."""
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.COMPLETED and is_task_overdue(task.due_date):
        task.status = TaskStatus.OVERDUE
    return _build_task_response(task)


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(data: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new task."""
    logger.info(f"Creating task: {data.title}")
    try:
        return await _create_task_impl(data, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


async def _create_task_impl(data: TaskCreate, db: AsyncSession):
    task = Task(
        title=data.title,
        description=data.description,
        priority=data.priority,
        points=data.points,
        due_date=data.due_date,
        recurrence_rule=data.recurrence_rule,
        recurrence_mode=data.recurrence_mode,
        completion_restriction_hours=data.completion_restriction_hours,
        parent_task_id=data.parent_task_id,
        created_by=data.created_by,
    )
    db.add(task)
    await db.flush()

    # Assign users
    if data.assignee_ids:
        users = await db.execute(select(User).where(User.id.in_(data.assignee_ids)))
        task.assignees = list(users.scalars().all())

    # Assign labels
    if data.label_ids:
        labels = await db.execute(select(Label).where(Label.id.in_(data.label_ids)))
        task.labels = list(labels.scalars().all())

    # Set up rotation
    if data.rotation:
        rotation = AssigneeRotation(
            task_id=task.id,
            rotation_type=data.rotation.rotation_type,
        )
        db.add(rotation)
        await db.flush()
        if data.rotation.participant_ids:
            participants = await db.execute(
                select(User).where(User.id.in_(data.rotation.participant_ids))
            )
            rotation.participants = list(participants.scalars().all())

    await db.flush()

    # Reload with relationships
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task.id)
    result = await db.execute(stmt)
    task = result.scalar_one()

    task_data = _build_task_response(task)
    await sync.broadcast_task_created(task_data)

    # Notify assignees
    for assignee in task.assignees:
        await notify_task_assigned(task.title, assignee.name)

    return task_data


@router.post("/nlp", response_model=TaskResponse, status_code=201)
async def create_task_from_nlp(data: TaskNLPCreate, db: AsyncSession = Depends(get_db)):
    """Create a task from natural language text."""
    logger.info(f"Creating task from NLP: {data.text}")
    try:
        return await _create_task_from_nlp_impl(data, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating NLP task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


async def _create_task_from_nlp_impl(data: TaskNLPCreate, db: AsyncSession):
    try:
        parsed = parse_task_text(data.text)
    except Exception:
        # If NLP parsing fails, use raw text as title
        from dataclasses import dataclass
        @dataclass
        class FallbackResult:
            title: str = data.text
            due_date: object = None
            rrule: object = None
        parsed = FallbackResult()

    task = Task(
        title=parsed.title,
        due_date=parsed.due_date,
        recurrence_rule=parsed.rrule,
        recurrence_mode=RecurrenceMode.DUE_DATE if parsed.rrule else None,
        created_by=data.created_by,
    )
    db.add(task)
    await db.flush()

    if data.assignee_ids:
        users = await db.execute(select(User).where(User.id.in_(data.assignee_ids)))
        task.assignees = list(users.scalars().all())
    if data.label_ids:
        labels = await db.execute(select(Label).where(Label.id.in_(data.label_ids)))
        task.labels = list(labels.scalars().all())

    await db.flush()

    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task.id)
    result = await db.execute(stmt)
    task = result.scalar_one()

    task_data = _build_task_response(task)
    await sync.broadcast_task_created(task_data)
    return task_data


@router.post("/nlp/parse", response_model=NLPParseResult)
async def parse_nlp_text(text: str):
    """Parse natural language text without creating a task (preview)."""
    try:
        parsed = parse_task_text(text)
        return NLPParseResult(
            title=parsed.title,
            due_date=parsed.due_date,
            recurrence_rule=parsed.rrule,
            recurrence_description=parsed.rrule_description,
            confidence=parsed.confidence,
        )
    except Exception:
        return NLPParseResult(title=text, confidence=0.0)


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: int, data: TaskUpdate, db: AsyncSession = Depends(get_db)):
    """Update a task."""
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle assignee updates
    if "assignee_ids" in update_data:
        ids = update_data.pop("assignee_ids")
        users = await db.execute(select(User).where(User.id.in_(ids)))
        task.assignees = list(users.scalars().all())

    # Handle label updates
    if "label_ids" in update_data:
        ids = update_data.pop("label_ids")
        labels = await db.execute(select(Label).where(Label.id.in_(ids)))
        task.labels = list(labels.scalars().all())

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.flush()

    # Reload
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task.id)
    result = await db.execute(stmt)
    task = result.scalar_one()

    task_data = _build_task_response(task)
    await sync.broadcast_task_updated(task_data)
    return task_data


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a task and all its subtasks."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.flush()
    await sync.broadcast_task_deleted(task_id)


# ── Task Completion ──

@router.post("/{task_id}/complete", response_model=CompletionResponse)
async def complete_task(
    task_id: int,
    data: TaskCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a task as completed. Handles recurring tasks, subtask reset, rotation, and points."""
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check completion restriction
    if not can_complete_task(task.due_date, task.completion_restriction_hours):
        hours = task.completion_restriction_hours
        raise HTTPException(
            status_code=400,
            detail=f"This task can only be completed within {hours} hours of its due date.",
        )

    now = datetime.datetime.utcnow()
    points = get_effective_points(task)

    # Record completion
    record = CompletionRecord(
        task_id=task.id,
        user_id=data.user_id,
        completed_at=now,
        points_earned=points,
        notes=data.notes,
    )
    db.add(record)

    # Handle recurring task
    if task.recurrence_rule:
        next_due = compute_next_due_date(
            task.recurrence_rule,
            task.recurrence_mode.value if task.recurrence_mode else "due_date",
            task.due_date,
            now,
        )
        task.due_date = next_due
        task.status = TaskStatus.PENDING
        task.completed_at = None

        # Reset all subtasks
        await _reset_subtasks(db, task.id)

        # Advance rotation if configured
        if task.rotation:
            next_assignee_id = await advance_rotation(db, task.rotation)
            if next_assignee_id:
                user = await db.get(User, next_assignee_id)
                if user:
                    task.assignees = [user]
    else:
        task.status = TaskStatus.COMPLETED
        task.completed_at = now

    await db.flush()

    # Get completing user name for notification
    user = await db.get(User, data.user_id)
    user_name = (user.name) if user else "Someone"

    await notify_task_completed(task.title, user_name, points)

    # Reload and broadcast
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task.id)
    result = await db.execute(stmt)
    task = result.scalar_one()
    task_data = _build_task_response(task)

    completion_data = {
        "id": record.id,
        "task_id": record.task_id,
        "user_id": record.user_id,
        "completed_at": record.completed_at.isoformat(),
        "points_earned": record.points_earned,
        "notes": record.notes,
    }
    await sync.broadcast_task_completed(task_data, completion_data)

    return completion_data


async def _reset_subtasks(db: AsyncSession, parent_id: int):
    """Recursively reset all subtasks to pending."""
    stmt = select(Task).where(Task.parent_task_id == parent_id)
    result = await db.execute(stmt)
    subtasks = result.scalars().all()
    for st in subtasks:
        st.status = TaskStatus.PENDING
        st.completed_at = None
        await _reset_subtasks(db, st.id)


# ── Time Tracking ──

@router.post("/time/start", response_model=TimeSessionResponse)
async def start_time_session(data: TimeSessionStart, db: AsyncSession = Depends(get_db)):
    """Start a time tracking session for a task."""
    task = await db.get(Task, data.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    session = TimeSession(
        task_id=data.task_id,
        user_id=data.user_id,
        started_at=datetime.datetime.utcnow(),
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.post("/time/stop", response_model=TimeSessionResponse)
async def stop_time_session(data: TimeSessionEnd, db: AsyncSession = Depends(get_db)):
    """Stop a time tracking session."""
    session = await db.get(TimeSession, data.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Time session not found")
    if session.ended_at:
        raise HTTPException(status_code=400, detail="Session already ended")

    session.ended_at = datetime.datetime.utcnow()
    session.duration_seconds = int((session.ended_at - session.started_at).total_seconds())
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/{task_id}/time", response_model=list[TimeSessionResponse])
async def get_task_time_sessions(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get all time sessions for a task."""
    stmt = (
        select(TimeSession)
        .where(TimeSession.task_id == task_id)
        .order_by(TimeSession.started_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


# ── Completion History ──

@router.get("/{task_id}/history", response_model=list[CompletionResponse])
async def get_task_history(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get completion history for a task."""
    stmt = (
        select(CompletionRecord)
        .where(CompletionRecord.task_id == task_id)
        .order_by(CompletionRecord.completed_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().all()
