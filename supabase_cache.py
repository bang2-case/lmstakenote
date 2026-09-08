import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"
SCHEMA_SQL_PATH = ROOT / "scripts" / "supabase_relational_schema.sql"
LMS_SCHEMA = "lms"


RELATIONAL_TABLES = [
    "classes",
    "class_teachers",
    "slots",
    "slot_comments",
    "slot_students",
    "class_students",
    "incomplete_students",
    "teachers",
    "teacher_centres",
    "teacher_blocks",
    "teacher_course_lines",
    "tp_records",
    "tp_students",
    "tp_teachers",
    "cp_records",
    "cp_students",
    "cp_teachers",
    "assignment_records",
    "assignment_students",
    "assignment_lessons",
    "assignment_submissions",
    "assignment_teachers",
    "assignment_fetch_errors",
    "oh_records",
    "oh_courses",
    "oh_course_lines",
    "oh_appointments",
    "oh_appointment_courses",
]

CONFLICT_COLUMNS = {
    "classes": ["id"],
    "class_teachers": ["id"],
    "slots": ["id"],
    "slot_comments": ["id"],
    "slot_students": ["id"],
    "class_students": ["id"],
    "incomplete_students": ["id"],
    "teachers": ["id"],
    "teacher_centres": ["id"],
    "teacher_blocks": ["id"],
    "teacher_course_lines": ["id"],
    "tp_records": ["classid"],
    "tp_students": ["id"],
    "tp_teachers": ["id"],
    "cp_records": ["classid"],
    "cp_students": ["id"],
    "cp_teachers": ["id"],
    "assignment_records": ["classid"],
    "assignment_students": ["classid", "studentuid"],
    "assignment_lessons": ["classid", "id"],
    "assignment_submissions": ["id"],
    "assignment_teachers": ["id"],
    "assignment_fetch_errors": ["classid"],
    "oh_records": ["id"],
    "oh_courses": ["id"],
    "oh_course_lines": ["id"],
    "oh_appointments": ["id"],
    "oh_appointment_courses": ["id"],
}

CAMEL_CASE_KEYS = {
    "studentcount": "studentCount",
    "attendedcount": "attendedCount",
    "completedcount": "completedCount",
    "completionrate": "completionRate",
    "commentpercentage": "commentPercentage",
    "totalslotswithstudents": "totalSlotsWithStudents",
    "slotswithfullcomments": "slotsWithFullComments",
    "startdate": "startDate",
    "enddate": "endDate",
    "createdat": "createdAt",
    "updatedat": "updatedAt",
    "classid": "classId",
    "slotid": "slotId",
    "starttime": "startTime",
    "endtime": "endTime",
    "commentstatus": "commentStatus",
    "studentsinslot": "studentsInSlot",
    "studentswithcomment": "studentsWithComment",
    "sessionindex": "sessionIndex",
    "slotdate": "slotDate",
    "studentid": "studentId",
    "studentname": "studentName",
    "sendcommentstatus": "sendCommentStatus",
    "activeinclass": "activeInClass",
    "retentiondate": "retentionDate",
    "completioninfo": "completionInfo",
    "previousclass": "previousClass",
    "fullname": "fullName",
    "personalemail": "personalEmail",
    "phonenumber": "phoneNumber",
    "isactive": "isActive",
    "teacherpoint": "teacherPoint",
    "joineddate": "joinedDate",
    "teacherid": "teacherId",
    "courseline": "courseLine",
    "classname": "className",
    "textanswers": "textAnswers",
    "cp1theory": "cp1Theory",
    "cp1practical": "cp1Practical",
    "cp2theory": "cp2Theory",
    "cp2practical": "cp2Practical",
    "theoryscore": "theoryScore",
    "practicalscore": "practicalScore",
    "displayname": "displayName",
    "studentuid": "studentUid",
    "learningcourseid": "learningCourseId",
    "displayorder": "displayOrder",
    "lessonid": "lessonId",
    "studentoriginalid": "studentOriginalId",
    "classsessionid": "classSessionId",
    "markedat": "markedAt",
    "markedby": "markedBy",
    "submittedat": "submittedAt",
    "submittedcount": "submittedCount",
    "expectedcount": "expectedCount",
    "gradablesubmittedcount": "gradableSubmittedCount",
    "markedcount": "markedCount",
    "inprogresscount": "inProgressCount",
    "averagescore": "averageScore",
    "lessoncount": "lessonCount",
    "contentjson": "contentJson",
    "errortype": "errorType",
    "fetchedat": "fetchedAt",
    "centreid": "centreId",
    "centrename": "centreName",
    "centreshortname": "centreShortName",
    "teacherfullname": "teacherFullName",
    "teacherusername": "teacherUsername",
    "teacheremail": "teacherEmail",
    "managernote": "managerNote",
    "createdbyusername": "createdByUsername",
    "ohid": "ohId",
    "courseid": "courseId",
    "coursename": "courseName",
    "shortname": "shortName",
    "courselineid": "courseLineId",
    "courselinename": "courseLineName",
    "appointmentid": "appointmentId",
    "candidateid": "candidateId",
    "candidatename": "candidateName",
}


