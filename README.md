# Bharat Bima Social Scraper

Automated weekly news digest for Bharat Bima Insurance Broking. Scrapes insurance and MFI-related news every Monday, summarizes it with Claude, saves a markdown digest, and logs everything to Google Sheets.

---

## What it does

1. Pulls articles from 8 RSS feeds (ET, LiveMint, MoneyControl, Google News) and scrapes IRDAI press releases + circulars
2. Filters to the last 7 days, deduplicates by URL
3. Sends all items to Claude (claude-sonnet-4-6) for a structured digest with LinkedIn signals
4. Saves `digests/YYYY-MM-DD-digest.md` and `digests/latest.md`
5. Appends each article to a **Google Sheet** (Articles tab) and logs the digest (Digests tab)
6. Runs automatically every Monday at 6:00 AM IST via GitHub Actions

---

## Running locally

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and fill in your env vars
cp .env.example .env
# edit .env with your keys

# Full run
python main.py

# Dry run (no files saved, no Sheets write)
python main.py --dry-run
```

---

## Adding new RSS sources

Edit `scraper/sources.py`. Add a dict to the `SOURCES` list:

```python
{
    "name": "My Source",
    "url": "https://example.com/rss.xml",
    "type": "rss",          # or "scrape" for HTML pages
    "priority": "medium",   # "high" or "medium"
    "tags": ["Market"],     # any of: IRDAI, Regulation, Group Health, Group Life, MFI, Microfinance, Market, Industry
},
```

---

## Google Sheets setup

### Sheet structure

Create a Google Sheet with **two tabs**:

| Tab name | Columns |
|----------|---------|
| `Articles` | Date · Week · Source · Title · URL · Summary · Tags · LinkedIn Signal |
| `Digests` | Date · Week · Item Count · Digest Markdown |

Headers are written automatically on the first run — you just need the two empty tabs.

### Authentication (Service Account)

1. Go to [Google Cloud Console](https://console.cloud.google.com) → Create or select a project
2. Enable **Google Sheets API**
3. Create a **Service Account** (IAM & Admin → Service Accounts)
4. Create a key for the service account → download as JSON
5. Open your Google Sheet → Share it with the service account email (e.g. `mybot@my-project.iam.gserviceaccount.com`) with **Editor** access
6. Copy the Sheet ID from the URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`

### Set env vars

```
GOOGLE_SERVICE_ACCOUNT_JSON=<paste entire JSON as one line>
GOOGLE_SHEET_ID=your_sheet_id
```

---

## GitHub Actions setup

Add three **Repository Secrets** (Settings → Secrets → Actions):

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Entire service account JSON (one line) |
| `GOOGLE_SHEET_ID` | Your Google Sheet ID |

The workflow runs every Monday at 6:00 AM IST and commits the digest file back to the repo. You can also trigger it manually from the Actions tab.

---

## How to generate LinkedIn posts

Once the Monday digest runs:

1. Open `digests/latest.md` (or the Digests tab in your Sheet)
2. Go to Claude.ai
3. Paste the digest and say:

> *"Here is this week's Bharat Bima digest. Generate two LinkedIn posts — one current/newsy, one educational. Use our voice: confident, plain-language, mission-driven."*

4. Review and schedule
