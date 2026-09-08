import requests
import json
import time
import os
import sqlite3
import base64
import sys
import atexit
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

# Fix encoding cho Windows terminal
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ─────────────────────────────────────────────────────────────────────────────
# TOKEN — đọc từ .env (không hardcode trong code)
# ─────────────────────────────────────────────────────────────────────────────

def load_token() -> str:
    """Đọc LMS_TOKEN từ file .env."""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        print("❌ Không tìm thấy file .env")
        print("   Hãy tạo file .env với nội dung: LMS_TOKEN=<token của bạn>")
        sys.exit(1)

    # utf-8-sig tự động bỏ BOM nếu có
    with open(env_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("LMS_TOKEN="):
                token = line[len("LMS_TOKEN="):].strip().strip('"').strip("'")
                if token:
                    return token

    print("❌ Không tìm thấy LMS_TOKEN trong file .env")
    print("   Đảm bảo file .env có dòng: LMS_TOKEN=<token>")
    sys.exit(1)


def check_token_expiry(token: str) -> bool:
    """
    Kiểm tra token JWT có còn hạn không.
    Trả về True nếu còn hạn, False nếu đã hết.
    """
    try:
        # JWT có dạng header.payload.signature — decode phần payload
        parts = token.split(".")
        if len(parts) != 3:
            return False
        # Thêm padding nếu cần
        payload_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        exp = payload.get("exp", 0)
        now = datetime.now(timezone.utc).timestamp()
        remaining = exp - now
        if remaining <= 0:
            print(f"❌ Token đã hết hạn {abs(int(remaining // 60))} phút trước.")
            return False
        print(f"✅ Token còn hạn: {int(remaining // 60)} phút {int(remaining % 60)} giây")
        return True
    except Exception as e:
        print(f"⚠ Không kiểm tra được token: {e}")
        return True  # Cho qua, để API tự báo lỗi


def update_env_token(new_token: str):
    """Cập nhật LMS_TOKEN trong file .env."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            lines = f.readlines()
    new_lines = []
    for line in lines:
        if line.strip().startswith("LMS_TOKEN="):
            new_lines.append(f"LMS_TOKEN={new_token}\n")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"LMS_TOKEN={new_token}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("✅ Đã cập nhật token vào .env")

_check_token_expiry_from_jwt = check_token_expiry


def read_env_file_value(key: str) -> str | None:
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return None

    with open(env_path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith(f"{key}="):
                value = line[len(key) + 1:].strip().strip('"').strip("'")
                if value:
                    return value

    return None


def env_value(*keys: str) -> str | None:
    for key in keys:
        value = os.environ.get(key) or read_env_file_value(key)
        if value:
            return value
    return None


def refresh_token_from_login() -> str | None:
    if not (
        env_value("FIREBASE_API_KEY", "NEXT_PUBLIC_FIREBASE_API_KEY")
        and env_value("LMS_LOGIN_EMAIL")
        and env_value("LMS_LOGIN_PASSWORD")
    ):
        return None

    import subprocess

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "get-idtoken.js")
    try:
        result = subprocess.run(
            ["node", script],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ},
        )
        token = result.stdout.strip().splitlines()[-1].strip()
        return token or None
    except Exception as e:
        print(f"Unable to refresh LMS_TOKEN from login credentials: {e}")
        return None


def load_token() -> str:
    token = env_value("LMS_TOKEN")
    if token:
        return token

    refreshed_token = refresh_token_from_login()
    if refreshed_token:
        return refreshed_token

    print("Missing LMS_TOKEN in environment variables or .env")
    sys.exit(1)


def check_token_expiry(token: str) -> bool:
    if _check_token_expiry_from_jwt(token):
        return True

    refreshed_token = refresh_token_from_login()
    if not refreshed_token:
        return False

    globals()["TOKEN"] = refreshed_token
    print("Refreshed LMS_TOKEN from login credentials")
    return _check_token_expiry_from_jwt(refreshed_token)


GRAPHQL_URL = "https://lms-api.mindx.edu.vn/"
TOKEN = load_token()
FETCH_LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".fetch.lock")
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def _get_process_command_line(pid: int) -> str:
    if os.name != "nt":
        return ""
    try:
        import subprocess
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
                    normalized = command_line.replace("\\", "/").lower()
                    return "main.py" in normalized
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _read_fetch_lock() -> dict:
    try:
        with open(FETCH_LOCK_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def acquire_fetch_lock() -> bool:
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    payload = {
        "pid": os.getpid(),
        "argv": sys.argv,
        "cwd": PROJECT_ROOT,
        "startedAt": datetime.now(timezone.utc).isoformat(),
    }
    try:
        fd = os.open(FETCH_LOCK_FILE, flags)
    except FileExistsError:
        existing = _read_fetch_lock()
        pid = int(existing.get("pid") or 0)
        if _pid_is_fetch_process(pid):
            print(f"❌ Đang có tiến trình fetch khác chạy (PID {pid}).")
            print("   Hãy đợi tiến trình đó xong hoặc bấm Hủy trong app trước khi fetch lại.")
            return False
        try:
            os.unlink(FETCH_LOCK_FILE)
        except OSError:
            print("❌ Không thể xóa fetch lock cũ. Hãy đóng các phiên dev server cũ rồi thử lại.")
            return False
        fd = os.open(FETCH_LOCK_FILE, flags)

    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return True


def release_fetch_lock():
    existing = _read_fetch_lock()
    if int(existing.get("pid") or 0) != os.getpid():
        return
    try:
        os.unlink(FETCH_LOCK_FILE)
    except FileNotFoundError:
        pass

# Kiểm tra token ngay khi khởi động
if not check_token_expiry(TOKEN):
    print("\n👉 Hãy lấy token mới từ LMS và cập nhật trong file .env")
    print('   Hoặc chạy: python main.py --update-token "TOKEN_MỚI"')
    if len(sys.argv) == 3 and sys.argv[1] == "--update-token":
        new_token = sys.argv[2]
        update_env_token(new_token)
        TOKEN = new_token
        print("✅ Token đã được cập nhật, tiếp tục chạy...")
    else:
        # Token hết hạn và không có token mới → dừng hẳn, không xóa data
        sys.exit(2)  # exit code 2 = token expired

# Cho phép update token qua CLI ngay cả khi token còn hạn
if len(sys.argv) == 3 and sys.argv[1] == "--update-token":
    new_token = sys.argv[2]
    update_env_token(new_token)
    TOKEN = new_token
    print("✅ Token đã được cập nhật")

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "Content-Language": "en",
    "Origin": "https://lms.mindx.edu.vn",
    "Referer": "https://lms.mindx.edu.vn/"
}

# ─────────────────────────────────────────────────────────────────────────────
AREA_CENTRES = {
    "HCM1": {
        "ids": [
            "62d6dc936e356729147d7399",  # 01 To Ky
            "609bf4149535070ca5e3edc0",  # Phan Van Tri
            "62b0234675379306da49f051",  # 261-263 Phan Xich Long
        ],
        "keywords": ["Tô Ký", "To Ky", "Phan Văn Trị", "Phan Van Tri", "Phan Xích Long", "Phan Xich Long"],
    },
    "HCM4": {
        "ids": [
            "62cc07753c1309654f472e60",  # Luy Ban Bich
            "63034f4a7d1d1e1cb14e4e57",  # Tay Thanh
            "62918d02af37d11e2da237e5",  # Ten Lua
            "62d6dcc16e356729147d73a6",  # Truong Chinh
        ],
        "keywords": ["Tên Lửa", "Ten Lua", "Tây Thạnh", "Tay Thanh", "Lũy Bán Bích", "Luy Ban Bich", "Trường Chinh", "Truong Chinh"],
    },
}

CENTRE_IDS = AREA_CENTRES["HCM1"]["ids"] + AREA_CENTRES["HCM4"]["ids"]
TARGET_CENTRE_KEYWORDS = AREA_CENTRES["HCM1"]["keywords"] + AREA_CENTRES["HCM4"]["keywords"]
CLASS_STATUSES_TO_FETCH = ["RUNNING", "FINISHED"]

HCM4_CENTRES = AREA_CENTRES["HCM4"]["keywords"]

def build_payload(page_index):
    return {
        "operationName": "GetClasses",
        "variables": {
            "search": "",
            "centres": CENTRE_IDS,
            "statusIn": CLASS_STATUSES_TO_FETCH,
            "courses": [],
            "courseLines": [],
            "startDate": [None, None],
            "endDate": [None, None],
            "pageIndex": page_index,
            "itemsPerPage": 100,
            "orderBy": "createdAt_desc",
            "type": "OFFSET",
            "teacherSlot": [],
            "passedSessionIndex": None,
            "unpassedSessionIndex": None,
            "haveSlotIn": {},
            "comments": {"criteria": []}
        },
        "query": """query GetClasses($search: String, $centre: String, $operationMethodId: [String], $openStatus: [String], $centres: [String], $courses: [String], $courseLines: [String], $startDateFrom: Date, $startDateTo: Date, $endDateFrom: Date, $endDateTo: Date, $haveSlotFrom: Date, $haveSlotTo: Date, $statusNotEquals: String, $attendanceCheckedExists: Boolean, $status: String, $statusIn: [String], $attendanceStatus: [String], $studentAttendanceStatus: [String], $teacherAttendanceStatus: [String], $pageIndex: Int!, $itemsPerPage: Int!, $orderBy: String, $teacherId: String, $teacherSlot: [String], $passedSessionIndex: Int, $unpassedSessionIndex: Int, $haveSlotIn: HaveSlotIn, $comments: ClassCommentQuery) {
  classes(payload: {filter_textSearch: $search, centre_equals: $centre, centre_in: $centres, operationMethodId_in: $operationMethodId, teacher_equals: $teacherId, teacherSlots: $teacherSlot, course_in: $courses, courseLine_in: $courseLines, startDate_gt: $startDateFrom, startDate_lt: $startDateTo, endDate_gt: $endDateFrom, endDate_lt: $endDateTo, haveSlot_from: $haveSlotFrom, haveSlot_to: $haveSlotTo, status_ne: $statusNotEquals, status_in: $statusIn, status_equals: $status, attendanceStatus_in: $attendanceStatus, studentAttendanceStatus_in: $studentAttendanceStatus, teacherAttendanceStatus_in: $teacherAttendanceStatus, attendanceChecked_exists: $attendanceCheckedExists, haveSlot_in: $haveSlotIn, passedSessionIndex: $passedSessionIndex, unpassedSessionIndex: $unpassedSessionIndex, pageIndex: $pageIndex, itemsPerPage: $itemsPerPage, orderBy: $orderBy, comments: $comments, openStatus: $openStatus}) {
    data {
      id
      name
      status
      createdAt
      course {
        name
        shortName
      }
      centre {
        name
        shortName
      }
      numberOfSessions
      teachers {
        teacher {
          fullName
          email
        }
        role {
          name
        }
      }
      students {
        _id
        note
        activeInClass
        completed
        student {
          id
          fullName
          status
          waitingStatus
          studentId
        }
        completionInfo {
          status
          note
          reason
          description
        }
        retentionDate
      }
      slots {
        _id
        date
        startTime
        endTime
        studentAttendance {
          _id
          student {
            id
            fullName
          }
          status
          comment
          sendCommentStatus
        }
        teacherAttendance {
          _id
          teacher {
            id
            fullName
          }
          status
          note
        }
      }
      startDate
      endDate
      level
    }
    pagination {
      total
    }
  }
}
"""
    }

def fetch_all():
    all_data = []
    page = 0

    while True:
        print(f"Fetching page {page}...")

        res = None
        for attempt in range(3):
            try:
                res = requests.post(GRAPHQL_URL, headers=HEADERS, json=build_payload(page), timeout=30)
            except requests.RequestException as e:
                print(f"  ⚠ Request error page {page} (lần {attempt + 1}/3): {e}")
                if attempt == 2:
                    raise
                time.sleep(1.5 * (attempt + 1))
                continue

            if res.status_code == 200:
                break

            print(f"  ⚠ Status {res.status_code} page {page} (lần {attempt + 1}/3)")
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))

        if res is None:
            raise RuntimeError(f"Không nhận được phản hồi khi fetch page {page}")

        if res.status_code != 200:
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text[:500]}")
            raise RuntimeError(f"Fetch classes page {page} thất bại với HTTP {res.status_code}")

        data = res.json()

        try:
            classes = data["data"]["classes"]["data"]
            total = data["data"]["classes"]["pagination"]["total"]
            print(f"  → {len(classes)} lớp (tổng: {total})")
        except Exception as e:
            print("Lỗi:", json.dumps(data, indent=2, ensure_ascii=False)[:500])
            raise RuntimeError(f"Không đọc được dữ liệu classes page {page}: {e}")

        if not classes:
            break

        for c in classes:
            centre_name = c.get("centre", {}).get("name", "")

            # Nếu CENTRE_IDS trống thì filter theo tên, ngược lại lấy hết
            if not CENTRE_IDS:
                if not any(x in centre_name for x in TARGET_CENTRE_KEYWORDS):
                    continue

            # Lấy danh sách giáo viên — chỉ lấy role "Lecturer"
            teachers = []
            if c.get("teachers"):
                for t in c["teachers"]:
                    teacher_info = t.get("teacher", {})
                    role_name = (t.get("role") or {}).get("name", "")
                    # Chỉ lấy Lecturer, bỏ qua TA, Supply teacher, Judge, v.v.
                    if teacher_info.get("fullName") and "Lecturer" in role_name:
                        teachers.append({
                            "name": teacher_info.get("fullName"),
                            "email": teacher_info.get("email"),
                            "role": role_name
                        })

            # Xác định khối từ course name — gộp "4+" vào "Robotics"
            # (cần biết block trước để xác định slot CP)
            course_name = c.get("course", {}).get("name", "")
            block = "Coding"
            if course_name:
                course_lower = course_name.lower()
                if "4+" in course_name or "robotics 4" in course_lower or "kind" in course_lower:
                    block = "Robotics"
                elif "robotics" in course_lower or "robot" in course_lower:
                    block = "Robotics"
                elif any(x in course_lower for x in ["visual", "graphic", "art", "design", "multimedia", "creative"]):
                    block = "ART"

            # Slot CP theo khối: Coding → 5 & 9, Robotics → 4 & 8
            if block == "Robotics":
                CP1_SLOT, CP2_SLOT = 4, 8
            else:
                CP1_SLOT, CP2_SLOT = 5, 9

            # Lấy slots và tính comments của giáo viên
            slots = []
            total_slots_with_students = 0
            slots_with_full_teacher_comments = 0
            # cp_slots: lưu attendance thô của buổi CP để fetch_cp dùng lại
            cp_slots: dict[str, list] = {}

            if c.get("slots"):
                for slot_idx, s in enumerate(c["slots"]):
                    session_num = slot_idx + 1  # 1-based
                    student_attendances = s.get("studentAttendance", [])
                    teacher_attendances = s.get("teacherAttendance", [])

                    # Chỉ đếm học viên có đi học
                    students_present = [
                        att for att in student_attendances
                        if att.get("status") not in ["ABSENT", "ABSENT_WITH_NOTICE"]
                    ]
                    slot_students = []
                    for att in students_present:
                        student = att.get("student") or {}
                        slot_students.append({
                            "id": student.get("id"),
                            "name": student.get("fullName", "Unknown"),
                            "status": att.get("status"),
                        })
                    students_in_slot = len(students_present)

                    # Đếm số học viên đã được comment
                    students_with_comment = 0
                    students_without_comment = []
                    slot_comments = []

                    for att in students_present:
                        student = att.get("student") or {}
                        student_name = student.get("fullName", "Unknown")
                        comment_text = att.get("comment") or ""
                        has_comment = bool(comment_text)
                        if comment_text.strip():
                            slot_comments.append({
                                "id": att.get("_id") or f"{s.get('_id')}:{student.get('id') or student_name}",
                                "slotId": s.get("_id"),
                                "sessionIndex": session_num,
                                "slotDate": s.get("date"),
                                "studentId": student.get("id"),
                                "studentName": student_name,
                                "comment": comment_text,
                                "sendCommentStatus": att.get("sendCommentStatus"),
                            })
                        if not has_comment:
                            for t_att in teacher_attendances:
                                if t_att.get("note"):
                                    has_comment = True
                                    break

                        if has_comment:
                            students_with_comment += 1
                        else:
                            students_without_comment.append(student_name)

                    slot_comment_status = "Chưa nhận xét"
                    if students_in_slot > 0:
                        if students_with_comment == students_in_slot:
                            slot_comment_status = "Đã nhận xét"
                            slots_with_full_teacher_comments += 1
                        elif students_with_comment > 0:
                            slot_comment_status = f"Thiếu: {', '.join(students_without_comment[:3])}"
                            if len(students_without_comment) > 3:
                                slot_comment_status += f" +{len(students_without_comment) - 3}"

                    if students_in_slot > 0:
                        total_slots_with_students += 1

                    slots.append({
                        "id": s.get("_id"),
                        "date": s.get("date"),
                        "startTime": s.get("startTime"),
                        "endTime": s.get("endTime"),
                        "commentStatus": slot_comment_status,
                        "studentsInSlot": students_in_slot,
                        "studentsWithComment": students_with_comment,
                        "students": slot_students,
                        "comments": slot_comments,
                    })

                    # Lưu lại attendance thô của buổi CP để fetch_cp dùng
                    if session_num == CP1_SLOT:
                        cp_slots["cp1"] = student_attendances
                    elif session_num == CP2_SLOT:
                        cp_slots["cp2"] = student_attendances

            # Tính % comments
            comment_percentage = 0
            if total_slots_with_students > 0:
                comment_percentage = round((slots_with_full_teacher_comments / total_slots_with_students) * 100)

            # ── Completion Rate ──────────────────────────────────────────────
            # Chỉ tính HV đã đi học ít nhất 1 buổi (có attendance không phải ABSENT/ABSENT_WITH_NOTICE)
            students_raw = c.get("students", [])
            student_count = len(students_raw)

            # Thu thập student IDs đã có attendance (đi học ít nhất 1 buổi)
            attended_student_ids = set()
            for slot in c.get("slots", []):
                for att in slot.get("studentAttendance", []):
                    if att.get("status") not in ["ABSENT", "ABSENT_WITH_NOTICE"]:
                        sid = att.get("student", {}).get("id")
                        if sid:
                            attended_student_ids.add(sid)

            # Chỉ tính completed/total trên HV đã đi học
            attended_students = [
                s for s in students_raw
                if (s.get("student") or {}).get("id") in attended_student_ids
            ]
            attended_count = len(attended_students)
            completed_count = sum(
                1 for s in attended_students
                if (s.get("completionInfo") or {}).get("status") == "COMPLETED"
            )
            completion_rate = 0
            if attended_count > 0:
                completion_rate = round((completed_count / attended_count) * 100)
            # ────────────────────────────────────────────────────────────────

            all_data.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "status": c.get("status"),
                "course": c.get("course", {}).get("name"),
                "centre": centre_name,
                "teachers": teachers,
                "sessions": c.get("numberOfSessions"),
                "createdAt": c.get("createdAt"),
                "startDate": c.get("startDate"),
                "endDate": c.get("endDate"),
                "level": c.get("level"),
                "block": block,
                "slots": slots,
                "studentCount": student_count,
                "attendedCount": attended_count,
                "completedCount": completed_count,
                "completionRate": completion_rate,
                "commentPercentage": comment_percentage,
                "totalSlotsWithStudents": total_slots_with_students,
                "slotsWithFullComments": slots_with_full_teacher_comments,
                "cp_slots": cp_slots,  # attendance thô của buổi CP (cp1/cp2)
            })

        fetched_so_far = (page + 1) * 100
        if fetched_so_far >= total:
            break

        page += 1
        time.sleep(0.2)

    return all_data

# ─────────────────────────────────────────────────────────────────────────────
# TEACHER FETCH
# ─────────────────────────────────────────────────────────────────────────────

def get_teacher_block(course_lines: list) -> list:
    """Map courseLines names → khối Art / Robotics / Coding"""
    blocks = set()
    for cl in course_lines:
        name = cl.get("name", "").upper()
        if "XART" in name or "ART" in name:
            blocks.add("Art")
        elif "ROB" in name or "KIND" in name:
            blocks.add("Robotics")
        else:
            blocks.add("Coding")
    return sorted(list(blocks))

def build_teacher_payload(page_index):
    return {
        "operationName": "GetTeachers",
        "variables": {
            "search": "",
            "centres": CENTRE_IDS,
            "pageIndex": page_index,
            "itemsPerPage": 100,
            "orderBy": "createdAt_desc",
        },
        "query": """query GetTeachers($search: String, $centres: [String], $pageIndex: Int!, $itemsPerPage: Int!, $orderBy: String) {
  teachers(payload: {
    filter_textSearch: $search,
    centres_in: $centres,
    pageIndex: $pageIndex,
    itemsPerPage: $itemsPerPage,
    orderBy: $orderBy
  }) {
    data {
      id
      fullName
      code
      username
      email
      personalEmail
      phoneNumber
      gender
      dob
      address
      isActive
      teacherPoint
      joinedDate
      createdAt
      courseLines {
        id
        name
      }
      centres {
        id
        name
      }
    }
    pagination {
      total
    }
  }
}"""
    }

def fetch_teachers():
    all_teachers = []
    page = 0

    while True:
        print(f"Fetching teachers page {page}...")
        res = requests.post(GRAPHQL_URL, headers=HEADERS, json=build_teacher_payload(page), timeout=30)

        if res.status_code != 200:
            print(f"  ❌ Status: {res.status_code} - {res.text[:300]}")
            break

        data = res.json()

        if "errors" in data:
            print(f"  ❌ Lỗi: {data['errors'][0]['message']}")
            break

        try:
            teachers = data["data"]["teachers"]["data"]
            total = data["data"]["teachers"]["pagination"]["total"]
            print(f"  → {len(teachers)} giáo viên (tổng: {total})")
        except Exception as e:
            print(f"  ❌ Parse error: {e}")
            print(json.dumps(data, indent=2, ensure_ascii=False)[:500])
            break

        if not teachers:
            break

        for t in teachers:
            # Chỉ lấy giáo viên còn hoạt động
            if not t.get("isActive", False):
                continue

            # Bỏ qua giáo viên có courseLines chứa "18+"
            course_lines = t.get("courseLines", [])
            if any(cl.get("name", "") == "18+" for cl in course_lines):
                continue

            # Chỉ lấy giáo viên có ít nhất 1 centre thuộc các khu vực đang theo dõi
            centres = t.get("centres", [])
            target_centres = [
                c for c in centres
                if any(kw in c.get("name", "") for kw in TARGET_CENTRE_KEYWORDS)
            ]
            if not target_centres:
                continue

            blocks = get_teacher_block(course_lines)

            all_teachers.append({
                "id": t.get("id"),
                "fullName": t.get("fullName"),
                "code": t.get("code"),
                "username": t.get("username"),
                "email": t.get("email"),
                "personalEmail": t.get("personalEmail"),
                "phoneNumber": t.get("phoneNumber"),
                "gender": t.get("gender"),
                "dob": t.get("dob"),
                "address": t.get("address"),
                "isActive": t.get("isActive"),
                "teacherPoint": t.get("teacherPoint", 0),
                "joinedDate": t.get("joinedDate"),
                "courseLines": [cl.get("name") for cl in course_lines],
                "blocks": blocks,
                "centres": [c.get("name") for c in target_centres],
            })

        fetched_so_far = (page + 1) * 100
        if fetched_so_far >= total:
            break

        page += 1
        time.sleep(0.2)

    return all_teachers

def save(data):
    if not data:
        print("\n⚠ Không có dữ liệu lớp mới; giữ nguyên public/classes.json và SQLite hiện tại")
        return

    public_data = []
    for item in data:
        public_item = dict(item)
        public_slots = []
        for slot in item.get("slots", []):
            public_slot = dict(slot)
            public_slot.pop("comments", None)
            public_slots.append(public_slot)
        public_item["slots"] = public_slots
        public_data.append(public_item)

    with open("public/classes.json", "w", encoding="utf-8") as f:
        json.dump(public_data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Đã lưu {len(data)} lớp vào public/classes.json")
    save_classes_to_sqlite(data)

def save_teachers(data):
    with open("public/teachers.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(data)} giáo viên vào public/teachers.json")
    save_teachers_to_sqlite(data)


# ─────────────────────────────────────────────────────────────────────────────
# SQLITE SAVE
# ─────────────────────────────────────────────────────────────────────────────

def get_sqlite_conn():
    db_path = os.path.join(os.path.dirname(__file__), "classroom_data.db")
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def save_classes_to_sqlite(data: list):
    """Upsert classes, teachers, slots, incomplete_students vào SQLite."""
    from scripts.init_db import init_db

    init_db()
    conn = get_sqlite_conn()
    c = conn.cursor()
    try:
        c.execute("""
            CREATE TABLE IF NOT EXISTS slot_comments (
                id                TEXT PRIMARY KEY,
                classId           TEXT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                slotId            TEXT NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
                sessionIndex      INTEGER,
                slotDate          TEXT,
                studentId         TEXT,
                studentName       TEXT,
                comment           TEXT,
                sendCommentStatus TEXT
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_slot_comments_classId ON slot_comments(classId)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_slot_comments_slotId  ON slot_comments(slotId)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS slot_students (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                classId     TEXT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                slotId      TEXT NOT NULL REFERENCES slots(id) ON DELETE CASCADE,
                studentId   TEXT,
                studentName TEXT,
                status      TEXT
            )
        """)
        c.execute("CREATE INDEX IF NOT EXISTS idx_slot_students_classId ON slot_students(classId)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_slot_students_slotId  ON slot_students(slotId)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS class_students (
                id              TEXT PRIMARY KEY,
                classId         TEXT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
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
        c.execute("CREATE INDEX IF NOT EXISTS idx_class_students_classId ON class_students(classId)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_class_students_studentId ON class_students(studentId)")

        for item in data:
            cid = item["id"]
            c.execute("""
                INSERT OR REPLACE INTO classes
                (id, name, status, course, centre, block, level, sessions,
                 studentCount, attendedCount, completedCount, completionRate,
                 commentPercentage, totalSlotsWithStudents, slotsWithFullComments,
                 startDate, endDate, createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                cid, item.get("name"), item.get("status"), item.get("course"),
                item.get("centre"), item.get("block"), item.get("level"),
                item.get("sessions"), item.get("studentCount", 0),
                item.get("attendedCount", 0), item.get("completedCount", 0),
                item.get("completionRate", 0), item.get("commentPercentage", 0),
                item.get("totalSlotsWithStudents", 0), item.get("slotsWithFullComments", 0),
                item.get("startDate"), item.get("endDate"), item.get("createdAt"),
            ))

            # Teachers
            c.execute("DELETE FROM class_teachers WHERE classId=?", (cid,))
            for t in item.get("teachers", []):
                c.execute(
                    "INSERT INTO class_teachers (classId, name, email, role) VALUES (?,?,?,?)",
                    (cid, t.get("name"), t.get("email"), t.get("role"))
                )

            # Class students are fetched lazily via findClassStudent when the CR modal opens.
            if "students" in item:
                c.execute("DELETE FROM class_students WHERE classId=?", (cid,))
                for s in item.get("students", []):
                    student = s.get("student") or {}
                    c.execute("""
                        INSERT OR REPLACE INTO class_students
                        (id, classId, studentId, activeInClass, completed, attended,
                         note, grade, retentionDate, completionInfo, student, previousClass)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """, (
                        s.get("id") or f"{cid}:{s.get('studentId') or student.get('id') or student.get('fullName') or ''}",
                        cid,
                        s.get("studentId") or student.get("id"),
                        1 if s.get("activeInClass") else 0,
                        1 if s.get("completed") else 0,
                        1 if s.get("attended") else 0,
                        s.get("note"),
                        json.dumps(s.get("grade"), ensure_ascii=False),
                        s.get("retentionDate"),
                        json.dumps(s.get("completionInfo"), ensure_ascii=False),
                        json.dumps(student, ensure_ascii=False),
                        json.dumps(s.get("previousClass"), ensure_ascii=False),
                    ))

            # Slots
            c.execute("DELETE FROM slots WHERE classId=?", (cid,))
            c.execute("DELETE FROM slot_comments WHERE classId=?", (cid,))
            c.execute("DELETE FROM slot_students WHERE classId=?", (cid,))
            for s in item.get("slots", []):
                c.execute("""
                    INSERT OR REPLACE INTO slots
                    (id, classId, date, startTime, endTime, commentStatus,
                     studentsInSlot, studentsWithComment)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (
                    s.get("id"), cid, s.get("date"), s.get("startTime"),
                    s.get("endTime"), s.get("commentStatus"),
                    s.get("studentsInSlot", 0), s.get("studentsWithComment", 0),
                ))
                for comment in s.get("comments", []):
                    comment_id = comment.get("id") or f"{s.get('id')}:{comment.get('studentId') or comment.get('studentName') or ''}"
                    c.execute("""
                        INSERT OR REPLACE INTO slot_comments
                        (id, classId, slotId, sessionIndex, slotDate, studentId,
                         studentName, comment, sendCommentStatus)
                        VALUES (?,?,?,?,?,?,?,?,?)
                    """, (
                        comment_id, cid, s.get("id"),
                        comment.get("sessionIndex"), comment.get("slotDate"),
                        comment.get("studentId"), comment.get("studentName"),
                        comment.get("comment"), comment.get("sendCommentStatus"),
                    ))
                for student in s.get("students", []):
                    c.execute("""
                        INSERT INTO slot_students
                        (classId, slotId, studentId, studentName, status)
                        VALUES (?,?,?,?,?)
                    """, (
                        cid, s.get("id"), student.get("id"),
                        student.get("name"), student.get("status"),
                    ))

            # Incomplete students
            c.execute("DELETE FROM incomplete_students WHERE classId=?", (cid,))
            for name in item.get("incompleteStudents", []):
                c.execute(
                    "INSERT INTO incomplete_students (classId, name) VALUES (?,?)",
                    (cid, name)
                )

        conn.commit()
        print(f"✅ Đã lưu {len(data)} lớp vào SQLite")
    except Exception as e:
        conn.rollback()
        print(f"⚠ SQLite error (classes): {e}")
    finally:
        conn.close()


def save_teachers_to_sqlite(data: list):
    """Upsert teachers vào SQLite."""
    conn = get_sqlite_conn()
    c = conn.cursor()
    try:
        for t in data:
            tid = t["id"]
            c.execute("""
                INSERT OR REPLACE INTO teachers
                (id, fullName, code, username, email, personalEmail, phoneNumber,
                 gender, dob, address, isActive, teacherPoint, joinedDate)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                tid, t.get("fullName"), t.get("code"), t.get("username"),
                t.get("email"), t.get("personalEmail"), t.get("phoneNumber"),
                t.get("gender"), t.get("dob"), t.get("address"),
                1 if t.get("isActive") else 0,
                t.get("teacherPoint", 0), t.get("joinedDate"),
            ))

            c.execute("DELETE FROM teacher_centres WHERE teacherId=?", (tid,))
            for centre in t.get("centres", []):
                c.execute("INSERT INTO teacher_centres (teacherId, centre) VALUES (?,?)", (tid, centre))

            c.execute("DELETE FROM teacher_blocks WHERE teacherId=?", (tid,))
            for block in t.get("blocks", []):
                c.execute("INSERT INTO teacher_blocks (teacherId, block) VALUES (?,?)", (tid, block))

            c.execute("DELETE FROM teacher_course_lines WHERE teacherId=?", (tid,))
            for cl in t.get("courseLines", []):
                c.execute("INSERT INTO teacher_course_lines (teacherId, courseLine) VALUES (?,?)", (tid, cl))

        conn.commit()
        print(f"✅ Đã lưu {len(data)} giáo viên vào SQLite")
    except Exception as e:
        conn.rollback()
        print(f"⚠ SQLite error (teachers): {e}")
    finally:
        conn.close()


