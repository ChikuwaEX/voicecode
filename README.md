# 🎤 VOICECODE — 声紋分析システム

> 声の周波数・ピッチ・リズムから、Big Five理論に基づいた「運命・使命・才能」を自動診断するWebシステム

---

## 必要な環境

- Python 3.11+
- pip
- インターネット接続（初回のパッケージインストール時）

---

## 🚀 セットアップ手順

### 1. リポジトリのクローン（またはフォルダに移動）
```powershell
cd c:\Users\smats\Desktop\ANTIGRAVITY開発\声紋分析システムVOICECODE
```

### 2. 仮想環境の作成
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. 依存パッケージのインストール
```powershell
pip install -r requirements.txt
```

### 4. 環境変数の設定
```powershell
copy .env.example .env
# .envファイルを編集して必要に応じて設定
```

### 5. サーバーの起動
```powershell
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 動作確認
ブラウザで http://localhost:8000 にアクセス
APIドキュメント: http://localhost:8000/docs

---

## 🎤 音声アップロードで診断する

```powershell
# curlでテスト（WAVファイルを用意してください）
curl -X POST http://localhost:8000/api/v1/audio/upload \
  -F "file=@test_audio.wav" \
  -F "user_name=テストユーザー" \
  -F "gender=female"
```

---

## 🌌 世界観テーマの切り替え

```python
# コード変更不要！YAMLを差し替えるだけ
# .envにWORLDVIEW_THEME=elements_v1 を設定
```

利用可能なテーマは `src/diagnosis/worldview/themes/` フォルダにある YAMLファイル。

---

## 🏗️ アーキテクチャ

```
音声 → AudioAnalyzer → AudioAnalysisResult
                  ↓
             DiagnosisEngine → Big5Score → DiagnosisResult
                  ↓
             ReportGenerator → PDFファイル
```

各エンジンはインターフェースによる**疎結合設計**です。

---

*VOICECODE v1.0 | Phase 1*
