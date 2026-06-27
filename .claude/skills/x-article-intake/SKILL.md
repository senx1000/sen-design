---
name: x-article-intake
description: >-
  X(Twitter)のリンク(x.com / twitter.com / t.co)を貼られたら、検索で遠回りせず
  この固定ルートで本文を取り込む。t.co 解決 → x.com 正規化 → ログイン済み
  Chrome で本文抽出 → 要点化 → 必要なら SEN へ精製。Codex 版 AI-OS/x-article-intake.md
  の Claude Code 対応版。X / Twitter / ポスト / ツイート のURLを読む時に使う。
---

# x-article-intake (Claude Code 版)

X のリンクを貼られた時の **標準ルート**。毎回これに乗せる。検索で遠回りしない。

```
X URL → scripts/resolve_x_articles.py → t.co解決 → x.com/<user>/status|i/article/<id>
      → ★ログイン済み Chrome で本文抽出★ → 要点化 → 必要なら SEN へ精製
```

これは Codex 版(`AI-OS/x-article-intake.md` ＋ `scripts/resolve_x_articles.py`)と
**同じ共通層**で、実行アダプタを Claude Code 向けにしたもの(SEN 第11.3 の二層化)。

---

## 前提(どこで走るか)

このスキルの核心 = **「ログイン済み Chrome ＋ x.com へ届く回線」**。
両方ある所でだけ最後まで走る。

| 走る場所 | 回線 | ログイン済み Chrome | 挙動 |
|---|---|---|---|
| **ローカル Claude Code(Mac)** | あり | あり | **フル実行**(本筋) |
| Claude Code web / sandbox | x.com 遮断 | なし | **縮退**(後述のフォールバック) |

まず自分の環境を1コマンドで判定してから進む(下記 Step 0)。盛らない。
届かないのに「読んだ」と言わない(SEN 第6条/正直性)。

---

## 手順

### Step 0 — 環境判定(必須・最初に1回)

```bash
python3 scripts/resolve_x_articles.py "<貼られたXのURL>"
```

返り値の `network` を見る。
- `network: true` かつ `status_id` が取れた → **Step 1 へ(フル実行可)**。
- `network: false` → この環境は x.com に届かない → **フォールバックへ**。

> resolver は標準ライブラリのみ。t.co 等の短縮は redirect を解決し、
> 既に `x.com/<user>/status/<id>` ならネット無しで正規化する。
> 出力は 1 URL = 1 行 JSON(`candidates` に status / i_status / i_article /
> syndication の各形)。複数 URL は引数か stdin でまとめて渡せる。

### Step 1 — 正規 URL を得る

resolver の `candidates` を使う。
- 通常ポスト → `candidates.status`
- 長文(X Articles)っぽい → `candidates.i_article` も開いて本文の所在を確認
- どちらか判別不能なら、本文抽出時(Step 2)に実体で確定する

### Step 2 — ログイン済み Chrome で本文抽出(フル実行の核)

ユーザーの**認証済み Chrome セッション**で開いて本文を取る。新しい無名
ブラウザではログイン壁に当たるので、**既存プロファイルに接続**する。

ローカル Claude Code での代表手段(環境に合う方を選ぶ):

1. **CDP で既存 Chrome に接続**(推奨。ログイン状態をそのまま使える)
   ```bash
   # Chrome をデバッグポート付きで起動済みにしておく(ユーザー環境の前提):
   #   "Google Chrome" --remote-debugging-port=9222 --profile-directory=Default
   # その上で Playwright から接続:
   #   chromium.connectOverCDP("http://127.0.0.1:9222") → 既存タブで goto → innerText
   ```
2. **AppleScript で Chrome を操作**(Mac、追加依存なし)
   ```bash
   open -a "Google Chrome" "<status_or_article_url>"
   # 読み込み後、front document の本文テキストを取得して標準出力へ
   ```

抽出するもの: 投稿本文(全文。"さらに表示"の省略を展開)、投稿者、
日時、スレッドなら連投分、引用元があれば引用先の本文も。
画像内テキストが要点に効くなら、その旨を記録(別途 OCR は任意)。

### Step 3 — 要点化

抽出本文から、ユーザーが必要としている粒度で要点を出す。
原文の直接コピペは最小限にし、**言い換え主体**(SEN System Prompt
"Default to paraphrasing over quoting")。複数 URL なら横断で論点を束ねる。

### Step 4 — 必要なら SEN へ精製(任意)

ユーザーが SEN 文脈(視差・批判・実装示唆)で扱いたい時のみ。
- 25条のどれに接続するか
- 視差(別角度)を1つ
- このリポジトリ(SEN Design)への含意があれば短く

頼まれていなければやらない(第7条:抽象は実行者が勝手に足さない)。

---

## フォールバック(x.com に届かない環境)

`network: false` の時。ここで詰まない。正直に縮退して、選択肢を出す:

1. **委譲** — 到達できる実行主体(ローカル Claude Code / Codex)へこの
   ルートを振り、抽出済み本文テキストだけ持ち帰る。SEN Routing Log の
   委譲パターン(#7)と同型。
2. **直貼り** — ユーザーに本文 or スクショを貼ってもらう。最速。
3. **回線変更** — x.com / twimg.com を許可した egress ポリシーで
   セッションを作り直す(恒久対処)。

resolver の `candidates` と `note` はフォールバック時もそのまま渡せる
(正規 URL は判っているので、委譲先は抽出だけやればいい)。

---

## やらないこと(摩擦配置/第4条・第5条)

- TLS 検証の無効化やプロキシ回避で遮断を「突破」しない。届かないなら
  届かないと報告する(回避は禁止)。
- 認証 Cookie / セッショントークンをファイルや外部へ書き出さない
  (データ主権・第5条)。Chrome の中だけで完結させる。
- ユーザーの Chrome で**閲覧以外**(投稿・いいね・DM 等)を一切しない。
  読み取り専用。

---

## 出力フォーマット(引き継ぎ)

- 取り込んだ URL と、解決後の正規 URL
- 本文の要点(言い換え主体)
- フル実行 / 縮退 のどちらで取ったか(縮退なら何が欠けたか)
- (任意)SEN への含意・視差

毎回これを満たす。満たせない項目は空欄にせず「未達」と明記する。
