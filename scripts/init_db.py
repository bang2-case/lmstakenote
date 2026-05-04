"""
Khởi tạo SQLite database với schema đầy đủ cho LMS TakeNote.
Chạy: python scripts/init_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "classroom_data.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── Classes ──────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS classes (
        id              TEXT PRIMARY KEY,
        name            TEXT NOT NULL,
        status          TEXT,
        course          TEXT,
        centre          TEXT,
        block           TEXT,
        level           TEXT,
        sessions        INTEGER,
        studentCount    INTEGER DEFAULT 0,
        attendedCount   INTEGER DEFAULT 0,
        completedCount  INTEGER DEFAULT 0,
        completionRate  INTEGER DEFAULT 0,
        commentPercentage INTEGER DEFAULT 0,
        totalSlotsWithStudents INTEGER DEFAULT 0,
        slotsWithFullComments  INTEGER DEFAULT 0,
        startDate       TEXT,
        endDate         TEXT,
        createdAt       TEXT,
        updatedAt       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # ── Teachers per class ───────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS class_teachers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        classId     TEXT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        name        TEXT,
        email       TEXT,
        role        TEXT
    )
    """)

    # ── Slots ────────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS slots (
        id                  TEXT PRIMARY KEY,
        classId             TEXT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        date                TEXT,
        startTime           TEXT,
        endTime             TEXT,
        commentStatus       TEXT,
        studentsInSlot      INTEGER DEFAULT 0,
        studentsWithComment INTEGER DEFAULT 0
    )
    """)

    # ── Incomplete students (CR) ─────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS incomplete_students (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        classId     TEXT NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
        name        TEXT
    )
    """)

    # ── Teachers ─────────────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id              TEXT PRIMARY KEY,
        fullName        TEXT,
        code            TEXT,
        username        TEXT,
        email           TEXT,
        personalEmail   TEXT,
        phoneNumber     TEXT,
        gender          TEXT,
        dob             TEXT,
        address         TEXT,
        isActive        INTEGER DEFAULT 1,
        teacherPoint    REAL DEFAULT 0,
        joinedDate      TEXT,
        updatedAt       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS teacher_centres (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        teacherId   TEXT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
        centre      TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS teacher_blocks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        teacherId   TEXT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
        block       TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS teacher_course_lines (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        teacherId   TEXT NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
        courseLine  TEXT
    )
    """)

    # ── TP (Teacher Point) ───────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS tp_records (
        classId     TEXT PRIMARY KEY REFERENCES classes(id) ON DELETE CASCADE,
        className   TEXT,
        centre      TEXT,
        block       TEXT,
        tp1         REAL,
        tp2         REAL,
        updatedAt   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tp_students (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        classId     TEXT NOT NULL REFERENCES tp_records(classId) ON DELETE CASCADE,
        round       INTEGER NOT NULL,   -- 1 = TP1, 2 = TP2
        name        TEXT,
        score       REAL,
        textAnswers TEXT               -- JSON array of {questionId, value}
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS tp_teachers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        classId     TEXT NOT NULL REFERENCES tp_records(classId) ON DELETE CASCADE,
        name        TEXT,
        email       TEXT,
        role        TEXT
    )
    """)

    # ── CP (Checkpoint) ──────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS cp_records (
        classId         TEXT PRIMARY KEY REFERENCES classes(id) ON DELETE CASCADE,
        className       TEXT,
        centre          TEXT,
        block           TEXT,
        cp1Theory       REAL,
        cp1Practical    REAL,
        cp2Theory       REAL,
        cp2Practical    REAL,
        updatedAt       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS cp_students (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        classId         TEXT NOT NULL REFERENCES cp_records(classId) ON DELETE CASCADE,
        round           INTEGER NOT NULL,   -- 1 = CP1, 2 = CP2
        name            TEXT,
        theoryScore     REAL,
        practicalScore  REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS cp_teachers (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        classId     TEXT NOT NULL REFERENCES cp_records(classId) ON DELETE CASCADE,
        name        TEXT,
        email       TEXT,
        role        TEXT
    )
    """)

    # ── OH (Office Hours) ────────────────────────────────────────────────────
    c.execute("""
    CREATE TABLE IF NOT EXISTS oh_records (
        id              TEXT PRIMARY KEY,
        startTime       TEXT,
        endTime         TEXT,
        status          TEXT,
        centreId        TEXT,
        centreName      TEXT,
        centreShortName TEXT,
        teacherId       TEXT,
        teacherFullName TEXT,
        teacherUsername TEXT,
        teacherEmail    TEXT,
        note            TEXT,
        managerNote     TEXT,
        type            TEXT,
        studentCount    INTEGER DEFAULT 0,
        createdByUsername TEXT,
        createdAt       TEXT,
        updatedAt       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS oh_courses (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        ohId        TEXT NOT NULL REFERENCES oh_records(id) ON DELETE CASCADE,
        courseId    TEXT,
        courseName  TEXT,
        shortName   TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS oh_course_lines (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        ohId            TEXT NOT NULL REFERENCES oh_records(id) ON DELETE CASCADE,
        courseLineId    TEXT,
        courseLineName  TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS oh_appointments (
        id              TEXT PRIMARY KEY,
        ohId            TEXT NOT NULL REFERENCES oh_records(id) ON DELETE CASCADE,
        title           TEXT,
        candidateId     TEXT,
        candidateName   TEXT,
        status          TEXT,
        note            TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS oh_appointment_courses (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        appointmentId   TEXT NOT NULL REFERENCES oh_appointments(id) ON DELETE CASCADE,
        courseId        TEXT,
        courseName      TEXT,
        shortName       TEXT
    )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_oh_centre    ON oh_records(centreId)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_oh_startTime ON oh_records(startTime)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_oh_appt_ohId ON oh_appointments(ohId)")

    # ── Indexes ──────────────────────────────────────────────────────────────
    c.execute("CREATE INDEX IF NOT EXISTS idx_classes_status  ON classes(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_classes_centre  ON classes(centre)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_classes_block   ON classes(block)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_slots_classId   ON slots(classId)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_tp_centre       ON tp_records(centre)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cp_centre       ON cp_records(centre)")

    conn.commit()
    conn.close()
    print(f"✅ Database khởi tạo thành công: {os.path.abspath(DB_PATH)}")
    print("   Mở bằng DB Browser for SQLite để xem cấu trúc.")


if __name__ == "__main__":
    init_db()
