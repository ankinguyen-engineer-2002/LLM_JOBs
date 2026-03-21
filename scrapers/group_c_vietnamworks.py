"""
VietnamWorks scraper — uses Algolia public search API via direct HTTP.
APP_ID and API_KEY are public search-only keys from the browser bundle.
"""

import requests
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime


class VietnamWorksScraper(BaseJobScraper):
    source_name = "vietnamworks"
    APP_ID = "JF8Q26WWUD"
    API_KEY = "ecef10153e66bbd6d54f08ea005b60fc"  # public search-only key
    INDEX_NAME = "vnw_job_v2"

    def _algolia_search(self, query: str, max_results: int = 50) -> dict:
        """Direct HTTP call to Algolia REST API — no SDK needed."""
        url = f"https://{self.APP_ID}-dsn.algolia.net/1/indexes/{self.INDEX_NAME}/query"
        headers = {
            "X-Algolia-Application-Id": self.APP_ID,
            "X-Algolia-API-Key": self.API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "query": query,
            "hitsPerPage": max_results,
            "filters": "isActive:1",
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        if resp.status_code != 200:
            return {}
        return resp.json()

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        jobs = []
        seen_ids = set()

        for keyword in keywords:
            try:
                result = self._algolia_search(keyword, max_results)
            except Exception as e:
                print(f"[vietnamworks] keyword={keyword} failed: {e}")
                continue

            for hit in result.get("hits", []):
                job_id = str(hit.get("jobId", ""))
                if not job_id or job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                alias = hit.get("alias", job_id)
                url = f"https://www.vietnamworks.com/viec-lam/{alias}-jv"
                salary = self._parse_salary(hit)

                working_locs = hit.get("workingLocations", [])
                if isinstance(working_locs, list) and working_locs:
                    location = ", ".join(str(l) for l in working_locs[:2])
                else:
                    location = "N/A"

                company_data = hit.get("company", {})
                if isinstance(company_data, dict):
                    company = company_data.get("companyName", "N/A") or "N/A"
                else:
                    company = "N/A"

                skills = hit.get("skills", [])
                tags = []
                if isinstance(skills, list):
                    for s in skills:
                        if isinstance(s, dict):
                            tags.append(s.get("skillName", "").lower())
                        elif isinstance(s, str):
                            tags.append(s.lower())
                tags = [t for t in tags if t]

                title = hit.get("jobTitle", "").strip()

                jobs.append(Job(
                    id=generate_job_id(self.source_name, str(job_id)),
                    source=self.source_name,
                    url=url,
                    title=title,
                    company=company,
                    location=location,
                    is_remote="remote" in title.lower(),
                    salary=salary,
                    tags=tags,
                    description_snippet=strip_html(hit.get("jobDescription", ""))[:300],
                    posted_date=str(hit.get("approvedDate", "") or "")[:10],
                    scraped_at=datetime.now().isoformat(),
                    first_seen=datetime.now().isoformat(),
                ))

        return jobs[:max_results]

    def _parse_salary(self, hit: dict) -> str:
        salary_data = hit.get("salary")
        if not isinstance(salary_data, dict):
            return "N/A"
        min_s = salary_data.get("from")
        max_s = salary_data.get("to")
        try:
            if min_s and max_s:
                return f"${int(min_s):,} – ${int(max_s):,}/month"
        except (ValueError, TypeError):
            pass
        return "N/A"
