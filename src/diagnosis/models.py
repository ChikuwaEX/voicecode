"""
診断 データモデル定義

Big5パーソナリティ理論に基づいた診断結果を格納します。
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
    診断結果データクラス。

    音声解析結果 → Big5スコア → スピリチュアル表現
    の変換結果をすべて格納します。
    """
    session_id: str
    big5_score: Big5Score

    # アーキタイプ情報（YAMLから取得）
    archetype_code: str = ""          # 例: "SOLAR_HERALD"
    archetype_name: str = ""          # 例: "太陽の伝道者"
    archetype_emoji: str = ""         # 例: "🔥"
    archetype_tagline: str = ""       # キャッチコピー
    archetype_rarity: str = ""        # 希少度テキスト

    # 詳細診断テキスト（YAMLから取得）
    hidden_talent_title: str = ""
    hidden_talent_description: str = ""
    hidden_talent_examples: list = field(default_factory=list)

    mission_title: str = ""
    mission_description: str = ""
    mission_past_interpretation: str = ""

    shadow_title: str = ""
    shadow_description: str = ""

    resonance_compatible_types: list = field(default_factory=list)
    resonance_compatible_description: str = ""
    resonance_chakra_activation: str = ""

    universe_message_title: str = ""
    universe_message_description: str = ""

    keys_to_bloom: list = field(default_factory=list)

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
    worldview_theme: str = "elements_v1"

    # 声紋コード（ユニークID表示用）
    voice_code_id: str = ""  # 例: "#A7-432Hz"

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "big5_score": self.big5_score.to_dict(),
            "archetype_code": self.archetype_code,
            "archetype_name": self.archetype_name,
            "archetype_emoji": self.archetype_emoji,
            "archetype_tagline": self.archetype_tagline,
            "archetype_rarity": self.archetype_rarity,
            "hidden_talent": {
                "title": self.hidden_talent_title,
                "description": self.hidden_talent_description,
                "examples": self.hidden_talent_examples,
            },
            "mission": {
                "title": self.mission_title,
                "description": self.mission_description,
                "past_interpretation": self.mission_past_interpretation,
            },
            "shadow": {
                "title": self.shadow_title,
                "description": self.shadow_description,
            },
            "resonance": {
                "compatible_types": self.resonance_compatible_types,
                "compatible_description": self.resonance_compatible_description,
                "chakra_activation": self.resonance_chakra_activation,
            },
            "universe_message": {
                "title": self.universe_message_title,
                "description": self.universe_message_description,
            },
            "keys_to_bloom": self.keys_to_bloom,
            "dominant_elements": self.dominant_elements,
            "voice_code_id": self.voice_code_id,
            "diagnosed_at": self.diagnosed_at.isoformat(),
            "worldview_theme": self.worldview_theme,
        }
