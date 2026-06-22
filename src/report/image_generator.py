"""
SNSシェア用画像生成モジュール

PillowでOGP画像（1200×630）とInstagramストーリー画像（1080×1920）を生成します。
NotoSansJP.ttf フォントを使用。
"""

import logging
from pathlib import Path
from typing import Tuple, List

from PIL import Image, ImageDraw, ImageFont

from ..diagnosis.models import DiagnosisResult

logger = logging.getLogger(__name__)

_FONT_DIR = Path(__file__).parent / "templates" / "fonts"
_FONT_JP = _FONT_DIR / "NotoSansJP.ttf"

# ブランドカラー
_GOLD = (212, 175, 55)
_BG_DARK = (8, 8, 15)
_TEXT_DIM = (144, 144, 176)
_TEXT_MID = (180, 170, 200)


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return _GOLD
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
    )


def _darken(rgb: Tuple[int, int, int], factor: float = 0.35) -> Tuple[int, int, int]:
    return (int(rgb[0] * factor), int(rgb[1] * factor), int(rgb[2] * factor))


def _draw_gradient(img: Image.Image, top_color: Tuple, bottom_color: Tuple) -> None:
    """縦方向グラデーションを描画"""
    draw = ImageDraw.Draw(img)
    w, h = img.size
    for y in range(h):
        t = y / h
        r = int(top_color[0] * (1 - t) + bottom_color[0] * t)
        g = int(top_color[1] * (1 - t) + bottom_color[1] * t)
        b = int(top_color[2] * (1 - t) + bottom_color[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(_FONT_JP), size)
    except Exception:
        return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> List[str]:
    """テキストを指定幅で折り返す（日本語対応）"""
    lines: List[str] = []
    current = ""
    for char in text:
        test = current + char
        try:
            bbox = font.getbbox(test)
            width = bbox[2] - bbox[0]
        except Exception:
            width = len(test) * (font.size if hasattr(font, "size") else 12)
        if width > max_width:
            if current:
                lines.append(current)
            current = char
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    cx: int,
    y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: Tuple,
) -> int:
    """中央揃えでテキストを描画し、次のy座標を返す"""
    try:
        bbox = font.getbbox(text)
        h = bbox[3] - bbox[1]
    except Exception:
        h = font.size if hasattr(font, "size") else 14
    draw.text((cx, y), text, font=font, fill=fill, anchor="mm")
    return y + h


def generate_ogp_image(diagnosis: DiagnosisResult, output_path: Path) -> Path:
    """
    OGP用シェア画像（1200×630）を生成する。
    SNSでリンクシェアしたときに表示されるサムネイル。
    """
    W, H = 1200, 630
    img = Image.new("RGB", (W, H))

    soul_rgb = _hex_to_rgb(diagnosis.soul_color_hex or "#D4AF37")
    bg_bottom = _darken(soul_rgb, 0.30)
    _draw_gradient(img, _BG_DARK, bg_bottom)

    draw = ImageDraw.Draw(img)
    cx = W // 2

    # 上下アクセントライン
    draw.line([(0, 3), (W, 3)], fill=soul_rgb, width=1)
    draw.line([(0, H - 3), (W, H - 3)], fill=soul_rgb, width=3)

    # ブランドロゴ
    draw.text((cx, 36), "V O I C E C O D E", font=_font(20), fill=_GOLD, anchor="mm")

    # アーキタイプ絵文字（レンダリング失敗時はスキップ）
    try:
        draw.text((cx, 165), diagnosis.archetype_emoji, font=_font(100), anchor="mm")
    except Exception:
        pass

    # アーキタイプ名
    draw.text((cx, 300), diagnosis.archetype_name, font=_font(68), fill=soul_rgb, anchor="mm")

    # タグライン
    if diagnosis.archetype_tagline:
        draw.text((cx, 382), diagnosis.archetype_tagline, font=_font(26), fill=_TEXT_MID, anchor="mm")

    # 区切り線
    draw.line([(cx - 220, 420), (cx + 220, 420)], fill=_GOLD, width=1)

    # 声紋コード・周波数
    info_parts: List[str] = []
    if diagnosis.voice_code_id:
        info_parts.append(diagnosis.voice_code_id)
    if diagnosis.note_name and diagnosis.note_frequency_hz:
        info_parts.append(f"{diagnosis.note_name} / {diagnosis.note_frequency_hz:.1f}Hz")
    if info_parts:
        draw.text((cx, 455), "  ·  ".join(info_parts), font=_font(22), fill=_TEXT_DIM, anchor="mm")

    # 診断日
    date_str = diagnosis.diagnosed_at.strftime("Diagnosed  %Y.%m.%d")
    draw.text((cx, H - 36), date_str, font=_font(18), fill=(60, 60, 90), anchor="mm")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    logger.info(f"OGP画像生成完了: {output_path}")
    return output_path


