"""
音声解析エンジン 実装クラス

科学的根拠:
    - librosa: スペクトル解析・MFCC・RMS・テンポ推定
    - parselmouth (PRAAT): ジッター・シマー・HNR・フォルマント（最高精度）
    - Big5との相関: Mairesse et al.(2007), Schuller et al.(2012)

疎結合設計:
    - IAudioAnalyzerインターフェースを実装
    - 将来的に別のアナライザー（例: openSMILE）に差し替え可能
"""

import logging
from pathlib import Path
from typing import Optional
from datetime import datetime
import time

import numpy as np
import librosa
import parselmouth
from parselmouth.praat import call

from .interfaces import IAudioAnalyzer
from .models import AudioFile, AudioAnalysisResult

logger = logging.getLogger(__name__)


# ========== 参照値（正規化のための基準値） ==========
# 男性・女性の正常域の中央値と標準偏差（科学文献に基づく）
REFERENCE = {
    "male": {
        "f0_mean": 125.0,      # Hz
        "f0_std": 30.0,
        "jitter": 0.5,         # % 正常値上限
        "shimmer": 2.0,        # %
        "hnr": 20.0,           # dB 良好な声の目安
        "rms_energy": 0.05,    # 正規化後の参照値
    },
    "female": {
        "f0_mean": 210.0,      # Hz
        "f0_std": 40.0,
        "jitter": 0.5,
        "shimmer": 2.0,
        "hnr": 20.0,
        "rms_energy": 0.05,
    },
    "unknown": {
        "f0_mean": 160.0,      # 男女の中間値
        "f0_std": 35.0,
        "jitter": 0.5,
        "shimmer": 2.0,
        "hnr": 20.0,
        "rms_energy": 0.05,
    }
}

# PRAAT解析のパラメータ
MIN_PITCH_HZ = 75.0
MAX_PITCH_HZ = 600.0
SILENCE_THRESHOLD = 0.03   # RMSがこれ以下の区間を無音とみなす


