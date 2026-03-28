"""
Home Assistant notification service.

Uses the HA Supervisor API to send notifications via HA's native notification system.
"""

import os
import logging
import aiohttp

logger = logging.getLogger(__name__)

SUPERVISOR_URL = "http://supervisor"
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")


async def _ha_api_request(method: str, endpoint: str, data: dict | None = None) -> dict | None:
    """Make a request to the Home Assistant Supervisor API."""
    headers = {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }
    url = f"{SUPERVISOR_URL}{endpoint}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    text = await resp.text()
                    logger.warning(f"HA API {method} {endpoint} returned {resp.status}: {text}")
                    return None
    except aiohttp.ClientError as e:
        logger.error(f"HA API request failed: {e}")
        return None


async def send_notification(
    title: str,
    message: str,
    target: str | None = None,
    data: dict | None = None,
) -> bool:
    """
    Send a notification through Home Assistant.

    Args:
        title: Notification title
        message: Notification body
        target: Optional notification target (e.g., "mobile_app_phone")
        data: Optional extra data for the notification
    """
    service_data = {
        "title": title,
        "message": message,
    }
    if data:
        service_data["data"] = data

    # Use persistent_notification if no specific target
    if target:
        endpoint = f"/core/api/services/notify/{target}"
    else:
        endpoint = "/core/api/services/persistent_notification/create"
        service_data["notification_id"] = f"hacpm_{hash(title + message) & 0xFFFFFFFF}"

    result = await _ha_api_request("POST", endpoint, service_data)
    return result is not None


async def notify_task_due(task_title: str, assignee_name: str | None = None, target: str | None = None):
    """Send a notification that a task is due."""
    msg = f"Task '{task_title}' is due"
    if assignee_name:
        msg += f" (assigned to {assignee_name})"
    await send_notification("HACPM - Task Due", msg, target=target)


async def notify_task_completed(
    task_title: str,
    completed_by: str,
    points: int,
    target: str | None = None,
):
    """Send a notification that a task was completed."""
    msg = f"{completed_by} completed '{task_title}' and earned {points} points!"
    await send_notification("HACPM - Task Completed", msg, target=target)


async def notify_task_assigned(
    task_title: str,
    assignee_name: str,
    target: str | None = None,
):
    """Send a notification that a task was assigned."""
    msg = f"You've been assigned: '{task_title}'"
    await send_notification(f"HACPM - New Task for {assignee_name}", msg, target=target)


# ── Home Assistant To-Do List Integration ──

async def sync_todo_list(user_name: str, tasks: list[dict]) -> bool:
    """
    Sync tasks to a HA to-do list entity for a specific user.
    Creates/updates a to-do list entity: todo.hacpm_{user_name}
    """
    entity_id = f"todo.hacpm_{user_name.lower().replace(' ', '_')}"

    for task in tasks:
        item_data = {
            "entity_id": entity_id,
            "item": task["title"],
        }
        if task.get("due_date"):
            item_data["due_datetime"] = task["due_date"]
        if task.get("description"):
            item_data["description"] = task["description"]

        await _ha_api_request(
            "POST",
            "/core/api/services/todo/add_item",
            item_data,
        )

    return True


async def get_ha_config() -> dict | None:
    """Get HA core configuration."""
    return await _ha_api_request("GET", "/core/api/config")
