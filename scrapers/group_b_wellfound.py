"""
Wellfound (AngelList) scraper — HTML role pages.
Wellfound blocks automated requests with 403 Forbidden.
This scraper attempts with browser-like headers and falls back gracefully.
"""

import requests
import time
import re
from bs4 import BeautifulSoup
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id
from datetime import datetime


class WellfoundScraper(BaseJobScraper):
    source_name = "wellfound"

    ROLE_MAP = {
        "data engineer": "data-engineer",
        "data engineering": "data-engineer",
        "analytics engineer": "data-analyst",
        "ML engineer": "machine-learning-engineer",
        "machine learning engineer": "machine-learning-engineer",
        "data platform engineer": "data-engineer",
        "data scientist": "data-scientist",
        "ETL engineer": "data-engineer",
        "dbt engineer": "data-engineer",
    }

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
        jobs = []
        seen_urls = set()

        # Get unique role slugs
        slugs = set()
        for kw in keywords:
            slug = self.ROLE_MAP.get(kw.lower())
            if slug:
                slugs.add(slug)
        if not slugs:
            slugs = {"data-engineer"}

        for slug in slugs:
            # Try both /role/r/ (remote) and /role/ (all)
            for url_pattern in [
                f"https://wellfound.com/role/r/{slug}",
                f"https://wellfound.com/role/{slug}",
            ]:
                try:
                    time.sleep(2)
                    resp = requests.get(url_pattern, headers=headers, timeout=15)
                    if resp.status_code == 403:
                        print(f"[wellfound] 403 Forbidden for {slug} — anti-bot protection")
                        continue
                    if resp.status_code != 200:
                        continue
                except requests.RequestException as e:
                    print(f"[wellfound] Request failed for {slug}: {e}")
                    continue

                soup = BeautifulSoup(resp.text, "html.parser")

                # Method 1: Find Apollo state / JSON data
                scripts = soup.select("script")
                for script in scripts:
                    text = script.get_text()
                    if "startup" in text.lower() or "job" in text.lower():
                        # Try to find JSON job data
                        json_matches = re.findall(r'"title"\s*:\s*"([^"]+)"', text)
                        url_matches = re.findall(r'"(https?://wellfound\.com/jobs/[^"]+)"', text)
                        for i, title in enumerate(json_matches):
                            if len(title) < 5:
                                continue
                            job_url = url_matches[i] if i < len(url_matches) else f"https://wellfound.com/role/{slug}#{i}"
                            if job_url in seen_urls:
                                continue
                            seen_urls.add(job_url)
                            jobs.append(Job(
                                id=generate_job_id(self.source_name, job_url),
                                source=self.source_name,
                                url=job_url,
                                title=title,
                                company="N/A",
                                location="Remote",
                                is_remote=True,
                                salary="N/A",
                                tags=[slug.replace("-", " ")],
                                scraped_at=datetime.now().isoformat(),
                                first_seen=datetime.now().isoformat(),
                            ))

                # Method 2: Find job links in HTML
                job_links = soup.find_all("a", href=re.compile(r"/jobs/\d"))
                for link in job_links:
                    href = link.get("href", "")
                    job_url = href if href.startswith("http") else f"https://wellfound.com{href}"
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    title = link.get_text(strip=True)
                    if not title or len(title) < 5:
                        continue

                    jobs.append(Job(
                        id=generate_job_id(self.source_name, job_url),
                        source=self.source_name,
                        url=job_url,
                        title=title,
                        company="N/A",
                        location="Remote",
                        is_remote=True,
                        salary="N/A",
                        tags=[slug.replace("-", " ")],
                        scraped_at=datetime.now().isoformat(),
                        first_seen=datetime.now().isoformat(),
                    ))

                if jobs:
                    break

            if len(jobs) >= max_results:
                break

        if not jobs:
            print("[wellfound] No jobs found — site blocks automated requests (403)")

        return jobs[:max_results]
