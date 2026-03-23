"""
Workable job board scraper — uses the public Workable API.
Searches across all jobs on jobs.workable.com with keyword queries.
Rich API data: title, company, location, workplace type, employment type, description.
"""

import requests
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime, timedelta
import time


class WorkableScraper(BaseJobScraper):
    source_name = "workable"

    API_URL = "https://jobs.workable.com/api/v1/jobs"
    PER_PAGE = 5        # Workable returns 5 jobs per page (fixed)
    MAX_PAGES = 20      # Deep scrape: 20 pages per keyword (5 × 20 = 100 jobs/keyword)

    def scrape(self, keywords: list[str], max_results: int = 200) -> list[Job]:
        jobs = []
        seen_ids = set()
        cutoff = datetime.now() - timedelta(days=30)

        for kw in keywords:
            page_token = None
            pages = 0

            while pages < self.MAX_PAGES:
                try:
                    params = {"query": kw}
                    if page_token:
                        params["pageToken"] = page_token

                    resp = requests.get(
                        self.API_URL,
                        params=params,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                            "Accept": "application/json",
                            "Referer": "https://jobs.workable.com/",
                        },
                        timeout=15,
                    )

                    if resp.status_code != 200:
                        print(f"[workable] HTTP {resp.status_code} for '{kw}' page {pages+1}")
                        break

                    data = resp.json()
                    job_list = data.get("jobs", [])
                    page_token = data.get("nextPageToken")

                    if not job_list:
                        break

                    for j in job_list:
                        wk_id = j.get("id", "")
                        if wk_id in seen_ids:
                            continue

                        # 30-day cutoff check
                        created = j.get("created", "")
                        posted_date = ""
                        if created:
                            try:
                                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                                if dt.replace(tzinfo=None) < cutoff:
                                    continue
                                posted_date = dt.strftime("%Y-%m-%d")
                            except Exception:
                                pass

                        seen_ids.add(wk_id)

                        # Extract location
                        loc_obj = j.get("location", {})
                        city = loc_obj.get("city", "")
                        country = loc_obj.get("countryName", "")
                        location = f"{city}, {country}" if city and country else city or country or "N/A"

                        # Workplace type (remote / hybrid / on_site)
                        workplace = j.get("workplace", "")
                        is_remote = workplace in ("remote", "hybrid")

                        # Extract company
                        comp = j.get("company", {})
                        company_name = comp.get("title", "N/A")

                        # URL
                        url = j.get("url", f"https://jobs.workable.com/view/{wk_id}")

                        # Description snippet
                        desc_html = j.get("description", "")
                        desc_text = strip_html(desc_html)[:500] if desc_html else ""

                        # Employment type
                        emp_type = j.get("employmentType", "N/A")

                        # Tags from department
                        tags = []
                        dept = j.get("department", "")
                        if dept:
                            tags.append(dept.lower())

                        jobs.append(Job(
                            id=generate_job_id(self.source_name, url),
                            source=self.source_name,
                            url=url,
                            title=j.get("title", "N/A"),
                            company=company_name,
                            location=location,
                            is_remote=is_remote,
                            salary="N/A",
                            tags=tags,
                            job_type=emp_type,
                            description_snippet=desc_text,
                            posted_date=posted_date,
                            scraped_at=datetime.now().isoformat(),
                            first_seen=datetime.now().isoformat(),
                        ))

                    pages += 1

                    if not page_token:
                        break

                    time.sleep(0.3)  # Rate limit

                except Exception as e:
                    print(f"[workable] Error on '{kw}' page {pages+1}: {e}")
                    break

            print(f"[workable] '{kw}': found {len(seen_ids)} total unique so far")

            time.sleep(0.5)

        print(f"[workable] Total: {len(jobs)} jobs")
        return jobs[:max_results]
