"""
PDFレポート生成エンジン インターフェース定義
"""

from abc import ABC, abstractmethod
from ..diagnosis.models import DiagnosisResult
from .models import PDFReport


class IReportGenerator(ABC):
    """
    PDFレポート生成エンジンのインターフェース。
    """

    @abstractmethod
    def generate(self, diagnosis: DiagnosisResult, user_name: str) -> PDFReport:
        """
        診断結果からPDFレポートを生成する。

        Args:
            diagnosis: 診断結果
            user_name: レポートに記載するユーザー名

        Returns:
            PDFReport: 生成されたPDFファイルの情報
        """
        ...
