# Instagram → Apify → Horizon (GitHub)

This extension lives in your Horizon fork, not in a separate SaaS product. It does **not** replace Horizon.

## Ready now
- An Instagram-specific editorial profile with Persian output prompts.
- A Python bridge from a preconfigured Apify **task** to RSS and a local history/report.
- A manual GitHub Actions workflow. No scheduled scraping or paid run is triggered merely by merging this code.
- Optional Horizon analysis after configuring a DeepSeek API key.

## One-time setup
1. In Apify, open `deepmine/instagram-reels-search`, set your Persian/English topic keywords (start with two), max **10 Reels per keyword**, last **30 days**, and a strict **maximum cost per run**. Save these settings as an Apify **Task**; copy its task ID. If your actor cannot create tasks on your plan, do not supply an arbitrary actor ID as a substitute.
2. In the **GitHub fork**, navigate to `Settings → Secrets and variables → Actions → New repository secret`. Create `APIFY_TOKEN` (from Apify API tokens) and `APIFY_TASK_ID` (the saved task ID). Do **not** paste either token into a chat or a tracked repository file.
3. In `Actions → Instagram radar (Apify to Horizon) → Run workflow`, run once. Apify may charge per record or run; the cap belongs inside the Apify task and account controls.
4. Download the `instagram-radar-report` artifact or view `data/instagram_radar/report.md` after the run.
5. Optionally add `DEEPSEEK_API_KEY` as a secret to let the existing Horizon AI analyze this feed and produce Persian idea suggestions. Without it, collection + statistical report still work but Horizon's AI stage is skipped.

## Important data-quality limitations
- Keyword-search results are not a random sample of Instagram; the feed cannot prove worldwide trend growth.
- A measured outlier ratio is provided **only if at least three OTHER sampled reels from the same creator are present in history**. Otherwise the report explicitly marks the baseline insufficient.
- Public views, likes and comments are observations returned by the third-party scraper, not verified private analytics. Shares, saves, retention, and follower conversion are not inferred.
- This fork and its history are public unless you change repository visibility. Public usernames, captions and URLs can appear in generated history.

## Code behavior
The bridge runs a SAVED Apify task with the Apify API, polls the run, downloads up to 150 records, normalizes them, updates a capped history, and generates an RSS feed. Horizon's existing RSS scraper reads this feed from a temporary localhost server when the AI key is present. No changes to Horizon core modules are required.

## Planned later step
After one successful, cost-checked trial, add an explicit scheduled trigger and decide whether to publish daily summaries to GitHub Pages. Neither is enabled by default.
