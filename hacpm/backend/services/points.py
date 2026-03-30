"""
Gamification / points service.

Points are awarded on task completion. Each task can have a custom point value,
or fall back to priority-based defaults from the add-on configuration.
"""

import os
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Task, CompletionRecord, Priority


# Default point values (overridden by HA add-on config)
PRIORITY_POINTS = {
    Priority.LOW: int(os.environ.get("HACPM_POINTS_LOW", "1")),
    Priority.MEDIUM: int(os.environ.get("HACPM_POINTS_MEDIUM", "3")),
    Priority.HIGH: int(os.environ.get("HACPM_POINTS_HIGH", "5")),
    Priority.CRITICAL: int(os.environ.get("HACPM_POINTS_CRITICAL", "10")),
}


def get_effective_points(task: Task) -> int:
    """Get the effective point value for a task (custom or priority-based)."""
    if task.points is not None:
        return task.points
    return PRIORITY_POINTS.get(task.priority, 3)


async def get_user_total_points(db: AsyncSession, user_id: int) -> int:
    """Get total points earned by a user across all time."""
    stmt = select(func.coalesce(func.sum(CompletionRecord.points_earned), 0)).where(
        CompletionRecord.user_id == user_id
    )
    result = await db.execute(stmt)
    return result.scalar()


async def get_user_points_in_period(
    db: AsyncSession,
    user_id: int,
    start: "datetime.datetime",
    end: "datetime.datetime",
) -> int:
    """Get points earned by a user within a specific time period."""
    import datetime
    stmt = (
        select(func.coalesce(func.sum(CompletionRecord.points_earned), 0))
        .where(
            CompletionRecord.user_id == user_id,
            CompletionRecord.completed_at >= start,
            CompletionRecord.completed_at <= end,
        )
    )
    result = await db.execute(stmt)
    return result.scalar()


async def get_leaderboard(db: AsyncSession, limit: int = 10) -> list[dict]:
    """Get a points leaderboard sorted by total points descending."""
    from ..models import User
    stmt = (
        select(
            User.id,
            User.name,
            User.avatar,
            func.coalesce(func.sum(CompletionRecord.points_earned), 0).label("total_points"),
            func.count(CompletionRecord.id).label("tasks_completed"),
        )
        .outerjoin(CompletionRecord, CompletionRecord.user_id == User.id)
        .where(User.is_active.is_(True))
        .group_by(User.id)
        .order_by(func.coalesce(func.sum(CompletionRecord.points_earned), 0).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [
        {
            "user_id": row.id,
            "name": row.name,
            "avatar": row.avatar,
            "total_points": row.total_points,
            "tasks_completed": row.tasks_completed,
        }
        for row in result
    ]
