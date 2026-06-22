"""
ブラウザ録音 WebUI ルーター

GET  /record        — 録音ページ（HTML）
POST /api/v1/record/submit — 音声を受け取り診断パイプラインを実行して結果JSONを返す

LINE内ブラウザ・スマホブラウザ両対応。
MediaRecorder API でブラウザ録音 → FormData でアップロード → 診断結果を画面に表示。
"""

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse

from .. import config
from ..audio.models import AudioFile

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# GET /record  —  録音ページ
# ---------------------------------------------------------------------------

@router.get("/record", response_class=HTMLResponse, include_in_schema=False)
async def record_page():
    """ブラウザ録音 WebUI を返す"""
    return _RECORD_HTML


# ---------------------------------------------------------------------------
# POST /api/v1/record/submit  —  音声受信 → 診断
# ---------------------------------------------------------------------------

@router.post("/record/submit")
async def submit_recording(
    audio: UploadFile = File(..., description="録音した音声ファイル (webm/wav/m4a)"),
    user_name: str = Form(default="ゲスト"),
    gender: str = Form(default="unknown"),
):
    """
    ブラウザから送られた音声を受け取り、診断パイプラインを同期実行する。

    Returns:
        診断結果 JSON（archetype_code, name, tagline, report URLs 等）
    """
    session_id = str(uuid.uuid4())
    ext = Path(audio.filename or "audio.webm").suffix.lower() or ".webm"
    audio_path = config.UPLOAD_DIR / f"web_{session_id}{ext}"

    try:
        # 音声保存
        content = await audio.read()
        audio_path.write_bytes(content)

        audio_file = AudioFile(
            file_path=audio_path,
            format=ext.lstrip("."),
            session_id=session_id,
            gender=gender,
        )

        # 解析→診断→レポート生成（重い処理はスレッドで実行）
        from ..audio.analyzer import AudioAnalyzer
        from ..diagnosis.engine import DiagnosisEngine
        from ..report.generator import ReportGenerator

        loop = asyncio.get_event_loop()

        analyzer = AudioAnalyzer(sample_rate=config.SAMPLE_RATE)
        analysis = await loop.run_in_executor(None, analyzer.analyze, audio_file)

        if analysis.analysis_duration_sec < config.MIN_AUDIO_DURATION_SEC:
            raise HTTPException(
                status_code=400,
                detail=f"音声が短すぎます（{config.MIN_AUDIO_DURATION_SEC:.0f}秒以上必要です）",
            )

        engine = DiagnosisEngine(worldview_theme=config.WORLDVIEW_THEME)
        diagnosis = engine.diagnose(analysis)

        generator = ReportGenerator(output_dir=config.OUTPUT_DIR)
        report = await loop.run_in_executor(
            None,
            lambda: generator.generate(diagnosis=diagnosis, user_name=user_name),
        )

        base_url = config.BASE_URL
        return JSONResponse({
            "session_id": session_id,
            "archetype": {
                "code": diagnosis.archetype_code,
                "name": diagnosis.archetype_name,
                "emoji": diagnosis.archetype_emoji,
                "tagline": diagnosis.archetype_tagline,
                "soul_color_hex": diagnosis.soul_color_hex,
                "soul_color_name": diagnosis.soul_color_name,
                "voice_code_id": diagnosis.voice_code_id,
                "rarity": diagnosis.archetype_rarity,
            },
            "report": {
                "view_url": f"{base_url}/api/v1/report/{session_id}/view",
                "download_url": f"{base_url}/api/v1/report/{session_id}/download",
                "share_url": f"{base_url}/api/v1/share/{session_id}",
            },
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"録音診断エラー: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"診断処理エラー: {e}")
    finally:
        if config.AUTO_DELETE_AUDIO and audio_path.exists():
            audio_path.unlink()


# ---------------------------------------------------------------------------
# 録音ページ HTML（インライン — フロントエンドファイルを別管理しない）
# ---------------------------------------------------------------------------

_RECORD_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VOICECODE — 声紋リーディング</title>
  <style>
    :root {
      --bg: #0a0a14;
      --surface: #13132a;
      --primary: #c0392b;
      --gold: #d4af37;
      --text: #e8e0f0;
      --muted: #7a7a9a;
      --radius: 16px;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Hiragino Kaku Gothic ProN', 'Noto Sans JP', sans-serif;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px 16px 48px;
    }
    header {
      text-align: center;
      margin-bottom: 32px;
    }
    header h1 {
      font-size: 1.6rem;
      letter-spacing: 0.2em;
      color: var(--gold);
    }
    header p { color: var(--muted); margin-top: 8px; font-size: 0.9rem; }

    .card {
      background: var(--surface);
      border-radius: var(--radius);
      padding: 32px 24px;
      max-width: 480px;
      width: 100%;
      border: 1px solid rgba(255,255,255,0.06);
    }

    /* 録音ボタン */
    #mic-btn {
      width: 120px; height: 120px;
      border-radius: 50%;
      border: 3px solid var(--primary);
      background: rgba(192,57,43,0.12);
      color: var(--primary);
      font-size: 2.8rem;
      cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      margin: 0 auto 20px;
      transition: all 0.3s;
      position: relative;
      outline: none;
    }
    #mic-btn.recording {
      background: rgba(192,57,43,0.3);
      border-color: #ff6b6b;
      box-shadow: 0 0 0 0 rgba(192,57,43,0.6);
      animation: pulse 1.2s infinite;
    }
    @keyframes pulse {
      0%   { box-shadow: 0 0 0 0 rgba(192,57,43,0.6); }
      70%  { box-shadow: 0 0 0 20px rgba(192,57,43,0); }
      100% { box-shadow: 0 0 0 0 rgba(192,57,43,0); }
    }

    #status-text {
      text-align: center;
      font-size: 1rem;
      color: var(--muted);
      min-height: 1.5em;
      margin-bottom: 12px;
    }
    #timer {
      text-align: center;
      font-size: 2rem;
      font-variant-numeric: tabular-nums;
      color: var(--gold);
      letter-spacing: 0.1em;
      min-height: 2.5rem;
    }

    /* 波形バー */
    #waveform {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;
      height: 48px;
      margin: 16px 0;
    }
    .bar {
      width: 5px;
      height: 8px;
      border-radius: 3px;
      background: var(--primary);
      opacity: 0.4;
      transition: height 0.08s ease;
    }

    /* 送信ボタン */
    #submit-btn {
      display: none;
      width: 100%;
      padding: 16px;
      border: none;
      border-radius: var(--radius);
      background: linear-gradient(135deg, var(--primary), #8e1a10);
      color: #fff;
      font-size: 1.1rem;
      font-weight: bold;
      cursor: pointer;
      margin-top: 16px;
      letter-spacing: 0.1em;
    }
    #submit-btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* フォーム */
    .field { margin-top: 16px; }
    label { display: block; color: var(--muted); font-size: 0.8rem; margin-bottom: 4px; }
    select, input[type=text] {
      width: 100%;
      padding: 10px 12px;
      border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      font-size: 0.95rem;
    }

    /* ガイド */
    .guide {
      margin-top: 20px;
      padding: 14px;
      border-radius: 10px;
      background: rgba(212,175,55,0.07);
      border: 1px solid rgba(212,175,55,0.2);
      font-size: 0.82rem;
      color: var(--muted);
      line-height: 1.6;
    }
    .guide strong { color: var(--gold); }

    /* 結果カード */
    #result-card {
      display: none;
      text-align: center;
      margin-top: 24px;
    }
    #result-emoji { font-size: 3.5rem; }
    #result-name { font-size: 1.5rem; color: var(--gold); margin: 8px 0 4px; }
    #result-tagline { font-size: 0.88rem; color: var(--muted); margin-bottom: 20px; }
    .btn-row { display: flex; gap: 10px; flex-direction: column; }
    .btn-link {
      display: block;
      padding: 14px;
      border-radius: var(--radius);
      font-size: 0.95rem;
      font-weight: bold;
      text-decoration: none;
      text-align: center;
      letter-spacing: 0.06em;
    }
    .btn-view   { background: var(--gold); color: #000; }
    .btn-share  { background: rgba(255,255,255,0.08); color: var(--text); border: 1px solid rgba(255,255,255,0.15); }
    .btn-retry  { background: none; color: var(--muted); border: 1px solid var(--muted); cursor: pointer; }

    /* エラー */
    #error-msg {
      display: none;
      color: #ff6b6b;
      text-align: center;
      font-size: 0.9rem;
      margin-top: 12px;
    }

    /* ローディング */
    #loading {
      display: none;
      text-align: center;
      margin-top: 16px;
    }
    .spinner {
      width: 40px; height: 40px;
      border: 3px solid rgba(212,175,55,0.15);
      border-top-color: var(--gold);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 12px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>

<header>
  <h1>✦ VOICECODE</h1>
  <p>声紋スピリチュアル診断</p>
</header>

<div class="card">
  <!-- 録音UI -->
  <div id="record-ui">
    <button id="mic-btn" aria-label="録音開始">🎤</button>
    <div id="status-text">ボタンを押して録音を開始</div>
    <div id="timer"></div>
    <div id="waveform"></div>

    <div class="field">
      <label>お名前（任意）</label>
      <input type="text" id="user-name" placeholder="ゲスト" value="ゲスト">
    </div>
    <div class="field">
      <label>声の高さ</label>
      <select id="gender">
        <option value="unknown">わからない</option>
        <option value="female">高め（女性・テノール）</option>
        <option value="male">低め（男性・バス）</option>
      </select>
    </div>

    <button id="submit-btn">✦ 声紋を送信して診断する</button>

    <div class="guide">
      <strong>録音のコツ</strong><br>
      静かな場所で、マイクから15〜20cm離れて自然に話してください。<br>
      30秒〜2分間、好きな言葉や日常のことを話すだけでOKです。
    </div>

    <div id="error-msg"></div>
  </div>

  <!-- ローディング -->
  <div id="loading">
    <div class="spinner"></div>
    <div style="color: var(--muted); font-size: 0.9rem;">
      声紋を解析中です...<br>
      <span style="font-size:0.75rem;">（30秒ほどかかります）</span>
    </div>
  </div>

  <!-- 結果 -->
  <div id="result-card">
    <div id="result-emoji"></div>
    <div id="result-name"></div>
    <div id="result-tagline"></div>
    <div id="result-voice-code" style="font-size:0.75rem;color:var(--muted);margin-bottom:20px;"></div>
    <div class="btn-row">
      <a id="btn-view" class="btn-link btn-view" href="#" target="_blank">📄 レポートを見る</a>
      <a id="btn-share" class="btn-link btn-share" href="#" target="_blank">📣 シェアページを開く</a>
      <button class="btn-link btn-retry" onclick="location.reload()">もう一度診断する</button>
    </div>
  </div>
</div>

<script>
(function() {
  // ---- 要素取得 ----
  const micBtn    = document.getElementById('mic-btn');
  const statusTxt = document.getElementById('status-text');
  const timerEl   = document.getElementById('timer');
  const waveEl    = document.getElementById('waveform');
  const submitBtn = document.getElementById('submit-btn');
  const loadingEl = document.getElementById('loading');
  const recordUI  = document.getElementById('record-ui');
  const resultEl  = document.getElementById('result-card');
  const errorEl   = document.getElementById('error-msg');

  // 波形バーを生成
  const BAR_COUNT = 20;
  for (let i = 0; i < BAR_COUNT; i++) {
    const b = document.createElement('div');
    b.className = 'bar';
    waveEl.appendChild(b);
  }
  const bars = Array.from(waveEl.querySelectorAll('.bar'));

  // ---- 録音状態管理 ----
  let mediaRec = null;
  let chunks   = [];
  let recording = false;
  let timerInterval = null;
  let seconds = 0;
  let analyserNode = null;
  let animFrame   = null;
  let audioCtx    = null;
  let audioBlob   = null;

  function formatTime(s) {
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }

  function startWaveAnim(stream) {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const src = audioCtx.createMediaStreamSource(stream);
    analyserNode = audioCtx.createAnalyser();
    analyserNode.fftSize = 64;
    src.connect(analyserNode);
    const data = new Uint8Array(analyserNode.frequencyBinCount);

    function draw() {
      animFrame = requestAnimationFrame(draw);
      analyserNode.getByteFrequencyData(data);
      bars.forEach((bar, i) => {
        const val = data[Math.floor(i * data.length / BAR_COUNT)] / 255;
        const h = Math.max(6, val * 44);
        bar.style.height = h + 'px';
        bar.style.opacity = 0.4 + val * 0.6;
      });
    }
    draw();
  }

  function stopWaveAnim() {
    if (animFrame) cancelAnimationFrame(animFrame);
    if (audioCtx) { audioCtx.close(); audioCtx = null; }
    bars.forEach(b => { b.style.height = '8px'; b.style.opacity = '0.4'; });
  }

  micBtn.addEventListener('click', async () => {
    if (recording) {
      // 録音停止
      mediaRec.stop();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      chunks = [];
      mediaRec = new MediaRecorder(stream);
      mediaRec.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
      mediaRec.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
        stopWaveAnim();
        clearInterval(timerInterval);

        audioBlob = new Blob(chunks, { type: 'audio/webm' });
        const mins = Math.floor(seconds / 60);
        statusTxt.textContent = `録音完了 — ${formatTime(seconds)}`;
        micBtn.textContent = '🎤';
        micBtn.classList.remove('recording');
        recording = false;

        if (seconds < 15) {
          showError('15秒以上録音してください。もう一度試してみてください。');
          submitBtn.style.display = 'none';
        } else {
          submitBtn.style.display = 'block';
        }
      };

      mediaRec.start(200);
      recording = true;
      seconds = 0;
      micBtn.classList.add('recording');
      micBtn.textContent = '⏹';
      statusTxt.textContent = '録音中... 話しかけてください';
      timerEl.textContent = '00:00';
      submitBtn.style.display = 'none';
      errorEl.style.display = 'none';

      timerInterval = setInterval(() => {
        seconds++;
        timerEl.textContent = formatTime(seconds);
        if (seconds >= 180) mediaRec.stop(); // 最大3分
      }, 1000);

      startWaveAnim(stream);

    } catch (err) {
      showError('マイクへのアクセスが許可されていません。ブラウザの設定を確認してください。');
    }
  });

  submitBtn.addEventListener('click', async () => {
    if (!audioBlob) return;
    showLoading();

    const fd = new FormData();
    fd.append('audio', audioBlob, 'recording.webm');
    fd.append('user_name', document.getElementById('user-name').value || 'ゲスト');
    fd.append('gender', document.getElementById('gender').value);

    try {
      const res = await fetch('/api/v1/record/submit', { method: 'POST', body: fd });
      const json = await res.json();
      if (!res.ok) {
        showError(json.detail || '診断に失敗しました。もう一度お試しください。');
        return;
      }
      showResult(json);
    } catch (e) {
      showError('通信エラーが発生しました。しばらくしてからもう一度お試しください。');
    }
  });

  function showLoading() {
    recordUI.style.display = 'none';
    loadingEl.style.display = 'block';
    resultEl.style.display = 'none';
  }

  function showResult(data) {
    loadingEl.style.display = 'none';
    resultEl.style.display = 'block';
    const a = data.archetype;
    document.getElementById('result-emoji').textContent = a.emoji || '✦';
    document.getElementById('result-name').textContent = a.name || '';
    document.getElementById('result-name').style.color = a.soul_color_hex || '#d4af37';
    document.getElementById('result-tagline').textContent = a.tagline || '';
    document.getElementById('result-voice-code').textContent = a.voice_code_id || '';
    document.getElementById('btn-view').href  = data.report.view_url;
    document.getElementById('btn-share').href = data.report.share_url;
  }

  function showError(msg) {
    loadingEl.style.display = 'none';
    recordUI.style.display = 'block';
    errorEl.style.display = 'block';
    errorEl.textContent = '⚠ ' + msg;
  }
})();
</script>
</body>
</html>"""