def save_tp_to_sqlite(data: list):
    """Upsert TP records vào SQLite."""
    conn = get_sqlite_conn()
    c = conn.cursor()
    try:
        for r in data:
            cid = r["classId"]
            c.execute("""
                INSERT OR REPLACE INTO tp_records
                (classId, className, centre, block, tp1, tp2)
                VALUES (?,?,?,?,?,?)
            """, (cid, r.get("className"), r.get("centre"), r.get("block"),
                  r.get("tp1"), r.get("tp2")))

            c.execute("DELETE FROM tp_students WHERE classId=?", (cid,))
            for s in r.get("tp1_students", []):
                c.execute(
                    "INSERT INTO tp_students (classId, round, name, score, textAnswers) VALUES (?,?,?,?,?)",
                    (cid, 1, s.get("name"), s.get("score"),
                     json.dumps(s.get("textAnswers", []), ensure_ascii=False))
                )
            for s in r.get("tp2_students", []):
                c.execute(
                    "INSERT INTO tp_students (classId, round, name, score, textAnswers) VALUES (?,?,?,?,?)",
                    (cid, 2, s.get("name"), s.get("score"),
                     json.dumps(s.get("textAnswers", []), ensure_ascii=False))
                )

            c.execute("DELETE FROM tp_teachers WHERE classId=?", (cid,))
            for t in r.get("teachers", []):
                c.execute(
                    "INSERT INTO tp_teachers (classId, name, email, role) VALUES (?,?,?,?)",
                    (cid, t.get("name"), t.get("email"), t.get("role"))
                )

        conn.commit()
        print(f"✅ Đã lưu {len(data)} TP records vào SQLite")
    except Exception as e:
        conn.rollback()
        print(f"⚠ SQLite error (tp): {e}")
    finally:
        conn.close()

