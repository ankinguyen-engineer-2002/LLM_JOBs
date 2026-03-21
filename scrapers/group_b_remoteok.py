"""
RemoteOK scraper — public JSON API.
Endpoint: GET https://remoteok.com/remote-jobs.json
"""

import requests
import time
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime


class RemoteOKScraper(BaseJobScraper):
    source_name = "remoteok"
    API_URL = "https://remoteok.com/remote-jobs.json"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        time.sleep(2)  # Required by RemoteOK to avoid 429
        headers = {"User-Agent": "Mozilla/5.0 (job-radar personal tool)"}
        response = requests.get(self.API_URL, headers=headers, timeout=30)
        response.raise_for_status()

        raw_jobs = response.json()[1:]  # Skip metadata object at index 0
        jobs = []

        for raw in raw_jobs[:max_results * 3]:  # Over-fetch to filter
            title = raw.get("position", "")
            if not self._matches_keywords(title, raw.get("tags", []), keywords):
                continue

            url = raw.get("url", "") or f"https://remoteok.com/l/{raw.get('id', '')}"
            if not url.startswith("http"):
                url = f"https://remoteok.com{url}"

            salary = self._build_salary(raw.get("salary_min"), raw.get("salary_max"))
            posted = self._parse_unix(raw.get("date", ""))

            jobs.append(Job(
                id=generate_job_id(self.source_name, url),
                source=self.source_name,
                url=url,
                title=title.strip(),
                company=raw.get("company", "N/A") or "N/A",
                location="Remote",
                is_remote=True,
                salary=salary,
                tags=[t.lower() for t in raw.get("tags", []) if t],
                description_snippet=strip_html(raw.get("description", ""))[:300],
                posted_date=posted,
                scraped_at=datetime.now().isoformat(),
                first_seen=datetime.now().isoformat(),
            ))

            if len(jobs) >= max_results:
                break

        return jobs

    def _matches_keywords(self, title: str, tags: list, keywords: list[str]) -> bool:
        searchable = (title + " " + " ".join(str(t) for t in tags)).lower()
        return any(kw.lower() in searchable for kw in keywords)

    def _build_salary(self, min_val, max_val) -> str:
        try:
            if min_val and max_val:
                return f"${int(min_val):,} – ${int(max_val):,}/year"
        except (ValueError, TypeError):
            pass
        return "N/A"

    def _parse_unix(self, unix_ts) -> str:
        try:
            return datetime.fromtimestamp(int(unix_ts)).strftime("%Y-%m-%d")
        except Exception:
            return ""
