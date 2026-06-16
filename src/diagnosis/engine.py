"""
診断エンジン 実装クラス

処理フロー:
    1. 音声解析結果（AudioAnalysisResult）を受け取る
    2. 各音響特徴量をBig5スコアに変換（科学的根拠に基づく重み付け）
    3. Big5スコアからアーキタイプを決定
    4. YAMLローダー経由でスピリチュアル表現テキストを取得
    5. DiagnosisResultを返す

科学的根拠:
    - Mairesse et al.(2007): 音響特徴量とBig5の相関
    - Schuller et al.(2012): INTERSPEECH Speaker Trait Challenge
    - 外向性・神経症傾向が最も音声で予測しやすい因子 (r=0.38〜0.40)

疎結合設計:
    - IDiagnosisEngineインターフェースを実装
    - 世界観YAMLは外部注入（コード変更なしで世界観変更可能）
"""

import logging
import hashlib
from datetime import datetime
from typing import Optional

from .interfaces import IDiagnosisEngine
from .models import Big5Score, DiagnosisResult
from .worldview.loader import WorldviewLoader
from ..audio.models import AudioAnalysisResult

logger = logging.getLogger(__name__)


# ========================================================
# Big5スコア計算の重み設定
# 科学文献に基づく各特徴量の寄与率
# ========================================================

# 外向性 (Extraversion) スコアの重み
# 最重要: RMSエネルギー(音量) r=0.38〜0.40 (Mairesse 2007)
EXTRAVERSION_WEIGHTS = {
    "rms_energy_norm": 0.40,        # 音量 - 最も信頼性高い指標
    "speech_rate_norm": 0.30,       # 話速
    "f0_std_norm": 0.20,            # ピッチ変動
    "pause_ratio_inv_norm": 0.10,   # ポーズ少ない（逆数）
}

# 神経症傾向 (Neuroticism) スコアの重み
# Jitter・Shimmer・HNRの逆数が主要指標
NEUROTICISM_WEIGHTS = {
    "jitter_norm": 0.35,            # ジッター（高いほど神経症傾向高）
    "shimmer_norm": 0.35,           # シマー（高いほど神経症傾向高）
    "hnr_inv_norm": 0.20,           # HNR低い（逆数）
    "pause_ratio_norm": 0.10,       # ポーズ多い
}

# 開放性 (Openness) スコアの重み
OPENNESS_WEIGHTS = {
    "f0_std_norm": 0.40,            # ピッチ変動が豊か
    "spectral_centroid_std_norm": 0.30,  # スペクトル重心の変動
    "mfcc_variability_norm": 0.30,  # MFCC変動（声道の多様性）
}

# 誠実性 (Conscientiousness) スコアの重み
CONSCIENTIOUSNESS_WEIGHTS = {
    "speech_rate_norm": 0.35,       # 安定した話速
    "hnr_norm": 0.35,               # HNR高い（明瞭な声）
    "jitter_inv_norm": 0.30,        # ジッター低い（安定）
}

# 協調性 (Agreeableness) スコアの重み
AGREEABLENESS_WEIGHTS = {
    "spectral_centroid_inv_norm": 0.40,  # スペクトル重心低め（温かい声）
    "f0_std_norm": 0.30,                 # 適度なピッチ変動
    "hnr_norm": 0.30,                    # HNR高い（清潔感のある声）
}


