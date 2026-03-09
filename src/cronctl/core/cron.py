from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

MONTH_NAMES = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

DOW_NAMES = {
    "sun": 0,
    "mon": 1,
    "tue": 2,
    "wed": 3,
    "thu": 4,
    "fri": 5,
    "sat": 6,
}


@dataclass(frozen=True)
class CronField:
    values: set[int]
    any_value: bool = False

    def matches(self, value: int) -> bool:
        return self.any_value or value in self.values


@dataclass(frozen=True)
class CronExpression:
    minute: CronField
    hour: CronField
    day_of_month: CronField
    month: CronField
    day_of_week: CronField

    def matches(self, value: datetime) -> bool:
        cron_dow = value.isoweekday() % 7
        dom_ok = self.day_of_month.matches(value.day)
        dow_ok = self.day_of_week.matches(cron_dow)
        dom_any = self.day_of_month.any_value
        dow_any = self.day_of_week.any_value
        if dom_any and dow_any:
            day_ok = True
        elif dom_any:
            day_ok = dow_ok
        elif dow_any:
            day_ok = dom_ok
        else:
            day_ok = dom_ok or dow_ok
        return (
            self.minute.matches(value.minute)
            and self.hour.matches(value.hour)
            and self.month.matches(value.month)
            and day_ok
        )


def parse_cron_expression(expression: str) -> CronExpression:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("Cron expression must have exactly 5 fields")
    minute, hour, dom, month, dow = fields
    return CronExpression(
        minute=_parse_field(minute, 0, 59),
        hour=_parse_field(hour, 0, 23),
        day_of_month=_parse_field(dom, 1, 31),
        month=_parse_field(month, 1, 12, MONTH_NAMES),
        day_of_week=_parse_field(dow, 0, 7, DOW_NAMES, normalize_weekday=True),
    )


def validate_cron_expression(expression: str) -> None:
    parse_cron_expression(expression)


def next_run(
    expression: str,
    after: datetime | None = None,
    limit_days: int = 366,
) -> datetime | None:
    parsed = parse_cron_expression(expression)
    current = (
        (after or datetime.now().astimezone()).replace(second=0, microsecond=0)
        + timedelta(minutes=1)
    )
    deadline = current + timedelta(days=limit_days)
    while current <= deadline:
        if parsed.matches(current):
            return current
        current += timedelta(minutes=1)
    return None


def _parse_field(
    token: str,
    minimum: int,
    maximum: int,
    names: dict[str, int] | None = None,
    normalize_weekday: bool = False,
) -> CronField:
    token = token.strip().lower()
    if token == "*":
        return CronField(values=set(), any_value=True)
    values: set[int] = set()
    for part in token.split(","):
        values.update(_parse_part(part, minimum, maximum, names, normalize_weekday))
    return CronField(values=values, any_value=False)


def _parse_part(
    part: str,
    minimum: int,
    maximum: int,
    names: dict[str, int] | None,
    normalize_weekday: bool,
) -> set[int]:
    if "/" in part:
        base, step_text = part.split("/", 1)
        step = int(step_text)
        if step <= 0:
            raise ValueError("Cron step must be positive")
        if base == "*":
            start = minimum
            end = maximum
        elif "-" in base:
            start_text, end_text = base.split("-", 1)
            start = _parse_value(start_text, minimum, maximum, names, normalize_weekday)
            end = _parse_value(end_text, minimum, maximum, names, normalize_weekday)
        else:
            start = _parse_value(base, minimum, maximum, names, normalize_weekday)
            end = maximum
        return set(range(start, end + 1, step))
    if "-" in part:
        start_text, end_text = part.split("-", 1)
        start = _parse_value(start_text, minimum, maximum, names, normalize_weekday)
        end = _parse_value(end_text, minimum, maximum, names, normalize_weekday)
        if end < start:
            raise ValueError("Cron range end must be >= start")
        return set(range(start, end + 1))
    return {_parse_value(part, minimum, maximum, names, normalize_weekday)}


def _parse_value(
    token: str,
    minimum: int,
    maximum: int,
    names: dict[str, int] | None,
    normalize_weekday: bool,
) -> int:
    value = names[token] if names and token in names else int(token)
    if normalize_weekday and value == 7:
        value = 0
    if not minimum <= value <= maximum:
        raise ValueError(f"Cron value out of range: {token}")
    return value
