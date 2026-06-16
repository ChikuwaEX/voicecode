"""
LINE リッチメニュー設定スクリプト

このスクリプトを1回実行するだけで、公式LINEアカウントに
VOICECODEのリッチメニューが設定されます。

実行方法:
    python scripts/setup_line_richmenu.py
"""

import os
import sys
import json
import requests
from pathlib import Path

# .env を読み込む
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

if not CHANNEL_ACCESS_TOKEN:
    print("❌ LINE_CHANNEL_ACCESS_TOKEN が設定されていません。")
    print("   .env ファイルを確認してください。")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def create_rich_menu() -> str:
    """リッチメニューを作成してIDを返す"""
    rich_menu = {
        "size": {"width": 2500, "height": 843},
        "selected": True,
        "name": "VOICECODE メインメニュー",
        "chatBarText": "メニューを開く",
        "areas": [
            {
                # 左: 声紋診断を始める
                "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
                "action": {
                    "type": "message",
                    "text": "診断を始める"
                }
            },
            {
                # 中: 使い方ガイド
                "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
                "action": {
                    "type": "message",
                    "text": "使い方"
                }
            },
            {
                # 右: 公式サイト
                "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
                "action": {
                    "type": "uri",
                    "uri": BASE_URL
                }
            }
        ]
    }

    resp = requests.post(
        "https://api.line.me/v2/bot/richmenu",
        headers=HEADERS,
        json=rich_menu
    )
    resp.raise_for_status()
    rich_menu_id = resp.json()["richMenuId"]
    print(f"✅ リッチメニュー作成: {rich_menu_id}")
    return rich_menu_id


def upload_rich_menu_image(rich_menu_id: str, image_path: str) -> None:
    """リッチメニューの画像をアップロード"""
    if not Path(image_path).exists():
        print(f"⚠️  画像ファイルが見つかりません: {image_path}")
        print("   画像なしで設定を続行します（LINE デフォルト表示になります）")
        return

    with open(image_path, "rb") as f:
        resp = requests.post(
            f"https://api-data.line.me/v2/bot/richmenu/{rich_menu_id}/content",
            headers={
                "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "image/png",
            },
            data=f.read()
        )
    resp.raise_for_status()
    print(f"✅ リッチメニュー画像アップロード完了")


def set_default_rich_menu(rich_menu_id: str) -> None:
    """全ユーザーのデフォルトリッチメニューとして設定"""
    resp = requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
        headers=HEADERS
    )
    resp.raise_for_status()
    print(f"✅ デフォルトリッチメニューとして設定完了")


def delete_all_rich_menus() -> None:
    """既存リッチメニューをすべて削除（クリーンアップ用）"""
    resp = requests.get("https://api.line.me/v2/bot/richmenu/list", headers=HEADERS)
    resp.raise_for_status()
    menus = resp.json().get("richmenus", [])
    for menu in menus:
        mid = menu["richMenuId"]
        requests.delete(f"https://api.line.me/v2/bot/richmenu/{mid}", headers=HEADERS)
        print(f"🗑️  削除: {mid}")
    print(f"✅ {len(menus)} 件のリッチメニューを削除しました")


def main():
    print("=" * 50)
    print("VOICECODE — LINE リッチメニュー設定")
    print("=" * 50)

    # 既存メニューを削除してクリーンな状態にする
    print("\n① 既存リッチメニューを削除中...")
    delete_all_rich_menus()

    # 新しいリッチメニューを作成
    print("\n② リッチメニューを作成中...")
    rich_menu_id = create_rich_menu()

    # 画像をアップロード（存在する場合）
    print("\n③ リッチメニュー画像をアップロード中...")
    image_path = Path(__file__).parent.parent / "frontend" / "assets" / "richmenu.png"
    upload_rich_menu_image(rich_menu_id, str(image_path))

    # デフォルトとして設定
    print("\n④ デフォルトリッチメニューとして設定中...")
    set_default_rich_menu(rich_menu_id)

    print("\n" + "=" * 50)
    print("✨ リッチメニュー設定完了！")
    print(f"   Rich Menu ID: {rich_menu_id}")
    print("=" * 50)
    print()
    print("次のステップ:")
    print("  LINE Developers Console で Webhook URL を設定してください:")
    print(f"  {BASE_URL}/api/v1/line/webhook")


if __name__ == "__main__":
    main()
