# 📋 PROGRESS_LOG — VOICECODE 進捗ログ

---

## 2026-06-13（Phase 0 開始・全体像確定）

### 完了事項
- ビジネスヒアリング（10項目）完了
- ビジネス全貌の詳細確定（以下参照）
- MASTER_PLAN.md v0.1 → v0.2 更新
- TODO_BUSINESS.md v0.1 → v0.2 更新
- TODO_DEV.md v0.1 → v0.2 更新
- TODO_MARKETING.md v0.1 → v0.2 更新
- ARCHITECTURE.md v0.1 → v0.2 更新

### 確定事項（v0.2で追加）

#### ビジネスモデル
- 顧客導線: SNS/広告 → 公式LINE → LINE上で決済 → 録音画面 → 自動処理 → LINEでPDF送付
- 公式LINEが全工程の中心プラットフォーム（MVP段階からLINE連携が必須）
- 収益ロードマップ:
  - Phase 4: 診断レポート課金（¥3,000〜¥5,000/回）
  - Phase 5-A: ヒーラー育成講座（高単価）
  - Phase 5-B: グッズ・物販

#### 診断ロジック
- 科学的根拠: ビッグ5（Big Five）パーソナリティ理論 + 音声学論文
- 表現変換: 科学的データ → スピ系ユーザー向けの言い回し・世界観に変換
- 内部処理はBig5ベース、ユーザーへの出力はすべてスピ系表現

### 重要な設計変更
- LINE連携がPhase 3から**MVP必須機能**に格上げ
- DiagnosisSessionクラスでフロー全体のステータス管理が必要
- 音声データは処理後に自動削除（プライバシーポリシー上必須）

### 次のアクション（優先順位順）
1. [ ] Big5と音声特徴量の対応論文調査
2. [ ] スピ系表現への変換辞書の言語化（コンテンツ設計）
3. [ ] 技術スタックの最終確定
4. [ ] ARCHITECTURE.md の詳細化
5. [ ] LINE Messaging API の調査・設定開始

---

## 2026-06-22（Phase C: バイラル装置 — SNSシェア機能 実装完了）

### 担当AI
Cursor (claude-sonnet-4-5)

### 完了事項

#### 新規作成ファイル
- `src/report/image_generator.py` — PillowによるSNSシェア画像生成エンジン
  - `generate_ogp_image()`: OGP用（1200×630px）アーキタイプカラーグラデーション背景
  - `generate_story_image()`: Instagramストーリー用（1080×1920px）縦長フォーマット
  - NotoSansJP.ttf使用、日本語テキスト折り返し対応
- `src/api/share.py` — SNSシェアAPIルーター
  - `GET /api/v1/share/{session_id}/ogp.png` → OGP画像
  - `GET /api/v1/share/{session_id}/story.png` → ストーリー画像
  - `GET /api/v1/share/{session_id}` → OGP対応シェアランディングページ（コピーテキスト付き）

#### 更新ファイル
- `src/report/generator.py` — レポート生成時に診断データを `outputs/{stem}.json` へ保存（シェア画像の遅延生成に対応）
- `src/line/client.py` — `build_result_flex()` に `share_url` 引数追加・「📣 SNSでシェアする」ボタンを追加
- `src/line/handler.py` — シェアURL（`/api/v1/share/{session_id}`）を組み立てて Flex に渡すよう更新
- `src/main.py` — `share_router` を安全にインポート・登録

### 設計のポイント
- シェア画像はオンデマンド生成 + ファイルキャッシュ（`outputs/voicecode_{prefix}_share_{kind}.png`）
- 診断データはJSONとして永続化するためサーバー再起動後もシェア可能
- LINEシェアボタン → シェアページ → OGP画像という完全なバイラルループを構築

---

## 2026-06-22（Phase D: Stripe課金・マネタイズ導線 実装完了）

### 担当AI
Cursor (claude-sonnet-4-5)

### 完了事項

#### 決済フロー設計
- **マネタイズモード**（`STRIPE_SECRET_KEY` 設定済み）:  
  音声解析完了 → テーザーFlex（アーキタイプ名のみ表示） + 「¥3,000で受け取る」Stripeボタン  
  → ユーザーが決済 → Stripe Webhook → LINE にフルレポートをプッシュ
- **フリーモード**（`STRIPE_SECRET_KEY` 未設定）:  
  従来通りフルレポートを即時送信（開発・テスト時に使用）

#### 変更ファイル
- `src/line/client.py`
  - `build_payment_prompt_flex()` 追加: テーザー + Stripe決済ボタン
  - `build_payment_complete_flex()` 追加: 決済完了後のフルレポート配信Flex
- `src/line/handler.py`
  - `_create_stripe_checkout_url()` ヘルパー追加
  - `_process_audio_and_push()` に SessionStore登録 + Stripe条件分岐を追加
- `src/api/payment.py`
  - Webhook に `_push_report_to_line()` を追加（決済完了 → LINE プッシュ）
  - `GET /api/v1/payment/line-success` 追加（決済完了ランディングページ）
  - `GET /api/v1/payment/line-cancel` 追加（キャンセルランディングページ）

#### Stripe設定（本番稼働に必要な手順）
1. `.env` に `STRIPE_SECRET_KEY=sk_live_...` を追加
2. `.env` に `STRIPE_WEBHOOK_SECRET=whsec_...` を追加
3. Stripe Dashboard で Webhook URL を設定:
   - URL: `https://あなたのドメイン/api/v1/payment/webhook`
   - イベント: `checkout.session.completed`
4. (任意) `DIAGNOSIS_PRICE_YEN=3000` で価格を設定

### 次のアクション（Phase E）
- [ ] 広告・PR展開（SNSコンテンツ戦略）

---

*ログは作業のたびに追記してください*
