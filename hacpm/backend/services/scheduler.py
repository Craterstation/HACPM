"""
Task scheduling service.

Handles recurrence computation, due date management, and subtask resets.
Supports both due-date-based and completion-date-based recurrence.
"""

import datetime
import re
from dateutil.rrule import rrulestr, rrule, DAILY, WEEKLY, MONTHLY, YEARLY


def compute_next_due_date(
    recurrence_rule: str,
    recurrence_mode: str,
    previous_due_date: datetime.datetime | None,
    completion_date: datetime.datetime | None,
) -> datetime.datetime | None:
    """
    Compute the next due date for a recurring task.

    Args:
        recurrence_rule: iCal RRULE string (e.g., "FREQ=WEEKLY;BYDAY=MO,TU")
        recurrence_mode: "due_date" or "completion_date"
        previous_due_date: The previous due date of the task
        completion_date: When the task was actually completed
    """
    if not recurrence_rule:
        return None

    # Determine the base date for computing next occurrence
    if recurrence_mode == "completion_date" and completion_date:
        base_date = completion_date
    elif previous_due_date:
        base_date = previous_due_date
    else:
        base_date = datetime.datetime.now()

    # Extract BYHOUR and BYMINUTE if present for time preservation
    hour, minute = _extract_time_from_rule(recurrence_rule)

    # Parse the RRULE - strip custom time params for dateutil compatibility
    clean_rule = _clean_rule_for_dateutil(recurrence_rule)

    try:
        rule_str = f"DTSTART:{base_date.strftime('%Y%m%dT%H%M%S')}\nRRULE:{clean_rule}"
        rule = rrulestr(rule_str)

        # Get the next occurrence after the base date
        next_date = rule.after(base_date)

        if next_date and hour is not None:
            next_date = next_date.replace(hour=hour, minute=minute or 0, second=0)

        return next_date
    except (ValueError, TypeError):
        return None


def get_upcoming_occurrences(
    recurrence_rule: str,
    start_date: datetime.datetime | None = None,
    count: int = 10,
) -> list[datetime.datetime]:
    """Get the next N occurrences of a recurring rule."""
    if not recurrence_rule:
        return []

    base_date = start_date or datetime.datetime.now()
    hour, minute = _extract_time_from_rule(recurrence_rule)
    clean_rule = _clean_rule_for_dateutil(recurrence_rule)

    try:
        rule_str = f"DTSTART:{base_date.strftime('%Y%m%dT%H%M%S')}\nRRULE:{clean_rule}"
        rule = rrulestr(rule_str)
        occurrences = []
        for dt in rule:
            if dt > base_date:
                if hour is not None:
                    dt = dt.replace(hour=hour, minute=minute or 0, second=0)
                occurrences.append(dt)
                if len(occurrences) >= count:
                    break
        return occurrences
    except (ValueError, TypeError):
        return []


def is_task_overdue(due_date: datetime.datetime | None) -> bool:
    """Check if a task is overdue."""
    if not due_date:
        return False
    return datetime.datetime.now() > due_date


def can_complete_task(
    due_date: datetime.datetime | None,
    restriction_hours: int | None,
) -> bool:
    """
    Check if a task can be completed based on completion restrictions.

    If restriction_hours is set, the task can only be completed within
    the last X hours before its due date.
    """
    if not restriction_hours or not due_date:
        return True

    now = datetime.datetime.now()
    earliest_completion = due_date - datetime.timedelta(hours=restriction_hours)
    return now >= earliest_completion


def describe_rrule(recurrence_rule: str) -> str:
    """Convert an RRULE string to a human-readable description."""
    if not recurrence_rule:
        return ""

    parts = dict(item.split("=", 1) for item in recurrence_rule.split(";") if "=" in item)
    freq = parts.get("FREQ", "")
    interval = int(parts.get("INTERVAL", "1"))
    byday = parts.get("BYDAY", "")
    bymonth = parts.get("BYMONTH", "")
    bymonthday = parts.get("BYMONTHDAY", "")
    byhour = parts.get("BYHOUR", "")
    byminute = parts.get("BYMINUTE", "0")

    day_names = {
        "MO": "Monday", "TU": "Tuesday", "WE": "Wednesday",
        "TH": "Thursday", "FR": "Friday", "SA": "Saturday", "SU": "Sunday",
    }
    month_names = {
        1: "January", 2: "February", 3: "March", 4: "April",
        5: "May", 6: "June", 7: "July", 8: "August",
        9: "September", 10: "October", 11: "November", 12: "December",
    }

    desc = ""
    if freq == "DAILY":
        desc = "Daily" if interval == 1 else f"Every {interval} days"
    elif freq == "WEEKLY":
        if byday:
            days = [day_names.get(d.strip(), d.strip()) for d in byday.split(",")]
            desc = f"Every {', '.join(days)}"
        else:
            desc = "Weekly" if interval == 1 else f"Every {interval} weeks"
    elif freq == "MONTHLY":
        if bymonthday:
            desc = f"Monthly on the {_ordinal(int(bymonthday))}"
        else:
            desc = "Monthly" if interval == 1 else f"Every {interval} months"
    elif freq == "YEARLY":
        if bymonth:
            months = [month_names.get(int(m.strip()), str(m)) for m in bymonth.split(",")]
            desc = f"Yearly in {', '.join(months)}"
        else:
            desc = "Yearly" if interval == 1 else f"Every {interval} years"

    if byhour:
        h = int(byhour)
        m = int(byminute)
        ampm = "AM" if h < 12 else "PM"
        display_h = h % 12 or 12
        time_str = f"{display_h}:{m:02d} {ampm}"
        desc += f" at {time_str}"

    return desc


def _extract_time_from_rule(rule: str) -> tuple[int | None, int | None]:
    """Extract BYHOUR and BYMINUTE from an RRULE string."""
    parts = dict(item.split("=", 1) for item in rule.split(";") if "=" in item)
    hour = int(parts["BYHOUR"]) if "BYHOUR" in parts else None
    minute = int(parts.get("BYMINUTE", "0")) if "BYHOUR" in parts else None
    return hour, minute


def _clean_rule_for_dateutil(rule: str) -> str:
    """Remove custom params (BYHOUR, BYMINUTE) that dateutil doesn't handle well in all contexts."""
    parts = rule.split(";")
    clean = [p for p in parts if not p.startswith("BYHOUR") and not p.startswith("BYMINUTE")]
    return ";".join(clean)


def _ordinal(n: int) -> str:
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
