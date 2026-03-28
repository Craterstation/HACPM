"""
Assignee rotation service.

Supports three rotation modes:
  - round_robin: Rotate through participants in fixed order
  - fewest_completed: Assign to whoever has completed the fewest tasks
  - random: Random assignment from participants
"""

import random
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AssigneeRotation, RotationType, CompletionRecord, rotation_participants, User


async def get_next_assignee(
    db: AsyncSession,
    rotation: AssigneeRotation,
) -> int | None:
    """
    Determine the next assignee based on rotation type.
    Returns the user_id of the next assignee.
    """
    # Get participant user IDs
    participant_ids = [u.id for u in rotation.participants]
    if not participant_ids:
        return None

    if rotation.rotation_type == RotationType.ROUND_ROBIN:
        return await _round_robin(db, rotation, participant_ids)
    elif rotation.rotation_type == RotationType.FEWEST_COMPLETED:
        return await _fewest_completed(db, rotation, participant_ids)
    elif rotation.rotation_type == RotationType.RANDOM:
        return _random_pick(participant_ids)
    return None


async def _round_robin(
    db: AsyncSession,
    rotation: AssigneeRotation,
    participant_ids: list[int],
) -> int:
    """Pick the next person in round-robin order and advance the index."""
    idx = rotation.current_index % len(participant_ids)
    next_user = participant_ids[idx]
    rotation.current_index = (idx + 1) % len(participant_ids)
    return next_user


async def _fewest_completed(
    db: AsyncSession,
    rotation: AssigneeRotation,
    participant_ids: list[int],
) -> int:
    """Pick the participant who has completed the fewest tasks for this task."""
    # Count completions per participant for this specific task
    stmt = (
        select(CompletionRecord.user_id, func.count(CompletionRecord.id).label("cnt"))
        .where(
            CompletionRecord.task_id == rotation.task_id,
            CompletionRecord.user_id.in_(participant_ids),
        )
        .group_by(CompletionRecord.user_id)
    )
    result = await db.execute(stmt)
    counts = {row.user_id: row.cnt for row in result}

    # Find participant(s) with fewest completions
    min_count = float("inf")
    candidates = []
    for uid in participant_ids:
        c = counts.get(uid, 0)
        if c < min_count:
            min_count = c
            candidates = [uid]
        elif c == min_count:
            candidates.append(uid)

    return random.choice(candidates)


def _random_pick(participant_ids: list[int]) -> int:
    """Pick a random participant."""
    return random.choice(participant_ids)


async def advance_rotation(
    db: AsyncSession,
    rotation: AssigneeRotation,
) -> int | None:
    """
    Get the next assignee and update the rotation state.
    Returns the user_id of the new assignee.
    """
    next_user_id = await get_next_assignee(db, rotation)
    if next_user_id is not None:
        await db.flush()
    return next_user_id
