"""
声紋言霊リーディング データモデル定義

Big5パーソナリティ理論に基づいたリーディング結果を格納します。
声→周波数→色→命名のフローを反映した構造。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Big5Score:
    """
    Big Fiveパーソナリティスコア（0.0〜1.0）

    Scientific basis: Mairesse et al.(2007), Schuller et al.(2012)

    Attributes:
        openness: 開放性 - 好奇心・創造性・感受性
        conscientiousness: 誠実性 - 計画性・自律性・責任感
        extraversion: 外向性 - 社交性・活発さ・エネルギー放出
        agreeableness: 協調性 - 共感力・優しさ・調和
        neuroticism: 神経症傾向 - 感情の波・繊細さ・不安定性
    """
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5

    def __post_init__(self):
        """スコアを0.0〜1.0の範囲にクランプ"""
        self.openness = max(0.0, min(1.0, self.openness))
        self.conscientiousness = max(0.0, min(1.0, self.conscientiousness))
        self.extraversion = max(0.0, min(1.0, self.extraversion))
        self.agreeableness = max(0.0, min(1.0, self.agreeableness))
        self.neuroticism = max(0.0, min(1.0, self.neuroticism))

    def get_level(self, score: float) -> str:
        """スコアをレベル（high/mid/low）に変換"""
        if score >= 0.6:
            return "high"
        elif score <= 0.4:
            return "low"
        return "mid"

    @property
    def openness_level(self) -> str:
        return self.get_level(self.openness)

    @property
    def conscientiousness_level(self) -> str:
        return self.get_level(self.conscientiousness)

    @property
    def extraversion_level(self) -> str:
        return self.get_level(self.extraversion)

    @property
    def agreeableness_level(self) -> str:
        return self.get_level(self.agreeableness)

    @property
    def neuroticism_level(self) -> str:
        return self.get_level(self.neuroticism)

    def to_dict(self) -> dict:
        return {
            "openness": round(self.openness, 3),
            "conscientiousness": round(self.conscientiousness, 3),
            "extraversion": round(self.extraversion, 3),
            "agreeableness": round(self.agreeableness, 3),
            "neuroticism": round(self.neuroticism, 3),
            "levels": {
                "openness": self.openness_level,
                "conscientiousness": self.conscientiousness_level,
                "extraversion": self.extraversion_level,
                "agreeableness": self.agreeableness_level,
                "neuroticism": self.neuroticism_level,
            }
        }


@dataclass
class DiagnosisResult:
    """
    声紋言霊リーディング結果データクラス。

    音声解析結果 → Big5スコア → 言霊テック世界観
    の変換結果をすべて格納します。

    声→周波数→色→命名のフローを反映。
    """
    session_id: str
    big5_score: Big5Score

    # アーキタイプ情報（YAMLから取得）
    archetype_code: str = ""          # 例: "GUREN_GUIDE"
    archetype_name: str = ""          # 例: "紅蓮の導き手"
    archetype_emoji: str = ""         # 例: "🔥"
    archetype_tagline: str = ""       # キャッチコピー
    archetype_rarity: str = ""        # 希少度テキスト（例: "100人に8人"）

    # ============================================================
    # 色・周波数情報（言霊テック世界観）
    # ============================================================
    soul_color_name: str = ""         # 和名（例: "紅蓮"）
    soul_color_reading: str = ""      # 読み（例: "ぐれん"）
    soul_color_hex: str = ""          # 基本色HEX（例: "#C0392B"）
    personal_color_hex: str = ""      # パーソナライズ色HEX（F0/HNR/RMS微調整）
    note_name: str = ""               # 音名（例: "A3"）
    note_frequency_hz: float = 0.0    # 最寄り音階の周波数
    chakra_number: int = 0            # チャクラ番号（1-7）
    chakra_name: str = ""             # チャクラ名
    polarity: str = ""                # "陽" or "陰"

    # ============================================================
    # 鑑定テキスト（YAMLから取得 — テキスト直接格納）
    # ============================================================
    hidden_talent: str = ""           # 隠れた才能テキスト
    mission: str = ""                 # 魂の使命テキスト
    shadow: str = ""                  # シャドウ（使いきれていない力）テキスト
    resonance: str = ""               # 共鳴テキスト
    universe_message: str = ""        # 宇宙からのメッセージ
    keys_to_bloom: str = ""           # 才能を開花させるカギ

    # 元素情報
    dominant_elements: list = field(default_factory=list)
    element_colors: dict = field(default_factory=dict)

    # ============================================================
    # 音響生データ（グラフ描画・科学的可視化用）
    # ============================================================
    # 基本周波数（ピッチ）
    f0_mean_hz: float = 0.0
    f0_std_hz: float = 0.0
    f0_max_hz: float = 0.0
    f0_min_hz: float = 0.0

    # 声の質指標
    jitter_local: float = 0.0    # 声帯振動の周波数摂動（%）- 低いほど安定
    shimmer_local: float = 0.0   # 声帯振動の振幅摂動（%）- 低いほどクリア
    hnr_db: float = 0.0          # ハーモニクス対ノイズ比（dB）- 高いほど澄んだ声

    # エネルギー・音量
    rms_energy: float = 0.0      # RMSエネルギー（音量の代表値）
    rms_std: float = 0.0         # RMS変動（ダイナミックレンジ）

    # リズム・テンポ
    speech_rate: float = 0.0     # 推定話速（音節/秒の近似値）
    tempo_bpm: float = 0.0       # テンポ（BPM）
    pause_ratio: float = 0.0     # 無音区間の割合（0〜1）

    # スペクトル特性
    spectral_centroid_mean: float = 0.0
    spectral_centroid_std: float = 0.0

    # フォルマント
    f1_mean_hz: float = 0.0
    f2_mean_hz: float = 0.0

    # MFCC（最初の13係数）
    mfcc_mean: list = field(default_factory=lambda: [0.0] * 13)

    # メタデータ
    diagnosed_at: datetime = field(default_factory=datetime.now)
    worldview_theme: str = "kotodama_v1"

    # 声紋コード（ユニークID表示用）
    voice_code_id: str = ""  # 例: "#A3-220Hz-藍"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "big5_score": self.big5_score.to_dict(),
            "archetype_code": self.archetype_code,
            "archetype_name": self.archetype_name,
            "archetype_emoji": self.archetype_emoji,
            "archetype_tagline": self.archetype_tagline,
            "archetype_rarity": self.archetype_rarity,
            # 色・周波数情報
            "soul_color": {
                "name": self.soul_color_name,
                "reading": self.soul_color_reading,
                "hex": self.soul_color_hex,
                "personal_hex": self.personal_color_hex,
            },
            "note": {
                "name": self.note_name,
                "frequency_hz": self.note_frequency_hz,
            },
            "chakra": {
                "number": self.chakra_number,
                "name": self.chakra_name,
            },
            "polarity": self.polarity,
            # 鑑定テキスト
            "hidden_talent": self.hidden_talent,
            "mission": self.mission,
            "shadow": self.shadow,
            "resonance": self.resonance,
            "universe_message": self.universe_message,
            "keys_to_bloom": self.keys_to_bloom,
            "dominant_elements": self.dominant_elements,
            "voice_code_id": self.voice_code_id,
            "diagnosed_at": self.diagnosed_at.isoformat(),
            "worldview_theme": self.worldview_theme,
        }
