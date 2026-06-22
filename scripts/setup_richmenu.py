"""
LINE リッチメニュー セットアップスクリプト

実行方法（プロジェクトルートで）:
    py scripts/setup_richmenu.py

事前準備:
    - .env に LINE_CHANNEL_ACCESS_TOKEN が設定されていること
    - BASE_URL が本番ドメインになっていること（例: https://voicecode-production.up.railway.app）

リッチメニューの構成（3列2行 × 6ボタン）:
    ┌──────────────┬──────────────┬──────────────┐
    │  🎤 声紋診断  │  📄 使い方   │  ✦ 10タイプ  │
    ├──────────────┼──────────────┼──────────────┤
    │  🔗 シェア   │  💳 料金    │  📞 お問合せ │
    └──────────────┴──────────────┴──────────────┘
"""

import os
import sys
import json
import httpx
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# プロジェクトルートを sys.path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
BASE_URL = os.getenv("BASE_URL", "https://voicecode-production.up.railway.app")

if not TOKEN:
    print("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

# ============================================================
# 1. リッチメニュー画像を生成する
# ============================================================

WIDTH, HEIGHT = 2500, 1686  # LINE推奨サイズ（6タブ）

MENU_ITEMS = [
    # (label, emoji, col, row)
    ("声紋診断を受ける", "🎤", 0, 0),
    ("使い方・ガイド",   "📖", 1, 0),
    ("10の声のタイプ",   "✦",  2, 0),
    ("シェアする",       "📣", 0, 1),
    ("料金・詳細",       "💳", 1, 1),
    ("よくある質問",     "❓", 2, 1),
]

BG_COLOR   = (8, 8, 20)
CELL_BORDER = (30, 30, 60)
GOLD       = (212, 175, 55)
TEXT_COLOR = (232, 224, 255)
MUTED      = (122, 122, 154)


def _make_richmenu_image(output_path: Path) -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    cell_w = WIDTH // 3
    cell_h = HEIGHT // 2

    # グリッド線
    for c in range(1, 3):
        x = c * cell_w
        draw.line([(x, 0), (x, HEIGHT)], fill=CELL_BORDER, width=2)
    draw.line([(0, cell_h), (WIDTH, cell_h)], fill=CELL_BORDER, width=2)
    draw.rectangle([(0, 0), (WIDTH - 1, HEIGHT - 1)], outline=CELL_BORDER, width=2)

    # 各セルに絵文字・ラベルを描画（フォントは環境依存のため簡易実装）
    for label, emoji, col, row in MENU_ITEMS:
        cx = col * cell_w + cell_w // 2
        cy = row * cell_h + cell_h // 2

        # ゴールドの丸アイコン背景
        r = 100
        draw.ellipse([(cx - r, cy - r - 60), (cx + r, cy + r - 60)],
                     fill=(30, 28, 10), outline=GOLD, width=3)

        # テキスト（フォントなし環境では bbox が変わる）
        try:
            font_em = ImageFont.truetype("NotoSansJP-Bold.ttf", 80)
            font_lb = ImageFont.truetype("NotoSansJP-Regular.ttf", 52)
        except Exception:
            font_em = ImageFont.load_default()
            font_lb = ImageFont.load_default()

        # 絵文字
        bbox = draw.textbbox((0, 0), emoji, font=font_em)
        ew = bbox[2] - bbox[0]
        draw.text((cx - ew // 2, cy - 105), emoji, font=font_em, fill=TEXT_COLOR)

        # ラベル
        bbox2 = draw.textbbox((0, 0), label, font=font_lb)
        lw = bbox2[2] - bbox2[0]
        draw.text((cx - lw // 2, cy + 70), label, font=font_lb, fill=MUTED)

    img.save(output_path, "PNG")
    print(f"✅ リッチメニュー画像生成: {output_path}")


# ============================================================
# 2. LINE API を使ってリッチメニューを作成・設定
# ============================================================

def create_richmenu() -> str:
    """リッチメニューオブジェクトを作成してIDを返す"""
    cell_w = WIDTH // 3
    cell_h = HEIGHT // 2

    actions = [
        {"type": "uri", "uri": f"{BASE_URL}/record"},           # 声紋診断
        {"type": "message", "text": "使い方"},                   # ガイド
        {"type": "message", "text": "10の声のタイプ"},            # タイプ一覧
        {"type": "uri", "uri": f"{BASE_URL}/api/v1/share/demo"}, # シェア
        {"type": "uri", "uri": f"{BASE_URL}/#pricing"},          # 料金
        {"type": "message", "text": "よくある質問"},              # FAQ
    ]

    areas = []
    for i, (label, emoji, col, row) in enumerate(MENU_ITEMS):
        areas.append({
            "bounds": {
                "x": col * cell_w, "y": row * cell_h,
                "width": cell_w,   "height": cell_h,
            },
            "action": actions[i],
        })

    body = {
        "size": {"width": WIDTH, "height": HEIGHT},
        "selected": True,
        "name": "VOICECODE メインメニュー",
        "chatBarText": "🎤 メニューを開く",
        "areas": areas,
    }

    resp = httpx.post(
        "https://api.line.me/v2/bot/richmenu",
        headers=HEADERS,
        json=body,
        timeout=30,
    )
    resp.raise_for_status()
    menu_id = resp.json()["richMenuId"]
    print(f"✅ リッチメニュー作成: {menu_id}")
    return menu_id


def upload_richmenu_image(menu_id: str, image_path: Path) -> None:
    """リッチメニュー画像をアップロード"""
    with open(image_path, "rb") as f:
        resp = httpx.post(
            f"https://api-data.line.me/v2/bot/richmenu/{menu_id}/content",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "image/png",
            },
            content=f.read(),
            timeout=60,
        )
    resp.raise_for_status()
    print(f"✅ 画像アップロード完了")


def set_default_richmenu(menu_id: str) -> None:
    """全ユーザーのデフォルトリッチメニューに設定"""
    resp = httpx.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{menu_id}",
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    print(f"✅ デフォルトリッチメニューに設定完了")


def delete_all_richmenus() -> None:
    """既存のリッチメニューを全削除（クリーンアップ）"""
    resp = httpx.get("https://api.line.me/v2/bot/richmenu/list", headers=HEADERS, timeout=15)
    if not resp.is_success:
        return
    for menu in resp.json().get("richmenus", []):
        mid = menu["richMenuId"]
        httpx.delete(f"https://api.line.me/v2/bot/richmenu/{mid}", headers=HEADERS, timeout=15)
        print(f"  🗑 削除: {mid}")


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":
    print("=" * 50)
    print("VOICECODE リッチメニュー セットアップ")
    print(f"BASE_URL: {BASE_URL}")
    print("=" * 50)

    # 既存リッチメニューをクリア
    print("\n① 既存リッチメニュー削除...")
    delete_all_richmenus()

    # 画像生成
    image_path = Path(__file__).parent / "richmenu.png"
    print("\n② リッチメニュー画像生成...")
    _make_richmenu_image(image_path)

    # LINE APIで作成
    print("\n③ リッチメニュー作成...")
    menu_id = create_richmenu()

    # 画像アップロード
    print("\n④ 画像アップロード...")
    upload_richmenu_image(menu_id, image_path)

    # デフォルト設定
    print("\n⑤ デフォルトに設定...")
    set_default_richmenu(menu_id)

    print("\n" + "=" * 50)
    print("✅ リッチメニュー設定完了！")
    print(f"   メニューID: {menu_id}")
    print("   LINEアプリでチャットを開くとメニューが表示されます")
    print("=" * 50)
