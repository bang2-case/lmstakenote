"""
Import data từ JSON files hiện có vào SQLite database.
Chạy: python scripts/import_json_to_db.py
"""
import os, json, sqlite3

ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "classroom_data.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def load_json(path):
    if not os.path.exists(path):
        print(f"  ⚠ Không tìm thấy: {path}")
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def import_classes(data):
    conn = get_conn()
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
            c.execute("DELETE FROM class_teachers WHERE classId=?", (cid,))
            for t in item.get("teachers", []):
                c.execute("INSERT INTO class_teachers (classId, name, email, role) VALUES (?,?,?,?)",
                          (cid, t.get("name"), t.get("email"), t.get("role")))
            c.execute("DELETE FROM slots WHERE classId=?", (cid,))
            for s in item.get("slots", []):
                c.execute("""INSERT OR REPLACE INTO slots
                    (id, classId, date, startTime, endTime, commentStatus, studentsInSlot, studentsWithComment)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (s.get("id"), cid, s.get("date"), s.get("startTime"), s.get("endTime"),
                     s.get("commentStatus"), s.get("studentsInSlot", 0), s.get("studentsWithComment", 0)))
            c.execute("DELETE FROM incomplete_students WHERE classId=?", (cid,))
            for name in item.get("incompleteStudents", []):
                c.execute("INSERT INTO incomplete_students (classId, name) VALUES (?,?)", (cid, name))
        conn.commit()
        print(f"  ✅ {len(data)} lớp → SQLite")
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Lỗi classes: {e}")
    finally:
        conn.close()


def import_teachers(data):
    conn = get_conn()
    c = conn.cursor()
    try:
        for t in data:
            tid = t["id"]
            c.execute("""INSERT OR REPLACE INTO teachers
                (id, fullName, code, username, email, personalEmail, phoneNumber,
                 gender, dob, address, isActive, teacherPoint, joinedDate)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (tid, t.get("fullName"), t.get("code"), t.get("username"),
                 t.get("email"), t.get("personalEmail"), t.get("phoneNumber"),
                 t.get("gender"), t.get("dob"), t.get("address"),
                 1 if t.get("isActive") else 0, t.get("teacherPoint", 0), t.get("joinedDate")))
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
        print(f"  ✅ {len(data)} giáo viên → SQLite")
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Lỗi teachers: {e}")
    finally:
        conn.close()


def import_tp(data):
    conn = get_conn()
    c = conn.cursor()
    try:
        for r in data:
            cid = r["classId"]
            c.execute("""INSERT OR REPLACE INTO tp_records
                (classId, className, centre, block, tp1, tp2) VALUES (?,?,?,?,?,?)""",
                (cid, r.get("className"), r.get("centre"), r.get("block"), r.get("tp1"), r.get("tp2")))
            c.execute("DELETE FROM tp_students WHERE classId=?", (cid,))
            for s in r.get("tp1_students", []):
                c.execute("INSERT INTO tp_students (classId, round, name, score, textAnswers) VALUES (?,?,?,?,?)",
                          (cid, 1, s.get("name"), s.get("score"),
                           json.dumps(s.get("textAnswers", []), ensure_ascii=False)))
            for s in r.get("tp2_students", []):
                c.execute("INSERT INTO tp_students (classId, round, name, score, textAnswers) VALUES (?,?,?,?,?)",
                          (cid, 2, s.get("name"), s.get("score"),
                           json.dumps(s.get("textAnswers", []), ensure_ascii=False)))
            c.execute("DELETE FROM tp_teachers WHERE classId=?", (cid,))
            for t in r.get("teachers", []):
                c.execute("INSERT INTO tp_teachers (classId, name, email, role) VALUES (?,?,?,?)",
                          (cid, t.get("name"), t.get("email"), t.get("role")))
        conn.commit()
        print(f"  ✅ {len(data)} TP records → SQLite")
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Lỗi tp: {e}")
    finally:
        conn.close()


print("📦 Importing JSON → SQLite...")

classes = load_json(os.path.join(ROOT, "public", "classes.json"))
if classes:
    print(f"  classes.json: {len(classes)} lớp")
    import_classes(classes)

teachers = load_json(os.path.join(ROOT, "public", "teachers.json"))
if teachers:
    print(f"  teachers.json: {len(teachers)} giáo viên")
    import_teachers(teachers)

tp = load_json(os.path.join(ROOT, "public", "tp.json"))
if tp:
    print(f"  tp.json: {len(tp)} TP records")
    import_tp(tp)

print("\n✅ Import xong!")
