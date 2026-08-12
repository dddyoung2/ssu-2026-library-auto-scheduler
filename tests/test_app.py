import io
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SESSION_SECRET"] = "test-secret"
os.environ["ADMIN_ID"] = "admin01"
os.environ["ADMIN_PASSWORD"] = "Admin1234!"
os.environ["ADMIN2_ID"] = "admin02"
os.environ["ADMIN2_PASSWORD"] = "Admin2345!"

from fastapi.testclient import TestClient
from app.database import Base, engine, sync_students
from app.main import app


def reset_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def build_schedule():
    from app.validators import default_schedule
    return default_schedule()


def login_admin(client, user_id="admin01", password="Admin1234!"):
    response = client.post("/login/admin", data={"user_id": user_id, "password": password}, follow_redirects=False)
    assert response.status_code == 303


def seed_student(name="테스트학생", student_no="20260001", work_type="A"):
    sync_students([
        {"name": name, "student_no": student_no, "work_type": work_type, "active": "1"}
    ])


def test_initial_database_has_no_student_login_and_second_admin_works():
    reset_db()
    with TestClient(app) as client:
        response = client.post("/login/student", data={"name": "아무학생", "student_no": "20260000"}, follow_redirects=False)
        assert response.status_code == 401
        assert "등록된 근로학생 명단이 없습니다" in response.text
        login_admin(client, "admin02", "Admin2345!")


def test_admin_can_add_edit_and_deactivate_student():
    reset_db()
    with TestClient(app) as client:
        login_admin(client)
        created = client.post(
            "/api/admin/students",
            json={"name": "김학생", "student_no": "20260001", "work_type": "", "active": True},
        )
        assert created.status_code == 200
        student_id = created.json()["student_id"]

        client.post("/logout")
        login = client.post("/login/student", data={"name": "김학생", "student_no": "20260001"}, follow_redirects=False)
        assert login.status_code == 303
        client.post("/logout")

        login_admin(client)
        edited = client.put(
            f"/api/admin/students/{student_id}",
            json={"name": "김수정", "student_no": "20260099", "work_type": "B", "active": False},
        )
        assert edited.status_code == 200
        client.post("/logout")
        blocked = client.post("/login/student", data={"name": "김수정", "student_no": "20260099"}, follow_redirects=False)
        assert blocked.status_code == 401


def test_csv_merge_and_sync_modes():
    reset_db()
    with TestClient(app) as client:
        login_admin(client)
        merge_csv = "name,student_no,work_type,active\n학생A,20260001,A,1\n학생B,20260002,B,1\n"
        response = client.post(
            "/api/admin/import-users",
            data={"mode": "merge"},
            files={"file": ("students.csv", merge_csv.encode("utf-8"), "text/csv")},
        )
        assert response.status_code == 200
        assert response.json()["count"] == 2

        sync_csv = "name,student_no,work_type,active\n학생A수정,20260001,A,1\n"
        response = client.post(
            "/api/admin/import-users",
            data={"mode": "sync"},
            files={"file": ("students.csv", sync_csv.encode("utf-8"), "text/csv")},
        )
        assert response.status_code == 200
        students = client.get("/api/admin/students").json()["students"]
        assert len(students) == 2
        assert next(item for item in students if item["student_no"] == "20260001")["active"] is True
        assert next(item for item in students if item["student_no"] == "20260002")["active"] is False


def test_student_weekly_warning_and_save():
    reset_db()
    with TestClient(app) as client:
        seed_student("테스트학생", "20260001", "A")
        response = client.post("/login/student", data={"name": "테스트학생", "student_no": "20260001"}, follow_redirects=False)
        assert response.status_code == 303
        schedule = build_schedule()
        for hour in range(9, 13):
            schedule["월"][str(hour)] = "first"
        saved = client.put("/api/me/schedule", json={"schedule": schedule, "state": "submitted"})
        assert saved.status_code == 200
        assert saved.json()["state"] == "submitted"
        assert saved.json()["warnings"]
        assert "월 최소 근로시간 56시간" in saved.json()["warnings"][0]


def test_reject_five_consecutive():
    reset_db()
    with TestClient(app) as client:
        seed_student("테스트학생", "20260001", "A")
        client.post("/login/student", data={"name": "테스트학생", "student_no": "20260001"})
        schedule = build_schedule()
        for hour in range(9, 14):
            schedule["월"][str(hour)] = "second"
        response = client.put("/api/me/schedule", json={"schedule": schedule, "state": "draft"})
        assert response.status_code == 422
        assert "최대 연속 근로" in response.json()["detail"]


def test_full_schedule_is_blocked_until_all_active_students_submit():
    reset_db()
    with TestClient(app) as client:
        login_admin(client)
        client.post("/api/admin/students", json={"name": "학생A", "student_no": "20260001", "work_type": "A", "active": True})
        client.post("/api/admin/students", json={"name": "학생B", "student_no": "20260002", "work_type": "B", "active": True})
        response = client.post("/api/admin/demo/generate-full", json={"min_staff": 1})
        assert response.status_code == 422
        assert "전원 최종 제출" in response.json()["detail"]


