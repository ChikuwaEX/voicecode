"""
LINE Webhook イベントハンドラー

LINEから届くイベント（フォロー・音声・テキスト等）を処理します。
音声メッセージを受信した場合は、音声解析→診断→レポート生成まで
完全にLINE内で完結させます。
"""

import logging
import os
import uuid
import asyncio
import httpx
from pathlib import Path

from linebot.v3.webhooks.models import (
    FollowEvent,
    MessageEvent,
    AudioMessageContent,
    TextMessageContent,
)

from . import client as line_client
from ..audio.models import AudioFile

logger = logging.getLogger(__name__)

def _get_base_url() -> str:
    """BASE_URLを毎回動的に取得（.env更新後の再起動不要）"""
    return os.getenv("BASE_URL", "http://localhost:8000")

_UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))

# ガイドを返すキーワード
_GUIDE_KEYWORDS = {"使い方", "ガイド", "help", "へるぷ", "方法", "診断を始める", "診断"}


async def handle_follow(event: FollowEvent) -> None:
    """
    フォローイベント処理。
    歓迎Flexメッセージを返信する。
    """
    user_id = event.source.user_id
    logger.info(f"フォローイベント: user_id={user_id}")

    try:
        flex = line_client.build_welcome_flex()
        line_client.reply_flex(
            reply_token=event.reply_token,
            alt_text="VOICECODEへようこそ！あなたの声で魂の診断を受けましょう。",
            flex_container=flex
        )
    except Exception as e:
        logger.error(f"フォロー処理エラー: {e}")


async def handle_audio_message(event: MessageEvent) -> None:
    """
    音声メッセージイベント処理。
    LINE上で音声を受け取り、解析→診断→レポート生成→結果返信まで完結させる。
    """
    user_id = event.source.user_id
    message_id = event.message.id
    logger.info(f"音声受信: user_id={user_id}, message_id={message_id}")

    # ① 「解析中」Flexメッセージを即座に返信
    line_client.reply_flex(
        reply_token=event.reply_token,
        alt_text="声紋を解析中です。約30秒お待ちください...",
        flex_container=line_client.build_analyzing_flex()
    )

    # ② 非同期で解析→診断→レポート生成→プッシュ送信
    asyncio.create_task(
        _process_audio_and_push(user_id=user_id, message_id=message_id)
    )


async def handle_text_message(event: MessageEvent) -> None:
    """
    テキストメッセージイベント処理。
    ガイド系キーワードにはガイドFlexを返す。
    それ以外には簡単な案内テキストを返す。
    """
    text = event.message.text.strip()
    logger.info(f"テキスト受信: '{text}'")

    # ガイドキーワードの判定
    if any(kw in text for kw in _GUIDE_KEYWORDS):
        line_client.reply_flex(
            reply_token=event.reply_token,
            alt_text="VOICECODEの使い方ガイド",
            flex_container=line_client.build_guide_flex()
        )
        return

    # その他のテキスト → シンプルな案内
    line_client.reply_text(
        reply_token=event.reply_token,
        text=(
            "🎤 声を送るだけで診断できます！\n\n"
            "このトークに「音声メッセージ」を送ってください。\n"
            "自動で声紋を解析し、12ページのプレミアムレポートをお届けします。\n\n"
            "「使い方」と送ると詳しいガイドを表示します。"
        )
    )


# ==============================================================
# 内部処理：音声ダウンロード→解析→診断→レポート→プッシュ
# ==============================================================

