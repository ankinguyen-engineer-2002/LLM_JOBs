"""
Jobicy scraper — public REST API for remote jobs.
Increased max results per keyword.
"""

import requests
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime


class JobicyScraper(BaseJobScraper):
    source_name = "jobicy"
    BASE_URL = "https://jobicy.com/api/v2/remote-jobs"

    def scrape(self, keywords: list[str], max_results: int = 100) -> list[Job]:
        jobs = []
        seen_urls = set()

        for keyword in keywords:
            params = {"count": 50, "tag": keyword}
            try:
                response = requests.get(self.BASE_URL, params=params, timeout=30)
                if response.status_code != 200:
                    print(f"[jobicy] HTTP {response.status_code} for '{keyword}'")
                    continue
            except Exception as e:
                print(f"[jobicy] Request failed for '{keyword}': {e}")
                continue

            data = response.json()
            batch = 0
            for raw in data.get("jobs", []):
                url = raw.get("url", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                job_type_raw = raw.get("jobType", "N/A") or "N/A"
                if isinstance(job_type_raw, list):
                    job_type_raw = job_type_raw[0] if job_type_raw else "N/A"
                job_type = str(job_type_raw).lower().replace(" ", "_").replace("-", "_")

                raw_tags = raw.get("jobIndustry", []) or []
                if isinstance(raw_tags, str):
                    raw_tags = [raw_tags]
                tags = [t.lower().strip() for t in raw_tags if t]

                jobs.append(Job(
                    id=generate_job_id(self.source_name, url),
                    source=self.source_name,
                    url=url,
                    title=raw.get("jobTitle", "").strip(),
                    company=raw.get("companyName", "N/A") or "N/A",
                    location=raw.get("jobGeo", "Remote") or "Remote",
                    is_remote=True,
                    salary=self._build_salary(raw),
                    job_type=job_type,
                    tags=tags,
                    description_snippet=strip_html(raw.get("jobDescription", ""))[:300],
                    posted_date=str(raw.get("pubDate", "") or "")[:10],
                    scraped_at=datetime.now().isoformat(),
                    first_seen=datetime.now().isoformat(),
                ))
                batch += 1

            print(f"[jobicy] '{keyword}': {batch} results")

            if len(jobs) >= max_results:
                break

        print(f"[jobicy] Total: {len(jobs)} jobs")
        return jobs[:max_results]

    def _build_salary(self, raw: dict) -> str:
        min_s = raw.get("annualSalaryMin")
        max_s = raw.get("annualSalaryMax")
        cur = raw.get("salaryCurrency", "USD") or "USD"
        try:
            if min_s and max_s:
                return f"{cur} {int(min_s):,} – {int(max_s):,}/year"
        except (ValueError, TypeError):
            pass
        return "N/A"
