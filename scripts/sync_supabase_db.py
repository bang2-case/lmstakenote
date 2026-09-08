import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from supabase_cache import sync_sqlite_to_supabase, write_api_cache, write_classes_summary_cache

CACHE_FILES = {
    "teachers": "teachers.json",
    "tp": "tp.json",
    "cp": "cp.json",
    "oh": "oh.json",
    "assignments": "assignments.json",
}

REQUIRED_SQLITE_TABLES = ["classes", "teachers", "oh_records"]


def load_public_json(filename: str):
    path = ROOT / "public" / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run python main.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_sqlite_source(db_path: Path) -> None:
    if not db_path.exists():
        raise FileNotFoundError(f"Missing {db_path}. Run python main.py first.")

    conn = sqlite3.connect(db_path)
    try:
        missing = []
        empty = []
        for table in REQUIRED_SQLITE_TABLES:
            exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table,),
            ).fetchone()
            if not exists:
                missing.append(table)
                continue
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if count <= 0:
                empty.append(table)
        if missing or empty:
            details = []
            if missing:
                details.append(f"missing tables: {', '.join(missing)}")
            if empty:
                details.append(f"empty tables: {', '.join(empty)}")
            raise RuntimeError(
                "SQLite source is incomplete after python main.py; "
                + "; ".join(details)
                + ". Check the Fetch data from LMS log above."
            )
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload generated LMS data to Supabase tables and fallback cache.")
    parser.add_argument(
        "--include-full-classes",
        action="store_true",
        help="Also upload public/classes.json with slots. This file can be very large.",
    )
    parser.add_argument(
        "--with-fallback-cache",
        action="store_true",
        help="Also upload the old JSON cache tables. The deployed app reads relational tables first.",
    )
    args = parser.parse_args()

    db_path = ROOT / "classroom_data.db"
    validate_sqlite_source(db_path)
    print("Uploading relational LMS tables to Supabase...", flush=True)
    counts = sync_sqlite_to_supabase(
        db_path,
        progress=lambda table, total: print(f"  {table}: {total}", flush=True),
    )
    synced_tables = sum(1 for count in counts.values() if count > 0)
    synced_rows = sum(counts.values())
    print(f"Uploaded relational tables: {synced_rows} rows across {synced_tables} tables", flush=True)

    if not args.with_fallback_cache:
        return 0

    print("Loading classes_summary from SQLite for fallback cache...", flush=True)
    os.environ["USE_SUPABASE"] = "0"
    from server import get_classes

    class_summary = get_classes(include_slots=False)
    if not isinstance(class_summary, list):
        raise RuntimeError("Cannot load class summary from SQLite.")
    print(f"Uploading classes_summary: {len(class_summary)} classes", flush=True)
    write_classes_summary_cache(
        class_summary,
        progress=lambda done, total: print(f"  classes_summary {done}/{total}", flush=True),
    )
    print(f"Uploaded classes_summary: {len(class_summary)} classes")

    if args.include_full_classes:
        print("Loading full public/classes.json...", flush=True)
        classes = load_public_json("classes.json")
        write_api_cache("classes", classes)
        print(f"Uploaded classes: {len(classes)} classes with slots")

    for key, filename in CACHE_FILES.items():
        payload = load_public_json(filename)
        write_api_cache(key, payload)
        count = len(payload) if isinstance(payload, list) else "object"
        print(f"Uploaded fallback {key}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
