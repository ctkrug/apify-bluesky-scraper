"""Apify Actor: scrape Bluesky public data.
  mode=author  -> an account's posts (no auth)
  mode=profile -> an account's profile stats (no auth)
  mode=search  -> keyword search (needs identifier + appPassword; searchPosts requires auth)
"""
from .bsky import search_posts, author_feed, get_profile, login


async def main():
    from apify import Actor
    async with Actor:
        inp = await Actor.get_input() or {}
        mode = inp.get("mode", "author")
        limit = int(inp.get("limit", 25))

        if mode == "profile":
            handle = inp.get("handle") or _need("handle")
            await Actor.push_data(get_profile(handle))
            return

        if mode == "author":
            handle = inp.get("handle") or _need("handle")
            Actor.log.info(f"author feed: {handle}")
            rows = author_feed(handle, limit)
        else:  # search
            query = inp.get("query") or _need("query")
            token = None
            ident, pw = inp.get("identifier"), inp.get("appPassword")
            if ident and pw:
                token = login(ident, pw)
            Actor.log.info(f"search: {query}")
            rows = search_posts(query, limit, token=token)

        for r in rows:
            await Actor.push_data(r)
        Actor.log.info(f"pushed {len(rows)} records")


def _need(field):
    raise RuntimeError(f"'{field}' is required for this mode")
