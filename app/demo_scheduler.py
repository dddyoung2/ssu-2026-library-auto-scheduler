from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass

from app.config import DAYS, HOURS, SATURDAY_ACTIVE_HOURS

WORKABLE_FALLBACK = {"second", "third"}
FALLBACK_SCORE = {"second": 100, "third": 60}


@dataclass(frozen=True)
class Slot:
    day: str
    hour: int

    @property
    def key(self) -> str:
        return f"{self.day}:{self.hour}"


def active_hours(day: str) -> list[int]:
    if day == "토":
        return sorted(SATURDAY_ACTIVE_HOURS)
    return list(HOURS)


def all_slots() -> list[Slot]:
    return [Slot(day, hour) for day in DAYS for hour in active_hours(day)]


def _max_consecutive(hours: set[int]) -> int:
    maximum = current = 0
    previous = None
    for hour in sorted(hours):
        if previous is not None and hour == previous + 1:
            current += 1
        else:
            current = 1
        maximum = max(maximum, current)
        previous = hour
    return maximum


def _first_slots(student: dict) -> list[Slot]:
    return [
        Slot(day, hour)
        for day in DAYS
        for hour in active_hours(day)
        if student["schedule"][day][str(hour)] == "first"
    ]


def generate_full_schedule(students: list[dict], min_staff: int = 5) -> tuple[dict, list[str]]:
    """1순위 시간을 학생별 총 근로시간 목표로 고정한 전체 근로표를 만든다.

    1) 모든 1순위 시간을 먼저 배정한다.
    2) 어떤 시간이 최소 인원보다 적으면 그 시간에 2순위/3순위를 표시한 학생을 찾는다.
    3) 그 학생의 다른 1순위 배정 중 인원이 여유로운 칸을 하나 빼고 부족 칸에 넣는다.

    따라서 2·3순위가 실제 배정에 사용되어도 학생의 주간 총 배정시간은
    원래 1순위로 제출한 시간 수와 동일하게 유지된다.
    """
    if min_staff < 1:
        raise ValueError("시간당 최소 인원은 1명 이상이어야 합니다.")
    if not students:
        raise ValueError("배정할 학생이 없습니다.")

    lookup = {student["id"]: student for student in students}
    slot_students: dict[tuple[str, int], set[int]] = defaultdict(set)
    assigned_slots: dict[int, set[Slot]] = defaultdict(set)
    original_first: dict[int, set[Slot]] = defaultdict(set)
    replacement_count = defaultdict(int)

    # 모든 1순위를 그대로 시작점으로 사용한다.
    for student in students:
        sid = student["id"]
        firsts = set(_first_slots(student))
        original_first[sid] = set(firsts)
        assigned_slots[sid] = set(firsts)
        for slot in firsts:
            slot_students[(slot.day, slot.hour)].add(sid)

    def valid_after_swap(sid: int, remove_slot: Slot, add_slot: Slot) -> bool:
        by_day: dict[str, set[int]] = defaultdict(set)
        for slot in assigned_slots[sid]:
            if slot != remove_slot:
                by_day[slot.day].add(slot.hour)
        by_day[add_slot.day].add(add_slot.hour)
        for day, hours in by_day.items():
            if len(hours) > 8:
                return False
            if _max_consecutive(hours) > 4:
                return False
        return True

    warnings: list[str] = []
    swaps: list[dict] = []

    # 후보가 적은 부족 시간부터 채운다. 한 번의 swap은 총 근로시간을 바꾸지 않는다.
    for _round in range(500):
        deficits = [
            Slot(day, hour)
            for day in DAYS
            for hour in active_hours(day)
            if len(slot_students[(day, hour)]) < min_staff
        ]
        if not deficits:
            break

        def fallback_candidate_count(slot: Slot) -> int:
            return sum(
                1
                for student in students
                if student["schedule"][slot.day][str(slot.hour)] in WORKABLE_FALLBACK
                and student["id"] not in slot_students[(slot.day, slot.hour)]
            )

        deficits.sort(key=lambda slot: (fallback_candidate_count(slot), len(slot_students[(slot.day, slot.hour)]), DAYS.index(slot.day), slot.hour))
        progress = False

        for deficit in deficits:
            while len(slot_students[(deficit.day, deficit.hour)]) < min_staff:
                candidates: list[tuple[float, int, Slot, str]] = []
                for student in students:
                    sid = student["id"]
                    if sid in slot_students[(deficit.day, deficit.hour)]:
                        continue
                    status = student["schedule"][deficit.day][str(deficit.hour)]
                    if status not in WORKABLE_FALLBACK:
                        continue

                    # 반드시 아직 실제 배정으로 남아 있는 '1순위' 칸을 빼서 총시간을 유지한다.
                    removable = []
                    for remove_slot in original_first[sid]:
                        if remove_slot not in assigned_slots[sid]:
                            continue
                        current_count = len(slot_students[(remove_slot.day, remove_slot.hour)])
                        if current_count <= min_staff:
                            continue
                        if not valid_after_swap(sid, remove_slot, deficit):
                            continue
                        surplus = current_count - min_staff
                        same_day_bonus = 8 if remove_slot.day == deficit.day else 0
                        removable.append((surplus * 12 + same_day_bonus, remove_slot))
                    if not removable:
                        continue
                    removal_score, remove_slot = max(removable, key=lambda item: item[0])
                    score = FALLBACK_SCORE[status] + removal_score - replacement_count[sid] * 6
                    candidates.append((score, sid, remove_slot, status))

                if not candidates:
                    warnings.append(
                        f"{deficit.day}요일 {deficit.hour:02d}:00 시간은 2·3순위 교체만으로 최소 {min_staff}명을 채우지 못했습니다."
                    )
                    break

                _, sid, remove_slot, used_status = max(candidates, key=lambda item: item[0])
                slot_students[(remove_slot.day, remove_slot.hour)].remove(sid)
                assigned_slots[sid].remove(remove_slot)
                slot_students[(deficit.day, deficit.hour)].add(sid)
                assigned_slots[sid].add(deficit)
                replacement_count[sid] += 1
                swaps.append({
                    "student_id": sid,
                    "name": lookup[sid]["name"],
                    "from": remove_slot.key,
                    "to": deficit.key,
                    "priority": used_status,
                })
                progress = True

        if not progress:
            break

    full = {
        day: {
            str(hour): [
                {
                    "id": sid,
                    "name": lookup[sid]["name"],
                    "student_no": lookup[sid]["student_no"],
                    "work_type": lookup[sid].get("work_type", ""),
                }
                for sid in sorted(slot_students[(day, hour)], key=lambda value: lookup[value]["name"])
            ]
            for hour in active_hours(day)
        }
        for day in DAYS
    }

    target_hours = {sid: len(original_first[sid]) for sid in lookup}
    actual_hours = {sid: len(assigned_slots[sid]) for sid in lookup}
    shortages = [
        {"day": day, "hour": hour, "count": len(slot_students[(day, hour)]), "required": min_staff}
        for day in DAYS
        for hour in active_hours(day)
        if len(slot_students[(day, hour)]) < min_staff
    ]
    if shortages:
        warnings.insert(0, f"최소 인원을 충족하지 못한 시간이 {len(shortages)}개 있습니다. 제출 데이터의 2·3순위 범위를 확인해 주세요.")

    return {
        "schedule": full,
        "target_hours": target_hours,
        "actual_hours": actual_hours,
        "swaps": swaps,
        "shortages": shortages,
        "min_staff": min_staff,
    }, list(dict.fromkeys(warnings))


