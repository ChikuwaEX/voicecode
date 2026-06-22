"""
Stripe 決済 APIエンドポイント

支払いフロー:
  1. POST /api/v1/payment/create-session  → Stripe Checkout URLを返す
  2. ユーザーがStripeで支払い
  3. POST /api/v1/payment/webhook          → 支払い完了を確認してセッションを解放
  4. GET  /api/v1/report/{id}/view         → レポートが閲覧可能になる
"""

import logging
import os
import json

import stripe
from fastapi import APIRouter, Request, Header, HTTPException
from fastapi.responses import JSONResponse

from ..session.store import get_store

logger = logging.getLogger(__name__)
router = APIRouter()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
PRICE_AMOUNT = int(os.getenv("DIAGNOSIS_PRICE_YEN", "3000"))
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


@router.post("/payment/create-session")
async def create_checkout_session(request: Request):
    """
    Stripe Checkout Sessionを作成してURLを返す。
    フロントエンドからsession_idをPOSTして呼び出す。
    """
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="決済システムが設定されていません")

    try:
        body = await request.json()
        session_id = body.get("session_id")
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id が必要です")

        store = get_store()
        session_data = store.get(session_id)
        if not session_data:
            raise HTTPException(status_code=404, detail="診断セッションが見つかりません")

        if session_data.is_paid:
            # すでに支払い済みならレポートURLを直接返す
            return JSONResponse({
                "already_paid": True,
                "report_url": f"{BASE_URL}/api/v1/report/{session_id}/view"
            })

        # Stripe Checkout Session 作成
        checkout = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {
                        "name": "VOICECODE 声紋スピリチュアル診断レポート",
                        "description": f"12ページ プレミアムレポート / アーキタイプ: {session_data.archetype_name or '解析済み'}",
                        "images": [],
                    },
                    "unit_amount": PRICE_AMOUNT,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{BASE_URL}/app?paid=true&session_id={session_id}",
            cancel_url=f"{BASE_URL}/app?cancelled=true&session_id={session_id}",
            metadata={"voicecode_session_id": session_id},
            locale="ja",
        )

        logger.info(f"Stripe Checkout Session作成: {checkout.id} / session_id={session_id}")
        return JSONResponse({"checkout_url": checkout.url})

    except stripe.StripeError as e:
        logger.error(f"Stripe エラー: {e}")
        raise HTTPException(status_code=500, detail=f"決済エラー: {str(e)}")
    except Exception as e:
        logger.error(f"支払いセッション作成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="内部エラーが発生しました")


@router.post("/payment/webhook")
async def stripe_webhook(  # noqa: C901
    request: Request,
    stripe_signature: str = Header(alias="stripe-signature", default="")
):
    """
    Stripe Webhook エンドポイント。
    支払い完了イベントを受け取り、セッションを「支払い済み」にする。

    Stripe Dashboard での設定:
        Webhook URL: https://あなたのドメイン/api/v1/payment/webhook
        イベント: checkout.session.completed
    """
    payload = await request.body()

    if not STRIPE_WEBHOOK_SECRET:
        # 開発環境では署名検証をスキップ
        logger.warning("STRIPE_WEBHOOK_SECRET 未設定 — 署名検証をスキップします（開発モード）")
        try:
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, STRIPE_WEBHOOK_SECRET
            )
        except stripe.SignatureVerificationError:
            logger.warning("Stripe Webhook: 署名検証失敗")
            raise HTTPException(status_code=400, detail="Invalid signature")

    # checkout.session.completed イベントを処理
    if event["type"] == "checkout.session.completed":
        checkout_session = event["data"]["object"]
        voicecode_session_id = checkout_session.get("metadata", {}).get("voicecode_session_id")
        payment_intent_id = checkout_session.get("payment_intent", "")
        checkout_session_id = checkout_session.get("id", "")

        if voicecode_session_id:
            store = get_store()
            success = store.mark_paid(
                session_id=voicecode_session_id,
                stripe_checkout_session_id=checkout_session_id,
                stripe_payment_intent_id=payment_intent_id,
            )
            if success:
                logger.info(f"支払い確認完了: session_id={voicecode_session_id}")
                # 決済完了後に LINE ユーザーへフルレポートをプッシュ
                await _push_report_to_line(voicecode_session_id)
            else:
                logger.warning(f"セッションが見つかりません: session_id={voicecode_session_id}")

    return JSONResponse({"status": "ok"})


