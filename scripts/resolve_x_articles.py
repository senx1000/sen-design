#!/usr/bin/env python3
"""resolve_x_articles.py — X(Twitter) リンクを「本文抽出の手前」まで正規化する。

役割(Claude Code 版 x-article-intake の第1段):
    X URL / t.co 短縮 → リダイレクト解決 → x.com の正規 URL 群に展開。
    本文抽出(ログイン済み Chrome)は次段の責務。ここはそのお膳立てだけ。

設計:
    - 標準ライブラリのみ(urllib)。どの環境でも追加依存なしで動く。
    - 1 入力 1 行 JSON で出力(複数 URL を一括処理できる)。
    - ネットワークに出られない環境(例: egress 制限された sandbox)では、
      解決を諦めて network=false で返す。捏造しない(第6条/正直性)。

使い方:
    python3 resolve_x_articles.py "https://t.co/xxxx" "https://x.com/user/status/123"
    echo "https://x.com/user/status/123" | python3 resolve_x_articles.py
    python3 resolve_x_articles.py --pretty <url>

出力(1 URL = 1 JSON):
    {
      "input": "...",
      "network": true,
      "resolved_url": "https://x.com/<user>/status/<id>",
      "host": "x.com",
      "username": "<user>",
      "status_id": "<id>",
      "candidates": {
        "status":      "https://x.com/<user>/status/<id>",
        "i_status":    "https://x.com/i/status/<id>",
        "i_article":   "https://x.com/i/article/<id>",
        "syndication": "https://cdn.syndication.twimg.com/tweet-result?id=<id>&lang=ja&token=a"
      },
      "note": null
    }
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
import urllib.error

# ブラウザ風 UA。素の Python UA だと弾かれやすい。
_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)
_TIMEOUT = 12
_SHORTENERS = {"t.co"}
_X_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"}

# x.com/<user>/status/<id> / x.com/i/status/<id> / x.com/i/article/<id> 等から id を拾う
_STATUS_RE = re.compile(r"/(?:i/(?:web/)?)?(?:status|statuses|article)/(\d+)")
_USER_RE = re.compile(r"^/([A-Za-z0-9_]{1,15})/(?:status|statuses)/\d+")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """1 ホップずつ Location を読むため、自動リダイレクトを止める。"""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: N802,D401
        return None


def _one_hop(url: str):
    """url を 1 回叩いて (final_or_none, location_or_none, error_or_none) を返す。"""
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": _UA})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        resp = opener.open(req, timeout=_TIMEOUT)
        return resp.geturl(), None, None
    except urllib.error.HTTPError as e:
        loc = e.headers.get("Location") if e.headers else None
        if e.code in (301, 302, 303, 307, 308) and loc:
            return None, loc, None
        # 403/405 等。t.co は HEAD/GET でも Location を返すことがあるので拾う
        loc = e.headers.get("Location") if e.headers else None
        if loc:
            return None, loc, None
        return None, None, f"HTTP {e.code}"
    except (urllib.error.URLError, OSError) as e:
        return None, None, str(getattr(e, "reason", e))


def _follow(url: str, max_hops: int = 8):
    """リダイレクトを手動追跡。(final_url, network_ok, error)。"""
    current = url
    last_err = None
    for _ in range(max_hops):
        final, loc, err = _one_hop(current)
        if final is not None:
            return final, True, None
        if loc is not None:
            # 相対 Location を絶対化
            if loc.startswith("//"):
                loc = "https:" + loc
            elif loc.startswith("/"):
                m = re.match(r"^(https?://[^/]+)", current)
                loc = (m.group(1) if m else "") + loc
            current = loc
            continue
        last_err = err
        break
    # 解決しきれなかった: ネットワーク自体が死んでいるか、最後のホップが err
    return current, last_err is None, last_err


def _host_of(url: str) -> str:
    m = re.match(r"^https?://([^/]+)", url, re.I)
    return (m.group(1) if m else "").lower()


def _build(input_url: str, resolved: str, network_ok: bool, err):
    host = _host_of(resolved)
    path = re.sub(r"^https?://[^/]+", "", resolved, flags=re.I)

    status_id = None
    m = _STATUS_RE.search(path)
    if m:
        status_id = m.group(1)

    username = None
    mu = _USER_RE.match(path)
    if mu and mu.group(1) != "i":  # "i" は予約セグメント(ユーザー名ではない)
        username = mu.group(1)

    candidates = {}
    if status_id:
        user_seg = username or "i"
        candidates = {
            "status": f"https://x.com/{user_seg}/status/{status_id}",
            "i_status": f"https://x.com/i/status/{status_id}",
            # X Articles(長文)を見るときの形。Codex 版の手順に合わせて候補に残す。
            # status か article かは本文抽出時に確定する(ここでは候補提示に留める)。
            "i_article": f"https://x.com/i/article/{status_id}",
            "syndication": (
                f"https://cdn.syndication.twimg.com/tweet-result?id={status_id}"
                f"&lang=ja&token=a"
            ),
        }

    note = None
    if not network_ok:
        note = (
            "network unreachable from this environment; resolution skipped. "
            "Run where x.com / t.co egress is allowed (e.g. local Claude Code)."
        )
    elif err:
        note = f"partial: {err}"
    elif host in _SHORTENERS:
        note = "still a shortener after follow; redirect not exposed."
    elif not status_id and host in _X_HOSTS:
        note = "x.com URL but no status/article id found (profile or non-post URL?)."

    return {
        "input": input_url,
        "network": bool(network_ok),
        "resolved_url": resolved,
        "host": host,
        "username": username,
        "status_id": status_id,
        "candidates": candidates,
        "note": note,
    }


def probe_reachable(url: str):
    """url に実際に到達できるか。(reachable_bool, detail)。

    resolver の `network` は「パースにネットが要ったか」でしかない。
    本文抽出(Step 2)の可否は、x.com に**実際に届くか**で決まる。
    egress 遮断環境では CONNECT トンネル 403 等で UNREACHABLE になる。
    """
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": _UA})
    try:
        urllib.request.urlopen(req, timeout=_TIMEOUT)
        return True, "ok"
    except urllib.error.HTTPError as e:
        # 401/403/404 等が返る = サーバには届いている(到達は可)
        return True, f"HTTP {e.code} (reached)"
    except (urllib.error.URLError, OSError) as e:
        reason = getattr(e, "reason", e)
        return False, f"{type(e).__name__}: {reason}"


def resolve(url: str, do_probe: bool = False) -> dict:
    url = url.strip()
    if not url:
        return _build(url, url, True, None)
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    host = _host_of(url)
    # 既に x.com の status 直リンクなら、ネットワークに出ずに展開できる
    if host in _X_HOSTS and _STATUS_RE.search(url):
        result = _build(url, url, True, None)
    else:
        # t.co 等はリダイレクト解決が要る
        resolved, network_ok, err = _follow(url)
        result = _build(url, resolved, network_ok, err)
    if do_probe:
        target = result["candidates"].get("status") or result["resolved_url"]
        reachable, detail = probe_reachable(target)
        result["reachable"] = reachable  # x.com に実際に届くか(抽出可否の真の判定)
        result["reachable_detail"] = detail
        if not reachable:
            result["note"] = (
                "x.com unreachable (extraction not possible here). "
                f"{detail}. Use fallback: delegate to local Claude Code / Codex, "
                "or paste the text."
            )
    return result


def _iter_inputs(argv):
    args = [a for a in argv if not a.startswith("-")]
    if args:
        yield from args
    else:
        for line in sys.stdin:
            line = line.strip()
            if line:
                yield line


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    pretty = "--pretty" in argv
    do_probe = "--probe" in argv
    any_input = False
    for url in _iter_inputs(argv):
        any_input = True
        result = resolve(url, do_probe=do_probe)
        if pretty:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
    if not any_input:
        sys.stderr.write(
            "usage: resolve_x_articles.py [--pretty] <x_or_tco_url> [more...]\n"
            "       echo <url> | resolve_x_articles.py\n"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
