from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
STATIC_DIR = Path(__file__).resolve().parent / "static"
USERS_CSV = DATA_DIR / "users.csv"
_ADMINS_CSV_ENV = os.getenv("ADMINS_CSV_PATH", "").strip()
_RENDER_ADMINS_SECRET = Path("/etc/secrets/admins.csv")
if _ADMINS_CSV_ENV:
    ADMINS_CSV = Path(_ADMINS_CSV_ENV)
elif _RENDER_ADMINS_SECRET.exists():
    ADMINS_CSV = _RENDER_ADMINS_SECRET
else:
    ADMINS_CSV = DATA_DIR / "admins.csv"

APP_TITLE = "도서관 근로학생 시간표 자동 생성기"
DAYS = ["월", "화", "수", "목", "금", "토"]
HOURS = list(range(9, 22))
SATURDAY_ACTIVE_HOURS = set(range(9, 15))

STATUS_UNSELECTED = "unselected"
STATUS_FIRST = "first"
STATUS_SECOND = "second"
STATUS_THIRD = "third"
STATUS_IMPOSSIBLE = "impossible"
STATUS_CLASS = "class"
STATUS_CLOSED = "closed"

EDITABLE_STATUSES = {
    STATUS_UNSELECTED,
    STATUS_FIRST,
    STATUS_SECOND,
    STATUS_THIRD,
    STATUS_IMPOSSIBLE,
    STATUS_CLASS,
}
WORK_AVAILABLE_STATUSES = {STATUS_FIRST, STATUS_SECOND, STATUS_THIRD}
MAX_CONSECUTIVE_AVAILABLE = 4

# 근로유형별 월/주 권장 범위.
# 주 기준은 학교에서 월 최소·최대 시간을 4주로 나누어 시간표 작성 시 안내하는 값이며,
# 최종 제출을 차단하는 강제 조건이 아니라 경고 기준으로 사용한다.
WORK_TYPE_LIMITS = {
    "A": {"monthly_min": 56, "monthly_max": 80, "weekly_min": 14, "weekly_max": 20},
    "B": {"monthly_min": 28, "monthly_max": 40, "weekly_min": 7, "weekly_max": 10},
}

STATUS_META = {
    STATUS_UNSELECTED: {"label": "미선택", "tool": "선택 지우기", "color": "#E4E8EE", "text": "#526174"},
    STATUS_FIRST: {"label": "1순위", "tool": "1순위 희망", "color": "#D8F5E5", "text": "#146C3A"},
    STATUS_SECOND: {"label": "2순위", "tool": "2순위 가능", "color": "#D9E8FF", "text": "#1E56A8"},
    STATUS_THIRD: {"label": "3순위", "tool": "3순위 가능", "color": "#FFF0BF", "text": "#765500"},
    STATUS_IMPOSSIBLE: {"label": "불가능", "tool": "절대 불가능", "color": "#FFDCDC", "text": "#A12626"},
    STATUS_CLASS: {"label": "수업", "tool": "정규 수업", "color": "#566173", "text": "#FFFFFF"},
    STATUS_CLOSED: {"label": "운영 안 함", "tool": "운영 안 함", "color": "#2F3744", "text": "#D8DEE8"},
}

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    DATABASE_URL = f"sqlite:///{(DATA_DIR / 'app.db').as_posix()}"
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

SESSION_SECRET = os.getenv("SESSION_SECRET", "local-development-secret-change-me")
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"
