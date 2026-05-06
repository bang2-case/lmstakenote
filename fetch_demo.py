"""
fetch_demo.py — Fetch lớp có buổi 14 trong khoảng ngày chỉ định
Dùng cho tính năng "Quản lý DEMO" trong LMS TakeNote.

Cơ sở:
  HCM1: Phan Xích Long, Phan Văn Trị, Tô Ký
  HCM4: Tên Lửa, Tây Thạnh, Lũy Bán Bích, Trường Chinh
"""
import requests
import json
import os
import base64
import re
from datetime import datetime, timezone, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Centre IDs
# ─────────────────────────────────────────────────────────────────────────────

DEMO_CENTRES = {
    # HCM1
    "609bf4149535070ca5e3edc0": {"name": "HCM - Phan Văn Trị",           "area": "HCM 1"},
    "62b0234675379306da49f051": {"name": "HCM - 261-263 Phan Xích Long", "area": "HCM 1"},
    "62d6dc936e356729147d7399": {"name": "HCM - 01 Tô Ký",               "area": "HCM 1"},
    # HCM4
    "62918d02af37d11e2da237e5": {"name": "HCM - Khu Tên Lửa",            "area": "HCM 4"},
    "63034f4a7d1d1e1cb14e4e57": {"name": "HCM - 322 Tây Thạnh",          "area": "HCM 4"},
    "62cc07753c1309654f472e60": {"name": "HCM - 414 Lũy Bán Bích",       "area": "HCM 4"},
    "62d6dcc16e356729147d73a6": {"name": "HCM - 01 Trường Chinh",        "area": "HCM 4"},
}

