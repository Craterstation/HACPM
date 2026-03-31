"""Task management routes — the core of HACPM."""

import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

logger = logging.getLogger("hacpm")

from ..database import get_db, async_session
from ..models import (
    Task, User, Label, TaskStatus, RecurrenceMode, AssigneeRotation,
    CompletionRecord, TimeSession, task_assignees, task_labels,
    rotation_participants,
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
    selectinload(Task.subtasks),
    selectinload(Task.photos),
    selectinload(Task.rotation).selectinload(AssigneeRotation.participants),
    selectinload(Task.time_sessions),
    selectinload(Task.creator),
]


async def _load_task_response(task_id: int) -> dict:
    """Load a task in a clean session and build response dict."""
    async with async_session() as session:
        stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one()
        return _build_task_response(task)


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
        "subtasks": [
            {
                "id": st.id, "title": st.title, "description": st.description,
                "status": st.status.value, "priority": st.priority.value,
                "points": st.points,
                "due_date": st.due_date.isoformat() if st.due_date else None,
                "completed_at": st.completed_at.isoformat() if st.completed_at else None,
                "subtasks": [],
            }
            for st in task.subtasks
        ],
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

        # Use direct SQL for association tables — avoids lazy-load on
        # relationship attributes which causes greenlet_spawn errors.
        for uid in (data.assignee_ids or []):
            await db.execute(insert(task_assignees).values(task_id=task.id, user_id=uid))
        for lid in (data.label_ids or []):
            await db.execute(insert(task_labels).values(task_id=task.id, label_id=lid))

        # Set up rotation
        if data.rotation:
            rotation = AssigneeRotation(
                task_id=task.id,
                rotation_type=data.rotation.rotation_type,
            )
            db.add(rotation)
            await db.flush()
            for uid in (data.rotation.participant_ids or []):
                await db.execute(
                    insert(rotation_participants).values(rotation_id=rotation.id, user_id=uid)
                )

        task_id = task.id
        await db.commit()

        task_data = await _load_task_response(task_id)
        await sync.broadcast_task_created(task_data)

        for assignee in task_data.get("assignees", []):
            await notify_task_assigned(task_data["title"], assignee["name"])

        return task_data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.post("/nlp", response_model=TaskResponse, status_code=201)
async def create_task_from_nlp(data: TaskNLPCreate, db: AsyncSession = Depends(get_db)):
    """Create a task from natural language text."""
    logger.info(f"Creating task from NLP: {data.text}")
    try:
        try:
            parsed = parse_task_text(data.text)
        except Exception:
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

        for uid in (data.assignee_ids or []):
            await db.execute(insert(task_assignees).values(task_id=task.id, user_id=uid))
        for lid in (data.label_ids or []):
            await db.execute(insert(task_labels).values(task_id=task.id, label_id=lid))

        task_id = task.id
        await db.commit()

        task_data = await _load_task_response(task_id)
        await sync.broadcast_task_created(task_data)
        return task_data
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error creating NLP task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


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
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)

    # Handle assignee updates via direct SQL
    if "assignee_ids" in update_data:
        ids = update_data.pop("assignee_ids")
        await db.execute(delete(task_assignees).where(task_assignees.c.task_id == task_id))
        for uid in ids:
            await db.execute(insert(task_assignees).values(task_id=task_id, user_id=uid))

    # Handle label updates via direct SQL
    if "label_ids" in update_data:
        ids = update_data.pop("label_ids")
        await db.execute(delete(task_labels).where(task_labels.c.task_id == task_id))
        for lid in ids:
            await db.execute(insert(task_labels).values(task_id=task_id, label_id=lid))

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()

    task_data = await _load_task_response(task_id)
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
    """Mark a task as completed."""
    stmt = select(Task).options(*TASK_LOAD_OPTIONS).where(Task.id == task_id)
    result = await db.execute(stmt)
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not can_complete_task(task.due_date, task.completion_restriction_hours):
        hours = task.completion_restriction_hours
        raise HTTPException(
            status_code=400,
            detail=f"This task can only be completed within {hours} hours of its due date.",
        )

    now = datetime.datetime.utcnow()
    points = get_effective_points(task)

    record = CompletionRecord(
        task_id=task.id,
        user_id=data.user_id,
        completed_at=now,
        points_earned=points,
        notes=data.notes,
    )
    db.add(record)

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

        await _reset_subtasks(db, task.id)

        if task.rotation:
            next_assignee_id = await advance_rotation(db, task.rotation)
            if next_assignee_id:
                # Direct SQL instead of relationship assignment
                await db.execute(
                    delete(task_assignees).where(task_assignees.c.task_id == task.id)
                )
                await db.execute(
                    insert(task_assignees).values(task_id=task.id, user_id=next_assignee_id)
                )
    else:
        task.status = TaskStatus.COMPLETED
        task.completed_at = now

    await db.flush()

    user = await db.get(User, data.user_id)
    user_name = (user.name) if user else "Someone"

    completion_data = {
        "id": record.id,
        "task_id": record.task_id,
        "user_id": record.user_id,
        "completed_at": record.completed_at.isoformat(),
        "points_earned": record.points_earned,
        "notes": record.notes,
    }
    task_title = task.title
    tid = task.id

    await db.commit()

    await notify_task_completed(task_title, user_name, points)
    task_data = await _load_task_response(tid)
    await sync.broadcast_task_completed(task_data, completion_data)

    return completion_data


async def _reset_subtasks(db: AsyncSession, parent_id: int):
    """Reset all subtasks to pending using direct SQL."""
    stmt = select(Task.id).where(Task.parent_task_id == parent_id)
    result = await db.execute(stmt)
    child_ids = [row[0] for row in result.all()]
    for cid in child_ids:
        child = await db.get(Task, cid)
        if child:
            child.status = TaskStatus.PENDING
            child.completed_at = None
        await _reset_subtasks(db, cid)


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
