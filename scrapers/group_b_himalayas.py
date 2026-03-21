"""
Himalayas scraper — public search API with pagination.
Endpoint: GET https://himalayas.app/jobs/api
"""

import requests
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime


class HimalayasScraper(BaseJobScraper):
    source_name = "himalayas"
    BASE_URL = "https://himalayas.app/jobs/api"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        jobs = []
        seen_urls = set()

        for keyword in keywords:
            page = 1
            while len(jobs) < max_results:
                params = {"limit": 20, "offset": (page - 1) * 20}
                response = requests.get(self.BASE_URL, params=params, timeout=30)
                if response.status_code != 200:
                    break
                data = response.json()
                raw_jobs = data.get("jobs", [])
                if not raw_jobs:
                    break

                for raw in raw_jobs:
                    title = raw.get("title", "")
                    company_name = raw.get("companyName", "N/A") or "N/A"
                    tags = [c.lower() for c in raw.get("categories", []) if c]

                    # Keyword match
                    searchable = f"{title} {company_name} {' '.join(tags)}".lower()
                    if not any(kw.lower() in searchable for kw in keywords):
                        continue

                    slug = raw.get("slug", "")
                    url = f"https://himalayas.app/jobs/{slug}" if slug else ""
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    salary = self._build_salary(raw)

                    jobs.append(Job(
                        id=generate_job_id(self.source_name, url),
                        source=self.source_name,
                        url=url,
                        title=title.strip(),
                        company=company_name,
                        location=raw.get("location", "Remote") or "Remote",
                        is_remote=True,
                        salary=salary,
                        job_type=self._map_job_type(raw.get("jobType", "")),
                        tags=tags,
                        description_snippet=strip_html(raw.get("description", ""))[:300],
                        posted_date=str(raw.get("pubDate", "") or "")[:10],
                        scraped_at=datetime.now().isoformat(),
                        first_seen=datetime.now().isoformat(),
                    ))

                page += 1
                if len(raw_jobs) < 20:
                    break

            if len(jobs) >= max_results:
                break

        return jobs[:max_results]

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

    def _map_job_type(self, raw: str) -> str:
        if not raw:
            return "N/A"
        mapping = {
            "Full Time": "full_time", "full_time": "full_time",
            "Part Time": "part_time", "part_time": "part_time",
            "Contract": "contract", "contract": "contract",
            "Internship": "internship", "internship": "internship",
        }
        return mapping.get(raw, "N/A")
