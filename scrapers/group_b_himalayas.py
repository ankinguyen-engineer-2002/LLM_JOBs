"""
Himalayas scraper — public REST API at himalayas.app/jobs/api.
The API has 90K+ total jobs, no server-side search.
Strategy: fetch recent pages, broad keyword matching on title.
"""

import requests
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime, timedelta
import time


class HimalayasScraper(BaseJobScraper):
    source_name = "himalayas"
    BASE_URL = "https://himalayas.app/jobs/api"

    def scrape(self, keywords: list[str], max_results: int = 100) -> list[Job]:
        jobs = []
        seen_urls = set()
        cutoff = datetime.now() - timedelta(days=30)

        # Build keyword terms for matching (whole words and short phrases)
        search_terms = set()
        for kw in keywords:
            search_terms.add(kw.lower())
            for word in kw.lower().split():
                if len(word) >= 3:  # skip tiny words
                    search_terms.add(word)

        offset = 0
        batch_size = 50
        max_pages = 20  # Fetch up to 1000 raw jobs
        matched = 0

        for page_num in range(max_pages):
            try:
                resp = requests.get(
                    self.BASE_URL,
                    params={"limit": batch_size, "offset": offset},
                    timeout=(5, 15),
                    headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
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

                # Match against title (case-insensitive)
                title_lower = title.lower()
                if not any(term in title_lower for term in search_terms):
                    continue

                slug = raw.get("slug", "")
                url = f"https://himalayas.app/jobs/{slug}" if slug else ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                # 30-day cutoff
                pub_date = str(raw.get("pubDate", "") or "")[:10]
                if pub_date:
                    try:
                        dt = datetime.strptime(pub_date, "%Y-%m-%d")
                        if dt < cutoff:
                            continue
                    except ValueError:
                        pass

                salary = self._build_salary(raw)

                # Location handling
                loc_restrictions = raw.get("locationRestrictions", []) or []
                if loc_restrictions:
                    location = ", ".join(loc_restrictions[:3])
                else:
                    location = "Worldwide"

                # Categories as tags
                categories = raw.get("categories", []) or []
                tags = [str(c).lower() for c in categories if c][:10]

                # Employment type
                emp_type = raw.get("employmentType", "N/A") or "N/A"

                jobs.append(Job(
                    id=generate_job_id(self.source_name, url),
                    source=self.source_name,
                    url=url,
                    title=title.strip(),
                    company=company,
                    location=location,
                    is_remote=True,
                    salary=salary,
                    job_type=emp_type,
                    tags=tags,
                    description_snippet=strip_html(raw.get("description", ""))[:300],
                    posted_date=pub_date,
                    scraped_at=datetime.now().isoformat(),
                    first_seen=datetime.now().isoformat(),
                ))
                matched += 1

                if matched >= max_results:
                    print(f"[himalayas] Total: {matched} jobs (hit max at page {page_num+1})")
                    return jobs

            offset += batch_size
            if len(raw_jobs) < batch_size:
                break

            time.sleep(0.3)  # Rate limit

        print(f"[himalayas] Total: {len(jobs)} jobs (scanned {offset} raw)")
        return jobs

    def _build_salary(self, raw: dict) -> str:
        min_s = raw.get("minSalary") or raw.get("salaryMin")
        max_s = raw.get("maxSalary") or raw.get("salaryMax")
        cur = raw.get("currency") or raw.get("salaryCurrency") or "USD"
        try:
            if min_s and max_s:
                return f"{cur} {int(min_s):,} – {int(max_s):,}/year"
            elif min_s:
                return f"{cur} {int(min_s):,}+/year"
        except (ValueError, TypeError):
            pass
        return "N/A"