# ─────────────────────────────────────────────────────────────────────────────
# TEACHER POINT (TP) FETCH
# ─────────────────────────────────────────────────────────────────────────────

def get_survey_id_for_class(class_id):
    """Lấy surveyId và classSurveyId của lớp qua findOneClassSurvey."""
    payload = {
        "operationName": "FindOneClassSurvey",
        "variables": {"classId": class_id},
        "query": """
        query FindOneClassSurvey($classId: String) {
          findOneClassSurvey(payload: { classId: $classId }) {
            id
            surveyId
          }
        }
        """
    }
    try:
        res = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=15)
        data = res.json()
        result = data.get("data", {}).get("findOneClassSurvey")
        if result:
            return result.get("surveyId"), result.get("id")  # (surveyId, classSurveyId)
    except Exception as e:
        print(f"    ⚠ get_survey_id error for {class_id}: {e}")
    return None, None


def get_survey_responses(survey_id, class_id, class_survey_id=None):
    """
    Lấy tất cả responses của một surveyId.
    - Nếu có class_survey_id: filter qua metadata JSON (chính xác, nhanh)
    - Fallback: filter qua metadata classId
    """
    import json as _json
    all_responses = []
    page = 0

    # Filter theo classSurveyId trong metadata (đúng cách API hỗ trợ)
    if class_survey_id:
        MAX_PAGES = 5
        while page < MAX_PAGES:
            payload = {
                "operationName": "FindSurveyResponses",
                "variables": {
                    "surveyId": survey_id,
                    "metadata": _json.dumps({"classSurveyId": class_survey_id}),
                    "page": page,
                    "limit": 100
                },
                "query": """
                query FindSurveyResponses($surveyId: String, $metadata: String, $page: Int, $limit: Int) {
                  findSurveyResponses(payload: {
                    filter: { surveyId: $surveyId, metadata: $metadata }
                    pagination: { page: $page, limit: $limit }
                  }) {
                    data {
                      id submittedAt metadata
                      answers { questionId value }
                    }
                    pagination { total }
                  }
                }
                """
            }
            try:
                res = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=15)
                data = res.json()
                if "errors" in data:
                    break
                result = data.get("data", {}).get("findSurveyResponses", {})
                items = result.get("data", [])
                if not items:
                    break
                all_responses.extend(items)
                if len(items) < 100:
                    break
                page += 1
            except Exception as e:
                print(f"    warning get_survey_responses (classSurveyId): {e}")
                break

        if all_responses:
            return all_responses

    # Fallback: filter theo classId trong metadata
    page = 0
    MAX_PAGES = 5
    while page < MAX_PAGES:
        payload = {
            "operationName": "FindSurveyResponses",
            "variables": {
                "surveyId": survey_id,
                "metadata": _json.dumps({"classId": class_id}),
                "page": page,
                "limit": 100
            },
            "query": """
            query FindSurveyResponses($surveyId: String, $metadata: String, $page: Int, $limit: Int) {
              findSurveyResponses(payload: {
                filter: { surveyId: $surveyId, metadata: $metadata }
                pagination: { page: $page, limit: $limit }
              }) {
                data {
                  id submittedAt metadata
                  answers { questionId value }
                }
                pagination { total }
              }
            }
            """
        }
        try:
            res = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=15)
            data = res.json()
            if "errors" in data:
                break
            result = data.get("data", {}).get("findSurveyResponses", {})
            items = result.get("data", [])
            if not items:
                break
            all_responses.extend(items)
            if len(items) < 100:
                break
            page += 1
        except Exception as e:
            print(f"    warning get_survey_responses (classId): {e}")
            break
    return all_responses


