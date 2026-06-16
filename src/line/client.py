"""
LINE Messaging API クライアントラッパー

LINE SDK を薄くラップし、Flex Messageの組み立てと送信を担当します。
"""

import logging
import os
from typing import Optional

from linebot.v3 import WebhookHandler
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer,
)
from linebot.v3.messaging.models import (
    FlexBubble,
    FlexBox,
    FlexText,
    FlexButton,
    FlexImage,
    URIAction,
    PostbackAction,
    MessageAction,
)

logger = logging.getLogger(__name__)

_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
_BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def get_handler() -> WebhookHandler:
    """Webhookハンドラを返す（署名検証用）"""
    return WebhookHandler(_CHANNEL_SECRET)


def get_messaging_api() -> MessagingApi:
    """MessagingApi インスタンスを返す"""
    configuration = Configuration(access_token=_CHANNEL_ACCESS_TOKEN)
    api_client = ApiClient(configuration)
    return MessagingApi(api_client)


# ==============================================================
# メッセージ送信ヘルパー
# ==============================================================

def reply_text(reply_token: str, text: str) -> None:
    """テキストメッセージで返信"""
    try:
        api = get_messaging_api()
        api.reply_message(ReplyMessageRequest(
            reply_token=reply_token,
            messages=[TextMessage(text=text)]
        ))
    except Exception as e:
        logger.error(f"LINE reply_text エラー: {e}")


def reply_flex(reply_token: str, alt_text: str, flex_container: dict) -> None:
    """Flexメッセージで返信"""
    try:
        api = get_messaging_api()
        api.reply_message(ReplyMessageRequest(
            reply_token=reply_token,
            messages=[FlexMessage(
                alt_text=alt_text,
                contents=FlexContainer.from_dict(flex_container)
            )]
        ))
    except Exception as e:
        logger.error(f"LINE reply_flex エラー: {e}")


def push_text(user_id: str, text: str) -> None:
    """テキストメッセージをプッシュ送信"""
    try:
        api = get_messaging_api()
        api.push_message(PushMessageRequest(
            to=user_id,
            messages=[TextMessage(text=text)]
        ))
    except Exception as e:
        logger.error(f"LINE push_text エラー: {e}")


def push_flex(user_id: str, alt_text: str, flex_container: dict) -> None:
    """Flexメッセージをプッシュ送信"""
    try:
        api = get_messaging_api()
        api.push_message(PushMessageRequest(
            to=user_id,
            messages=[FlexMessage(
                alt_text=alt_text,
                contents=FlexContainer.from_dict(flex_container)
            )]
        ))
    except Exception as e:
        logger.error(f"LINE push_flex エラー: {e}")


# ==============================================================
# Flex Messageテンプレート
# ==============================================================

def build_welcome_flex() -> dict:
    """フォロー時の歓迎Flexメッセージ"""
    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#08080F",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": "V O I C E C O D E",
                    "color": "#D4AF37",
                    "size": "xs",
                    "align": "center",
                    "letterSpacing": "6px",
                    "weight": "bold"
                },
                {
                    "type": "text",
                    "text": "あなたの声に、\n宇宙の答えがある。",
                    "color": "#E8E0FF",
                    "size": "lg",
                    "align": "center",
                    "weight": "bold",
                    "wrap": True,
                    "margin": "md"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "20px",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "友達追加ありがとうございます✨\nVOICECODEは、あなたの声の周波数を科学的に分析し、魂の使命・才能・運命パターンをプレミアムレポートでお届けするサービスです。",
                    "color": "#9090B0",
                    "size": "sm",
                    "wrap": True
                },
                {
                    "type": "separator",
                    "margin": "md",
                    "color": "#D4AF3740"
                },
                {
                    "type": "text",
                    "text": "📋 診断の流れ",
                    "color": "#D4AF37",
                    "size": "sm",
                    "weight": "bold",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "① このトークに「声」を送る\n② 約30秒で音響解析完了\n③ 12ページのプレミアムレポートを受け取る",
                    "color": "#C8C0E0",
                    "size": "sm",
                    "wrap": True
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "🎤 今すぐ声を送って診断する",
                        "text": "診断を始める"
                    },
                    "style": "primary",
                    "color": "#D4AF37",
                    "height": "sm"
                },
                {
                    "type": "text",
                    "text": "またはこのトークに直接「音声メッセージ」を送るだけでOK",
                    "color": "#4A4A6A",
                    "size": "xxs",
                    "align": "center",
                    "margin": "sm",
                    "wrap": True
                }
            ]
        }
    }


def build_analyzing_flex() -> dict:
    """解析中メッセージ"""
    return {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "24px",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "🔮",
                    "size": "3xl",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": "声紋を解析中...",
                    "color": "#D4AF37",
                    "size": "lg",
                    "align": "center",
                    "weight": "bold"
                },
                {
                    "type": "text",
                    "text": "周波数・ピッチ・声帯特性を分析しています。\n少々お待ちください（約30秒）",
                    "color": "#7A7A9A",
                    "size": "sm",
                    "align": "center",
                    "wrap": True,
                    "margin": "md"
                }
            ]
        }
    }