async def _process_audio_and_push(user_id: str, message_id: str) -> None:
    """
    LINEの音声メッセージを処理してレポートを生成し、プッシュ送信する。
    """
    session_id = str(uuid.uuid4())
    audio_path = _UPLOAD_DIR / f"line_{session_id}.m4a"

    try:
        # STEP 1: LINEサーバーから音声ファイルをダウンロード
        logger.info(f"音声ダウンロード開始: message_id={message_id}")
        await _download_line_audio(message_id=message_id, save_path=audio_path)
        logger.info(f"音声ダウンロード完了: {audio_path}")

        # STEP 2: 音声解析
        audio_file = AudioFile(
            file_path=audio_path,
            format="m4a",
            session_id=session_id,
        )
        from ..audio.analyzer import AudioAnalyzer
        analyzer = AudioAnalyzer()
        analysis = await asyncio.get_event_loop().run_in_executor(
            None, analyzer.analyze, audio_file
        )
        logger.info(f"解析完了: F0={analysis.f0_mean_hz:.1f}Hz")

        # 尺チェック（15秒未満はエラー）
        if analysis.analysis_duration_sec < 15:
            line_client.push_flex(
                user_id=user_id,
                alt_text="音声が短すぎます",
                flex_container=line_client.build_error_flex(
                    "音声が短すぎます（15秒以上必要です）。\n"
                    "もう少し長めの声を送ってみてください。"
                )
            )
            return

        # STEP 3: スピリチュアル診断
        from ..diagnosis.engine import DiagnosisEngine
        engine = DiagnosisEngine()
        diagnosis = engine.diagnose(analysis)
        logger.info(f"診断完了: archetype={diagnosis.archetype_name}")

        # STEP 4: レポート生成（PDF + HTML）—— 同期関数なのでexecutorで実行
        from ..config import OUTPUT_DIR
        from ..report.generator import ReportGenerator
        generator = ReportGenerator(output_dir=OUTPUT_DIR)
        report = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: generator.generate(diagnosis=diagnosis, user_name="ゲスト")
        )
        logger.info(f"レポート生成完了: {report.file_path}")

        # STEP 5: レポートURLを組み立てて結果をプッシュ
        base_url = _get_base_url()
        view_url = f"{base_url}/api/v1/report/{session_id}/view"
        download_url = f"{base_url}/api/v1/report/{session_id}/download"

        flex = line_client.build_result_flex(
            archetype_name=diagnosis.archetype_name,
            archetype_emoji=diagnosis.archetype_emoji,
            voice_code_id=diagnosis.voice_code_id,
            report_view_url=view_url,
            report_download_url=download_url,
            rarity=diagnosis.archetype_rarity,
            soul_color_name=getattr(diagnosis, 'soul_color_name', ''),
            soul_color_hex=getattr(diagnosis, 'soul_color_hex', '#D4AF37'),
            personal_color_hex=getattr(diagnosis, 'personal_color_hex', '#D4AF37'),
            tagline=getattr(diagnosis, 'archetype_tagline', ''),
            note_name=getattr(diagnosis, 'note_name', ''),
            note_frequency_hz=getattr(diagnosis, 'note_frequency_hz', 0.0),
        )
        # 色名を含めた新しいメッセージ形式
        color_name = getattr(diagnosis, 'soul_color_name', '')
        alt = f"✦ 声紋リーディング完了｜あなたの声の色は「{color_name}」— {diagnosis.archetype_name}"
        line_client.push_flex(
            user_id=user_id,
            alt_text=alt,
            flex_container=flex
        )

    except Exception as e:
        logger.error(f"音声処理エラー: {e}", exc_info=True)
        line_client.push_flex(
            user_id=user_id,
            alt_text="解析中にエラーが発生しました",
            flex_container=line_client.build_error_flex(
                f"解析中にエラーが発生しました。\n"
                f"もう一度音声を送ってみてください。\n\n"
                f"（エラー: {str(e)[:50]}）"
            )
        )
    finally:
        # 音声ファイルをクリーンアップ
        try:
            if audio_path.exists():
                audio_path.unlink()
        except Exception:
            pass


async def _download_line_audio(message_id: str, save_path: Path) -> None:
    """
    LINE Messaging APIから音声コンテンツをダウンロードして保存する。
    """
    from .client import _CHANNEL_ACCESS_TOKEN

    save_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"https://api-data.line.me/v2/bot/message/{message_id}/content"
    headers = {"Authorization": f"Bearer {_CHANNEL_ACCESS_TOKEN}"}

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            with open(save_path, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
