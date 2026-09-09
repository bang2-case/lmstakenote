import csv
import html
import json
import os
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from server import GRAPHQL_URL, TOKEN_REFRESH_THRESHOLD, check_token, read_token, refresh_token_silent

DB_PATH = os.path.join(ROOT, "classroom_data.db")
EXPORTS_DIR = os.path.join(ROOT, "exports")
BASE_CSV = os.path.join(EXPORTS_DIR, "hoc_vien_robotics_hcm1_hcm4_tu_7_tuoi_tro_len_co_id.csv")
OUTPUT_CSV = os.path.join(EXPORTS_DIR, "hoc_vien_robotics_hcm1_hcm4_tu_6_tuoi_tro_len_co_id.csv")

HEADERS = [
    "ID học viên",
    "Tên",
    "Lớp hiện tại",
    "Giáo viên hiện tại",
    "Ngày tháng năm sinh",
    "Tên phụ huynh",
    "Liên lạc của PH (số điện thoại/facebook/zalo/email)",
    "Nhận xét buổi 4",
    "Nhận xét buổi 8",
]

HCM1_HCM4_CENTRES = [
    "HCM - Phan Văn Trị",
    "HCM - 261-263 Phan Xích Long",
    "HCM - 01 Tô Ký",
    "HCM - Khu Tên Lửa",
    "HCM - 322 Tây Thạnh",
    "HCM - 414 Lũy Bán Bích",
    "HCM - 01 Trường Chinh",
]

FIND_CLASS_STUDENT_QUERY = """query FindClassStudent($classId: String) {
  findClassStudent(payload: {classId: $classId}) {
    data {
      id
      classId
      studentId
      activeInClass
      student {
        id
        fullName
        dob
        phoneNumber
        email
        facebook
        zalo
        contactPhoneNumber
        customer {
          fullName
          phoneNumber
          email
          facebook
          zalo
        }
      }
    }
  }
}"""


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_lms_token():
    token = read_token()
    if token:
        info = check_token(token)
        if not info["valid"] or info["remaining_minutes"] <= TOKEN_REFRESH_THRESHOLD:
            refresh_token_silent()
            token = read_token()
    if not token:
        raise RuntimeError("Không có LMS_TOKEN để fetch dữ liệu LMS.")
    return token


def fetch_class_students(class_id, token):
    payload = {
        "operationName": "FindClassStudent",
        "variables": {"classId": class_id},
        "query": FIND_CLASS_STUDENT_QUERY,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    last_error = None
    for attempt in range(5):
        response = requests.post(GRAPHQL_URL, headers=headers, json=payload, timeout=30)
        try:
            data = response.json()
        except Exception:
            data = {}
        if response.status_code == 200 and not data.get("errors"):
            return (((data.get("data") or {}).get("findClassStudent") or {}).get("data") or [])
        message = data.get("errors", [{}])[0].get("message") if isinstance(data, dict) else response.text[:200]
        last_error = message or f"HTTP {response.status_code}"
        if response.status_code == 429:
            time.sleep(4 + attempt * 4)
            continue
        break
    raise RuntimeError(last_error or "Không fetch được học viên")


def parse_dob(value):
    if not value:
        return "", None

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            dt = datetime.strptime(text[:24] if "%f" in fmt else text[:20], fmt)
            return dt.strftime("%d/%m/%Y"), dt.year
        except ValueError:
            pass

    match = re.search(r"\b([A-Z][a-z]{2})\s+(\d{1,2})\s+((?:19|20)\d{2})\b", text)
    if match:
        month_map = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }
        month = month_map.get(match.group(1))
        day = int(match.group(2))
        year = int(match.group(3))
        if month:
            return f"{day:02d}/{month:02d}/{year}", year

    year_match = re.search(r"\b((?:19|20)\d{2})\b", text)
    if year_match:
        return text, int(year_match.group(1))
    return text, None


def clean_comment(value):
    if not value:
        return ""
    text = html.unescape(str(value))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()


