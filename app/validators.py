from __future__ import annotations

from app.config import (
    DAYS,
    EDITABLE_STATUSES,
    HOURS,
    MAX_CONSECUTIVE_AVAILABLE,
    MAX_DAILY_FIRST_CHOICE_HOURS,
    SATURDAY_ACTIVE_HOURS,
    STATUS_CLOSED,
    STATUS_FIRST,
    STATUS_UNSELECTED,
    WORK_AVAILABLE_STATUSES,
)


def default_schedule() -> dict[str, dict[str, str]]:
    return {
        day: {
            str(hour): (
                STATUS_CLOSED
                if day == "토" and hour not in SATURDAY_ACTIVE_HOURS
                else STATUS_UNSELECTED
            )
            for hour in HOURS
        }
        for day in DAYS
    }


def normalize_schedule(payload: object) -> dict[str, dict[str, str]]:
    default = default_schedule()
    if not isinstance(payload, dict):
        return default
    result = default_schedule()
    for day in DAYS:
        day_data = payload.get(day, {})
        if not isinstance(day_data, dict):
            continue
        for hour in HOURS:
            if day == "토" and hour not in SATURDAY_ACTIVE_HOURS:
                result[day][str(hour)] = STATUS_CLOSED
                continue
            value = day_data.get(str(hour), STATUS_UNSELECTED)
            result[day][str(hour)] = value if value in EDITABLE_STATUSES else STATUS_UNSELECTED
    return result


def max_consecutive_available(schedule: dict[str, dict[str, str]], day: str) -> int:
    maximum = current = 0
    for hour in HOURS:
        status = schedule[day][str(hour)]
        if status in WORK_AVAILABLE_STATUSES:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def daily_first_choice_hours(schedule: dict[str, dict[str, str]], day: str) -> int:
    return sum(1 for hour in HOURS if schedule[day][str(hour)] == STATUS_FIRST)


def validate_schedule(payload: object) -> dict[str, dict[str, str]]:
    schedule = normalize_schedule(payload)
    consecutive_violations = []
    daily_hour_violations = []
    for day in DAYS:
        consecutive = max_consecutive_available(schedule, day)
        if consecutive > MAX_CONSECUTIVE_AVAILABLE:
            consecutive_violations.append(f"{day}요일에 연속 근무 가능시간이 {consecutive}시간 선택되어 있습니다.")
        first_hours = daily_first_choice_hours(schedule, day)
        if first_hours > MAX_DAILY_FIRST_CHOICE_HOURS:
            daily_hour_violations.append(f"{day}요일에 1순위 시간이 {first_hours}시간 선택되어 있습니다.")
    if consecutive_violations:
        raise ValueError("최대 연속 근로는 4시간까지 가능합니다. " + " ".join(consecutive_violations))
    if daily_hour_violations:
        raise ValueError(
            f"하루 1순위 근로 가능 시간은 최대 {MAX_DAILY_FIRST_CHOICE_HOURS}시간까지 선택할 수 있습니다. "
            + " ".join(daily_hour_violations)
        )
    return schedule


def first_choice_total(schedule: dict[str, dict[str, str]]) -> int:
    """학생이 1순위로 선택한 주간 총 시간을 계산한다."""
    return sum(
        1
        for day in DAYS
        for hour in HOURS
        if schedule[day][str(hour)] == "first"
    )


def weekly_first_choice_warnings(schedule: dict[str, dict[str, str]], work_type: str) -> list[str]:
    """A/B유형 월 한도를 4주로 나눈 주간 안내 범위를 기준으로 경고를 반환한다.

    경고는 제출을 막지 않는다. 실제 월별 근로일수/주차 수에 따라 운영자가 조정할 수 있기 때문이다.
    """
    from app.config import WORK_TYPE_LIMITS

    work_type = (work_type or "").strip().upper()
    limits = WORK_TYPE_LIMITS.get(work_type)
    if not limits:
        return []

    total = first_choice_total(schedule)
    warnings: list[str] = []
    if total < limits["weekly_min"]:
        warnings.append(
            f"{work_type}형 1순위 선택시간이 {total}시간입니다. "
            f"주 {limits['weekly_min']}시간 미만이면 월 최소 근로시간 {limits['monthly_min']}시간이 부족할 수 있습니다."
        )
    if total > limits["weekly_max"]:
        warnings.append(
            f"{work_type}형 1순위 선택시간이 {total}시간입니다. "
            f"주 {limits['weekly_max']}시간을 초과하면 월 최대 근로시간 {limits['monthly_max']}시간을 초과할 수 있습니다."
        )
    return warnings
