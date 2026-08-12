from __future__ import annotations

import csv
import io
import secrets
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from app.config import (
    APP_TITLE,
    COOKIE_SECURE,
    DAYS,
    HOURS,
    MAX_CONSECUTIVE_AVAILABLE,
    SESSION_SECRET,
    STATIC_DIR,
    STATUS_META,
    TEMPLATES_DIR,
    WORK_TYPE_LIMITS,
)
from app.admin_auth import admin_id_is_active, load_admin_credentials
from app.database import (
    active_student_count,
    admin_students,
    authenticate_student,
    create_student,
    generate_dummy_students,
    get_student,
    get_student_schedule,
    init_database,
    latest_schedule_run,
    save_schedule_run,
    save_student_schedule,
    schedule_generation_readiness,
    student_access_status,
    set_student_access_window,
    lock_student_access,
    clear_student_access_window,
    scheduler_students,
    sync_students,
    update_student,
    update_work_type,
)
from app.demo_scheduler import build_demo_schedules, build_desk_from_full, build_full_demo
from app.exports import build_demo_workbook
from app.validators import default_schedule, validate_schedule, weekly_first_choice_warnings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=COOKIE_SECURE,
    max_age=60 * 60 * 8,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


class SchedulePayload(BaseModel):
    schedule: dict
    state: Literal["draft", "submitted"]


class WorkTypePayload(BaseModel):
    work_type: str


class StudentCreatePayload(BaseModel):
    name: str
    student_no: str
    work_type: str = ""
    active: bool = True


class StudentUpdatePayload(BaseModel):
    name: str
    student_no: str
    work_type: str = ""
    active: bool = True


class FullScheduleSettings(BaseModel):
    min_staff: int = 5


class DeskScheduleSettings(BaseModel):
    weekly_max_a: int
    weekly_max_b: int
    daily_max: int
    two_person_slots: list[str] = []


class StudentAccessWindowPayload(BaseModel):
    start_at: str
    end_at: str


class AdminSchedulePayload(BaseModel):
    schedule: dict
    state: Literal["draft", "submitted"]


def current_student_id(request: Request) -> int:
    student_id = request.session.get("student_id")
    if not isinstance(student_id, int):
        raise HTTPException(status_code=401, detail="학생 로그인이 필요합니다.")
    if not student_access_status()["is_open"]:
        request.session.clear()
        raise HTTPException(status_code=423, detail="학생 시간표 입력 기간이 종료되어 현재 수정할 수 없습니다.")
    return student_id


def require_admin(request: Request) -> None:
    admin_id = request.session.get("admin_id")
    if request.session.get("admin") is not True or not isinstance(admin_id, str) or not admin_id_is_active(admin_id):
        request.session.clear()
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")


def authenticate_admin(user_id: str, password: str) -> str | None:
    # data/admins.csv를 로그인할 때마다 다시 읽으므로 파일 수정이 즉시 다음 로그인에 반영됩니다.
    for configured_id, configured_password in load_admin_credentials():
        if secrets.compare_digest(user_id, configured_id) and secrets.compare_digest(password, configured_password):
            return configured_id
    return None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    if request.session.get("student_id"):
        return RedirectResponse("/student", status_code=303)
    if request.session.get("admin"):
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"title": APP_TITLE, "student_access": student_access_status()})


@app.post("/login/student")
def student_login(request: Request, name: str = Form(...), student_no: str = Form(...)):
    access = student_access_status()
    if not access["is_open"]:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": APP_TITLE, "student_error": access["message"], "student_access": access},
            status_code=423,
        )
    student = authenticate_student(name, student_no)
    if student is None:
        if active_student_count() == 0:
            message = "아직 등록된 근로학생 명단이 없습니다. 담당자가 명단을 등록한 뒤 로그인해 주세요."
        else:
            message = "등록된 근로학생 정보와 일치하지 않습니다. 이름과 학번을 확인해 주세요."
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": APP_TITLE, "student_error": message, "student_access": access},
            status_code=401,
        )
    request.session.clear()
    request.session["student_id"] = student.id
    return RedirectResponse("/student", status_code=303)


@app.post("/login/admin")
def admin_login(request: Request, user_id: str = Form(...), password: str = Form(...)):
    matched_admin = authenticate_admin(user_id.strip(), password)
    if matched_admin is None:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": APP_TITLE, "admin_error": "관리자 아이디 또는 비밀번호가 올바르지 않습니다."},
            status_code=401,
        )
    request.session.clear()
    request.session["admin"] = True
    request.session["admin_id"] = matched_admin
    return RedirectResponse("/admin", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/student", response_class=HTMLResponse)
def student_page(request: Request):
    if not student_access_status()["is_open"]:
        request.session.clear()
        return RedirectResponse("/", status_code=303)
    student_id = current_student_id(request)
    student = get_student(student_id)
    if student is None or not student.active:
        request.session.clear()
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "student.html",
        {
            "title": APP_TITLE,
            "student": student,
            "days": DAYS,
            "hours": HOURS,
            "status_meta": STATUS_META,
            "max_consecutive": MAX_CONSECUTIVE_AVAILABLE,
            "work_type_limits": WORK_TYPE_LIMITS,
        },
    )


