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
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

# ログ設定（最初に行う）
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ============================================================
# configを安全にimport
# ============================================================
try:
    from . import config
    logger.info("✅ config import OK")
except Exception as e:
    logger.error(f"❌ config import FAILED: {e}")
    import types
    config = types.SimpleNamespace(
        APP_ENV="production",
        APP_HOST="0.0.0.0",
        APP_PORT=8000,
        BASE_URL="http://localhost:8000",
        UPLOAD_DIR=Path("./uploads"),
        OUTPUT_DIR=Path("./outputs"),
        WORLDVIEW_THEME="elements_v1",
        LINE_CHANNEL_ACCESS_TOKEN="",
        LINE_CHANNEL_SECRET="",
    )

# ============================================================
# 各ルーターを安全にimport（失敗しても起動を続ける）
# ============================================================
audio_router = None
diagnosis_router = None
report_router = None
line_router = None
payment_router = None
share_router = None

try:
    from .api import audio as audio_router
    logger.info("✅ audio router import OK")
except Exception as e:
    logger.error(f"❌ audio router import FAILED: {e}", exc_info=True)

try:
    from .api import diagnosis as diagnosis_router
    logger.info("✅ diagnosis router import OK")
except Exception as e:
    logger.error(f"❌ diagnosis router import FAILED: {e}", exc_info=True)

try:
    from .api import report as report_router
    logger.info("✅ report router import OK")
except Exception as e:
    logger.error(f"❌ report router import FAILED: {e}", exc_info=True)

try:
    from .api import line_webhook as line_router
    logger.info("✅ line router import OK")
except Exception as e:
    logger.error(f"❌ line router import FAILED: {e}", exc_info=True)

try:
    from .api import payment as payment_router
    logger.info("✅ payment router import OK")
except Exception as e:
    logger.error(f"❌ payment router import FAILED: {e}", exc_info=True)

try:
    from .api import share as share_router
    logger.info("✅ share router import OK")
except Exception as e:
    logger.error(f"❌ share router import FAILED: {e}", exc_info=True)


FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("VOICECODE 起動中...")
    logger.info(f"環境: {config.APP_ENV}")
    logger.info(f"アップロードディレクトリ: {config.UPLOAD_DIR}")
    logger.info(f"出力ディレクトリ: {config.OUTPUT_DIR}")
    logger.info(f"世界観テーマ: {config.WORLDVIEW_THEME}")
    line_ok = bool(config.LINE_CHANNEL_ACCESS_TOKEN and config.LINE_CHANNEL_SECRET)
    logger.info(f"LINE Bot: {'✅ 設定済み' if line_ok else '⚠️  未設定'}")
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


class NgrokSkipMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["ngrok-skip-browser-warning"] = "true"
        return response

app.add_middleware(NgrokSkipMiddleware)


# APIルートを安全に登録
def _safe_include(router_module, tag: str):
    if router_module is None:
        logger.warning(f"⚠️  {tag} router skipped (import failed)")
        return
    try:
        app.include_router(router_module.router, prefix="/api/v1", tags=[tag])
        logger.info(f"✅ {tag} router registered")
    except Exception as e:
        logger.error(f"❌ {tag} router registration failed: {e}", exc_info=True)

_safe_include(audio_router, "audio")
_safe_include(diagnosis_router, "diagnosis")
_safe_include(report_router, "report")
_safe_include(line_router, "line")
_safe_include(payment_router, "payment")
_safe_include(share_router, "share")


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
    import os
    port = int(os.getenv("PORT", str(getattr(config, "APP_PORT", 8000))))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
