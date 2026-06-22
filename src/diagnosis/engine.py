"""
声紋言霊リーディング エンジン

処理フロー:
    1. 音声解析結果（AudioAnalysisResult）を受け取る
    2. 各音響特徴量をBig5スコアに変換（科学的根拠に基づく重み付け）
    3. Big5スコアから支配元素＋陰陽を決定
    4. F0→音階→色を算出
    5. YAMLローダー経由で鑑定テキストを取得
    6. DiagnosisResultを返す

科学的根拠:
    - Mairesse et al.(2007): 音響特徴量とBig5の相関
    - Schuller et al.(2012): INTERSPEECH Speaker Trait Challenge
    - 外向性・神経症傾向が最も音声で予測しやすい因子 (r=0.38〜0.40)

世界観:
    - 「言霊テック」：声明の5つの徳 ≒ Big5
    - 声→周波数→色→命名の直感フロー
    - 5元素 × 陰陽 = 10タイプ
"""

import logging
import hashlib
import math
import colorsys
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
# 独自指標: RMSエネルギー（音量）、話速
EXTRAVERSION_WEIGHTS = {
    "rms_energy_norm": 0.50,        # 音量 - 最も信頼性高い指標
    "speech_rate_norm": 0.50,       # 話速
}

# 神経症傾向 (Neuroticism) スコアの重み
# 独自指標: ジッター、シマー
NEUROTICISM_WEIGHTS = {
    "jitter_norm": 0.50,            # ジッター（高いほど神経症傾向高）
    "shimmer_norm": 0.50,           # シマー（高いほど神経症傾向高）
}

# 開放性 (Openness) スコアの重み
# 独自指標: F0変動、スペクトル重心変動
OPENNESS_WEIGHTS = {
    "f0_std_norm": 0.50,            # ピッチ変動が豊か
    "spectral_centroid_std_norm": 0.50,  # スペクトル重心の変動
}

# 誠実性 (Conscientiousness) スコアの重み
# 独自指標: HNR（明瞭さ）、ポーズ比率逆数（途切れない）
CONSCIENTIOUSNESS_WEIGHTS = {
    "hnr_norm": 0.50,               # HNR高い（明瞭な声）
    "pause_ratio_inv_norm": 0.50,   # ポーズ少ない（途切れない発話）
}

# 協調性 (Agreeableness) スコアの重み
# 独自指標: スペクトル重心逆数（温かさ）、RMS変動逆数（安定）
AGREEABLENESS_WEIGHTS = {
    "spectral_centroid_inv_norm": 0.50,  # スペクトル重心低め（温かい声）
    "rms_std_inv_norm": 0.50,            # 音量変動少ない（穏やか）
}

# ========================================================
# 元素とBig5因子のマッピング
# ========================================================
ELEMENT_MAP = {
    "extraversion":     "FIRE",
    "neuroticism":      "WATER",
    "openness":         "WIND",
    "conscientiousness": "EARTH",
    "agreeableness":    "SKY",
}

# ========================================================
# 陰陽とアーキタイプコードのマッピング
# 5元素 × 陰陽 = 10タイプ
# ========================================================
ARCHETYPE_MAP = {
    ("FIRE",  "陽"): "GUREN_GUIDE",
    ("FIRE",  "陰"): "KOHAKU_SHAMAN",
    ("EARTH", "陽"): "KOGANE_ARCHITECT",
    ("EARTH", "陰"): "SHIKKOKU_GUARDIAN",
    ("SKY",   "陽"): "SUIGYOKU_TUNER",
    ("SKY",   "陰"): "SHION_VOYAGER",
    ("WIND",  "陽"): "RURI_SEEKER",
    ("WIND",  "陰"): "SHIROGANE_PIONEER",
    ("WATER", "陽"): "USUKURENAI_ORACLE",
    ("WATER", "陰"): "AI_SAGE",
}

# ========================================================
# F0→音階→色 変換テーブル
# チャクラベースの音名→色マッピング
# ========================================================
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

