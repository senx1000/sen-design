# scripts

SEN Design リポジトリの補助スクリプト。

## resolve_x_articles.py

X(Twitter)リンクを「本文抽出の手前」まで正規化する。
Claude Code スキル [`x-article-intake`](../.claude/skills/x-article-intake/SKILL.md)
の第1段。Codex 版(別 Vault `sen-brain` の同名スクリプト)の Claude Code 対応版。

```bash
# 単発
python3 scripts/resolve_x_articles.py "https://x.com/user/status/123"
# 整形
python3 scripts/resolve_x_articles.py --pretty "https://t.co/xxxx"
# 到達性プローブ付き(x.com に実際に届くか確認 = 抽出可否の判定)
python3 scripts/resolve_x_articles.py --probe "https://x.com/user/status/123"
# 一括(引数 or stdin)
python3 scripts/resolve_x_articles.py "https://t.co/a" "https://x.com/u/status/1"
echo "https://x.com/u/status/1" | python3 scripts/resolve_x_articles.py
```

- 標準ライブラリのみ(追加依存なし)。
- t.co 等の短縮はリダイレクト解決。`x.com/<user>/status/<id>` 直リンクは
  ネット無しで正規化。
- 出力は 1 URL = 1 行 JSON。`candidates` に status / i_status / i_article /
  syndication の各形、`note` に注意点。
- `network` は「パースに通信が要ったか」。status 直リンクは常に true。
  **抽出可否の真の判定は `--probe` が付ける `reachable`** で見る
  (x.com に実際に届くか)。届かない環境では `reachable: false` を正直に返す。
- 本文抽出(ログイン済み Chrome)は走る環境でだけ可能 → スキル本体参照。
