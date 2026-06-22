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
from typing import Optional

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
# シェアリンクを返すキーワード
_SHARE_KEYWORDS = {"シェアする", "シェア", "share", "共有", "シェアリンク"}
# 10タイプ一覧を返すキーワード
_TYPES_KEYWORDS = {"10の声のタイプ", "10タイプ", "声のタイプ", "タイプ一覧", "アーキタイプ"}


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

    # シェアキーワード → 直近のセッションのシェアURLを返す
    if any(kw in text for kw in _SHARE_KEYWORDS):
        await _handle_share_request(event)
        return

    # 10タイプキーワード → アーキタイプ一覧Flexを返す
    if any(kw in text for kw in _TYPES_KEYWORDS):
        line_client.reply_flex(
            reply_token=event.reply_token,
            alt_text="VOICECODEの10の声のタイプ",
            flex_container=line_client.build_archetypes_list_flex()
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
# 内部処理：シェアリクエスト
# ==============================================================

async def _handle_share_request(event: MessageEvent) -> None:
    """
    ユーザーの直近のセッションIDを取得してシェアURLを返す。
    診断履歴がない場合は案内を送る。
    """
    user_id = event.source.user_id
    base_url = _get_base_url()

    try:
        from ..session.store import get_store
        store = get_store()
        sessions = store.get_all()
        # このユーザーの最新セッションを探す
        user_sessions = [s for s in sessions if s.get("line_user_id") == user_id]
    except Exception:
        user_sessions = []

    if not user_sessions:
        line_client.reply_text(
            reply_token=event.reply_token,
            text=(
                "📣 シェアするには、まず声紋診断を受けてください！\n\n"
                "音声メッセージを送るか、下のボタンから録音できます。\n"
                f"▶ {base_url}/record"
            )
        )
        return

    # 最新のセッションのシェアURL
    latest = user_sessions[-1]
    session_id = latest.get("session_id", "")
    archetype_name = latest.get("archetype_name", "あなたのアーキタイプ")
    share_url = f"{base_url}/share/{session_id}"

    line_client.reply_text(
        reply_token=event.reply_token,
        text=(
            f"📣 あなたのシェアページはこちらです！\n\n"
            f"✦ {archetype_name}\n\n"
            f"🔗 {share_url}\n\n"
            "このURLをSNSでシェアすると、OGP画像付きで表示されます。\n"
            "Instagramストーリー用の縦長画像もダウンロードできます！"
        )
    )


# ==============================================================
# 内部処理：音声ダウンロード→解析→診断→レポート→プッシュ
# ==============================================================

def _create_stripe_checkout_url(
    session_id: str,
    archetype_name: str,
    base_url: str,
) -> Optional[str]:
    """
    Stripe Checkout Session を作成して URL を返す。
    STRIPE_SECRET_KEY が未設定の場合は None を返す（フリーモードにフォールバック）。
    """
    import stripe as stripe_sdk

    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not secret_key:
        return None

    price_yen = int(os.getenv("DIAGNOSIS_PRICE_YEN", "3000"))
    stripe_sdk.api_key = secret_key

    try:
        checkout = stripe_sdk.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {
                        "name": "VOICECODE 声紋スピリチュアル診断レポート",
                        "description": (
                            f"12ページ プレミアムレポート / アーキタイプ: {archetype_name}\n"
                            "チャクラ診断・魂の使命・隠れた才能・30日間プランを収録"
                        ),
                    },
                    "unit_amount": price_yen,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{base_url}/api/v1/payment/line-success?session_id={session_id}",
            cancel_url=f"{base_url}/api/v1/payment/line-cancel?session_id={session_id}",
            metadata={"voicecode_session_id": session_id},
            locale="ja",
        )
        logger.info(f"Stripe Checkout作成完了: {checkout.id}")
        return checkout.url
    except Exception as e:
        logger.error(f"Stripe Checkout作成エラー: {e}")
        return None


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

        # STEP 5: セッションストアに登録（決済後のレポート配信に使用）
        from ..session.store import get_store as _get_session_store
        html_path = report.file_path.with_suffix(".html")
        _get_session_store().create(
            session_id=session_id,
            line_user_id=user_id,
            archetype_name=diagnosis.archetype_name,
            report_html_path=str(html_path),
            report_pdf_path=str(report.file_path),
        )

        # STEP 6: Stripe設定に応じて送信フローを切り替え
        base_url = _get_base_url()
        view_url = f"{base_url}/api/v1/report/{session_id}/view"
        download_url = f"{base_url}/api/v1/report/{session_id}/download"
        share_url = f"{base_url}/api/v1/share/{session_id}"

        checkout_url = _create_stripe_checkout_url(
            session_id=session_id,
            archetype_name=diagnosis.archetype_name,
            base_url=base_url,
        )

        price_yen = int(os.getenv("DIAGNOSIS_PRICE_YEN", "3000"))

        if checkout_url:
            # --- マネタイズモード: テーザー + 決済ボタン ---
            flex = line_client.build_payment_prompt_flex(
                archetype_name=diagnosis.archetype_name,
                archetype_emoji=diagnosis.archetype_emoji,
                soul_color_hex=getattr(diagnosis, 'soul_color_hex', '#D4AF37'),
                tagline=getattr(diagnosis, 'archetype_tagline', ''),
                rarity=diagnosis.archetype_rarity,
                checkout_url=checkout_url,
                voice_code_id=diagnosis.voice_code_id,
                note_name=getattr(diagnosis, 'note_name', ''),
                note_frequency_hz=getattr(diagnosis, 'note_frequency_hz', 0.0),
                price_yen=price_yen,
            )
            color_name = getattr(diagnosis, 'soul_color_name', '')
            alt = f"✦ 声紋解析完了｜{diagnosis.archetype_name}｜¥{price_yen:,}でレポートを受け取る"
        else:
            # --- フリーモード（Stripe未設定）: フルレポートを即送信 ---
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
                share_url=share_url,
            )
            color_name = getattr(diagnosis, 'soul_color_name', '')
            alt = f"✦ 声紋リーディング完了｜あなたの声の色は「{color_name}」— {diagnosis.archetype_name}"

        line_client.push_flex(user_id=user_id, alt_text=alt, flex_container=flex)

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