class DiagnosisEngine(IDiagnosisEngine):
    """
    診断エンジンの実装クラス。

    音声特徴量 → Big5スコア → アーキタイプ → 診断テキスト
    の変換を担当します。
    """

    def __init__(self, worldview_theme: str = "elements_v1"):
        """
        Args:
            worldview_theme: 使用する世界観YAMLテーマ名
        """
        self._loader = WorldviewLoader(theme_name=worldview_theme)
        logger.info(f"DiagnosisEngine 初期化完了 (theme={worldview_theme})")

    def set_worldview_theme(self, theme_name: str) -> None:
        """世界観テーマを切り替える（コード変更不要）"""
        self._loader.switch_theme(theme_name)
        logger.info(f"世界観テーマを切り替えました: {theme_name}")

    def diagnose(self, analysis: AudioAnalysisResult) -> DiagnosisResult:
        """
        音声解析結果から完全な診断結果を生成する。

        Step 1: 音響特徴量を正規化
        Step 2: Big5スコアを計算
        Step 3: アーキタイプを決定
        Step 4: YAMLからテキストを取得
        Step 5: DiagnosisResultを組み立てて返す
        """
        logger.info(f"診断開始: session_id={analysis.session_id}")

        # Step 1 & 2: Big5スコアを計算
        big5 = self._calculate_big5_score(analysis)
        logger.info(f"Big5スコア: E={big5.extraversion:.3f}, N={big5.neuroticism:.3f}, "
                    f"O={big5.openness:.3f}, C={big5.conscientiousness:.3f}, A={big5.agreeableness:.3f}")

        # Step 3: アーキタイプを決定
        archetype_code = self._select_archetype(big5)
        logger.info(f"アーキタイプ決定: {archetype_code}")

        # Step 4: YAMLからテキストを取得
        archetype_data = self._loader.get_archetype(archetype_code)

        # Step 5: DiagnosisResultを組み立て
        result = self._build_diagnosis_result(
            session_id=analysis.session_id,
            big5=big5,
            archetype_code=archetype_code,
            archetype_data=archetype_data,
            f0_mean=analysis.f0_mean_hz,
            analysis=analysis,  # 音響生データをそのまま渡す
        )

        logger.info(f"診断完了: session_id={analysis.session_id}, type={archetype_data.get('name', '')}")
        return result

    def _calculate_big5_score(self, a: AudioAnalysisResult) -> Big5Score:
        """
        音響特徴量からBig5スコアを計算する。

        各特徴量を0〜1の範囲に正規化し、重み付き平均でスコアを算出。
        性別補正済みの値を使用することを前提とする。
        """
        norm = self._normalize_features(a)

        extraversion = (
            norm["rms_energy_norm"] * EXTRAVERSION_WEIGHTS["rms_energy_norm"] +
            norm["speech_rate_norm"] * EXTRAVERSION_WEIGHTS["speech_rate_norm"] +
            norm["f0_std_norm"] * EXTRAVERSION_WEIGHTS["f0_std_norm"] +
            norm["pause_ratio_inv_norm"] * EXTRAVERSION_WEIGHTS["pause_ratio_inv_norm"]
        )

        neuroticism = (
            norm["jitter_norm"] * NEUROTICISM_WEIGHTS["jitter_norm"] +
            norm["shimmer_norm"] * NEUROTICISM_WEIGHTS["shimmer_norm"] +
            norm["hnr_inv_norm"] * NEUROTICISM_WEIGHTS["hnr_inv_norm"] +
            norm["pause_ratio_norm"] * NEUROTICISM_WEIGHTS["pause_ratio_norm"]
        )

        openness = (
            norm["f0_std_norm"] * OPENNESS_WEIGHTS["f0_std_norm"] +
            norm["spectral_centroid_std_norm"] * OPENNESS_WEIGHTS["spectral_centroid_std_norm"] +
            norm["mfcc_variability_norm"] * OPENNESS_WEIGHTS["mfcc_variability_norm"]
        )

        conscientiousness = (
            norm["speech_rate_norm"] * CONSCIENTIOUSNESS_WEIGHTS["speech_rate_norm"] +
            norm["hnr_norm"] * CONSCIENTIOUSNESS_WEIGHTS["hnr_norm"] +
            norm["jitter_inv_norm"] * CONSCIENTIOUSNESS_WEIGHTS["jitter_inv_norm"]
        )

        agreeableness = (
            norm["spectral_centroid_inv_norm"] * AGREEABLENESS_WEIGHTS["spectral_centroid_inv_norm"] +
            norm["f0_std_norm"] * AGREEABLENESS_WEIGHTS["f0_std_norm"] +
            norm["hnr_norm"] * AGREEABLENESS_WEIGHTS["hnr_norm"]
        )

        return Big5Score(
            openness=float(openness),
            conscientiousness=float(conscientiousness),
            extraversion=float(extraversion),
            agreeableness=float(agreeableness),
            neuroticism=float(neuroticism),
        )

    def _normalize_features(self, a: AudioAnalysisResult) -> dict:
        """
        音響特徴量を0〜1の範囲に正規化する。

        正規化ロジック:
            - sigmoid関数を使用して滑らかに0〜1に変換
            - 参照値を中心に分布するよう調整
            - 性別差は音声解析段階で補正済みを前提とする
        """
        def sigmoid(x):
            """シグモイド関数で0〜1に変換"""
            import math
            return 1 / (1 + math.exp(-x))

        def norm_clamp(value, ref_low, ref_high):
            """参照範囲で線形正規化してクランプ"""
            if ref_high == ref_low:
                return 0.5
            normalized = (value - ref_low) / (ref_high - ref_low)
            return max(0.0, min(1.0, normalized))

        # RMSエネルギー正規化（0.001〜0.2の範囲が典型的）
        rms_norm = norm_clamp(a.rms_energy, 0.001, 0.15)

        # 話速正規化（0〜10の範囲）
        speech_rate_norm = norm_clamp(a.speech_rate, 0, 10)

        # F0標準偏差正規化（0〜80Hzの範囲が典型的）
        f0_std_norm = norm_clamp(a.f0_std_hz, 0, 80)

        # ポーズ比率正規化（0〜1の範囲、すでに正規化済み）
        pause_ratio_norm = max(0.0, min(1.0, a.pause_ratio))
        pause_ratio_inv_norm = 1.0 - pause_ratio_norm

        # ジッター正規化（0〜3%の範囲、正常値は0.5%以下）
        jitter_norm = norm_clamp(a.jitter_local, 0, 3.0)
        jitter_inv_norm = 1.0 - jitter_norm

        # シマー正規化（0〜10%の範囲、正常値は3%以下）
        shimmer_norm = norm_clamp(a.shimmer_local, 0, 10.0)

        # HNR正規化（0〜30dBの範囲、15dB以上が正常）
        hnr_norm = norm_clamp(a.hnr_db, 0, 30)
        hnr_inv_norm = 1.0 - hnr_norm

        # スペクトル重心正規化（500〜4000Hzの範囲）
        spectral_centroid_norm = norm_clamp(a.spectral_centroid_mean, 500, 4000)
        spectral_centroid_inv_norm = 1.0 - spectral_centroid_norm
        spectral_centroid_std_norm = norm_clamp(a.spectral_centroid_std, 0, 1500)

        # MFCC変動性（MCCの標準偏差の平均）
        mfcc_variability = sum(abs(v) for v in a.mfcc_std) / max(len(a.mfcc_std), 1)
        mfcc_variability_norm = norm_clamp(mfcc_variability, 0, 50)

        return {
            "rms_energy_norm": rms_norm,
            "speech_rate_norm": speech_rate_norm,
            "f0_std_norm": f0_std_norm,
            "pause_ratio_norm": pause_ratio_norm,
            "pause_ratio_inv_norm": pause_ratio_inv_norm,
            "jitter_norm": jitter_norm,
            "jitter_inv_norm": jitter_inv_norm,
            "shimmer_norm": shimmer_norm,
            "hnr_norm": hnr_norm,
            "hnr_inv_norm": hnr_inv_norm,
            "spectral_centroid_norm": spectral_centroid_norm,
            "spectral_centroid_inv_norm": spectral_centroid_inv_norm,
            "spectral_centroid_std_norm": spectral_centroid_std_norm,
            "mfcc_variability_norm": mfcc_variability_norm,
        }

    def _select_archetype(self, big5: Big5Score) -> str:
        """
        Big5の相対的パターンからアーキタイプを決定する。

        【改訂版】絶対閾値ではなく「5因子の中で最も高い上位2因子のペア」で決定。
        これにより全10アーキタイプが自然に分散する。

        マッピング（C(5,2)=10通り）:
            E+N → STORM_SHAMAN    カリスマ的・感情豊か
            E+O → SOLAR_HERALD    エネルギッシュ・創造的
            E+C → EARTH_GUARDIAN  行動力・誠実
            E+A → SKY_HARMONIST   社交的・調和
            N+O → COMET_SEEKER    芸術的・感受性豊か
            N+C → FOG_ORACLE      慎重・几帳面
            N+A → WIND_PIONEER    共感力・先駆
            O+C → STAR_ARCHITECT  創造×組織力
            O+A → TIDE_WANDERER   開放的・協調
            C+A → MOON_SAGE       誠実・温かさ
        """
        scores = [
            ("E", big5.extraversion),
            ("N", big5.neuroticism),
            ("O", big5.openness),
            ("C", big5.conscientiousness),
            ("A", big5.agreeableness),
        ]

        # スコアの高い順にソート（同点の場合はリスト順で安定ソート）
        sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

        # 上位2因子のペアを取得
        top1 = sorted_scores[0][0]
        top2 = sorted_scores[1][0]
        top_pair = frozenset([top1, top2])

        archetype_map = {
            frozenset(["E", "N"]): "STORM_SHAMAN",
            frozenset(["E", "O"]): "SOLAR_HERALD",
            frozenset(["E", "C"]): "EARTH_GUARDIAN",
            frozenset(["E", "A"]): "SKY_HARMONIST",
            frozenset(["N", "O"]): "COMET_SEEKER",
            frozenset(["N", "C"]): "FOG_ORACLE",
            frozenset(["N", "A"]): "WIND_PIONEER",
            frozenset(["O", "C"]): "STAR_ARCHITECT",
            frozenset(["O", "A"]): "TIDE_WANDERER",
            frozenset(["C", "A"]): "MOON_SAGE",
        }

        archetype_code = archetype_map.get(top_pair, "SOLAR_HERALD")

        logger.info(
            f"アーキタイプ選択: top1={top1}({sorted_scores[0][1]:.3f}), "
            f"top2={top2}({sorted_scores[1][1]:.3f}) → {archetype_code}"
        )
        return archetype_code

    def _generate_voice_code_id(self, session_id: str, f0_mean: float) -> str:
        """
        声紋コードIDを生成する（例: #A7-432Hz）

        ユーザーに見せる「宇宙のユニークID」として機能する。
        科学的数値（F0）をそのまま使い、神秘感を演出。
        """
        # セッションIDからアルファベット部分を生成
        hash_val = hashlib.md5(session_id.encode()).hexdigest()[:2].upper()
        # F0平均値を整数に丸める
        f0_int = int(round(f0_mean)) if f0_mean > 0 else 432
        return f"#{hash_val}-{f0_int}Hz"

    def _build_diagnosis_result(
        self,
        session_id: str,
        big5: Big5Score,
        archetype_code: str,
        archetype_data: dict,
        f0_mean: float,
        analysis=None,  # AudioAnalysisResult（音響生データ、グラフ用）
    ) -> DiagnosisResult:
        """
        YAMLデータからDiagnosisResultを組み立てる。
        """
        hidden_talent = archetype_data.get("hidden_talent", {})
        mission = archetype_data.get("mission", {})
        shadow = archetype_data.get("shadow", {})
        resonance = archetype_data.get("resonance", {})
        universe_msg = archetype_data.get("universe_message_2026", {})
        keys = archetype_data.get("keys_to_bloom", [])

        # ドミナント元素の色情報を取得
        dominant_elements = archetype_data.get("dominant_elements", [])
        element_colors = {}
        for elem_code in dominant_elements:
            elem_data = self._loader.get_element(elem_code)
            if elem_data:
                element_colors[elem_code] = elem_data.get("color", "#FFFFFF")

        return DiagnosisResult(
            session_id=session_id,
            big5_score=big5,
            archetype_code=archetype_code,
            archetype_name=archetype_data.get("name", ""),
            archetype_emoji=archetype_data.get("emoji", ""),
            archetype_tagline=archetype_data.get("tagline", ""),
            archetype_rarity=archetype_data.get("rarity", ""),
            hidden_talent_title=hidden_talent.get("title", ""),
            hidden_talent_description=hidden_talent.get("description", ""),
            hidden_talent_examples=hidden_talent.get("examples", []),
            mission_title=mission.get("title", ""),
            mission_description=mission.get("description", ""),
            mission_past_interpretation=mission.get("past_interpretation", ""),
            shadow_title=shadow.get("title", ""),
            shadow_description=shadow.get("description", ""),
            resonance_compatible_types=resonance.get("compatible_types", []),
            resonance_compatible_description=resonance.get("compatible_description", ""),
            resonance_chakra_activation=resonance.get("chakra_activation", ""),
            universe_message_title=universe_msg.get("title", ""),
            universe_message_description=universe_msg.get("description", ""),
            keys_to_bloom=keys,
            dominant_elements=dominant_elements,
            element_colors=element_colors,
            diagnosed_at=datetime.now(),
            worldview_theme=self._loader.theme_name,
            voice_code_id=self._generate_voice_code_id(session_id, f0_mean),
            # 音響生データ（グラフ描画用）
            f0_mean_hz=analysis.f0_mean_hz if analysis else f0_mean,
            f0_std_hz=analysis.f0_std_hz if analysis else 0.0,
            f0_max_hz=analysis.f0_max_hz if analysis else 0.0,
            f0_min_hz=analysis.f0_min_hz if analysis else 0.0,
            jitter_local=analysis.jitter_local if analysis else 0.0,
            shimmer_local=analysis.shimmer_local if analysis else 0.0,
            hnr_db=analysis.hnr_db if analysis else 0.0,
            rms_energy=analysis.rms_energy if analysis else 0.0,
            rms_std=analysis.rms_std if analysis else 0.0,
            speech_rate=analysis.speech_rate if analysis else 0.0,
            tempo_bpm=analysis.tempo_bpm if analysis else 0.0,
            pause_ratio=analysis.pause_ratio if analysis else 0.0,
            spectral_centroid_mean=analysis.spectral_centroid_mean if analysis else 0.0,
            spectral_centroid_std=analysis.spectral_centroid_std if analysis else 0.0,
            f1_mean_hz=analysis.f1_mean_hz if analysis else 0.0,
            f2_mean_hz=analysis.f2_mean_hz if analysis else 0.0,
            mfcc_mean=analysis.mfcc_mean if analysis else [0.0] * 13,
        )

