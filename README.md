# 📡 Job Radar

**Automated Job Intelligence Dashboard** — scrapes 9+ job sources, deduplicates data, and serves a beautiful public dashboard via GitHub Pages. **Zero cost, zero infrastructure.**

---

## 🚀 Features

- **9+ Job Sources**: LinkedIn, Indeed, Google Jobs, RemoteOK, Himalayas, Jobicy, Wellfound, VietnamWorks, ITviec, TopCV, Turing
- **Auto-scraping**: GitHub Actions runs 3x daily (07:00, 14:00, 20:00 ICT)
- **Smart deduplication**: Stable job IDs prevent duplicate entries
- **Beautiful dashboard**: Dark-mode UI with charts, filters, search, and bookmarks
- **Zero cost**: Runs entirely on GitHub Actions free tier + GitHub Pages
- **Optional AI enrichment**: Gemini Flash extracts skills from job descriptions

## 📊 Dashboard Tabs

| Tab | Features |
|-----|----------|
| **Dashboard** | Stats cards, top jobs today/week/month, daily chart, source breakdown |
| **Browse** | Full-text search, multi-filter (source, location, remote, salary, tags, date), table/card view, pagination |
| **Analytics** | 30-day trends, top tags, source distribution, remote vs on-site, posting heatmap |
| **Saved** | Bookmark jobs, export to CSV, persistent via localStorage |
| **About** | Source list with counts, update schedule, tech stack |

## 🛠 Setup

### Prerequisites
- Python 3.11+
- GitHub account

### Local Development

```bash
# Clone and install
git clone <your-repo-url> job-radar
cd job-radar
pip install -r requirements.txt

# Configure search keywords
vim config/keywords.yml

# Run scrapers locally
python main.py

# View dashboard
# Copy data/jobs.json → docs/jobs.json, then open docs/index.html in browser
cp data/jobs.json docs/jobs.json
open docs/index.html
```

### GitHub Setup

1. **Push to GitHub**
2. **Settings → Pages → Source**: GitHub Actions
3. **Settings → Secrets** (optional):
   - `ITVIEC_SESSION`: Cookie from ITviec browser session
   - `GEMINI_API_KEY`: Google AI Studio API key

### Refreshing ITviec Session Cookie

1. Open [itviec.com](https://itviec.com) in Chrome
2. Browse or log in
3. DevTools → Application → Cookies → copy `_ITViec_session` value
4. Update GitHub Secret: `ITVIEC_SESSION`

## 🔧 Configuration

Edit `config/keywords.yml`:

```yaml
search_keywords:
  - "data engineer"
  - "ML engineer"

title_exclude:
  - "intern"
  - "student"

locations_include: []  # empty = all locations
min_salary_usd: 0
```

## 🧪 Tests

```bash
python -m pytest tests/ -v
```

## 📦 Tech Stack

| Layer | Tech |
|-------|------|
| Scraping | Python 3.11, requests, BeautifulSoup4, python-jobspy, Algolia, feedparser |
| CI/CD | GitHub Actions |
| Frontend | Vanilla JS, Tailwind CSS (CDN), Chart.js, Lucide Icons |
| Hosting | GitHub Pages |
| Data | Single `jobs.json` file |

## 📁 Project Structure

```
job-radar/
├── .github/workflows/    # Scrape + deploy automation
├── scrapers/             # 10 scraper modules (Groups A/B/C)
├── processor/            # Normalizer, dedup, filter
├── enricher/             # Optional Gemini enrichment
├── config/               # keywords.yml search config
├── data/                 # jobs.json (source of truth)
├── docs/                 # GitHub Pages (index.html + favicon)
├── tests/                # Unit tests
└── main.py               # Orchestrator entry point
```

## 📄 License

MIT
