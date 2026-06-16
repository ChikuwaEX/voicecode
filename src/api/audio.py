"""
音声アップロード APIルーター

POST /api/v1/audio/upload — 音声ファイルを受信し、解析を開始する。
"""

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .. import config
from ..audio.models import AudioFile
from ..session.models import DiagnosisSession, SessionStatus

logger = logging.getLogger(__name__)
router = APIRouter()

# エンジンは遅延初期化（起動時のクラッシュを防ぐ）
_audio_analyzer = None
_diagnosis_engine = None
_report_generator = None

# インメモリコア（後でDBに置き換え）
_sessions: dict[str, DiagnosisSession] = {}


def _get_engines():
    """エンジンの遅延初期化（初回リクエスト時に実行）"""
    global _audio_analyzer, _diagnosis_engine, _report_generator
    if _audio_analyzer is None:
        from ..audio.analyzer import AudioAnalyzer
        from ..diagnosis.engine import DiagnosisEngine
        from ..report.generator import ReportGenerator
        _audio_analyzer = AudioAnalyzer(sample_rate=config.SAMPLE_RATE)
        _diagnosis_engine = DiagnosisEngine(worldview_theme=config.WORLDVIEW_THEME)
        _report_generator = ReportGenerator(output_dir=config.OUTPUT_DIR)
    return _audio_analyzer, _diagnosis_engine, _report_generator


@router.post("/audio/upload")
async def upload_audio(
    file: UploadFile = File(...),
    user_name: str = Form(default="ゲスト"),
    gender: str = Form(default="unknown"),
):
    """
    音声ファイルをアップロードして完全自動診断パイプラインを実行する。

    処理フロー:
        1. 音声ファイルを保存
        2. 音声解析（周波数・ピッチ・リズム等）
        3. Big5診断 → アーキタイプ決定
        4. PDFレポート生成
        5. 音声データを自動削除（プライバシー保護）

    Returns:
        セッションIDと診断結果の要約
    """
    session_id = str(uuid.uuid4())
    logger.info(f"新規診断リクエスト: session_id={session_id}, user={user_name}")

    # セッションを作成
    session = DiagnosisSession(
        session_id=session_id,
        user_name=user_name,
        gender=gender,
    )
    _sessions[session_id] = session

    # 音声ファイルを一時保存
    file_extension = Path(file.filename or "audio.wav").suffix.lower()
    if file_extension not in [".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"]:
        raise HTTPException(
            status_code=400,
            detail=f"非対応ファイル形式: {file_extension}"
        )

    audio_path = config.UPLOAD_DIR / f"{session_id}{file_extension}"

    try:
        # ファイルを保存
        content = await file.read()
        with open(audio_path, "wb") as f:
            f.write(content)

        session.update_status(SessionStatus.RECORDING_COMPLETE)
        session.audio_file_path = str(audio_path)

        # --- Step 1: 音声解析 ---
        session.update_status(SessionStatus.PROCESSING)
        audio_file = AudioFile(
            file_path=audio_path,
            format=file_extension.lstrip("."),
            session_id=session_id,
            gender=gender,
        )
        audio_analyzer, diagnosis_engine, report_generator = _get_engines()
        analysis_result = audio_analyzer.analyze(audio_file)
        logger.info(f"[{session_id}] 音声解析完了: F0={analysis_result.f0_mean_hz:.1f}Hz")

        # --- Step 2: 診断 ---
        diagnosis_result = diagnosis_engine.diagnose(analysis_result)
        logger.info(f"[{session_id}] 診断完了: type={diagnosis_result.archetype_name}")

        # --- Step 3: PDF生成 ---
        pdf_report = report_generator.generate(diagnosis_result, user_name)
        session.report_file_path = str(pdf_report.file_path)
        session.update_status(SessionStatus.REPORT_READY)
        logger.info(f"[{session_id}] PDF生成完了: {pdf_report.file_name}")

    except ValueError as e:
        session.update_status(SessionStatus.ERROR, str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        session.update_status(SessionStatus.ERROR, str(e))
        logger.error(f"[{session_id}] エラー発生: {e}")
        raise HTTPException(status_code=500, detail=f"診断処理中にエラーが発生しました: {str(e)}")
    finally:
        # 音声データを自動削除（プライバシー保護）
        if config.AUTO_DELETE_AUDIO and audio_path.exists():
            audio_path.unlink()
            logger.info(f"[{session_id}] 音声データを自動削除しました")

    session.update_status(SessionStatus.COMPLETED)

    return JSONResponse(content={
        "session_id": session_id,
        "status": "completed",
        "archetype": {
            "code": diagnosis_result.archetype_code,
            "name": diagnosis_result.archetype_name,
            "emoji": diagnosis_result.archetype_emoji,
            "tagline": diagnosis_result.archetype_tagline,
            "voice_code_id": diagnosis_result.voice_code_id,
        },
        "big5_score": diagnosis_result.big5_score.to_dict(),
        "report": {
            "view_url": f"/api/v1/report/{session_id}/view",
            "download_url": f"/api/v1/report/{session_id}/download",
        },
        "message": f"診断完了！{diagnosis_result.archetype_name}のレポートをダウンロードしてください。",
    })
