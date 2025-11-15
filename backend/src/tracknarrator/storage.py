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
        db.execute("""
        CREATE TABLE IF NOT EXISTS shares(
            jti TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            label TEXT,
            exp_ts INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        db.execute("""
        CREATE TABLE IF NOT EXISTS revocations(
            jti TEXT PRIMARY KEY,
            revoked_at INTEGER NOT NULL
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

def add_share(jti: str, session_id: str, exp_ts: int, *, label: str|None=None) -> None:
    now = int(time.time())
    with _db() as db:
        db.execute("INSERT OR REPLACE INTO shares(jti, session_id, label, exp_ts, created_at) VALUES(?,?,?,?,?)",
                   (jti, session_id, label, exp_ts, now))

def list_shares(session_id: str|None=None) -> List[Dict[str, Any]]:
    now = int(time.time())
    q = """
        SELECT s.jti, s.session_id, s.label, s.exp_ts, s.created_at
        FROM shares s
        LEFT JOIN revocations r ON s.jti = r.jti
        WHERE r.jti IS NULL AND s.exp_ts > ?
    """
    args = [now]
    if session_id:
        q += " AND s.session_id=?"; args.append(session_id)
    q += " ORDER BY s.created_at DESC"
    with _db() as db:
        cur = db.execute(q, tuple(args))
        return [dict(r) for r in cur.fetchall()]

def revoke_share(jti: str) -> bool:
    now = int(time.time())
    with _db() as db:
        db.execute("INSERT OR REPLACE INTO revocations(jti, revoked_at) VALUES(?,?)", (jti, now))
        db.execute("DELETE FROM shares WHERE jti=?", (jti,))
        return True

def is_revoked(jti: str) -> bool:
    with _db() as db:
        cur = db.execute("SELECT 1 FROM revocations WHERE jti=? LIMIT 1", (jti,))
        return cur.fetchone() is not None