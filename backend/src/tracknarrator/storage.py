import os, json, sqlite3, time, threading
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

DB_PATH = os.getenv("TN_DB_PATH", "tracknarrator.db")
_lock = threading.Lock()

def _connect():
    # isolation_level=None -> autocommit off; we will commit explicitly
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def _db():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

def init_db():
    with _db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS sessions(
            session_id TEXT PRIMARY KEY,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            name TEXT,
            bundle_json TEXT NOT NULL
        )""")

def upsert_session(bundle: Dict[str, Any], *, name: Optional[str]=None) -> str:
    sid = bundle.get("session_id") or bundle.get("id") or f"s_{int(time.time()*1000)}"
    now = int(time.time())
    payload = json.dumps(bundle, separators=(",", ":"), ensure_ascii=False)
    with _db() as db:
        db.execute("""
        INSERT INTO sessions(session_id, created_at, updated_at, name, bundle_json)
        VALUES(?,?,?,?,?)
        ON CONFLICT(session_id) DO UPDATE SET
            updated_at=excluded.updated_at,
            name=COALESCE(excluded.name, sessions.name),
            bundle_json=excluded.bundle_json
        """, (sid, now, now, name, payload))
    return sid

def get_session_bundle(session_id: str) -> Optional[Dict[str, Any]]:
    with _db() as db:
        cur = db.execute("SELECT bundle_json FROM sessions WHERE session_id=?", (session_id,))
        row = cur.fetchone()
        if not row: return None
        return json.loads(row["bundle_json"])

def list_sessions(limit: int=50, offset: int=0) -> List[Dict[str, Any]]:
    with _db() as db:
        cur = db.execute("""
        SELECT session_id, created_at, updated_at, name
        FROM sessions
        ORDER BY updated_at DESC
        LIMIT ? OFFSET ?""", (limit, offset))
        return [dict(r) for r in cur.fetchall()]

def delete_session(session_id: str) -> bool:
    with _db() as db:
        cur = db.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
        return cur.rowcount > 0