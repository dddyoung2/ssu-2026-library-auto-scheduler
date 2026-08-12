from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from app.config import DAYS
from app.demo_scheduler import active_hours

HEADER_GREEN = "A9D18E"
TIME_GREEN = "E2EFD8"
TITLE_TEXT = "1F2937"
GRID_COLOR = "525B66"
CLOSED_FILL = "D9DEE6"


def _write_schedule_sheet(workbook: Workbook, sheet_name: str, title: str, schedule: dict, *, desk: bool = False) -> None:
    ws = workbook.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False

    # 사진과 비슷하게 제목 → 안내문 → 요일 헤더 → 시간표 순서로 구성한다.
    ws.merge_cells("A1:G2")
    ws["A1"] = title
    ws["A1"].font = Font(name="맑은 고딕", size=20, bold=True, color=TITLE_TEXT)
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A3:G3")
    ws["A3"] = "※ 자동 배정 결과입니다. 실제 운영 전 담당자가 최종 확인해 주세요."
    ws["A3"].font = Font(name="맑은 고딕", size=9, color="5E6670")
    ws["A3"].alignment = Alignment(horizontal="center", vertical="center")

    headers = ["", *DAYS]
    for col, value in enumerate(headers, start=1):
        cell = ws.cell(row=4, column=col, value=value)
        cell.fill = PatternFill("solid", fgColor=HEADER_GREEN)
        cell.font = Font(name="맑은 고딕", bold=True, size=11)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    thin = Side(style="thin", color=GRID_COLOR)
    medium = Side(style="medium", color=GRID_COLOR)
    all_hours = list(range(9, 22))
    for row_index, hour in enumerate(all_hours, start=5):
        time_cell = ws.cell(row=row_index, column=1, value=f"{hour}:00")
        time_cell.fill = PatternFill("solid", fgColor=TIME_GREEN)
        time_cell.font = Font(name="맑은 고딕", bold=True, size=10)
        time_cell.alignment = Alignment(horizontal="center", vertical="center")
        for day_index, day in enumerate(DAYS, start=2):
            cell = ws.cell(row=row_index, column=day_index)
            if hour not in active_hours(day):
                cell.value = ""
                cell.fill = PatternFill("solid", fgColor=CLOSED_FILL)
            else:
                people = schedule.get(day, {}).get(str(hour), []) if schedule else []
                # 첨부 예시처럼 이름 중심으로 간결하게 표시한다.
                names = [person["name"] for person in people]
                if desk:
                    cell.value = " ".join(names)
                else:
                    # 전체 시간표는 인원이 많아질 수 있어 3~4명 단위로 줄바꿈한다.
                    chunks = [" ".join(names[i:i + 4]) for i in range(0, len(names), 4)]
                    cell.value = "\n".join(chunks)
            cell.font = Font(name="맑은 고딕", size=9)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    max_row = 4 + len(all_hours)
    for row in ws.iter_rows(min_row=4, max_row=max_row, min_col=1, max_col=7):
        for cell in row:
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    # 바깥 테두리를 조금 더 굵게 보이도록 한다.
    for col in range(1, 8):
        ws.cell(4, col).border = Border(top=medium, left=thin, right=thin, bottom=thin)
        ws.cell(max_row, col).border = Border(bottom=medium, left=thin, right=thin, top=thin)
    for row in range(4, max_row + 1):
        ws.cell(row, 1).border = Border(left=medium, right=thin, top=thin, bottom=thin)
        ws.cell(row, 7).border = Border(right=medium, left=thin, top=thin, bottom=thin)

    ws.column_dimensions["A"].width = 12
    for index in range(2, 8):
        ws.column_dimensions[get_column_letter(index)].width = 24 if desk else 29
    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 16
    ws.row_dimensions[3].height = 20
    ws.row_dimensions[4].height = 28
    for row_index in range(5, max_row + 1):
        ws.row_dimensions[row_index].height = 44 if desk else 62

    ws.freeze_panes = "B5"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True
    ws.print_area = f"A1:G{max_row}"
    ws.sheet_properties.pageSetUpPr.autoPageBreaks = False


def build_demo_workbook(run: dict) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    _write_schedule_sheet(workbook, "전체시간표", "근로학생 전체 시간표", run.get("full_schedule") or {}, desk=False)
    _write_schedule_sheet(workbook, "데스크시간표", "안내데스크 시간표", run.get("desk_schedule") or {}, desk=True)

    ws = workbook.create_sheet("학생별요약")
    ws.append(["이름", "학번", "근로유형", "1순위 목표시간", "전체 배정시간", "데스크 배정시간"])
    for item in run.get("student_summary", []):
        ws.append([
            item["name"], item["student_no"], item["work_type"],
            item.get("target_hours", item.get("full_hours", 0)),
            item.get("full_hours", 0), item.get("desk_hours", 0),
        ])
    for cell in ws[1]:
        cell.font = Font(name="맑은 고딕", bold=True)
        cell.fill = PatternFill("solid", fgColor=HEADER_GREEN)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(horizontal="center", vertical="center")
    for width, column in zip((16, 16, 12, 17, 17, 18), "ABCDEF"):
        ws.column_dimensions[column].width = width
    ws.freeze_panes = "A2"

    info = workbook.create_sheet("생성정보")
    summary = run.get("summary", {})
    info.append(["항목", "값"])
    rows = [
        ("학생 수", summary.get("student_count", "")),
        ("전체 최소 인원 설정", summary.get("full_min_staff_setting", summary.get("full_settings", {}).get("min_staff", ""))),
        ("전체시간표 실제 최소 인원", summary.get("full_min_staff", "")),
        ("전체시간표 최대 인원", summary.get("full_max_staff", "")),
        ("2·3순위 교체 횟수", summary.get("fallback_swap_count", "")),
        ("전체 최소인원 미충족 칸", summary.get("full_shortage_count", "")),
        ("A형 주 최대 데스크", summary.get("desk_settings", {}).get("weekly_max_a", "")),
        ("B형 주 최대 데스크", summary.get("desk_settings", {}).get("weekly_max_b", "")),
        ("하루 최대 데스크", summary.get("desk_settings", {}).get("daily_max", "")),
        ("데스크 2명 허용시간", ", ".join(summary.get("desk_settings", {}).get("two_person_slots", []))),
        ("2시간 데스크 블록 수", summary.get("two_hour_blocks", "")),
        ("1시간 데스크 블록 수", summary.get("one_hour_blocks", "")),
        ("데스크 미충족 칸", summary.get("desk_shortage_count", "")),
        ("경고", "\n".join(summary.get("warnings", [])) or "없음"),
    ]
    for row in rows:
        info.append(list(row))
    for cell in info[1]:
        cell.font = Font(name="맑은 고딕", bold=True)
        cell.fill = PatternFill("solid", fgColor=HEADER_GREEN)
    info.column_dimensions["A"].width = 30
    info.column_dimensions["B"].width = 90
    for row in info.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    info.freeze_panes = "A2"

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
