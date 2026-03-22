"""
Himalayas scraper — public REST API at himalayas.app/jobs/api.
Fetches ALL jobs, filters client-side by keywords.
Increased fetch pages for broader coverage.
"""

import requests
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime, timedelta


class HimalayasScraper(BaseJobScraper):
    source_name = "himalayas"
    BASE_URL = "https://himalayas.app/jobs/api"

    def scrape(self, keywords: list[str], max_results: int = 100) -> list[Job]:
        jobs = []
        seen_urls = set()
        cutoff = datetime.now() - timedelta(days=30)

        # Broad keyword terms for matching
        search_terms = set()
        for kw in keywords:
            search_terms.update(kw.lower().split())
        search_terms.update(["data", "engineer", "analytics", "ml", "ai",
                             "machine", "learning", "etl", "dbt", "platform",
                             "llm", "prompt", "nlp", "python", "sql"])

        offset = 0
        batch_size = 50
        max_pages = 10  # Fetch up to 500 raw jobs

        for page in range(max_pages):
            try:
                resp = requests.get(
                    self.BASE_URL,
                    params={"limit": batch_size, "offset": offset},
                    timeout=(5, 15),
                    headers={"User-Agent": "JobRadar/1.0"},
                )
                if resp.status_code != 200:
                    print(f"[himalayas] HTTP {resp.status_code} at offset {offset}")
                    break
            except requests.RequestException as e:
                print(f"[himalayas] Request failed at offset {offset}: {e}")
                break

            data = resp.json()
            raw_jobs = data.get("jobs", [])
            if not raw_jobs:
                break

            for raw in raw_jobs:
                title = raw.get("title", "")
                company = raw.get("companyName", "") or "N/A"
                categories = [str(c).lower() for c in (raw.get("categories", []) or []) if c]

                # Match against title + categories + company
                searchable = f"{title} {' '.join(categories)} {company}".lower()
                if not any(term in searchable for term in search_terms):
                    continue

                slug = raw.get("slug", "")
                url = f"https://himalayas.app/jobs/{slug}" if slug else ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                salary = self._build_salary(raw)
                location = raw.get("location", "") or "Remote"

                jobs.append(Job(
                    id=generate_job_id(self.source_name, url),
                    source=self.source_name,
                    url=url,
                    title=title.strip(),
                    company=company,
                    location=location if isinstance(location, str) else "Remote",
                    is_remote=True,
                    salary=salary,
                    tags=categories[:10],
                    description_snippet=strip_html(raw.get("description", ""))[:300],
                    posted_date=str(raw.get("pubDate", "") or "")[:10],
                    scraped_at=datetime.now().isoformat(),
                    first_seen=datetime.now().isoformat(),
                ))

                if len(jobs) >= max_results:
                    print(f"[himalayas] Total: {len(jobs)} jobs (hit max)")
                    return jobs

            offset += batch_size
            if len(raw_jobs) < batch_size:
                break

        print(f"[himalayas] Total: {len(jobs)} jobs")
        return jobs

    def _build_salary(self, raw: dict) -> str:
        min_s = raw.get("salaryMin")
        max_s = raw.get("salaryMax")
        cur = raw.get("salaryCurrency", "USD") or "USD"
        try:
            if min_s and max_s:
                return f"{cur} {int(min_s):,} – {int(max_s):,}/year"
        except (ValueError, TypeError):
            pass
        return "N/A"
