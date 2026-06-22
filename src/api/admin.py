"""
管理者ダッシュボード APIルーター

GET /admin         — ダッシュボード（HTML、Basic Auth保護）
GET /admin/stats   — 統計情報 JSON

環境変数:
    ADMIN_USERNAME  : Basic Auth ユーザー名（デフォルト: admin）
    ADMIN_PASSWORD  : Basic Auth パスワード（デフォルト: voicecode）
"""

import os
import secrets
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from .. import config

logger_name = __name__
router = APIRouter()
security = HTTPBasic()


def _check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Basic Auth でアクセス制御。タイミング攻撃対策のため secrets.compare_digest を使用。"""
    ok_user = secrets.compare_digest(
        credentials.username,
        os.getenv("ADMIN_USERNAME", "admin"),
    )
    ok_pass = secrets.compare_digest(
        credentials.password,
        os.getenv("ADMIN_PASSWORD", "voicecode"),
    )
    if not (ok_user and ok_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証失敗",
            headers={"WWW-Authenticate": "Basic"},
        )


def _get_dir_stats(directory: Path) -> dict:
    """ディレクトリの使用量・ファイル数を集計する"""
    if not directory.exists():
        return {"count": 0, "size_mb": 0.0}
    files = list(directory.glob("**/*"))
    files = [f for f in files if f.is_file()]
    total = sum(f.stat().st_size for f in files)
    return {"count": len(files), "size_mb": round(total / 1_048_576, 2)}


@router.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard(_: None = Depends(_check_admin)):
    """管理者ダッシュボード HTML"""
    from ..session.store import get_store
    store = get_store()
    stats = store.count_stats()
    sessions = store.get_all(limit=50)

    output_stat = _get_dir_stats(config.OUTPUT_DIR)
    upload_stat = _get_dir_stats(config.UPLOAD_DIR)

    rows_html = ""
    for s in sessions:
        paid_badge = (
            '<span style="color:#2ecc71">✔ 決済済み</span>'
            if s.is_paid else
            '<span style="color:#7a7a9a">未決済</span>'
        )
        created = s.created_at.strftime("%m/%d %H:%M")
        archetype = s.archetype_name or "—"
        rows_html += f"""
        <tr>
          <td style="font-size:0.75rem;color:#aaa">{s.session_id[:8]}…</td>
          <td>{archetype}</td>
          <td>{paid_badge}</td>
          <td style="font-size:0.8rem;color:#aaa">{created}</td>
          <td style="font-size:0.75rem;color:#aaa">{s.line_user_id or '—'}</td>
        </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>VOICECODE 管理ダッシュボード</title>
  <style>
    body {{ background:#0a0a14; color:#e8e0f0; font-family:sans-serif; padding:24px; }}
    h1 {{ color:#d4af37; margin-bottom:24px; font-size:1.4rem; }}
    .cards {{ display:flex; gap:16px; flex-wrap:wrap; margin-bottom:32px; }}
    .card {{
      background:#13132a; border:1px solid rgba(255,255,255,0.07);
      border-radius:12px; padding:20px 24px; min-width:160px;
    }}
    .card .label {{ color:#7a7a9a; font-size:0.78rem; margin-bottom:4px; }}
    .card .value {{ font-size:1.8rem; font-weight:bold; color:#d4af37; }}
    table {{ border-collapse:collapse; width:100%; max-width:900px; }}
    th {{
      text-align:left; padding:10px 12px; font-size:0.78rem;
      color:#7a7a9a; border-bottom:1px solid rgba(255,255,255,0.08);
    }}
    td {{ padding:10px 12px; border-bottom:1px solid rgba(255,255,255,0.04); font-size:0.88rem; }}
    tr:hover td {{ background:rgba(255,255,255,0.03); }}
    .section-title {{
      font-size:0.85rem; color:#7a7a9a; letter-spacing:0.12em;
      margin:24px 0 12px; text-transform:uppercase;
    }}
    a.btn {{
      display:inline-block; padding:8px 16px; border-radius:8px;
      background:rgba(192,57,43,0.2); color:#ff6b6b;
      text-decoration:none; font-size:0.82rem; margin-top:8px;
    }}
  </style>
</head>
<body>
<h1>✦ VOICECODE 管理ダッシュボード</h1>

<div class="cards">
  <div class="card">
    <div class="label">総診断数</div>
    <div class="value">{stats['total']}</div>
  </div>
  <div class="card">
    <div class="label">決済済み</div>
    <div class="value" style="color:#2ecc71">{stats['paid']}</div>
  </div>
  <div class="card">
    <div class="label">未決済（無料/テスト）</div>
    <div class="value">{stats['free']}</div>
  </div>
  <div class="card">
    <div class="label">出力ファイル数</div>
    <div class="value" style="color:#9b59b6">{output_stat['count']}</div>
    <div style="font-size:0.75rem;color:#7a7a9a">{output_stat['size_mb']} MB</div>
  </div>
  <div class="card">
    <div class="label">アップロード残留</div>
    <div class="value" style="color:#e67e22">{upload_stat['count']}</div>
    <div style="font-size:0.75rem;color:#7a7a9a">{upload_stat['size_mb']} MB</div>
  </div>
</div>

<div class="section-title">直近50件のセッション</div>
<table>
  <thead>
    <tr>
      <th>Session ID</th>
      <th>アーキタイプ</th>
      <th>決済状態</th>
      <th>作成日時</th>
      <th>LINE User ID</th>
    </tr>
  </thead>
  <tbody>
    {rows_html if rows_html else '<tr><td colspan="5" style="color:#7a7a9a;text-align:center;padding:20px">データなし</td></tr>'}
  </tbody>
</table>

<div class="section-title">クイックリンク</div>
<a class="btn" href="/admin/stats">📊 統計 JSON</a>
<a class="btn" href="/health" style="margin-left:8px">💚 ヘルスチェック</a>
<a class="btn" href="/docs" style="margin-left:8px">📝 API ドキュメント</a>

<div style="color:#7a7a9a;font-size:0.75rem;margin-top:32px">
  最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} JST
</div>
</body>
</html>"""
    return html


@router.get("/config/public")
async def public_config():
    """
    フロントエンドが参照する公開設定値を返す。
    認証不要・機密情報なし。LINE_ADD_FRIEND_URL など。
    """
    return JSONResponse({
        "line_add_friend_url": os.getenv("LINE_ADD_FRIEND_URL", ""),
        "diagnosis_price_yen": int(os.getenv("DIAGNOSIS_PRICE_YEN", "3000")),
    })


@router.get("/admin/stats", include_in_schema=False)
async def admin_stats(_: None = Depends(_check_admin)):
    """管理用統計 JSON"""
    from ..session.store import get_store
    store = get_store()
    return JSONResponse({
        "sessions": store.count_stats(),
        "storage": {
            "output": _get_dir_stats(config.OUTPUT_DIR),
            "upload": _get_dir_stats(config.UPLOAD_DIR),
        },
        "timestamp": datetime.utcnow().isoformat(),
    })
