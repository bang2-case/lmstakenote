import requests
import json
import time

GRAPHQL_URL = "https://lms-api.mindx.edu.vn/"
TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjJiMzZhYjQxYTczOTJlMTRlNjM1ZmRlM2M2YWYwOWZlYmFhM2YyZDYiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiVEUgUGhhbiBOZ-G7jWMgSG_DoG5nIEFuaCIsImlkIjoiNWZmMjZiOWYzNzI5MjAwOTlkMjU4ODIzIiwidXNlcm5hbWUiOiJhbmhwbmgwMDEiLCJyb2xlcyI6WyI1ZmIzNzk4NTBkZGNjYTQ3OGU5M2RlZjgiXSwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL21pbmR4LWVkdS1wcm9kIiwiYXVkIjoibWluZHgtZWR1LXByb2QiLCJhdXRoX3RpbWUiOjE3Nzc0Mzg0MjMsInVzZXJfaWQiOiJaakVuTW9ha3FZVE1mNUdOdkVXZEl1OXlPRGEyIiwic3ViIjoiWmpFbk1vYWtxWVRNZjVHTnZFV2RJdTl5T0RhMiIsImlhdCI6MTc3NzQzODQyNCwiZXhwIjoxNzc3NDQyMDI0LCJlbWFpbCI6ImFuaHBuaEBtaW5keC5jb20udm4iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwicGhvbmVfbnVtYmVyIjoiKzg0MzY2NzU0MzQyIiwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJhbmhwbmhAbWluZHguY29tLnZuIl0sInBob25lIjpbIis4NDM2Njc1NDM0MiJdfSwic2lnbl9pbl9wcm92aWRlciI6ImN1c3RvbSJ9fQ.QIMEIug4FFnqpCQCe-DXORZF_sLUzP5aNOKQiOCr8_xvdFIz486DhG9_hxqCNdjGf6tSkt1M216jqLs2W6l-p3H4c3kewX9o3Nw2FitibJgRDY_xrbuU--TDVX3Lb5WBfQPDXqn7wmQHOM3gpPbeG6zWzzdqwBeq20g2bKOsLtylW7UJAuMxRF-NVU9Qwwaduby0V6aICUvvM18_4ugJebGGEqN3zMimd9Is8nSI0DJQV124Dtc9OPyd12JGCzjKYcYnB7um1RppoqygQKJtx3AIlut9CRTyWY6J8FF8q1jJhBcIFz3DfZ2u3PaXDC6d_RHGYT08dWHNv54LZXnpUQ"

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

            # Xác định khối từ course name
            course_name = c.get("course", {}).get("name", "")
            block = "Coding"
            if course_name:
                course_lower = course_name.lower()
                if "4+" in course_name or "robotics 4" in course_lower:
                    block = "4+"
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

def save(data):
    with open("public/classes.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Đã lưu {len(data)} lớp vào public/classes.json")

if __name__ == "__main__":
    data = fetch_all()
    save(data)
