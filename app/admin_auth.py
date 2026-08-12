from __future__ import annotations

import csv
import os
from pathlib import Path

from app.config import ADMINS_CSV

_TRUE_VALUES = {"1", "true", "yes", "y", "on", "활성"}


def _is_active(value: str | None) -> bool:
    if value is None or not str(value).strip():
        return True
    return str(value).strip().lower() in _TRUE_VALUES


def load_admin_credentials() -> list[tuple[str, str]]:
    """관리자 계정 목록을 읽는다.

    우선 data/admins.csv를 사용하고, 파일이 없거나 활성 계정이 하나도 없으면
    기존 환경변수 ADMIN_ID/ADMIN_PASSWORD, ADMIN2_ID/ADMIN2_PASSWORD를 fallback으로 사용한다.
    CSV는 로그인 때마다 다시 읽으므로 파일 수정 후 서버 재시작이 필요 없다.
    """
    credentials: list[tuple[str, str]] = []

    path = Path(ADMINS_CSV)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                fields = {str(field).strip() for field in (reader.fieldnames or []) if field}
                if {"user_id", "password"}.issubset(fields):
                    seen: set[str] = set()
                    for row in reader:
                        user_id = str(row.get("user_id", "")).strip()
                        password = str(row.get("password", ""))
                        if not user_id or not password or not _is_active(row.get("active")):
                            continue
                        if user_id in seen:
                            continue
                        seen.add(user_id)
                        credentials.append((user_id, password))
        except (OSError, csv.Error):
            credentials = []

    if credentials:
        return credentials

    # CSV를 사용할 수 없는 경우에만 환경변수 방식으로 fallback.
    env_pairs = [
        (os.getenv("ADMIN_ID", "").strip(), os.getenv("ADMIN_PASSWORD", "")),
        (os.getenv("ADMIN2_ID", "").strip(), os.getenv("ADMIN2_PASSWORD", "")),
    ]
    return [(user_id, password) for user_id, password in env_pairs if user_id and password]


def admin_id_is_active(user_id: str) -> bool:
    return any(configured_id == user_id for configured_id, _ in load_admin_credentials())
