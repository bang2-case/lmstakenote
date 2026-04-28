import requests
import json
import time

GRAPHQL_URL = "https://lms-api.mindx.edu.vn/"
TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IjNiMDk1NzQ3YmY4MzMxZWE0YWQ1M2YzNzBjNjMyNjAxNzliMGQyM2EiLCJ0eXAiOiJKV1QifQ.eyJuYW1lIjoiVEUgUGhhbiBOZ-G7jWMgSG_DoG5nIEFuaCIsImlkIjoiNWZmMjZiOWYzNzI5MjAwOTlkMjU4ODIzIiwidXNlcm5hbWUiOiJhbmhwbmgwMDEiLCJyb2xlcyI6WyI1ZmIzNzk4NTBkZGNjYTQ3OGU5M2RlZjgiXSwiaXNzIjoiaHR0cHM6Ly9zZWN1cmV0b2tlbi5nb29nbGUuY29tL21pbmR4LWVkdS1wcm9kIiwiYXVkIjoibWluZHgtZWR1LXByb2QiLCJhdXRoX3RpbWUiOjE3NzczOTkxNjEsInVzZXJfaWQiOiJaakVuTW9ha3FZVE1mNUdOdkVXZEl1OXlPRGEyIiwic3ViIjoiWmpFbk1vYWtxWVRNZjVHTnZFV2RJdTl5T0RhMiIsImlhdCI6MTc3NzM5OTE2MSwiZXhwIjoxNzc3NDAyNzYxLCJlbWFpbCI6ImFuaHBuaEBtaW5keC5jb20udm4iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwicGhvbmVfbnVtYmVyIjoiKzg0MzY2NzU0MzQyIiwiZmlyZWJhc2UiOnsiaWRlbnRpdGllcyI6eyJlbWFpbCI6WyJhbmhwbmhAbWluZHguY29tLnZuIl0sInBob25lIjpbIis4NDM2Njc1NDM0MiJdfSwic2lnbl9pbl9wcm92aWRlciI6ImN1c3RvbSJ9fQ.Gac1Mn7ATFQYhhp8E3N661wh9aFP_UhmZjelbjjzitLZJJpD8fAg-D2ymoQ7YPtmtjwfqKuSFUfSwl2f8YkE6Yzl2owiBa53SLhb-prnn4zT-3GZOzlKZuZmgUvcE8p2i7v9-HcaAJ1VFYR1P7tedz0j7bQA560AS_R37kZxBb8Kn95fL642lpav2tMtYSWWAOIaL7fp3NUehhFIT0O8gUDaRNIqiLI5HWPw62a-_8xBYunesE2mOew6fGHBBZ0-5Np5OVo-i_zD8KU5vIKPZbhY4Z96m2IJPxwIk8zi2vfh1N0NAzlM0QdHZ_8vNtoU6GLkRVTln6f9-tKrHfOEIg"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
    "Content-Language": "en",
    "Origin": "https://lms.mindx.edu.vn",
    "Referer": "https://lms.mindx.edu.vn/"
}

def build_payload(page_index):
    # ID của 4 cơ sở cần lọc - sẽ được điền sau khi tìm thấy
    CENTRE_IDS = []  # Để trống = lấy tất cả, sau đó filter bằng tên
    
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
          customer {
            fullName
          }
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
            
            # Chỉ lấy 4 cơ sở: Tên Lửa, Tây Thạnh, Lũy Bán Bích, Trường Chinh
            if not any(x in centre_name for x in ["Tên Lửa", "Tây Thạnh", "Lũy Bán Bích", "Trường Chinh"]):
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
                    
                    # Chỉ đếm học viên có đi học (không phải ABSENT hoặc ABSENT_WITH_NOTICE)
                    students_present = []
                    for att in student_attendances:
                        status = att.get("status", "")
                        # Bỏ qua học viên vắng
                        if status not in ["ABSENT", "ABSENT_WITH_NOTICE"]:
                            students_present.append(att)
                    
                    students_in_slot = len(students_present)
                    
                    # Đếm số học viên đã được comment
                    students_with_comment = 0
                    students_without_comment = []
                    
                    for att in students_present:
                        student_name = att.get("student", {}).get("fullName", "Unknown")
                        # Kiểm tra có comment không
                        has_comment = False
                        if att.get("comment"):
                            has_comment = True
                        else:
                            # Kiểm tra teacherAttendance có note không
                            for t_att in teacher_attendances:
                                if t_att.get("note"):
                                    has_comment = True
                                    break
                        
                        if has_comment:
                            students_with_comment += 1
                        else:
                            students_without_comment.append(student_name)
                    
                    # Tính trạng thái comment của slot
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
                    
                    slot_data = {
                        "id": s.get("_id"),
                        "date": s.get("date"),
                        "startTime": s.get("startTime"),
                        "endTime": s.get("endTime"),
                        "commentStatus": slot_comment_status,
                        "studentsInSlot": students_in_slot,
                        "studentsWithComment": students_with_comment
                    }
                    slots.append(slot_data)
            
            # Tính % comments dựa trên slots
            comment_percentage = 0
            if total_slots_with_students > 0:
                comment_percentage = round((slots_with_full_teacher_comments / total_slots_with_students) * 100)
            
            # Đếm học viên
            student_count = len(c.get("students", []))

            # Xác định khối từ course name - chỉ có 4 khối: 4+, Robotics, ART, Coding
            course_name = c.get("course", {}).get("name", "")
            block = "Coding"  # default - bao gồm Producer, Computer Science, Web, Game, App Development, etc.
            if course_name:
                course_lower = course_name.lower()
                if "4+" in course_name or "robotics 4" in course_lower:
                    block = "4+"
                elif "robotics" in course_lower or "robot" in course_lower:
                    block = "Robotics"
                elif any(x in course_lower for x in ["visual", "graphic", "art", "design", "multimedia", "creative"]):
                    block = "ART"
                # Tất cả còn lại → "Coding" (Producer, Computer Science, Web Development, Game Development, App Development, etc.)

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
                "commentPercentage": comment_percentage,
                "totalSlotsWithStudents": total_slots_with_students,
                "slotsWithFullComments": slots_with_full_teacher_comments
            })

        if len(all_data) >= total or len(all_data) >= 500:  # Giới hạn 500 lớp
            break

        page += 1
        time.sleep(0.5)

    return all_data

def save(data):
    with open("public/classes.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Đã lưu {len(data)} lớp vào public/classes.json")

if __name__ == "__main__":
    data = fetch_all()
    save(data)