def _parse_two_person_slots(values: list[str] | set[str]) -> set[tuple[str, int]]:
    result: set[tuple[str, int]] = set()
    for value in values:
        try:
            day, hour_text = str(value).split(":", 1)
            hour = int(hour_text)
        except (ValueError, TypeError):
            continue
        if day in DAYS and hour in active_hours(day):
            result.add((day, hour))
    return result


def _generate_desk_once(
    students: list[dict],
    full_schedule: dict,
    *,
    weekly_max_a: int,
    weekly_max_b: int,
    daily_max: int,
    two_person_slots: list[str] | set[str],
    seed: int = 20260808,
) -> tuple[dict, list[str]]:
    if weekly_max_a < 1 or weekly_max_b < 1:
        raise ValueError("A형/B형 주간 최대 데스크 시간을 각각 1시간 이상 입력해 주세요.")
    if daily_max < 1:
        raise ValueError("하루 최대 데스크 시간을 1시간 이상 입력해 주세요.")

    rng = random.Random(seed)
    lookup = {student["id"]: student for student in students}
    allowed_two = _parse_two_person_slots(two_person_slots)
    working = {
        (day, hour): {item["id"] for item in full_schedule.get(day, {}).get(str(hour), [])}
        for day in DAYS for hour in active_hours(day)
    }
    required = {
        (day, hour): (2 if (day, hour) in allowed_two else 3)
        for day in DAYS for hour in active_hours(day)
    }
    desk: dict[tuple[str, int], set[int]] = defaultdict(set)
    weekly = defaultdict(int)
    daily_hours: dict[tuple[int, str], set[int]] = defaultdict(set)
    warnings: list[str] = []

    def weekly_limit(sid: int) -> int:
        return weekly_max_a if lookup[sid].get("work_type") == "A" else weekly_max_b

    def can_take(sid: int, day: str, hours: list[int], *, allow_second_block: bool) -> bool:
        if any(sid not in working[(day, hour)] for hour in hours):
            return False
        if weekly[sid] + len(hours) > weekly_limit(sid):
            return False
        new_hours = set(daily_hours[(sid, day)]) | set(hours)
        if len(new_hours) > daily_max:
            return False
        if not allow_second_block and daily_hours[(sid, day)]:
            # 기본 원칙: 하루 한 번의 데스크 블록만 배정한다.
            existing = sorted(daily_hours[(sid, day)])
            merged = sorted(new_hours)
            if merged != list(range(merged[0], merged[-1] + 1)):
                return False
            if len(merged) > 2:
                return False
        return True

    def candidate_score(sid: int, hours: list[int], pair: bool) -> float:
        limit = weekly_limit(sid)
        ratio = weekly[sid] / max(limit, 1)
        existing = daily_hours[(sid, hours and next(iter(DAYS), "월"))]  # unused; keep scoring simple
        return (30 if pair else 0) - ratio * 70 - weekly[sid] * 2 + rng.random() * 5

    # 요일별로 2시간 블록을 먼저 채운다.
    for day in DAYS:
        hours = active_hours(day)
        pair_starts = list(range(0, len(hours) - 1, 2))
        for idx in pair_starts:
            h1, h2 = hours[idx], hours[idx + 1]
            pair_need = min(required[(day, h1)] - len(desk[(day, h1)]), required[(day, h2)] - len(desk[(day, h2)]))
            while pair_need > 0:
                candidates = []
                common = working[(day, h1)] & working[(day, h2)]
                for sid in common:
                    if sid in desk[(day, h1)] or sid in desk[(day, h2)]:
                        continue
                    if not can_take(sid, day, [h1, h2], allow_second_block=False):
                        continue
                    score = 100 - (weekly[sid] / max(weekly_limit(sid), 1)) * 60 - weekly[sid] * 2 + rng.random() * 5
                    candidates.append((score, sid))
                if not candidates:
                    break
                _, sid = max(candidates, key=lambda item: item[0])
                desk[(day, h1)].add(sid)
                desk[(day, h2)].add(sid)
                daily_hours[(sid, day)].update({h1, h2})
                weekly[sid] += 2
                pair_need -= 1

        # 남은 한 시간 단위 수요를 채운다. 먼저 하루 한 블록 원칙을 지킨다.
        for allow_second_block in (False, True):
            for hour in hours:
                while len(desk[(day, hour)]) < required[(day, hour)]:
                    candidates = []
                    for sid in working[(day, hour)]:
                        if sid in desk[(day, hour)]:
                            continue
                        if not can_take(sid, day, [hour], allow_second_block=allow_second_block):
                            continue
                        existing = daily_hours[(sid, day)]
                        adjacent = any(abs(hour - used) == 1 for used in existing)
                        score = (
                            (26 if adjacent else 0)
                            - (weekly[sid] / max(weekly_limit(sid), 1)) * 65
                            - weekly[sid] * 2
                            - (35 if existing and not adjacent else 0)
                            + rng.random() * 4
                        )
                        candidates.append((score, sid))
                    if not candidates:
                        break
                    _, sid = max(candidates, key=lambda item: item[0])
                    had_hours = bool(daily_hours[(sid, day)])
                    desk[(day, hour)].add(sid)
                    daily_hours[(sid, day)].add(hour)
                    weekly[sid] += 1
                    if allow_second_block and had_hours:
                        warnings.append(f"{lookup[sid]['name']} 학생은 {day}요일에 불가피하게 두 번째 데스크 블록이 배정되었습니다.")
                if len(desk[(day, hour)]) < required[(day, hour)] and allow_second_block:
                    warnings.append(
                        f"{day}요일 {hour:02d}:00 데스크는 {len(desk[(day, hour)])}명만 배정되었습니다. (필요 {required[(day, hour)]}명)"
                    )

    result = {
        day: {
            str(hour): [
                {
                    "id": sid,
                    "name": lookup[sid]["name"],
                    "student_no": lookup[sid]["student_no"],
                    "work_type": lookup[sid].get("work_type", ""),
                }
                for sid in sorted(desk[(day, hour)], key=lambda value: lookup[value]["name"])
            ]
            for hour in active_hours(day)
        }
        for day in DAYS
    }

    two_hour_blocks = 0
    one_hour_blocks = 0
    split_blocks = 0
    for sid in lookup:
        for day in DAYS:
            used = sorted(daily_hours[(sid, day)])
            if not used:
                continue
            # 연속 구간 수 계산
            blocks = []
            current = [used[0]]
            for hour in used[1:]:
                if hour == current[-1] + 1:
                    current.append(hour)
                else:
                    blocks.append(current)
                    current = [hour]
            blocks.append(current)
            if len(blocks) > 1:
                split_blocks += 1
            for block in blocks:
                if len(block) >= 2:
                    two_hour_blocks += len(block) // 2
                    if len(block) % 2:
                        one_hour_blocks += 1
                else:
                    one_hour_blocks += 1

    shortages = [
        {"day": day, "hour": hour, "assigned": len(desk[(day, hour)]), "required": required[(day, hour)]}
        for day in DAYS for hour in active_hours(day)
        if len(desk[(day, hour)]) < required[(day, hour)]
    ]

    return {
        "schedule": result,
        "weekly": dict(weekly),
        "two_hour_blocks": two_hour_blocks,
        "one_hour_blocks": one_hour_blocks,
        "split_blocks": split_blocks,
        "shortages": shortages,
        "settings": {
            "weekly_max_a": weekly_max_a,
            "weekly_max_b": weekly_max_b,
            "daily_max": daily_max,
            "two_person_slots": sorted(f"{day}:{hour}" for day, hour in allowed_two),
        },
    }, sorted(set(warnings))


