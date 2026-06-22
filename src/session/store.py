"""
SQLite ベースのセッションストア

インメモリから SQLite に変更することで、サーバー再起動後も
セッションデータ（決済状態・レポートパス・LINE user_id）が保持される。

Python 標準の sqlite3 を使用するため追加依存なし。
"""

import sqlite3
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class SessionData:
    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    is_paid: bool = False
    paid_at: Optional[datetime] = None
    stripe_payment_intent_id: Optional[str] = None
    stripe_checkout_session_id: Optional[str] = None
    report_html_path: Optional[str] = None
    report_pdf_path: Optional[str] = None
    archetype_name: Optional[str] = None
    line_user_id: Optional[str] = None


class SessionStore:
    """
    SQLite ベースのセッションストア。

    sqlite3.connect() は接続をスレッドをまたいで使い回せないため、
    呼び出しのたびに接続を開き直す方式（connection-per-call）を採用。
    Railway のような単一プロセス環境では十分なパフォーマンス。
    """

    _COLUMNS = (
        "session_id", "created_at", "is_paid", "paid_at",
        "stripe_payment_intent_id", "stripe_checkout_session_id",
        "report_html_path", "report_pdf_path", "archetype_name", "line_user_id",
    )

    def __init__(self, db_path: str = "voicecode.db", ttl_hours: int = 48):
        self._db_path = db_path
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id                TEXT PRIMARY KEY,
                    created_at                TEXT NOT NULL,
                    is_paid                   INTEGER NOT NULL DEFAULT 0,
                    paid_at                   TEXT,
                    stripe_payment_intent_id  TEXT,
                    stripe_checkout_session_id TEXT,
                    report_html_path          TEXT,
                    report_pdf_path           TEXT,
                    archetype_name            TEXT,
                    line_user_id              TEXT
                )
            """)

    @staticmethod
    def _row_to_session(row: sqlite3.Row) -> SessionData:
        return SessionData(
            session_id=row["session_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            is_paid=bool(row["is_paid"]),
            paid_at=datetime.fromisoformat(row["paid_at"]) if row["paid_at"] else None,
            stripe_payment_intent_id=row["stripe_payment_intent_id"],
            stripe_checkout_session_id=row["stripe_checkout_session_id"],
            report_html_path=row["report_html_path"],
            report_pdf_path=row["report_pdf_path"],
            archetype_name=row["archetype_name"],
            line_user_id=row["line_user_id"],
        )

    def create(self, session_id: str, **kwargs) -> SessionData:
        data = SessionData(session_id=session_id, **kwargs)
        with self._lock, self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions
                    (session_id, created_at, is_paid, paid_at,
                     stripe_payment_intent_id, stripe_checkout_session_id,
                     report_html_path, report_pdf_path, archetype_name, line_user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.session_id,
                data.created_at.isoformat(),
                int(data.is_paid),
                data.paid_at.isoformat() if data.paid_at else None,
                data.stripe_payment_intent_id,
                data.stripe_checkout_session_id,
                data.report_html_path,
                data.report_pdf_path,
                data.archetype_name,
                data.line_user_id,
            ))
        return data

    def get(self, session_id: str) -> Optional[SessionData]:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        data = self._row_to_session(row)
        if datetime.utcnow() - data.created_at > self._ttl:
            self.delete(session_id)
            return None
        return data

    def mark_paid(
        self,
        session_id: str,
        stripe_checkout_session_id: str = "",
        stripe_payment_intent_id: str = "",
    ) -> bool:
        with self._lock, self._connect() as conn:
            result = conn.execute("""
                UPDATE sessions
                SET is_paid = 1, paid_at = ?,
                    stripe_checkout_session_id = ?,
                    stripe_payment_intent_id = ?
                WHERE session_id = ?
            """, (
                datetime.utcnow().isoformat(),
                stripe_checkout_session_id,
                stripe_payment_intent_id,
                session_id,
            ))
            return result.rowcount > 0

    def set_report_paths(self, session_id: str, html_path: str, pdf_path: str) -> bool:
        with self._lock, self._connect() as conn:
            result = conn.execute("""
                UPDATE sessions SET report_html_path = ?, report_pdf_path = ?
                WHERE session_id = ?
            """, (html_path, pdf_path, session_id))
            return result.rowcount > 0

    def is_paid(self, session_id: str) -> bool:
        data = self.get(session_id)
        return data.is_paid if data else False

    def delete(self, session_id: str) -> None:
        with self._lock, self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))

    def cleanup_expired(self) -> int:
        """TTL切れセッションを削除し、削除件数を返す"""
        cutoff = (datetime.utcnow() - self._ttl).isoformat()
        with self._lock, self._connect() as conn:
            result = conn.execute(
                "DELETE FROM sessions WHERE created_at < ?", (cutoff,)
            )
            return result.rowcount

    def get_all(self, limit: int = 200) -> list:
        """管理画面用: 全セッション取得（新しい順）"""
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def count_stats(self) -> dict:
        """管理画面用: 統計情報"""
        with self._lock, self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            paid = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE is_paid = 1"
            ).fetchone()[0]
        return {"total": total, "paid": paid, "free": total - paid}


# ---------------------------------------------------------------------------
# グローバルシングルトン
# ---------------------------------------------------------------------------
_store: Optional[SessionStore] = None


def get_store() -> SessionStore:
    """アプリ全体で共有するストアインスタンスを返す"""
    global _store
    if _store is None:
        try:
            from ..config import BASE_DIR
            db_path = str(BASE_DIR / "voicecode.db")
        except Exception:
            db_path = "voicecode.db"
        _store = SessionStore(db_path=db_path)
    return _store
