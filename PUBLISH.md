# Publishing this Actor + setting Pay-Per-Event pricing

The code is already **monetization-wired**: it charges two events via the Apify SDK
(`src/main.py`). Those events earn **nothing** until you create matching events (same names) in
the Apify Console and publish the Actor. Do that here.

## 1. Push to your Apify account (2 commands)

```bash
cd apify-bluesky-scraper
apify login            # paste your Apify API token (console.apify.com → Settings → Integrations → API token)
apify push             # builds + uploads this Actor to your account
```

`apify` CLI: `npm i -g apify-cli` (or `npx apify-cli@latest login` / `... push` with no global install).

## 2. Turn on Pay-Per-Event pricing (Apify Console)

Open the Actor → **Publication → Monetization** → choose **Pay per event** → run the wizard.

Create exactly these two events — **the names must match the code character-for-character**
(`src/main.py` calls `Actor.charge("actor-start")` and `Actor.push_data(row, "result-item")`).
A name mismatch silently bills **$0**.

| Event name (exact) | When the code charges it | Suggested price (tune freely) |
|---|---|---|
| `actor-start`  | Once per run (fixed overhead)        | **$0.005** |
| `result-item`  | Per post/profile record returned     | **$0.0008** (≈ $0.80 / 1,000 records) |

The wizard may pre-create a default `apify-actor-start` and an `apify-default-dataset-item` event.
**Delete those (or rename the start one to `actor-start`)** and add the two above — the code does NOT
charge the default names, so leaving them would either bill nothing or, for the dataset-item one,
risk double-charging. Keep it to just `actor-start` + `result-item`.

Pricing rationale: Bluesky is an underserved niche (30M+ users, weak incumbent scraper), so compete
on price. ~$0.80/1k posts is in line with cheap Apify scrapers while the start fee keeps tiny runs
profitable. Raise `result-item` later if adoption is healthy.

## 3. Publish to the Store

Same screen → **Publish to Apify Store**. Fill SEO title/description/categories (social-media
scraping, Bluesky). Distribution is then pure marketplace pull — no outreach needed.

## How the billing works (for reference)

- `await Actor.charge("actor-start")` — one fixed charge at run start.
- `await Actor.push_data(row, "result-item")` — pushes the row **and** charges one `result-item`;
  the SDK auto-stops at the buyer's per-run budget. The loop also breaks on
  `event_charge_limit_reached` so we never do unpaid work.
- On non-PPE or local runs these calls are no-ops (data still pushed), so the Actor runs fine either way.
