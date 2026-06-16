"""
音声解析 データモデル定義

疎結合設計：このモジュールは他のモジュールに依存しません。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class AudioFile:
    """
    分析対象の音声ファイルを表すデータクラス。

    Attributes:
        file_path: 音声ファイルの絶対パス
        format: ファイル形式 (wav, mp3, m4a, webm等)
        session_id: この音声に対応するセッションID
        duration_sec: 音声の長さ（秒）
        sample_rate: サンプリングレート（Hz）
        gender: 性別 ('male' / 'female' / 'unknown') - F0正規化に使用
    """
    file_path: Path
    format: str
    session_id: str
    duration_sec: float = 0.0
    sample_rate: int = 16000
    gender: str = "unknown"

    def __post_init__(self):
        """パスをPathオブジェクトに変換"""
        self.file_path = Path(self.file_path)


@dataclass
class AudioAnalysisResult:
    """
    音声解析の結果を格納するデータクラス。

    科学的根拠:
        - F0関連: Mairesse et al.(2007), Scherer(2003)
        - Jitter/Shimmer: 声帯振動安定性の指標
        - HNR: 声のクリアさ・心理的健康状態の指標
        - RMS: 外向性と最も相関が高い音声特徴量
    """
    session_id: str

    # 基本周波数（ピッチ）
    f0_mean_hz: float = 0.0        # F0平均値
    f0_std_hz: float = 0.0         # F0標準偏差（ピッチ変動）
    f0_max_hz: float = 0.0         # F0最大値
    f0_min_hz: float = 0.0         # F0最小値

    # 声の質指標
    jitter_local: float = 0.0      # ジッター（周波数摂動）%
    shimmer_local: float = 0.0     # シマー（振幅摂動）%
    hnr_db: float = 0.0            # ハーモニクス対ノイズ比 dB

    # エネルギー・音量
    rms_energy: float = 0.0        # RMSエネルギー（音量）
    rms_std: float = 0.0           # RMSの変動（ダイナミックレンジ）

    # リズム・テンポ
    speech_rate: float = 0.0       # 推定話速（音節/秒の近似値）
    tempo_bpm: float = 0.0         # テンポ（BPM）
    pause_ratio: float = 0.0       # 無音区間の割合（0〜1）

    # スペクトル特性
    spectral_centroid_mean: float = 0.0   # スペクトル重心平均
    spectral_centroid_std: float = 0.0    # スペクトル重心変動

    # MFCC（声道特性）
    mfcc_mean: list = field(default_factory=lambda: [0.0] * 13)
    mfcc_std: list = field(default_factory=lambda: [0.0] * 13)

    # フォルマント（パスルマウスで取得）
    f1_mean_hz: float = 0.0        # 第1フォルマント
    f2_mean_hz: float = 0.0        # 第2フォルマント

    # メタデータ
    analyzed_at: datetime = field(default_factory=datetime.now)
    analysis_duration_sec: float = 0.0  # 分析に使用した音声の実際の長さ
    gender: str = "unknown"             # 性別補正のため保持

    def to_dict(self) -> dict:
        """辞書形式に変換（APIレスポンス・ログ用）"""
        return {
            "session_id": self.session_id,
            "f0_mean_hz": round(self.f0_mean_hz, 2),
            "f0_std_hz": round(self.f0_std_hz, 2),
            "f0_max_hz": round(self.f0_max_hz, 2),
            "f0_min_hz": round(self.f0_min_hz, 2),
            "jitter_local": round(self.jitter_local, 4),
            "shimmer_local": round(self.shimmer_local, 4),
            "hnr_db": round(self.hnr_db, 2),
            "rms_energy": round(self.rms_energy, 4),
            "rms_std": round(self.rms_std, 4),
            "speech_rate": round(self.speech_rate, 2),
            "tempo_bpm": round(self.tempo_bpm, 2),
            "pause_ratio": round(self.pause_ratio, 3),
            "spectral_centroid_mean": round(self.spectral_centroid_mean, 2),
            "spectral_centroid_std": round(self.spectral_centroid_std, 2),
            "f1_mean_hz": round(self.f1_mean_hz, 2),
            "f2_mean_hz": round(self.f2_mean_hz, 2),
            "gender": self.gender,
            "analyzed_at": self.analyzed_at.isoformat(),
        }
