"""
LINE Webhook APIエンドポイント

LINEプラットフォームからのWebhookリクエストを受け取り、
署名検証後にイベントハンドラーへ振り分けます。
"""

import logging
import os
import json

from fastapi import APIRouter, Request, Header, HTTPException
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks.models import (
    FollowEvent,
    MessageEvent,
    AudioMessageContent,
    TextMessageContent,
)

from ..line import client as line_client
from ..line import handler as line_handler

logger = logging.getLogger(__name__)
router = APIRouter()

_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")


@router.post("/line/webhook")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(alias="X-Line-Signature", default="")
):
    """
    LINE Webhook エンドポイント。

    LINEプラットフォームからPOSTリクエストを受け取り、
    署名を検証してイベントを処理します。

    LINE Developers Console での設定:
        Webhook URL: https://あなたのドメイン/api/v1/line/webhook
    """
    body = await request.body()
    body_str = body.decode("utf-8")
    logger.info("LINE Webhook 受信")

    # linebot.v3 の WebhookParser で署名検証 + イベントパースを同時に行う
    parser = WebhookParser(_CHANNEL_SECRET)
    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        logger.warning("LINE Webhook: 署名検証失敗")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"LINE Webhook パースエラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    # イベントの振り分け
    for event in events:
        try:
            # フォローイベント
            if isinstance(event, FollowEvent):
                await line_handler.handle_follow(event)

            # メッセージイベント
            elif isinstance(event, MessageEvent):
                if isinstance(event.message, AudioMessageContent):
                    # 音声メッセージ → 解析パイプライン起動
                    await line_handler.handle_audio_message(event)
                elif isinstance(event.message, TextMessageContent):
                    # テキストメッセージ → ガイド等
                    await line_handler.handle_text_message(event)
                else:
                    # その他（画像・スタンプ等）→ 案内テキスト
                    logger.info(f"未対応メッセージ種別: {type(event.message).__name__}")
                    line_client.reply_text(
                        reply_token=event.reply_token,
                        text="🎤 音声メッセージを送ってください。\n声を分析して、あなたの魂のブループリントをお届けします。"
                    )
        except Exception as e:
            logger.error(f"イベント処理エラー: {e}", exc_info=True)

    return {"status": "ok"}
