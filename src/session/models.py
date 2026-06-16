"""
セッション データモデル定義

診断フローの状態管理（決済→録音→処理→完了）を担当します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SessionStatus(str, Enum):
    """
    診断セッションのステータス一覧。

    CREATED         → セッション作成直後
    PAYMENT_PENDING → 決済待ち
    PAID            → 決済完了
    RECORDING_URL_SENT → 録音URLをLINEで送付済み
    RECORDING_COMPLETE → 音声アップロード完了
    PROCESSING      → 音声解析・診断処理中
    REPORT_READY    → PDF生成完了
    COMPLETED       → LINE送付完了・全工程終了
    ERROR           → エラー発生
    CANCELLED       → キャンセル
    """
    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAID = "PAID"
    RECORDING_URL_SENT = "RECORDING_URL_SENT"
    RECORDING_COMPLETE = "RECORDING_COMPLETE"
    PROCESSING = "PROCESSING"
    REPORT_READY = "REPORT_READY"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"


@dataclass
class DiagnosisSession:
    """
    診断セッションのデータクラス。

    ユーザーの診断フロー全体の状態を管理します。
    決済完了〜診断完了まですべてのステータスを追跡します。
    """
    session_id: str
    status: SessionStatus = SessionStatus.CREATED

    # ユーザー情報
    user_line_id: str = ""
    user_name: str = "ゲスト"
    gender: str = "unknown"

    # 決済情報
    payment_amount_yen: int = 0
    payment_intent_id: str = ""
    paid_at: Optional[datetime] = None

    # 音声情報
    audio_file_path: str = ""
    audio_uploaded_at: Optional[datetime] = None

    # 診断結果
    diagnosis_result_json: str = ""
    report_file_path: str = ""
    report_sent_at: Optional[datetime] = None

    # エラー情報
    error_message: str = ""

    # タイムスタンプ
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def update_status(self, new_status: SessionStatus, error_msg: str = "") -> None:
        """ステータスを更新し、updated_atを記録する"""
        self.status = new_status
        self.updated_at = datetime.now()
        if error_msg:
            self.error_message = error_msg

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status.value,
            "user_name": self.user_name,
            "gender": self.gender,
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
