"""
音声解析エンジン インターフェース定義

疎結合設計の核心:
    - 上位モジュールはこのインターフェースにのみ依存する
    - 実装（analyzer.py）はいつでも差し替え可能
    - テスト時はモック実装で代替可能
"""

from abc import ABC, abstractmethod
from .models import AudioFile, AudioAnalysisResult


class IAudioAnalyzer(ABC):
    """
    音声解析エンジンのインターフェース。

    すべての音声解析実装はこのインターフェースを実装しなければならない。
    依存性逆転の原則（DIP）を実現するための抽象クラス。
    """

    @abstractmethod
    def analyze(self, audio_file: AudioFile) -> AudioAnalysisResult:
        """
        音声ファイルを解析し、音響特徴量を返す。

        Args:
            audio_file: 分析対象の音声ファイル情報

        Returns:
            AudioAnalysisResult: 抽出された音響特徴量

        Raises:
            ValueError: 音声ファイルが無効な場合
            RuntimeError: 解析処理中にエラーが発生した場合
        """
        ...

    @abstractmethod
    def validate_audio(self, audio_file: AudioFile) -> tuple[bool, str]:
        """
        音声ファイルが分析可能な品質かどうかを検証する。

        Args:
            audio_file: 検証対象の音声ファイル情報

        Returns:
            tuple[bool, str]: (検証結果, エラーメッセージ or 空文字)
        """
        ...
