"""
診断エンジンの単体テスト

kotodama_v1 テーマに対応した最新版。
モックのAudioAnalysisResultを使用して、各アーキタイプが正しく判定されるかを検証します。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.audio.models import AudioAnalysisResult
from src.diagnosis.engine import DiagnosisEngine, ARCHETYPE_MAP
from src.diagnosis.models import Big5Score


def make_analysis(session_id="test-001", **kwargs) -> AudioAnalysisResult:
    """テスト用AudioAnalysisResultを作成するHelper（平均的な日本人音声をデフォルト値に）"""
    defaults = {
        "f0_mean_hz": 150.0,
        "f0_std_hz": 22.0,          # 日本人平均
        "f0_max_hz": 200.0,
        "f0_min_hz": 100.0,
        "jitter_local": 0.65,       # 日本人平均
        "shimmer_local": 3.2,       # 日本人平均
        "hnr_db": 17.0,             # 日本人平均
        "rms_energy": 0.045,        # 日本人平均
        "rms_std": 0.016,           # 日本人平均
        "speech_rate": 5.2,         # 日本人平均
        "tempo_bpm": 120.0,
        "pause_ratio": 0.23,        # 日本人平均
        "spectral_centroid_mean": 1900.0,  # 日本人平均
        "spectral_centroid_std": 500.0,    # 日本人平均
        "mfcc_mean": [0.0] * 13,
        "mfcc_std": [3.0] * 13,     # 日本人平均
        "f1_mean_hz": 700.0,
        "f2_mean_hz": 1500.0,
        "gender": "unknown",
        "analysis_duration_sec": 30.0,
    }
    defaults.update(kwargs)
    return AudioAnalysisResult(session_id=session_id, **defaults)


# 現行の有効アーキタイプコード一覧
VALID_ARCHETYPE_CODES = list(ARCHETYPE_MAP.values())


class TestDiagnosisEngine:
    """診断エンジンの単体テスト"""

    def setup_method(self):
        self.engine = DiagnosisEngine(worldview_theme="kotodama_v1")

    def test_diagnose_returns_result(self):
        """診断結果オブジェクトが返ってくること"""
        result = self.engine.diagnose(make_analysis())
        assert result is not None
        assert result.session_id == "test-001"
        assert result.archetype_code != ""
        assert result.archetype_name != ""

    def test_archetype_code_is_valid(self):
        """返ってくるアーキタイプコードが現行の10種のいずれかであること"""
        result = self.engine.diagnose(make_analysis())
        assert result.archetype_code in VALID_ARCHETYPE_CODES, (
            f"不正なアーキタイプコード: {result.archetype_code}\n"
            f"有効なコード: {VALID_ARCHETYPE_CODES}"
        )

    # ------------------------------------------------------------------
    # アーキタイプ別プロファイルテスト
    # ------------------------------------------------------------------

    def test_guren_guide_profile(self):
        """FIRE×陽 → GUREN_GUIDE（紅蓮の導き手）: 音量大・話速速・ポーズ少"""
        result = self.engine.diagnose(make_analysis(
            rms_energy=0.12,       # 音量大（外向性高）
            speech_rate=8.0,       # 話速速い
            pause_ratio=0.08,      # ポーズ少ない（陽判定を強化）
            jitter_local=0.3,      # ジッター低（神経症傾向低）
            shimmer_local=1.5,     # シマー低
        ))
        assert result.archetype_code == "GUREN_GUIDE", (
            f"期待: GUREN_GUIDE, 実際: {result.archetype_code} "
            f"(Big5: E={result.big5_score.extraversion:.2f}, "
            f"N={result.big5_score.neuroticism:.2f}, "
            f"O={result.big5_score.openness:.2f}, "
            f"C={result.big5_score.conscientiousness:.2f}, "
            f"A={result.big5_score.agreeableness:.2f})"
        )

    def test_ai_sage_profile(self):
        """WATER×陰 → AI_SAGE（藍の賢者）: ジッター・シマー高・音量小・話速遅"""
        result = self.engine.diagnose(make_analysis(
            rms_energy=0.01,       # 音量小（外向性低）
            speech_rate=2.0,       # 話速遅い
            pause_ratio=0.45,      # ポーズ多い（陰判定を強化）
            jitter_local=1.5,      # ジッター高（神経症傾向高）
            shimmer_local=6.0,     # シマー高
        ))
        assert result.archetype_code == "AI_SAGE", (
            f"期待: AI_SAGE, 実際: {result.archetype_code} "
            f"(Big5: E={result.big5_score.extraversion:.2f}, "
            f"N={result.big5_score.neuroticism:.2f}, "
            f"O={result.big5_score.openness:.2f}, "
            f"C={result.big5_score.conscientiousness:.2f}, "
            f"A={result.big5_score.agreeableness:.2f})"
        )

    def test_kogane_architect_profile(self):
        """EARTH×陽 → KOGANE_ARCHITECT（黄金の建築家）: HNR高・ポーズ少・明瞭な声"""
        result = self.engine.diagnose(make_analysis(
            hnr_db=28.0,           # HNR高（誠実性高）
            pause_ratio=0.08,      # ポーズ少ない（陽 + 誠実性高）
            speech_rate=6.0,       # 話速やや速い（陽判定）
            rms_energy=0.06,       # 音量やや大（陽判定）
            jitter_local=0.4,      # ジッター低（神経症傾向低）
            shimmer_local=2.0,     # シマー低
            f0_std_hz=15.0,        # ピッチ安定（開放性低め）
        ))
        assert result.archetype_code == "KOGANE_ARCHITECT", (
            f"期待: KOGANE_ARCHITECT, 実際: {result.archetype_code} "
            f"(Big5: E={result.big5_score.extraversion:.2f}, "
            f"N={result.big5_score.neuroticism:.2f}, "
            f"O={result.big5_score.openness:.2f}, "
            f"C={result.big5_score.conscientiousness:.2f}, "
            f"A={result.big5_score.agreeableness:.2f})"
        )

    # ------------------------------------------------------------------
    # Big5スコアの品質テスト
    # ------------------------------------------------------------------

    def test_big5_score_range(self):
        """Big5スコアが0.0〜1.0の範囲に収まっていること"""
        result = self.engine.diagnose(make_analysis())
        big5 = result.big5_score
        for name, score in [
            ("openness", big5.openness),
            ("conscientiousness", big5.conscientiousness),
            ("extraversion", big5.extraversion),
            ("agreeableness", big5.agreeableness),
            ("neuroticism", big5.neuroticism),
        ]:
            assert 0.0 <= score <= 1.0, f"{name}のスコアが範囲外: {score}"

    def test_big5_scores_are_distinct(self):
        """因子間バイアス補正後、最高スコアと最低スコアが区別されていること
        （全入力が平均値だと全因子=0になるため、明確に差のあるプロファイルを使用）"""
        result = self.engine.diagnose(make_analysis(
            rms_energy=0.10,   # 音量大（外向性高）
            jitter_local=1.2,  # ジッター高（神経症傾向高）
        ))
        big5 = result.big5_score
        scores = [big5.openness, big5.conscientiousness, big5.extraversion,
                  big5.agreeableness, big5.neuroticism]
        assert max(scores) != min(scores), "全スコアが同値になっている（正規化異常）"

    # ------------------------------------------------------------------
    # 出力フィールドのテスト
    # ------------------------------------------------------------------

    def test_voice_code_id_format(self):
        """voice_code_idのフォーマットが '#XX-NNNHz-色名' 形式であること"""
        result = self.engine.diagnose(make_analysis(f0_mean_hz=200.0))
        assert result.voice_code_id.startswith("#"), f"先頭が#でない: {result.voice_code_id}"
        assert "Hz" in result.voice_code_id, f"Hzが含まれない: {result.voice_code_id}"

    def test_archetype_texts_are_loaded(self):
        """アーキタイプのテキストフィールドが空でないこと"""
        result = self.engine.diagnose(make_analysis())
        assert result.archetype_name != "", "archetype_nameが空"
        assert result.archetype_tagline != "", "archetype_taglineが空"
        assert result.hidden_talent != "", "hidden_talentが空"
        assert result.mission != "", "missionが空"
        assert result.shadow != "", "shadowが空"
        assert result.universe_message != "", "universe_messageが空"

    def test_color_info_is_loaded(self):
        """色情報フィールドが設定されていること"""
        result = self.engine.diagnose(make_analysis())
        assert result.soul_color_name != "", "soul_color_nameが空"
        assert result.soul_color_hex.startswith("#"), f"HEXカラーが不正: {result.soul_color_hex}"
        assert result.personal_color_hex.startswith("#"), f"パーソナルカラーが不正: {result.personal_color_hex}"

    def test_note_info_is_loaded(self):
        """音名・周波数・チャクラ情報が設定されていること"""
        result = self.engine.diagnose(make_analysis(f0_mean_hz=220.0))
        assert result.note_name != "", "note_nameが空"
        assert result.note_frequency_hz > 0, "note_frequency_hzが0"
        assert 1 <= result.chakra_number <= 7, f"chakra_numberが範囲外: {result.chakra_number}"
        assert result.chakra_name != "", "chakra_nameが空"

    def test_polarity_is_valid(self):
        """polarityが '陽' または '陰' であること"""
        result = self.engine.diagnose(make_analysis())
        assert result.polarity in ("陽", "陰"), f"不正なpolarity: {result.polarity}"

    def test_theme_name_is_kotodama(self):
        """worldview_themeがkotodama_v1であること"""
        result = self.engine.diagnose(make_analysis())
        assert result.worldview_theme == "kotodama_v1"

    def test_acoustic_data_is_preserved(self):
        """音響生データがDiagnosisResultに正しく格納されていること"""
        result = self.engine.diagnose(make_analysis(
            f0_mean_hz=180.0,
            rms_energy=0.07,
            hnr_db=20.0,
        ))
        assert result.f0_mean_hz == pytest.approx(180.0)
        assert result.rms_energy == pytest.approx(0.07)
        assert result.hnr_db == pytest.approx(20.0)


class TestBig5Score:
    """Big5Scoreデータクラスの単体テスト"""

    def test_score_clamped_to_range(self):
        """スコアが0.0〜1.0にクランプされること"""
        score = Big5Score(openness=1.5, conscientiousness=-0.3,
                          extraversion=0.8, agreeableness=0.2, neuroticism=0.0)
        assert score.openness == 1.0
        assert score.conscientiousness == 0.0

    def test_level_high(self):
        """0.6以上は 'high' になること"""
        assert Big5Score(extraversion=0.7).extraversion_level == "high"

    def test_level_low(self):
        """0.4以下は 'low' になること"""
        assert Big5Score(neuroticism=0.3).neuroticism_level == "low"

    def test_level_mid(self):
        """0.4〜0.6は 'mid' になること"""
        assert Big5Score(openness=0.5).openness_level == "mid"

    def test_to_dict_includes_levels(self):
        """to_dict()にlevelsキーが含まれること"""
        d = Big5Score().to_dict()
        assert "levels" in d
        assert "openness" in d["levels"]


class TestWorldviewLoader:
    """世界観ローダーの単体テスト（kotodama_v1対応）"""

    def setup_method(self):
        from src.diagnosis.worldview.loader import WorldviewLoader
        self.loader = WorldviewLoader(theme_name="kotodama_v1")

    def test_get_archetype_guren(self):
        """GUREN_GUIDEのアーキタイプ情報を取得できること"""
        archetype = self.loader.get_archetype("GUREN_GUIDE")
        assert archetype["name"] == "紅蓮"
        assert "hidden_talent" in archetype
        assert "mission" in archetype
        assert "shadow" in archetype
        assert "universe_message" in archetype

    def test_all_archetypes_loaded(self):
        """全10タイプが読み込まれること"""
        archetypes = self.loader.get_all_archetypes()
        assert len(archetypes) == 10, f"アーキタイプ数が10でない: {len(archetypes)}"

    def test_all_archetype_codes_present(self):
        """全10コードが存在すること"""
        archetypes = self.loader.get_all_archetypes()
        for code in VALID_ARCHETYPE_CODES:
            assert code in archetypes, f"アーキタイプコードが見つからない: {code}"

    def test_invalid_archetype_raises(self):
        """存在しないコードはKeyErrorを発生させること"""
        with pytest.raises(KeyError):
            self.loader.get_archetype("SOLAR_HERALD")  # 旧コード

    def test_get_element_fire(self):
        """FIRE元素の情報を取得できること"""
        fire = self.loader.get_element("FIRE")
        assert fire["name"] == "火"
        assert "yang_color" in fire
        assert "yin_color" in fire

    def test_get_element_color_yang(self):
        """FIRE×陽の色情報が正しく取得できること"""
        color = self.loader.get_element_color("FIRE", "陽")
        assert color["name"] == "紅蓮"
        assert color["hex"] == "#C0392B"

    def test_get_element_color_yin(self):
        """FIRE×陰の色情報が正しく取得できること"""
        color = self.loader.get_element_color("FIRE", "陰")
        assert color["name"] == "琥珀"
        assert color["hex"] == "#E67E22"

    def test_all_elements_loaded(self):
        """5元素が全て読み込まれること"""
        for code in ["FIRE", "WATER", "WIND", "EARTH", "SKY"]:
            elem = self.loader.get_element(code)
            assert elem != {}, f"元素が空: {code}"

    def test_list_themes_includes_kotodama(self):
        """テーマ一覧に kotodama_v1 が含まれること"""
        themes = self.loader.list_available_themes()
        assert "kotodama_v1" in themes
