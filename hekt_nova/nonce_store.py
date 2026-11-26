import hashlib, os, sqlite3, time
from enum import Enum
from typing import Optional

DEFAULT_DB_PATH = os.getenv("HEKT_NONCE_DB", "hekt_nonces.sqlite3")

class ReserveResult(str, Enum):
    RESERVED = "RESERVED"
    DUPLICATE = "DUPLICATE"
    STORE_UNAVAILABLE = "STORE_UNAVAILABLE"

class SqliteNonceStore:
    """Almacén persistente y atómico de nonces anti-replay (SQLite WAL, retención >= 900s, fail-closed)."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH, retention_seconds: int = 900):
        self.db_path = db_path
        self.retention_seconds = max(900, retention_seconds)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS used_nonces (nonce_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_nonces_exp ON used_nonces(expires_at);")
        if self.db_path != ":memory:" and os.path.exists(self.db_path):
            try:
                os.chmod(self.db_path, 0o600)
            except OSError:
                pass

    @staticmethod
    def _key_digest(nonce_key: str) -> str:
        return hashlib.sha256(nonce_key.encode("utf-8")).hexdigest()

    def contains(self, nonce_key: str, now_ts: Optional[int] = None) -> bool:
        now = int(time.time()) if now_ts is None else now_ts
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM used_nonces WHERE nonce_hash = ? AND expires_at > ?;", (self._key_digest(nonce_key), now)).fetchone()
            return row is not None

    def reserve(self, nonce_key: str, now_ts: Optional[int] = None) -> ReserveResult:
        now = int(time.time()) if now_ts is None else now_ts
        exp = now + self.retention_seconds
        conn = None
        try:
            conn = self._connect()
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute("DELETE FROM used_nonces WHERE expires_at <= ?;", (now,))
            cur = conn.execute("INSERT OR IGNORE INTO used_nonces(nonce_hash, expires_at) VALUES (?, ?);", (self._key_digest(nonce_key), exp))
            conn.execute("COMMIT;")
            return ReserveResult.RESERVED if cur.rowcount == 1 else ReserveResult.DUPLICATE
        except Exception:
            if conn is not None:
                try:
                    conn.execute("ROLLBACK;")
                except Exception:
                    pass
            return ReserveResult.STORE_UNAVAILABLE
        finally:
            if conn is not None:
                conn.close()

    def add_if_absent(self, nonce_key: str, now_ts: Optional[int] = None) -> bool:
        return self.reserve(nonce_key, now_ts=now_ts) == ReserveResult.RESERVED
