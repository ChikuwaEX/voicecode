"""
PDFダウンロードおよびWebレポート表示 APIルーター

GET /api/v1/report/{session_id}/view — Webレポート（HTML）を返す
GET /api/v1/report/{session_id}/download — PDFレポートを返す
"""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from .. import config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/report/{session_id}/view")
async def view_report(session_id: str):
    """
    セッションIDに対応するWebレポート（HTML）をブラウザで表示する。
    """
    session_prefix = session_id[:8]
    matching_files = list(config.OUTPUT_DIR.glob(f"voicecode_{session_prefix}_*.html"))

    if not matching_files:
        logger.warning(f"Webレポートが見つかりません: session_id={session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"レポートが見つかりません。セッションIDを確認してください: {session_id}"
        )

    # 最新のHTMLファイルを読み込んで返す
    html_path = sorted(matching_files)[-1]
    logger.info(f"Webレポート配信: {html_path.name}")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    return HTMLResponse(content=content)


@router.get("/report/{session_id}/download")
async def download_report(session_id: str):
    """
    セッションIDに対応するPDFレポートをダウンロードする。
    """
    session_prefix = session_id[:8]
    matching_files = list(config.OUTPUT_DIR.glob(f"voicecode_{session_prefix}_*.pdf"))

    if not matching_files:
        logger.warning(f"PDFレポートが見つかりません: session_id={session_id}")
        raise HTTPException(
            status_code=404,
            detail=f"レポートが見つかりません。セッションIDを確認してください: {session_id}"
        )

    # 最新のPDFファイルを返す
    pdf_path = sorted(matching_files)[-1]
    logger.info(f"PDFレポート配信: {pdf_path.name}")

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"VOICECODE_PremiumReport_{session_id[:8]}.pdf",
    )
