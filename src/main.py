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

        # Pay-per-event monetization. Two events (configure matching names + prices in the
        # Apify Console → Monetization wizard): a fixed "actor-start" fee covering run overhead,
        # then "result-item" per record returned. On non-PPE/local runs charge() is a no-op and
        # all data is still pushed, so the actor works either way. See PUBLISH.md.
        await Actor.charge("actor-start")

        if mode == "profile":
            handle = inp.get("handle") or _need("handle")
            await Actor.push_data(get_profile(handle), "result-item")
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

        pushed = 0
        for r in rows:
            result = await Actor.push_data(r, "result-item")
            pushed += 1
            # Stop once the buyer's per-run budget is spent (avoids paying for compute that earns nothing).
            if result and result.event_charge_limit_reached:
                Actor.log.info("pay-per-event budget reached — stopping early")
                break
        Actor.log.info(f"pushed {pushed} records")


def _need(field):
    raise RuntimeError(f"'{field}' is required for this mode")