CHROMA_CHAKRA = {
    'C':  {'chakra': 1, 'chakra_name': 'ムーラーダーラ（ルート）'},
    'C#': {'chakra': 1, 'chakra_name': 'ムーラーダーラ（ルート）'},
    'D':  {'chakra': 2, 'chakra_name': 'スワーディシュターナ（仙骨）'},
    'D#': {'chakra': 2, 'chakra_name': 'スワーディシュターナ（仙骨）'},
    'E':  {'chakra': 3, 'chakra_name': 'マニプーラ（太陽神経叢）'},
    'F':  {'chakra': 4, 'chakra_name': 'アナーハタ（ハート）'},
    'F#': {'chakra': 4, 'chakra_name': 'アナーハタ（ハート）'},
    'G':  {'chakra': 5, 'chakra_name': 'ヴィシュッダ（喉）'},
    'G#': {'chakra': 5, 'chakra_name': 'ヴィシュッダ（喉）'},
    'A':  {'chakra': 6, 'chakra_name': 'アージュニャー（第三の眼）'},
    'A#': {'chakra': 6, 'chakra_name': 'アージュニャー（第三の眼）'},
    'B':  {'chakra': 7, 'chakra_name': 'サハスラーラ（クラウン）'},
}


class DiagnosisEngine(IDiagnosisEngine):
    """
    声紋言霊リーディング エンジン

    音声特徴量 → Big5スコア → 元素＋陰陽 → 色 → 鑑定テキスト
    の変換を担当します。
    """

    def __init__(self, worldview_theme: str = "kotodama_v1"):
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
        音声解析結果から完全なリーディング結果を生成する。

        Step 1: 音響特徴量を正規化
        Step 2: Big5スコアを計算
        Step 3: 支配元素を決定（上位1因子）
        Step 4: 陰陽を判定（外向的発現 vs 内向的発現）
        Step 5: F0→音階→色を算出
        Step 6: パーソナルカラーを微調整
        Step 7: YAMLからテキストを取得
        Step 8: DiagnosisResultを組み立てて返す
        """
        logger.info(f"リーディング開始: session_id={analysis.session_id}")

        # Step 1 & 2: Big5スコアを計算
        big5 = self._calculate_big5_score(analysis)
        logger.info(f"Big5スコア: E={big5.extraversion:.3f}, N={big5.neuroticism:.3f}, "
                    f"O={big5.openness:.3f}, C={big5.conscientiousness:.3f}, A={big5.agreeableness:.3f}")

        # Step 3: 支配元素を決定
        dominant_element = self._determine_dominant_element(big5)

        # Step 4: 陰陽を判定
        polarity = self._determine_polarity(analysis, big5)

        # Step 5: アーキタイプコードを決定
        archetype_code = ARCHETYPE_MAP.get(
            (dominant_element, polarity), "GUREN_GUIDE"
        )
        logger.info(f"アーキタイプ決定: {dominant_element}/{polarity} → {archetype_code}")

        # Step 6: F0→音階→色を算出
        note_info = self._f0_to_note(analysis.f0_mean_hz)

        # Step 7: YAMLからテキストを取得
        archetype_data = self._loader.get_archetype(archetype_code)

        # 色情報を取得
        color_info = self._loader.get_element_color(dominant_element, polarity)

        # Step 8: パーソナルカラーを微調整
        personal_hex = self._calculate_personal_color(
            color_info.get("hex", "#FFFFFF"),
            analysis.f0_mean_hz,
            analysis.hnr_db,
            analysis.rms_energy,
        )

        # Step 9: DiagnosisResultを組み立て
        result = self._build_diagnosis_result(
            session_id=analysis.session_id,
            big5=big5,
            archetype_code=archetype_code,
            archetype_data=archetype_data,
            dominant_element=dominant_element,
            polarity=polarity,
            color_info=color_info,
            personal_hex=personal_hex,
            note_info=note_info,
            analysis=analysis,
        )

        logger.info(f"リーディング完了: session_id={analysis.session_id}, "
                    f"type={archetype_data.get('name', '')}, color={color_info.get('name', '')}")
        return result

    # ======================================================================
    # Big5スコア計算（科学的根拠に基づく — 変更なし）
    # ======================================================================

    def _calculate_big5_score(self, a: AudioAnalysisResult) -> Big5Score:
        """
        音響特徴量からBig5スコアを計算する。

        各特徴量を0〜1の範囲に正規化し、重み付き平均でスコアを算出。
        性別補正済みの値を使用することを前提とする。
        """
        norm = self._normalize_features(a)

        extraversion = (
            norm["rms_energy_norm"] * EXTRAVERSION_WEIGHTS["rms_energy_norm"] +
            norm["speech_rate_norm"] * EXTRAVERSION_WEIGHTS["speech_rate_norm"]
        )

        neuroticism = (
            norm["jitter_norm"] * NEUROTICISM_WEIGHTS["jitter_norm"] +
            norm["shimmer_norm"] * NEUROTICISM_WEIGHTS["shimmer_norm"]
        )

        openness = (
            norm["f0_std_norm"] * OPENNESS_WEIGHTS["f0_std_norm"] +
            norm["spectral_centroid_std_norm"] * OPENNESS_WEIGHTS["spectral_centroid_std_norm"]
        )

        conscientiousness = (
            norm["hnr_norm"] * CONSCIENTIOUSNESS_WEIGHTS["hnr_norm"] +
            norm["pause_ratio_inv_norm"] * CONSCIENTIOUSNESS_WEIGHTS["pause_ratio_inv_norm"]
        )

        agreeableness = (
            norm["spectral_centroid_inv_norm"] * AGREEABLENESS_WEIGHTS["spectral_centroid_inv_norm"] +
            norm["rms_std_inv_norm"] * AGREEABLENESS_WEIGHTS["rms_std_inv_norm"]
        )
        # ==============================================
        # 因子間バイアス補正（ランク正規化）
        # ==============================================
        # 各因子の重み計算で使う特徴量が異なるため、
        # 特定の因子が構造的に高くなる傾向がある。
        # 例: 誠実性(C)はHNR+speech_rate+jitter_invの全てが
        #     中央値寄りになりやすく、常に0.5付近に収束する。
        # これを補正するため、5因子を順位ベースで再正規化する。
        # 「声の個性のどの側面が最も際立っているか」を判定。
        raw_scores = {
            "openness": openness,
            "conscientiousness": conscientiousness,
            "extraversion": extraversion,
            "agreeableness": agreeableness,
            "neuroticism": neuroticism,
        }
        # 各因子を0-1内で相対正規化（min-max rescale）
        vals = list(raw_scores.values())
        s_min = min(vals)
        s_max = max(vals)
        spread = s_max - s_min if s_max > s_min else 1.0
        normalized = {k: (v - s_min) / spread for k, v in raw_scores.items()}

        return Big5Score(
            openness=float(normalized["openness"]),
            conscientiousness=float(normalized["conscientiousness"]),
            extraversion=float(normalized["extraversion"]),
            agreeableness=float(normalized["agreeableness"]),
            neuroticism=float(normalized["neuroticism"]),
        )

    def _normalize_features(self, a: AudioAnalysisResult) -> dict:
        """
        音響特徴量を0〜1の範囲に正規化する。
        """
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
        shimmer_inv_norm = 1.0 - shimmer_norm

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

        # RMS変動性（音量の起伏）
        rms_std_norm = norm_clamp(a.rms_std, 0, 0.05)
        rms_std_inv_norm = 1.0 - rms_std_norm

        return {
            "rms_energy_norm": rms_norm,
            "speech_rate_norm": speech_rate_norm,
            "f0_std_norm": f0_std_norm,
            "pause_ratio_norm": pause_ratio_norm,
            "pause_ratio_inv_norm": pause_ratio_inv_norm,
            "jitter_norm": jitter_norm,
            "jitter_inv_norm": jitter_inv_norm,
            "shimmer_norm": shimmer_norm,
            "shimmer_inv_norm": shimmer_inv_norm,
            "hnr_norm": hnr_norm,
            "hnr_inv_norm": hnr_inv_norm,
            "spectral_centroid_norm": spectral_centroid_norm,
            "spectral_centroid_inv_norm": spectral_centroid_inv_norm,
            "spectral_centroid_std_norm": spectral_centroid_std_norm,
            "mfcc_variability_norm": mfcc_variability_norm,
            "rms_std_norm": rms_std_norm,
            "rms_std_inv_norm": rms_std_inv_norm,
        }

    # ======================================================================
    # 新アルゴリズム：支配元素＋陰陽判定
    # ======================================================================

    def _determine_dominant_element(self, big5: Big5Score) -> str:
        """
        Big5の最高スコアの因子から支配元素を決定する。

        声明の5つの徳 ≒ Big5:
            正直（extraversion→FIRE）、調和（agreeableness→SKY）、
            明瞭（conscientiousness→EARTH）、充実（openness→WIND）、
            到達（neuroticism→WATER）
        """
        scores = {
            "extraversion": big5.extraversion,
            "neuroticism": big5.neuroticism,
            "openness": big5.openness,
            "conscientiousness": big5.conscientiousness,
            "agreeableness": big5.agreeableness,
        }
        dominant_factor = max(scores, key=scores.get)
        return ELEMENT_MAP[dominant_factor]

    def _determine_polarity(self, analysis: AudioAnalysisResult, big5: Big5Score) -> str:
        """
        陰陽を判定する。

        陽（外向的発現）: エネルギーが外に向かう
            - RMSが高い（声が力強い）
            - 話速が速い（テンポ感がある）
            - ポーズが少ない（エネルギッシュ）

        陰（内向的発現）: エネルギーが内に向かう
            - RMSが低い（声が穏やか）
            - 話速が遅い（熟考型）
            - ポーズが多い（間を大切にする）
        """
        # 陽スコアを計算（0〜1）
        def norm(value, low, high):
            if high == low:
                return 0.5
            return max(0.0, min(1.0, (value - low) / (high - low)))

        yang_score = (
            norm(analysis.rms_energy, 0.001, 0.15) * 0.40 +
            norm(analysis.speech_rate, 0, 10) * 0.30 +
            (1.0 - max(0.0, min(1.0, analysis.pause_ratio))) * 0.30
        )

        return "陽" if yang_score >= 0.5 else "陰"

    # ======================================================================
    # F0→音階→色 変換
    # ======================================================================

    def _f0_to_note(self, f0_hz: float) -> dict:
        """
        F0（基本周波数）を最も近い音名に変換し、チャクラ情報を付与する。

        Returns:
            {
                "note_name": "A3",
                "note_frequency_hz": 220.0,
                "chroma": "A",
                "chakra_number": 6,
                "chakra_name": "アージュニャー（第三の眼）",
            }
        """
        if f0_hz <= 0:
            return {
                "note_name": "A3",
                "note_frequency_hz": 220.0,
                "chroma": "A",
                "chakra_number": 6,
                "chakra_name": "アージュニャー（第三の眼）",
            }

        # MIDI変換
        midi = 69 + 12 * math.log2(f0_hz / 440.0)
        midi_rounded = round(midi)
        chroma = NOTE_NAMES[midi_rounded % 12]
        octave = (midi_rounded // 12) - 1

        # 最寄り音階の正確な周波数
        note_freq = 440.0 * (2 ** ((midi_rounded - 69) / 12.0))

        # チャクラ情報
        chakra = CHROMA_CHAKRA.get(chroma, {'chakra': 1, 'chakra_name': 'ムーラーダーラ（ルート）'})

        return {
            "note_name": f"{chroma}{octave}",
            "note_frequency_hz": round(note_freq, 2),
            "chroma": chroma,
            "chakra_number": chakra['chakra'],
            "chakra_name": chakra['chakra_name'],
        }

    # ======================================================================
    # パーソナルカラー微調整
    # ======================================================================

    def _calculate_personal_color(
        self, base_hex: str, f0_hz: float, hnr_db: float, rms_energy: float
    ) -> str:
        """
        タイプの基本色を個人のF0・HNR・RMSで微調整する。

        同じタイプでも一人ひとり微妙に色が異なる →「世界に一つだけの色」

        調整:
            - F0 → 明度（高い声ほど明るく）
            - HNR → 彩度（澄んだ声ほど鮮やかに）
            - RMS → 深み（力強い声ほど濃く）
        """
        try:
            # HEX → RGB → HLS
            hex_clean = base_hex.lstrip('#')
            r, g, b = int(hex_clean[0:2], 16), int(hex_clean[2:4], 16), int(hex_clean[4:6], 16)
            h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

            # F0による明度調整（±15%範囲）
            f0_factor = max(0.0, min(1.0, (f0_hz - 80) / (300 - 80)))
            l_adj = l + (f0_factor - 0.5) * 0.15

            # HNRによる彩度調整（±10%範囲）
            hnr_factor = max(0.0, min(1.0, (hnr_db - 10) / (30 - 10)))
            s_adj = s + (hnr_factor - 0.5) * 0.10

            # RMSによる深み調整（±5%範囲）
            rms_factor = max(0.0, min(1.0, rms_energy / 0.15))
            l_adj = l_adj - (rms_factor - 0.5) * 0.05

            # クランプ
            l_adj = max(0.1, min(0.9, l_adj))
            s_adj = max(0.1, min(1.0, s_adj))

            # HLS → RGB → HEX
            r2, g2, b2 = colorsys.hls_to_rgb(h, l_adj, s_adj)
            return f"#{int(r2 * 255):02X}{int(g2 * 255):02X}{int(b2 * 255):02X}"

        except Exception as e:
            logger.warning(f"パーソナルカラー計算エラー（基本色を使用）: {e}")
            return base_hex

    # ======================================================================
    # 声紋コードID生成
    # ======================================================================

    def _generate_voice_code_id(
        self, session_id: str, f0_mean: float, note_name: str, color_name: str
    ) -> str:
        """
        声紋コードIDを生成する（例: #A3-220Hz-藍）

        ユーザーに見せる「宇宙のユニークID」として機能する。
        科学的数値（F0）と色名を統合し、神秘感を演出。
        """
        # セッションIDからアルファベット部分を生成
        hash_val = hashlib.md5(session_id.encode()).hexdigest()[:2].upper()
        # F0平均値を整数に丸める
        f0_int = int(round(f0_mean)) if f0_mean > 0 else 220
        return f"#{hash_val}-{f0_int}Hz-{color_name}"

    # ======================================================================
    # 結果組み立て
    # ======================================================================

    def _build_diagnosis_result(
        self,
        session_id: str,
        big5: Big5Score,
        archetype_code: str,
        archetype_data: dict,
        dominant_element: str,
        polarity: str,
        color_info: dict,
        personal_hex: str,
        note_info: dict,
        analysis=None,
    ) -> DiagnosisResult:
        """
        全データからDiagnosisResultを組み立てる。
        """
        # ドミナント元素の色情報を取得
        dominant_elements = archetype_data.get("dominant_elements", [dominant_element])
        element_colors = {}
        for elem_code in dominant_elements:
            elem_data = self._loader.get_element(elem_code)
            if elem_data:
                # 新形式のyang_color/yin_colorから取得を試みる
                p = archetype_data.get("polarity", polarity)
                color_key = "yang_color" if p == "陽" else "yin_color"
                color_d = elem_data.get(color_key)
                if color_d:
                    element_colors[elem_code] = color_d.get("hex", "#FFFFFF")
                else:
                    element_colors[elem_code] = elem_data.get("color", "#FFFFFF")

        # 声紋コードID
        voice_code_id = self._generate_voice_code_id(
            session_id,
            analysis.f0_mean_hz if analysis else 0,
            note_info.get("note_name", "A3"),
            color_info.get("name", ""),
        )

        return DiagnosisResult(
            session_id=session_id,
            big5_score=big5,
            archetype_code=archetype_code,
            archetype_name=archetype_data.get("name", ""),
            archetype_emoji=archetype_data.get("emoji", ""),
            archetype_tagline=archetype_data.get("tagline", ""),
            archetype_rarity=archetype_data.get("rarity", ""),
            # 色・周波数情報
            soul_color_name=color_info.get("name", ""),
            soul_color_reading=color_info.get("reading", ""),
            soul_color_hex=color_info.get("hex", "#FFFFFF"),
            personal_color_hex=personal_hex,
            note_name=note_info.get("note_name", ""),
            note_frequency_hz=note_info.get("note_frequency_hz", 0.0),
            chakra_number=note_info.get("chakra_number", 0),
            chakra_name=note_info.get("chakra_name", ""),
            polarity=polarity,
            # 鑑定テキスト（新形式：テキスト直接格納）
            hidden_talent=archetype_data.get("hidden_talent", ""),
            mission=archetype_data.get("mission", ""),
            shadow=archetype_data.get("shadow", ""),
            resonance=archetype_data.get("resonance", ""),
            universe_message=archetype_data.get("universe_message", ""),
            keys_to_bloom=archetype_data.get("keys_to_bloom", ""),
            # 元素情報
            dominant_elements=dominant_elements,
            element_colors=element_colors,
            # メタデータ
            diagnosed_at=datetime.now(),
            worldview_theme=self._loader.theme_name,
            voice_code_id=voice_code_id,
            # 音響生データ（グラフ描画用）
            f0_mean_hz=analysis.f0_mean_hz if analysis else 0.0,
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
