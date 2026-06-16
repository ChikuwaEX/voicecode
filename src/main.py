"""
VOICECODE アプリケーション エントリーポイント

FastAPIアプリを起動し、全APIルートとフロントエンドを登録します。
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from .api import audio as audio_router
from .api import diagnosis as diagnosis_router
from .api import report as report_router
from .api import line_webhook as line_router
from .api import payment as payment_router
from . import config

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("VOICECODE 起動中...")
    logger.info(f"環境: {config.APP_ENV}")
    logger.info(f"アップロードディレクトリ: {config.UPLOAD_DIR}")
    logger.info(f"出力ディレクトリ: {config.OUTPUT_DIR}")
    logger.info(f"世界観テーマ: {config.WORLDVIEW_THEME}")
    logger.info(f"GUI: http://localhost:{config.APP_PORT}")
    logger.info(f"LINE Webhook: {config.BASE_URL}/api/v1/line/webhook")
    line_ok = bool(config.LINE_CHANNEL_ACCESS_TOKEN and config.LINE_CHANNEL_SECRET)
    logger.info(f"LINE Bot: {'✅ 設定済み' if line_ok else '⚠️  未設定（.envを確認）'}")
    logger.info("=" * 50)
    yield
    logger.info("VOICECODE シャットダウン完了")


app = FastAPI(
    title="VOICECODE API",
    description="声紋分析システム VOICECODE - REST API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ngrok ブラウザ警告ページをスキップするミドルウェア
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class NgrokSkipMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response

app.add_middleware(NgrokSkipMiddleware)


# APIルートを安全に登録（エラーが出ても他のルートは動く）
def _safe_include_router(router_module, name: str):
    try:
        app.include_router(router_module.router, prefix="/api/v1", tags=[name])
        logger.info(f"✅ ルーター登録成功: {name}")
    except Exception as e:
        logger.error(f"❌ ルーター登録失敗: {name} — {e}")

_safe_include_router(audio_router, "audio")
_safe_include_router(diagnosis_router, "diagnosis")
_safe_include_router(report_router, "report")
_safe_include_router(line_router, "line")
_safe_include_router(payment_router, "payment")


@app.get("/")
async def serve_frontend():
    """インデックス（ランディングページ）"""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"service": "VOICECODE", "version": "1.0.0", "status": "running"})


@app.get("/app")
async def serve_app():
    """診断UIページ"""
    app_path = FRONTEND_DIR / "app.html"
    if app_path.exists():
        return FileResponse(str(app_path))
    # app.htmlがなければLPにフォールバック
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/law")
async def serve_law():
    """特定商取引法に基づく表記"""
    law_path = FRONTEND_DIR / "law.html"
    if law_path.exists():
        return FileResponse(str(law_path))
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/privacy")
async def serve_privacy():
    """プライバシーポリシー"""
    privacy_path = FRONTEND_DIR / "privacy.html"
    if privacy_path.exists():
        return FileResponse(str(privacy_path))
    return JSONResponse({"error": "Not found"}, status_code=404)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=config.APP_HOST,
        port=config.APP_PORT,
        reload=config.APP_ENV == "development",
        log_level="info",
    )
