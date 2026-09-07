"""
LMS TakeNote — FastAPI Server
- REST API: /api/classes, /api/teachers, /api/tp
- WebSocket: /ws  (push thông báo khi data cập nhật)
- Background scheduler: tự fetch mỗi 3 giờ
- Manual trigger: POST /api/refresh
- Token status: GET /api/token-status
"""
import sqlite3
import json
import os
import asyncio
import threading
import base64
import subprocess
import sys
import re
import html as html_lib
import requests
from difflib import SequenceMatcher
from datetime import datetime, timezone
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from supabase_cache import (
    read_api_cache,
    read_class_students_cache,
    read_classes_summary_cache,
    strip_class_slots,
    use_supabase_cache,
    write_class_students_cache,
)

# UTF-8 JSON response to fix Vietnamese encoding
class UTF8JSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False).encode("utf-8")

app = FastAPI(title="LMS TakeNote API", default_response_class=UTF8JSONResponse)

# ─────────────────────────────────────────────────────────────────────────────
DB_PATH   = os.path.join(os.path.dirname(__file__), "classroom_data.db")
ENV_PATH  = os.path.join(os.path.dirname(__file__), ".env")
FETCH_LOCK_PATH = os.path.join(os.path.dirname(__file__), ".fetch.lock")
FETCH_INTERVAL_HOURS = 3
GRAPHQL_URL = "https://lms-api.mindx.edu.vn/"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# WebSocket connection manager
# ─────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        self.active.discard(ws)

    async def broadcast(self, message: dict):
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        self.active -= dead

manager = ConnectionManager()

# ─────────────────────────────────────────────────────────────────────────────
# Fetch state
# ─────────────────────────────────────────────────────────────────────────────

fetch_state = {
    "is_fetching": False,
    "last_fetch": None,
    "last_status": "idle",
    "last_message": "",
    "next_fetch": None,
    "last_log": "",      # full stdout+stderr from last run
}

# Lưu subprocess hiện tại để có thể cancel
_fetch_process: subprocess.Popen | None = None


