"""Bluesky public AppView client — NO auth required (uses public.api.bsky.app).
Pure, dep-free, testable standalone. Covers the two highest-demand scrapes: search + author feed."""
import json, urllib.parse, urllib.request

BASE = "https://public.api.bsky.app/xrpc"
UA = "Mozilla/5.0 (compatible; BlueskyScraper/0.1)"


def _get(method: str, params: dict):
    url = f"{BASE}/{method}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def _flatten(post: dict) -> dict:
    p = post.get("post", post)
    rec = p.get("record", {}) or {}
    author = p.get("author", {}) or {}
    return {
        "uri": p.get("uri"),
        "text": rec.get("text"),
        "createdAt": rec.get("createdAt"),
        "authorHandle": author.get("handle"),
        "authorDisplayName": author.get("displayName"),
        "likeCount": p.get("likeCount"),
        "repostCount": p.get("repostCount"),
        "replyCount": p.get("replyCount"),
        "langs": rec.get("langs"),
    }


def get_profile(handle: str) -> dict:
    """Public profile (no auth)."""
    d = _get("app.bsky.actor.getProfile", {"actor": handle})
    return {k: d.get(k) for k in ("did", "handle", "displayName", "description",
                                  "followersCount", "followsCount", "postsCount", "avatar")}


def login(identifier: str, app_password: str) -> str:
    """Exchange a handle + app-password for an access token (for endpoints that need auth, e.g. search).
    App passwords are created at bsky.app Settings → App Passwords (NOT your main password)."""
    body = json.dumps({"identifier": identifier, "password": app_password}).encode()
    req = urllib.request.Request("https://bsky.social/xrpc/com.atproto.server.createSession",
                                 data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["accessJwt"]


def search_posts(query: str, limit: int = 25, token=None):
    """Search recent posts. NOTE: searchPosts now requires auth — pass a `token` from login().
    Without a token this raises a clear error (use author/profile mode for no-auth scraping)."""
    if not token:
        raise RuntimeError("Bluesky searchPosts requires auth — provide identifier + appPassword "
                           "(or use mode=author / mode=profile, which need no login).")
    host = "https://bsky.social/xrpc"
    out, cursor = [], None
    while len(out) < limit:
        params = {"q": query, "limit": min(100, limit - len(out))}
        if cursor:
            params["cursor"] = cursor
        url = f"{host}/app.bsky.feed.searchPosts?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        for post in data.get("posts", []):
            out.append(_flatten({"post": post}))
        cursor = data.get("cursor")
        if not cursor or not data.get("posts"):
            break
    return out[:limit]


def author_feed(handle: str, limit: int = 25):
    """Public posts from one account."""
    out, cursor = [], None
    while len(out) < limit:
        params = {"actor": handle, "limit": min(100, limit - len(out))}
        if cursor:
            params["cursor"] = cursor
        data = _get("app.bsky.feed.getAuthorFeed", params)
        feed = data.get("feed", [])
        for item in feed:
            out.append(_flatten(item))
        cursor = data.get("cursor")
        if not cursor or not feed:
            break
    return out[:limit]