async def _push_report_to_line(session_id: str) -> None:
    """
    決済完了後、SessionStore から LINE user_id を取得してレポートをプッシュする。
    """
    try:
        store = get_store()
        session_data = store.get(session_id)
        if not session_data or not session_data.line_user_id:
            logger.warning(f"LINE user_id が見つかりません: session_id={session_id}")
            return

        from ..line import client as line_client

        view_url = f"{BASE_URL}/api/v1/report/{session_id}/view"
        download_url = f"{BASE_URL}/api/v1/report/{session_id}/download"
        share_url = f"{BASE_URL}/api/v1/share/{session_id}"

        flex = line_client.build_payment_complete_flex(
            archetype_name=session_data.archetype_name or "",
            report_view_url=view_url,
            report_download_url=download_url,
            share_url=share_url,
        )

        line_client.push_flex(
            user_id=session_data.line_user_id,
            alt_text="✦ お支払い完了！プレミアムレポートが届きました",
            flex_container=flex,
        )
        logger.info(f"決済完了レポートをLINEに送信: user_id={session_data.line_user_id}")

    except Exception as e:
        logger.error(f"LINE レポートプッシュエラー: {e}", exc_info=True)


@router.get("/payment/line-success")
async def payment_line_success(session_id: str = ""):
    """
    Stripe 決済完了後のリダイレクト先。
    ユーザーに「LINEに戻ってレポートを確認してください」と案内する。
    """
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>お支払い完了 | VOICECODE</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #08080F; color: #E8E0FF;
      font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif;
      min-height: 100vh; display: flex; flex-direction: column;
      align-items: center; justify-content: center; padding: 24px;
      text-align: center;
    }
    .icon { font-size: 72px; margin-bottom: 24px; }
    .title { font-size: 22px; font-weight: bold; color: #D4AF37; margin-bottom: 12px; }
    .body { font-size: 15px; color: #9090B0; line-height: 1.7; margin-bottom: 32px; }
    .btn {
      display: inline-block; padding: 14px 32px; background: #D4AF37;
      color: #08080F; font-size: 16px; font-weight: bold;
      border-radius: 8px; text-decoration: none; margin-bottom: 16px;
    }
    .sub { font-size: 12px; color: #4A4A6A; margin-top: 24px; }
    .brand { color: #D4AF37; letter-spacing: 5px; font-size: 11px; margin-bottom: 32px; }
  </style>
</head>
<body>
  <div class="brand">V O I C E C O D E</div>
  <div class="icon">🎉</div>
  <div class="title">お支払いが完了しました！</div>
  <div class="body">
    ありがとうございます。<br>
    LINEに戻ると、プレミアムレポートの<br>
    リンクが届いています。
  </div>
  <a href="https://line.me/R/" class="btn">LINE を開く</a>
  <div class="sub">VOICECODE — あなたの声に、宇宙の答えがある。</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/payment/line-cancel")
async def payment_line_cancel(session_id: str = ""):
    """
    Stripe 決済キャンセル後のリダイレクト先。
    """
    from fastapi.responses import HTMLResponse
    html = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>お支払いキャンセル | VOICECODE</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      background: #08080F; color: #E8E0FF;
      font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif;
      min-height: 100vh; display: flex; flex-direction: column;
      align-items: center; justify-content: center; padding: 24px;
      text-align: center;
    }
    .icon { font-size: 72px; margin-bottom: 24px; }
    .title { font-size: 22px; font-weight: bold; color: #9090B0; margin-bottom: 12px; }
    .body { font-size: 15px; color: #7A7A9A; line-height: 1.7; margin-bottom: 32px; }
    .btn {
      display: inline-block; padding: 14px 32px; background: #2A2A4A;
      color: #C8C0E0; font-size: 16px; font-weight: bold;
      border-radius: 8px; text-decoration: none; margin-bottom: 16px;
    }
    .sub { font-size: 12px; color: #4A4A6A; margin-top: 24px; }
    .brand { color: #D4AF37; letter-spacing: 5px; font-size: 11px; margin-bottom: 32px; }
  </style>
</head>
<body>
  <div class="brand">V O I C E C O D E</div>
  <div class="icon">🌙</div>
  <div class="title">お支払いはキャンセルされました</div>
  <div class="body">
    お支払いはキャンセルされました。<br>
    LINEに戻ると、もう一度お試しいただけます。
  </div>
  <a href="https://line.me/R/" class="btn">LINE に戻る</a>
  <div class="sub">VOICECODE — あなたの声に、宇宙の答えがある。</div>
</body>
</html>"""
    return HTMLResponse(content=html)


@router.get("/payment/status/{session_id}")
async def payment_status(session_id: str):
    """
    フロントエンドが支払い状態をポーリングするためのエンドポイント。
    """
    store = get_store()
    data = store.get(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="セッションが見つかりません")

    return JSONResponse({
        "session_id": session_id,
        "is_paid": data.is_paid,
        "report_url": f"{BASE_URL}/api/v1/report/{session_id}/view" if data.is_paid else None,
    })
