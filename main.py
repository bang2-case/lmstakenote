import requests
import json
import time
import os
import sqlite3
import base64
import sys
from datetime import datetime, timezone

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


GRAPHQL_URL = "https://lms-api.mindx.edu.vn/"
TOKEN = load_token()

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
CENTRE_IDS = [
    "62cc07753c1309654f472e60",     # Lũy Bán Bích
    "63034f4a7d1d1e1cb14e4e57",     # Tây Thạnh
    "62918d02af37d11e2da237e5",     # Tên Lửa
    "62d6dcc16e356729147d73a6"      # Trường Chinh
]

HCM4_CENTRES = ["Tên Lửa", "Tây Thạnh", "Lũy Bán Bích", "Trường Chinh"]

def build_payload(page_index):
    return {
        "operationName": "GetClasses",
        "variables": {
            "search": "",
            "centres": CENTRE_IDS,
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
        student {
          id
          customer {
            fullName
          }
        }
        completionInfo {
          status
          note
          reason
        }
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

        res = requests.post(GRAPHQL_URL, headers=HEADERS, json=build_payload(page))

        if res.status_code != 200:
            print(f"Status: {res.status_code}")
            print(f"Response: {res.text[:500]}")
            break

        data = res.json()

        try:
            classes = data["data"]["classes"]["data"]
            total = data["data"]["classes"]["pagination"]["total"]
            print(f"  → {len(classes)} lớp (tổng: {total})")
        except:
            print("Lỗi:", json.dumps(data, indent=2, ensure_ascii=False)[:500])
            break

        if not classes:
            break

        for c in classes:
            centre_name = c.get("centre", {}).get("name", "")

            # Nếu CENTRE_IDS trống thì filter theo tên, ngược lại lấy hết
            if not CENTRE_IDS:
                if not any(x in centre_name for x in HCM4_CENTRES):
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
                    students_in_slot = len(students_present)

                    # Đếm số học viên đã được comment
                    students_with_comment = 0
                    students_without_comment = []

                    for att in students_present:
                        student_name = att.get("student", {}).get("fullName", "Unknown")
                        has_comment = bool(att.get("comment"))
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
                        "studentsWithComment": students_with_comment
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

            # Chỉ lấy giáo viên có ít nhất 1 centre thuộc HCM4
            centres = t.get("centres", [])
            hcm4_centres = [
                c for c in centres
                if any(kw in c.get("name", "") for kw in HCM4_CENTRES)
            ]
            if not hcm4_centres:
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
                "centres": [c.get("name") for c in hcm4_centres],  # Chỉ lưu cơ sở HCM4
            })

        fetched_so_far = (page + 1) * 100
        if fetched_so_far >= total:
            break

        page += 1
        time.sleep(0.2)

    return all_teachers

