import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from supabase_cache import write_api_cache, write_classes_summary_cache

CACHE_FILES = {
    "teachers": "teachers.json",
    "tp": "tp.json",
    "cp": "cp.json",
    "oh": "oh.json",
    "assignments": "assignments.json",
}


def load_public_json(filename: str):
    path = ROOT / "public" / filename
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run python main.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload generated public JSON data to Supabase cache.")
    parser.add_argument(
        "--include-full-classes",
        action="store_true",
        help="Also upload public/classes.json with slots. This file can be very large.",
    )
    args = parser.parse_args()

    print("Loading classes_summary from SQLite...", flush=True)
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
        print(f"Uploaded {key}: {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