DEMO_CENTRE_IDS = list(DEMO_CENTRES.keys())
GRAPHQL_URL = "https://lms-api.mindx.edu.vn/"

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_token() -> str:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        raise RuntimeError("Không tìm thấy file .env")
    with open(env_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line.startswith("LMS_TOKEN="):
                token = line[len("LMS_TOKEN="):].strip().strip('"').strip("'")
                if token:
                    return token
    raise RuntimeError("Không tìm thấy LMS_TOKEN trong .env")


def check_token(token: str) -> dict:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {"valid": False}
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        return {"valid": exp > now, "remaining_minutes": max(0, int((exp - now) // 60))}
    except Exception:
        return {"valid": False}


def get_block(name: str) -> str:
    """Xác định khối từ tên lớp."""
    cleaned = re.sub(r'\s*\(.*?\)', '', name).strip()
    parts = cleaned.split('-')
    if len(parts) >= 2:
        code = parts[1].upper()
        if code in {"ROB", "KIND"}:
            return "Robotics"
        if code in {"XART"}:
            return "Art"
        if code in {"C4K", "JSB", "JSI", "JSA", "CSB", "CSI", "CSA"}:
            return "Coding"
    name_lower = name.lower()
    if "robotics" in name_lower or "robot" in name_lower or "kind" in name_lower:
        return "Robotics"
    if "xart" in name_lower or "art" in name_lower:
        return "Art"
    return "Coding"


def fmt_time_utc7(iso: str) -> str:
    """Format ISO time string sang HH:MM (UTC+7)."""
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        local = dt + timedelta(hours=7)
        return local.strftime("%H:%M")
    except Exception:
        return iso[11:16] if len(iso) > 15 else iso


def fmt_date_vn(date_str: str) -> str:
    """Format YYYY-MM-DD sang DD/MM/YYYY."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return date_str[:10]


def day_of_week_vn(date_str: str) -> str:
    """Trả về tên thứ tiếng Việt."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        return days[dt.weekday()]
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# GraphQL query — chỉ lấy fields cần thiết, không lấy studentAttendance
# ─────────────────────────────────────────────────────────────────────────────

DEMO_QUERY = """query GetClasses($centres: [String], $haveSlotFrom: Date, $haveSlotTo: Date, $pageIndex: Int!, $itemsPerPage: Int!) {
  classes(payload: {
    centre_in: $centres,
    haveSlot_from: $haveSlotFrom,
    haveSlot_to: $haveSlotTo,
    pageIndex: $pageIndex,
    itemsPerPage: $itemsPerPage,
    orderBy: "createdAt_desc"
  }) {
    data {
      id
      name
      centre { id name }
      teachers {
        teacher { fullName }
        role { name }
      }
      students { student { id } }
      slots { _id date startTime endTime }
    }
    pagination { total }
  }
}"""


# ─────────────────────────────────────────────────────────────────────────────
# Main fetch function
# ─────────────────────────────────────────────────────────────────────────────

def fetch_demo_classes(date_from: str, date_to: str = "") -> list:
    """
    Fetch lớp có buổi 14 diễn ra trong khoảng date_from → date_to (YYYY-MM-DD).
    Nếu date_to trống thì chỉ lấy đúng ngày date_from.
    """
    token = load_token()
    token_info = check_token(token)
    if not token_info["valid"]:
        raise RuntimeError("Token đã hết hạn. Vui lòng cập nhật token mới.")

    try:
        datetime.strptime(date_from, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Ngày không hợp lệ: {date_from}. Định dạng: YYYY-MM-DD")

    if not date_to:
        date_to = date_from
    else:
        try:
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Ngày không hợp lệ: {date_to}. Định dạng: YYYY-MM-DD")

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Content-Language": "en",
        "Origin": "https://lms.mindx.edu.vn",
        "Referer": "https://lms.mindx.edu.vn/"
    }

    ITEMS_PER_PAGE = 100

    TOTAL_QUERY = """query GetClasses($centres: [String], $haveSlotFrom: Date, $haveSlotTo: Date, $pageIndex: Int!, $itemsPerPage: Int!) {
  classes(payload: { centre_in: $centres, haveSlot_from: $haveSlotFrom, haveSlot_to: $haveSlotTo, pageIndex: $pageIndex, itemsPerPage: $itemsPerPage }) {
    pagination { total }
  }
}"""

    def fetch_page(page: int) -> list:
        payload = {
            "operationName": "GetClasses",
            "variables": {
                "centres": DEMO_CENTRE_IDS,
                "haveSlotFrom": date_from,
                "haveSlotTo": date_to,
                "pageIndex": page,
                "itemsPerPage": ITEMS_PER_PAGE,
            },
            "query": DEMO_QUERY,
        }
        try:
            res = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=30)
            if res.status_code != 200:
                return []
            data = res.json()
            if "errors" in data:
                return []
            return (data.get("data") or {}).get("classes", {}).get("data") or []
        except Exception:
            return []

    def get_total() -> int:
        payload = {
            "operationName": "GetClasses",
            "variables": {
                "centres": DEMO_CENTRE_IDS,
                "haveSlotFrom": date_from,
                "haveSlotTo": date_to,
                "pageIndex": 0,
                "itemsPerPage": 1,
            },
            "query": TOTAL_QUERY,
        }
        try:
            res = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=15)
            if res.status_code != 200:
                raise RuntimeError(f"LMS API trả về HTTP {res.status_code}")
            data = res.json()
            if "errors" in data:
                err_msg = data["errors"][0].get("message", "GraphQL error")
                raise RuntimeError(f"LMS API lỗi: {err_msg}")
            return (data.get("data") or {}).get("classes", {}).get("pagination", {}).get("total", 0)
        except RuntimeError:
            raise
        except Exception as e:
            raise RuntimeError(f"Không thể kết nối LMS API: {e}")

    # Lấy tổng số lớp
    total = get_total()
    num_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    # Fetch song song tất cả pages (max 5 concurrent để tránh rate-limit)
    import concurrent.futures
    all_raw = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_page, p): p for p in range(num_pages)}
        for future in concurrent.futures.as_completed(futures):
            try:
                all_raw.extend(future.result())
            except Exception:
                pass

    # Filter: chỉ lấy lớp có buổi 14 diễn ra trong khoảng date_from → date_to
    all_classes = []
    for c in all_raw:
        centre_id = (c.get("centre") or {}).get("id", "")
        centre_name = (c.get("centre") or {}).get("name", "")
        centre_info = DEMO_CENTRES.get(centre_id, {"name": centre_name, "area": "?"})

        slots = sorted(c.get("slots", []), key=lambda s: s.get("date", ""))

        if len(slots) < 14:
            continue

        slot_14 = slots[13]
        slot_date = slot_14.get("date", "")[:10]

        # Kiểm tra buổi 14 có nằm trong range không
        if slot_date < date_from or slot_date > date_to:
            continue

        # Giáo viên chính
        main_teacher = ""
        for t in c.get("teachers", []):
            role = (t.get("role") or {}).get("name", "")
            if "Lecturer" in role:
                main_teacher = (t.get("teacher") or {}).get("fullName", "")
                break

        start_fmt  = fmt_time_utc7(slot_14.get("startTime", ""))
        end_fmt    = fmt_time_utc7(slot_14.get("endTime", ""))
        time_range = f"{start_fmt} - {end_fmt}" if start_fmt and end_fmt else ""
        time_demo  = f"{fmt_date_vn(slot_date)} {time_range}".strip()

        all_classes.append({
            "id":            c.get("id"),
            "name":          c.get("name", ""),
            "centre":        centre_info["name"].replace("HCM - ", ""),
            "centre_full":   centre_info["name"],
            "area":          centre_info["area"],
            "block":         get_block(c.get("name", "")),
            "teacher":       main_teacher,
            "student_count": len(c.get("students", [])),
            "date":          fmt_date_vn(slot_date),
            "day_of_week":   day_of_week_vn(slot_date),
            "time":          time_range,
            "time_demo":     time_demo,
            "slot_14_date":  slot_date,
        })

    # Sort: block → area → date → time → name
    block_order = {"Coding": 0, "Robotics": 1, "Art": 2}
    all_classes.sort(key=lambda x: (
        block_order.get(x["block"], 9),
        x["area"],
        x["slot_14_date"],
        x["time"],
        x["name"]
    ))

    return all_classes


