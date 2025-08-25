
# RSS / Alerts Monitor（JST対応）

## 推奨ランタイム（客観）
- **GitHub Actions（推奨）**：無料枠／定刻実行／ログ・差分がGitで残る。
- **Google Apps Script（次点）**：Google内で完結。RSS量・TLS制限に注意。
- **Google Colab（非推奨）**：定期実行に不向き（セッション切断）。

## セットアップ（GitHub Actions）
1. このフォルダをリポジトリへpush。
2. `Settings > Secrets and variables > Actions` に `SLACK_WEBHOOK_URL` を登録（任意）。
3. `.github/workflows/rss_monitor.yml` の `cron` は **UTC 00:00 / 07:00**（= JST 09:00 / 16:00）。
4. 実行すると `data/latest.csv` と `data/collected/*.csv`、`data/seen_state.json` が更新・コミット。

## ローカル実行
```bash
pip install -r requirements.txt
python monitor.py
```

## 監視対象編集
- `sources.json` の `feeds` と `keywords_any` を編集。
- `type: "rss" | "page"`（pageは本文差分検知＋キーワード一致時のみ通知）。