def generate_story_image(diagnosis: DiagnosisResult, output_path: Path) -> Path:
    """
    Instagramストーリー用画像（1080×1920）を生成する。
    縦長フォーマット。
    """
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H))

    soul_rgb = _hex_to_rgb(diagnosis.soul_color_hex or "#D4AF37")
    bg_mid = _darken(soul_rgb, 0.28)

    # 上→中→下のグラデーション（2段階）
    top_half = Image.new("RGB", (W, H // 2))
    _draw_gradient(top_half, _BG_DARK, bg_mid)
    img.paste(top_half, (0, 0))

    bot_half = Image.new("RGB", (W, H - H // 2))
    _draw_gradient(bot_half, bg_mid, _BG_DARK)
    img.paste(bot_half, (0, H // 2))

    draw = ImageDraw.Draw(img)
    cx = W // 2

    # 外枠
    draw.rectangle([(30, 30), (W - 30, H - 30)], outline=soul_rgb, width=1)

    # ブランドロゴ
    draw.text((cx, 105), "V O I C E C O D E", font=_font(32), fill=_GOLD, anchor="mm")
    draw.text((cx, 150), "声 紋 リ ー デ ィ ン グ", font=_font(22), fill=(100, 100, 140), anchor="mm")
    draw.line([(cx - 180, 188), (cx + 180, 188)], fill=_GOLD, width=1)

    # アーキタイプ絵文字
    try:
        draw.text((cx, 460), diagnosis.archetype_emoji, font=_font(160), anchor="mm")
    except Exception:
        pass

    # アーキタイプ名
    draw.text((cx, 660), diagnosis.archetype_name, font=_font(80), fill=soul_rgb, anchor="mm")

    # タグライン（折り返し）
    y = 760
    if diagnosis.archetype_tagline:
        lines = _wrap_text(diagnosis.archetype_tagline, _font(36), W - 140)
        for line in lines[:3]:
            draw.text((cx, y), line, font=_font(36), fill=_TEXT_MID, anchor="mm")
            y += 52

    draw.line([(cx - 280, y + 20), (cx + 280, y + 20)], fill=_GOLD, width=1)
    y += 60

    # 詳細情報グループ
    font_info = _font(32)
    if diagnosis.soul_color_name:
        draw.text((cx, y), f"声の色：{diagnosis.soul_color_name}", font=font_info, fill=soul_rgb, anchor="mm")
        y += 55
    if diagnosis.note_name and diagnosis.note_frequency_hz:
        draw.text(
            (cx, y),
            f"周波数：{diagnosis.note_name} / {diagnosis.note_frequency_hz:.1f}Hz",
            font=font_info,
            fill=_TEXT_DIM,
            anchor="mm",
        )
        y += 55
    if diagnosis.chakra_name:
        draw.text((cx, y), f"チャクラ：{diagnosis.chakra_name}", font=font_info, fill=_TEXT_DIM, anchor="mm")
        y += 55
    if diagnosis.archetype_rarity:
        draw.text((cx, y), diagnosis.archetype_rarity, font=_font(28), fill=(80, 80, 120), anchor="mm")
        y += 55

    draw.line([(cx - 280, y + 10), (cx + 280, y + 10)], fill=_GOLD, width=1)
    y += 50

    # 声紋コード
    if diagnosis.voice_code_id:
        draw.text(
            (cx, y),
            f"VOICE CODE  {diagnosis.voice_code_id}",
            font=_font(26),
            fill=(74, 74, 106),
            anchor="mm",
        )
        y += 50

    # 宇宙からのメッセージ（短縮版）
    msg = diagnosis.universe_message
    if msg:
        font_msg = _font(28)
        short_msg = msg[:50] + ("…" if len(msg) > 50 else "")
        lines = _wrap_text(short_msg, font_msg, W - 160)
        msg_y = H - 260
        for line in lines[:3]:
            draw.text((cx, msg_y), line, font=font_msg, fill=(100, 100, 140), anchor="mm")
            msg_y += 42

    # 下部ブランド帯
    draw.line([(0, H - 110), (W, H - 110)], fill=soul_rgb, width=2)
    draw.text(
        (cx, H - 72),
        "voicecode.jp  ·  あなたの声に、宇宙の答えがある。",
        font=_font(24),
        fill=(74, 74, 106),
        anchor="mm",
    )
    draw.text(
        (cx, H - 42),
        diagnosis.diagnosed_at.strftime("%Y.%m.%d"),
        font=_font(20),
        fill=(55, 55, 80),
        anchor="mm",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(output_path), "PNG")
    logger.info(f"ストーリー画像生成完了: {output_path}")
    return output_path