def _read_fetch_lock() -> dict:
    try:
        with open(FETCH_LOCK_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _get_process_command_line(pid: int) -> str:
    if os.name != "nt":
        return ""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"(Get-CimInstance Win32_Process -Filter \"ProcessId = {int(pid)}\").CommandLine",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        return ""
    return ""


def _pid_is_fetch_process(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                command_line = _get_process_command_line(pid)
                if command_line:
                    return "main.py" in command_line.replace("\\", "/").lower()
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _unlink_fetch_lock():
    try:
        os.unlink(FETCH_LOCK_PATH)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def external_fetch_lock() -> dict | None:
    lock = _read_fetch_lock()
    pid = int(lock.get("pid") or 0)
    if not pid:
        return None
    if _pid_is_fetch_process(pid):
        return lock
    _unlink_fetch_lock()
    return None


def current_fetch_state() -> dict:
    state = dict(fetch_state)
    if state["is_fetching"]:
        return state

    lock = external_fetch_lock()
    if lock:
        pid = int(lock.get("pid") or 0)
        state["is_fetching"] = True
        state["last_status"] = "running"
        state["last_message"] = f"Đang có tiến trình fetch khác chạy (PID {pid})"
        return state

    if state["last_status"] == "error" and "tiến trình fetch khác" in state.get("last_message", ""):
        state["last_status"] = "idle"
        state["last_message"] = ""
    return state


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def query(sql: str, params: tuple = ()) -> list[dict]:
    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def ensure_slot_comments_table():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS slot_comments (
                id                TEXT PRIMARY KEY,
                classId           TEXT NOT NULL,
                slotId            TEXT NOT NULL,
                sessionIndex      INTEGER,
                slotDate          TEXT,
                studentId         TEXT,
                studentName       TEXT,
                comment           TEXT,
                sendCommentStatus TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_slot_comments_classId ON slot_comments(classId)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_slot_comments_slotId  ON slot_comments(slotId)")
        conn.commit()
    finally:
        conn.close()


def ensure_slot_students_table():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS slot_students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                classId     TEXT NOT NULL,
                slotId      TEXT NOT NULL,
                studentId   TEXT,
                studentName TEXT,
                status      TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_slot_students_classId ON slot_students(classId)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_slot_students_slotId  ON slot_students(slotId)")
        conn.commit()
    finally:
        conn.close()


def ensure_class_students_table():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS class_students (
                id              TEXT PRIMARY KEY,
                classId         TEXT NOT NULL,
                studentId       TEXT,
                activeInClass   INTEGER DEFAULT 0,
                completed       INTEGER DEFAULT 0,
                attended        INTEGER DEFAULT 0,
                note            TEXT,
                grade           TEXT,
                retentionDate   TEXT,
                completionInfo  TEXT,
                student         TEXT,
                previousClass   TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_class_students_classId ON class_students(classId)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_class_students_studentId ON class_students(studentId)")
        conn.commit()
    finally:
        conn.close()


def get_class_student_rows(class_id: str) -> list[dict]:
    ensure_class_students_table()
    return query("""
        SELECT id, classId, studentId, activeInClass, completed, attended,
               note, grade, retentionDate, completionInfo, student, previousClass
        FROM class_students
        WHERE classId = ?
        ORDER BY id
    """, (class_id,))


def decode_class_student_row(row: dict) -> dict:
    def loads_json(value, fallback):
        try:
            return json.loads(value) if value else fallback
        except Exception:
            return fallback

    return {
        "id": row["id"],
        "classId": row["classId"],
        "studentId": row["studentId"],
        "activeInClass": bool(row["activeInClass"]),
        "completed": bool(row["completed"]),
        "attended": bool(row["attended"]),
        "note": row["note"],
        "grade": loads_json(row.get("grade"), row.get("grade")),
        "retentionDate": row["retentionDate"],
        "completionInfo": loads_json(row["completionInfo"], None),
        "student": loads_json(row["student"], {}),
        "previousClass": loads_json(row["previousClass"], None),
    }


def get_attended_student_ids(class_id: str) -> set[str]:
    if use_supabase_cache() and not os.path.exists(DB_PATH):
        return set()
    ensure_slot_students_table()
    rows = query("""
        SELECT DISTINCT studentId
        FROM slot_students
        WHERE classId = ? AND studentId IS NOT NULL AND studentId != ''
    """, (class_id,))
    return {row["studentId"] for row in rows}


def normalize_class_student(raw: dict, class_id: str, attended_ids: set[str], index: int) -> dict:
    student = raw.get("student") or {}
    customer = student.get("customer")
    student_id = raw.get("studentId") or student.get("id")
    completion_info = raw.get("completionInfo")
    previous_class = raw.get("previousClass")
    return {
        "id": raw.get("id") or raw.get("_id") or f"{class_id}:{student_id or index}",
        "classId": raw.get("classId") or class_id,
        "studentId": student_id,
        "learningMediumId": raw.get("learningMediumId"),
        "note": raw.get("note"),
        "activeInClass": bool(raw.get("activeInClass")),
        "completed": bool(raw.get("completed")),
        "completionInfo": {
            "status": (completion_info or {}).get("status"),
            "reason": (completion_info or {}).get("reason"),
            "description": (completion_info or {}).get("description"),
            "note": (completion_info or {}).get("note"),
        } if completion_info else None,
        "retentionDate": raw.get("retentionDate"),
        "grade": raw.get("grade"),
        "isTransfer": bool(raw.get("isTransfer")),
        "transfers": raw.get("transfers") or [],
        "previousClass": {
            "id": previous_class.get("id"),
            "name": previous_class.get("name"),
            "startDate": previous_class.get("startDate"),
        } if previous_class else None,
        "attended": student_id in attended_ids if student_id else False,
        "student": {
            "id": student_id,
            "fullName": student.get("fullName") or "Unknown",
            "status": student.get("status"),
            "waitingStatus": student.get("waitingStatus"),
            "phoneNumber": student.get("phoneNumber"),
            "email": student.get("email"),
            "gender": student.get("gender"),
            "dob": student.get("dob"),
            "address": student.get("address"),
            "imageUrl": student.get("imageUrl"),
            "facebook": student.get("facebook"),
            "zalo": student.get("zalo"),
            "school": student.get("school"),
            "contactPhoneNumber": student.get("contactPhoneNumber"),
            "customer": {
                "_id": (customer or {}).get("_id"),
                "fullName": (customer or {}).get("fullName"),
                "phoneNumber": (customer or {}).get("phoneNumber"),
                "email": (customer or {}).get("email"),
                "facebook": (customer or {}).get("facebook"),
                "zalo": (customer or {}).get("zalo"),
            } if customer else None,
            "studentId": student.get("studentId"),
            "isVip": bool(student.get("isVip")),
        },
    }


def class_sort_time(item: dict) -> str:
    return item.get("startDate") or item.get("endDate") or item.get("createdAt") or ""


def derive_previous_class(study_classes: list[dict], current_class_id: str) -> dict | None:
    if not study_classes:
        return None

    sorted_classes = sorted(study_classes, key=class_sort_time)
    current_index = next(
        (index for index, item in enumerate(sorted_classes) if item.get("id") == current_class_id),
        -1,
    )
    if current_index <= 0:
        return None

    previous = sorted_classes[current_index - 1]
    return {
        "id": previous.get("id"),
        "name": previous.get("name"),
        "startDate": previous.get("startDate"),
    }


def fetch_student_study_classes(student_id: str, headers: dict) -> list[dict]:
    payload = {
        "operationName": "StudentStudyClasses",
        "variables": {"studentId": student_id},
        "query": """query StudentStudyClasses($studentId: String) {
  studentStudyClasses(payload: {studentId: $studentId, paginationType: OFFSET, pageIndex: 0, itemsPerPage: 50}) {
    data {
      id
      name
      startDate
      endDate
      status
      createdAt
    }
  }
}""",
    }
    try:
        res = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=20)
        data = res.json()
        if res.status_code != 200 or data.get("errors"):
            return []
        return (((data.get("data") or {}).get("studentStudyClasses") or {}).get("data") or [])
    except Exception:
        return []


def save_class_students_to_sqlite(class_id: str, students: list[dict]):
    ensure_class_students_table()
    conn = get_db()
    try:
        conn.execute("DELETE FROM class_students WHERE classId=?", (class_id,))
        for item in students:
            student = item.get("student") or {}
            conn.execute("""
                INSERT OR REPLACE INTO class_students
                (id, classId, studentId, activeInClass, completed, attended,
                 note, grade, retentionDate, completionInfo, student, previousClass)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                item.get("id") or f"{class_id}:{item.get('studentId') or student.get('id') or student.get('fullName') or ''}",
                class_id,
                item.get("studentId") or student.get("id"),
                1 if item.get("activeInClass") else 0,
                1 if item.get("completed") else 0,
                1 if item.get("attended") else 0,
                item.get("note"),
                json.dumps(item.get("grade"), ensure_ascii=False),
                item.get("retentionDate"),
                json.dumps(item.get("completionInfo"), ensure_ascii=False),
                json.dumps(student, ensure_ascii=False),
                json.dumps(item.get("previousClass"), ensure_ascii=False),
            ))
        conn.commit()
    finally:
        conn.close()


def fetch_class_students_from_lms(class_id: str) -> list[dict]:
    token = read_token()
    if token:
        info = check_token(token)
        if not info["valid"] or info["remaining_minutes"] <= TOKEN_REFRESH_THRESHOLD:
            refresh_token_silent()
            token = read_token()
    if not token:
        raise RuntimeError("Không có LMS_TOKEN để tải học viên.")

    payload = {
        "operationName": "FindClassStudent",
        "variables": {"classId": class_id},
        "query": """query FindClassStudent($classId: String) {
  findClassStudent(payload: {classId: $classId}) {
    data {
      id
      classId
      studentId
      learningMediumId
      note
      activeInClass
      classSiteId
      createdBy
      createdAt
      lastModifiedAt
      lastModifiedBy
      completed
      completionInfo {
        status
        reason
        description
        note
      }
      retentionDate
      student {
        id
        fullName
        status
        waitingStatus
        phoneNumber
        email
        gender
        dob
        address
        imageUrl
        facebook
        zalo
        school
        contactPhoneNumber
        studentId
        isVip
        customer {
          _id
          fullName
          phoneNumber
          email
          facebook
          zalo
        }
      }
      isTransfer
      transfers {
        classFrom
        classTo
        dateFrom
        dateTo
      }
      grade {
        averageScore
        fileUrls
        linkUrls
      }
    }
  }
}""",
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    res = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=30)
    data = res.json()
    if res.status_code != 200 or data.get("errors"):
        message = data.get("errors", [{}])[0].get("message") if isinstance(data, dict) else res.text[:200]
        raise RuntimeError(message or f"HTTP {res.status_code}")

    attended_ids = get_attended_student_ids(class_id)
    rows = (((data.get("data") or {}).get("findClassStudent") or {}).get("data") or [])
    students = [normalize_class_student(row, class_id, attended_ids, index) for index, row in enumerate(rows)]

    for student in students:
        if student.get("previousClass"):
            continue
        student_id = student.get("studentId") or (student.get("student") or {}).get("id")
        if not student_id:
            continue
        study_classes = fetch_student_study_classes(student_id, headers)
        student["previousClass"] = derive_previous_class(study_classes, class_id)

    return students


def ensure_assignment_tables(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS assignment_records (
            classId     TEXT PRIMARY KEY,
            className   TEXT,
            centre      TEXT,
            block       TEXT,
            status      TEXT,
            updatedAt   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS assignment_students (
            id          TEXT,
            classId     TEXT NOT NULL,
            displayName TEXT,
            studentUid  TEXT,
            PRIMARY KEY (classId, studentUid)
        );
        CREATE TABLE IF NOT EXISTS assignment_lessons (
            id               TEXT,
            classId          TEXT NOT NULL,
            name             TEXT,
            type             TEXT,
            isActive         INTEGER DEFAULT 0,
            learningCourseId TEXT,
            displayOrder     INTEGER,
            PRIMARY KEY (classId, id)
        );
        CREATE TABLE IF NOT EXISTS assignment_submissions (
            id                TEXT PRIMARY KEY,
            classId           TEXT NOT NULL,
            type              TEXT,
            note              TEXT,
            score             REAL,
            status            TEXT,
            category          TEXT,
            lessonId          TEXT,
            learningCourseId  TEXT,
            studentUid        TEXT,
            studentOriginalId TEXT,
            classSessionId    TEXT,
            markedAt          TEXT,
            markedBy          TEXT,
            createdAt         TEXT,
            submittedAt       TEXT,
            submittedCount    INTEGER DEFAULT 0,
            contentJson       TEXT
        );
        CREATE TABLE IF NOT EXISTS assignment_teachers (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            classId TEXT NOT NULL,
            name    TEXT,
            email   TEXT,
            role    TEXT
        );
        CREATE TABLE IF NOT EXISTS assignment_fetch_errors (
            classId    TEXT PRIMARY KEY,
            className  TEXT,
            centre     TEXT,
            block      TEXT,
            status     TEXT,
            errorType  TEXT,
            message    TEXT,
            fetchedAt  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_assignment_students_classId ON assignment_students(classId);
        CREATE INDEX IF NOT EXISTS idx_assignment_lessons_classId ON assignment_lessons(classId);
        CREATE INDEX IF NOT EXISTS idx_assignment_submissions_classId ON assignment_submissions(classId);
        CREATE INDEX IF NOT EXISTS idx_assignment_submissions_lessonId ON assignment_submissions(lessonId);
        CREATE INDEX IF NOT EXISTS idx_assignment_submissions_studentUid ON assignment_submissions(studentUid);
    """)
    conn.commit()


def load_assignments_cache() -> list:
    cache_path = os.path.join(os.path.dirname(__file__), "public", "assignments.json")
    if not os.path.exists(cache_path):
        return []
    try:
        with open(cache_path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def normalize_comment_text(value: str | None) -> str:
    if not value:
        return ""
    text = html_lib.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def display_comment_text(value: str | None) -> str:
    if not value:
        return ""
    text = html_lib.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def longest_common_text(a: str, b: str) -> str:
    matcher = SequenceMatcher(None, a, b, autojunk=False)
    blocks = matcher.get_matching_blocks()
    best = max(blocks, key=lambda block: block.size, default=None)
    if not best or best.size < 8:
        return ""
    return a[best.a:best.a + best.size].strip()


def build_comment_duplicate_result(rows: list[dict], mode: str, threshold: int = 70, limit: int = 300) -> dict:
    matches = []
    total_pairs = 0

    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            if left["slotId"] == right["slotId"]:
                continue
            if mode == "same_student":
                left_student = left.get("studentId") or left.get("studentName")
                right_student = right.get("studentId") or right.get("studentName")
                if not left_student or left_student != right_student:
                    continue
            elif mode == "any_student":
                left_student = left.get("studentId") or left.get("studentName")
                right_student = right.get("studentId") or right.get("studentName")
                if left_student and right_student and left_student == right_student:
                    continue

            total_pairs += 1
            matcher = SequenceMatcher(None, left["normalized"], right["normalized"], autojunk=False)
            similarity = round(matcher.ratio() * 100)
            if similarity < threshold:
                continue

            matches.append({
                "id": f"{left['id']}::{right['id']}",
                "similarity": similarity,
                "commonText": longest_common_text(left["normalized"], right["normalized"]),
                "left": {
                    "slotId": left["slotId"],
                    "sessionIndex": left["sessionIndex"],
                    "slotDate": left["slotDate"],
                    "studentId": left["studentId"],
                    "studentName": left["studentName"],
                    "comment": left["displayText"],
                },
                "right": {
                    "slotId": right["slotId"],
                    "sessionIndex": right["sessionIndex"],
                    "slotDate": right["slotDate"],
                    "studentId": right["studentId"],
                    "studentName": right["studentName"],
                    "comment": right["displayText"],
                },
            })

    matches.sort(key=lambda item: item["similarity"], reverse=True)
    total_matches = len(matches)
    return {
        "totalPairs": total_pairs,
        "totalMatches": total_matches,
        "returnedMatches": min(total_matches, limit),
        "hasMore": total_matches > limit,
        "matches": matches[:limit],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Token helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_token() -> str | None:
    token = os.environ.get("LMS_TOKEN", "").strip().strip('"').strip("'")
    if token:
        return token
    if not os.path.exists(ENV_PATH):
        return None
    with open(ENV_PATH, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line.startswith("LMS_TOKEN="):
                return line[len("LMS_TOKEN="):].strip().strip('"').strip("'") or None
    return None


def read_env_value(key: str) -> str | None:
    if not os.path.exists(ENV_PATH):
        return None
    with open(ENV_PATH, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.strip() == key:
                return value.strip().strip('"').strip("'") or None
    return None


def check_token(token: str) -> dict:
    """Returns {valid, expires_at, remaining_minutes}"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {"valid": False, "expires_at": None, "remaining_minutes": 0}
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        remaining = exp - now
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc).isoformat()
        return {
            "valid": remaining > 0,
            "expires_at": expires_at,
            "remaining_minutes": max(0, int(remaining // 60)),
        }
    except Exception:
        return {"valid": False, "expires_at": None, "remaining_minutes": 0}


# ─────────────────────────────────────────────────────────────────────────────
# Auto token refresh
# ─────────────────────────────────────────────────────────────────────────────

TOKEN_REFRESH_INTERVAL = 50 * 60   # refresh mỗi 50 phút
TOKEN_REFRESH_THRESHOLD = 15       # refresh khi còn dưới 15 phút

IDTOKEN_SCRIPT = os.path.join(os.path.dirname(__file__), "get-idtoken.js")


def token_refresh_config_status() -> dict:
    has_api_key = bool(
        os.environ.get("FIREBASE_API_KEY")
        or os.environ.get("NEXT_PUBLIC_FIREBASE_API_KEY")
        or read_env_value("FIREBASE_API_KEY")
        or read_env_value("NEXT_PUBLIC_FIREBASE_API_KEY")
    )
    has_email = bool(os.environ.get("LMS_LOGIN_EMAIL") or read_env_value("LMS_LOGIN_EMAIL"))
    has_password = bool(os.environ.get("LMS_LOGIN_PASSWORD") or read_env_value("LMS_LOGIN_PASSWORD"))

    missing = []
    if not has_api_key:
        missing.append("FIREBASE_API_KEY")
    if not has_email:
        missing.append("LMS_LOGIN_EMAIL")
    if not has_password:
        missing.append("LMS_LOGIN_PASSWORD")

    return {
        "configured": not missing,
        "missing": missing,
    }


def set_runtime_token(new_token: str):
    """Use the refreshed token for this server process without touching .env."""
    os.environ["LMS_TOKEN"] = new_token


def refresh_token_silent() -> bool:
    """
    Gọi `node get-idtoken.js` để lấy token mới và lưu trong process hiện tại.
    Trả về True nếu thành công, False nếu thất bại.
    Hoàn toàn âm thầm — không broadcast WebSocket.
    """
    if not os.path.exists(IDTOKEN_SCRIPT):
        print("[token-refresh] get-idtoken.js khong tim thay, bo qua auto-refresh token")
        return False
    config = token_refresh_config_status()
    if not config["configured"]:
        print(f"[token-refresh] Thieu cau hinh: {', '.join(config['missing'])}")
        return False
    try:
        result = subprocess.run(
            ["node", IDTOKEN_SCRIPT],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.path.dirname(__file__),
        )
        if result.returncode != 0:
            print(f"[token-refresh] That bai: {result.stderr.strip()[:200]}")
            return False
        new_token = result.stdout.strip().splitlines()[-1].strip()
        if not new_token or len(new_token) < 100:
            print("[token-refresh] Token tra ve khong hop le")
            return False
        info = check_token(new_token)
        if not info["valid"]:
            print("[token-refresh] Token moi khong hop le hoac da het han")
            return False
        set_runtime_token(new_token)
        print(f"[token-refresh] Token da duoc lam moi, con {info.get('remaining_minutes', '?')} phut")
        return True
    except subprocess.TimeoutExpired:
        print("[token-refresh] Timeout")
        return False
    except FileNotFoundError:
        print("[token-refresh] Khong tim thay lenh 'node'. Hay cai Node.js 18+")
        return False
    except Exception as e:
        print(f"[token-refresh] Loi: {e}")
        return False


async def token_refresh_scheduler():
    """
    Background task: kiểm tra token mỗi 50 phút.
    Nếu token còn dưới TOKEN_REFRESH_THRESHOLD phút → tự refresh.
    """
    # Đợi 5 giây sau startup rồi kiểm tra lần đầu
    await asyncio.sleep(5)
    while True:
        token = read_token()
        if token:
            info = check_token(token)
            if not info["valid"] or info["remaining_minutes"] <= TOKEN_REFRESH_THRESHOLD:
                await asyncio.get_event_loop().run_in_executor(None, refresh_token_silent)
        await asyncio.sleep(TOKEN_REFRESH_INTERVAL)


# ─────────────────────────────────────────────────────────────────────────────
# Background fetch
# ─────────────────────────────────────────────────────────────────────────────

async def run_fetch(loop: asyncio.AbstractEventLoop):
    """Run main.py in subprocess and broadcast result via WebSocket."""
    global _fetch_process

    if fetch_state["is_fetching"]:
        return

    fetch_state["is_fetching"] = True
    fetch_state["last_status"] = "running"
    fetch_state["last_message"] = "Đang fetch dữ liệu..."

    await manager.broadcast({
        "type": "fetch_start",
        "message": "Đang cập nhật dữ liệu từ LMS...",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        # Kiểm tra token trước khi chạy — tự refresh nếu hết hạn
        token = read_token()
        if token:
            token_info = check_token(token)
            if not token_info["valid"] or token_info["remaining_minutes"] <= TOKEN_REFRESH_THRESHOLD:
                # Thử tự refresh trước
                refreshed = await asyncio.get_event_loop().run_in_executor(None, refresh_token_silent)
                if refreshed:
                    token = read_token()  # đọc lại token mới
                    token_info = check_token(token or "")
                if not token_info["valid"]:
                    fetch_state["last_status"] = "error"
                    fetch_state["last_message"] = "Token đã hết hạn và không thể tự làm mới"
                    await manager.broadcast({
                        "type": "fetch_done",
                        "status": "token_expired",
                        "message": "Token đã hết hạn. Vui lòng lấy token mới từ LMS và cập nhật vào .env",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    return

        def run_subprocess():
            global _fetch_process
            import tempfile

            # Dùng file tạm thay vì PIPE để tránh deadlock trên Windows với threading
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.log', delete=False,
                encoding='utf-8', prefix='lms_fetch_'
            ) as f:
                log_path = f.name

            try:
                with open(log_path, 'w', encoding='utf-8') as log_file:
                    _fetch_process = subprocess.Popen(
                        [sys.executable, "main.py", "--no-exit"],
                        stdout=log_file, stderr=log_file,
                        text=True, encoding="utf-8",
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                        cwd=os.path.dirname(__file__),
                    )
                try:
                    _fetch_process.wait(timeout=1800)
                    returncode = _fetch_process.returncode
                except subprocess.TimeoutExpired:
                    _fetch_process.kill()
                    _fetch_process.wait()
                    returncode = -1
            finally:
                _fetch_process = None

            # Đọc log từ file
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    output = f.read()
            except Exception:
                output = ""
            try:
                os.unlink(log_path)
            except Exception:
                pass

            return returncode, output, ""

        returncode, stdout, stderr = await asyncio.get_event_loop().run_in_executor(None, run_subprocess)

        full_log = (stdout or "") + "\n" + (stderr or "")
        fetch_state["last_log"] = full_log.strip()

        if returncode == -999:
            # Bị cancel bởi người dùng
            fetch_state["last_status"] = "idle"
            fetch_state["last_message"] = "Đã hủy cập nhật"
            await manager.broadcast({
                "type": "fetch_done",
                "status": "canceled",
                "message": "Đã hủy quá trình cập nhật.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        elif returncode == 2:
            # Token hết hạn (exit code 2) — thử tự refresh rồi retry 1 lần
            refreshed = await asyncio.get_event_loop().run_in_executor(None, refresh_token_silent)
            if refreshed:
                # Retry fetch với token mới
                fetch_state["last_message"] = "Token đã được làm mới, đang thử lại..."
                returncode2, stdout2, stderr2 = await asyncio.get_event_loop().run_in_executor(None, run_subprocess)
                if returncode2 == 0:
                    fetch_state["last_status"] = "success"
                    fetch_state["last_message"] = "Cập nhật thành công"
                    fetch_state["last_fetch"] = datetime.now(timezone.utc).isoformat()
                    await manager.broadcast({
                        "type": "fetch_done",
                        "status": "success",
                        "message": "Dữ liệu đã được cập nhật!",
                        "timestamp": fetch_state["last_fetch"],
                    })
                else:
                    fetch_state["last_status"] = "error"
                    fetch_state["last_message"] = "Lỗi sau khi làm mới token"
                    await manager.broadcast({
                        "type": "fetch_done",
                        "status": "error",
                        "message": "Lỗi fetch sau khi làm mới token",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
            else:
                fetch_state["last_status"] = "error"
                fetch_state["last_message"] = "Token đã hết hạn và không thể tự làm mới"
                await manager.broadcast({
                    "type": "fetch_done",
                    "status": "token_expired",
                    "message": "Token đã hết hạn. Vui lòng lấy token mới từ LMS và cập nhật vào .env",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
        elif returncode == 0:
            fetch_state["last_status"] = "success"
            fetch_state["last_message"] = "Cập nhật thành công"
            fetch_state["last_fetch"] = datetime.now(timezone.utc).isoformat()
            await manager.broadcast({
                "type": "fetch_done",
                "status": "success",
                "message": "Dữ liệu đã được cập nhật!",
                "timestamp": fetch_state["last_fetch"],
            })
        elif returncode == 9:
            fetch_state["last_status"] = "error"
            fetch_state["last_message"] = "Đang có tiến trình fetch khác chạy"
            await manager.broadcast({
                "type": "fetch_done",
                "status": "error",
                "message": "Đang có tiến trình fetch khác chạy. Hãy đợi hoặc hủy tiến trình cũ rồi thử lại.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            err_lines = [l for l in full_log.splitlines() if l.strip() and not l.startswith("  ")]
            err = err_lines[-1][:300] if err_lines else full_log[:300]
            fetch_state["last_status"] = "error"
            fetch_state["last_message"] = err
            await manager.broadcast({
                "type": "fetch_done",
                "status": "error",
                "message": f"Lỗi: {err}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        fetch_state["last_status"] = "error"
        fetch_state["last_message"] = str(e)
        await manager.broadcast({
            "type": "fetch_done",
            "status": "error",
            "message": f"Lỗi: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        fetch_state["is_fetching"] = False
        _fetch_process = None
        # Schedule next fetch
        next_dt = datetime.now(timezone.utc).timestamp() + FETCH_INTERVAL_HOURS * 3600
        fetch_state["next_fetch"] = datetime.fromtimestamp(next_dt, tz=timezone.utc).isoformat()


async def scheduler():
    """Background task: fetch every FETCH_INTERVAL_HOURS hours."""
    # Wait 10s after startup before first fetch
    await asyncio.sleep(10)
    while True:
        loop = asyncio.get_event_loop()
        await run_fetch(loop)
        await asyncio.sleep(FETCH_INTERVAL_HOURS * 3600)


@app.on_event("startup")
async def startup():
    # Set initial next_fetch time
    next_dt = datetime.now(timezone.utc).timestamp() + 10
    fetch_state["next_fetch"] = datetime.fromtimestamp(next_dt, tz=timezone.utc).isoformat()
    if os.getenv("DISABLE_AUTO_FETCH") != "1":
        asyncio.create_task(scheduler())
    asyncio.create_task(token_refresh_scheduler())
    print("LMS TakeNote API running")
    if os.getenv("DISABLE_AUTO_FETCH") == "1":
        print("   Auto-fetch disabled")
    else:
        print(f"   Auto-fetch every {FETCH_INTERVAL_HOURS}h")
    print(f"   Auto token refresh every {TOKEN_REFRESH_INTERVAL // 60}min")
    print(f"   WebSocket: ws://127.0.0.1:{os.getenv('API_PORT', '8000')}/ws")


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send current state on connect
    await ws.send_json({
        "type": "state",
        "fetch_state": current_fetch_state(),
        "token": {
            **check_token(read_token() or ""),
            "auto_refresh": token_refresh_config_status(),
        },
    })
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(ws)


# ─────────────────────────────────────────────────────────────────────────────
# REST endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/token-status")
def token_status():
    token = read_token()
    auto_refresh = token_refresh_config_status()
    if not token:
        return {
            "valid": False,
            "message": "Không tìm thấy token trong .env",
            "auto_refresh": auto_refresh,
        }
    info = check_token(token)
    message = f"Còn {info['remaining_minutes']} phút" if info["valid"] else "Token đã hết hạn"
    if not info["valid"] and not auto_refresh["configured"]:
        missing = ", ".join(auto_refresh["missing"])
        message = f"Token đã hết hạn; auto-refresh thiếu cấu hình: {missing}"
    return {**info, "message": message, "auto_refresh": auto_refresh}


@app.post("/api/refresh")
async def manual_refresh(background_tasks: BackgroundTasks):
    """Trigger manual fetch."""
    if fetch_state["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Đang fetch, vui lòng chờ..."})
    lock = external_fetch_lock()
    if lock:
        pid = int(lock.get("pid") or 0)
        return JSONResponse({"ok": False, "message": f"Đang có tiến trình fetch khác chạy (PID {pid})."})
    loop = asyncio.get_event_loop()
    asyncio.create_task(run_fetch(loop))
    return {"ok": True, "message": "Đã bắt đầu fetch dữ liệu..."}


@app.post("/api/cancel")
async def cancel_fetch():
    """Cancel đang fetch."""
    global _fetch_process
    if not fetch_state["is_fetching"]:
        lock = external_fetch_lock()
        if not lock:
            return JSONResponse({"ok": False, "message": "Không có quá trình fetch nào đang chạy."})
        pid = int(lock.get("pid") or 0)
        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True, timeout=5)
            except Exception:
                pass
        else:
            try:
                os.kill(pid, 9)
            except OSError:
                pass
        _unlink_fetch_lock()
        fetch_state["last_status"] = "idle"
        fetch_state["last_message"] = "Đã hủy cập nhật"
        await manager.broadcast({
            "type": "fetch_done",
            "status": "canceled",
            "message": "Đã hủy quá trình cập nhật.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {"ok": True, "message": "Đã hủy."}
    proc = _fetch_process
    if proc and proc.poll() is None:
        try:
            proc.kill()
            proc.wait()  # đợi process thực sự dừng
            fetch_state["is_fetching"] = False
            fetch_state["last_status"] = "idle"
            fetch_state["last_message"] = "Đã hủy cập nhật"
            await manager.broadcast({
                "type": "fetch_done",
                "status": "canceled",
                "message": "Đã hủy quá trình cập nhật.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return {"ok": True, "message": "Đã hủy."}
        except Exception as e:
            return JSONResponse({"ok": False, "message": str(e)})
    # Subprocess chưa start kịp, đánh dấu để run_fetch tự dừng
    fetch_state["is_fetching"] = False
    fetch_state["last_status"] = "idle"
    fetch_state["last_message"] = "Đã hủy cập nhật"
    await manager.broadcast({
        "type": "fetch_done",
        "status": "canceled",
        "message": "Đã hủy quá trình cập nhật.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "message": "Đã hủy."}


@app.post("/api/cancel/{module}")
async def cancel_module_fetch(module: str):
    """Cancel một module fetch đang chạy."""
    if module not in module_fetch_state:
        return JSONResponse({"ok": False, "message": "Module không hợp lệ."}, status_code=404)

    state = module_fetch_state[module]
    if not state["is_fetching"]:
        return JSONResponse({"ok": False, "message": f"Không có quá trình tải {module} nào đang chạy."})

    with _module_fetch_process_lock:
        _module_cancel_requested.add(module)
        proc = _module_fetch_processes.get(module)

    if proc and proc.poll() is None:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass

    state["is_fetching"] = False
    state["last_status"] = "idle"
    state["last_message"] = "Đã hủy tải dữ liệu"
    await manager.broadcast({
        "type": "module_fetch_done",
        "module": module,
        "status": "idle",
        "message": f"Đã hủy tải dữ liệu {module}.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    return {"ok": True, "message": "Đã hủy."}


@app.get("/api/fetch-status")
def fetch_status():
    return current_fetch_state()


@app.get("/api/fetch-log")
def fetch_log():
    """Return full log from last fetch run for debugging."""
    return {"log": fetch_state.get("last_log", ""), "status": fetch_state["last_status"]}


# ─────────────────────────────────────────────────────────────────────────────
# Per-module refresh endpoints
# ─────────────────────────────────────────────────────────────────────────────

# Trạng thái fetch riêng cho từng module (độc lập với full fetch)
module_fetch_state: dict[str, dict] = {
    "classes":  {"is_fetching": False, "last_status": "idle", "last_message": ""},
    "teachers": {"is_fetching": False, "last_status": "idle", "last_message": ""},
    "tp":       {"is_fetching": False, "last_status": "idle", "last_message": ""},
    "cp":       {"is_fetching": False, "last_status": "idle", "last_message": ""},
    "oh":       {"is_fetching": False, "last_status": "idle", "last_message": ""},
    "assignments": {"is_fetching": False, "last_status": "idle", "last_message": ""},
}
_module_fetch_processes: dict[str, subprocess.Popen] = {}
_module_cancel_requested: set[str] = set()
_module_fetch_process_lock = threading.Lock()


async def run_module_fetch(module: str):
    """Chạy fetch cho 1 module cụ thể trong subprocess."""
    state = module_fetch_state[module]
    if state["is_fetching"]:
        return

    state["is_fetching"] = True
    state["last_status"] = "running"
    state["last_message"] = f"Đang tải {module}..."

    await manager.broadcast({
        "type": "module_fetch_start",
        "module": module,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    try:
        # Tự refresh token nếu cần
        token = read_token()
        if token:
            token_info = check_token(token)
            if not token_info["valid"] or token_info["remaining_minutes"] <= TOKEN_REFRESH_THRESHOLD:
                await asyncio.get_event_loop().run_in_executor(None, refresh_token_silent)

        def run_subprocess():
            import tempfile
            proc = None
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.log', delete=False,
                encoding='utf-8', prefix=f'lms_{module}_'
            ) as f:
                log_path = f.name
            try:
                with open(log_path, 'w', encoding='utf-8') as log_file:
                    proc = subprocess.Popen(
                        [sys.executable, "main.py", f"--only={module}"],
                        stdout=log_file, stderr=log_file,
                        text=True, encoding="utf-8",
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                        cwd=os.path.dirname(__file__),
                    )
                    with _module_fetch_process_lock:
                        _module_fetch_processes[module] = proc
                try:
                    proc.wait(timeout=600)
                    with _module_fetch_process_lock:
                        canceled = module in _module_cancel_requested
                    returncode = -999 if canceled else proc.returncode
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    returncode = -1
            finally:
                with _module_fetch_process_lock:
                    if proc is not None and _module_fetch_processes.get(module) is proc:
                        _module_fetch_processes.pop(module, None)
                    _module_cancel_requested.discard(module)
            try:
                with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                    output = f.read()
            except Exception:
                output = ""
            try:
                os.unlink(log_path)
            except Exception:
                pass
            return returncode, output

        returncode, output = await asyncio.get_event_loop().run_in_executor(None, run_subprocess)

        if returncode == -999:
            state["last_status"] = "idle"
            state["last_message"] = "Đã hủy tải dữ liệu"
            await manager.broadcast({
                "type": "module_fetch_done",
                "module": module,
                "status": "idle",
                "message": f"Đã hủy tải dữ liệu {module}.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        elif returncode == 0:
            state["last_status"] = "success"
            state["last_message"] = "Tải thành công"
            await manager.broadcast({
                "type": "module_fetch_done",
                "module": module,
                "status": "success",
                "message": f"Đã tải xong dữ liệu {module}!",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Thông báo để UI reload data
            window_event = {
                "classes":  "lms-data-updated",
                "teachers": "lms-data-updated",
                "tp":       "lms-tp-updated",
                "cp":       "lms-cp-updated",
                "oh":       "lms-oh-updated",
                "assignments": "lms-assignments-updated",
            }
            await manager.broadcast({
                "type": "data_updated",
                "module": module,
                "event": window_event.get(module, "lms-data-updated"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        elif returncode == 9:
            state["last_status"] = "error"
            state["last_message"] = "Đang có tiến trình fetch khác chạy"
            await manager.broadcast({
                "type": "module_fetch_done",
                "module": module,
                "status": "error",
                "message": "Đang có tiến trình fetch khác chạy. Hãy đợi hoặc hủy tiến trình cũ rồi thử lại.",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        else:
            err_lines = [l for l in output.splitlines() if l.strip()]
            err = err_lines[-1][:200] if err_lines else "Lỗi không xác định"
            state["last_status"] = "error"
            state["last_message"] = err
            await manager.broadcast({
                "type": "module_fetch_done",
                "module": module,
                "status": "error",
                "message": f"Lỗi: {err}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        state["last_status"] = "error"
        state["last_message"] = str(e)
        await manager.broadcast({
            "type": "module_fetch_done",
            "module": module,
            "status": "error",
            "message": f"Lỗi: {e}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        state["is_fetching"] = False


@app.post("/api/refresh/classes")
async def refresh_classes():
    if module_fetch_state["classes"]["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Đang tải classes..."})
    asyncio.create_task(run_module_fetch("classes"))
    return {"ok": True, "message": "Đang tải dữ liệu lớp học..."}


@app.post("/api/refresh/teachers")
async def refresh_teachers():
    if module_fetch_state["teachers"]["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Đang tải teachers..."})
    asyncio.create_task(run_module_fetch("teachers"))
    return {"ok": True, "message": "Đang tải dữ liệu giáo viên..."}


@app.post("/api/refresh/tp")
async def refresh_tp():
    if module_fetch_state["tp"]["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Đang tải TP..."})
    asyncio.create_task(run_module_fetch("tp"))
    return {"ok": True, "message": "Đang tải dữ liệu TP..."}


@app.post("/api/refresh/cp")
async def refresh_cp():
    if module_fetch_state["cp"]["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Đang tải CP..."})
    asyncio.create_task(run_module_fetch("cp"))
    return {"ok": True, "message": "Đang tải dữ liệu CP..."}


@app.post("/api/refresh/oh")
async def refresh_oh():
    if module_fetch_state["oh"]["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Đang tải OH..."})
    asyncio.create_task(run_module_fetch("oh"))
    return {"ok": True, "message": "Đang tải dữ liệu OH..."}


@app.post("/api/refresh/assignments")
async def refresh_assignments():
    if module_fetch_state["assignments"]["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Dang tai assignments..."})
    asyncio.create_task(run_module_fetch("assignments"))
    return {"ok": True, "message": "Dang tai du lieu bai tap..."}


@app.get("/api/module-fetch-status")
def get_module_fetch_status():
    return module_fetch_state


# ─────────────────────────────────────────────────────────────────────────────
# DEMO endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/demo/classes")
async def get_demo_classes(date: str, date_to: str = ""):
    """Lấy danh sách lớp có buổi 14 trong khoảng ngày chỉ định (YYYY-MM-DD)."""
    try:
        from fetch_demo import fetch_demo_classes
        loop = asyncio.get_event_loop()
        classes = await loop.run_in_executor(None, lambda: fetch_demo_classes(date, date_to))
        return classes
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/demo/export")
async def export_demo_to_sheet(request: Request):
    """Xuất danh sách lớp ra Google Sheet, tạo tab mới."""
    body = await request.json()
    date = body.get("date", "")
    date_to = body.get("date_to", "")
    provided_classes = body.get("classes")
    if not date:
        return JSONResponse({"error": "Thiếu tham số date"}, status_code=400)
    try:
        from fetch_demo import fetch_demo_classes, export_to_sheet, is_running_class
        loop = asyncio.get_event_loop()
        if isinstance(provided_classes, list) and all(isinstance(c, dict) and "status" in c for c in provided_classes):
            classes = [c for c in provided_classes if is_running_class(c)]
        else:
            classes = await loop.run_in_executor(None, lambda: fetch_demo_classes(date, date_to))
        result = await loop.run_in_executor(None, lambda: export_to_sheet(classes, date, date_to))
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/classes")
def get_classes(include_slot_students: bool = False, include_students: bool = False, include_slots: bool = True):
    if use_supabase_cache():
        try:
            if include_slots:
                cached = read_api_cache("classes")
                if cached is None:
                    cached = read_classes_summary_cache()
            else:
                cached = read_classes_summary_cache()
            if cached is None and not include_slots:
                full_cache = read_api_cache("classes")
                cached = strip_class_slots(full_cache) if isinstance(full_cache, list) else None
            if cached is not None:
                return cached
        except Exception as e:
            return JSONResponse({"error": f"Supabase cache error: {e}"}, status_code=503)
        return JSONResponse(
            {"error": "Supabase classes cache missing. Run python scripts/sync_supabase_cache.py."},
            status_code=503,
        )

    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found. Run python main.py first."}, status_code=503)

    classes = query("""
        SELECT id, name, status, course, centre, block, level, sessions,
               studentCount, attendedCount, completedCount, completionRate,
               commentPercentage, totalSlotsWithStudents, slotsWithFullComments,
               startDate, endDate, createdAt
        FROM classes ORDER BY createdAt DESC
    """)
    if not classes:
        return []

    ids = [c["id"] for c in classes]
    placeholders = ",".join("?" * len(ids))

    teachers_rows = query(
        f"SELECT classId, name, email, role FROM class_teachers WHERE classId IN ({placeholders})",
        tuple(ids)
    )
    slots_rows: list[dict] = []
    if include_slots:
        slots_rows = query(
            f"""SELECT classId, id, date, startTime, endTime, commentStatus,
                       studentsInSlot, studentsWithComment
                FROM slots WHERE classId IN ({placeholders}) ORDER BY date""",
            tuple(ids)
        )
    slot_students_rows: list[dict] = []
    if include_slots and include_slot_students:
        ensure_slot_students_table()
        slot_students_rows = query(
            f"""SELECT classId, slotId, studentId, studentName, status
                FROM slot_students WHERE classId IN ({placeholders}) ORDER BY id""",
            tuple(ids)
        )
    class_students_rows: list[dict] = []
    if include_students:
        ensure_class_students_table()
        class_students_rows = query(
            f"""SELECT id, classId, studentId, activeInClass, completed, attended,
                       note, grade, retentionDate, completionInfo, student, previousClass
                FROM class_students WHERE classId IN ({placeholders}) ORDER BY id""",
            tuple(ids)
        )
    incomplete_rows = query(
        f"SELECT classId, name FROM incomplete_students WHERE classId IN ({placeholders})",
        tuple(ids)
    )

    teachers_map: dict[str, list] = {}
    for t in teachers_rows:
        teachers_map.setdefault(t["classId"], []).append(
            {"name": t["name"], "email": t["email"], "role": t["role"]}
        )

    slots_map: dict[str, list] = {}
    for s in slots_rows:
        slots_map.setdefault(s["classId"], []).append({
            "id": s["id"], "date": s["date"],
            "startTime": s["startTime"], "endTime": s["endTime"],
            "commentStatus": s["commentStatus"],
            "studentsInSlot": s["studentsInSlot"],
            "studentsWithComment": s["studentsWithComment"],
        })

    if include_slots and include_slot_students:
        slot_students_map: dict[str, list] = {}
        for student in slot_students_rows:
            slot_students_map.setdefault(student["slotId"], []).append({
                "id": student["studentId"],
                "name": student["studentName"],
                "status": student["status"],
            })

        for slot_list in slots_map.values():
            for slot in slot_list:
                slot["students"] = slot_students_map.get(slot["id"], [])

    class_students_map: dict[str, list] = {}
    if include_students:
        for row in class_students_rows:
            class_students_map.setdefault(row["classId"], []).append(decode_class_student_row(row))

    incomplete_map: dict[str, list] = {}
    for r in incomplete_rows:
        incomplete_map.setdefault(r["classId"], []).append(r["name"])

    for c in classes:
        cid = c["id"]
        c["teachers"] = teachers_map.get(cid, [])
        c["slots"] = slots_map.get(cid, [])
        c["incompleteStudents"] = incomplete_map.get(cid, [])
        if include_students:
            c["students"] = class_students_map.get(cid, [])

    return classes


@app.get("/api/classes/{class_id}/students")
def get_class_students(class_id: str):
    if use_supabase_cache():
        try:
            cached = read_class_students_cache(class_id)
        except Exception:
            cached = None
        try:
            students = fetch_class_students_from_lms(class_id)
            write_class_students_cache(class_id, students)
            return students
        except Exception as e:
            if cached:
                return cached
            return JSONResponse({"error": str(e)}, status_code=400)

    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found."}, status_code=503)

    rows = get_class_student_rows(class_id)
    try:
        students = fetch_class_students_from_lms(class_id)
        save_class_students_to_sqlite(class_id, students)
        return students
    except Exception as e:
        if rows:
            return [decode_class_student_row(row) for row in rows]
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/classes/{class_id}/slot-students")
def get_class_slot_students(class_id: str):
    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found."}, status_code=503)

    ensure_slot_students_table()
    rows = query("""
        SELECT slotId, studentId, studentName, status
        FROM slot_students
        WHERE classId = ?
        ORDER BY id
    """, (class_id,))

    result: dict[str, list] = {}
    for row in rows:
        result.setdefault(row["slotId"], []).append({
            "id": row["studentId"],
            "name": row["studentName"],
            "status": row["status"],
        })
    return result


@app.get("/api/assignments")
def get_assignments():
    if use_supabase_cache():
        try:
            cached = read_api_cache("assignments")
            if cached is not None:
                return {"records": cached, "errors": []}
        except Exception as e:
            return JSONResponse({"error": f"Supabase cache error: {e}"}, status_code=503)
        return JSONResponse(
            {"error": "Supabase cache missing 'assignments'. Run python scripts/sync_supabase_cache.py."},
            status_code=503,
        )

    cached = load_assignments_cache()
    if not os.path.exists(DB_PATH):
        if cached:
            return cached
        return JSONResponse({"error": "DB not found."}, status_code=503)

    conn = get_db()
    try:
        ensure_assignment_tables(conn)
        records = [dict(r) for r in conn.execute("""
            SELECT classId, className, centre, block, status
            FROM assignment_records
            ORDER BY className
        """).fetchall()]
        error_rows = [dict(r) for r in conn.execute("""
            SELECT e.classId, e.className, e.centre, e.block, e.status,
                   e.errorType, e.message, e.fetchedAt
            FROM assignment_fetch_errors e
            LEFT JOIN assignment_records ar ON ar.classId = e.classId
            WHERE ar.classId IS NULL
            ORDER BY e.fetchedAt DESC, e.className
        """).fetchall()]
        if not records:
            return {"records": cached, "errors": error_rows}

        student_counts = {
            r["classId"]: r["total"]
            for r in conn.execute("""
                SELECT classId, COUNT(*) AS total
                FROM assignment_students
                GROUP BY classId
            """).fetchall()
        }
        lesson_counts = {
            r["classId"]: r["total"]
            for r in conn.execute("""
                SELECT classId, COUNT(*) AS total
                FROM assignment_lessons
                WHERE isActive = 1
                GROUP BY classId
            """).fetchall()
        }
        summary_rows = [dict(r) for r in conn.execute("""
            SELECT
                classId,
                COUNT(*) AS expectedCount,
                SUM(CASE
                    WHEN UPPER(COALESCE(status, '')) IN ('SUBMITTED', 'MARKED')
                         OR NULLIF(TRIM(COALESCE(submittedAt, '')), '') IS NOT NULL
                         OR COALESCE(submittedCount, 0) > 0
                    THEN 1 ELSE 0 END) AS submittedCount,
                SUM(CASE
                    WHEN (
                        UPPER(COALESCE(status, '')) IN ('SUBMITTED', 'MARKED')
                        OR NULLIF(TRIM(COALESCE(submittedAt, '')), '') IS NOT NULL
                        OR COALESCE(submittedCount, 0) > 0
                    ) AND UPPER(COALESCE(status, '')) NOT IN ('REDO', 'RE_SUBMITTED')
                    THEN 1 ELSE 0 END) AS gradableSubmittedCount,
                SUM(CASE
                    WHEN (
                        UPPER(COALESCE(status, '')) IN ('SUBMITTED', 'MARKED')
                        OR NULLIF(TRIM(COALESCE(submittedAt, '')), '') IS NOT NULL
                        OR COALESCE(submittedCount, 0) > 0
                    ) AND UPPER(COALESCE(status, '')) NOT IN ('REDO', 'RE_SUBMITTED') AND (
                        UPPER(COALESCE(status, '')) = 'MARKED'
                        OR NULLIF(TRIM(COALESCE(markedAt, '')), '') IS NOT NULL
                        OR NULLIF(TRIM(COALESCE(markedBy, '')), '') IS NOT NULL
                    )
                    THEN 1 ELSE 0 END) AS markedCount,
                SUM(CASE
                    WHEN UPPER(COALESCE(status, '')) = 'IN_PROGRESS'
                    THEN 1 ELSE 0 END) AS inProgressCount,
                AVG(CASE
                    WHEN (
                        UPPER(COALESCE(status, '')) IN ('SUBMITTED', 'MARKED')
                        OR NULLIF(TRIM(COALESCE(submittedAt, '')), '') IS NOT NULL
                        OR COALESCE(submittedCount, 0) > 0
                    ) AND UPPER(COALESCE(status, '')) NOT IN ('REDO', 'RE_SUBMITTED') AND COALESCE(score, 0) > 0
                    THEN score ELSE NULL END) AS averageScore
            FROM assignment_submissions
            WHERE UPPER(COALESCE(type, '')) = 'UPLOAD_FILE'
               OR UPPER(COALESCE(category, '')) LIKE 'PRACTICE_TASK%'
            GROUP BY classId
        """).fetchall()]
        teachers_rows = [dict(r) for r in conn.execute("""
            SELECT classId, name, email, role
            FROM assignment_teachers
        """).fetchall()]
    finally:
        conn.close()

    teachers_map: dict[str, list] = {}
    for t in teachers_rows:
        teachers_map.setdefault(t["classId"], []).append({
            "name": t["name"],
            "email": t["email"],
            "role": t["role"],
        })

    summary_map = {r["classId"]: r for r in summary_rows}
    for record in records:
        cid = record["classId"]
        summary = summary_map.get(cid, {})
        submitted_count = int(summary.get("submittedCount") or 0)
        gradable_value = summary.get("gradableSubmittedCount")
        gradable_submitted_count = int(submitted_count if gradable_value is None else gradable_value or 0)
        marked_count = int(summary.get("markedCount") or 0)
        student_count = int(student_counts.get(cid, 0) or 0)
        lesson_count = int(lesson_counts.get(cid, 0) or 0)
        expected_count = int(summary.get("expectedCount") or 0) or student_count * lesson_count
        record["teachers"] = teachers_map.get(cid, [])
        record["students"] = []
        record["lessons"] = []
        record["submissions"] = []
        record["studentCount"] = student_count
        record["lessonCount"] = lesson_count
        record["expectedCount"] = expected_count
        record["submittedCount"] = submitted_count
        record["gradableSubmittedCount"] = gradable_submitted_count
        record["markedCount"] = marked_count
        record["inProgressCount"] = int(summary.get("inProgressCount") or 0)
        record["needsMarkingCount"] = max(0, gradable_submitted_count - marked_count)
        avg_score = summary.get("averageScore")
        record["averageScore"] = round(avg_score) if avg_score is not None else None

    return {"records": records, "errors": error_rows}


def build_assignment_detail(conn: sqlite3.Connection, class_id: str) -> dict | None:
    record_row = conn.execute("""
        SELECT classId, className, centre, block, status
        FROM assignment_records
        WHERE classId = ?
    """, (class_id,)).fetchone()
    if not record_row:
        return None

    record = dict(record_row)
    students_rows = [dict(r) for r in conn.execute("""
        SELECT id, displayName, studentUid
        FROM assignment_students
        WHERE classId = ?
        ORDER BY displayName
    """, (class_id,)).fetchall()]
    lessons_rows = [dict(r) for r in conn.execute("""
        SELECT id, name, type, isActive, learningCourseId, displayOrder
        FROM assignment_lessons
        WHERE classId = ?
        ORDER BY displayOrder
    """, (class_id,)).fetchall()]
    submissions_rows = [dict(r) for r in conn.execute("""
        SELECT id, classId, type, note, score, status, category, lessonId,
               learningCourseId, studentUid, studentOriginalId, classSessionId,
               markedAt, markedBy, createdAt, submittedAt, submittedCount, contentJson
        FROM assignment_submissions
        WHERE classId = ?
        ORDER BY lessonId, studentUid
    """, (class_id,)).fetchall()]
    teachers_rows = [dict(r) for r in conn.execute("""
        SELECT name, email, role
        FROM assignment_teachers
        WHERE classId = ?
    """, (class_id,)).fetchall()]

    record["students"] = [
        {"id": s["id"], "displayName": s["displayName"], "studentUid": s["studentUid"]}
        for s in students_rows
    ]
    record["lessons"] = [
        {
            "id": lesson["id"],
            "name": lesson["name"],
            "type": lesson["type"],
            "isActive": bool(lesson["isActive"]),
            "learningCourseId": lesson["learningCourseId"],
            "displayOrder": lesson["displayOrder"] or 0,
        }
        for lesson in lessons_rows
    ]
    submissions = []
    for submission in submissions_rows:
        try:
            content = json.loads(submission.get("contentJson") or "{}")
        except Exception:
            content = {}
        submissions.append({
            "id": submission["id"],
            "type": submission["type"],
            "note": submission["note"],
            "score": submission["score"] or 0,
            "status": submission["status"],
            "category": submission["category"],
            "classId": submission["classId"],
            "lessonId": submission["lessonId"],
            "learningCourseId": submission["learningCourseId"],
            "studentUid": submission["studentUid"],
            "studentOriginalId": submission["studentOriginalId"],
            "classSessionId": submission["classSessionId"],
            "markedAt": submission["markedAt"],
            "markedBy": submission["markedBy"],
            "createdAt": submission["createdAt"],
            "submittedAt": submission["submittedAt"],
            "submittedCount": submission["submittedCount"] or 0,
            "content": content,
        })
    record["submissions"] = submissions
    record["teachers"] = [
        {"name": t["name"], "email": t["email"], "role": t["role"]}
        for t in teachers_rows
    ]
    return record


@app.get("/api/assignments/{class_id}")
def get_assignment_detail(class_id: str):
    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found."}, status_code=503)

    conn = get_db()
    try:
        ensure_assignment_tables(conn)
        detail = build_assignment_detail(conn, class_id)
    finally:
        conn.close()

    if not detail:
        return JSONResponse({"error": "Assignment data not found."}, status_code=404)
    return detail


@app.get("/api/classes/{class_id}/comment-duplicates")
def get_class_comment_duplicates(class_id: str):
    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found. Run python main.py first."}, status_code=503)

    ensure_slot_comments_table()
    rows = query("""
        SELECT id, classId, slotId, sessionIndex, slotDate, studentId,
               studentName, comment, sendCommentStatus
        FROM slot_comments
        WHERE classId = ?
        ORDER BY sessionIndex, studentName
    """, (class_id,))

    comments = []
    for row in rows:
        normalized = normalize_comment_text(row.get("comment"))
        if not normalized:
            continue
        item = dict(row)
        item["normalized"] = normalized
        item["displayText"] = display_comment_text(row.get("comment"))
        comments.append(item)

    threshold = 70
    limit = 300
    return {
        "classId": class_id,
        "threshold": threshold,
        "totalComments": len(comments),
        "modes": {
            "same_student": build_comment_duplicate_result(comments, "same_student", threshold, limit),
            "any_student": build_comment_duplicate_result(comments, "any_student", threshold, limit),
        },
    }


@app.get("/api/teachers")
def get_teachers():
    if use_supabase_cache():
        try:
            cached = read_api_cache("teachers")
            if cached is not None:
                return cached
        except Exception as e:
            return JSONResponse({"error": f"Supabase cache error: {e}"}, status_code=503)
        return JSONResponse(
            {"error": "Supabase cache missing 'teachers'. Run python scripts/sync_supabase_cache.py."},
            status_code=503,
        )

    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found."}, status_code=503)

    teachers = query("SELECT * FROM teachers ORDER BY fullName")
    if not teachers:
        return []

    ids = [t["id"] for t in teachers]
    placeholders = ",".join("?" * len(ids))

    centres_rows = query(
        f"SELECT teacherId, centre FROM teacher_centres WHERE teacherId IN ({placeholders})",
        tuple(ids)
    )
    blocks_rows = query(
        f"SELECT teacherId, block FROM teacher_blocks WHERE teacherId IN ({placeholders})",
        tuple(ids)
    )
    cl_rows = query(
        f"SELECT teacherId, courseLine FROM teacher_course_lines WHERE teacherId IN ({placeholders})",
        tuple(ids)
    )

    centres_map: dict[str, list] = {}
    for r in centres_rows:
        centres_map.setdefault(r["teacherId"], []).append(r["centre"])

    blocks_map: dict[str, list] = {}
    for r in blocks_rows:
        blocks_map.setdefault(r["teacherId"], []).append(r["block"])

    cl_map: dict[str, list] = {}
    for r in cl_rows:
        cl_map.setdefault(r["teacherId"], []).append(r["courseLine"])

    for t in teachers:
        tid = t["id"]
        t["centres"] = centres_map.get(tid, [])
        t["blocks"] = blocks_map.get(tid, [])
        t["courseLines"] = cl_map.get(tid, [])

    return teachers


@app.get("/api/tp")
def get_tp():
    if use_supabase_cache():
        try:
            cached = read_api_cache("tp")
            if cached is not None:
                return cached
        except Exception as e:
            return JSONResponse({"error": f"Supabase cache error: {e}"}, status_code=503)
        return JSONResponse(
            {"error": "Supabase cache missing 'tp'. Run python scripts/sync_supabase_cache.py."},
            status_code=503,
        )

    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found."}, status_code=503)

    records = query("SELECT * FROM tp_records ORDER BY className")
    if not records:
        return []

    ids = [r["classId"] for r in records]
    placeholders = ",".join("?" * len(ids))

    students_rows = query(
        f"""SELECT classId, round, name, score, textAnswers
            FROM tp_students WHERE classId IN ({placeholders}) ORDER BY classId, round""",
        tuple(ids)
    )
    teachers_rows = query(
        f"SELECT classId, name, email, role FROM tp_teachers WHERE classId IN ({placeholders})",
        tuple(ids)
    )

    students_map: dict[str, dict] = {}
    for s in students_rows:
        cid = s["classId"]
        if cid not in students_map:
            students_map[cid] = {"tp1_students": [], "tp2_students": []}
        try:
            text_answers = json.loads(s["textAnswers"] or "[]")
        except Exception:
            text_answers = []
        entry = {"name": s["name"], "score": s["score"], "textAnswers": text_answers}
        if s["round"] == 1:
            students_map[cid]["tp1_students"].append(entry)
        else:
            students_map[cid]["tp2_students"].append(entry)

    teachers_map: dict[str, list] = {}
    for t in teachers_rows:
        teachers_map.setdefault(t["classId"], []).append(
            {"name": t["name"], "email": t["email"], "role": t["role"]}
        )

    for r in records:
        cid = r["classId"]
        r["teachers"] = teachers_map.get(cid, [])
        r["tp1_students"] = students_map.get(cid, {}).get("tp1_students", [])
        r["tp2_students"] = students_map.get(cid, {}).get("tp2_students", [])

    return records


@app.get("/api/cp")
def get_cp():
    if use_supabase_cache():
        try:
            cached = read_api_cache("cp")
            if cached is not None:
                return cached
        except Exception as e:
            return JSONResponse({"error": f"Supabase cache error: {e}"}, status_code=503)
        return JSONResponse(
            {"error": "Supabase cache missing 'cp'. Run python scripts/sync_supabase_cache.py."},
            status_code=503,
        )

    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found."}, status_code=503)

    records = query("SELECT * FROM cp_records ORDER BY className")
    if not records:
        return []

    ids = [r["classId"] for r in records]
    placeholders = ",".join("?" * len(ids))

    students_rows = query(
        f"""SELECT classId, round, name, theoryScore, practicalScore
            FROM cp_students WHERE classId IN ({placeholders}) ORDER BY classId, round""",
        tuple(ids)
    )
    teachers_rows = query(
        f"SELECT classId, name, email, role FROM cp_teachers WHERE classId IN ({placeholders})",
        tuple(ids)
    )

    students_map: dict[str, dict] = {}
    for s in students_rows:
        cid = s["classId"]
        if cid not in students_map:
            students_map[cid] = {"cp1_students": [], "cp2_students": []}
        entry = {"name": s["name"], "theoryScore": s["theoryScore"], "practicalScore": s["practicalScore"]}
        if s["round"] == 1:
            students_map[cid]["cp1_students"].append(entry)
        else:
            students_map[cid]["cp2_students"].append(entry)

    teachers_map: dict[str, list] = {}
    for t in teachers_rows:
        teachers_map.setdefault(t["classId"], []).append(
            {"name": t["name"], "email": t["email"], "role": t["role"]}
        )

    for r in records:
        cid = r["classId"]
        r["teachers"] = teachers_map.get(cid, [])
        r["cp1_students"] = students_map.get(cid, {}).get("cp1_students", [])
        r["cp2_students"] = students_map.get(cid, {}).get("cp2_students", [])

    return records


@app.get("/api/oh")
def get_oh():
    if use_supabase_cache():
        try:
            cached = read_api_cache("oh")
            if cached is not None:
                return cached
        except Exception as e:
            return JSONResponse({"error": f"Supabase cache error: {e}"}, status_code=503)
        return JSONResponse(
            {"error": "Supabase cache missing 'oh'. Run python scripts/sync_supabase_cache.py."},
            status_code=503,
        )

    if not os.path.exists(DB_PATH):
        return JSONResponse({"error": "DB not found."}, status_code=503)

    records = query("""
        SELECT id, startTime, endTime, status,
               centreId, centreName, centreShortName,
               teacherId, teacherFullName, teacherUsername, teacherEmail,
               note, managerNote, type, studentCount, createdByUsername, createdAt
        FROM oh_records
        ORDER BY startTime DESC
    """)
    if not records:
        return []

    ids = [r["id"] for r in records]
    placeholders = ",".join("?" * len(ids))

    courses_rows = query(
        f"SELECT ohId, courseId, courseName, shortName FROM oh_courses WHERE ohId IN ({placeholders})",
        tuple(ids)
    )
    cl_rows = query(
        f"SELECT ohId, courseLineId, courseLineName FROM oh_course_lines WHERE ohId IN ({placeholders})",
        tuple(ids)
    )
    appt_rows = query(
        f"""SELECT id, ohId, title, candidateId, candidateName, status, note
            FROM oh_appointments WHERE ohId IN ({placeholders}) ORDER BY ohId""",
        tuple(ids)
    )

    # Appointment courses
    appt_ids = [a["id"] for a in appt_rows]
    appt_course_rows: list[dict] = []
    if appt_ids:
        ap = ",".join("?" * len(appt_ids))
        appt_course_rows = query(
            f"SELECT appointmentId, courseId, courseName, shortName FROM oh_appointment_courses WHERE appointmentId IN ({ap})",
            tuple(appt_ids)
        )

    # Build maps
    courses_map: dict[str, list] = {}
    for c in courses_rows:
        courses_map.setdefault(c["ohId"], []).append(
            {"id": c["courseId"], "name": c["courseName"], "shortName": c["shortName"]}
        )

    cl_map: dict[str, list] = {}
    for cl in cl_rows:
        cl_map.setdefault(cl["ohId"], []).append(
            {"id": cl["courseLineId"], "name": cl["courseLineName"]}
        )

    appt_course_map: dict[str, list] = {}
    for ac in appt_course_rows:
        appt_course_map.setdefault(ac["appointmentId"], []).append(
            {"id": ac["courseId"], "name": ac["courseName"], "shortName": ac["shortName"]}
        )

    appts_map: dict[str, list] = {}
    for a in appt_rows:
        appts_map.setdefault(a["ohId"], []).append({
            "id": a["id"],
            "title": a["title"],
            "candidate": {"id": a["candidateId"], "fullName": a["candidateName"]} if a["candidateId"] else None,
            "courses": appt_course_map.get(a["id"], []),
            "status": a["status"],
            "note": a["note"],
        })

    for r in records:
        oid = r["id"]
        r["centre"] = {
            "id": r.pop("centreId"), "name": r.pop("centreName"), "shortName": r.pop("centreShortName")
        } if r.get("centreId") else None
        r["teacher"] = {
            "id": r.pop("teacherId"), "fullName": r.pop("teacherFullName"),
            "username": r.pop("teacherUsername"), "email": r.pop("teacherEmail"),
        } if r.get("teacherId") else None
        r["createdBy"] = {"username": r.pop("createdByUsername")} if r.get("createdByUsername") else None
        r["courses"]     = courses_map.get(oid, [])
        r["courseLines"] = cl_map.get(oid, [])
        r["appointments"] = appts_map.get(oid, [])

    return records


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=int(os.getenv("API_PORT", "8000")), reload=False)
