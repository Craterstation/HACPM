"""
Natural Language Processing service for task creation.

Parses phrases like:
  - "Change water filter every 6 months"
  - "Take the trash out every Monday and Tuesday at 6:15 pm"
  - "Water plants every 3 days starting next Monday"
  - "Clean gutters twice a year in March and September"
  - "Pay rent on the 1st of every month"
"""

import re
import datetime
from dataclasses import dataclass, field

import dateparser
from dateutil.rrule import rrule, DAILY, WEEKLY, MONTHLY, YEARLY, MO, TU, WE, TH, FR, SA, SU

DAY_MAP = {
    "monday": MO, "mon": MO,
    "tuesday": TU, "tue": TU, "tues": TU,
    "wednesday": WE, "wed": WE,
    "thursday": TH, "thu": TH, "thur": TH, "thurs": TH,
    "friday": FR, "fri": FR,
    "saturday": SA, "sat": SA,
    "sunday": SU, "sun": SU,
}

MONTH_MAP = {
    "january": 1, "jan": 1, "february": 2, "feb": 2,
    "march": 3, "mar": 3, "april": 4, "apr": 4,
    "may": 5, "june": 6, "jun": 6,
    "july": 7, "jul": 7, "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10, "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

ORDINAL_MAP = {
    "1st": 1, "2nd": 2, "3rd": 3, "first": 1, "second": 2, "third": 3,
    "4th": 4, "5th": 5, "6th": 6, "7th": 7, "8th": 8, "9th": 9,
    "10th": 10, "11th": 11, "12th": 12, "13th": 13, "14th": 14,
    "15th": 15, "16th": 16, "17th": 17, "18th": 18, "19th": 19,
    "20th": 20, "21st": 21, "22nd": 22, "23rd": 23, "24th": 24,
    "25th": 25, "26th": 26, "27th": 27, "28th": 28, "29th": 29,
    "30th": 30, "31st": 31,
}


@dataclass
class NLPResult:
    title: str = ""
    due_date: datetime.datetime | None = None
    rrule: str | None = None
    rrule_description: str | None = None
    confidence: float = 0.0
    time_of_day: datetime.time | None = None


def parse_task_text(text: str) -> NLPResult:
    """Parse natural language text into structured task data."""
    result = NLPResult()
    original_text = text.strip()
    working = original_text.lower()
    confidence = 0.0

    # ── Extract time of day ──
    time_match = re.search(
        r'(?:at\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)',
        working, re.IGNORECASE
    )
    time_of_day = None
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2) or 0)
        ampm = time_match.group(3).replace(".", "").lower()
        if ampm == "pm" and hour != 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        time_of_day = datetime.time(hour, minute)
        result.time_of_day = time_of_day
        # Remove time from working text for cleaner title extraction
        working = working[:time_match.start()] + working[time_match.end():]
        confidence += 0.2

    # ── Detect recurrence patterns ──
    rrule_str = None
    rrule_desc = None

    # Pattern: "every X days/weeks/months/years"
    interval_match = re.search(
        r'every\s+(\d+)\s+(day|week|month|year)s?',
        working
    )
    if interval_match:
        interval = int(interval_match.group(1))
        unit = interval_match.group(2)
        freq_map = {"day": DAILY, "week": WEEKLY, "month": MONTHLY, "year": YEARLY}
        freq = freq_map[unit]
        rule = rrule(freq=freq, interval=interval, dtstart=datetime.datetime.now())
        rrule_str = _rrule_to_string(freq, interval=interval)
        rrule_desc = f"Every {interval} {unit}{'s' if interval > 1 else ''}"
        working = working[:interval_match.start()] + working[interval_match.end():]
        confidence += 0.4

    # Pattern: "every day/daily"
    elif re.search(r'\b(every\s*day|daily)\b', working):
        rrule_str = _rrule_to_string(DAILY)
        rrule_desc = "Daily"
        working = re.sub(r'\b(every\s*day|daily)\b', '', working)
        confidence += 0.4

    # Pattern: "every week/weekly"
    elif re.search(r'\b(every\s*week|weekly)\b', working):
        rrule_str = _rrule_to_string(WEEKLY)
        rrule_desc = "Weekly"
        working = re.sub(r'\b(every\s*week|weekly)\b', '', working)
        confidence += 0.4

    # Pattern: "every month/monthly"
    elif re.search(r'\b(every\s*month|monthly)\b', working):
        rrule_str = _rrule_to_string(MONTHLY)
        rrule_desc = "Monthly"
        working = re.sub(r'\b(every\s*month|monthly)\b', '', working)
        confidence += 0.4

    # Pattern: "every year/yearly/annually"
    elif re.search(r'\b(every\s*year|yearly|annually)\b', working):
        rrule_str = _rrule_to_string(YEARLY)
        rrule_desc = "Yearly"
        working = re.sub(r'\b(every\s*year|yearly|annually)\b', '', working)
        confidence += 0.4

    # Pattern: "every Monday and Tuesday" / "every Mon, Wed, Fri"
    elif re.search(r'every\s+', working):
        days_found = []
        day_names_found = []
        remaining = working
        day_pattern = re.compile(
            r'every\s+((?:(?:' + '|'.join(DAY_MAP.keys()) + r')[\s,]*(?:and\s*)?)+)',
            re.IGNORECASE
        )
        day_match = day_pattern.search(working)
        if day_match:
            day_text = day_match.group(1)
            for day_name, day_const in DAY_MAP.items():
                if day_name in day_text.lower() and day_const not in days_found:
                    days_found.append(day_const)
                    day_names_found.append(day_name.capitalize())
            if days_found:
                day_codes = ",".join(_day_to_code(d) for d in days_found)
                rrule_str = f"FREQ=WEEKLY;BYDAY={day_codes}"
                rrule_desc = f"Every {', '.join(day_names_found)}"
                working = working[:day_match.start()] + working[day_match.end():]
                confidence += 0.5

    # Pattern: "on the 1st of every month" / "on the 15th monthly"
    if not rrule_str:
        ordinal_match = re.search(
            r'(?:on\s+)?(?:the\s+)?(\d{1,2}(?:st|nd|rd|th)|' +
            '|'.join(ORDINAL_MAP.keys()) +
            r')\s+(?:of\s+)?(?:every|each)\s+month',
            working
        )
        if ordinal_match:
            day_text = ordinal_match.group(1).lower()
            day_num = ORDINAL_MAP.get(day_text, None)
            if day_num is None:
                day_num = int(re.match(r'(\d+)', day_text).group(1))
            rrule_str = f"FREQ=MONTHLY;BYMONTHDAY={day_num}"
            rrule_desc = f"Monthly on the {_ordinal(day_num)}"
            working = working[:ordinal_match.start()] + working[ordinal_match.end():]
            confidence += 0.5

    # Pattern: "twice a year in March and September"
    if not rrule_str:
        months_match = re.search(
            r'(?:twice\s+a\s+year|every\s+year)\s+(?:in\s+)?((?:(?:' +
            '|'.join(MONTH_MAP.keys()) +
            r')[\s,]*(?:and\s*)?)+)',
            working, re.IGNORECASE
        )
        if months_match:
            month_text = months_match.group(1)
            months_found = []
            month_names_found = []
            for month_name, month_num in MONTH_MAP.items():
                if month_name in month_text.lower() and month_num not in months_found:
                    months_found.append(month_num)
                    month_names_found.append(month_name.capitalize())
            if months_found:
                month_codes = ",".join(str(m) for m in sorted(months_found))
                rrule_str = f"FREQ=YEARLY;BYMONTH={month_codes}"
                rrule_desc = f"Yearly in {', '.join(month_names_found)}"
                working = working[:months_match.start()] + working[months_match.end():]
                confidence += 0.5

    # Add time to rrule if found
    if rrule_str and time_of_day:
        rrule_str += f";BYHOUR={time_of_day.hour};BYMINUTE={time_of_day.minute}"

    result.rrule = rrule_str
    result.rrule_description = rrule_desc

    # ── Extract specific due date (non-recurring) ──
    if not rrule_str:
        parsed_date = dateparser.parse(
            original_text,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.datetime.now(),
            },
        )
        if parsed_date and parsed_date > datetime.datetime.now():
            result.due_date = parsed_date
            confidence += 0.3

    # If we have a recurrence but no due date, set due date to next occurrence
    if rrule_str and not result.due_date:
        now = datetime.datetime.now()
        if time_of_day:
            now = now.replace(hour=time_of_day.hour, minute=time_of_day.minute, second=0)
        result.due_date = now

    # ── Extract title ──
    # Remove scheduling phrases to get the clean task title
    title = original_text
    # Remove common scheduling phrases
    patterns_to_remove = [
        r'\s*every\s+\d+\s+(?:day|week|month|year)s?\s*',
        r'\s*every\s*(?:day|week|month|year|daily|weekly|monthly|yearly|annually)\s*',
        r'\s*(?:at\s+)?\d{1,2}(?::\d{2})?\s*(?:am|pm|a\.m\.|p\.m\.)\s*',
        r'\s*(?:on\s+)?(?:the\s+)?\d{1,2}(?:st|nd|rd|th)\s+(?:of\s+)?(?:every|each)\s+month\s*',
        r'\s*every\s+(?:(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday|'
        r'mon|tue|tues|wed|thu|thur|thurs|fri|sat|sun)[\s,]*(?:and\s*)?)+\s*',
        r'\s*(?:twice\s+a\s+year|every\s+year)\s+(?:in\s+)?(?:(?:january|february|march|'
        r'april|may|june|july|august|september|october|november|december|'
        r'jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec)[\s,]*(?:and\s*)?)+\s*',
        r'\s*(?:starting|beginning|from)\s+.*$',
    ]
    for pattern in patterns_to_remove:
        title = re.sub(pattern, ' ', title, flags=re.IGNORECASE)

    title = re.sub(r'\s+', ' ', title).strip()
    title = re.sub(r'^[\s,\-]+|[\s,\-]+$', '', title)

    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]

    result.title = title or original_text
    result.confidence = min(confidence, 1.0)

    return result


def _rrule_to_string(freq: int, interval: int = 1, **kwargs) -> str:
    """Convert rrule params to iCal RRULE string."""
    freq_map = {DAILY: "DAILY", WEEKLY: "WEEKLY", MONTHLY: "MONTHLY", YEARLY: "YEARLY"}
    parts = [f"FREQ={freq_map[freq]}"]
    if interval > 1:
        parts.append(f"INTERVAL={interval}")
    return ";".join(parts)


def _day_to_code(day) -> str:
    """Convert dateutil day constant to iCal day code."""
    mapping = {MO: "MO", TU: "TU", WE: "WE", TH: "TH", FR: "FR", SA: "SA", SU: "SU"}
    return mapping.get(day, "MO")


def _ordinal(n: int) -> str:
    """Convert integer to ordinal string."""
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"
