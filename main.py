import requests
import json
import time
import os

GRAPHQL_URL = "https://lms-api.mindx.edu.vn/"
TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjJiMzZhYjQxYTczOTJlMTRlNjM1ZmRlM2M2YWYwOWZlYmFhM2YyZDYiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiVEUgUGhhbiBOZ-G7jWMgSG_DoG5nIEFuaCIsImlkIjoiNWZmMjZiOWYzNzI5MjAwOTlkMjU4ODIzIiwidXNlcm5hbWUiOiJhbmhwbmgwMDEiLCJyb2xlcyI6WyI1ZmIzNzk4NTBkZGNjYTQ3OGU5M2RlZjgiXSwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL21pbmR4LWVkdS1wcm9kIiwiYXVkIjoibWluZHgtZWR1LXByb2QiLCJhdXRoX3RpbWUiOjE3Nzc1NjA3NTEsInVzZXJfaWQiOiJaakVuTW9ha3FZVE1mNUdOdkVXZEl1OXlPRGEyIiwic3ViIjoiWmpFbk1vYWtxWVRNZjVHTnZFV2RJdTl5T0RhMiIsImlhdCI6MTc3NzU2MDc1MiwiZXhwIjoxNzc3NTY0MzUyLCJlbWFpbCI6ImFuaHBuaEBtaW5keC5jb20udm4iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwicGhvbmVfbnVtYmVyIjoiKzg0MzY2NzU0MzQyIiwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJhbmhwbmhAbWluZHguY29tLnZuIl0sInBob25lIjpbIis4NDM2Njc1NDM0MiJdfSwic2lnbl9pbl9wcm92aWRlciI6ImN1c3RvbSJ9fQ.DtC5bpFtWyp86s1AGLmqyJUMpKQyS8oH_3kaZHd463m7Yr3FAljef-Tmgz3tUXrY7BkS3L9k8wnqckAUkhZ8BgSN5vw460FUAp11yC3x2SUN2RaUPwVU66-I0M2m5Wwdt06IQG4mY8_Roy1HxJhNazAUZ03rbCDFHkwjBGDiDqmlRhExLGP8aFMi3DLkqa5BozrWs0xftMRF3kHcXtj_wsPuIdlwDl69FEIp2UsB2zceYedhcqTqx3YeExwjBfMtNbNKLMekrO1I4s7aby_y-MgCK1jUwjuYRj9BiQMVwmrZaGEg5yzj1IAaOo-NcD-yQFQlCrT1CW1I-xDtmsuTRA"

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

            # Lấy danh sách giáo viên
            teachers = []
            if c.get("teachers"):
                for t in c["teachers"]:
                    teacher_info = t.get("teacher", {})
                    if teacher_info.get("fullName"):
                        teachers.append({
                            "name": teacher_info.get("fullName"),
                            "email": teacher_info.get("email"),
                            "role": t.get("role", {}).get("name")
                        })

            # Lấy slots và tính comments của giáo viên
            slots = []
            total_slots_with_students = 0
            slots_with_full_teacher_comments = 0

            if c.get("slots"):
                for s in c["slots"]:
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

            # Xác định khối từ course name — gộp "4+" vào "Robotics"
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
                "slotsWithFullComments": slots_with_full_teacher_comments
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

def save_teachers(data):
    with open("public/teachers.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(data)} giáo viên vào public/teachers.json")

# ─────────────────────────────────────────────────────────────────────────────
# TEACHER POINT (TP) FETCH
# ─────────────────────────────────────────────────────────────────────────────

def get_survey_id_for_class(class_id):
    """Lấy surveyId của lớp qua findOneClassSurvey."""
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
            return result.get("surveyId")
    except Exception as e:
        print(f"    ⚠ get_survey_id error for {class_id}: {e}")
    return None


def get_survey_responses(survey_id, class_id):
    """Lấy tất cả responses của một surveyId, filter theo classId trong metadata."""
    all_responses = []
    page = 0
    # API trả về total=0 dù có data — dùng limit lớn và dừng khi không còn items
    while True:
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
                  id
                  submittedAt
                  metadata
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
            # Filter theo classId trong metadata
            for r in items:
                try:
                    meta = json.loads(r.get("metadata", "{}"))
                except Exception:
                    meta = {}
                if meta.get("classId") == class_id:
                    all_responses.append(r)
            # Nếu trả về ít hơn limit thì đã hết
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


async def async_get_survey_id(session: aiohttp.ClientSession, class_id: str) -> str | None:
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
    return result.get("surveyId") if result else None


async def async_get_responses(session: aiohttp.ClientSession, survey_id: str, class_id: str) -> list:
    """Fetch tất cả pages của survey, filter theo classId."""
    all_responses = []
    page = 0
    while True:
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
        survey_id = await async_get_survey_id(session, class_id)
        if not survey_id:
            return {
                "classId": class_id, "className": class_name,
                "centre": c.get("centre"), "block": c.get("block"),
                "teachers": c.get("teachers", []),
                "tp1": None, "tp2": None,
                "tp1_students": [], "tp2_students": []
            }

        responses = await async_get_responses(session, survey_id, class_id)
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
    """
    # Lọc lớp cần xử lý
    candidates = [
        c for c in classes_data
        if c.get("status") == "FINISHED"
        and c.get("block") == "Coding"
        and is_regular_class(c.get("name", ""))
    ]
    print(f"\n📊 TP candidates: {len(candidates)} lớp FINISHED Coding chính quy")

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

    # Fetch async
    new_results = asyncio.run(_fetch_tp_async(to_fetch))

    # Gộp cache + kết quả mới, giữ thứ tự theo candidates
    result_map = {r["classId"]: r for r in new_results}
    result_map.update({r["classId"]: r for r in cached})

    return [result_map[c["id"]] for c in candidates if c["id"] in result_map]


def save_tp(data):
    with open(TP_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Đã lưu {len(data)} lớp TP vào {TP_CACHE_FILE}")


if __name__ == "__main__":
    print("=" * 50)
    print("📚 Fetching classes...")
    print("=" * 50)
    data = fetch_all()
    save(data)

    print()
    print("=" * 50)
    print("👨‍🏫 Fetching teachers...")
    print("=" * 50)
    teachers = fetch_teachers()
    save_teachers(teachers)

    print()
    print("=" * 50)
    print("📊 Fetching Teacher Points (TP)...")
    print("=" * 50)
    tp_data = fetch_tp(data)
    save_tp(tp_data)
