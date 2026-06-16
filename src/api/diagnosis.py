"""
診断結果取得 APIルーター

GET /api/v1/diagnosis/{session_id} — 診断結果を取得する。
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger_import = __import__('logging')
logger = logger_import.getLogger(__name__)

router = APIRouter()


@router.get("/diagnosis/{session_id}")
async def get_diagnosis(session_id: str):
    """
    セッションIDから診断結果のサマリーを取得する。
    完全な診断情報はPDFダウンロードで提供されます。
    """
    # 注意: 実際はセッションストアから取得する。
    # Phase1ではシンプルなメッセージを返す。
    return JSONResponse(content={
        "session_id": session_id,
        "message": "診断結果はPDFレポートで確認してください。",
        "report_url": f"/api/v1/report/{session_id}",
    })