def parse_score(value: str) -> float | None:
    """Lấy số điểm từ đầu chuỗi, ví dụ '4. Dễ hiểu' → 4.0"""
    if not value:
        return None
    try:
        return float(value.strip()[0])
    except (ValueError, IndexError):
        return None


def calc_tp_from_responses(responses: list) -> dict:
    """
    Tính TP1 và TP2 từ danh sách responses.
    - Sort theo submittedAt
    - Nhóm theo sessionId (trong metadata)
    - Lần đầu = TP1, lần sau = TP2
    - Điểm mỗi HV = trung bình các câu SINGLE_CHOICE
    - Điểm lớp = trung bình điểm các HV
    """
    # Group responses by sessionId
    sessions = {}
    for r in responses:
        meta_raw = r.get("metadata", "{}")
        try:
            meta = json.loads(meta_raw)
        except Exception:
            meta = {}
        session_id = meta.get("sessionId", "unknown")
        submitted_at = int(r.get("submittedAt", 0))
        if session_id not in sessions:
            sessions[session_id] = {"submittedAt": submitted_at, "responses": []}
        sessions[session_id]["responses"].append(r)
        # Keep earliest submittedAt for sorting
        if submitted_at < sessions[session_id]["submittedAt"]:
            sessions[session_id]["submittedAt"] = submitted_at

    # Sort sessions by earliest submittedAt
    sorted_sessions = sorted(sessions.values(), key=lambda x: x["submittedAt"])

    result = {"tp1": None, "tp2": None, "tp1_students": [], "tp2_students": []}

    for idx, session in enumerate(sorted_sessions[:2]):  # Only TP1 and TP2
        tp_key = "tp1" if idx == 0 else "tp2"
        students_key = "tp1_students" if idx == 0 else "tp2_students"

        student_scores = []
        student_details = []

        for r in session["responses"]:
            meta_raw = r.get("metadata", "{}")
            try:
                meta = json.loads(meta_raw)
            except Exception:
                meta = {}
            student_name = meta.get("studentName", "—")

            # Tính điểm trung bình của HV (chỉ SINGLE_CHOICE — có số ở đầu)
            scores = []
            text_answers = []
            for ans in r.get("answers", []):
                score = parse_score(ans.get("value", ""))
                if score is not None:
                    scores.append(score)
                else:
                    # TEXT answer
                    text_answers.append({
                        "questionId": ans.get("questionId"),
                        "value": ans.get("value", "")
                    })

            avg = round(sum(scores) / len(scores), 2) if scores else None
            if avg is not None:
                student_scores.append(avg)

            student_details.append({
                "name": student_name,
                "score": avg,
                "textAnswers": text_answers
            })

        class_avg = round(sum(student_scores) / len(student_scores), 2) if student_scores else None
        result[tp_key] = class_avg
        result[students_key] = student_details

    return result


def is_regular_class(name: str) -> bool:
    """
    Lớp chính quy:
    - 2 phần: TL-JSB01 → True
    - 3+ phần, phần giữa là ROB/KIND/XART/C4K: TL-ROB-ARMB13 → True
    - 3 phần, phần cuối là suffix học bù/online (HB, ONL, HB2...): TT-JSB15-HB → True
    - 3+ phần, phần giữa khác: 01TC-THT-D30301 → False
    Bỏ qua phần trong ngoặc như (1:1), (ONL) trước khi xử lý.
    """
    import re
    cleaned = re.sub(r'\s*\(.*?\)', '', name).strip()
    parts = cleaned.split('-')
    if len(parts) < 2:
        return False
    if len(parts) == 2:
        return True
    # 3 phần: kiểm tra phần giữa là mã khối hợp lệ
    if parts[1].upper() in {'ROB', 'KIND', 'XART', 'C4K'}:
        return True
    # 3 phần: phần cuối là suffix học bù/online → coi như 2 phần
    SUFFIXES = {'HB', 'ONL', 'HB2', 'HB3', 'ONL2'}
    if len(parts) == 3 and parts[2].upper() in SUFFIXES:
        return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# ASYNC TP FETCH  (parallel + cache)
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
import aiohttp

TP_CACHE_FILE = "public/tp.json"
CONCURRENCY   = 10   # số lớp fetch song song