def generate_desk_schedule(
    students: list[dict],
    full_schedule: dict,
    *,
    weekly_max_a: int,
    weekly_max_b: int,
    daily_max: int,
    two_person_slots: list[str] | set[str],
) -> tuple[dict, list[str]]:
    """여러 시드로 데스크표를 만들어 미충족 칸이 가장 적고 2시간 블록이 많은 결과를 고른다."""
    best = None
    best_key = None
    for attempt in range(36):
        result, warnings = _generate_desk_once(
            students,
            full_schedule,
            weekly_max_a=weekly_max_a,
            weekly_max_b=weekly_max_b,
            daily_max=daily_max,
            two_person_slots=two_person_slots,
            seed=20260808 + attempt * 71,
        )
        key = (len(result["shortages"]), -result["two_hour_blocks"], result["one_hour_blocks"], len(warnings))
        if best is None or key < best_key:
            best = (result, warnings)
            best_key = key
        if key[0] == 0 and result["one_hour_blocks"] <= 12:
            break
    assert best is not None
    return best


def build_full_demo(students: list[dict], min_staff: int) -> dict:
    full_result, warnings = generate_full_schedule(students, min_staff=min_staff)
    counts = [len(full_result["schedule"][day][str(hour)]) for day in DAYS for hour in active_hours(day)]
    student_summary = []
    for student in sorted(students, key=lambda item: item["name"]):
        sid = student["id"]
        student_summary.append({
            "name": student["name"],
            "student_no": student["student_no"],
            "work_type": student.get("work_type", ""),
            "target_hours": full_result["target_hours"].get(sid, 0),
            "full_hours": full_result["actual_hours"].get(sid, 0),
            "desk_hours": 0,
        })
    return {
        "full_schedule": full_result["schedule"],
        "desk_schedule": {},
        "student_summary": student_summary,
        "summary": {
            "student_count": len(students),
            "full_min_staff_setting": min_staff,
            "full_min_staff": min(counts) if counts else 0,
            "full_max_staff": max(counts) if counts else 0,
            "fallback_swap_count": len(full_result["swaps"]),
            "full_shortage_count": len(full_result["shortages"]),
            "desk_min_staff": 0,
            "desk_max_staff": 0,
            "two_hour_blocks": 0,
            "one_hour_blocks": 0,
            "warnings": warnings,
            "full_settings": {"min_staff": min_staff},
        },
    }