@app.get("/api/me/schedule")
def api_get_schedule(request: Request):
    student_id = current_student_id(request)
    student = get_student(student_id)
    if student is None or not student.active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="현재 활성화된 근로학생 계정이 아닙니다.")
    record = get_student_schedule(student_id)
    if record is None:
        record = {"schedule": default_schedule(), "state": "not_started", "saved_at": None, "submitted_at": None}
    return {**record, "work_type": student.work_type}


@app.put("/api/me/work-type")
def api_me_work_type(request: Request, payload: WorkTypePayload):
    student_id = current_student_id(request)
    student = get_student(student_id)
    if student is None or not student.active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="현재 활성화된 근로학생 계정이 아닙니다.")
    try:
        update_work_type(student_id, payload.work_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "work_type": payload.work_type.strip().upper()}


@app.put("/api/me/schedule")
def api_save_schedule(request: Request, payload: SchedulePayload):
    student_id = current_student_id(request)
    student = get_student(student_id)
    if student is None or not student.active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="현재 활성화된 근로학생 계정이 아닙니다.")
    if payload.state == "submitted" and student.work_type not in {"A", "B"}:
        raise HTTPException(status_code=422, detail="최종 제출 전에 근로유형 A 또는 B를 선택해 주세요.")
    try:
        schedule = validate_schedule(payload.schedule)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    warnings = weekly_first_choice_warnings(schedule, student.work_type) if payload.state == "submitted" else []
    meta = save_student_schedule(student_id, schedule, payload.state)
    return {"ok": True, **meta, "schedule": schedule, "work_type": student.work_type, "warnings": warnings}


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request):
    require_admin(request)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "title": APP_TITLE,
            "days": DAYS,
            "hours": HOURS,
            "admin_id": request.session.get("admin_id", "관리자"),
            "status_meta": STATUS_META,
        },
    )


@app.get("/api/admin/students")
def api_admin_students(request: Request):
    require_admin(request)
    return {"students": admin_students(), "readiness": schedule_generation_readiness()}




@app.get("/api/admin/student-access")
def api_admin_student_access(request: Request):
    require_admin(request)
    return student_access_status()


@app.put("/api/admin/student-access")
def api_admin_set_student_access(request: Request, payload: StudentAccessWindowPayload):
    require_admin(request)
    try:
        return set_student_access_window(payload.start_at, payload.end_at)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/admin/student-access/lock")
def api_admin_lock_student_access(request: Request):
    require_admin(request)
    return lock_student_access()


@app.delete("/api/admin/student-access")
def api_admin_clear_student_access(request: Request):
    require_admin(request)
    return clear_student_access_window()


@app.get("/api/admin/students/{student_id}/schedule")
def api_admin_get_student_schedule(request: Request, student_id: int):
    require_admin(request)
    student = get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    record = get_student_schedule(student_id)
    if record is None:
        record = {"schedule": default_schedule(), "state": "not_started", "saved_at": None, "submitted_at": None}
    return {
        **record,
        "student": {
            "id": student.id,
            "name": student.name,
            "student_no": student.student_no,
            "work_type": student.work_type,
            "active": student.active,
        },
        "student_access": student_access_status(),
    }


@app.put("/api/admin/students/{student_id}/schedule")
def api_admin_update_student_schedule(request: Request, student_id: int, payload: AdminSchedulePayload):
    require_admin(request)
    access = student_access_status()
    if access["is_open"]:
        raise HTTPException(status_code=409, detail="학생 입력기간 중에는 관리자 수정이 잠겨 있습니다. 입력기간 종료 후 수정해 주세요.")
    student = get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    try:
        schedule = validate_schedule(payload.schedule)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    state = payload.state if payload.state in {"draft", "submitted"} else "draft"
    admin_id = str(request.session.get("admin_id", "관리자"))
    meta = save_student_schedule(
        student_id,
        schedule,
        state,
        actor_type="admin",
        actor_id=admin_id,
    )
    return {"ok": True, **meta, "schedule": schedule, "edited_by": admin_id}


@app.post("/api/admin/students")
def api_create_student(request: Request, payload: StudentCreatePayload):
    require_admin(request)
    try:
        student_id = create_student(payload.name, payload.student_no, payload.work_type, payload.active)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "student_id": student_id}


