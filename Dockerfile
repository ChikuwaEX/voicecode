FROM python:3.11-slim

# Playwright / Chromium が必要とするシステムライブラリをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    # Chromium の依存関係
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 \
    libasound2 libpango-1.0-0 libcairo2 libxshmfence1 \
    libx11-6 libxext6 libxfixes3 libxrender1 libxcb1 \
    fonts-liberation fonts-noto-cjk \
    # librosa / scipy の依存関係
    libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存関係をキャッシュ効率よくインストール（コード変更時に再実行しない）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright の Chromium ブラウザをインストール
RUN playwright install chromium

# アプリケーションコードをコピー
COPY . .

# アップロード・出力ディレクトリを作成
RUN mkdir -p uploads outputs

# ポート公開
EXPOSE 8000

# 本番起動（reload なし）
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
