"""Analytics and reporting routes."""

import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import (
    Task, User, Label, CompletionRecord, TimeSession,
    TaskStatus, Priority, task_labels, task_assignees,
)
from ..schemas import UserStats, OverviewStats
from ..services.points import get_leaderboard, get_user_total_points

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewStats)
async def get_overview(db: AsyncSession = Depends(get_db)):
    """Get overall task statistics."""
    # Total counts by status
    status_stmt = (
        select(Task.status, func.count(Task.id))
        .where(Task.parent_task_id.is_(None))
        .group_by(Task.status)
    )
    result = await db.execute(status_stmt)
    status_counts = {row[0].value: row[1] for row in result}

    total = sum(status_counts.values())
    completed = status_counts.get("completed", 0)
    pending = status_counts.get("pending", 0) + status_counts.get("in_progress", 0)
    overdue = status_counts.get("overdue", 0)

    # By priority
    priority_stmt = (
        select(Task.priority, func.count(Task.id))
        .where(Task.parent_task_id.is_(None))
        .group_by(Task.priority)
    )
    result = await db.execute(priority_stmt)
    by_priority = {row[0].value: row[1] for row in result}

    # By label
    label_stmt = (
        select(Label.name, func.count(task_labels.c.task_id))
        .join(task_labels, Label.id == task_labels.c.label_id)
        .group_by(Label.name)
    )
    result = await db.execute(label_stmt)
    by_label = {row[0]: row[1] for row in result}

    return OverviewStats(
        total_tasks=total,
        completed_tasks=completed,
        pending_tasks=pending,
        overdue_tasks=overdue,
        tasks_by_priority=by_priority,
        tasks_by_label=by_label,
        tasks_by_status=status_counts,
        completion_rate=round(completed / total * 100, 1) if total > 0 else 0.0,
    )


@router.get("/users/{user_id}", response_model=UserStats)
async def get_user_stats(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get statistics for a specific user."""
    user = await db.get(User, user_id)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")

    total_pts = await get_user_total_points(db, user_id)

    # Completed tasks count
    completed_stmt = select(func.count(CompletionRecord.id)).where(
        CompletionRecord.user_id == user_id
    )
    result = await db.execute(completed_stmt)
    tasks_completed = result.scalar()

    # Pending tasks assigned to user
    pending_stmt = (
        select(func.count(Task.id))
        .join(task_assignees, Task.id == task_assignees.c.task_id)
        .where(
            task_assignees.c.user_id == user_id,
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS, TaskStatus.OVERDUE]),
        )
    )
    result = await db.execute(pending_stmt)
    tasks_pending = result.scalar()

    # Total time tracked
    time_stmt = select(
        func.coalesce(func.sum(TimeSession.duration_seconds), 0)
    ).where(TimeSession.user_id == user_id)
    result = await db.execute(time_stmt)
    total_time = result.scalar()

    # Completions by label
    label_stmt = (
        select(Label.name, func.count(CompletionRecord.id))
        .join(Task, CompletionRecord.task_id == Task.id)
        .join(task_labels, Task.id == task_labels.c.task_id)
        .join(Label, task_labels.c.label_id == Label.id)
        .where(CompletionRecord.user_id == user_id)
        .group_by(Label.name)
    )
    result = await db.execute(label_stmt)
    by_label = {row[0]: row[1] for row in result}

    return UserStats(
        user_id=user_id,
        user_name=user.name,
        total_points=total_pts,
        tasks_completed=tasks_completed,
        tasks_pending=tasks_pending,
        total_time_seconds=total_time,
        completions_by_label=by_label,
    )


@router.get("/leaderboard")
async def leaderboard(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get the points leaderboard."""
    return await get_leaderboard(db, limit=limit)


@router.get("/completions")
async def completion_history(
    days: int = Query(default=30, ge=1, le=365),
    user_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Get completion history over a time period (for charts)."""
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)

    stmt = (
        select(
            func.date(CompletionRecord.completed_at).label("date"),
            func.count(CompletionRecord.id).label("count"),
            func.sum(CompletionRecord.points_earned).label("points"),
        )
        .where(CompletionRecord.completed_at >= since)
        .group_by(func.date(CompletionRecord.completed_at))
        .order_by(func.date(CompletionRecord.completed_at))
    )

    if user_id:
        stmt = stmt.where(CompletionRecord.user_id == user_id)

    result = await db.execute(stmt)
    return [
        {"date": str(row.date), "count": row.count, "points": row.points}
        for row in result
    ]
