"""Bluesky public AppView client — NO auth required for author/profile (uses public.api.bsky.app).
Pure, dep-free, testable standalone. Rich extraction: media, links, quoted posts, hashtags/mentions,
thread context, engagement counts, and a clickable post URL — not just bare text."""
from __future__ import annotations
import json, time, urllib.parse, urllib.request, urllib.error

BASE = "https://public.api.bsky.app/xrpc"
AUTH_HOST = "https://bsky.social/xrpc"
UA = "Mozilla/5.0 (compatible; BlueskyScraper/0.2; +https://apify.com)"


def _open(url: str, headers: dict, retries: int = 3):
    """GET with a clean error message + simple 429/5xx backoff. Raises a readable RuntimeError
    on failure instead of leaking a raw urllib stack trace (which would crash the Actor)."""
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json", **headers})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                pass
            # Rate-limited or transient server error → back off and retry.
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                wait = int(e.headers.get("retry-after", 0)) or (2 ** attempt)
                time.sleep(min(wait, 10))
                last = e
                continue
            msg = body
            try:
                msg = json.loads(body).get("message", body)
            except Exception:
                pass
            raise RuntimeError(f"Bluesky API error {e.code}: {msg or e.reason}") from None
        except urllib.error.URLError as e:
            last = e
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Network error reaching Bluesky: {e.reason}") from None
    raise RuntimeError(f"Bluesky request failed after {retries} attempts: {last}")


def _get(method: str, params: dict):
    return _open(f"{BASE}/{method}?{urllib.parse.urlencode(params)}", {})


def _post_url(uri: str, handle: str) -> str | None:
    """at://did/app.bsky.feed.post/<rkey>  ->  https://bsky.app/profile/<handle>/post/<rkey>"""
    if not uri or "/" not in uri:
        return None
    rkey = uri.rsplit("/", 1)[-1]
    return f"https://bsky.app/profile/{handle or 'unknown'}/post/{rkey}" if rkey else None


def _facets(rec: dict) -> dict:
    """Pull hashtags, mentions (dids), and in-text links out of richtext facets."""
    tags, mentions, links = [], [], []
    for f in rec.get("facets", []) or []:
        for feat in f.get("features", []) or []:
            t = feat.get("$type", "")
            if t.endswith("#tag") and feat.get("tag"):
                tags.append(feat["tag"])
            elif t.endswith("#mention") and feat.get("did"):
                mentions.append(feat["did"])
            elif t.endswith("#link") and feat.get("uri"):
                links.append(feat["uri"])
    return {"hashtags": tags, "mentionDids": mentions, "links": links}


def _embed(p: dict) -> dict:
    """Extract media images, an external link card, and any quoted post from the hydrated view embed."""
    images, external, quoted = [], None, None
    emb = p.get("embed") or {}
    t = emb.get("$type", "")

    # recordWithMedia wraps a media embed + a quoted record.
    media = emb
    if "recordWithMedia" in t:
        media = emb.get("media") or {}
        rec_view = (emb.get("record") or {}).get("record")
        quoted = _quoted(rec_view)
        t = media.get("$type", "")

    if "embed.images" in t:
        for im in media.get("images", []) or []:
            images.append({"url": im.get("fullsize") or im.get("thumb"), "alt": im.get("alt") or None})
    elif "embed.video" in t:
        images.append({"url": media.get("playlist") or media.get("thumbnail"), "alt": media.get("alt") or None})
    elif "embed.external" in t:
        ext = media.get("external") or {}
        external = {"uri": ext.get("uri"), "title": ext.get("title"), "description": ext.get("description")}
    elif "embed.record" in t and quoted is None:
        quoted = _quoted(emb.get("record"))

    return {"images": images, "externalLink": external, "quotedPost": quoted}


def _quoted(rec_view: dict | None) -> dict | None:
    """Summarize a quoted/embedded post view."""
    if not isinstance(rec_view, dict):
        return None
    val = rec_view.get("value") or {}
    author = rec_view.get("author") or {}
    if not (rec_view.get("uri") or val.get("text")):
        return None
    return {
        "uri": rec_view.get("uri"),
        "authorHandle": author.get("handle"),
        "text": val.get("text"),
    }


