"""
LINE メッセージングサービス インターフェース定義
"""

from abc import ABC, abstractmethod
from ..report.models import PDFReport


class ILineMessagingService(ABC):
    """
    LINE Messaging APIのインターフェース。
    """

    @abstractmethod
    def send_pdf(self, user_line_id: str, report: PDFReport) -> bool:
        """
        指定ユーザーのLINEにPDFを送付する。

        Args:
            user_line_id: LINE UserID
            report: 送付するPDFレポート

        Returns:
            bool: 送信成功かどうか
        """
        ...

    @abstractmethod
    def send_message(self, user_line_id: str, message: str) -> bool:
        """
        指定ユーザーのLINEにテキストメッセージを送る。

        Args:
            user_line_id: LINE UserID
            message: 送信するテキスト

        Returns:
            bool: 送信成功かどうか
        """
        ...

    @abstractmethod
    def send_recording_page_url(self, user_line_id: str, session_id: str) -> bool:
        """
        決済完了後に録音ページURLをLINEで送付する。

        Args:
            user_line_id: LINE UserID
            session_id: セッションID（録音URLに含める）

        Returns:
            bool: 送信成功かどうか
        """
        ...