@app.put("/api/admin/students/{student_id}")
def api_update_student(request: Request, student_id: int, payload: StudentUpdatePayload):
    require_admin(request)
    try:
        update_student(student_id, payload.name, payload.student_no, payload.work_type, payload.active)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@app.put("/api/admin/students/{student_id}/work-type")
def api_update_work_type(request: Request, student_id: int, payload: WorkTypePayload):
    require_admin(request)
    try:
        update_work_type(student_id, payload.work_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/admin/import-users")
async def api_import_users(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Form("merge"),
):
    require_admin(request)
    if mode not in {"merge", "sync"}:
        raise HTTPException(status_code=400, detail="명단 반영 방식이 올바르지 않습니다.")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="CSV 파일만 업로드할 수 있습니다.")
    content = await file.read()
    if len(content) > 2_000_000:
        raise HTTPException(status_code=400, detail="파일이 너무 큽니다.")
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {"name", "student_no", "work_type", "active"}
        if not reader.fieldnames or not required.issubset({field.strip() for field in reader.fieldnames if field}):
            raise ValueError("CSV 열은 name, student_no, work_type, active가 필요합니다.")
        rows = list(reader)
        if mode == "sync" and not any(str(row.get("student_no", "")).strip() for row in rows):
            raise ValueError("전체 명단 동기화에는 학생이 1명 이상 포함되어야 합니다.")
        count = sync_students(rows, deactivate_missing=(mode == "sync"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "count": count, "mode": mode}


@app.post("/api/admin/demo/generate-students")
def api_generate_dummy_students(request: Request):
    require_admin(request)
    try:
        count = generate_dummy_students(40)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "count": count}


@app.post("/api/admin/demo/generate-full")
def api_generate_full_schedule(request: Request, payload: FullScheduleSettings):
    require_admin(request)
    readiness = schedule_generation_readiness()
    if readiness["active_count"] == 0:
        raise HTTPException(status_code=422, detail="먼저 근로학생 명단을 등록해 주세요.")
    if not readiness["ready"]:
        parts = []
        if readiness["not_submitted"]:
            names = ", ".join(readiness["not_submitted"][:6])
            more = len(readiness["not_submitted"]) - 6
            parts.append(f"최종 미제출 {len(readiness['not_submitted'])}명({names}{f' 외 {more}명' if more > 0 else ''})")
        if readiness["untyped"]:
            parts.append(f"근로유형 미지정 {len(readiness['untyped'])}명")
        raise HTTPException(status_code=422, detail="전원 최종 제출 후 생성할 수 있습니다. " + " / ".join(parts))
    students = scheduler_students()
    if len(students) < payload.min_staff:
        raise HTTPException(status_code=422, detail="설정한 최소 인원보다 학생 수가 적습니다.")
    try:
        result = build_full_demo(students, min_staff=payload.min_staff)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "run": save_schedule_run(result)}


@app.post("/api/admin/demo/generate-desk")
def api_generate_desk_schedule(request: Request, payload: DeskScheduleSettings):
    require_admin(request)
    students = scheduler_students()
    latest = latest_schedule_run()
    if latest is None or not latest.get("full_schedule"):
        raise HTTPException(status_code=422, detail="먼저 전체 시간표를 생성해 주세요.")
    try:
        result = build_desk_from_full(
            students,
            latest,
            weekly_max_a=payload.weekly_max_a,
            weekly_max_b=payload.weekly_max_b,
            daily_max=payload.daily_max,
            two_person_slots=payload.two_person_slots,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "run": save_schedule_run(result)}


@app.post("/api/admin/demo/generate-schedules")
def api_generate_demo_schedules(request: Request):
    """v4.2 호환용 기존 데모 엔드포인트."""
    require_admin(request)
    students = scheduler_students()
    if len(students) < 5:
        raise HTTPException(status_code=422, detail="먼저 더미데이터를 생성해 주세요.")
    try:
        result = build_demo_schedules(students)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "run": save_schedule_run(result)}


@app.get("/api/admin/demo/latest")
def api_latest_demo(request: Request):
    require_admin(request)
    return {"run": latest_schedule_run()}


@app.get("/api/admin/demo/export.xlsx")
def api_export_demo_excel(request: Request):
    require_admin(request)
    run = latest_schedule_run()
    if run is None:
        raise HTTPException(status_code=404, detail="먼저 데모 시간표를 생성해 주세요.")
    data = build_demo_workbook(run)
    return StreamingResponse(
        iter([data]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="library_demo_schedules.xlsx"'},
    )



@app.exception_handler(HTTPException)
def http_exception_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
    return templates.TemplateResponse(request, "error.html", {"title": APP_TITLE, "message": exc.detail}, status_code=exc.status_code)
