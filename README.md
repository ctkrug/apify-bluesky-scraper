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
Set Pay-Per-Result/Event pricing in the console. **Why it can win:** weak incumbent + growing platform
+ open protocol (the research's exact "winnable niche" pattern). Differentiate on reliability + the
no-login author/profile modes.

## Output
Per post: uri, text, createdAt, authorHandle/DisplayName, like/repost/replyCount, langs.
(profile mode: did, handle, displayName, description, follower/follow/post counts.)