def load_tp_cache() -> dict:
    """Load cache từ tp.json, trả về dict {classId: record}."""
    if not os.path.exists(TP_CACHE_FILE):
        return {}
    try:
        with open(TP_CACHE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        # Chỉ giữ lại lớp đã có đủ TP1 + TP2 (không cần fetch lại)
        return {
            r["classId"]: r
            for r in data
            if r.get("tp1") is not None and r.get("tp2") is not None
        }
    except Exception:
        return {}


async def async_post(session: aiohttp.ClientSession, payload: dict) -> dict:
    """POST GraphQL và trả về JSON, retry 1 lần nếu lỗi."""
    for attempt in range(2):
        try:
            async with session.post(
                GRAPHQL_URL,
                json=payload,
                headers=HEADERS,
                timeout=aiohttp.ClientTimeout(total=20)
            ) as resp:
                return await resp.json()
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(1)
            else:
                return {}
    return {}


async def async_get_survey_id(session: aiohttp.ClientSession, class_id: str) -> tuple[str | None, str | None]:
    """Trả về (surveyId, classSurveyId)."""
    payload = {
        "operationName": "FindOneClassSurvey",
        "variables": {"classId": class_id},
        "query": """
        query FindOneClassSurvey($classId: String) {
          findOneClassSurvey(payload: { classId: $classId }) {
            id surveyId
          }
        }
        """
    }
    data = await async_post(session, payload)
    result = (data.get("data") or {}).get("findOneClassSurvey")
    if result:
        return result.get("surveyId"), result.get("id")
    return None, None


async def async_get_responses(session: aiohttp.ClientSession, survey_id: str, class_id: str, class_survey_id: str | None = None) -> list:
    """Fetch tất cả pages của survey, filter qua metadata JSON."""
    all_responses = []
    page = 0

    SURVEY_QUERY = """
    query FindSurveyResponses($surveyId: String, $metadata: String, $page: Int, $limit: Int) {
      findSurveyResponses(payload: {
        filter: { surveyId: $surveyId, metadata: $metadata }
        pagination: { page: $page, limit: $limit }
      }) {
        data { id submittedAt metadata answers { questionId value } }
        pagination { total }
      }
    }
    """

    # Filter theo classSurveyId trong metadata (chính xác nhất)
    if class_survey_id:
        MAX_PAGES = 5
        while page < MAX_PAGES:
            payload = {
                "operationName": "FindSurveyResponses",
                "variables": {
                    "surveyId": survey_id,
                    "metadata": json.dumps({"classSurveyId": class_survey_id}),
                    "page": page, "limit": 100
                },
                "query": SURVEY_QUERY
            }
            data = await async_post(session, payload)
            if "errors" in data:
                break
            result = (data.get("data") or {}).get("findSurveyResponses") or {}
            items = result.get("data") or []
            if not items:
                break
            all_responses.extend(items)
            if len(items) < 100:
                break
            page += 1

        if all_responses:
            return all_responses

    # Fallback: filter theo classId trong metadata
    page = 0
    MAX_PAGES = 5
    while page < MAX_PAGES:
        payload = {
            "operationName": "FindSurveyResponses",
            "variables": {
                "surveyId": survey_id,
                "metadata": json.dumps({"classId": class_id}),
                "page": page, "limit": 100
            },
            "query": SURVEY_QUERY
        }
        data = await async_post(session, payload)
        if "errors" in data:
            break
        result = (data.get("data") or {}).get("findSurveyResponses") or {}
        items = result.get("data") or []
        if not items:
            break
        all_responses.extend(items)
        if len(items) < 100:
            break
        page += 1
    return all_responses


async def fetch_tp_for_class(
    session: aiohttp.ClientSession,
    c: dict,
    semaphore: asyncio.Semaphore
) -> dict:
    """Fetch TP cho 1 lớp (survey id + responses + tính điểm)."""
    class_id   = c["id"]
    class_name = c.get("name", "")

    async with semaphore:
        survey_id, class_survey_id = await async_get_survey_id(session, class_id)
        if not survey_id:
            return {
                "classId": class_id, "className": class_name,
                "centre": c.get("centre"), "block": c.get("block"),
                "teachers": c.get("teachers", []),
                "tp1": None, "tp2": None,
                "tp1_students": [], "tp2_students": []
            }

        responses = await async_get_responses(session, survey_id, class_id, class_survey_id)
        tp = calc_tp_from_responses(responses)

        return {
            "classId": class_id, "className": class_name,
            "centre": c.get("centre"), "block": c.get("block"),
            "teachers": c.get("teachers", []),
            "tp1": tp["tp1"], "tp2": tp["tp2"],
            "tp1_students": tp["tp1_students"],
            "tp2_students": tp["tp2_students"]
        }


async def _fetch_tp_async(classes_to_fetch: list) -> list:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [
            fetch_tp_for_class(session, c, semaphore)
            for c in classes_to_fetch
        ]
        results = []
        # Chạy và in tiến độ
        done = 0
        total = len(tasks)
        for coro in asyncio.as_completed(tasks):
            result = await coro
            done += 1
            tp1 = result.get("tp1")
            tp2 = result.get("tp2")
            print(f"  [{done}/{total}] {result['className']} → TP1={tp1} TP2={tp2}")
            results.append(result)
        return results


def fetch_tp(classes_data: list) -> list:
    """
    Fetch TP với parallel requests + cache thông minh.
    - Lớp FINISHED Coding chính quy đã có đủ TP1+TP2 trong cache → giữ nguyên
    - Lớp mới hoặc chưa đủ data → fetch async song song
    - Bỏ qua lớp kết thúc trước 01/03/2026 (quá cũ, không cần TP)
    """
    from datetime import datetime, timezone
    CUTOFF_DATE = datetime(2026, 3, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)

    def is_after_cutoff(c: dict) -> bool:
        end_date_str = c.get("endDate")
        if not end_date_str:
            return True  # không có endDate → giữ lại
        try:
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            return end_date >= CUTOFF_DATE
        except Exception:
            return True  # parse lỗi → giữ lại

    def has_passed_tp_slot(c: dict) -> bool:
        """Kiểm tra lớp đã qua buổi TP (buổi 4 hoặc buổi 8) và có học viên."""
        slots = sorted(c.get("slots", []), key=lambda s: s.get("date", ""))
        for idx in [3, 7]:  # buổi 4 và buổi 8
            if idx < len(slots):
                s = slots[idx]
                date_str = s.get("date", "")
                try:
                    if "T" in date_str:
                        slot_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        slot_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    if slot_date < now and s.get("studentsInSlot", 0) > 0:
                        return True
                except Exception:
                    pass
        return False

    # Lọc lớp cần xử lý:
    # - FINISHED: lớp đã kết thúc (logic cũ)
    # - RUNNING/OPEN/...: lớp đang chạy nhưng đã qua buổi TP
    candidates = [
        c for c in classes_data
        if c.get("block") == "Coding"
        and is_regular_class(c.get("name", ""))
        and is_after_cutoff(c)
        and (c.get("status") == "FINISHED" or has_passed_tp_slot(c))
    ]
    print(f"\n📊 TP candidates: {len(candidates)} lớp Coding chính quy có buổi TP (từ 01/03/2026)")

    # Load cache
    cache = load_tp_cache()
    print(f"   Cache hit: {len(cache)} lớp đã có đủ TP1+TP2 → bỏ qua")

    # Tách lớp cần fetch vs lớp đã cache
    to_fetch  = [c for c in candidates if c["id"] not in cache]
    cached    = [cache[c["id"]] for c in candidates if c["id"] in cache]

    print(f"   Cần fetch: {len(to_fetch)} lớp (parallel, {CONCURRENCY} concurrent)")

    if not to_fetch:
        print("   Tất cả đã có cache!")
        return cached

    # Fetch async — dùng new event loop trong thread để tránh conflict
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        new_results = loop.run_until_complete(_fetch_tp_async(to_fetch))
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    # Gộp cache + kết quả mới, giữ thứ tự theo candidates
    result_map = {r["classId"]: r for r in new_results}
    result_map.update({r["classId"]: r for r in cached})

    return [result_map[c["id"]] for c in candidates if c["id"] in result_map]


def save_tp(data):
    with open(TP_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(data)} lớp TP vào {TP_CACHE_FILE}")
    save_tp_to_sqlite(data)


# ─────────────────────────────────────────────────────────────────────────────
# CHECKPOINT (CP) FETCH
# ─────────────────────────────────────────────────────────────────────────────

import re
from html.parser import HTMLParser

class ScoreExtractor(HTMLParser):
    """Parse HTML để lấy điểm từ comment"""
    def __init__(self):
        super().__init__()
        self.theory_score = None
        self.practical_score = None
        self.in_theory_tag = False
        self.in_practical_tag = False
        self.capture_next = False
        
    def handle_starttag(self, tag, attrs):
        if tag == 'strong':
            if self.in_theory_tag or self.in_practical_tag:
                self.capture_next = True
    
    def handle_data(self, data):
        # Look for "Điểm lý thuyết" and "Điểm thực hành"
        if 'Điểm lý thuyết' in data or 'lý thuyết' in data.lower():
            self.in_theory_tag = True
            self.in_practical_tag = False
        elif 'Điểm thực hành' in data or 'thực hành' in data.lower():
            self.in_practical_tag = True
            self.in_theory_tag = False
        elif self.capture_next:
            # Try to extract score from text like "4 điểm"
            score_match = re.search(r'(\d+(?:\.\d+)?)', data)
            if score_match:
                score = float(score_match.group(1))
                if self.in_theory_tag:
                    self.theory_score = score
                elif self.in_practical_tag:
                    self.practical_score = score
                self.capture_next = False
                self.in_theory_tag = False
                self.in_practical_tag = False

def extract_cp_scores(comment_html):
    """Extract 'Điểm lý thuyết' và 'Điểm thực hành' từ HTML comment"""
    if not comment_html:
        return None, None
    
    # Pattern handles HTML tags and spaces/colon: "Điểm lý thuyết: 4 điểm" hoặc "<strong>Điểm lý thuyết</strong>: <strong>4 điểm</strong>"
    # Remove HTML tags để matching dễ hơn
    clean_text = re.sub(r'<[^>]+>', '', comment_html)
    
    # Tìm "Điểm lý thuyết: X điểm" (handle multiple spaces/newlines)
    theory_match = re.search(r'Điểm\s+lý\s+thuyết\s*:\s*(\d+(?:[.,]\d+)?)\s*điểm', clean_text, re.IGNORECASE)
    practical_match = re.search(r'Điểm\s+thực\s+hành\s*:\s*(\d+(?:[.,]\d+)?)\s*điểm', clean_text, re.IGNORECASE)
    
    def parse_score(match):
        if not match:
            return None
        score_str = match.group(1).replace(',', '.')
        try:
            return float(score_str)
        except:
            return None
    
    theory_score = parse_score(theory_match)
    practical_score = parse_score(practical_match)
    
    return theory_score, practical_score


def fetch_cp_for_class(class_data: dict) -> dict:
    """
    Fetch CP data cho 1 lớp từ attendance records đã có sẵn trong cp_slots.
    - Coding:   CP1 = slot 5, CP2 = slot 9
    - Robotics: CP1 = slot 4, CP2 = slot 8
    - Parse comment để lấy "Điểm lý thuyết" và "Điểm thực hành"
    """
    class_id   = class_data["id"]
    class_name = class_data.get("name", "")
    centre     = class_data.get("centre", "")
    block      = class_data.get("block", "")
    teachers   = class_data.get("teachers", [])
    cp_slots   = class_data.get("cp_slots", {})  # đã được fetch_all() chuẩn bị sẵn

    result = {
        "classId": class_id,
        "className": class_name,
        "centre": centre,
        "block": block,
        "teachers": teachers,
        "cp1Theory": None,
        "cp1Practical": None,
        "cp2Theory": None,
        "cp2Practical": None,
        "cp1_students": [],
        "cp2_students": []
    }

    for cp_key in ("cp1", "cp2"):
        attendances = cp_slots.get(cp_key, [])
        students = []

        for att in attendances:
            if att.get("status") in ["ABSENT", "ABSENT_WITH_NOTICE"]:
                continue
            student_name = (att.get("student") or {}).get("fullName", "Unknown")
            comment = att.get("comment", "")
            if not comment:
                continue
            theory_score, practical_score = extract_cp_scores(comment)
            if theory_score is not None or practical_score is not None:
                students.append({
                    "name": student_name,
                    "theoryScore": theory_score,
                    "practicalScore": practical_score
                })

        if students:
            theory_scores    = [s["theoryScore"]    for s in students if s["theoryScore"]    is not None]
            practical_scores = [s["practicalScore"] for s in students if s["practicalScore"] is not None]
            result[f"{cp_key}Theory"]    = round(sum(theory_scores)    / len(theory_scores),    2) if theory_scores    else None
            result[f"{cp_key}Practical"] = round(sum(practical_scores) / len(practical_scores), 2) if practical_scores else None
            result[f"{cp_key}_students"] = students

    return result


def fetch_cp(classes_data: list) -> list:
    """Fetch CP data cho tất cả các lớp (synchronously)"""
    print("\n📊 Fetching Checkpoint data...")

    # Lọc lớp cần xử lý: RUNNING, khối Coding hoặc Robotics, lớp chính quy
    candidates = [
        c for c in classes_data
        if c.get("status") == "RUNNING"
        and c.get("block") in ("Coding", "Robotics")
        and is_regular_class(c.get("name", ""))
    ]
    print(f"   CP candidates: {len(candidates)} lớp RUNNING (Coding/Robotics) chính quy")
    
    results = []
    for i, c in enumerate(candidates, 1):
        cp_record = fetch_cp_for_class(c)
        cp1_theory = cp_record.get("cp1Theory")
        cp1_practical = cp_record.get("cp1Practical")
        cp2_theory = cp_record.get("cp2Theory")
        cp2_practical = cp_record.get("cp2Practical")
        print(f"  [{i}/{len(candidates)}] {cp_record['className']} → CP1(LT={cp1_theory},TH={cp1_practical}) CP2(LT={cp2_theory},TH={cp2_practical})")
        results.append(cp_record)
    
    return results


def save_cp_to_sqlite(data: list):
    """Upsert CP records vào SQLite."""
    conn = get_sqlite_conn()
    c = conn.cursor()
    try:
        for r in data:
            cid = r["classId"]
            c.execute("""
                INSERT OR REPLACE INTO cp_records
                (classId, className, centre, block, cp1Theory, cp1Practical, cp2Theory, cp2Practical)
                VALUES (?,?,?,?,?,?,?,?)
            """, (cid, r.get("className"), r.get("centre"), r.get("block"),
                  r.get("cp1Theory"), r.get("cp1Practical"),
                  r.get("cp2Theory"), r.get("cp2Practical")))

            c.execute("DELETE FROM cp_students WHERE classId=?", (cid,))
            for s in r.get("cp1_students", []):
                c.execute(
                    "INSERT INTO cp_students (classId, round, name, theoryScore, practicalScore) VALUES (?,?,?,?,?)",
                    (cid, 1, s.get("name"), s.get("theoryScore"), s.get("practicalScore"))
                )
            for s in r.get("cp2_students", []):
                c.execute(
                    "INSERT INTO cp_students (classId, round, name, theoryScore, practicalScore) VALUES (?,?,?,?,?)",
                    (cid, 2, s.get("name"), s.get("theoryScore"), s.get("practicalScore"))
                )

            c.execute("DELETE FROM cp_teachers WHERE classId=?", (cid,))
            for t in r.get("teachers", []):
                c.execute(
                    "INSERT INTO cp_teachers (classId, name, email, role) VALUES (?,?,?,?)",
                    (cid, t.get("name"), t.get("email"), t.get("role"))
                )

        conn.commit()
        print(f"✅ Đã lưu {len(data)} CP records vào SQLite")
    except Exception as e:
        conn.rollback()
        print(f"⚠ SQLite error (cp): {e}")
    finally:
        conn.close()


CP_CACHE_FILE = "public/cp.json"

def save_cp(data):
    with open(CP_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(data)} lớp CP vào {CP_CACHE_FILE}")
    save_cp_to_sqlite(data)


# ─────────────────────────────────────────────────────────────────────────────

# ASSIGNMENTS / HOMEWORK FETCH
ASSIGNMENT_QUERY = """query FindStudentSubmissionByClass($payload: FindStudentSubmissionByClassQuery!) {
  findStudentSubmissionByClass(payload: $payload) {
    students { id displayName studentUid __typename }
    lessons { id name type isActive learningCourseId displayOrder __typename }
    submissions {
      id type note score status category classId lessonId learningCourseId
      studentUid studentOriginalId classSessionId markedAt markedBy createdAt submittedAt submittedCount
      content { scratchState type attachments totalQuiz submitQuiz correctAnswer __typename }
      __typename
    }
    __typename
  }
}"""

ASSIGNMENT_CACHE_FILE = "public/assignments.json"
ASSIGNMENT_CONCURRENCY = 2
ASSIGNMENT_FINISHED_LOOKBACK_DAYS = 90
ASSIGNMENT_MAX_RETRIES = 5


def should_fetch_assignment_class(class_item: dict) -> bool:
    status = class_item.get("status")
    if status == "RUNNING":
        return True
    if status != "FINISHED":
        return False

    end_date = class_item.get("endDate")
    if not end_date:
        return False
    try:
        end_dt = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
    except Exception:
        return False
    return end_dt >= datetime.now(timezone.utc) - timedelta(days=ASSIGNMENT_FINISHED_LOOKBACK_DAYS)


def build_assignment_fetch_error(class_item: dict, error_type: str, message: str) -> dict:
    return {
        "classId": class_item.get("id"),
        "className": class_item.get("name", ""),
        "centre": class_item.get("centre"),
        "block": class_item.get("block", ""),
        "status": class_item.get("status", ""),
        "fetchError": {
            "errorType": error_type,
            "message": message,
        },
    }


def classify_assignment_error(message: str) -> str:
    text = message.lower()
    if "not mapped on denise" in text:
        return "mapping"
    return "lms_error"


def fetch_assignments_for_class(class_item: dict) -> dict | None:
    class_id = class_item.get("id")
    if not class_id:
        return None

    payload = {
        "operationName": "FindStudentSubmissionByClass",
        "variables": {"payload": {"classId": class_id}},
        "query": ASSIGNMENT_QUERY,
    }

    last_error: dict | None = None
    for attempt in range(1, ASSIGNMENT_MAX_RETRIES + 1):
        try:
            res = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
            if res.status_code != 200:
                message = f"HTTP {res.status_code}"
                print(f"  assignment {class_item.get('name', class_id)}: {message}")
                last_error = build_assignment_fetch_error(class_item, "http", message)
                if attempt < ASSIGNMENT_MAX_RETRIES and res.status_code in (429, 502, 503, 504):
                    retry_after = res.headers.get("Retry-After")
                    try:
                        wait_seconds = float(retry_after) if retry_after else 0
                    except Exception:
                        wait_seconds = 0
                    wait_seconds = max(wait_seconds, 2 ** attempt)
                    time.sleep(wait_seconds)
                    continue
                return last_error

            data = res.json()
            if "errors" in data:
                message = data["errors"][0].get("message", "") if data.get("errors") else "LMS returned an error"
                error_type = classify_assignment_error(message)
                print(f"  assignment {class_item.get('name', class_id)}: {message[:160]}")
                return build_assignment_fetch_error(class_item, error_type, message)

            result = (data.get("data") or {}).get("findStudentSubmissionByClass") or {}
            return {
                "classId": class_id,
                "className": class_item.get("name", ""),
                "centre": class_item.get("centre"),
                "block": class_item.get("block", ""),
                "status": class_item.get("status", ""),
                "teachers": class_item.get("teachers", []),
                "students": result.get("students") or [],
                "lessons": result.get("lessons") or [],
                "submissions": result.get("submissions") or [],
            }
        except Exception as e:
            message = str(e)
            print(f"  assignment {class_item.get('name', class_id)}: {message}")
            last_error = build_assignment_fetch_error(class_item, "network", message)
            if attempt < ASSIGNMENT_MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            return last_error

    return last_error


def load_classes_for_assignments_from_db() -> list[dict]:
    conn = get_sqlite_conn()
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("""
            SELECT id, name, status, centre, block, endDate
            FROM classes
            WHERE status = 'RUNNING'
               OR (
                    status = 'FINISHED'
                    AND date(substr(endDate, 1, 10)) >= date('now', ?)
               )
            ORDER BY createdAt DESC
        """, (f"-{ASSIGNMENT_FINISHED_LOOKBACK_DAYS} day",)).fetchall()
        class_ids = [r["id"] for r in rows]
        teachers_map: dict[str, list] = {}
        if class_ids:
            placeholders = ",".join("?" * len(class_ids))
            teachers = conn.execute(
                f"SELECT classId, name, email, role FROM class_teachers WHERE classId IN ({placeholders})",
                tuple(class_ids),
            ).fetchall()
            for t in teachers:
                teachers_map.setdefault(t["classId"], []).append({
                    "name": t["name"],
                    "email": t["email"],
                    "role": t["role"],
                })

        return [
            {
                "id": r["id"],
                "name": r["name"],
                "status": r["status"],
                "centre": r["centre"],
                "block": r["block"],
                "endDate": r["endDate"],
                "teachers": teachers_map.get(r["id"], []),
            }
            for r in rows
        ]
    finally:
        conn.close()


def fetch_assignments(classes_data: list[dict] | None = None) -> list[dict]:
    print("\nFetching assignment data...")
    classes_data = classes_data or load_classes_for_assignments_from_db()
    classes_data = [item for item in classes_data if should_fetch_assignment_class(item)]
    records: list[dict] = []
    errors = 0
    total = len(classes_data)
    if total == 0:
        print("  No class data available for assignments")
        return []

    with ThreadPoolExecutor(max_workers=ASSIGNMENT_CONCURRENCY) as executor:
        futures = {executor.submit(fetch_assignments_for_class, item): item for item in classes_data}
        done = 0
        for future in as_completed(futures):
            done += 1
            record = future.result()
            if record is not None:
                if record.get("fetchError"):
                    errors += 1
                records.append(record)
            if done % 50 == 0 or done == total:
                print(f"  assignment progress: {done}/{total}")
            time.sleep(0.02)

    records.sort(key=lambda r: r.get("className") or "")
    print(f"  Assignment records: {len(records) - errors} success, {errors} errors")
    return records


def ensure_assignment_tables(cursor):
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS assignment_records (
            classId     TEXT PRIMARY KEY REFERENCES classes(id) ON DELETE CASCADE,
            className   TEXT,
            centre      TEXT,
            block       TEXT,
            status      TEXT,
            updatedAt   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS assignment_students (
            id          TEXT,
            classId     TEXT NOT NULL REFERENCES assignment_records(classId) ON DELETE CASCADE,
            displayName TEXT,
            studentUid  TEXT,
            PRIMARY KEY (classId, studentUid)
        );
        CREATE TABLE IF NOT EXISTS assignment_lessons (
            id               TEXT,
            classId          TEXT NOT NULL REFERENCES assignment_records(classId) ON DELETE CASCADE,
            name             TEXT,
            type             TEXT,
            isActive         INTEGER DEFAULT 0,
            learningCourseId TEXT,
            displayOrder     INTEGER,
            PRIMARY KEY (classId, id)
        );
        CREATE TABLE IF NOT EXISTS assignment_submissions (
            id               TEXT PRIMARY KEY,
            classId          TEXT NOT NULL REFERENCES assignment_records(classId) ON DELETE CASCADE,
            type             TEXT,
            note             TEXT,
            score            REAL,
            status           TEXT,
            category         TEXT,
            lessonId         TEXT,
            learningCourseId TEXT,
            studentUid       TEXT,
            studentOriginalId TEXT,
            classSessionId   TEXT,
            markedAt         TEXT,
            markedBy         TEXT,
            createdAt        TEXT,
            submittedAt      TEXT,
            submittedCount   INTEGER DEFAULT 0,
            contentJson      TEXT
        );
        CREATE TABLE IF NOT EXISTS assignment_teachers (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            classId     TEXT NOT NULL REFERENCES assignment_records(classId) ON DELETE CASCADE,
            name        TEXT,
            email       TEXT,
            role        TEXT
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


def is_assignment_submitted(submission: dict) -> bool:
    status = str(submission.get("status") or "").upper()
    return (
        status in ("SUBMITTED", "MARKED")
        or bool(submission.get("submittedAt"))
        or int(submission.get("submittedCount") or 0) > 0
    )


def is_assignment_resubmit_pending(submission: dict) -> bool:
    status = str(submission.get("status") or "").upper()
    return status in ("REDO", "RE_SUBMITTED")


def is_assignment_gradable(submission: dict) -> bool:
    return is_assignment_submitted(submission) and not is_assignment_resubmit_pending(submission)


def is_assignment_marked(submission: dict) -> bool:
    status = str(submission.get("status") or "").upper()
    return status == "MARKED" or bool(submission.get("markedAt")) or bool(submission.get("markedBy"))


def is_homework_submission(submission: dict) -> bool:
    submission_type = str(submission.get("type") or "").upper()
    category = str(submission.get("category") or "").upper()
    return submission_type == "UPLOAD_FILE" or category.startswith("PRACTICE_TASK")


def summarize_assignment_record(record: dict) -> dict:
    lessons = [lesson for lesson in record.get("lessons", []) if lesson.get("isActive")]
    submissions = [
        submission for submission in record.get("submissions", [])
        if is_homework_submission(submission)
    ]
    submitted = [submission for submission in submissions if is_assignment_submitted(submission)]
    gradable_submitted = [submission for submission in submissions if is_assignment_gradable(submission)]
    marked = [submission for submission in gradable_submitted if is_assignment_marked(submission)]
    scored = [
        float(submission.get("score") or 0)
        for submission in gradable_submitted
        if float(submission.get("score") or 0) > 0
    ]
    expected_count = len(submissions) or len(record.get("students", [])) * len(lessons)
    return {
        "classId": record.get("classId"),
        "className": record.get("className"),
        "centre": record.get("centre"),
        "block": record.get("block"),
        "status": record.get("status"),
        "teachers": record.get("teachers", []),
        "students": [],
        "lessons": [],
        "submissions": [],
        "studentCount": len(record.get("students", [])),
        "lessonCount": len(lessons),
        "expectedCount": expected_count,
        "submittedCount": len(submitted),
        "gradableSubmittedCount": len(gradable_submitted),
        "markedCount": len(marked),
        "inProgressCount": len([
            submission for submission in submissions
            if str(submission.get("status") or "").upper() == "IN_PROGRESS"
        ]),
        "needsMarkingCount": max(0, len(gradable_submitted) - len(marked)),
        "averageScore": round(sum(scored) / len(scored)) if scored else None,
    }


def chunks(items: list, size: int = 800):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def save_assignments_to_sqlite(data: list[dict]):
    conn = get_sqlite_conn()
    c = conn.cursor()
    try:
        ensure_assignment_tables(c)
        for r in data:
            cid = r["classId"]
            fetch_error = r.get("fetchError")
            if fetch_error:
                c.execute("""
                    INSERT OR REPLACE INTO assignment_fetch_errors
                    (classId, className, centre, block, status, errorType, message, fetchedAt)
                    VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                """, (
                    cid, r.get("className"), r.get("centre"), r.get("block"), r.get("status"),
                    fetch_error.get("errorType"), fetch_error.get("message"),
                ))
                continue

            c.execute("""
                INSERT OR REPLACE INTO assignment_records
                (classId, className, centre, block, status, updatedAt)
                VALUES (?,?,?,?,?,CURRENT_TIMESTAMP)
            """, (cid, r.get("className"), r.get("centre"), r.get("block"), r.get("status")))
            c.execute("DELETE FROM assignment_fetch_errors WHERE classId=?", (cid,))

            c.execute("DELETE FROM assignment_students WHERE classId=?", (cid,))
            for s in r.get("students", []):
                c.execute("""
                    INSERT OR REPLACE INTO assignment_students
                    (id, classId, displayName, studentUid)
                    VALUES (?,?,?,?)
                """, (s.get("id"), cid, s.get("displayName"), s.get("studentUid")))

            c.execute("DELETE FROM assignment_lessons WHERE classId=?", (cid,))
            for lesson in r.get("lessons", []):
                c.execute("""
                    INSERT OR REPLACE INTO assignment_lessons
                    (id, classId, name, type, isActive, learningCourseId, displayOrder)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    lesson.get("id"), cid, lesson.get("name"), lesson.get("type"),
                    1 if lesson.get("isActive") else 0,
                    lesson.get("learningCourseId"), lesson.get("displayOrder"),
                ))

            c.execute("DELETE FROM assignment_submissions WHERE classId=?", (cid,))
            for submission in r.get("submissions", []):
                c.execute("""
                    INSERT OR REPLACE INTO assignment_submissions
                    (id, classId, type, note, score, status, category, lessonId,
                     learningCourseId, studentUid, studentOriginalId, classSessionId,
                     markedAt, markedBy, createdAt, submittedAt, submittedCount, contentJson)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    submission.get("id"), cid, submission.get("type"), submission.get("note"),
                    submission.get("score"), submission.get("status"), submission.get("category"),
                    submission.get("lessonId"), submission.get("learningCourseId"),
                    submission.get("studentUid"), submission.get("studentOriginalId"),
                    submission.get("classSessionId"), submission.get("markedAt"),
                    submission.get("markedBy"), submission.get("createdAt"),
                    submission.get("submittedAt"), submission.get("submittedCount", 0),
                    json.dumps(submission.get("content") or {}, ensure_ascii=False),
                ))

            c.execute("DELETE FROM assignment_teachers WHERE classId=?", (cid,))
            for t in r.get("teachers", []):
                c.execute(
                    "INSERT INTO assignment_teachers (classId, name, email, role) VALUES (?,?,?,?)",
                    (cid, t.get("name"), t.get("email"), t.get("role"))
                )

        conn.commit()
        success_count = len([r for r in data if not r.get("fetchError")])
        error_count = len(data) - success_count
        print(f"Saved {success_count} assignment records and {error_count} assignment errors to SQLite")
    except Exception as e:
        conn.rollback()
        print(f"SQLite error (assignments): {e}")
    finally:
        conn.close()


def save_assignments(data: list[dict]):
    success_records = [record for record in data if not record.get("fetchError")]
    public_map: dict[str, dict] = {}
    if os.path.exists(ASSIGNMENT_CACHE_FILE):
        try:
            with open(ASSIGNMENT_CACHE_FILE, encoding="utf-8") as f:
                existing_public_data = json.load(f)
            if isinstance(existing_public_data, list):
                public_map = {
                    item.get("classId"): item
                    for item in existing_public_data
                    if isinstance(item, dict) and item.get("classId")
                }
        except Exception:
            public_map = {}

    for record in success_records:
        summary = summarize_assignment_record(record)
        if summary.get("classId"):
            public_map[summary["classId"]] = summary

    public_data = sorted(public_map.values(), key=lambda item: item.get("className") or "")
    with open(ASSIGNMENT_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(public_data, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(public_data)} assignment summaries to {ASSIGNMENT_CACHE_FILE}")
    save_assignments_to_sqlite(data)


# OFFICE HOURS (OH) FETCH
# ─────────────────────────────────────────────────────────────────────────────

OH_CUTOFF_ISO = "2026-04-01T00:00:00.000Z"  # 01/04/2026 00:00:00 UTC

OH_QUERY = """query GetOfficeHours($payload: OfficeHourQuery) {
  officeHours(payload: $payload) {
    data {
      id
      courses { id name shortName __typename }
      courseLines { id name __typename }
      startTime endTime status
      centre { id name shortName __typename }
      teacher { id username code fullName imageUrl email phoneNumber __typename }
      note managerNote type studentCount
      createdBy { username __typename }
      createdAt
      appointments {
        id title
        candidate { id fullName __typename }
        courses { id name shortName __typename }
        status note __typename
      }
      __typename
    }
    pagination { type total __typename }
    __typename
  }
}"""


def fetch_oh() -> list:
    """Fetch Office Hours từ 01/03/2026 cho 4 cơ sở HCM4."""
    print("\n🏢 Fetching Office Hours...")
    all_oh: list = []
    page = 0

    while True:
        payload = {
            "operationName": "GetOfficeHours",
            "variables": {
                "payload": {
                    "pageIndex": page,
                    "itemsPerPage": 100,
                    "orderBy": "startTime_desc",
                    "centreIn": CENTRE_IDS,
                    "courseIn": [],
                    "timeFrom": OH_CUTOFF_ISO,
                }
            },
            "query": OH_QUERY,
        }

        try:
            res = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=30)
            if res.status_code != 200:
                print(f"  ❌ HTTP {res.status_code}: {res.text[:300]}")
                break

            data = res.json()
            if "errors" in data:
                print(f"  ❌ GraphQL error: {data['errors'][0].get('message', '')}")
                break

            oh_result = (data.get("data") or {}).get("officeHours") or {}
            items = oh_result.get("data") or []
            total = (oh_result.get("pagination") or {}).get("total", 0)
            print(f"  → {len(items)} OH (tổng: {total})")

            if not items:
                break

            for oh in items:
                centre  = oh.get("centre") or {}
                teacher = oh.get("teacher") or {}
                cb      = oh.get("createdBy") or {}

                record = {
                    "id": oh.get("id"),
                    "startTime": oh.get("startTime"),
                    "endTime": oh.get("endTime"),
                    "status": oh.get("status"),
                    "centre": {
                        "id": centre.get("id", ""),
                        "name": centre.get("name", ""),
                        "shortName": centre.get("shortName", ""),
                    } if centre.get("id") else None,
                    "teacher": {
                        "id": teacher.get("id", ""),
                        "fullName": teacher.get("fullName", ""),
                        "username": teacher.get("username", ""),
                        "email": teacher.get("email", ""),
                    } if teacher.get("id") else None,
                    "courses": [
                        {"id": c.get("id", ""), "name": c.get("name", ""), "shortName": c.get("shortName", "")}
                        for c in (oh.get("courses") or [])
                    ],
                    "courseLines": [
                        {"id": cl.get("id", ""), "name": cl.get("name", "")}
                        for cl in (oh.get("courseLines") or [])
                    ],
                    "note": oh.get("note"),
                    "managerNote": oh.get("managerNote"),
                    "type": oh.get("type"),
                    "studentCount": oh.get("studentCount", 0),
                    "createdBy": {"username": cb.get("username", "")} if cb.get("username") else None,
                    "createdAt": oh.get("createdAt"),
                    "appointments": [
                        {
                            "id": a.get("id"),
                            "title": a.get("title", ""),
                            "candidate": {
                                "id": (a.get("candidate") or {}).get("id", ""),
                                "fullName": (a.get("candidate") or {}).get("fullName", ""),
                            } if a.get("candidate") else None,
                            "courses": [
                                {"id": c.get("id", ""), "name": c.get("name", ""), "shortName": c.get("shortName", "")}
                                for c in (a.get("courses") or [])
                            ],
                            "status": a.get("status", "WAITING"),
                            "note": a.get("note"),
                        }
                        for a in (oh.get("appointments") or [])
                        if a.get("id")
                    ],
                }
                all_oh.append(record)

            fetched = (page + 1) * 100
            if fetched >= total:
                break
            page += 1
            time.sleep(0.2)

        except Exception as e:
            print(f"  ❌ Exception: {e}")
            break

    print(f"  ✅ Tổng: {len(all_oh)} OH")
    return all_oh


def save_oh_to_sqlite(data: list):
    """Upsert OH records vào SQLite."""
    conn = get_sqlite_conn()
    c = conn.cursor()
    try:
        # Migration-safe: tạo bảng nếu chưa có
        c.executescript("""
            CREATE TABLE IF NOT EXISTS oh_records (
                id TEXT PRIMARY KEY, startTime TEXT, endTime TEXT, status TEXT,
                centreId TEXT, centreName TEXT, centreShortName TEXT,
                teacherId TEXT, teacherFullName TEXT, teacherUsername TEXT, teacherEmail TEXT,
                note TEXT, managerNote TEXT, type TEXT, studentCount INTEGER DEFAULT 0,
                createdByUsername TEXT, createdAt TEXT,
                updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS oh_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ohId TEXT NOT NULL,
                courseId TEXT, courseName TEXT, shortName TEXT
            );
            CREATE TABLE IF NOT EXISTS oh_course_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ohId TEXT NOT NULL,
                courseLineId TEXT, courseLineName TEXT
            );
            CREATE TABLE IF NOT EXISTS oh_appointments (
                id TEXT PRIMARY KEY, ohId TEXT NOT NULL,
                title TEXT, candidateId TEXT, candidateName TEXT, status TEXT, note TEXT
            );
            CREATE TABLE IF NOT EXISTS oh_appointment_courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT, appointmentId TEXT NOT NULL,
                courseId TEXT, courseName TEXT, shortName TEXT
            );
        """)

        for r in data:
            oid     = r["id"]
            centre  = r.get("centre") or {}
            teacher = r.get("teacher") or {}
            cb      = r.get("createdBy") or {}

            c.execute("""
                INSERT OR REPLACE INTO oh_records
                (id, startTime, endTime, status, centreId, centreName, centreShortName,
                 teacherId, teacherFullName, teacherUsername, teacherEmail,
                 note, managerNote, type, studentCount, createdByUsername, createdAt)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                oid, r.get("startTime"), r.get("endTime"), r.get("status"),
                centre.get("id"), centre.get("name"), centre.get("shortName"),
                teacher.get("id"), teacher.get("fullName"), teacher.get("username"), teacher.get("email"),
                r.get("note"), r.get("managerNote"), r.get("type"),
                r.get("studentCount", 0), cb.get("username"), r.get("createdAt"),
            ))

            c.execute("DELETE FROM oh_courses WHERE ohId=?", (oid,))
            for course in r.get("courses", []):
                c.execute(
                    "INSERT INTO oh_courses (ohId, courseId, courseName, shortName) VALUES (?,?,?,?)",
                    (oid, course.get("id"), course.get("name"), course.get("shortName"))
                )

            c.execute("DELETE FROM oh_course_lines WHERE ohId=?", (oid,))
            for cl in r.get("courseLines", []):
                c.execute(
                    "INSERT INTO oh_course_lines (ohId, courseLineId, courseLineName) VALUES (?,?,?)",
                    (oid, cl.get("id"), cl.get("name"))
                )

            for appt in r.get("appointments", []):
                aid = appt.get("id")
                if not aid:
                    continue
                cand = appt.get("candidate") or {}
                c.execute("""
                    INSERT OR REPLACE INTO oh_appointments
                    (id, ohId, title, candidateId, candidateName, status, note)
                    VALUES (?,?,?,?,?,?,?)
                """, (
                    aid, oid, appt.get("title"),
                    cand.get("id"), cand.get("fullName"),
                    appt.get("status", "WAITING"), appt.get("note"),
                ))

                c.execute("DELETE FROM oh_appointment_courses WHERE appointmentId=?", (aid,))
                for course in appt.get("courses", []):
                    c.execute(
                        "INSERT INTO oh_appointment_courses (appointmentId, courseId, courseName, shortName) VALUES (?,?,?,?)",
                        (aid, course.get("id"), course.get("name"), course.get("shortName"))
                    )

        conn.commit()
        print(f"✅ Đã lưu {len(data)} OH records vào SQLite")
    except Exception as e:
        conn.rollback()
        print(f"⚠ SQLite error (oh): {e}")
    finally:
        conn.close()


def save_oh(data: list):
    with open("public/oh.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(data)} OH vào public/oh.json")
    save_oh_to_sqlite(data)


if __name__ == "__main__":
    import threading
    import time as _time

    if not acquire_fetch_lock():
        sys.exit(9)
    atexit.register(release_fetch_lock)

    # ── Per-module fetch (--only=<module>) ───────────────────────────────────
    only_module = None
    for arg in sys.argv[1:]:
        if arg.startswith("--only="):
            only_module = arg[len("--only="):]
            break

    if only_module:
        t_start = _time.time()
        print(f"🔄 Fetch module: {only_module}")

        if only_module == "classes":
            data = fetch_all()
            save(data)

        elif only_module == "teachers":
            teachers = fetch_teachers()
            save_teachers(teachers)

        elif only_module == "oh":
            oh = fetch_oh()
            save_oh(oh)

        elif only_module == "tp":
            # TP cần classes data — load từ DB thay vì fetch lại
            import sqlite3 as _sq
            conn = _sq.connect(os.path.join(os.path.dirname(__file__), "classroom_data.db"))
            conn.row_factory = _sq.Row
            rows = conn.execute("""
                SELECT c.id, c.name, c.centre, c.block, c.status, c.endDate,
                       GROUP_CONCAT(DISTINCT s.date || '|' || COALESCE(s.studentsInSlot,0)) as slot_data
                FROM classes c
                LEFT JOIN slots s ON s.classId = c.id
                GROUP BY c.id
            """).fetchall()
            conn.close()

            classes_for_tp = []
            for r in rows:
                slots = []
                if r["slot_data"]:
                    for part in r["slot_data"].split(","):
                        bits = part.split("|")
                        if len(bits) == 2:
                            slots.append({"date": bits[0], "studentsInSlot": int(bits[1] or 0)})
                classes_for_tp.append({
                    "id": r["id"], "name": r["name"], "centre": r["centre"],
                    "block": r["block"], "status": r["status"],
                    "endDate": r["endDate"], "teachers": [], "slots": slots,
                    "cp_slots": {},
                })

            tp_data = fetch_tp(classes_for_tp)
            save_tp(tp_data)

        elif only_module == "cp":
            # CP cần cp_slots từ fetch_all — fetch lại classes để lấy slots
            data = fetch_all()
            cp_data = fetch_cp(data)
            save_cp(cp_data)

        elif only_module == "assignments":
            assignment_data = fetch_assignments()
            save_assignments(assignment_data)

        else:
            print(f"❌ Module không hợp lệ: {only_module}")
            sys.exit(1)

        elapsed = _time.time() - t_start
        print(f"✅ Hoàn tất module '{only_module}' sau {elapsed:.0f}s")
        sys.exit(0)

    t_start = _time.time()

    print("=" * 50)
    print("🚀 Bắt đầu fetch song song: classes + teachers + OH")
    print("=" * 50)

    classes_result: dict = {}
    teachers_result: dict = {}
    oh_result: dict = {}
    tp_result: dict = {}
    cp_result: dict = {}
    assignment_result: dict = {}
    errors: list = []

    # ── Phase 1: fetch_all + fetch_teachers + fetch_oh song song ──────────
    def run_fetch_all():
        try:
            classes_result["data"] = fetch_all()
            print(f"\n✅ [classes] Xong: {len(classes_result['data'])} lớp")
        except Exception as e:
            errors.append(f"fetch_all: {e}")
            classes_result["data"] = []

    def run_fetch_teachers():
        try:
            teachers_result["data"] = fetch_teachers()
            print(f"\n✅ [teachers] Xong: {len(teachers_result['data'])} giáo viên")
        except Exception as e:
            errors.append(f"fetch_teachers: {e}")
            teachers_result["data"] = []

    def run_fetch_oh():
        try:
            oh_result["data"] = fetch_oh()
            print(f"\n✅ [OH] Xong: {len(oh_result['data'])} OH")
        except Exception as e:
            errors.append(f"fetch_oh: {e}")
            oh_result["data"] = []

    phase1_threads = [
        threading.Thread(target=run_fetch_all,      name="fetch-classes"),
        threading.Thread(target=run_fetch_teachers, name="fetch-teachers"),
        threading.Thread(target=run_fetch_oh,       name="fetch-oh"),
    ]
    for t in phase1_threads:
        t.start()
    for t in phase1_threads:
        t.join()

    elapsed1 = _time.time() - t_start
    print(f"\n⏱ Phase 1 xong sau {elapsed1:.0f}s")

    if errors:
        print(f"⚠ Lỗi phase 1: {errors}")
        sys.exit(1)
    if not classes_result["data"]:
        print("❌ Không tải được dữ liệu lớp; dừng để tránh upload dữ liệu rỗng.")
        sys.exit(1)

    # Lưu ngay sau phase 1
    data = classes_result["data"]
    save(data)
    save_teachers(teachers_result["data"])
    save_oh(oh_result["data"])

    # ── Phase 2: fetch_tp + fetch_cp song song (cả 2 cần data từ fetch_all) ──
    print()
    print("=" * 50)
    print("🚀 Phase 2: TP + CP song song")
    print("=" * 50)

    def run_fetch_tp():
        try:
            tp_result["data"] = fetch_tp(data)
            print(f"\n✅ [TP] Xong: {len(tp_result['data'])} lớp")
        except Exception as e:
            errors.append(f"fetch_tp: {e}")
            tp_result["data"] = []

    def run_fetch_cp():
        try:
            cp_result["data"] = fetch_cp(data)
            print(f"\n✅ [CP] Xong: {len(cp_result['data'])} lớp")
        except Exception as e:
            errors.append(f"fetch_cp: {e}")
            cp_result["data"] = []

    phase2_threads = [
        threading.Thread(target=run_fetch_tp, name="fetch-tp"),
        threading.Thread(target=run_fetch_cp, name="fetch-cp"),
    ]
    for t in phase2_threads:
        t.start()
    for t in phase2_threads:
        t.join()

    elapsed2 = _time.time() - t_start
    print(f"\n⏱ Phase 2 xong sau {elapsed2:.0f}s")

    if errors:
        print(f"⚠ Lỗi phase 2: {errors}")
        sys.exit(1)

    save_tp(tp_result["data"])
    save_cp(cp_result["data"])

    print()
    print("=" * 50)
    print("Fetching assignments")
    print("=" * 50)

    try:
        classes_for_assignments = [item for item in data if should_fetch_assignment_class(item)]
        assignment_result["data"] = fetch_assignments(classes_for_assignments)
        save_assignments(assignment_result["data"])
    except Exception as e:
        errors.append(f"fetch_assignments: {e}")
        assignment_result["data"] = []

    if errors:
        print(f"❌ Lỗi khi fetch LMS: {errors}")
        sys.exit(1)

    elapsed_total = _time.time() - t_start
    print()
    print("=" * 50)
    print(f"✅ Hoàn tất tất cả! Tổng thời gian: {elapsed_total:.0f}s")
    print("=" * 50)
    sys.exit(0)