def _flatten(post: dict) -> dict:
    p = post.get("post", post)
    rec = p.get("record", {}) or {}
    author = p.get("author", {}) or {}
    reply = rec.get("reply") or {}
    emb = _embed(p)
    return {
        "uri": p.get("uri"),
        "cid": p.get("cid"),
        "url": _post_url(p.get("uri"), author.get("handle")),
        "text": rec.get("text"),
        "createdAt": rec.get("createdAt"),
        "indexedAt": p.get("indexedAt"),
        "authorHandle": author.get("handle"),
        "authorDisplayName": author.get("displayName"),
        "authorDid": author.get("did"),
        "authorAvatar": author.get("avatar"),
        "likeCount": p.get("likeCount"),
        "repostCount": p.get("repostCount"),
        "replyCount": p.get("replyCount"),
        "quoteCount": p.get("quoteCount"),
        "langs": rec.get("langs"),
        "isReply": bool(reply),
        "replyParentUri": (reply.get("parent") or {}).get("uri"),
        "replyRootUri": (reply.get("root") or {}).get("uri"),
        "hashtags": _facets(rec)["hashtags"],
        "mentionDids": _facets(rec)["mentionDids"],
        "links": _facets(rec)["links"],
        "images": emb["images"],
        "externalLink": emb["externalLink"],
        "quotedPost": emb["quotedPost"],
    }


def get_profile(handle: str) -> dict:
    """Public profile (no auth)."""
    d = _get("app.bsky.actor.getProfile", {"actor": handle})
    return {k: d.get(k) for k in ("did", "handle", "displayName", "description",
                                  "followersCount", "followsCount", "postsCount",
                                  "avatar", "banner", "createdAt", "indexedAt")}


def login(identifier: str, app_password: str) -> str:
    """Exchange a handle + app-password for an access token (for endpoints that need auth, e.g. search).
    App passwords are created at bsky.app Settings → App Passwords (NOT your main password)."""
    body = json.dumps({"identifier": identifier, "password": app_password}).encode()
    req = urllib.request.Request(f"{AUTH_HOST}/com.atproto.server.createSession",
                                 data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["accessJwt"]
    except urllib.error.HTTPError as e:
        raise RuntimeError("Bluesky login failed — check the handle + app password "
                           "(create one at bsky.app → Settings → App Passwords).") from None


def search_posts(query: str, limit: int = 25, token=None, sort=None, since=None,
                 until=None, lang=None, tag=None, author=None):
    """Search posts. searchPosts requires auth — pass a `token` from login().
    Optional filters map straight to the Bluesky API: sort ('top'|'latest'), since/until (ISO or YYYY-MM-DD),
    lang (e.g. 'en'), tag (hashtag without #), author (handle)."""
    if not token:
        raise RuntimeError("Bluesky searchPosts requires auth — provide identifier + appPassword "
                           "(or use mode=author / mode=profile, which need no login).")
    out, cursor = [], None
    while len(out) < limit:
        params = {"q": query, "limit": min(100, limit - len(out))}
        for k, v in (("sort", sort), ("since", since), ("until", until),
                     ("lang", lang), ("tag", tag), ("author", author)):
            if v:
                params[k] = v
        if cursor:
            params["cursor"] = cursor
        data = _open(f"{AUTH_HOST}/app.bsky.feed.searchPosts?{urllib.parse.urlencode(params)}",
                     {"Authorization": f"Bearer {token}"})
        posts = data.get("posts", [])
        for post in posts:
            out.append(_flatten({"post": post}))
        cursor = data.get("cursor")
        if not cursor or not posts:
            break
    return out[:limit]


def author_feed(handle: str, limit: int = 25, include_replies: bool = True, include_reposts: bool = True):
    """Public posts from one account (no auth). Optionally drop replies and/or reposts."""
    out, cursor = [], None
    filt = "posts_with_replies" if include_replies else "posts_no_replies"
    while len(out) < limit:
        params = {"actor": handle, "limit": min(100, limit - len(out)), "filter": filt}
        if cursor:
            params["cursor"] = cursor
        data = _get("app.bsky.feed.getAuthorFeed", params)
        feed = data.get("feed", [])
        for item in feed:
            # A repost arrives with a `reason` of type #reasonRepost.
            is_repost = bool(item.get("reason"))
            if is_repost and not include_reposts:
                continue
            row = _flatten(item)
            row["isRepost"] = is_repost
            out.append(row)
        cursor = data.get("cursor")
        if not cursor or not feed:
            break
    return out[:limit]