def parent_contact(student):
    parent = student.get("customer") or {}
    parts = []
    phone = parent.get("phoneNumber") or student.get("contactPhoneNumber") or student.get("phoneNumber")
    facebook = parent.get("facebook") or student.get("facebook")
    zalo = parent.get("zalo") or student.get("zalo")
    email = parent.get("email") or student.get("email")
    if phone:
        parts.append(f"SĐT: {phone}")
    if facebook:
        parts.append(f"Facebook: {facebook}")
    if zalo:
        parts.append(f"Zalo: {zalo}")
    if email:
        parts.append(f"Email: {email}")
    return "; ".join(parts)


def load_base_rows():
    if not os.path.exists(BASE_CSV):
        return []
    with open(BASE_CSV, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_running_robotics_classes():
    conn = get_db()
    try:
        placeholders = ",".join("?" * len(HCM1_HCM4_CENTRES))
        rows = conn.execute(
            f"""
            SELECT c.id, c.name, c.centre, COALESCE(
                (
                    SELECT group_concat(ct.name, ', ')
                    FROM class_teachers ct
                    WHERE ct.classId = c.id AND ct.role = 'Lecturer'
                ),
                ''
            ) AS teachers
            FROM classes c
            WHERE c.status = 'RUNNING'
              AND c.block = 'Robotics'
              AND c.centre IN ({placeholders})
            ORDER BY c.centre, c.name
            """,
            HCM1_HCM4_CENTRES,
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def load_comments():
    conn = get_db()
    try:
        rows = conn.execute(
            """
            SELECT classId, studentId, sessionIndex, comment
            FROM slot_comments
            WHERE sessionIndex IN (4, 8)
            """
        ).fetchall()
    finally:
        conn.close()

    comments = {}
    for row in rows:
        key = (row["classId"], row["studentId"], row["sessionIndex"])
        comments[key] = clean_comment(row["comment"])
    return comments


def main():
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    base_rows = load_base_rows()
    existing_keys = {
        (row.get("ID học viên", "").strip(), row.get("Lớp hiện tại", "").strip())
        for row in base_rows
    }

    classes = load_running_robotics_classes()
    comments = load_comments()
    token = get_lms_token()
    errors = []
    new_rows = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(fetch_class_students, item["id"], token): item for item in classes}
        for future in as_completed(futures):
            class_item = futures[future]
            try:
                students = future.result()
            except Exception as e:
                errors.append({"classId": class_item["id"], "className": class_item["name"], "error": str(e)})
                continue

            for item in students:
                if not item.get("activeInClass"):
                    continue
                student = item.get("student") or {}
                student_id = item.get("studentId") or student.get("id") or ""
                dob, birth_year = parse_dob(student.get("dob"))
                if birth_year not in (2019, 2020):
                    continue
                row_key = (student_id, class_item["name"])
                if row_key in existing_keys:
                    continue

                new_rows.append(
                    {
                        "ID học viên": student_id,
                        "Tên": student.get("fullName") or "",
                        "Lớp hiện tại": class_item["name"],
                        "Giáo viên hiện tại": class_item.get("teachers") or "",
                        "Ngày tháng năm sinh": dob,
                        "Tên phụ huynh": (student.get("customer") or {}).get("fullName") or "",
                        "Liên lạc của PH (số điện thoại/facebook/zalo/email)": parent_contact(student),
                        "Nhận xét buổi 4": comments.get((class_item["id"], student_id, 4), ""),
                        "Nhận xét buổi 8": comments.get((class_item["id"], student_id, 8), ""),
                    }
                )

    new_rows.sort(key=lambda row: (row["Lớp hiện tại"], row["Tên"]))
    output_rows = base_rows + new_rows

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for row in output_rows:
            writer.writerow({header: row.get(header, "") for header in HEADERS})

    errors_path = os.path.join(EXPORTS_DIR, "hoc_vien_robotics_hcm1_hcm4_6plus_fetch_errors.json")
    with open(errors_path, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

    print(f"base_rows={len(base_rows)}")
    print(f"added_rows={len(new_rows)}")
    print(f"output_rows={len(output_rows)}")
    print(f"errors={len(errors)}")
    print(OUTPUT_CSV)


if __name__ == "__main__":
    main()
