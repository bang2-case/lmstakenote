"""
LMS TakeNote — Local API Server (Python stdlib, không cần cài thêm gì)
Chạy: python server.py
Port: 8000
"""
import sqlite3
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

DB_PATH = os.path.join(os.path.dirname(__file__), "classroom_data.db")
PORT = 8000


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


# ── Route handlers ────────────────────────────────────────────────────────────

def handle_classes(qs: dict) -> list:
    """GET /api/classes — trả về danh sách lớp với teachers và slots."""
    # Build WHERE clause từ query params
    conditions = []
    params = []

    if qs.get("centre"):
        conditions.append("c.centre = ?")
        params.append(qs["centre"][0])
    if qs.get("status"):
        conditions.append("c.status = ?")
        params.append(qs["status"][0])
    if qs.get("block"):
        conditions.append("c.block = ?")
        params.append(qs["block"][0])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    classes = query(f"""
        SELECT c.id, c.name, c.status, c.course, c.centre, c.block, c.level,
               c.sessions, c.studentCount, c.attendedCount, c.completedCount,
               c.completionRate, c.commentPercentage, c.totalSlotsWithStudents,
               c.slotsWithFullComments, c.startDate, c.endDate, c.createdAt
        FROM classes c
        {where}
        ORDER BY c.createdAt DESC
    """, tuple(params))

    if not classes:
        return []

    # Batch load teachers and slots
    ids = [c["id"] for c in classes]
    placeholders = ",".join("?" * len(ids))

    teachers_rows = query(
        f"SELECT classId, name, email, role FROM class_teachers WHERE classId IN ({placeholders})",
        tuple(ids)
    )
    slots_rows = query(
        f"""SELECT classId, id, date, startTime, endTime, commentStatus,
                   studentsInSlot, studentsWithComment
            FROM slots WHERE classId IN ({placeholders}) ORDER BY date""",
        tuple(ids)
    )
    incomplete_rows = query(
        f"SELECT classId, name FROM incomplete_students WHERE classId IN ({placeholders})",
        tuple(ids)
    )

    # Group by classId
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

    incomplete_map: dict[str, list] = {}
    for r in incomplete_rows:
        incomplete_map.setdefault(r["classId"], []).append(r["name"])

    # Assemble
    for c in classes:
        cid = c["id"]
        c["teachers"] = teachers_map.get(cid, [])
        c["slots"] = slots_map.get(cid, [])
        c["incompleteStudents"] = incomplete_map.get(cid, [])

    return classes


def handle_teachers(qs: dict) -> list:
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


def handle_tp(qs: dict) -> list:
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


ROUTES = {
    "/api/classes":  handle_classes,
    "/api/teachers": handle_teachers,
    "/api/tp":       handle_tp,
}


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        if path not in ROUTES:
            self.send_json({"error": "Not found"}, 404)
            return

        if not os.path.exists(DB_PATH):
            self.send_json({"error": "Database not found. Run python main.py first."}, 503)
            return

        try:
            data = ROUTES[path](qs)
            self.send_json(data)
        except Exception as e:
            self.send_json({"error": str(e)}, 500)


if __name__ == "__main__":
    print(f"🚀 API Server running at http://localhost:{PORT}")
    print(f"   Endpoints: /api/classes  /api/teachers  /api/tp")
    print(f"   DB: {DB_PATH}")
    httpd = HTTPServer(("localhost", PORT), Handler)
    httpd.serve_forever()
