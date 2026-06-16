# 🏛️ ARCHITECTURE — VOICECODE システム設計

> バージョン: v0.2 (2026-06-13) | ステータス: Draft（Phase 0）

---

## 設計原則

1. **疎結合（Loose Coupling）** — 各モジュールはインターフェースのみで通信し、実装に依存しない
2. **単一責任の原則（SRP）** — 各クラスは1つの責任のみを持つ
3. **依存性逆転の原則（DIP）** — 上位モジュールは下位モジュールの実装ではなくインターフェースに依存する
4. **テスタビリティ** — 各エンジンは独立してテスト可能
5. **自動化ファースト** — 人手が介在しない完全自動フロー

---

## カスタマージャーニーとシステムフロー

```
[ユーザー: LINE]
    │
    ① 友だち追加
    │   → LineBot: ウェルカムメッセージ送信
    │
    ② 診断申し込み
    │   → PaymentService: Stripe決済ページURL生成・送付
    │
    ③ 決済完了（Stripe Webhook）
    │   → PaymentService: 決済確認
    │   → SessionService: DiagnosisSession作成（status: PAID）
    │   → LineBot: 録音ページURL送付
    │
    ④ 録音（Web UI: ブラウザ）
    │   → AudioUploadService: 音声ファイル受信・保存
    │   → SessionService: status更新（RECORDING_COMPLETE）
    │
    ⑤ 自動処理パイプライン
    │   → AudioAnalyzer: 音声特徴量抽出
    │   → DiagnosisEngine: Big5マッピング + スピ系変換
    │   → ReportGenerator: PDF生成
    │   → SessionService: status更新（REPORT_READY）
    │
    ⑥ LINE自動送付
        → LineMessagingService: PDFをLINEで送信
        → SessionService: status更新（COMPLETED）
```

---

## コアインターフェース設計

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

# ===== データクラス =====

@dataclass
class AudioFile:
    file_path: str
    format: str          # wav, mp3, webm, m4a
    duration_sec: float
    sample_rate: int
    session_id: str

@dataclass
class AudioAnalysisResult:
    session_id: str
    fundamental_frequency: float   # 基本周波数 F0 (Hz)
    pitch_category: str            # low / mid / high
    tempo_bpm: float               # リズム・テンポ
    formant_f1: float              # フォルマントF1
    formant_f2: float              # フォルマントF2
    frequency_bands: dict          # 帯域ごとのエネルギー分布
    pitch_stability: float         # 声の安定性 (0.0〜1.0)
    analyzed_at: datetime

@dataclass
class Big5Score:
    openness: float        # 開放性
    conscientiousness: float  # 誠実性
    extraversion: float    # 外向性
    agreeableness: float   # 協調性
    neuroticism: float     # 神経症傾向

@dataclass
class DiagnosisResult:
    session_id: str
    big5_score: Big5Score
    spirit_type: str           # スピ系タイプ名（例：「宇宙の探求者」）
    mission_description: str   # 使命の説明文（スピ系表現）
    talent_description: str    # 才能の説明文（スピ系表現）
    destiny_description: str   # 運命の説明文（スピ系表現）
    advice: str                # アドバイス文
    diagnosed_at: datetime

@dataclass
class PDFReport:
    file_path: str
    session_id: str
    generated_at: datetime
    user_line_id: str

@dataclass
class DiagnosisSession:
    session_id: str
    user_line_id: str
    status: str  # CREATED / PAID / RECORDING_COMPLETE / PROCESSING / REPORT_READY / COMPLETED / ERROR
    created_at: datetime
    updated_at: datetime

# ===== インターフェース =====

class IAudioAnalyzer(ABC):
    @abstractmethod
    def analyze(self, audio_file: AudioFile) -> AudioAnalysisResult:
        """音声ファイルを解析し、特徴量を返す"""
        ...

class IDiagnosisEngine(ABC):
    @abstractmethod
    def diagnose(self, analysis: AudioAnalysisResult) -> DiagnosisResult:
        """音声特徴量をBig5マッピング→スピ系表現に変換し診断結果を返す"""
        ...

class IReportGenerator(ABC):
    @abstractmethod
    def generate(self, diagnosis: DiagnosisResult, user_name: str) -> PDFReport:
        """診断結果からPDFレポートを生成する"""
        ...

class ILineMessagingService(ABC):
    @abstractmethod
    def send_pdf(self, user_line_id: str, report: PDFReport) -> bool:
        """指定ユーザーのLINEにPDFを送付する"""
        ...
    
    @abstractmethod
    def send_message(self, user_line_id: str, message: str) -> bool:
        """指定ユーザーのLINEにテキストメッセージを送る"""
        ...

class IPaymentService(ABC):
    @abstractmethod
    def create_payment_url(self, session_id: str, amount: int) -> str:
        """決済URLを生成する"""
        ...
    
    @abstractmethod
    def verify_payment(self, session_id: str) -> bool:
        """決済完了を確認する"""
        ...

class ISessionRepository(ABC):
    @abstractmethod
    def create(self, session: DiagnosisSession) -> DiagnosisSession:
        ...
    
    @abstractmethod
    def find_by_id(self, session_id: str) -> Optional[DiagnosisSession]:
        ...
    
    @abstractmethod
    def update_status(self, session_id: str, status: str) -> DiagnosisSession:
        ...
```

---

## 技術スタック候補（確定待ち）

| レイヤー | 候補 | 理由 |
|---|---|---|
| バックエンド | Python (FastAPI) | 音声処理ライブラリが豊富・Webhookサーバーに最適 |
| 音声解析 | librosa + parselmouth | F0・ピッチ・フォルマント解析に定評あり |
| PDF生成 | WeasyPrint or reportlab | 高品質PDF出力 |
| フロントエンド（録音UI） | Vanilla JS or Next.js | LINE内ブラウザ対応が重要 |
| データベース | PostgreSQL + Supabase | スケーラブルなBaaS |
| 音声ストレージ | Supabase Storage or AWS S3 | 安価で信頼性高い |
| LINE連携 | LINE Messaging API (Python SDK) | 標準SDK |
| 決済 | Stripe | 標準的な決済基盤 |
| ホスティング | Railway or Render | 小〜中規模に最適・コスト低 |

---

## APIエンドポイント設計（仮）

| メソッド | エンドポイント | 説明 |
|---|---|---|
| POST | /api/v1/webhook/line | LINE Webhook受信 |
| POST | /api/v1/webhook/stripe | Stripe決済完了受信 |
| POST | /api/v1/audio/upload | 音声ファイルアップロード |
| GET | /api/v1/session/{id} | セッション状態確認 |
| GET | /api/v1/report/{id} | PDFダウンロード |

---

## セキュリティ設計（方針）

- 音声データは処理完了後に自動削除（プライバシー保護）
- LINE User IDの安全な管理（暗号化保存）
- Stripe Webhookの署名検証
- LINE Webhookの署名検証（X-Line-Signature）
- HTTPSのみ（TLS必須）

---

*最終更新: 2026-06-13 v0.2 / Phase 0 Draft*
