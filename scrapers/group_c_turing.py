"""
Turing.com scraper — public jobs page at work.turing.com/jobs.
Since it's a Next.js SPA, we attempt to extract from the __NEXT_DATA__ JSON blob
embedded in the initial HTML, which often contains the pre-rendered job data.
Falls back gracefully if the data structure changes.
"""

import requests
import json
import re
import time
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id
from datetime import datetime


class TuringScraper(BaseJobScraper):
    source_name = "turing"
    BASE_URL = "https://work.turing.com/jobs"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        jobs = []
        seen_urls = set()

        try:
            time.sleep(1)
            resp = requests.get(self.BASE_URL, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"[turing] HTTP {resp.status_code}")
                return []
        except requests.RequestException as e:
            print(f"[turing] Request failed: {e}")
            return []

        html = resp.text

        # Strategy 1: Look for __NEXT_DATA__ JSON which often contains pre-rendered data
        next_data_match = re.search(
            r'<script\s+id="__NEXT_DATA__"\s+type="application/json">(.*?)</script>',
            html, re.DOTALL
        )

        if next_data_match:
            try:
                next_data = json.loads(next_data_match.group(1))
                jobs = self._parse_next_data(next_data, keywords, max_results)
                if jobs:
                    return jobs
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[turing] Could not parse __NEXT_DATA__: {e}")

        # Strategy 2: Try JSON embedded in script tags (common for SSR hydration)
        script_matches = re.findall(
            r'<script[^>]*>(.*?)</script>', html, re.DOTALL
        )
        for script_text in script_matches:
            # Look for arrays of job-like objects
            json_matches = re.findall(r'\[{.*?"title".*?}\]', script_text)
            for jm in json_matches:
                try:
                    data = json.loads(jm)
                    if isinstance(data, list) and len(data) > 0:
                        for item in data:
                            if 'title' in item:
                                job = self._item_to_job(item, keywords, seen_urls)
                                if job:
                                    jobs.append(job)
                                    if len(jobs) >= max_results:
                                        return jobs
                except (json.JSONDecodeError, TypeError):
                    continue

        if not jobs:
            print(f"[turing] No jobs found — page may require JavaScript rendering")

        return jobs

    def _parse_next_data(self, data: dict, keywords: list[str], max_results: int) -> list[Job]:
        """Try to find job listings in the Next.js pre-rendered data."""
        jobs = []
        seen_urls = set()

        # Walk the nested structure looking for job-like arrays
        job_items = self._find_job_arrays(data)

        for item in job_items:
            job = self._item_to_job(item, keywords, seen_urls)
            if job:
                jobs.append(job)
                if len(jobs) >= max_results:
                    break

        return jobs

    def _find_job_arrays(self, obj, depth=0) -> list:
        """Recursively search for arrays of objects that look like job listings."""
        if depth > 10:
            return []

        results = []

        if isinstance(obj, list):
            # Check if this looks like a job array
            if len(obj) > 0 and isinstance(obj[0], dict):
                has_title = any('title' in item for item in obj if isinstance(item, dict))
                if has_title:
                    results.extend(obj)
            for item in obj:
                results.extend(self._find_job_arrays(item, depth + 1))
        elif isinstance(obj, dict):
            for key, value in obj.items():
                results.extend(self._find_job_arrays(value, depth + 1))

        return results

    def _item_to_job(self, item: dict, keywords: list[str], seen_urls: set) -> Job | None:
        """Convert a raw dict item to a Job, or None if it doesn't match."""
        if not isinstance(item, dict):
            return None

        title = item.get('title', '') or item.get('jobTitle', '') or item.get('name', '')
        if not title:
            return None

        # Keyword matching
        if keywords and not any(kw.lower() in title.lower() for kw in keywords):
            return None

        # Build URL
        slug = item.get('slug', '') or item.get('id', '') or item.get('jobId', '')
        url = item.get('url', '') or item.get('applyUrl', '')
        if not url and slug:
            url = f"https://work.turing.com/jobs/{slug}"
        elif not url:
            url = f"https://work.turing.com/jobs/{title.lower().replace(' ', '-')}"

        if url in seen_urls:
            return None
        seen_urls.add(url)

        company = (item.get('company', '') or item.get('companyName', '')
                   or item.get('organization', '') or 'Turing')
        if isinstance(company, dict):
            company = company.get('name', 'Turing')

        location = item.get('location', '') or item.get('jobLocation', '') or 'Remote'
        salary = item.get('salary', '') or item.get('compensation', '') or 'N/A'
        if isinstance(salary, dict):
            salary = f"{salary.get('min', '')} - {salary.get('max', '')} {salary.get('currency', 'USD')}"

        tags = item.get('skills', []) or item.get('tags', []) or item.get('technologies', [])
        if isinstance(tags, list):
            tags = [str(t).lower() if isinstance(t, str) else str(t.get('name', '')).lower()
                    for t in tags if t]
        else:
            tags = []

        description = item.get('description', '') or item.get('jobDescription', '') or ''
        if len(description) > 200:
            description = description[:200] + '...'

        return Job(
            id=generate_job_id(self.source_name, url),
            source=self.source_name,
            url=url,
            title=title.strip(),
            company=company if isinstance(company, str) else 'Turing',
            location=location if isinstance(location, str) else 'Remote',
            is_remote=True,
            salary=str(salary) if salary else 'N/A',
            tags=tags[:10],
            description_snippet=description,
            posted_date=item.get('postedDate', '') or item.get('createdAt', ''),
            scraped_at=datetime.now().isoformat(),
            first_seen=datetime.now().isoformat(),
        )
