from __future__ import annotations

import csv
import json
import random
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, create_engine, delete, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import DATABASE_URL, DAYS, HOURS, SATURDAY_ACTIVE_HOURS, USERS_CSV
from app.validators import default_schedule


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), index=True)
    student_no: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    work_type: Mapped[str] = mapped_column(String(5), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    schedule: Mapped["Schedule | None"] = relationship(back_populates="student", uselist=False)


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), unique=True, index=True)
    schedule_json: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    student: Mapped[Student] = relationship(back_populates="schedule")


class ScheduleRevision(Base):
    __tablename__ = "schedule_revisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    schedule_json: Mapped[str] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class ScheduleRun(Base):
    __tablename__ = "schedule_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_schedule_json: Mapped[str] = mapped_column(Text)
    desk_schedule_json: Mapped[str] = mapped_column(Text)
    student_summary_json: Mapped[str] = mapped_column(Text)
    summary_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine_kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
if DATABASE_URL == "sqlite:///:memory:":
    engine_kwargs["poolclass"] = StaticPool
engine = create_engine(DATABASE_URL, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def init_database() -> None:
    # 운영 배포에서는 학생 명단을 코드/CSV에서 자동 주입하지 않습니다.
    # 최초 DB는 비어 있고, 관리자가 웹 화면에서 학생을 등록한 뒤 로그인할 수 있습니다.
    Base.metadata.create_all(engine)


def _read_csv_rows() -> list[dict[str, str]]:
    if not USERS_CSV.exists():
        return []
    with USERS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def sync_students(rows: Iterable[dict[str, str]], deactivate_missing: bool = False) -> int:
    normalized: list[dict[str, str | bool]] = []
    seen: set[str] = set()
    for row in rows:
        name = str(row.get("name", "")).strip()
        student_no = str(row.get("student_no", "")).strip()
        work_type = str(row.get("work_type", "")).strip().upper()
        active_text = str(row.get("active", "1")).strip().lower()
        active = active_text not in {"0", "false", "n", "no"}
        if not name or not student_no:
            continue
        if student_no in seen:
            raise ValueError(f"중복 학번: {student_no}")
        if work_type not in {"", "A", "B"}:
            raise ValueError(f"근로유형은 A, B 또는 빈 값만 가능합니다: {student_no}")
        seen.add(student_no)
        normalized.append({"name": name, "student_no": student_no, "work_type": work_type, "active": active})

    with SessionLocal() as session:
        if deactivate_missing:
            for student in session.scalars(select(Student)).all():
                student.active = False
        for row in normalized:
            student = session.scalar(select(Student).where(Student.student_no == row["student_no"]))
            if student is None:
                student = Student(**row)
                session.add(student)
            else:
                student.name = str(row["name"])
                student.work_type = str(row["work_type"])
                student.active = bool(row["active"])
        # 명단이 바뀌면 기존 자동배정 결과는 더 이상 최신 상태가 아니므로 폐기합니다.
        session.execute(delete(ScheduleRun))
        session.commit()
    return len(normalized)


def sync_students_from_csv() -> int:
    # 더미학생이 재시작 시 비활성화되지 않도록, 초기 CSV 동기화는 기존 학생을 유지한다.
    return sync_students(_read_csv_rows(), deactivate_missing=False)


def authenticate_student(name: str, student_no: str) -> Student | None:
    with SessionLocal() as session:
        return session.scalar(
            select(Student).where(
                Student.name == name.strip(),
                Student.student_no == student_no.strip(),
                Student.active.is_(True),
            )
        )


def get_student(student_id: int) -> Student | None:
    with SessionLocal() as session:
        return session.get(Student, student_id)


def get_student_schedule(student_id: int) -> dict | None:
    with SessionLocal() as session:
        row = session.scalar(select(Schedule).where(Schedule.student_id == student_id))
        if row is None:
            return None
        return {
            "schedule": json.loads(row.schedule_json),
            "state": row.state,
            "saved_at": row.saved_at.isoformat(),
            "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
        }


def save_student_schedule(student_id: int, schedule: dict, state: str) -> dict:
    now = utcnow()
    with SessionLocal() as session:
        row = session.scalar(select(Schedule).where(Schedule.student_id == student_id))
        if row is None:
            row = Schedule(
                student_id=student_id,
                schedule_json=json.dumps(schedule, ensure_ascii=False),
                state=state,
                saved_at=now,
                submitted_at=now if state == "submitted" else None,
            )
            session.add(row)
        else:
            row.schedule_json = json.dumps(schedule, ensure_ascii=False)
            row.state = state
            row.saved_at = now
            if state == "submitted":
                row.submitted_at = now
        session.add(
            ScheduleRevision(
                student_id=student_id,
                schedule_json=json.dumps(schedule, ensure_ascii=False),
                state=state,
                created_at=now,
            )
        )
        # 학생 제출내용이 바뀌면 이전 자동배정 결과는 무효화합니다.
        session.execute(delete(ScheduleRun))
        session.commit()
        return {
            "state": row.state,
            "saved_at": row.saved_at.isoformat(),
            "submitted_at": row.submitted_at.isoformat() if row.submitted_at else None,
        }


def admin_students() -> list[dict]:
    with SessionLocal() as session:
        students = session.scalars(select(Student).order_by(Student.active.desc(), Student.name, Student.student_no)).all()
        result = []
        for student in students:
            schedule = session.scalar(select(Schedule).where(Schedule.student_id == student.id))
            result.append({
                "id": student.id,
                "name": student.name,
                "student_no": student.student_no,
                "work_type": student.work_type,
                "active": student.active,
                "state": schedule.state if schedule else "not_started",
                "saved_at": schedule.saved_at.isoformat() if schedule else None,
                "submitted_at": schedule.submitted_at.isoformat() if schedule and schedule.submitted_at else None,
            })
        return result


def active_student_count() -> int:
    with SessionLocal() as session:
        return len(session.scalars(select(Student).where(Student.active.is_(True))).all())


def create_student(name: str, student_no: str, work_type: str = "", active: bool = True) -> int:
    name = name.strip()
    student_no = student_no.strip()
    work_type = work_type.strip().upper()
    if not name or not student_no:
        raise ValueError("이름과 학번을 모두 입력해 주세요.")
    if work_type not in {"", "A", "B"}:
        raise ValueError("근로유형은 A, B 또는 미지정만 가능합니다.")
    with SessionLocal() as session:
        if session.scalar(select(Student).where(Student.student_no == student_no)) is not None:
            raise ValueError("이미 등록된 학번입니다.")
        student = Student(name=name, student_no=student_no, work_type=work_type, active=active)
        session.add(student)
        session.execute(delete(ScheduleRun))
        session.commit()
        session.refresh(student)
        return student.id


def update_student(student_id: int, name: str, student_no: str, work_type: str, active: bool) -> None:
    name = name.strip()
    student_no = student_no.strip()
    work_type = work_type.strip().upper()
    if not name or not student_no:
        raise ValueError("이름과 학번을 모두 입력해 주세요.")
    if work_type not in {"", "A", "B"}:
        raise ValueError("근로유형은 A, B 또는 미지정만 가능합니다.")
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise ValueError("학생을 찾을 수 없습니다.")
        duplicate = session.scalar(select(Student).where(Student.student_no == student_no, Student.id != student_id))
        if duplicate is not None:
            raise ValueError("이미 다른 학생이 사용 중인 학번입니다.")
        student.name = name
        student.student_no = student_no
        student.work_type = work_type
        student.active = active
        session.execute(delete(ScheduleRun))
        session.commit()


def schedule_generation_readiness() -> dict:
    with SessionLocal() as session:
        students = session.scalars(select(Student).where(Student.active.is_(True)).order_by(Student.name)).all()
        not_submitted: list[str] = []
        untyped: list[str] = []
        for student in students:
            schedule = session.scalar(select(Schedule).where(Schedule.student_id == student.id))
            if schedule is None or schedule.state != "submitted":
                not_submitted.append(student.name)
            if student.work_type not in {"A", "B"}:
                untyped.append(student.name)
        return {
            "active_count": len(students),
            "submitted_count": len(students) - len(not_submitted),
            "not_submitted": not_submitted,
            "untyped": untyped,
            "ready": bool(students) and not not_submitted and not untyped,
        }


def update_work_type(student_id: int, work_type: str) -> None:
    work_type = work_type.strip().upper()
    if work_type not in {"", "A", "B"}:
        raise ValueError("근로유형은 A, B 또는 미지정만 가능합니다.")
    with SessionLocal() as session:
        student = session.get(Student, student_id)
        if student is None:
            raise ValueError("학생을 찾을 수 없습니다.")
        student.work_type = work_type
        session.execute(delete(ScheduleRun))
        session.commit()


def _dummy_schedule(seed: int, work_type: str, global_first_counts: dict[tuple[str, int], int]) -> dict:
    """실제 제출 패턴에 가까운 더미 시간표를 만든다.

    A형은 1순위 14~20시간, B형은 7~10시간을 만들고, 1순위가 특정 시간에 몰리지
    않도록 현재 전역 1순위 인원이 적은 시간부터 우선 선택한다. 2·3순위도 연속
    가능시간 4시간 제한을 넘지 않도록 추가한다.
    """
    rng = random.Random(seed)
    schedule = default_schedule()
    active_slots = [(day, hour) for day in DAYS for hour in (sorted(SATURDAY_ACTIVE_HOURS) if day == "토" else HOURS)]

    # 먼저 소수의 수업/절대불가능 시간을 만든다.
    shuffled = list(active_slots)
    rng.shuffle(shuffled)
    class_count = 5 if work_type == "A" else 7
    impossible_count = 3 if work_type == "A" else 4
    for day, hour in shuffled[:class_count]:
        schedule[day][str(hour)] = "class"
    for day, hour in shuffled[class_count:class_count + impossible_count]:
        if schedule[day][str(hour)] == "unselected":
            schedule[day][str(hour)] = "impossible"

    target = rng.randint(14, 20) if work_type == "A" else rng.randint(7, 10)
    chosen: set[tuple[str, int]] = set()

    def can_add_work(day: str, hour: int) -> bool:
        day_hours = sorted(h for d, h in chosen if d == day)
        test = sorted(set(day_hours + [hour]))
        if len(test) > 8:
            return False
        current = maximum = 0
        previous = None
        for value in test:
            if previous is not None and value == previous + 1:
                current += 1
            else:
                current = 1
            maximum = max(maximum, current)
            previous = value
        return maximum <= 4

    # 실제 근무표처럼 2시간 연속 블록을 우선 만들면서 시간대별 인원도 고르게 분산한다.
    block_candidates = []
    for day in DAYS:
        day_active = sorted(SATURDAY_ACTIVE_HOURS) if day == "토" else list(HOURS)
        for hour in day_active[:-1]:
            if hour + 1 not in day_active:
                continue
            if schedule[day][str(hour)] != "unselected" or schedule[day][str(hour + 1)] != "unselected":
                continue
            balance = global_first_counts.get((day, hour), 0) + global_first_counts.get((day, hour + 1), 0)
            block_candidates.append((balance + rng.random(), day, hour))
    block_candidates.sort(key=lambda item: item[0])

    pair_target = target // 2
    pairs_added = 0
    for _, day, hour in block_candidates:
        if pairs_added >= pair_target:
            break
        if (day, hour) in chosen or (day, hour + 1) in chosen:
            continue
        if can_add_work(day, hour):
            chosen.add((day, hour))
            # 두 번째 칸까지 넣었을 때 연속 4시간 제한을 다시 확인한다.
            if can_add_work(day, hour + 1):
                chosen.add((day, hour + 1))
                schedule[day][str(hour)] = "first"
                schedule[day][str(hour + 1)] = "first"
                global_first_counts[(day, hour)] = global_first_counts.get((day, hour), 0) + 1
                global_first_counts[(day, hour + 1)] = global_first_counts.get((day, hour + 1), 0) + 1
                pairs_added += 1
            else:
                chosen.remove((day, hour))

    # 목표 시간이 홀수이거나 일부 블록을 만들지 못한 경우 균형이 가장 좋은 단일 시간을 채운다.
    candidates = [slot for slot in active_slots if schedule[slot[0]][str(slot[1])] == "unselected" and slot not in chosen]
    candidates.sort(key=lambda slot: (global_first_counts.get(slot, 0), rng.random()))
    for day, hour in candidates:
        if len(chosen) >= target:
            break
        if can_add_work(day, hour):
            chosen.add((day, hour))
            schedule[day][str(hour)] = "first"
            global_first_counts[(day, hour)] = global_first_counts.get((day, hour), 0) + 1

    # 2·3순위는 예비 시간으로 넉넉하게 주되 연속 가능시간 4시간 규칙은 유지한다.
    def max_consecutive_if(day: str, hour: int, status: str) -> int:
        current = maximum = 0
        for h in HOURS:
            value = status if h == hour else schedule[day][str(h)]
            if value in {"first", "second", "third"}:
                current += 1
                maximum = max(maximum, current)
            else:
                current = 0
        return maximum

    remaining = [slot for slot in active_slots if schedule[slot[0]][str(slot[1])] == "unselected"]
    rng.shuffle(remaining)
    for day, hour in remaining:
        r = rng.random()
        if r < 0.34:
            status = "second"
        elif r < 0.56:
            status = "third"
        else:
            continue
        if max_consecutive_if(day, hour, status) <= 4:
            schedule[day][str(hour)] = status

    return schedule


def generate_dummy_students(total: int = 40) -> int:
    if total < 6 or total > 50:
        raise ValueError("더미 학생 수는 6명 이상 50명 이하로 생성할 수 있습니다.")
    # 공개 소스/배포본에는 실제 학생정보를 넣지 않고 완전한 가상 계정만 생성합니다.
    rows = []
    for index in range(total):
        name = f"더미학생{index + 1:02d}"
        student_no = f"DUMMY{index + 1:03d}"
        rows.append({
            "name": name,
            "student_no": student_no,
            "work_type": "A" if index % 2 == 0 else "B",
            "active": "1",
        })
    sync_students(rows, deactivate_missing=True)

    with SessionLocal() as session:
        students = session.scalars(select(Student).where(Student.active.is_(True)).order_by(Student.student_no)).all()
        session.execute(delete(ScheduleRun))
        now = utcnow()
        global_first_counts: dict[tuple[str, int], int] = {}
        for index, student in enumerate(students):
            schedule_data = _dummy_schedule(
                seed=20260808 + index * 137,
                work_type=student.work_type or "B",
                global_first_counts=global_first_counts,
            )
            schedule = session.scalar(select(Schedule).where(Schedule.student_id == student.id))
            if schedule is None:
                schedule = Schedule(
                    student_id=student.id,
                    schedule_json=json.dumps(schedule_data, ensure_ascii=False),
                    state="submitted",
                    saved_at=now,
                    submitted_at=now,
                )
                session.add(schedule)
            else:
                schedule.schedule_json = json.dumps(schedule_data, ensure_ascii=False)
                schedule.state = "submitted"
                schedule.saved_at = now
                schedule.submitted_at = now
            session.add(ScheduleRevision(
                student_id=student.id,
                schedule_json=json.dumps(schedule_data, ensure_ascii=False),
                state="submitted",
                created_at=now,
            ))
        session.commit()
    return total

def scheduler_students() -> list[dict]:
    """자동배정에는 활성 + 최종제출 + 유형확정 학생만 전달합니다."""
    with SessionLocal() as session:
        students = session.scalars(select(Student).where(Student.active.is_(True)).order_by(Student.name)).all()
        result = []
        for student in students:
            schedule = session.scalar(select(Schedule).where(Schedule.student_id == student.id))
            if schedule is None or schedule.state != "submitted" or student.work_type not in {"A", "B"}:
                continue
            result.append({
                "id": student.id,
                "name": student.name,
                "student_no": student.student_no,
                "work_type": student.work_type,
                "schedule": json.loads(schedule.schedule_json),
            })
        return result


def save_schedule_run(data: dict) -> dict:
    now = utcnow()
    with SessionLocal() as session:
        row = ScheduleRun(
            full_schedule_json=json.dumps(data["full_schedule"], ensure_ascii=False),
            desk_schedule_json=json.dumps(data["desk_schedule"], ensure_ascii=False),
            student_summary_json=json.dumps(data.get("student_summary", []), ensure_ascii=False),
            summary_json=json.dumps(data.get("summary", {}), ensure_ascii=False),
            created_at=now,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"id": row.id, "created_at": row.created_at.isoformat(), **data}


def latest_schedule_run() -> dict | None:
    with SessionLocal() as session:
        row = session.scalar(select(ScheduleRun).order_by(ScheduleRun.id.desc()))
        if row is None:
            return None
        return {
            "id": row.id,
            "created_at": row.created_at.isoformat(),
            "full_schedule": json.loads(row.full_schedule_json),
            "desk_schedule": json.loads(row.desk_schedule_json),
            "student_summary": json.loads(row.student_summary_json),
            "summary": json.loads(row.summary_json),
        }
