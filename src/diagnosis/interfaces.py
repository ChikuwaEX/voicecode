"""
診断エンジン インターフェース定義
"""

from abc import ABC, abstractmethod
from ..audio.models import AudioAnalysisResult
from .models import DiagnosisResult


class IDiagnosisEngine(ABC):
    """
    診断エンジンのインターフェース。

    音声解析結果 → Big5スコア → スピリチュアル表現 の変換を担当。
    世界観（YAMLテーマ）は外部から注入される。
    """

    @abstractmethod
    def diagnose(self, analysis: AudioAnalysisResult) -> DiagnosisResult:
        """
        音声解析結果から診断結果を生成する。

        Args:
            analysis: 音声解析結果（AudioAnalysisResult）

        Returns:
            DiagnosisResult: 完全な診断結果
        """
        ...

    @abstractmethod
    def set_worldview_theme(self, theme_name: str) -> None:
        """
        使用する世界観テーマを切り替える。

        Args:
            theme_name: YAMLテーマ名（例: 'elements_v1'）
        """
        ...
