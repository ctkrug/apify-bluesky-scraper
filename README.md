# Bluesky Scraper (Apify Actor)

Scrape Bluesky public data — **author feeds and profiles need no login**; keyword search uses an
optional app password. Targets an **underserved marketplace niche**: Bluesky has 30M+ users but the
leading scraper had ~240 users (wiki research). Pull-based distribution = Apify marketplace discovery.

> POC #6 from the wiki research. Public client is pure/dep-free (`src/bsky.py`) and verified live.

## Modes
- `author` — an account's posts (no auth). ✅ verified
- `profile` — an account's stats (followers/posts/etc.) (no auth). ✅ verified
- `search` — keyword search. ⚠️ Bluesky's `searchPosts` now **requires auth** → pass `identifier` +
  `appPassword` (created at bsky.app → Settings → App Passwords; never your main password).

## Run locally
```bash
python3 -c "from src.bsky import author_feed; print(len(author_feed('bsky.app',5)),'posts')"
pip install apify && apify run   # full actor run
```

## Publish (your Apify account — the one manual step)
```bash
npm i -g apify-cli && apify login && apify push
```
Pay-per-event billing is already **wired into the code** (`actor-start` + `result-item`). After
`apify push`, create those two events with matching names + prices in the Console and publish — full
step-by-step (event names that MUST match, suggested prices) in **[PUBLISH.md](PUBLISH.md)**.

**Why it can win:** weak incumbent + growing platform + open protocol (the research's exact "winnable
niche" pattern). Differentiate on reliability + the no-login author/profile modes.

## Output
Per post (rich): uri, **url** (clickable bsky.app link), cid, text, createdAt, indexedAt,
author handle/displayName/did/avatar, like/repost/reply/**quote** counts, langs, isReply/isRepost,
reply parent+root URIs, **hashtags**, **mentionDids**, **links**, **images** (url + alt),
**externalLink** (link card), and **quotedPost**. Author mode can drop replies/reposts; search mode
supports sort (top/latest), since/until dates, lang, hashtag, and from-author filters.
(profile mode: did, handle, displayName, description, follower/follow/post counts, avatar, banner, createdAt.)
