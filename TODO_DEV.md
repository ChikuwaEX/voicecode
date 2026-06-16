# 💻 TODO_DEV — VOICECODE 開発TODO

> 最終更新: 2026-06-13 v0.2 | フェーズ: Phase 0（設計・計画）
> 開発原則: 疎結合（Loose Coupling）+ オブジェクト指向（OOP）

---

## 🔴 Phase 0 — アーキテクチャ設計（今すぐやること）

### 技術スタック確定
- [ ] バックエンド言語・フレームワーク選定（Python/FastAPI 推奨）
- [ ] 音声解析ライブラリ選定（librosa / pyworld / parselmouth 等）
- [ ] PDF生成ライブラリ選定（WeasyPrint / reportlab / Puppeteer等）
- [ ] データベース選定（PostgreSQL + Supabase 推奨）
- [ ] ホスティング選定（Railway / Render / AWS等）
- [ ] LINE Messaging API の利用方針確定
- [ ] 決済: Stripe の設定方針確定

### インターフェース設計（疎結合の核）
- [ ] `IAudioAnalyzer` インターフェース定義
- [ ] `IDiagnosisEngine` インターフェース定義
- [ ] `IReportGenerator` インターフェース定義
- [ ] `ILineMessagingService` インターフェース定義
- [ ] `IPaymentService` インターフェース定義
- [ ] `IUserRepository` インターフェース定義

### データモデル設計
- [ ] `AudioFile` データクラス設計
- [ ] `AudioAnalysisResult` データクラス設計
- [ ] `Big5Score` データクラス設計
- [ ] `DiagnosisResult` データクラス設計
- [ ] `PDFReport` データクラス設計
- [ ] `User` データクラス設計
- [ ] `DiagnosisSession` データクラス設計（決済〜完了までの状態管理）

### ARCHITECTURE.md の詳細化
- [ ] 全コンポーネント間の依存関係図の完成
- [ ] カスタマージャーニーと対応するAPIフローの明確化
- [ ] エラーハンドリング戦略の設計
- [ ] セキュリティ設計（音声データの暗号化等）

---

## 🟠 Phase 1 — コアエンジン開発

### 🎵 音声解析エンジン (AudioAnalyzer)
- [ ] 音声ファイル入力対応（WAV/MP3/WebM/M4A）
- [ ] 基本周波数（F0）抽出
- [ ] ピッチ検出と音域分類（低・中・高）
- [ ] リズム・テンポ解析（BPM相当値）
- [ ] フォルマント分析（F1・F2）
- [ ] 周波数帯域ごとのエネルギー分布
- [ ] 声の安定性・変動性の算出
- [ ] 解析結果のJSON出力
- [ ] 単体テスト作成

### 🔮 診断ロジックエンジン (DiagnosisEngine)
- [ ] 音声特徴量 → Big5スコア変換ルールの実装
- [ ] Big5スコア → スピ系タイプ分類ロジック
- [ ] スピ系表現変換辞書のJSON/YAML化
- [ ] 複合スコアリングロジック（複数特徴量の重み付け）
- [ ] 診断パターン（最低10種）の実装
- [ ] 診断結果オブジェクトの生成
- [ ] 単体テスト作成

### 📄 PDFレポート生成エンジン (ReportGenerator)
- [ ] デザインテンプレートの作成（神秘的・美しいビジュアル）
- [ ] 診断結果 → PDF変換処理
- [ ] ユーザー名・診断日の動的挿入
- [ ] グラフ・チャートの埋め込み（Big5レーダーチャート等）
- [ ] PDF出力・保存機能
- [ ] 単体テスト作成

---

## 🟡 Phase 2 — LINE連携 & 決済 & Web UI

### 📱 LINE Bot基盤 (LineBotService)
- [ ] LINE Messaging API の設定（チャンネル作成・Webhook設定）
- [ ] Webhook受信サーバーの実装
- [ ] メッセージ受信・送信の基本実装
- [ ] 決済完了後の録音ページURL送付機能
- [ ] 完成PDFのLINE自動送付機能
- [ ] 診断フロー全体のステータス管理
- [ ] エラー時のユーザーへの自動通知

### 💳 決済サービス (PaymentService)
- [ ] Stripe アカウント設定・API連携
- [ ] LINE上からStripe決済ページへの誘導実装
- [ ] 決済完了Webhook受信・処理
- [ ] 決済状態管理（未払い・完了・返金）
- [ ] 領収書の自動送付

### 🎙️ 録音Web UI
- [ ] ブラウザ録音ページの実装（MediaRecorder API）
- [ ] 録音ガイド画面（「30秒間、この言葉を読んでください」等）
- [ ] 録音データのサーバーアップロード
- [ ] 録音完了後の自動処理トリガー
- [ ] スマートフォン対応（LINE内ブラウザでの動作確認）

### APIゲートウェイ
- [ ] `POST /api/v1/webhook/line` — LINE Webhook受信
- [ ] `POST /api/v1/webhook/stripe` — Stripe決済完了受信
- [ ] `POST /api/v1/audio/upload` — 音声ファイルアップロード
- [ ] `GET /api/v1/diagnosis/{session_id}` — 診断結果取得
- [ ] `GET /api/v1/report/{session_id}` — PDFダウンロード
- [ ] エラーハンドリングの統一

---

## 🟢 Phase 3 — 品質向上・スケール準備

- [ ] 負荷テスト・パフォーマンス最適化
- [ ] セキュリティ監査（音声データ・個人情報の暗号化確認）
- [ ] 監視・ログ体制の構築
- [ ] 管理者ダッシュボードの実装
- [ ] 診断精度の改善サイクル設計

---

*凡例: [ ] 未着手 / [/] 進行中 / [x] 完了*
