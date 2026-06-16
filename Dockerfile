FROM python:3.11-slim

# システムライブラリ一括インストール
# build-essential: pyworld/parselmouth のコンパイルに必要
# ffmpeg: 音声変換に必要
# fonts-noto-cjk: PDF日本語フォントに必要
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential python3-dev pkg-config \
    wget gnupg ca-certificates \
    libsndfile1 ffmpeg \
    fonts-liberation fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Step1: コンパイル系の前提パッケージを先にインストール
# pyworld は numpy + Cython が必要
COPY requirements.txt .
RUN pip install --no-cache-dir numpy cython wheel setuptools

# Step2: 全パッケージインストール
RUN pip install --no-cache-dir -r requirements.txt

# Step3: Playwright + Chromium インストール（依存ライブラリも自動取得）
RUN python -m playwright install chromium --with-deps

# Step4: アプリコードをコピー
COPY . .

# ディレクトリ作成
RUN mkdir -p uploads outputs

EXPOSE 8000

CMD uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