class AudioAnalyzer(IAudioAnalyzer):
    """
    音声解析エンジンの実装クラス。

    librosa + parselmouth (PRAAT) を組み合わせて
    Big5予測に必要な全音響特徴量を抽出します。
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Args:
            sample_rate: 解析に使用するサンプリングレート（Hz）
        """
        self._sample_rate = sample_rate
        logger.info(f"AudioAnalyzer 初期化完了 (sample_rate={sample_rate}Hz)")

    def validate_audio(self, audio_file: AudioFile) -> tuple[bool, str]:
        """
        音声ファイルが分析可能な品質かどうかを検証する。

        Returns:
            (True, "") → 検証OK
            (False, "エラーメッセージ") → 検証NG
        """
        if not audio_file.file_path.exists():
            return False, f"音声ファイルが見つかりません: {audio_file.file_path}"

        if audio_file.file_path.stat().st_size < 1000:
            return False, "ファイルサイズが小さすぎます（破損の可能性）"

        try:
            y, sr = librosa.load(str(audio_file.file_path), sr=self._sample_rate, mono=True)
            duration = len(y) / sr

            if duration < 10.0:
                return False, f"音声が短すぎます（{duration:.1f}秒）。15秒以上録音してください。"

            if duration > 300.0:
                return False, f"音声が長すぎます（{duration:.1f}秒）。5分以内で録音してください。"

            # 無音チェック
            rms = np.sqrt(np.mean(y ** 2))
            if rms < 0.001:
                return False, "音声がほぼ無音です。マイクの確認をお願いします。"

        except Exception as e:
            return False, f"音声ファイルの読み込みに失敗しました: {str(e)}"

        return True, ""

    def analyze(self, audio_file: AudioFile) -> AudioAnalysisResult:
        """
        音声ファイルを解析し、全音響特徴量を返す。

        処理フロー:
            1. librosaで音声読み込み
            2. parselmouthでPRAATベースの特徴量抽出
            3. librosaでスペクトル・MFCC特徴量抽出
            4. AudioAnalysisResultにまとめて返す
        """
        start_time = time.time()
        logger.info(f"音声解析開始: session_id={audio_file.session_id}")

        # 検証
        valid, error_msg = self.validate_audio(audio_file)
        if not valid:
            raise ValueError(f"音声検証エラー: {error_msg}")

        # 音声読み込み
        y, sr = librosa.load(
            str(audio_file.file_path),
            sr=self._sample_rate,
            mono=True
        )
        duration = len(y) / sr

        # 結果オブジェクトを初期化
        result = AudioAnalysisResult(
            session_id=audio_file.session_id,
            analysis_duration_sec=duration,
            gender=audio_file.gender,
        )

        # --- PRAAT特徴量の抽出 ---
        try:
            self._extract_praat_features(audio_file.file_path, result, audio_file.gender)
        except Exception as e:
            logger.warning(f"PRAAT特徴量抽出エラー（デフォルト値を使用）: {e}")

        # --- librosa特徴量の抽出 ---
        try:
            self._extract_librosa_features(y, sr, result)
        except Exception as e:
            logger.warning(f"librosa特徴量抽出エラー（デフォルト値を使用）: {e}")

        elapsed = time.time() - start_time
        logger.info(f"音声解析完了: session_id={audio_file.session_id}, 処理時間={elapsed:.2f}秒")

        return result

    def _extract_praat_features(
        self,
        file_path: Path,
        result: AudioAnalysisResult,
        gender: str = "unknown"
    ) -> None:
        """
        parselmouthを使用してPRAATベースの特徴量を抽出する。

        抽出する特徴量:
            - F0（基本周波数）の統計値
            - ジッター（周波数摂動）
            - シマー（振幅摂動）
            - HNR（ハーモニクス対ノイズ比）
            - フォルマント（F1, F2）
        """
        sound = parselmouth.Sound(str(file_path))

        # =========================================
        # F0（基本周波数）の抽出
        # =========================================
        pitch = sound.to_pitch(
            time_step=0.01,
            pitch_floor=MIN_PITCH_HZ,
            pitch_ceiling=MAX_PITCH_HZ
        )
        pitch_values = pitch.selected_array["frequency"]
        voiced_pitches = pitch_values[pitch_values > 0]  # 有声部分のみ

        if len(voiced_pitches) > 0:
            result.f0_mean_hz = float(np.mean(voiced_pitches))
            result.f0_std_hz = float(np.std(voiced_pitches))
            result.f0_max_hz = float(np.max(voiced_pitches))
            result.f0_min_hz = float(np.min(voiced_pitches))

        # =========================================
        # ジッター・シマー・HNRの抽出
        # =========================================
        point_process = call(sound, "To PointProcess (periodic, cc)", MIN_PITCH_HZ, MAX_PITCH_HZ)

        # ジッター（局所的な周波数変動）
        try:
            jitter = call(
                point_process, "Get jitter (local)",
                0, 0, 0.0001, 0.02, 1.3
            )
            result.jitter_local = float(jitter) * 100  # パーセント表示
        except Exception:
            result.jitter_local = 0.5  # デフォルト値

        # シマー（局所的な振幅変動）
        try:
            shimmer = call(
                [sound, point_process], "Get shimmer (local)",
                0, 0, 0.0001, 0.02, 1.3, 1.6
            )
            result.shimmer_local = float(shimmer) * 100  # パーセント表示
        except Exception:
            result.shimmer_local = 2.0  # デフォルト値

        # HNR（調波対雑音比）
        try:
            harmonicity = call(sound, "To Harmonicity (cc)", 0.01, MIN_PITCH_HZ, 0.1, 1.0)
            hnr = call(harmonicity, "Get mean", 0, 0)
            result.hnr_db = float(hnr) if hnr != float("-inf") else 0.0
        except Exception:
            result.hnr_db = 15.0  # デフォルト値（正常範囲の下限）

        # =========================================
        # フォルマント（F1, F2）の抽出
        # 性別によってmax_formantを変更
        # =========================================
        max_formant = 5500.0 if gender == "female" else 5000.0

        try:
            formants = sound.to_formant_burg(
                time_step=0.025,
                max_number_of_formants=5.0,
                maximum_formant=max_formant,
                window_length=0.025,
                pre_emphasis_from=50.0
            )

            # 有声区間のフォルマント値を収集
            f1_values = []
            f2_values = []
            duration = sound.duration

            for t in np.arange(0.025, duration - 0.025, 0.025):
                f1 = formants.get_value_at_time(1, t)
                f2 = formants.get_value_at_time(2, t)
                if f1 and not np.isnan(f1) and f1 > 0:
                    f1_values.append(f1)
                if f2 and not np.isnan(f2) and f2 > 0:
                    f2_values.append(f2)

            if f1_values:
                result.f1_mean_hz = float(np.mean(f1_values))
            if f2_values:
                result.f2_mean_hz = float(np.mean(f2_values))

        except Exception as e:
            logger.warning(f"フォルマント抽出エラー: {e}")

    def _extract_librosa_features(
        self,
        y: np.ndarray,
        sr: int,
        result: AudioAnalysisResult
    ) -> None:
        """
        librosaを使用してスペクトル・エネルギー・テンポ特徴量を抽出する。

        抽出する特徴量:
            - RMSエネルギー（音量）
            - 話速推定
            - テンポ（BPM）
            - 無音区間比率
            - スペクトル重心
            - MFCC 13係数
        """
        # =========================================
        # RMSエネルギー（音量・外向性の最重要指標）
        # =========================================
        frame_length = 2048
        hop_length = 512
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        result.rms_energy = float(np.mean(rms))
        result.rms_std = float(np.std(rms))

        # =========================================
        # 無音区間の検出（ポーズ比率 → 神経症傾向と相関）
        # =========================================
        silent_frames = np.sum(rms < SILENCE_THRESHOLD)
        result.pause_ratio = float(silent_frames / len(rms))

        # =========================================
        # テンポ（リズム解析）
        # =========================================
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        result.tempo_bpm = float(tempo) if not np.isnan(tempo) else 120.0

        # =========================================
        # 話速推定
        # Zero-crossing rateを利用した近似
        # =========================================
        zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]
        # ZCRが高い区間（子音・発話区間）の比率から話速を推定
        speaking_frames = np.sum(zcr > np.percentile(zcr, 20))
        speaking_duration = speaking_frames * hop_length / sr
        # 1秒あたりの話速（仮想的な音節数）を推定
        if speaking_duration > 0:
            result.speech_rate = float(speaking_frames / len(zcr)) * 10  # 0〜10の範囲に正規化
        else:
            result.speech_rate = 4.0  # デフォルト（平均的な話速）

        # =========================================
        # スペクトル重心（声の「明るさ」・覚醒度）
        # =========================================
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        result.spectral_centroid_mean = float(np.mean(spectral_centroid))
        result.spectral_centroid_std = float(np.std(spectral_centroid))

        # =========================================
        # MFCC 13係数（声の質感・声道特性）
        # =========================================
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
        result.mfcc_mean = [float(np.mean(mfcc[i])) for i in range(13)]
        result.mfcc_std = [float(np.std(mfcc[i])) for i in range(13)]
