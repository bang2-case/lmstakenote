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
import subprocess
import time as time_module
from datetime import datetime, timezone, timedelta, time as dt_time
from urllib.parse import quote

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
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
IDTOKEN_SCRIPT = os.path.join(PROJECT_ROOT, "get-idtoken.js")
VN_TZ = timezone(timedelta(hours=7))
DEMO_CLASS_STATUSES = ["RUNNING", "FINISHED"]
EXCLUDED_DEMO_STATUSES = {
    "ABANDONED",
    "CANCELLED",
    "CANCELED",
    "REJECT",
    "REJECTED",
    "SUSPENDED",
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_env_file_value(key: str) -> str | None:
    if not os.path.exists(ENV_PATH):
        return None
    with open(ENV_PATH, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == key:
                value = value.strip().strip('"').strip("'")
                return value or None
    return None


def env_value(*keys: str) -> str | None:
    for key in keys:
        value = os.environ.get(key) or read_env_file_value(key)
        if value:
            return value.strip().strip('"').strip("'")
    return None


def refresh_token_from_login() -> str | None:
    if not os.path.exists(IDTOKEN_SCRIPT):
        return None
    if not (
        env_value("FIREBASE_API_KEY", "NEXT_PUBLIC_FIREBASE_API_KEY")
        and env_value("LMS_LOGIN_EMAIL")
        and env_value("LMS_LOGIN_PASSWORD")
    ):
        return None
    try:
        result = subprocess.run(
            ["node", IDTOKEN_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=PROJECT_ROOT,
            env={**os.environ},
        )
        if result.returncode != 0:
            return None
        token = result.stdout.strip().splitlines()[-1].strip()
        if not token or len(token) < 100:
            return None
        info = check_token(token)
        if not info["valid"]:
            return None
        os.environ["LMS_TOKEN"] = token
        return token
    except Exception:
        return None


def load_token() -> str:
    token = env_value("LMS_TOKEN")
    if token and check_token(token)["valid"]:
        return token

    refreshed_token = refresh_token_from_login()
    if refreshed_token:
        return refreshed_token

    if token:
        raise RuntimeError(
            "Token đã hết hạn và không thể tự lấy token mới. "
            "Hãy kiểm tra FIREBASE_API_KEY, LMS_LOGIN_EMAIL, LMS_LOGIN_PASSWORD trong .env."
        )
    raise RuntimeError(
        "Không tìm thấy LMS_TOKEN hoặc thông tin đăng nhập LMS trong .env."
    )


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


def get_class_status(item) -> str:
    status = item.get("status") if isinstance(item, dict) else ""
    if isinstance(status, dict):
        status = status.get("name") or status.get("code") or status.get("value") or ""
    return str(status or "").strip().upper()


def is_running_class(item) -> bool:
    return get_class_status(item) == "RUNNING"


def is_demo_class(item) -> bool:
    """Lớp hợp lệ cho DEMO: không lấy lớp hủy/từ chối/tạm dừng."""
    status = get_class_status(item)
    if status in EXCLUDED_DEMO_STATUSES:
        return False
    return True


def parse_ymd(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def normalize_date_range(date_from: str, date_to: str = "") -> tuple[str, str]:
    start = parse_ymd(date_from)
    end = parse_ymd(date_to or date_from)
    if end < start:
        start, end = end, start
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def iso_to_datetime(iso: str) -> datetime | None:
    if not iso:
        return None
    value = str(iso).strip()
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def to_vn_datetime(iso: str) -> datetime | None:
    dt = iso_to_datetime(iso)
    return dt.astimezone(VN_TZ) if dt else None


def to_lms_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def lms_date_bounds(date_from: str, date_to: str) -> tuple[str, str]:
    start_date = parse_ymd(date_from).date()
    end_date = parse_ymd(date_to).date()
    start_local = datetime.combine(start_date, dt_time.min, tzinfo=VN_TZ)
    end_local = datetime.combine(end_date, dt_time.max, tzinfo=VN_TZ)
    return to_lms_utc_iso(start_local), to_lms_utc_iso(end_local)


def get_student_count(item: dict) -> int:
    if not isinstance(item, dict):
        return 0
    students = item.get("students")
    if isinstance(students, list):
        return len(students)
    count = item.get("student_count") or item.get("studentCount") or 0
    try:
        return int(count)
    except Exception:
        return 0


def slot_reference_iso(slot: dict) -> str:
    return slot.get("startTime") or slot.get("date") or slot.get("endTime") or ""


def slot_sort_key(slot: dict) -> tuple[str, str]:
    dt = iso_to_datetime(slot_reference_iso(slot))
    if dt:
        return (dt.isoformat(), slot.get("_id", "") or slot.get("id", ""))
    fallback = slot.get("date", "") or slot.get("startTime", "") or slot.get("endTime", "")
    return (str(fallback), slot.get("_id", "") or slot.get("id", ""))


def fmt_time_utc7(iso: str) -> str:
    """Format ISO time string sang HH:MM (UTC+7)."""
    if not iso:
        return ""
    try:
        local = to_vn_datetime(iso)
        if local:
            return local.strftime("%H:%M")
    except Exception:
        pass
    return iso[11:16] if len(iso) > 15 else iso


def date_utc7(iso: str) -> str:
    """Return YYYY-MM-DD in Vietnam time for LMS UTC datetime strings."""
    if not iso:
        return ""
    raw = iso[:10]
    try:
        local = to_vn_datetime(iso)
        if local:
            return local.strftime("%Y-%m-%d")
    except Exception:
        pass
    return raw


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

DEMO_QUERY = """query GetClasses($centres: [String], $haveSlotFrom: Date, $haveSlotTo: Date, $statuses: [String], $pageIndex: Int!, $itemsPerPage: Int!) {
  classes(payload: {
    centre_in: $centres,
    haveSlot_from: $haveSlotFrom,
    haveSlot_to: $haveSlotTo,
    status_in: $statuses,
    pageIndex: $pageIndex,
    itemsPerPage: $itemsPerPage,
    orderBy: "createdAt_desc"
  }) {
    data {
      id
      name
      status
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
        parse_ymd(date_from)
    except ValueError:
        raise ValueError(f"Ngày không hợp lệ: {date_from}. Định dạng: YYYY-MM-DD")
    if date_to:
        try:
            parse_ymd(date_to)
        except ValueError:
            raise ValueError(f"Ngày không hợp lệ: {date_to}. Định dạng: YYYY-MM-DD")
    date_from, date_to = normalize_date_range(date_from, date_to)
    api_date_from, api_date_to = lms_date_bounds(date_from, date_to)

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "Content-Language": "en",
        "Origin": "https://lms.mindx.edu.vn",
        "Referer": "https://lms.mindx.edu.vn/"
    }

    ITEMS_PER_PAGE = 100
    MAX_WORKERS = 5
    MAX_RETRIES = 3

    TOTAL_QUERY = """query GetClasses($centres: [String], $haveSlotFrom: Date, $haveSlotTo: Date, $statuses: [String], $pageIndex: Int!, $itemsPerPage: Int!) {
  classes(payload: { centre_in: $centres, haveSlot_from: $haveSlotFrom, haveSlot_to: $haveSlotTo, status_in: $statuses, pageIndex: $pageIndex, itemsPerPage: $itemsPerPage }) {
    pagination { total }
  }
}"""

    def post_lms(payload: dict, timeout: int = 30) -> dict:
        last_error = ""
        for attempt in range(MAX_RETRIES):
            try:
                res = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=timeout)
                if res.status_code != 200:
                    last_error = f"HTTP {res.status_code}: {res.text[:300]}"
                else:
                    data = res.json()
                    if "errors" in data:
                        messages = [
                            str(error.get("message", error))
                            for error in data.get("errors", [])
                        ]
                        last_error = "; ".join(messages) or "GraphQL error"
                    else:
                        return data
            except Exception as e:
                last_error = str(e)

            if attempt < MAX_RETRIES - 1:
                time_module.sleep(0.8 * (attempt + 1))

        raise RuntimeError(f"LMS API lỗi sau {MAX_RETRIES} lần thử: {last_error}")

    def fetch_page(page: int) -> list:
        payload = {
            "operationName": "GetClasses",
            "variables": {
                "centres": DEMO_CENTRE_IDS,
                "haveSlotFrom": api_date_from,
                "haveSlotTo": api_date_to,
                "statuses": DEMO_CLASS_STATUSES,
                "pageIndex": page,
                "itemsPerPage": ITEMS_PER_PAGE,
            },
            "query": DEMO_QUERY,
        }
        data = post_lms(payload, timeout=30)
        return (data.get("data") or {}).get("classes", {}).get("data") or []

    def get_total() -> int:
        payload = {
            "operationName": "GetClasses",
            "variables": {
                "centres": DEMO_CENTRE_IDS,
                "haveSlotFrom": api_date_from,
                "haveSlotTo": api_date_to,
                "statuses": DEMO_CLASS_STATUSES,
                "pageIndex": 0,
                "itemsPerPage": 1,
            },
            "query": TOTAL_QUERY,
        }
        data = post_lms(payload, timeout=15)
        return (data.get("data") or {}).get("classes", {}).get("pagination", {}).get("total", 0)

    total = get_total()
    num_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    # Fetch song song tất cả pages trong range ngày VN đã đổi sang UTC.
    import concurrent.futures
    all_raw = []
    page_errors = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(fetch_page, p): p for p in range(num_pages)}
        for future in concurrent.futures.as_completed(futures):
            page = futures[future]
            try:
                all_raw.extend(future.result())
            except Exception as e:
                page_errors.append(f"page {page}: {e}")

    if page_errors:
        detail = "; ".join(page_errors[:3])
        if len(page_errors) > 3:
            detail += f"; ... +{len(page_errors) - 3} page"
        raise RuntimeError(f"Không lấy đủ dữ liệu DEMO từ LMS: {detail}")

    raw_by_id = {}
    for item in all_raw:
        class_id = item.get("id") if isinstance(item, dict) else None
        if class_id and class_id not in raw_by_id:
            raw_by_id[class_id] = item

    # Filter: chỉ lấy lớp có buổi 14 diễn ra trong khoảng date_from → date_to
    all_classes = []
    for c in raw_by_id.values():
        if not is_demo_class(c):
            continue

        student_count = get_student_count(c)
        if student_count <= 0:
            continue

        centre_id = (c.get("centre") or {}).get("id", "")
        centre_name = (c.get("centre") or {}).get("name", "")
        centre_info = DEMO_CENTRES.get(centre_id, {"name": centre_name, "area": "?"})

        slots = sorted(
            [s for s in c.get("slots", []) if isinstance(s, dict) and slot_reference_iso(s)],
            key=slot_sort_key,
        )

        if len(slots) < 14:
            continue

        slot_14 = slots[13]
        slot_date = date_utc7(slot_reference_iso(slot_14))

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
            "status":        c.get("status", ""),
            "centre":        centre_info["name"].replace("HCM - ", ""),
            "centre_full":   centre_info["name"],
            "area":          centre_info["area"],
            "block":         get_block(c.get("name", "")),
            "teacher":       main_teacher,
            "student_count": student_count,
            "date":          fmt_date_vn(slot_date),
            "day_of_week":   day_of_week_vn(slot_date),
            "time":          time_range,
            "time_demo":     time_demo,
            "slot_14_date":  slot_date,
            "slot_14_id":    slot_14.get("_id") or slot_14.get("id", ""),
            "slot_14_start": slot_14.get("startTime", ""),
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
    sheet_id = env_value("GOOGLE_SHEET_ID")
    if sheet_id:
        return sheet_id
    raise RuntimeError("Không tìm thấy GOOGLE_SHEET_ID trong .env")


def load_google_credentials(scopes):
    from google.oauth2.service_account import Credentials

    raw_credentials = env_value("GOOGLE_CREDENTIALS_JSON", "GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_credentials:
        try:
            raw_credentials = raw_credentials.strip()
            if raw_credentials.startswith("{"):
                info = json.loads(raw_credentials)
            else:
                decoded = base64.b64decode(raw_credentials).decode("utf-8")
                info = json.loads(decoded)
            return Credentials.from_service_account_info(info, scopes=scopes)
        except Exception as e:
            raise RuntimeError(f"GOOGLE_CREDENTIALS_JSON không hợp lệ: {e}")

    creds_path = os.path.join(PROJECT_ROOT, "google_credentials.json")
    if not os.path.exists(creds_path):
        raise RuntimeError(
            "Không tìm thấy google_credentials.json hoặc GOOGLE_CREDENTIALS_JSON trong env"
        )
    return Credentials.from_service_account_file(creds_path, scopes=scopes)


def google_api_request(creds, method: str, url: str, **kwargs):
    from google.auth.transport.requests import Request as GoogleAuthRequest

    if not creds.valid:
        creds.refresh(GoogleAuthRequest())

    headers = dict(kwargs.pop("headers", {}) or {})
    headers["Authorization"] = f"Bearer {creds.token}"
    headers.setdefault("Accept", "application/json")

    response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
    if response.status_code >= 400:
        detail = response.text[:800]
        raise RuntimeError(f"Google Sheets API lỗi {response.status_code}: {detail}")
    if not response.content:
        return {}
    return response.json()


def sheet_range(tab_name: str, a1_range: str) -> str:
    escaped = tab_name.replace("'", "''")
    return quote(f"'{escaped}'!{a1_range}", safe="")


def get_spreadsheet(creds, sheet_id: str, fields: str):
    return google_api_request(
        creds,
        "GET",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}",
        params={"fields": fields},
    )


def batch_update_spreadsheet(creds, sheet_id: str, requests_list: list[dict]):
    if not requests_list:
        return {}
    return google_api_request(
        creds,
        "POST",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}:batchUpdate",
        json={"requests": requests_list},
    )


def update_sheet_values(creds, sheet_id: str, tab_name: str, values: list[list], value_input_option: str = "USER_ENTERED"):
    return google_api_request(
        creds,
        "PUT",
        f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/{sheet_range(tab_name, 'A1')}",
        params={"valueInputOption": value_input_option},
        json={"values": values},
    )


def list_sheet_refs(spreadsheet_meta: dict) -> list[dict]:
    result = []
    for sheet in spreadsheet_meta.get("sheets", []):
        props = sheet.get("properties", {}) or {}
        result.append({
            "id": props.get("sheetId"),
            "title": props.get("title", ""),
            "rowCount": (props.get("gridProperties", {}) or {}).get("rowCount"),
            "columnCount": (props.get("gridProperties", {}) or {}).get("columnCount"),
        })
    return result



def export_to_sheet(classes: list, date_from: str, date_to: str = "") -> dict:
    """
    Xuất danh sách lớp ra Google Sheet.
    - Cùng range ngày → ghi đè tab cũ (xóa rồi tạo lại)
    - Range ngày khác → tạo tab mới
    Format: font Exo, ẩn gridlines, màu header đúng, bảng tổng hợp trái,
    cột Judge nền hồng, đường viền solid/dot, kích thước cột/hàng chuẩn.
    """
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
    ]
    creds = load_google_credentials(scopes)

    sheet_id = load_sheet_id()
    classes = [c for c in classes if is_demo_class(c) and get_student_count(c) > 0]
    spreadsheet_meta = get_spreadsheet(
        creds,
        sheet_id,
        "sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))",
    )
    worksheets_before = list_sheet_refs(spreadsheet_meta)

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

    def pick_format_template():
        candidates = [
            w for w in worksheets_before
            if w["title"] != tab_name and not w["title"].startswith("_temp_export_")
        ]
        dated = [w for w in candidates if re.search(r"\d{2}/\d{2}", w["title"])]
        return (dated or candidates or [None])[-1]

    format_template_ws = pick_format_template()

    # ── Tạo/ghi đè tab ───────────────────────────────────────────────────
    # Chỉ tạo temp khi ghi đè sheet cuối cùng để tránh lỗi "can't remove all visible sheets".
    temp_sheet_id = None
    existing_ws = next((w for w in worksheets_before if w["title"] == tab_name), None)

    if existing_ws is not None:
        if len(worksheets_before) <= 1:
            temp_title = f"_temp_export_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            temp_result = batch_update_spreadsheet(creds, sheet_id, [{
                "addSheet": {
                    "properties": {
                        "title": temp_title,
                        "gridProperties": {"rowCount": 1, "columnCount": 1},
                    }
                }
            }])
            temp_sheet_id = (
                temp_result.get("replies", [{}])[0]
                .get("addSheet", {})
                .get("properties", {})
                .get("sheetId")
            )
        batch_update_spreadsheet(creds, sheet_id, [{
            "deleteSheet": {"sheetId": existing_ws["id"]}
        }])

    sheet_rows = max(300, len(classes) + 20)
    add_result = batch_update_spreadsheet(creds, sheet_id, [{
        "addSheet": {
            "properties": {
                "title": tab_name,
                "gridProperties": {"rowCount": sheet_rows, "columnCount": 44},
            }
        }
    }])
    sid = (
        add_result.get("replies", [{}])[0]
        .get("addSheet", {})
        .get("properties", {})
        .get("sheetId")
    )
    if sid is None:
        raise RuntimeError("Không tạo được tab Google Sheet mới.")

    cleanup_reqs = []
    cleanup_sheet_ids = set()
    if temp_sheet_id is not None:
        cleanup_sheet_ids.add(temp_sheet_id)
        cleanup_reqs.append({"deleteSheet": {"sheetId": temp_sheet_id}})
    refreshed_meta = get_spreadsheet(
        creds,
        sheet_id,
        "sheets(properties(sheetId,title))",
    )
    for stale_ws in list_sheet_refs(refreshed_meta):
        stale_id = stale_ws["id"]
        if stale_id != sid and stale_id not in cleanup_sheet_ids and stale_ws["title"].startswith("_temp_export_"):
            cleanup_sheet_ids.add(stale_id)
            cleanup_reqs.append({"deleteSheet": {"sheetId": stale_id}})
    batch_update_spreadsheet(creds, sheet_id, cleanup_reqs)

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

    update_sheet_values(creds, sheet_id, tab_name, all_rows, value_input_option="RAW")

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

    if format_template_ws is not None:
        try:
            template_meta = google_api_request(
                creds,
                "GET",
                f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}",
                params={
                    "includeGridData": "true",
                    "fields": "sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)),data(rowMetadata(pixelSize),columnMetadata(pixelSize)))",
                },
            )
            template_sheet = next(
                (
                    s for s in template_meta.get("sheets", [])
                    if s.get("properties", {}).get("sheetId") == format_template_ws["id"]
                ),
                None,
            )
            template_data = (template_sheet or {}).get("data", [{}])[0]
            template_rows = (template_sheet or {}).get("properties", {}).get("gridProperties", {}).get("rowCount", sheet_rows)
            copy_rows = min(sheet_rows, template_rows or sheet_rows)
            reqs.append({"copyPaste": {
                "source": rng(0, copy_rows, 0, 44) | {"sheetId": format_template_ws["id"]},
                "destination": rng(0, copy_rows, 0, 44),
                "pasteType": "PASTE_FORMAT",
                "pasteOrientation": "NORMAL",
            }})
            for idx, meta in enumerate(template_data.get("columnMetadata", [])[:44]):
                px = meta.get("pixelSize")
                if px:
                    reqs.append(col_width(idx, idx + 1, px))
            for idx, meta in enumerate(template_data.get("rowMetadata", [])[:min(40, sheet_rows)]):
                px = meta.get("pixelSize")
                if px:
                    reqs.append(row_height(idx, idx + 1, px))
        except Exception:
            pass

    batch_update_spreadsheet(creds, sheet_id, reqs)

    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit#gid={sid}"
    return {
        "url": sheet_url,
        "tab_name": tab_name,
        "coding_count": len(coding),
        "robotics_count": len(robotics),
        "art_count": len(art),
        "total": len(classes),
    }