# ─────────────────────────────────────────────────────────────────────────────
# Google Sheets export
# ─────────────────────────────────────────────────────────────────────────────

def load_sheet_id() -> str:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    with open(env_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line.startswith("GOOGLE_SHEET_ID="):
                val = line[len("GOOGLE_SHEET_ID="):].strip().strip('"').strip("'")
                if val:
                    return val
    raise RuntimeError("Không tìm thấy GOOGLE_SHEET_ID trong .env")



def export_to_sheet(classes: list, date_from: str, date_to: str = "") -> dict:
    """
    Xuất danh sách lớp ra Google Sheet.
    - Cùng range ngày → ghi đè tab cũ (xóa rồi tạo lại)
    - Range ngày khác → tạo tab mới
    Format: font Exo, ẩn gridlines, màu header đúng, bảng tổng hợp trái,
    cột Judge nền hồng, đường viền solid/dot, kích thước cột/hàng chuẩn.
    """
    import gspread
    from google.oauth2.service_account import Credentials
    import googleapiclient.discovery

    creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "google_credentials.json")
    if not os.path.exists(creds_path):
        raise RuntimeError("Không tìm thấy google_credentials.json")

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    service = googleapiclient.discovery.build('sheets', 'v4', credentials=creds)

    sheet_id = load_sheet_id()
    spreadsheet = gc.open_by_key(sheet_id)

    # ── Tên tab = range ngày ──────────────────────────────────────────────
    if not date_to or date_to == date_from:
        try:
            tab_name = datetime.strptime(date_from, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            tab_name = date_from
    else:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            dt_to   = datetime.strptime(date_to,   "%Y-%m-%d")
            tab_name = f"{dt_from.strftime('%d/%m')} - {dt_to.strftime('%d/%m/%Y')}"
        except Exception:
            tab_name = f"{date_from} - {date_to}"

    # ── Tạo/ghi đè tab ───────────────────────────────────────────────────
    # Luôn tạo temp trước để tránh lỗi "can't remove all visible sheets"
    temp_ws = spreadsheet.add_worksheet(title="_temp_export_", rows=1, cols=1)
    try:
        existing_ws = spreadsheet.worksheet(tab_name)
        spreadsheet.del_worksheet(existing_ws)
    except gspread.exceptions.WorksheetNotFound:
        pass
    ws = spreadsheet.add_worksheet(title=tab_name, rows=300, cols=44)
    spreadsheet.del_worksheet(temp_ws)
    sid = ws.id

    # ── Phân loại theo khối ───────────────────────────────────────────────
    coding   = [c for c in classes if c["block"] == "Coding"]
    robotics = [c for c in classes if c["block"] == "Robotics"]
    art      = [c for c in classes if c["block"] == "Art"]
    max_rows = max(len(coding), len(robotics), len(art), 1)

    # ── Màu sắc ───────────────────────────────────────────────────────────
    C_CODING_BG   = {"red": 0.10980392, "green": 0.27058825, "blue": 0.5294118}
    C_ROBOTICS_BG = {"red": 1.0,        "green": 0.6,        "blue": 0.0}
    C_ART_BG      = {"red": 0.6,        "green": 0.0,        "blue": 0.0}
    C_WHITE       = {"red": 1.0,        "green": 1.0,        "blue": 1.0}
    C_JUDGE_BG    = {"red": 0.95686275, "green": 0.8,        "blue": 0.8}
    C_SUMMARY_BG  = {"red": 1.0,        "green": 0.94902,    "blue": 0.8}
    C_ART_FG      = {"red": 1.0,        "green": 0.0,        "blue": 0.0}
    C_CODING_FG   = {"red": 0.0,        "green": 0.0,        "blue": 1.0}
    C_ROBOTICS_FG = {"red": 0.98431,    "green": 0.73725,    "blue": 0.01569}
    FONT = "Exo"

    # ── Bảng tổng hợp bên trái ────────────────────────────────────────────
    hcm1_total  = sum(1 for c in classes if c["area"] == "HCM 1")
    hcm4_total  = sum(1 for c in classes if c["area"] == "HCM 4")
    hcm1_art    = sum(1 for c in classes if c["area"] == "HCM 1" and c["block"] == "Art")
    hcm1_coding = sum(1 for c in classes if c["area"] == "HCM 1" and c["block"] == "Coding")
    hcm1_rob    = sum(1 for c in classes if c["area"] == "HCM 1" and c["block"] == "Robotics")
    hcm4_art    = sum(1 for c in classes if c["area"] == "HCM 4" and c["block"] == "Art")
    hcm4_coding = sum(1 for c in classes if c["area"] == "HCM 4" and c["block"] == "Coding")
    hcm4_rob    = sum(1 for c in classes if c["area"] == "HCM 4" and c["block"] == "Robotics")

    # summary_left[i] = 8 cells cho cols A-H (index 0-7)
    # Row 9 (index 8): col C = "Khu vực", col D = "Course" (C9:E9 sẽ được merge → text "Course")
    summary_left = [
        ["", "Tổng lớp End/BA", "SL", "", "", "", "", ""],                                    # row 3
        ["", "HCM 1", str(hcm1_total), "", "", "", "", ""],                                   # row 4
        ["", "HCM 4", str(hcm4_total), "", "", "", "", ""],                                   # row 5
        ["", "Tổng cộng", str(len(classes)), "", "", "", "", ""],                             # row 6
        ["", "", "", "", "", "", "", ""],                                                       # row 7
        ["", "", "", "", "", "", "", ""],                                                       # row 8
        ["", "Khu vực", "Course", "", "", "", "", ""],                                         # row 9  ← C9:E9 merge
        ["", "Tổng lớp End/BA ( Khối )", "Art", "Coding", "Robotics", "", "", ""],           # row 10
        ["", "HCM 1", str(hcm1_art), str(hcm1_coding), str(hcm1_rob), "", "", ""],           # row 11
        ["", "HCM 4", str(hcm4_art), str(hcm4_coding), str(hcm4_rob), "", "", ""],           # row 12
    ]

    col_headers = ["No", "BA", "Class Name", "Centre Name", "Time Demo", "Sĩ số",
                   "Date", "Day of the week", "Time", "Judge", "Leader\nxác nhận"]

    HEADER_ROW1 = ([""] * 8 + ["CODING"]   + [""] * 10 + [""] +
                               ["ROBOTICS"] + [""] * 10 + [""] +
                               ["XART"]     + [""] * 10 + [""])
    HEADER_ROW2 = [""] * 8 + col_headers + [""] + col_headers + [""] + col_headers + [""]

    def make_data_row(idx: int, item) -> list:
        if item is None:
            return [""] * 11
        return [
            idx + 1,
            item["area"],
            item["name"],
            item["centre_full"],
            item["time_demo"],
            item["student_count"],
            item["date"],
            item["day_of_week"],
            item["time"],
            "",   # Judge
            "",   # Leader xác nhận
        ]

    all_rows = [HEADER_ROW1, HEADER_ROW2]
    for i in range(max_rows):
        left = summary_left[i] if i < len(summary_left) else [""] * 8
        row = (left +
               make_data_row(i, coding[i]   if i < len(coding)   else None) + [""] +
               make_data_row(i, robotics[i] if i < len(robotics) else None) + [""] +
               make_data_row(i, art[i]      if i < len(art)       else None) + [""])
        all_rows.append(row)

    total_row = (["", "Tổng", str(len(classes)), "", "", "", "", ""] +
                 ["Tổng", "", "", "", "", str(len(coding)),   "", "", "", "", ""] + [""] +
                 ["Tổng", "", "", "", "", str(len(robotics)), "", "", "", "", ""] + [""] +
                 ["Tổng", "", "", "", "", str(len(art)),      "", "", "", "", ""] + [""])
    all_rows.append(total_row)

    ws.update(values=all_rows, range_name="A1")

    # ── Helpers ───────────────────────────────────────────────────────────
    def rng(r0, r1, c0, c1):
        return {"sheetId": sid, "startRowIndex": r0, "endRowIndex": r1,
                "startColumnIndex": c0, "endColumnIndex": c1}

    def repeat_cell(r0, r1, c0, c1, fmt):
        return {"repeatCell": {
            "range": rng(r0, r1, c0, c1),
            "cell": {"userEnteredFormat": fmt},
            "fields": "userEnteredFormat(" + ",".join(fmt.keys()) + ")",
        }}

    def merge(r0, r1, c0, c1):
        return {"mergeCells": {"range": rng(r0, r1, c0, c1), "mergeType": "MERGE_ALL"}}

    def col_width(c0, c1, px):
        return {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "COLUMNS",
                      "startIndex": c0, "endIndex": c1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"
        }}

    def row_height(r0, r1, px):
        return {"updateDimensionProperties": {
            "range": {"sheetId": sid, "dimension": "ROWS",
                      "startIndex": r0, "endIndex": r1},
            "properties": {"pixelSize": px}, "fields": "pixelSize"
        }}

    def border_style(style_type):
        """style_type: 'SOLID' hoặc 'DOTTED'"""
        return {"style": style_type, "width": 1,
                "color": {"red": 0, "green": 0, "blue": 0}}

    def update_borders(r0, r1, c0, c1, outer_style, inner_v_style, inner_h_style):
        """
        Áp dụng đường viền cho vùng:
        - outer: 4 cạnh ngoài cùng (top/bottom/left/right của toàn vùng)
        - inner_v: đường dọc bên trong (giữa các cột)
        - inner_h: đường ngang bên trong (giữa các hàng)
        Dùng updateBorders cho từng cell trong vùng.
        """
        reqs = []
        outer = border_style(outer_style)
        inner_v = border_style(inner_v_style)
        inner_h = border_style(inner_h_style)

        for r in range(r0, r1):
            for c in range(c0, c1):
                top    = outer if r == r0 else inner_h
                bottom = outer if r == r1 - 1 else inner_h
                left   = outer if c == c0 else inner_v
                right  = outer if c == c1 - 1 else inner_v
                reqs.append({"updateBorders": {
                    "range": rng(r, r + 1, c, c + 1),
                    "top":    top,
                    "bottom": bottom,
                    "left":   left,
                    "right":  right,
                }})
        return reqs

    reqs = []

    # ── Ẩn gridlines + freeze ─────────────────────────────────────────────
    reqs.append({"updateSheetProperties": {
        "properties": {"sheetId": sid, "gridProperties": {
            "frozenRowCount": 2, "hideGridlines": True
        }},
        "fields": "gridProperties.frozenRowCount,gridProperties.hideGridlines"
    }})

    # ── Merge headers khối ────────────────────────────────────────────────
    reqs += [merge(0, 1, 8, 19), merge(0, 1, 20, 31), merge(0, 1, 32, 43)]

    # ── Merge bảng tổng hợp ───────────────────────────────────────────────
    # "Tổng lớp End/BA ( Khối )" cols B-E (1-4), row 10 (index 9)
    reqs.append(merge(9, 10, 1, 5))
    # C9:E9 → merge cols C,D,E (index 2-4), row 9 (index 8) — text "Course"
    reqs.append(merge(8, 9, 2, 5))

    # ── Font toàn bộ sheet ────────────────────────────────────────────────
    reqs.append(repeat_cell(0, len(all_rows) + 2, 0, 44, {
        "textFormat": {"fontFamily": FONT},
    }))

    # ── Row 1: tiêu đề khối ───────────────────────────────────────────────
    for c_start, bg in [(8, C_CODING_BG), (20, C_ROBOTICS_BG), (32, C_ART_BG)]:
        reqs.append(repeat_cell(0, 1, c_start, c_start + 11, {
            "textFormat": {"bold": True, "fontSize": 14, "fontFamily": FONT,
                           "foregroundColor": C_WHITE},
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "backgroundColor": bg,
        }))

    # ── Row 2: sub-headers ────────────────────────────────────────────────
    for c_start in [8, 20, 32]:
        reqs.append(repeat_cell(1, 2, c_start, c_start + 11, {
            "textFormat": {"bold": True, "fontSize": 11, "fontFamily": FONT},
            "horizontalAlignment": "CENTER",
            "verticalAlignment": "MIDDLE",
            "wrapStrategy": "WRAP",
        }))

    # ── Data rows: CENTER align ───────────────────────────────────────────
    if max_rows > 0:
        for c_start in [8, 20, 32]:
            reqs.append(repeat_cell(2, 2 + max_rows, c_start, c_start + 11, {
                "textFormat": {"fontFamily": FONT},
                "horizontalAlignment": "CENTER",
            }))
            # Cột Judge (offset 9): nền hồng
            reqs.append(repeat_cell(2, 2 + max_rows, c_start + 9, c_start + 10, {
                "backgroundColor": C_JUDGE_BG,
            }))

    # ── Bảng tổng hợp bên trái ────────────────────────────────────────────
    # Row 3 (index 2): "Tổng lớp End/BA" + "SL" — nền vàng nhạt, bold
    reqs.append(repeat_cell(2, 3, 1, 3, {
        "textFormat": {"bold": True, "fontFamily": FONT},
        "horizontalAlignment": "CENTER",
        "backgroundColor": C_SUMMARY_BG,
    }))
    # Row 9 (index 8): "Khu vực" + "Course" — nền vàng nhạt, bold
    reqs.append(repeat_cell(8, 9, 1, 5, {
        "textFormat": {"bold": True, "fontFamily": FONT},
        "horizontalAlignment": "CENTER",
        "backgroundColor": C_SUMMARY_BG,
    }))
    # Row 10 (index 9): Art=đỏ, Coding=xanh, Robotics=vàng
    reqs.append(repeat_cell(9, 10, 2, 3, {
        "textFormat": {"bold": True, "fontFamily": FONT, "foregroundColor": C_ART_FG},
        "horizontalAlignment": "CENTER",
    }))
    reqs.append(repeat_cell(9, 10, 3, 4, {
        "textFormat": {"bold": True, "fontFamily": FONT, "foregroundColor": C_CODING_FG},
        "horizontalAlignment": "CENTER",
    }))
    reqs.append(repeat_cell(9, 10, 4, 5, {
        "textFormat": {"bold": True, "fontFamily": FONT, "foregroundColor": C_ROBOTICS_FG},
        "horizontalAlignment": "CENTER",
    }))

    # ── Row heights ───────────────────────────────────────────────────────
    reqs.append(row_height(0, 1, 40))
    reqs.append(row_height(1, 2, 40))
    if max_rows > 0:
        reqs.append(row_height(2, 2 + max_rows, 21))

    # ── Column widths ─────────────────────────────────────────────────────
    # Theo yêu cầu:
    # A(0)=70, B(1)=130, C(2)=70, D(3)=70, E(4)=70, F(5)=70, G(6)=70, H(7)=70
    # I(8)=No, J(9)=BA, K(10)=ClassName, L(11)=CentreName, M(12)=TimeDemo,
    # N(13)=Sĩsố, O(14)=Date, P(15)=Day, Q(16)=Time, R(17)=Judge=100, S(18)=Leader=100
    # T(19)=separator=100
    # U(20)=No, ..., AD(29)=Judge=100, AE(30)=Leader=100
    # AF(31)=separator=100
    # AG(32)=No, ..., AP(41)=Judge=100, AQ(42)=Leader=100
    # AR(43)=trailing=100
    col_widths_spec = [
        (0,  1,  70),   # A
        (1,  2,  130),  # B: label tổng hợp (giữ nguyên)
        (2,  3,  70),   # C
        (3,  4,  70),   # D
        (4,  5,  70),   # E
        (5,  6,  70),   # F
        (6,  7,  70),   # G
        (7,  8,  70),   # H
        (8,  9,  35),   # I: No
        (9,  10, 55),   # J: BA
        (10, 11, 155),  # K: Class Name
        (11, 12, 195),  # L: Centre Name
        (12, 13, 165),  # M: Time Demo
        (13, 14, 45),   # N: Sĩ số
        (14, 15, 85),   # O: Date
        (15, 16, 75),   # P: Day of the week
        (16, 17, 95),   # Q: Time
        (17, 18, 100),  # R: Judge (Coding)
        (18, 19, 100),  # S: Leader (Coding)
        (19, 20, 100),  # T: separator
        (20, 21, 35),   # U: No
        (21, 22, 55),   # V: BA
        (22, 23, 155),  # W: Class Name
        (23, 24, 195),  # X: Centre Name
        (24, 25, 165),  # Y: Time Demo
        (25, 26, 45),   # Z: Sĩ số
        (26, 27, 85),   # AA: Date
        (27, 28, 75),   # AB: Day
        (28, 29, 95),   # AC: Time
        (29, 30, 100),  # AD: Judge (Robotics)
        (30, 31, 100),  # AE: Leader (Robotics)
        (31, 32, 100),  # AF: separator
        (32, 33, 35),   # AG: No
        (33, 34, 55),   # AH: BA
        (34, 35, 155),  # AI: Class Name
        (35, 36, 195),  # AJ: Centre Name
        (36, 37, 165),  # AK: Time Demo
        (37, 38, 45),   # AL: Sĩ số
        (38, 39, 85),   # AM: Date
        (39, 40, 75),   # AN: Day
        (40, 41, 95),   # AO: Time
        (41, 42, 100),  # AP: Judge (Art)
        (42, 43, 100),  # AQ: Leader (Art)
        (43, 44, 100),  # AR: trailing
    ]
    for c0, c1, px in col_widths_spec:
        reqs.append(col_width(c0, c1, px))

    # ── Đường viền 3 vùng dữ liệu ────────────────────────────────────────
    # Vùng I1:S(max_rows+2) = cols 8-18, rows 0-(max_rows+2)
    # Vùng U1:AE(max_rows+2) = cols 20-30
    # Vùng AG1:AQ(max_rows+2) = cols 32-42
    # Outer: SOLID, inner vertical: SOLID, inner horizontal: DOTTED
    border_end_row = 2 + max_rows  # rows 0 → border_end_row (exclusive)
    for c_start in [8, 20, 32]:
        reqs.extend(update_borders(
            0, border_end_row,
            c_start, c_start + 11,
            outer_style="SOLID",
            inner_v_style="SOLID",
            inner_h_style="DOTTED",
        ))

    service.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={"requests": reqs}
    ).execute()

    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid={ws.id}"
    return {
        "url": sheet_url,
        "tab_name": tab_name,
        "coding_count": len(coding),
        "robotics_count": len(robotics),
        "art_count": len(art),
        "total": len(classes),
    }
