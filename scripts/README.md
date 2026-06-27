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
# 一括(引数 or stdin)
python3 scripts/resolve_x_articles.py "https://t.co/a" "https://x.com/u/status/1"
echo "https://x.com/u/status/1" | python3 scripts/resolve_x_articles.py
```

- 標準ライブラリのみ(追加依存なし)。
- t.co 等の短縮はリダイレクト解決。`x.com/<user>/status/<id>` 直リンクは
  ネット無しで正規化。
- 出力は 1 URL = 1 行 JSON。`candidates` に status / i_status / i_article /
  syndication の各形、`network` に到達可否、`note` に注意点。
- x.com に届かない環境では `network: false` を正直に返す(捏造しない)。
  本文抽出(ログイン済み Chrome)は走る環境でだけ可能 → スキル本体参照。
