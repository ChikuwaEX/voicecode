"""
PDFレポート生成エンジン 実装クラス

Playwright + Jinja2で最高品質のWebレポートをPDFとしてキャプチャします。
FastAPIのasyncio環境対応のため、PlaywrightはThreadPoolExecutorで別スレッドで実行します。
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from playwright.sync_api import sync_playwright

from .interfaces import IReportGenerator
from .models import PDFReport
from ..diagnosis.models import DiagnosisResult

logger = logging.getLogger(__name__)

# Playwright専用のスレッドプール（シングルスレッドで直列実行）
_playwright_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="playwright")


def _render_pdf_in_thread(html_content: str, pdf_path: str) -> None:
    """
    Playwrightを別スレッドで実行してPDFを生成する（asyncio対応用）。
    FastAPIのasyncioループ内からsync_playwrightを直接呼べないため、
    ThreadPoolExecutorを介して呼び出す。
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # HTMLを直接セット（外部への通信なし）
        page.set_content(html_content, wait_until="domcontentloaded")
        # Chart.jsが描画を完了するまで待機
        page.wait_for_timeout(1000)
        page.pdf(
            path=pdf_path,
            format="A4",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"}
        )
        browser.close()


class ReportGenerator(IReportGenerator):
    """
    Playwrightを使用した次世代PDFレポート生成エンジン。
    Web標準のモダンCSSとChart.jsによる美しいグラフをそのままPDF化します。
    """

    def __init__(
        self,
        output_dir: Path,
        template_dir: Optional[Path] = None
    ):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        if template_dir is None:
            template_dir = Path(__file__).parent / "templates"

        self._env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html"]),
        )
        logger.info(f"ReportGenerator (Playwright版) 初期化完了 (output_dir={output_dir})")

    def generate(self, diagnosis: DiagnosisResult, user_name: str) -> PDFReport:
        logger.info(f"PDF生成開始: session_id={diagnosis.session_id}")

        context = self._build_template_context(diagnosis, user_name)

        template = self._env.get_template("premium_report.html")
        html_content = template.render(**context)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_stem = f"voicecode_{diagnosis.session_id[:8]}_{timestamp}"
        pdf_filename = f"{file_stem}.pdf"
        html_filename = f"{file_stem}.html"
        pdf_path = self._output_dir / pdf_filename
        html_path = self._output_dir / html_filename

        # Web閲覧用にHTMLを保存
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # PlaywrightをThreadPoolExecutorで別スレッドで実行（asyncioループ対応）
        try:
            future = _playwright_executor.submit(_render_pdf_in_thread, html_content, str(pdf_path))
            future.result(timeout=120)  # 最大120秒待機
        except Exception as e:
            logger.error(f"Playwright PDF変換エラー: {e}")
            raise RuntimeError(f"PDFの生成に失敗しました: {e}")

        logger.info(f"PDF生成完了: {pdf_path}")

        return PDFReport(
            session_id=diagnosis.session_id,
            file_path=pdf_path,
            user_name=user_name,
        )


    def _build_template_context(self, diagnosis: DiagnosisResult, user_name: str) -> dict:
        big5 = diagnosis.big5_score

        big5_percent = {
            "openness": int(big5.openness * 100),
            "conscientiousness": int(big5.conscientiousness * 100),
            "extraversion": int(big5.extraversion * 100),
            "agreeableness": int(big5.agreeableness * 100),
            "neuroticism": int(big5.neuroticism * 100),
        }

        # 元素表示情報（固定）
        element_display = {
            "FIRE": {"name": "火", "emoji": "🔥"},
            "WATER": {"name": "水", "emoji": "🌊"},
            "WIND": {"name": "風", "emoji": "🌬️"},
            "EARTH": {"name": "地", "emoji": "🌍"},
            "SKY": {"name": "空", "emoji": "✨"},
        }

        dominant_element_data = []
        for elem_code in diagnosis.dominant_elements:
            if elem_code in element_display:
                dominant_element_data.append(element_display[elem_code])

        # パーソナルカラーをメインカラーとして使用（世界に一つだけの色）
        main_color = diagnosis.personal_color_hex or diagnosis.soul_color_hex or "#C0392B"

        return {
            "session_id": diagnosis.session_id,
            "user_name": user_name,
            "voice_code_id": diagnosis.voice_code_id,
            "diagnosed_at": diagnosis.diagnosed_at.strftime("%Y.%m.%d"),
            "score_data": big5_percent,
            "score_json": json.dumps(big5_percent),
            "element_color": main_color,
            # 色・周波数情報（NEW）
            "soul_color_name": diagnosis.soul_color_name,
            "soul_color_reading": diagnosis.soul_color_reading,
            "soul_color_hex": diagnosis.soul_color_hex,
            "personal_color_hex": diagnosis.personal_color_hex,
            "note_name": diagnosis.note_name,
            "note_frequency_hz": diagnosis.note_frequency_hz,
            "chakra_number": diagnosis.chakra_number,
            "chakra_name": diagnosis.chakra_name,
            "polarity": diagnosis.polarity,
            "archetype": {
                "name": diagnosis.archetype_name,
                "emoji": diagnosis.archetype_emoji,
                "tagline": diagnosis.archetype_tagline,
                "rarity": diagnosis.archetype_rarity,
                "dominant_elements": [e["name"] for e in dominant_element_data],
                "dominant_element_codes": diagnosis.dominant_elements,
                # 鑑定テキスト（新形式：テキスト直接格納）
                "hidden_talent": diagnosis.hidden_talent,
                "mission": diagnosis.mission,
                "shadow": diagnosis.shadow,
                "resonance": diagnosis.resonance,
                "universe_message": diagnosis.universe_message,
                "keys_to_bloom": diagnosis.keys_to_bloom,
            },
            # ========================================================
            # 音響生データ（科学的可視化グラフ用）
            # ========================================================
            "acoustic_json": json.dumps({
                # ピッチ（基本周波数）
                "f0_mean": round(diagnosis.f0_mean_hz, 1),
                "f0_std": round(diagnosis.f0_std_hz, 1),
                "f0_max": round(diagnosis.f0_max_hz, 1),
                "f0_min": round(diagnosis.f0_min_hz, 1),
                # 声の質指標（正規化0-100）
                "jitter_pct": round(min(diagnosis.jitter_local * 10, 100), 1),
                "shimmer_pct": round(min(diagnosis.shimmer_local * 10, 100), 1),
                "hnr_pct": round(min(diagnosis.hnr_db / 30 * 100, 100), 1),
                "hnr_score": round(min(diagnosis.hnr_db / 30 * 100, 100), 1),
                "jitter_score": round(max(0, 100 - min(diagnosis.jitter_local * 10, 100)), 1),
                "shimmer_score": round(max(0, 100 - min(diagnosis.shimmer_local * 10, 100)), 1),
                # エネルギー・リズム
                "rms_energy_pct": round(min(diagnosis.rms_energy * 500, 100), 1),
                "speech_rate_pct": round(min(diagnosis.speech_rate * 10, 100), 1),
                "pause_ratio_pct": round(diagnosis.pause_ratio * 100, 1),
                # スペクトル特性
                "spectral_centroid": round(diagnosis.spectral_centroid_mean, 0),
                # フォルマント（母音空間）
                "f1": round(diagnosis.f1_mean_hz, 0),
                "f2": round(diagnosis.f2_mean_hz, 0),
                # MFCC（最初の6係数を正規化して表示）
                "mfcc": [round(v, 2) for v in (diagnosis.mfcc_mean[:6] if diagnosis.mfcc_mean else [0]*6)],
            }),
        }

