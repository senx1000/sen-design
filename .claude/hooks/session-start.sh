#!/bin/bash
# SessionStart hook — SEN 能動発動リマインダ
# .claude/skills/*/SKILL.md を自動スキャンし、目録＋能動発動の指示を
# セッション文脈に注入する。新しい Skill を足しても書き換え不要（自動発見型）。
set -uo pipefail

SKILLS_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}/.claude/skills"

cat <<'HEADER'
[SEN 能動発動リマインダ / auto-generated]
このリポジトリには以下の「手足（Skill）」が生えている。
ユーザーはコマンド名を覚えていない前提で動くこと。
下の「発動状況」に合う意図・症状（例：「またCodexに同じ説明してる」
「これ手作業で何十件やるのか」「作業台にしたい」）が会話に現れたら、
待たずに該当 Skill を提案・起動する。受動的に手作業で処理しない。
どれを使うか曖昧なときは、実装を止めて一言確認する（第4条 摩擦配置 / 第7条）。

利用可能な Skill（name — 発動状況）:
HEADER

found=0
if [ -d "$SKILLS_DIR" ]; then
  for f in "$SKILLS_DIR"/*/SKILL.md; do
    [ -e "$f" ] || continue
    name=$(grep -m1 '^name:' "$f" | sed 's/^name:[[:space:]]*//')
    desc=$(grep -m1 '^description:' "$f" | sed 's/^description:[[:space:]]*//')
    [ -n "$name" ] || continue
    printf -- '- /%s — %s\n' "$name" "$desc"
    found=1
  done
fi
[ "$found" -eq 1 ] || echo '- (まだ Skill なし)'

cat <<'FOOTER'

新しい Skill を .claude/skills/<name>/SKILL.md に足せば、
次回セッションでこの目録は自動更新される（この Hook の書き換えは不要）。
発動を外した実例は SEN_Routing_Log.md に記録し、description を磨く（第11.5）。
FOOTER