def save(data):
    with open("public/classes.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
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
    conn = get_sqlite_conn()
    c = conn.cursor()
    try:
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

            # Slots
            c.execute("DELETE FROM slots WHERE classId=?", (cid,))
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
    - Nếu có class_survey_id: filter trực tiếp qua API (chính xác, nhanh)
    - Fallback: scan pages và filter theo classId trong metadata
    """
    all_responses = []
    page = 0

    # Thử filter theo classSurveyId trước (chính xác hơn, không bị giới hạn page)
    if class_survey_id:
        MAX_PAGES = 5  # classSurveyId filter rất chính xác, ít pages
        while page < MAX_PAGES:
            payload = {
                "operationName": "FindSurveyResponses",
                "variables": {
                    "surveyId": survey_id,
                    "classSurveyId": class_survey_id,
                    "page": page,
                    "limit": 100
                },
                "query": """
                query FindSurveyResponses($surveyId: String, $classSurveyId: String, $page: Int, $limit: Int) {
                  findSurveyResponses(payload: {
                    filter: { surveyId: $surveyId, classSurveyId: $classSurveyId }
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
                # Nếu API không hỗ trợ classSurveyId filter → fallback
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
        # Nếu classSurveyId filter không trả về gì → fallback sang scan

    # Fallback: scan pages và filter theo classId trong metadata
    page = 0
    MAX_PAGES = 20
    while page < MAX_PAGES:
        payload = {
            "operationName": "FindSurveyResponses",
            "variables": {"surveyId": survey_id, "page": page, "limit": 100},
            "query": """
            query FindSurveyResponses($surveyId: String, $page: Int, $limit: Int) {
              findSurveyResponses(payload: {
                filter: { surveyId: $surveyId }
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
            result = data.get("data", {}).get("findSurveyResponses", {})
            items = result.get("data", [])
            if not items:
                break
            for r in items:
                try:
                    meta = json.loads(r.get("metadata", "{}"))
                except Exception:
                    meta = {}
                if meta.get("classId") == class_id:
                    all_responses.append(r)
            if len(items) < 100:
                break
            page += 1
        except Exception as e:
            print(f"    warning get_survey_responses: {e}")
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
    return parts[1].upper() in {'ROB', 'KIND', 'XART', 'C4K'}


# ─────────────────────────────────────────────────────────────────────────────
# ASYNC TP FETCH  (parallel + cache)
# ─────────────────────────────────────────────────────────────────────────────
import asyncio
import aiohttp

TP_CACHE_FILE = "public/tp.json"
CONCURRENCY   = 20   # số lớp fetch song song


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
    """Fetch tất cả pages của survey, ưu tiên filter theo classSurveyId."""
    all_responses = []
    page = 0

    # Thử filter theo classSurveyId trước
    if class_survey_id:
        MAX_PAGES = 5
        while page < MAX_PAGES:
            payload = {
                "operationName": "FindSurveyResponses",
                "variables": {
                    "surveyId": survey_id,
                    "classSurveyId": class_survey_id,
                    "page": page, "limit": 100
                },
                "query": """
                query FindSurveyResponses($surveyId: String, $classSurveyId: String, $page: Int, $limit: Int) {
                  findSurveyResponses(payload: {
                    filter: { surveyId: $surveyId, classSurveyId: $classSurveyId }
                    pagination: { page: $page, limit: $limit }
                  }) {
                    data { id submittedAt metadata answers { questionId value } }
                    pagination { total }
                  }
                }
                """
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

    # Fallback: scan pages và filter theo classId trong metadata
    page = 0
    MAX_PAGES = 20
    while page < MAX_PAGES:
        payload = {
            "operationName": "FindSurveyResponses",
            "variables": {"surveyId": survey_id, "page": page, "limit": 100},
            "query": """
            query FindSurveyResponses($surveyId: String, $page: Int, $limit: Int) {
              findSurveyResponses(payload: {
                filter: { surveyId: $surveyId }
                pagination: { page: $page, limit: $limit }
              }) {
                data { id submittedAt metadata answers { questionId value } }
                pagination { total }
              }
            }
            """
        }
        data = await async_post(session, payload)
        result = (data.get("data") or {}).get("findSurveyResponses") or {}
        items = result.get("data") or []
        if not items:
            break
        for r in items:
            try:
                meta = json.loads(r.get("metadata", "{}"))
            except Exception:
                meta = {}
            if meta.get("classId") == class_id:
                all_responses.append(r)
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

    t_start = _time.time()

    print("=" * 50)
    print("🚀 Bắt đầu fetch song song: classes + teachers + OH")
    print("=" * 50)

    classes_result: dict = {}
    teachers_result: dict = {}
    oh_result: dict = {}
    tp_result: dict = {}
    cp_result: dict = {}
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

    save_tp(tp_result["data"])
    save_cp(cp_result["data"])

    elapsed_total = _time.time() - t_start
    print()
    print("=" * 50)
    print(f"✅ Hoàn tất tất cả! Tổng thời gian: {elapsed_total:.0f}s")
    print("=" * 50)
    sys.exit(0)
