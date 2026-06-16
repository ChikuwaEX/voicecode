"""VOICECODEの診断APIテストスクリプト"""
import requests
import json
import sys

API_URL = "http://localhost:8000/api/v1"
TEST_FILES = [
    ("test_audio/sample_female_en.wav",  "テストユーザーA", "female"),
    ("test_audio/sample_female_en3.wav", "テストユーザーB", "female"),
    ("test_audio/sample_female_en4.wav", "テストユーザーC", "female"),
]

for audio_path, user_name, gender in TEST_FILES:
    print(f"\n{'='*50}")
    print(f"ファイル: {audio_path}")
    print(f"ユーザー: {user_name} ({gender})")
    print("送信中...")

    try:
        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.split("/")[-1], f, "audio/wav")}
            data  = {"user_name": user_name, "gender": gender}
            r = requests.post(f"{API_URL}/audio/upload", files=files, data=data, timeout=120)

        if r.ok:
            d = r.json()
            a = d["archetype"]
            b = d["big5_score"]
            print(f"\n--- 診断結果 ---")
            print(f"声紋コードID : {a['voice_code_id']}")
            print(f"アーキタイプ : {a['emoji']} {a['name']}")
            print(f"タグライン   : {a['tagline']}")
            print(f"PDFダウンロード: http://localhost:8000{d['report']['download_url']}")
            print("\nBig5スコア:")
            for k, v in b.items():
                if k != "levels":
                    bar = "█" * int(v * 20)
                    spaces = " " * (20 - int(v * 20))
                    print(f"  {k:<22}: [{bar}{spaces}] {int(v*100):3d}%")
        else:
            print(f"エラー ({r.status_code}): {r.text[:300]}")

    except Exception as e:
        print(f"例外: {e}")

print(f"\n{'='*50}")
print("テスト完了！")
