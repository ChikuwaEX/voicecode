"""
セッション管理モジュール
インメモリでセッションの状態（診断結果・支払い状態）を管理します。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict
import threading


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
    line_user_id: Optional[str] = None  # LINEから来た場合


class SessionStore:
    """
    インメモリセッションストア。
    将来的にはRedisやSQLiteに置き換え可能。
    """

    def __init__(self, ttl_hours: int = 48):
        self._store: Dict[str, SessionData] = {}
        self._lock = threading.Lock()
        self._ttl = timedelta(hours=ttl_hours)

    def create(self, session_id: str, **kwargs) -> SessionData:
        with self._lock:
            data = SessionData(session_id=session_id, **kwargs)
            self._store[session_id] = data
            return data

    def get(self, session_id: str) -> Optional[SessionData]:
        with self._lock:
            data = self._store.get(session_id)
            if data and datetime.utcnow() - data.created_at > self._ttl:
                del self._store[session_id]
                return None
            return data

    def mark_paid(
        self,
        session_id: str,
        stripe_checkout_session_id: str = "",
        stripe_payment_intent_id: str = "",
    ) -> bool:
        with self._lock:
            data = self._store.get(session_id)
            if not data:
                return False
            data.is_paid = True
            data.paid_at = datetime.utcnow()
            data.stripe_checkout_session_id = stripe_checkout_session_id
            data.stripe_payment_intent_id = stripe_payment_intent_id
            return True

    def set_report_paths(self, session_id: str, html_path: str, pdf_path: str) -> bool:
        with self._lock:
            data = self._store.get(session_id)
            if not data:
                return False
            data.report_html_path = html_path
            data.report_pdf_path = pdf_path
            return True

    def is_paid(self, session_id: str) -> bool:
        data = self.get(session_id)
        return data.is_paid if data else False

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._store.pop(session_id, None)

    def cleanup_expired(self) -> int:
        """期限切れセッションを削除してクリーンアップ"""
        with self._lock:
            expired = [
                sid for sid, data in self._store.items()
                if datetime.utcnow() - data.created_at > self._ttl
            ]
            for sid in expired:
                del self._store[sid]
            return len(expired)


# グローバルシングルトン
_store = SessionStore()

def get_store() -> SessionStore:
    return _store
