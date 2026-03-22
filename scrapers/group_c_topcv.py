"""
TopCV.vn scraper — Vietnamese job board, server-side rendered HTML.
URL format: https://www.topcv.vn/tim-viec-lam-{keyword-hyphenated}
"""

import requests
import time
from bs4 import BeautifulSoup
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime


class TopCVScraper(BaseJobScraper):
    source_name = "topcv"
    BASE_URL = "https://www.topcv.vn/tim-viec-lam-"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.8",
        }
        jobs = []
        seen_urls = set()

        for keyword in keywords:
            slug = keyword.lower().replace(" ", "-")
            url = f"{self.BASE_URL}{slug}"

            try:
                time.sleep(1)  # Rate limit
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    print(f"[topcv] HTTP {resp.status_code} for {slug}")
                    continue
            except requests.RequestException as e:
                print(f"[topcv] Request failed for {slug}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Primary selector: .job-item-2
            cards = soup.select(".job-item-2")
            if not cards:
                # Fallback selectors
                cards = soup.select(".job-item-search-result") or soup.select("[class*='job-item']")

            for card in cards:
                # Title
                title_el = card.select_one("h3.title a span")
                if not title_el:
                    title_el = card.select_one("h3 a span") or card.select_one(".job-title a span")
                if not title_el:
                    title_el = card.select_one("h3 a") or card.select_one(".title a")
                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                # URL
                link_el = card.select_one("h3.title a") or card.select_one("h3 a") or card.select_one(".title a")
                job_href = link_el.get("href", "") if link_el else ""
                if not job_href:
                    continue
                job_url = job_href if job_href.startswith("http") else f"https://www.topcv.vn{job_href}"
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                # Company
                company_el = card.select_one("a.company") or card.select_one(".company-name a")
                company = company_el.get_text(strip=True) if company_el else "N/A"

                # Salary
                salary_el = card.select_one(".title-salary") or card.select_one("[class*='salary']")
                salary = salary_el.get_text(strip=True) if salary_el else "N/A"

                # Location
                loc_el = card.select_one("label.address") or card.select_one("[class*='location']")
                location = loc_el.get_text(strip=True) if loc_el else "N/A"

                # Tags
                tag_els = card.select(".item-tag") or card.select("[class*='tag']")
                tags = [t.get_text(strip=True).lower() for t in tag_els if t.get_text(strip=True)]

                # Experience
                exp_el = card.select_one("label.exp") or card.select_one("[class*='exp']")
                exp = exp_el.get_text(strip=True) if exp_el else ""

                is_remote = "remote" in f"{title} {location}".lower()

                jobs.append(Job(
                    id=generate_job_id(self.source_name, job_url),
                    source=self.source_name,
                    url=job_url,
                    title=title,
                    company=company,
                    location=location,
                    is_remote=is_remote,
                    salary=salary,
                    tags=tags[:10],
                    description_snippet=exp,
                    posted_date="",
                    scraped_at=datetime.now().isoformat(),
                    first_seen=datetime.now().isoformat(),
                ))

                if len(jobs) >= max_results:
                    return jobs

        return jobs[:max_results]
