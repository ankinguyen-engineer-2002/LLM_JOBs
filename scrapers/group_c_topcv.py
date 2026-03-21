"""
TopCV scraper — Vietnamese job site, requests + BeautifulSoup.
Target: https://www.topcv.vn/tim-viec-lam-{keyword}
"""

import requests
import time
from bs4 import BeautifulSoup
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime
from urllib.parse import quote_plus


class TopCVScraper(BaseJobScraper):
    source_name = "topcv"
    BASE_URL = "https://www.topcv.vn/tim-viec-lam-moi-nhat"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        jobs = []
        seen_urls = set()

        for keyword in keywords:
            for page in range(1, 4):
                time.sleep(1.5)
                url = f"https://www.topcv.vn/viec-lam-{quote_plus(keyword)}-kw?page={page}"
                try:
                    resp = requests.get(url, headers=headers, timeout=30)
                    if resp.status_code != 200:
                        break
                except requests.RequestException:
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = (soup.select(".job-item-search-result") or
                         soup.select(".job-item") or
                         soup.select("[class*='job-list'] [class*='job']"))
                if not cards:
                    break

                for card in cards:
                    # Title and URL
                    title_el = (card.select_one("h3.title a") or card.select_one("h3 a") or
                                card.select_one(".body a") or card.select_one("a[href*='topcv.vn']"))
                    if not title_el:
                        continue
                    job_href = title_el.get("href", "")
                    if not job_href:
                        continue
                    job_url = job_href if job_href.startswith("http") else f"https://www.topcv.vn{job_href}"
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    title = title_el.get("title", "") or title_el.get_text(strip=True)

                    # Company
                    company_el = (card.select_one(".company-title") or card.select_one("[class*='company']") or
                                  card.select_one("a.company"))
                    company = company_el.get_text(strip=True) if company_el else "N/A"

                    # Salary
                    salary_el = card.select_one(".label-content") or card.select_one("[class*='salary']")
                    salary = salary_el.get_text(strip=True) if salary_el else "N/A"

                    # Location
                    location_el = card.select_one(".address") or card.select_one("[class*='location']")
                    location = location_el.get_text(strip=True) if location_el else "N/A"

                    jobs.append(Job(
                        id=generate_job_id(self.source_name, job_url),
                        source=self.source_name,
                        url=job_url,
                        title=title.strip(),
                        company=company,
                        location=location,
                        is_remote="remote" in (title + " " + location).lower(),
                        salary=salary,
                        posted_date="",
                        scraped_at=datetime.now().isoformat(),
                        first_seen=datetime.now().isoformat(),
                    ))

                if len(jobs) >= max_results:
                    break
            if len(jobs) >= max_results:
                break

        return jobs[:max_results]
