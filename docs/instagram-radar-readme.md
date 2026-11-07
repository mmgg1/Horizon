# Horizon Instagram Trend Radar — prepared integration (not yet deployed)

The repository contains a testable Apify-to-Horizon bridge. It has **not been installed into your GitHub repository** because the connected GitHub integration does not currently have permission to create a branch or write files (HTTP 403). No paid Apify run was started.

Included files:
- `scripts/instagram_radar.py` — reads a saved Apify task and converts results to RSS + a historical statistics table.
- `.github/workflows/instagram-radar.yml` — manual GitHub Actions workflow; no schedule yet.
- `profiles/content-trend-radar/*` — custom broad-topic content discovery / Persian editorial instructions.
- `INSTAGRAM_RADAR_SETUP.md` — setup and secrets guide.

After GitHub write permissions are available, these files can be added to a separate feature branch for review, without changing the existing working Horizon pipeline.