def build_result_flex(
    archetype_name: str,
    archetype_emoji: str,
    voice_code_id: str,
    report_view_url: str,
    report_download_url: str,
    rarity: str,
) -> dict:
    """診断結果Flexメッセージ"""
    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#08080F",
            "paddingAll": "20px",
            "contents": [
                {
                    "type": "text",
                    "text": "V O I C E C O D E",
                    "color": "#D4AF37",
                    "size": "xxs",
                    "align": "center",
                    "letterSpacing": "4px"
                },
                {
                    "type": "text",
                    "text": "✦ 声紋解析 完了 ✦",
                    "color": "#E8E0FF",
                    "size": "sm",
                    "align": "center",
                    "margin": "sm"
                }
            ]
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "24px",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": archetype_emoji,
                    "size": "5xl",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": archetype_name,
                    "color": "#F0D060",
                    "size": "xl",
                    "align": "center",
                    "weight": "bold",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": rarity,
                    "color": "#7A7A9A",
                    "size": "xs",
                    "align": "center"
                },
                {
                    "type": "separator",
                    "margin": "lg",
                    "color": "#D4AF3740"
                },
                {
                    "type": "box",
                    "layout": "horizontal",
                    "margin": "lg",
                    "contents": [
                        {
                            "type": "text",
                            "text": "声紋コード",
                            "color": "#4A4A6A",
                            "size": "xs",
                            "flex": 1
                        },
                        {
                            "type": "text",
                            "text": voice_code_id,
                            "color": "#D4AF37",
                            "size": "xs",
                            "align": "end",
                            "flex": 2,
                            "weight": "bold"
                        }
                    ]
                },
                {
                    "type": "text",
                    "text": "12ページのプレミアムレポートが生成されました。科学的音響分析・チャクラ診断・30日間プラン等を収録しています。",
                    "color": "#9090B0",
                    "size": "sm",
                    "wrap": True,
                    "margin": "lg"
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "16px",
            "spacing": "sm",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "✨ プレミアムレポートを見る",
                        "uri": report_view_url
                    },
                    "style": "primary",
                    "color": "#D4AF37",
                    "height": "sm"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "uri",
                        "label": "📄 PDFをダウンロード",
                        "uri": report_download_url
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "sm"
                }
            ]
        }
    }


def build_error_flex(message: str = "解析に失敗しました") -> dict:
    """エラーFlexメッセージ"""
    return {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "24px",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "⚠️",
                    "size": "3xl",
                    "align": "center"
                },
                {
                    "type": "text",
                    "text": "解析エラー",
                    "color": "#ff6b6b",
                    "size": "lg",
                    "align": "center",
                    "weight": "bold"
                },
                {
                    "type": "text",
                    "text": message,
                    "color": "#7A7A9A",
                    "size": "sm",
                    "align": "center",
                    "wrap": True,
                    "margin": "md"
                },
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "🔄 もう一度試す",
                        "text": "診断を始める"
                    },
                    "style": "secondary",
                    "height": "sm",
                    "margin": "lg"
                }
            ]
        }
    }


def build_guide_flex() -> dict:
    """使い方ガイドFlexメッセージ"""
    return {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "20px",
            "spacing": "md",
            "contents": [
                {
                    "type": "text",
                    "text": "📖 使い方ガイド",
                    "color": "#D4AF37",
                    "size": "md",
                    "weight": "bold"
                },
                {
                    "type": "separator",
                    "color": "#D4AF3740",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": "STEP 1 — 声を送る",
                    "color": "#F0D060",
                    "size": "sm",
                    "weight": "bold",
                    "margin": "lg"
                },
                {
                    "type": "text",
                    "text": "このトークで「＋」ボタン → 「音声メッセージ」を選択。15秒〜3分の声を送ってください。",
                    "color": "#9090B0",
                    "size": "sm",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": "STEP 2 — 解析を待つ",
                    "color": "#F0D060",
                    "size": "sm",
                    "weight": "bold",
                    "margin": "lg"
                },
                {
                    "type": "text",
                    "text": "声を受信すると自動で解析が始まります。約30秒でレポートが届きます。",
                    "color": "#9090B0",
                    "size": "sm",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": "STEP 3 — レポートを受け取る",
                    "color": "#F0D060",
                    "size": "sm",
                    "weight": "bold",
                    "margin": "lg"
                },
                {
                    "type": "text",
                    "text": "アーキタイプ・チャクラ診断・30日間プランなど12ページのプレミアムレポートが届きます。",
                    "color": "#9090B0",
                    "size": "sm",
                    "wrap": True
                }
            ]
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#0D0D1A",
            "paddingAll": "16px",
            "contents": [
                {
                    "type": "button",
                    "action": {
                        "type": "message",
                        "label": "🎤 声を送って診断を始める",
                        "text": "診断を始める"
                    },
                    "style": "primary",
                    "color": "#D4AF37",
                    "height": "sm"
                }
            ]
        }
    }
