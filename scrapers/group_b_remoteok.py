"""
RemoteOK scraper — public JSON API.
Relaxed keyword filter for broader results.
"""

import requests
import time
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime, timedelta


class RemoteOKScraper(BaseJobScraper):
    source_name = "remoteok"
    API_URL = "https://remoteok.com/remote-jobs.json"

    def scrape(self, keywords: list[str], max_results: int = 100) -> list[Job]:
        time.sleep(2)  # Required by RemoteOK to avoid 429
        headers = {"User-Agent": "Mozilla/5.0 (job-radar personal tool)"}
        try:
            response = requests.get(self.API_URL, headers=headers, timeout=30)
            response.raise_for_status()
        except Exception as e:
            print(f"[remoteok] API request failed: {e}")
            return []

        raw_jobs = response.json()[1:]  # Skip metadata object at index 0
        jobs = []
        cutoff = datetime.now() - timedelta(days=30)

        # Build broad keyword set for matching
        search_terms = set()
        for kw in keywords:
            search_terms.update(kw.lower().split())
        # Add common related terms
        search_terms.update(["data", "engineer", "analytics", "ml", "ai",
                             "machine", "learning", "llm", "prompt",
                             "python", "etl", "dbt", "platform", "nlp"])

        for raw in raw_jobs:
            title = raw.get("position", "")
            tags = [str(t).lower() for t in raw.get("tags", []) if t]
            company = raw.get("company", "N/A") or "N/A"

            # Check posted within 30 days
            posted = self._parse_unix(raw.get("date", ""))
            if posted:
                try:
                    post_dt = datetime.fromisoformat(posted)
                    if post_dt < cutoff:
                        continue
                except Exception:
                    pass

            # Relaxed matching: any keyword term in title OR tags
            searchable = f"{title} {' '.join(tags)} {company}".lower()
            if not any(term in searchable for term in search_terms):
                continue

            url = raw.get("url", "") or f"https://remoteok.com/l/{raw.get('id', '')}"
            if not url.startswith("http"):
                url = f"https://remoteok.com{url}"

            salary = self._build_salary(raw.get("salary_min"), raw.get("salary_max"))
            location = raw.get("location", "Remote") or "Remote"

            jobs.append(Job(
                id=generate_job_id(self.source_name, url),
                source=self.source_name,
                url=url,
                title=title.strip(),
                company=company,
                location=location,
                is_remote=True,
                salary=salary,
                tags=tags[:10],
                description_snippet=strip_html(raw.get("description", ""))[:300],
                posted_date=posted,
                scraped_at=datetime.now().isoformat(),
                first_seen=datetime.now().isoformat(),
            ))

            if len(jobs) >= max_results:
                break

        print(f"[remoteok] Total: {len(jobs)} jobs (from {len(raw_jobs)} raw)")
        return jobs

    def _build_salary(self, min_s, max_s) -> str:
        try:
            if min_s and max_s:
                return f"USD {int(min_s):,} – {int(max_s):,}/year"
        except (ValueError, TypeError):
            pass
        return "N/A"

    def _parse_unix(self, date_str: str) -> str:
        if not date_str:
            return ""
        try:
            # RemoteOK uses ISO format
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            try:
                dt = datetime.utcfromtimestamp(int(date_str))
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return ""
