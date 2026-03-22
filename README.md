<div align="center">
  <h1>📡 Job Radar</h1>
  <p><strong>An Automated, AI-Enriched, Serverless Job Intelligence Pipeline & Cyberpunk Dashboard</strong></p>
  
  [![GitHub Actions](https://img.shields.io/badge/Automated-GitHub_Actions-2088FF?style=for-the-badge&logo=githubactions)](https://github.com/features/actions)
  [![UI/UX](https://img.shields.io/badge/UI-Cyberpunk_Glassmorphism-FF0055?style=for-the-badge)](./docs/index.html)
  [![AI](https://img.shields.io/badge/AI_Powered-Gemini_2.0_Flash-4285F4?style=for-the-badge&logo=google)](https://aistudio.google.com/)
</div>

---

## 🌟 The Vision
Job hunting across fragmented platforms is exhausting. **Job Radar** revolutionizes this by aggregating high-quality Tech, Data, and AI roles from over 12 global and local platforms into a single, lightning-fast, visually stunning dashboard. 

Built entirely on **Serverless Architecture** (GitHub Actions + GitHub Pages), this project costs **$0 to run** while delivering enterprise-grade data pipelines and a premium user experience.

---

## 🏗 Data Scraping Architecture
Job Radar employs a multi-tiered, resilient scraping engine designed to bypass anti-bot measures and normalize unstructured HTML/API data.

### 1. The Multi-Source Engine
We scrape across 4 distinct groups of sources:
- **Global Boards (JobSpy)**: LinkedIn, Indeed, Google Jobs.
- **Remote-First APIs**: RemoteOK, Jobicy, Himalayas.
- **Regional Giants (Vietnam)**: TopCV, ITviec, VietnamWorks.
- **Boutique/Startup Feeds**: Wellfound, Turing, WeWorkRemotely, Workable.

### 2. Gemini 2.0 AI Enrichment Pipeline
Raw scraped jobs are often messy. Our pipeline passes the raw text through **Google Gemini 2.0 Flash**, which acts as an intelligent normalizer:
- **Extracts technical skills** (e.g., Python, AWS, Snowflake).
- **Categorizes the role** (Data Engineering, ML/AI, Analytics, DevOps).
- **Cleans up** clickbait titles and normalizes location data.

### 3. Smart Deduplication
Every job generates a deterministic `ID` hash based on its Source and URL. The pipeline automatically loads the historical database (`jobs.json`) and surgically merges only newly discovered roles, updating their `scraped_at` timestamp.

---

## 🎨 UI/UX Excellence: The Cyberpunk Dashboard
The frontend (`docs/`) is a masterpiece of **Vanilla JavaScript and CSS3**, requiring zero build tools or hefty frameworks like React.

- **Cyberpunk Aesthetics**: Deep dark themes (`#0d0d12`), neon accents (`#63c8ff`, `#00ffb2`), and a custom interactive cursor ring that visually snaps to clickable elements.
- **Fluid Layout**: Expanded to 1600px max-width to fully utilize modern wide monitors.
- **Client-Side Blazing Speed**: All filtering, searching, and sorting across thousands of nodes happens instantly in-memory.
- **Multidimensional Filtering**: Filter simultaneously by *Domain Pattern* (e.g., `supply chain`, `data engineer`), *Source*, *Level*, *Location*, and *Freshness*.
- **Admin Command Center**: A simulated "Admin" tab featuring local config management, keyword injections, and an animated progress terminal mimicking the backend CI/CD pipeline.

---

## 🚀 Quick Setup Guide

Run your own instance of Job Radar in under 5 minutes.

### 1. Local Configuration

```bash
# Clone the repository
git clone https://github.com/yourusername/job-radar.git
cd job-radar

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure your desired search keywords
vim config/keywords.yml
```

### 2. Run the Engine Locally

```bash
export GEMINI_API_KEY="your-gemini-key"
python main.py

# The orchestrator will scrape, enrich, and save to data/jobs.json!
```

### 3. Deploy to GitHub (Serverless)
Job Radar is designed to run automatically **3 times a day** via GitHub Actions.

1. Commit and push your changes to GitHub.
2. Go to your Repository **Settings → Pages** and set the source to deploy from the `main` branch, `/docs` folder.
3. Go to **Settings → Secrets and variables → Actions** and add:
   - `GEMINI_API_KEY`: Your Google AI Studio API key.
   - `ITVIEC_SESSION`: (Optional) Your browser cookie for ITviec scraping.
4. Go to the **Actions** tab and manually trigger the `Scrape Jobs` workflow for the first time.

Sit back and watch the jobs flow into your beautifully hosted GitHub Pages dashboard!

---

## 🛠 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend / Scraper** | Python 3.11, `requests`, `python-jobspy`, `playwright-stealth`, `feedparser` |
| **AI Processing** | `google-genai` (Gemini 2.0 Flash) |
| **Automation** | GitHub Actions (Cron + Workflow Dispatch) |
| **Frontend UI** | HTML5, CSS3, Vanilla JavaScript (ES6) |
| **Data Viz & Icons**| Chart.js, Lucide Icons |
| **Database** | Static JSON (`jobs.json`) |

---
<div align="center">
  <p>Built with ❤️ by an AI Agent & A Human Developer</p>
</div>