def _load_env_file() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values

    for raw_line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def get_env_value(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is not None:
        return value.strip()
    return _load_env_file().get(name, default).strip()


def get_database_url() -> str:
    return _normalize_database_url(get_env_value("DATABASE_URL"))


def _normalize_database_url(database_url: str) -> str:
    if "://" not in database_url:
        return database_url

    scheme, rest = database_url.split("://", 1)
    authority, slash, tail = rest.partition("/")
    if authority.count("@") <= 1 or ":" not in authority:
        return database_url

    userinfo, hostinfo = authority.rsplit("@", 1)
    username, password = userinfo.split(":", 1)
    encoded_user = quote(username, safe="%")
    encoded_password = quote(password, safe="%")
    return f"{scheme}://{encoded_user}:{encoded_password}@{hostinfo}{slash}{tail}"


def wants_supabase_cache() -> bool:
    flag = get_env_value("USE_SUPABASE", "0").lower()
    is_vercel = bool(os.getenv("VERCEL")) or bool(os.getenv("VERCEL_ENV"))
    return flag in {"1", "true", "yes", "on"} or is_vercel


def use_supabase_cache() -> bool:
    return wants_supabase_cache() and bool(get_database_url())


def _connect():
    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured.")
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("Missing psycopg. Run pip install -r requirements.txt.") from exc
    return psycopg.connect(database_url, row_factory=dict_row)


def ensure_cache_schema() -> None:
    with _connect() as conn:
        conn.execute("CREATE SCHEMA IF NOT EXISTS lms")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lms.api_cache (
                key text PRIMARY KEY,
                payload text NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lms.class_students_cache (
                class_id text PRIMARY KEY,
                payload text NOT NULL,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lms.classes_summary_cache (
                id text PRIMARY KEY,
                payload text NOT NULL,
                created_at_sort text,
                updated_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_classes_summary_cache_created_at "
            "ON lms.classes_summary_cache(created_at_sort DESC)"
        )
        conn.execute("REVOKE ALL ON SCHEMA lms FROM anon, authenticated")
        conn.execute("REVOKE ALL ON ALL TABLES IN SCHEMA lms FROM anon, authenticated")
        conn.commit()


def ensure_relational_schema() -> None:
    if not SCHEMA_SQL_PATH.exists():
        raise FileNotFoundError(f"Missing {SCHEMA_SQL_PATH}")
    with _connect() as conn:
        conn.execute(SCHEMA_SQL_PATH.read_text(encoding="utf-8"))
        conn.commit()


def _camelize(row: dict[str, Any]) -> dict[str, Any]:
    return {CAMEL_CASE_KEYS.get(key, key): value for key, value in dict(row).items()}


def _read_rows(
    table: str,
    *,
    where: tuple[str, Any] | None = None,
    order_by: str | None = None,
    desc: bool = False,
) -> list[dict[str, Any]]:
    if table not in RELATIONAL_TABLES:
        raise ValueError(f"Unsupported table: {table}")
    params: list[Any] = []
    query = f"SELECT * FROM {LMS_SCHEMA}.{table}"
    if where:
        column, value = where
        if not column.replace("_", "").isalnum():
            raise ValueError(f"Unsupported column: {column}")
        query += f" WHERE {column} = %s"
        params.append(value)
    if order_by:
        if not order_by.replace("_", "").isalnum():
            raise ValueError(f"Unsupported order column: {order_by}")
        query += f" ORDER BY {order_by} {'DESC' if desc else 'ASC'}"

    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_camelize(row) for row in rows]


def _decode_json(value: Any, fallback: Any):
    if value is None:
        return fallback
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return fallback


def decode_class_student_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "classId": row.get("classId"),
        "studentId": row.get("studentId"),
        "activeInClass": bool(row.get("activeInClass")),
        "completed": bool(row.get("completed")),
        "attended": bool(row.get("attended")),
        "note": row.get("note"),
        "grade": _decode_json(row.get("grade"), None),
        "retentionDate": row.get("retentionDate"),
        "completionInfo": _decode_json(row.get("completionInfo"), None),
        "student": _decode_json(row.get("student"), {}),
        "previousClass": _decode_json(row.get("previousClass"), None),
    }


def _teacher_entries(rows: list[dict[str, Any]], id_key: str = "classId") -> dict[str, list]:
    result: dict[str, list] = {}
    for row in rows:
        result.setdefault(row[id_key], []).append(
            {"name": row.get("name"), "email": row.get("email"), "role": row.get("role")}
        )
    return result


def read_classes_db(
    include_slot_students: bool = False,
    include_students: bool = False,
    include_slots: bool = True,
) -> list[dict[str, Any]]:
    classes = _read_rows("classes", order_by="createdat", desc=True)
    if not classes:
        return []

    teachers_map = _teacher_entries(_read_rows("class_teachers"), "classId")

    slots_map: dict[str, list] = {}
    if include_slots:
        for slot in _read_rows("slots", order_by="date"):
            slots_map.setdefault(slot["classId"], []).append({
                "id": slot.get("id"),
                "date": slot.get("date"),
                "startTime": slot.get("startTime"),
                "endTime": slot.get("endTime"),
                "commentStatus": slot.get("commentStatus"),
                "studentsInSlot": slot.get("studentsInSlot"),
                "studentsWithComment": slot.get("studentsWithComment"),
            })

    if include_slots and include_slot_students:
        slot_students_map: dict[str, list] = {}
        for student in _read_rows("slot_students", order_by="id"):
            slot_students_map.setdefault(student["slotId"], []).append({
                "id": student.get("studentId"),
                "name": student.get("studentName"),
                "status": student.get("status"),
            })
        for slot_list in slots_map.values():
            for slot in slot_list:
                slot["students"] = slot_students_map.get(slot["id"], [])

    class_students_map: dict[str, list] = {}
    if include_students:
        for row in _read_rows("class_students", order_by="id"):
            class_students_map.setdefault(row["classId"], []).append(decode_class_student_row(row))

    incomplete_map: dict[str, list] = {}
    for row in _read_rows("incomplete_students"):
        incomplete_map.setdefault(row["classId"], []).append(row.get("name"))

    for item in classes:
        cid = item["id"]
        item.pop("updatedAt", None)
        item["teachers"] = teachers_map.get(cid, [])
        item["slots"] = slots_map.get(cid, [])
        item["incompleteStudents"] = incomplete_map.get(cid, [])
        if include_students:
            item["students"] = class_students_map.get(cid, [])
    return classes


def read_class_students_db(class_id: str) -> list[dict[str, Any]] | None:
    rows = _read_rows("class_students", where=("classid", class_id), order_by="id")
    if not rows:
        return None
    return [decode_class_student_row(row) for row in rows]


def write_class_students_db(class_id: str, payload: list[dict[str, Any]]) -> None:
    ensure_relational_schema()
    rows = []
    for item in payload:
        student = item.get("student") or {}
        rows.append((
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
    with _connect() as conn:
        conn.execute("DELETE FROM lms.class_students WHERE classid = %s", (class_id,))
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO lms.class_students
                (id, classid, studentid, activeinclass, completed, attended,
                 note, grade, retentiondate, completioninfo, student, previousclass)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (id) DO UPDATE
                SET studentid = EXCLUDED.studentid,
                    activeinclass = EXCLUDED.activeinclass,
                    completed = EXCLUDED.completed,
                    attended = EXCLUDED.attended,
                    note = EXCLUDED.note,
                    grade = EXCLUDED.grade,
                    retentiondate = EXCLUDED.retentiondate,
                    completioninfo = EXCLUDED.completioninfo,
                    student = EXCLUDED.student,
                    previousclass = EXCLUDED.previousclass
                """,
                rows,
            )
        conn.commit()


def read_slot_students_db(class_id: str) -> dict[str, list]:
    result: dict[str, list] = {}
    for row in _read_rows("slot_students", where=("classid", class_id), order_by="id"):
        result.setdefault(row["slotId"], []).append({
            "id": row.get("studentId"),
            "name": row.get("studentName"),
            "status": row.get("status"),
        })
    return result


def read_comment_rows_db(class_id: str) -> list[dict[str, Any]]:
    return _read_rows("slot_comments", where=("classid", class_id), order_by="sessionindex")


def read_teachers_db() -> list[dict[str, Any]]:
    teachers = _read_rows("teachers", order_by="fullname")
    if not teachers:
        return []
    centres_map: dict[str, list] = {}
    for row in _read_rows("teacher_centres"):
        centres_map.setdefault(row["teacherId"], []).append(row.get("centre"))
    blocks_map: dict[str, list] = {}
    for row in _read_rows("teacher_blocks"):
        blocks_map.setdefault(row["teacherId"], []).append(row.get("block"))
    course_lines_map: dict[str, list] = {}
    for row in _read_rows("teacher_course_lines"):
        course_lines_map.setdefault(row["teacherId"], []).append(row.get("courseLine"))

    for teacher in teachers:
        teacher["centres"] = centres_map.get(teacher["id"], [])
        teacher["blocks"] = blocks_map.get(teacher["id"], [])
        teacher["courseLines"] = course_lines_map.get(teacher["id"], [])
    return teachers


def read_tp_db() -> list[dict[str, Any]]:
    records = _read_rows("tp_records", order_by="classname")
    if not records:
        return []
    students_map: dict[str, dict] = {}
    for student in _read_rows("tp_students", order_by="classid"):
        cid = student["classId"]
        students_map.setdefault(cid, {"tp1_students": [], "tp2_students": []})
        entry = {
            "name": student.get("name"),
            "score": student.get("score"),
            "textAnswers": _decode_json(student.get("textAnswers"), []),
        }
        target = "tp1_students" if student.get("round") == 1 else "tp2_students"
        students_map[cid][target].append(entry)
    teachers_map = _teacher_entries(_read_rows("tp_teachers"), "classId")
    for record in records:
        cid = record["classId"]
        record["teachers"] = teachers_map.get(cid, [])
        record["tp1_students"] = students_map.get(cid, {}).get("tp1_students", [])
        record["tp2_students"] = students_map.get(cid, {}).get("tp2_students", [])
    return records


def read_cp_db() -> list[dict[str, Any]]:
    records = _read_rows("cp_records", order_by="classname")
    if not records:
        return []
    students_map: dict[str, dict] = {}
    for student in _read_rows("cp_students", order_by="classid"):
        cid = student["classId"]
        students_map.setdefault(cid, {"cp1_students": [], "cp2_students": []})
        entry = {
            "name": student.get("name"),
            "theoryScore": student.get("theoryScore"),
            "practicalScore": student.get("practicalScore"),
        }
        target = "cp1_students" if student.get("round") == 1 else "cp2_students"
        students_map[cid][target].append(entry)
    teachers_map = _teacher_entries(_read_rows("cp_teachers"), "classId")
    for record in records:
        cid = record["classId"]
        record["teachers"] = teachers_map.get(cid, [])
        record["cp1_students"] = students_map.get(cid, {}).get("cp1_students", [])
        record["cp2_students"] = students_map.get(cid, {}).get("cp2_students", [])
    return records


def _is_submitted(submission: dict[str, Any]) -> bool:
    status = (submission.get("status") or "").upper()
    return (
        status in {"SUBMITTED", "MARKED"}
        or bool(str(submission.get("submittedAt") or "").strip())
        or int(submission.get("submittedCount") or 0) > 0
    )


def _is_gradable(submission: dict[str, Any]) -> bool:
    return (submission.get("status") or "").upper() not in {"REDO", "RE_SUBMITTED"}


def _is_marked(submission: dict[str, Any]) -> bool:
    status = (submission.get("status") or "").upper()
    return status == "MARKED" or bool(str(submission.get("markedAt") or "").strip()) or bool(str(submission.get("markedBy") or "").strip())


def _is_expected_submission(submission: dict[str, Any]) -> bool:
    return (submission.get("type") or "").upper() == "UPLOAD_FILE" or (submission.get("category") or "").upper().startswith("PRACTICE_TASK")


def read_assignments_db() -> dict[str, Any]:
    with _connect() as conn:
        records = [_camelize(row) for row in conn.execute(
            """
            SELECT classid, classname, centre, block, status
            FROM lms.assignment_records
            ORDER BY classname
            """
        ).fetchall()]
        errors = [_camelize(row) for row in conn.execute(
            """
            SELECT e.classid, e.classname, e.centre, e.block, e.status,
                   e.errortype, e.message, e.fetchedat
            FROM lms.assignment_fetch_errors e
            LEFT JOIN lms.assignment_records ar ON ar.classid = e.classid
            WHERE ar.classid IS NULL
            ORDER BY e.fetchedat DESC, e.classname
            """
        ).fetchall()]
        student_counts = {
            row["classid"]: int(row["total"] or 0)
            for row in conn.execute(
                """
                SELECT classid, COUNT(*) AS total
                FROM lms.assignment_students
                GROUP BY classid
                """
            ).fetchall()
        }
        lesson_counts = {
            row["classid"]: int(row["total"] or 0)
            for row in conn.execute(
                """
                SELECT classid, COUNT(*) AS total
                FROM lms.assignment_lessons
                WHERE isactive = 1
                GROUP BY classid
                """
            ).fetchall()
        }
        summary = {
            row["classId"]: row
            for row in (
                _camelize(row)
                for row in conn.execute(
                    """
                    WITH expected AS (
                        SELECT *,
                               (
                                   UPPER(COALESCE(type, '')) = 'UPLOAD_FILE'
                                   OR UPPER(COALESCE(category, '')) LIKE 'PRACTICE_TASK%'
                               ) AS is_expected,
                               (
                                   UPPER(COALESCE(status, '')) IN ('SUBMITTED', 'MARKED')
                                   OR NULLIF(BTRIM(COALESCE(submittedat, '')), '') IS NOT NULL
                                   OR COALESCE(submittedcount, 0) > 0
                               ) AS is_submitted,
                               UPPER(COALESCE(status, '')) NOT IN ('REDO', 'RE_SUBMITTED') AS is_gradable,
                               (
                                   UPPER(COALESCE(status, '')) = 'MARKED'
                                   OR NULLIF(BTRIM(COALESCE(markedat, '')), '') IS NOT NULL
                                   OR NULLIF(BTRIM(COALESCE(markedby, '')), '') IS NOT NULL
                               ) AS is_marked
                        FROM lms.assignment_submissions
                    )
                    SELECT
                        classid,
                        COUNT(*) FILTER (WHERE is_expected) AS expectedcount,
                        COUNT(*) FILTER (WHERE is_expected AND is_submitted) AS submittedcount,
                        COUNT(*) FILTER (WHERE is_expected AND is_submitted AND is_gradable) AS gradablesubmittedcount,
                        COUNT(*) FILTER (WHERE is_expected AND is_submitted AND is_gradable AND is_marked) AS markedcount,
                        COUNT(*) FILTER (WHERE is_expected AND UPPER(COALESCE(status, '')) = 'IN_PROGRESS') AS inprogresscount,
                        AVG(score) FILTER (WHERE is_expected AND is_submitted AND is_gradable AND COALESCE(score, 0) > 0) AS averagescore
                    FROM expected
                    GROUP BY classid
                    """
                ).fetchall()
            )
        }
        teachers_rows = [_camelize(row) for row in conn.execute(
            "SELECT classid, name, email, role FROM lms.assignment_teachers"
        ).fetchall()]
    teachers_map = _teacher_entries(teachers_rows, "classId")

    for record in records:
        cid = record["classId"]
        item = summary.get(cid, {})
        submitted_count = int(item.get("submittedCount") or 0)
        gradable_count = int(item.get("gradableSubmittedCount") or 0)
        marked_count = int(item.get("markedCount") or 0)
        student_count = int(student_counts.get(cid, 0) or 0)
        lesson_count = int(lesson_counts.get(cid, 0) or 0)
        expected_count = int(item.get("expectedCount") or 0) or student_count * lesson_count
        record["teachers"] = teachers_map.get(cid, [])
        record["students"] = []
        record["lessons"] = []
        record["submissions"] = []
        record["studentCount"] = student_count
        record["lessonCount"] = lesson_count
        record["expectedCount"] = expected_count
        record["submittedCount"] = submitted_count
        record["gradableSubmittedCount"] = gradable_count
        record["markedCount"] = marked_count
        record["inProgressCount"] = int(item.get("inProgressCount") or 0)
        record["needsMarkingCount"] = max(0, gradable_count - marked_count)
        average_score = item.get("averageScore")
        record["averageScore"] = round(average_score) if average_score is not None else None
    return {"records": records, "errors": errors}


def read_assignment_detail_db(class_id: str) -> dict[str, Any] | None:
    records = _read_rows("assignment_records", where=("classid", class_id))
    if not records:
        return None
    record = records[0]
    record["students"] = [
        {"id": row.get("id"), "displayName": row.get("displayName"), "studentUid": row.get("studentUid")}
        for row in _read_rows("assignment_students", where=("classid", class_id), order_by="displayname")
    ]
    record["lessons"] = [
        {
            "id": lesson.get("id"),
            "name": lesson.get("name"),
            "type": lesson.get("type"),
            "isActive": bool(lesson.get("isActive")),
            "learningCourseId": lesson.get("learningCourseId"),
            "displayOrder": lesson.get("displayOrder") or 0,
        }
        for lesson in _read_rows("assignment_lessons", where=("classid", class_id), order_by="displayorder")
    ]
    submissions = []
    for submission in _read_rows("assignment_submissions", where=("classid", class_id), order_by="lessonid"):
        submissions.append({
            "id": submission.get("id"),
            "type": submission.get("type"),
            "note": submission.get("note"),
            "score": submission.get("score") or 0,
            "status": submission.get("status"),
            "category": submission.get("category"),
            "classId": submission.get("classId"),
            "lessonId": submission.get("lessonId"),
            "learningCourseId": submission.get("learningCourseId"),
            "studentUid": submission.get("studentUid"),
            "studentOriginalId": submission.get("studentOriginalId"),
            "classSessionId": submission.get("classSessionId"),
            "markedAt": submission.get("markedAt"),
            "markedBy": submission.get("markedBy"),
            "createdAt": submission.get("createdAt"),
            "submittedAt": submission.get("submittedAt"),
            "submittedCount": submission.get("submittedCount") or 0,
            "content": _decode_json(submission.get("contentJson"), {}),
        })
    record["submissions"] = submissions
    record["teachers"] = [
        {"name": row.get("name"), "email": row.get("email"), "role": row.get("role")}
        for row in _read_rows("assignment_teachers", where=("classid", class_id))
    ]
    return record


def read_oh_db() -> list[dict[str, Any]]:
    records = _read_rows("oh_records", order_by="starttime", desc=True)
    if not records:
        return []

    courses_map: dict[str, list] = {}
    for row in _read_rows("oh_courses"):
        courses_map.setdefault(row["ohId"], []).append(
            {"id": row.get("courseId"), "name": row.get("courseName"), "shortName": row.get("shortName")}
        )

    course_lines_map: dict[str, list] = {}
    for row in _read_rows("oh_course_lines"):
        course_lines_map.setdefault(row["ohId"], []).append(
            {"id": row.get("courseLineId"), "name": row.get("courseLineName")}
        )

    appointment_courses_map: dict[str, list] = {}
    for row in _read_rows("oh_appointment_courses"):
        appointment_courses_map.setdefault(row["appointmentId"], []).append(
            {"id": row.get("courseId"), "name": row.get("courseName"), "shortName": row.get("shortName")}
        )

    appointments_map: dict[str, list] = {}
    for row in _read_rows("oh_appointments"):
        appointments_map.setdefault(row["ohId"], []).append({
            "id": row.get("id"),
            "title": row.get("title"),
            "candidate": {"id": row.get("candidateId"), "fullName": row.get("candidateName")} if row.get("candidateId") else None,
            "courses": appointment_courses_map.get(row.get("id"), []),
            "status": row.get("status"),
            "note": row.get("note"),
        })

    for record in records:
        oid = record["id"]
        record["centre"] = {
            "id": record.pop("centreId"),
            "name": record.pop("centreName"),
            "shortName": record.pop("centreShortName"),
        } if record.get("centreId") else None
        record["teacher"] = {
            "id": record.pop("teacherId"),
            "fullName": record.pop("teacherFullName"),
            "username": record.pop("teacherUsername"),
            "email": record.pop("teacherEmail"),
        } if record.get("teacherId") else None
        record["createdBy"] = {"username": record.pop("createdByUsername")} if record.get("createdByUsername") else None
        record["courses"] = courses_map.get(oid, [])
        record["courseLines"] = course_lines_map.get(oid, [])
        record["appointments"] = appointments_map.get(oid, [])
    return records


def _sqlite_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return bool(row)


def _prepare_sqlite_row(table: str, row: sqlite3.Row, columns: list[str]) -> dict[str, Any]:
    data = {column.lower(): row[column] for column in columns}
    if table == "assignment_students" and not data.get("studentuid"):
        data["studentuid"] = data.get("id") or data.get("displayname") or "unknown"
    if table == "assignment_lessons" and not data.get("id"):
        data["id"] = data.get("name") or data.get("learningcourseid") or "unknown"
    for timestamp_col in ("updatedat", "fetchedat"):
        if data.get(timestamp_col) == "":
            data[timestamp_col] = None
    return data


def _sync_table(
    sqlite_conn: sqlite3.Connection,
    pg_conn,
    table: str,
    *,
    batch_size: int = 1000,
    progress: Callable[[str, int], None] | None = None,
) -> int:
    if not _sqlite_table_exists(sqlite_conn, table):
        return 0

    columns = [row["name"] for row in sqlite_conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if not columns:
        return 0
    pg_columns = [column.lower() for column in columns]
    conflict_columns = CONFLICT_COLUMNS[table]
    update_columns = [column for column in pg_columns if column not in conflict_columns]

    try:
        from psycopg import sql
    except ImportError as exc:
        raise RuntimeError("Missing psycopg. Run pip install -r requirements.txt.") from exc

    insert_sql = sql.SQL("INSERT INTO {}.{} ({}) VALUES ({})").format(
        sql.Identifier(LMS_SCHEMA),
        sql.Identifier(table),
        sql.SQL(", ").join(sql.Identifier(column) for column in pg_columns),
        sql.SQL(", ").join(sql.Placeholder() for _ in pg_columns),
    )
    if update_columns:
        insert_sql += sql.SQL(" ON CONFLICT ({}) DO UPDATE SET {}").format(
            sql.SQL(", ").join(sql.Identifier(column) for column in conflict_columns),
            sql.SQL(", ").join(
                sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(column), sql.Identifier(column))
                for column in update_columns
            ),
        )
    else:
        insert_sql += sql.SQL(" ON CONFLICT ({}) DO NOTHING").format(
            sql.SQL(", ").join(sql.Identifier(column) for column in conflict_columns)
        )

    pg_conn.execute(sql.SQL("TRUNCATE {}.{}").format(sql.Identifier(LMS_SCHEMA), sql.Identifier(table)))
    total = 0
    sqlite_cur = sqlite_conn.execute(f"SELECT * FROM {table}")
    while True:
        rows = sqlite_cur.fetchmany(batch_size)
        if not rows:
            break
        prepared = [_prepare_sqlite_row(table, row, columns) for row in rows]
        values = [tuple(item.get(column) for column in pg_columns) for item in prepared]
        with pg_conn.cursor() as pg_cur:
            pg_cur.executemany(insert_sql, values)
        total += len(rows)
        if progress:
            progress(table, total)
    return total


def sync_sqlite_to_supabase(
    db_path: str | Path,
    *,
    batch_size: int = 1000,
    progress: Callable[[str, int], None] | None = None,
) -> dict[str, int]:
    ensure_relational_schema()
    sqlite_path = Path(db_path)
    if not sqlite_path.exists():
        raise FileNotFoundError(f"Missing SQLite database: {sqlite_path}")

    result: dict[str, int] = {}
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    try:
        with _connect() as pg_conn:
            for table in RELATIONAL_TABLES:
                result[table] = _sync_table(
                    sqlite_conn,
                    pg_conn,
                    table,
                    batch_size=batch_size,
                    progress=progress,
                )
            pg_conn.commit()
    finally:
        sqlite_conn.close()
    return result


def read_api_cache(key: str) -> Any | None:
    with _connect() as conn:
        row = conn.execute("SELECT payload FROM lms.api_cache WHERE key = %s", (key,)).fetchone()
    if not row:
        return None
    payload = row["payload"]
    return json.loads(payload) if isinstance(payload, str) else payload


def write_api_cache(key: str, payload: Any) -> None:
    ensure_cache_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO lms.api_cache (key, payload, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (key) DO UPDATE
            SET payload = EXCLUDED.payload,
                updated_at = now()
            """,
            (key, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()


def read_classes_summary_cache() -> list[dict] | None:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT payload
            FROM lms.classes_summary_cache
            ORDER BY created_at_sort DESC NULLS LAST
            """
        ).fetchall()
    if not rows:
        return None
    result: list[dict] = []
    for row in rows:
        payload = row["payload"]
        result.append(json.loads(payload) if isinstance(payload, str) else payload)
    return result


def write_classes_summary_cache(classes: list[dict], batch_size: int = 500, progress=None) -> None:
    ensure_cache_schema()
    rows = [
        (
            item.get("id"),
            json.dumps(item, ensure_ascii=False),
            item.get("createdAt") or "",
        )
        for item in classes
        if item.get("id")
    ]
    with _connect() as conn:
        conn.execute("TRUNCATE lms.classes_summary_cache")
        total = len(rows)
        for start in range(0, total, batch_size):
            batch = rows[start:start + batch_size]
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO lms.classes_summary_cache (id, payload, created_at_sort, updated_at)
                    VALUES (%s, %s, %s, now())
                    ON CONFLICT (id) DO UPDATE
                    SET payload = EXCLUDED.payload,
                        created_at_sort = EXCLUDED.created_at_sort,
                        updated_at = now()
                    """,
                    batch,
                )
            if progress:
                progress(min(start + len(batch), total), total)
        conn.commit()


def read_class_students_cache(class_id: str) -> list[dict] | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM lms.class_students_cache WHERE class_id = %s",
            (class_id,),
        ).fetchone()
    if not row:
        return None
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    return payload if isinstance(payload, list) else None


def write_class_students_cache(class_id: str, payload: list[dict]) -> None:
    ensure_cache_schema()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO lms.class_students_cache (class_id, payload, updated_at)
            VALUES (%s, %s, now())
            ON CONFLICT (class_id) DO UPDATE
            SET payload = EXCLUDED.payload,
                updated_at = now()
            """,
            (class_id, json.dumps(payload, ensure_ascii=False)),
        )
        conn.commit()


def strip_class_slots(classes: list[dict]) -> list[dict]:
    result: list[dict] = []
    for item in classes:
        copied = dict(item)
        copied["slots"] = []
        copied.pop("students", None)
        result.append(copied)
    return result
