"""
Home Assistant Integration Module

Syncs HACPM tasks to native HA to-do list entities via the Supervisor API.
Each user gets their own to-do list in HA (e.g., todo.hacpm_john).
"""

import logging
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import Task, User, TaskStatus, task_assignees
from .services.notifications import _ha_api_request

logger = logging.getLogger(__name__)


async def sync_user_todo_lists(db: AsyncSession):
    """
    Sync all user task lists to HA native to-do lists.
    Called periodically or after task changes.
    """
    # Get all active users
    result = await db.execute(select(User).where(User.is_active.is_(True)))
    users = result.scalars().all()

    for user in users:
        await _sync_user_list(db, user)


async def _sync_user_list(db: AsyncSession, user: User):
    """Sync tasks for a single user to their HA to-do list."""
    entity_id = f"todo.hacpm_{user.name.lower().replace(' ', '_')}"

    # Get tasks assigned to this user
    stmt = (
        select(Task)
        .where(
            Task.assignees.any(User.id == user.id),
            Task.parent_task_id.is_(None),
        )
        .order_by(Task.due_date.asc().nullslast())
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    # First, try to remove all existing items for a clean sync
    # Then add current tasks
    for task in tasks:
        status = "needs_action" if task.status != TaskStatus.COMPLETED else "completed"

        item_data = {
            "entity_id": entity_id,
            "item": task.title,
            "status": status,
        }

        if task.due_date:
            item_data["due_datetime"] = task.due_date.isoformat()
        if task.description:
            item_data["description"] = task.description

        await _ha_api_request("POST", "/core/api/services/todo/add_item", item_data)


async def create_ha_todo_lists(db: AsyncSession):
    """
    Create HA to-do list helper entities for each active user.
    This is done via the HA helpers API if available, or relies on
    the todo.add_item service to auto-create lists.
    """
    result = await db.execute(select(User).where(User.is_active.is_(True)))
    users = result.scalars().all()

    for user in users:
        entity_id = f"todo.hacpm_{user.name.lower().replace(' ', '_')}"
        logger.info(f"Ensuring HA to-do list exists: {entity_id}")

        # Add a placeholder item to ensure the list exists
        await _ha_api_request(
            "POST",
            "/core/api/services/todo/add_item",
            {
                "entity_id": entity_id,
                "item": f"Welcome to HACPM, {user.name}!",
                "status": "completed",
            },
        )


async def mark_ha_task_complete(user: User, task_title: str):
    """Mark a task as completed in the user's HA to-do list."""
    entity_id = f"todo.hacpm_{user.name.lower().replace(' ', '_')}"
    await _ha_api_request(
        "POST",
        "/core/api/services/todo/update_item",
        {
            "entity_id": entity_id,
            "item": task_title,
            "status": "completed",
        },
    )


async def remove_ha_task(user: User, task_title: str):
    """Remove a task from the user's HA to-do list."""
    entity_id = f"todo.hacpm_{user.name.lower().replace(' ', '_')}"
    await _ha_api_request(
        "POST",
        "/core/api/services/todo/remove_item",
        {
            "entity_id": entity_id,
            "item": task_title,
        },
    )
