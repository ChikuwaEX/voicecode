"""
SNSシェア用APIルーター

GET /api/v1/share/{session_id}/ogp.png   — OGP画像（1200×630）
GET /api/v1/share/{session_id}/story.png — Instagramストーリー画像（1080×1920）
GET /share/{session_id}                  — OGP対応シェアランディングページ（main.pyで登録）
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .. import config
from ..diagnosis.models import DiagnosisResult, Big5Score

logger = logging.getLogger(__name__)
router = APIRouter()


# ==============================================================
# 診断JSONからDiagnosisResultを復元
# ==============================================================

def _load_diagnosis(session_id: str) -> DiagnosisResult:
    """
    outputs/ ディレクトリから診断JSONを読み込み DiagnosisResult を復元する。
    """
    session_prefix = session_id[:8]
    candidates = sorted(config.OUTPUT_DIR.glob(f"voicecode_{session_prefix}_*.json"))
    if not candidates:
        raise HTTPException(status_code=404, detail=f"診断データが見つかりません: {session_id}")

    with open(candidates[-1], "r", encoding="utf-8") as f:
        data = json.load(f)

    big5_raw = data.get("big5_score", {})
    big5 = Big5Score(
        openness=big5_raw.get("openness", 0.5),
        conscientiousness=big5_raw.get("conscientiousness", 0.5),
        extraversion=big5_raw.get("extraversion", 0.5),
        agreeableness=big5_raw.get("agreeableness", 0.5),
        neuroticism=big5_raw.get("neuroticism", 0.5),
    )

    note = data.get("note", {})
    soul_color = data.get("soul_color", {})
    chakra = data.get("chakra", {})

    diagnosed_at_raw = data.get("diagnosed_at", "")
    try:
        diagnosed_at = datetime.fromisoformat(diagnosed_at_raw)
    except Exception:
        diagnosed_at = datetime.now()

    return DiagnosisResult(
        session_id=data.get("session_id", session_id),
        big5_score=big5,
        archetype_code=data.get("archetype_code", ""),
        archetype_name=data.get("archetype_name", ""),
        archetype_emoji=data.get("archetype_emoji", ""),
        archetype_tagline=data.get("archetype_tagline", ""),
        archetype_rarity=data.get("archetype_rarity", ""),
        soul_color_name=soul_color.get("name", ""),
        soul_color_reading=soul_color.get("reading", ""),
        soul_color_hex=soul_color.get("hex", "#D4AF37"),
        personal_color_hex=soul_color.get("personal_hex", "#D4AF37"),
        note_name=note.get("name", ""),
        note_frequency_hz=note.get("frequency_hz", 0.0),
        chakra_number=chakra.get("number", 0),
        chakra_name=chakra.get("name", ""),
        polarity=data.get("polarity", ""),
        hidden_talent=data.get("hidden_talent", ""),
        mission=data.get("mission", ""),
        shadow=data.get("shadow", ""),
        resonance=data.get("resonance", ""),
        universe_message=data.get("universe_message", ""),
        keys_to_bloom=data.get("keys_to_bloom", ""),
        dominant_elements=data.get("dominant_elements", []),
        voice_code_id=data.get("voice_code_id", ""),
        diagnosed_at=diagnosed_at,
    )


def _get_or_generate_image(session_id: str, kind: str) -> Path:
    """
    シェア画像を取得（なければ生成）して Path を返す。
    kind: "ogp" or "story"
    """
    session_prefix = session_id[:8]

    # キャッシュ確認
    cached = list(config.OUTPUT_DIR.glob(f"voicecode_{session_prefix}_share_{kind}.png"))
    if cached:
        return cached[0]

    # 診断データ読み込み
    diagnosis = _load_diagnosis(session_id)

    # 画像生成
    from ..report.image_generator import generate_ogp_image, generate_story_image
    out_path = config.OUTPUT_DIR / f"voicecode_{session_prefix}_share_{kind}.png"

    if kind == "ogp":
        generate_ogp_image(diagnosis, out_path)
    else:
        generate_story_image(diagnosis, out_path)

    return out_path


# ==============================================================
# APIエンドポイント
# ==============================================================

@router.get("/share/{session_id}/ogp.png")
async def get_ogp_image(session_id: str):
    """
    OGP用シェア画像（1200×630）を返す。
    SNSのリンクプレビューに使用。
    """
    try:
        img_path = _get_or_generate_image(session_id, "ogp")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OGP画像生成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="画像の生成に失敗しました")

    return FileResponse(
        path=str(img_path),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/share/{session_id}/story.png")
async def get_story_image(session_id: str):
    """
    Instagramストーリー用画像（1080×1920）を返す。
    """
    try:
        img_path = _get_or_generate_image(session_id, "story")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ストーリー画像生成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="画像の生成に失敗しました")

    return FileResponse(
        path=str(img_path),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get("/share/{session_id}")
async def get_share_page(session_id: str):
    """
    OGPタグ付きシェアランディングページを返す。
    TwitterやLINEでシェアしたときのプレビューに対応。
    """
    try:
        diagnosis = _load_diagnosis(session_id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"シェアページ生成エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ページの生成に失敗しました")

    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    ogp_image_url = f"{base_url}/api/v1/share/{session_id}/ogp.png"
    story_image_url = f"{base_url}/api/v1/share/{session_id}/story.png"
    report_url = f"{base_url}/api/v1/report/{session_id}/view"

    title = f"私の声は「{diagnosis.archetype_name}」| VOICECODE"
    description = diagnosis.archetype_tagline or f"声紋リーディングで判明した魂のアーキタイプ。{diagnosis.archetype_rarity}"

    soul_color = diagnosis.soul_color_hex or "#D4AF37"

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>

  <!-- OGP -->
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:image" content="{ogp_image_url}">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{base_url}/share/{session_id}">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <meta name="twitter:image" content="{ogp_image_url}">

  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
      background: #08080F;
      color: #E8E0FF;
      font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px 16px;
    }}
    .brand {{
      color: {soul_color};
      letter-spacing: 6px;
      font-size: 13px;
      font-weight: bold;
      margin-bottom: 32px;
    }}
    .ogp-preview {{
      width: 100%;
      max-width: 600px;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 0 40px {soul_color}40;
    }}
    .ogp-preview img {{
      width: 100%;
      display: block;
    }}
    .archetype-name {{
      font-size: 28px;
      font-weight: bold;
      color: {soul_color};
      text-align: center;
      margin: 28px 0 8px;
    }}
    .tagline {{
      font-size: 15px;
      color: #9090B0;
      text-align: center;
      margin-bottom: 28px;
      padding: 0 24px;
    }}
    .divider {{
      width: 120px;
      height: 1px;
      background: {soul_color}60;
      margin: 0 auto 28px;
    }}
    .buttons {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      width: 100%;
      max-width: 400px;
    }}
    .btn {{
      display: block;
      padding: 14px 24px;
      border-radius: 8px;
      text-align: center;
      font-size: 15px;
      font-weight: bold;
      text-decoration: none;
      cursor: pointer;
      border: none;
    }}
    .btn-primary {{
      background: {soul_color};
      color: #08080F;
    }}
    .btn-secondary {{
      background: transparent;
      border: 1px solid {soul_color}80;
      color: {soul_color};
    }}
    .btn-dark {{
      background: #1A1A2E;
      color: #9090B0;
    }}
    .share-section {{
      margin-top: 32px;
      width: 100%;
      max-width: 400px;
    }}
    .share-title {{
      font-size: 12px;
      color: #4A4A6A;
      letter-spacing: 3px;
      text-align: center;
      margin-bottom: 16px;
    }}
    .copy-area {{
      background: #0D0D1A;
      border: 1px solid #2A2A3A;
      border-radius: 8px;
      padding: 12px 16px;
      font-size: 13px;
      color: #7A7A9A;
      width: 100%;
      margin-bottom: 10px;
      cursor: pointer;
      user-select: all;
    }}
    .footer {{
      margin-top: 48px;
      font-size: 11px;
      color: #3A3A5A;
      text-align: center;
    }}
  </style>
</head>
<body>

  <div class="brand">V O I C E C O D E</div>

  <div class="ogp-preview">
    <img src="{ogp_image_url}" alt="{diagnosis.archetype_name}" loading="lazy">
  </div>

  <div class="archetype-name">{diagnosis.archetype_emoji} {diagnosis.archetype_name}</div>
  <div class="tagline">{description}</div>
  <div class="divider"></div>

  <div class="buttons">
    <a href="{report_url}" class="btn btn-primary">✨ プレミアムレポートを見る</a>
    <a href="{story_image_url}" download="VOICECODE_story.png" class="btn btn-secondary">📲 ストーリー用画像をDL</a>
    <a href="{ogp_image_url}" download="VOICECODE_ogp.png" class="btn btn-dark">🖼 OGP画像をDL</a>
  </div>

  <div class="share-section">
    <div class="share-title">— SNS でシェア —</div>
    <div class="copy-area" id="copy-text" onclick="copyText()"
         title="タップしてコピー">私の声は「{diagnosis.archetype_name}」でした🎤✨
{description}
#VOICECODE #声紋診断 #魂のアーキタイプ
{base_url}/share/{session_id}</div>

    <button class="btn btn-dark" onclick="copyText()">📋 テキストをコピー</button>
  </div>

  <div class="footer">
    VOICECODE — あなたの声に、宇宙の答えがある。<br>
    Diagnosed {diagnosis.diagnosed_at.strftime('%Y.%m.%d')}
  </div>

  <script>
    function copyText() {{
      const el = document.getElementById('copy-text');
      const text = el.innerText;
      if (navigator.clipboard) {{
        navigator.clipboard.writeText(text).then(() => alert('コピーしました！'));
      }} else {{
        const ta = document.createElement('textarea');
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        alert('コピーしました！');
      }}
    }}
  </script>
</body>
</html>"""

    return HTMLResponse(content=html)
