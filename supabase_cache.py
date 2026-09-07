import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
ENV_PATH = ROOT / ".env"


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


def use_supabase_cache() -> bool:
    return wants_supabase_cache() and bool(get_database_url())


def wants_supabase_cache() -> bool:
    flag = get_env_value("USE_SUPABASE", "0").lower()
    is_vercel = bool(os.getenv("VERCEL")) or bool(os.getenv("VERCEL_ENV"))
    return flag in {"1", "true", "yes", "on"} or is_vercel


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