def test_dummy_full_schedule_preserves_first_choice_targets_and_desk_settings():
    reset_db()
    with TestClient(app) as client:
        login_admin(client)
        generated = client.post("/api/admin/demo/generate-students")
        assert generated.status_code == 200
        assert generated.json()["count"] == 40

        students = client.get("/api/admin/students").json()["students"]
        assert students[0]["name"].startswith("더미학생")
        assert all(not item["student_no"].startswith("2022") for item in students)

        full_response = client.post("/api/admin/demo/generate-full", json={"min_staff": 5})
        assert full_response.status_code == 200, full_response.text
        full_run = full_response.json()["run"]
        assert full_run["summary"]["full_min_staff"] >= 5
        assert all(item["target_hours"] == item["full_hours"] for item in full_run["student_summary"])

        desk_response = client.post(
            "/api/admin/demo/generate-desk",
            json={
                "weekly_max_a": 8,
                "weekly_max_b": 4,
                "daily_max": 2,
                "two_person_slots": ["월:20", "월:21", "금:20", "금:21"],
            },
        )
        assert desk_response.status_code == 200, desk_response.text
        run = desk_response.json()["run"]
        assert run["summary"]["desk_settings"]["weekly_max_a"] == 8
        assert run["summary"]["desk_settings"]["weekly_max_b"] == 4
        by_type = {item["student_no"]: item for item in run["student_summary"]}
        assert all(item["desk_hours"] <= (8 if item["work_type"] == "A" else 4) for item in by_type.values())
        assert len(run["desk_schedule"]["월"]["20"]) <= 2
        assert len(run["desk_schedule"]["월"]["21"]) <= 2

        excel = client.get("/api/admin/demo/export.xlsx")
        assert excel.status_code == 200
        assert len(excel.content) > 1000


def test_admin_page_has_no_submission_csv_button_and_empty_message_has_no_active_word():
    reset_db()
    with TestClient(app) as client:
        login_admin(client)
        page = client.get('/admin')
        assert page.status_code == 200
        assert '제출파일 CSV 다운로드' not in page.text
        js = open('app/static/admin.js', encoding='utf-8').read()
        assert '등록된 근로학생이 없습니다.' in js
        assert '등록된 활성 근로학생이 없습니다.' not in js


def test_admin_credentials_csv_has_two_default_accounts():
    from app.admin_auth import load_admin_credentials
    credentials = dict(load_admin_credentials())
    assert credentials.get('admin01') == 'Admin1234!'
    assert credentials.get('admin02') == 'Admin2345!'


def test_student_access_window_locks_login_outside_period_and_allows_inside_period():
    reset_db()
    with TestClient(app) as client:
        seed_student("기간학생", "20260111", "A")
        login_admin(client)
        future = client.put(
            "/api/admin/student-access",
            json={"start_at": "2099-01-01T09:00", "end_at": "2099-01-02T23:59"},
        )
        assert future.status_code == 200
        assert future.json()["is_open"] is False
        client.post("/logout")
        blocked = client.post("/login/student", data={"name": "기간학생", "student_no": "20260111"}, follow_redirects=False)
        assert blocked.status_code == 423
        assert "입력은" in blocked.text

        login_admin(client)
        cleared = client.delete("/api/admin/student-access")
        assert cleared.status_code == 200
        assert cleared.json()["is_open"] is True
        client.post("/logout")
        allowed = client.post("/login/student", data={"name": "기간학생", "student_no": "20260111"}, follow_redirects=False)
        assert allowed.status_code == 303


def test_admin_can_view_schedule_anytime_but_edit_only_when_student_access_locked():
    reset_db()
    with TestClient(app) as client:
        seed_student("수정학생", "20260222", "A")
        client.post("/login/student", data={"name": "수정학생", "student_no": "20260222"})
        schedule = build_schedule()
        schedule["월"]["9"] = "first"
        saved = client.put("/api/me/schedule", json={"schedule": schedule, "state": "submitted"})
        assert saved.status_code == 200
        client.post("/logout")

        login_admin(client)
        students = client.get("/api/admin/students").json()["students"]
        student_id = next(item["id"] for item in students if item["student_no"] == "20260222")
        viewed = client.get(f"/api/admin/students/{student_id}/schedule")
        assert viewed.status_code == 200
        assert viewed.json()["schedule"]["월"]["9"] == "first"

        edited_schedule = viewed.json()["schedule"]
        edited_schedule["월"]["9"] = "second"
        blocked = client.put(
            f"/api/admin/students/{student_id}/schedule",
            json={"schedule": edited_schedule, "state": "submitted"},
        )
        assert blocked.status_code == 409

        locked = client.post("/api/admin/student-access/lock")
        assert locked.status_code == 200
        assert locked.json()["is_open"] is False
        edited = client.put(
            f"/api/admin/students/{student_id}/schedule",
            json={"schedule": edited_schedule, "state": "submitted"},
        )
        assert edited.status_code == 200
        assert edited.json()["schedule"]["월"]["9"] == "second"
        assert edited.json()["edited_by"] == "admin01"

        reread = client.get(f"/api/admin/students/{student_id}/schedule")
        assert reread.json()["schedule"]["월"]["9"] == "second"


def test_admin_schedule_popup_and_access_controls_exist_in_admin_page():
    reset_db()
    with TestClient(app) as client:
        login_admin(client)
        page = client.get("/admin")
        assert page.status_code == 200
        assert "학생 시간표 작성 가능 기간" in page.text
        assert "studentScheduleModal" in page.text
        assert "관리자 수정 저장" in page.text
        assert "시간표</th>" in page.text
