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
from datetime import datetime, timezone
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# UTF-8 JSON response to fix Vietnamese encoding
class UTF8JSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(content, ensure_ascii=False).encode("utf-8")

app = FastAPI(title="LMS TakeNote API", default_response_class=UTF8JSONResponse)

# ─────────────────────────────────────────────────────────────────────────────
DB_PATH   = os.path.join(os.path.dirname(__file__), "classroom_data.db")
ENV_PATH  = os.path.join(os.path.dirname(__file__), ".env")
FETCH_INTERVAL_HOURS = 3

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


# ─────────────────────────────────────────────────────────────────────────────
# Token helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_token() -> str | None:
    if not os.path.exists(ENV_PATH):
        return None
    with open(ENV_PATH, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if line.startswith("LMS_TOKEN="):
                return line[len("LMS_TOKEN="):].strip().strip('"').strip("'") or None
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
        # Kiểm tra token trước khi chạy
        token = read_token()
        if token:
            token_info = check_token(token)
            if not token_info["valid"]:
                fetch_state["last_status"] = "error"
                fetch_state["last_message"] = "Token đã hết hạn — vui lòng cập nhật token mới"
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
            # Token hết hạn (exit code 2)
            fetch_state["last_status"] = "error"
            fetch_state["last_message"] = "Token đã hết hạn — vui lòng cập nhật token mới"
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
    asyncio.create_task(scheduler())
    print(f"🚀 LMS TakeNote API running")
    print(f"   Auto-fetch every {FETCH_INTERVAL_HOURS}h")
    print(f"   WebSocket: ws://localhost:8000/ws")


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    # Send current state on connect
    await ws.send_json({
        "type": "state",
        "fetch_state": fetch_state,
        "token": check_token(read_token() or ""),
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
    if not token:
        return {"valid": False, "message": "Không tìm thấy token trong .env"}
    info = check_token(token)
    return {**info, "message": f"Còn {info['remaining_minutes']} phút" if info["valid"] else "Token đã hết hạn"}


@app.post("/api/refresh")
async def manual_refresh(background_tasks: BackgroundTasks):
    """Trigger manual fetch."""
    if fetch_state["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Đang fetch, vui lòng chờ..."})
    loop = asyncio.get_event_loop()
    asyncio.create_task(run_fetch(loop))
    return {"ok": True, "message": "Đã bắt đầu fetch dữ liệu..."}


@app.post("/api/cancel")
async def cancel_fetch():
    """Cancel đang fetch."""
    global _fetch_process
    if not fetch_state["is_fetching"]:
        return JSONResponse({"ok": False, "message": "Không có quá trình fetch nào đang chạy."})
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


@app.get("/api/fetch-status")
def fetch_status():
    return fetch_state


@app.get("/api/fetch-log")
def fetch_log():
    """Return full log from last fetch run for debugging."""
    return {"log": fetch_state.get("last_log", ""), "status": fetch_state["last_status"]}


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
    if not date:
        return JSONResponse({"error": "Thiếu tham số date"}, status_code=400)
    try:
        from fetch_demo import fetch_demo_classes, export_to_sheet
        loop = asyncio.get_event_loop()
        classes = await loop.run_in_executor(None, lambda: fetch_demo_classes(date, date_to))
        result = await loop.run_in_executor(None, lambda: export_to_sheet(classes, date, date_to))
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.get("/api/classes")
def get_classes():
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

    for c in classes:
        cid = c["id"]
        c["teachers"] = teachers_map.get(cid, [])
        c["slots"] = slots_map.get(cid, [])
        c["incompleteStudents"] = incomplete_map.get(cid, [])

    return classes


@app.get("/api/teachers")
def get_teachers():
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
    uvicorn.run("server:app", host="localhost", port=8000, reload=False)
