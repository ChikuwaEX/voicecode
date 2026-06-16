"""
VOICECODE 設定管理モジュール

環境変数の読み込みとアプリケーション設定を一元管理します。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .env ファイルを読み込む
load_dotenv()

# ベースディレクトリ
BASE_DIR = Path(__file__).parent.parent
SRC_DIR = Path(__file__).parent

# アプリケーション設定
APP_ENV = os.getenv("APP_ENV", "development")
APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
APP_PORT = int(os.getenv("APP_PORT", "8000"))
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
BASE_URL = os.getenv("BASE_URL", f"http://localhost:{os.getenv('APP_PORT', '8000')}")

# ファイルパス設定
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", str(BASE_DIR / "outputs")))
WORLDVIEW_THEME_DIR = SRC_DIR / "diagnosis" / "worldview" / "themes"
WORLDVIEW_THEME = os.getenv("WORLDVIEW_THEME", "elements_v1")

# ディレクトリを自動作成
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# データベース
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/voicecode.db")

# LINE Bot 設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")

# 診断設定
DIAGNOSIS_PRICE_YEN = int(os.getenv("DIAGNOSIS_PRICE_YEN", "3000"))
MIN_AUDIO_DURATION_SEC = float(os.getenv("MIN_AUDIO_DURATION_SEC", "15"))
MAX_AUDIO_DURATION_SEC = float(os.getenv("MAX_AUDIO_DURATION_SEC", "180"))

# 音声解析設定
SAMPLE_RATE = 16000  # Hz
MIN_PITCH_HZ = 75.0
MAX_PITCH_HZ = 600.0

# セキュリティ：音声データ処理後の自動削除
AUTO_DELETE_AUDIO = os.getenv("AUTO_DELETE_AUDIO", "true").lower() == "true"
