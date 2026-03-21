"""
ITviec scraper — server-rendered HTML, requires session cookie.
Set ITVIEC_SESSION environment variable with cookie value.
"""

import requests
import os
import time
from bs4 import BeautifulSoup
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime


class ITviecScraper(BaseJobScraper):
    source_name = "itviec"
    BASE_URL = "https://itviec.com/it-jobs"

    def __init__(self):
        self.session_cookie = os.environ.get("ITVIEC_SESSION", "")

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        if not self.session_cookie:
            print("[itviec] ITVIEC_SESSION not set — skipping")
            return []

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        cookies = {"_ITViec_session": self.session_cookie}
        jobs = []
        seen_urls = set()

        for keyword in keywords:
            for page in range(1, 4):  # max 3 pages per keyword
                time.sleep(1.5)
                url = f"{self.BASE_URL}?q={keyword}&page={page}"
                try:
                    resp = requests.get(url, headers=headers, cookies=cookies, timeout=30)
                    if resp.status_code != 200:
                        break
                except requests.RequestException:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                # ITviec uses various card selectors
                cards = (soup.select("[data-job-id]") or
                         soup.select(".job_content") or
                         soup.select(".job-item"))
                if not cards:
                    break

                for card in cards:
                    # Extract URL
                    link_el = card.select_one("a[href*='/it-jobs/']") or card.select_one("h3 a") or card.select_one("a[href]")
                    if not link_el:
                        continue
                    job_href = link_el.get("href", "")
                    if not job_href:
                        continue
                    job_url = job_href if job_href.startswith("http") else f"https://itviec.com{job_href}"

                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Extract fields
                    title_el = (card.select_one("h3.title") or card.select_one(".job-name") or
                                card.select_one("h3 a") or card.select_one("h2 a"))
                    company_el = (card.select_one(".employer-name") or card.select_one(".company-name") or
                                  card.select_one("[class*='company']"))
                    salary_el = card.select_one(".salary") or card.select_one("[class*='salary']")
                    location_el = card.select_one(".location") or card.select_one("[class*='location']")
                    tag_els = card.select(".tag-item") or card.select(".skills span") or card.select("[class*='tag']")

                    title = title_el.get_text(strip=True) if title_el else ""
                    if not title:
                        continue

                    company = company_el.get_text(strip=True) if company_el else "N/A"
                    salary = salary_el.get_text(strip=True) if salary_el else "N/A"
                    location = location_el.get_text(strip=True) if location_el else "N/A"
                    tags = [t.get_text(strip=True).lower() for t in tag_els if t.get_text(strip=True)]

                    jobs.append(Job(
                        id=generate_job_id(self.source_name, job_url),
                        source=self.source_name,
                        url=job_url,
                        title=title,
                        company=company,
                        location=location,
                        is_remote="remote" in location.lower(),
                        salary=salary,
                        tags=tags,
                        posted_date="",
                        scraped_at=datetime.now().isoformat(),
                        first_seen=datetime.now().isoformat(),
                    ))

                if len(jobs) >= max_results:
                    break
            if len(jobs) >= max_results:
                break

        return jobs[:max_results]