def build_desk_from_full(
    students: list[dict],
    full_run: dict,
    *,
    weekly_max_a: int,
    weekly_max_b: int,
    daily_max: int,
    two_person_slots: list[str],
) -> dict:
    full_schedule = full_run.get("full_schedule") or {}
    if not full_schedule:
        raise ValueError("먼저 전체 시간표를 생성해 주세요.")

    desk_result, warnings = generate_desk_schedule(
        students,
        full_schedule,
        weekly_max_a=weekly_max_a,
        weekly_max_b=weekly_max_b,
        daily_max=daily_max,
        two_person_slots=two_person_slots,
    )
    desk_counts = [len(desk_result["schedule"][day][str(hour)]) for day in DAYS for hour in active_hours(day)]

    # 전체 근로시간은 기존 run의 학생별 요약을 그대로 유지하고 데스크 시간만 덧붙인다.
    base_summary = {item["student_no"]: item for item in full_run.get("student_summary", [])}
    by_no = {student["student_no"]: student for student in students}
    id_by_no = {student["student_no"]: student["id"] for student in students}
    student_summary = []
    for student_no, student in sorted(by_no.items(), key=lambda item: item[1]["name"]):
        base = base_summary.get(student_no, {})
        sid = id_by_no[student_no]
        student_summary.append({
            "name": student["name"],
            "student_no": student_no,
            "work_type": student.get("work_type", ""),
            "target_hours": base.get("target_hours", base.get("full_hours", 0)),
            "full_hours": base.get("full_hours", 0),
            "desk_hours": desk_result["weekly"].get(sid, 0),
        })

    summary = dict(full_run.get("summary", {}))
    summary.update({
        "desk_min_staff": min(desk_counts) if desk_counts else 0,
        "desk_max_staff": max(desk_counts) if desk_counts else 0,
        "two_hour_blocks": desk_result["two_hour_blocks"],
        "one_hour_blocks": desk_result["one_hour_blocks"],
        "split_desk_blocks": desk_result["split_blocks"],
        "desk_shortage_count": len(desk_result["shortages"]),
        "desk_settings": desk_result["settings"],
        "warnings": list(full_run.get("summary", {}).get("warnings", [])) + warnings,
    })
    return {
        "full_schedule": full_schedule,
        "desk_schedule": desk_result["schedule"],
        "student_summary": student_summary,
        "summary": summary,
    }


# v4.2 호환용: 기존 한 번에 생성 엔드포인트가 호출되어도 기본 데모 설정으로 동작한다.
def build_demo_schedules(students: list[dict]) -> dict:
    full = build_full_demo(students, min_staff=5)
    return build_desk_from_full(
        students,
        full,
        weekly_max_a=8,
        weekly_max_b=4,
        daily_max=2,
        two_person_slots=[],
    )
