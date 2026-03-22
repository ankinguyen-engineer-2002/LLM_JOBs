"""
ITviec scraper — Vietnamese IT job board, publicly accessible HTML.
URL format: https://itviec.com/it-jobs/{keyword}
No login required for listings. Salary hidden behind sign-in.
"""

import requests
import time
from bs4 import BeautifulSoup
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id
from datetime import datetime


class ITviecScraper(BaseJobScraper):
    source_name = "itviec"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,vi;q=0.8",
        }
        jobs = []
        seen_urls = set()

        for keyword in keywords:
            slug = keyword.lower().replace(" ", "-")
            url = f"https://itviec.com/it-jobs/{slug}"

            try:
                time.sleep(1)
                resp = requests.get(url, headers=headers, timeout=15)
                if resp.status_code != 200:
                    print(f"[itviec] HTTP {resp.status_code} for {slug}")
                    continue
            except requests.RequestException as e:
                print(f"[itviec] Request failed for {slug}: {e}")
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.select(".job-card")

            for card in cards:
                # Title — directly in h3 text, URL in h3's data-url attribute
                h3 = card.select_one("h3")
                if not h3:
                    continue
                title = h3.get_text(strip=True)
                if not title:
                    continue

                # URL from data-url attribute or from card's data attribute
                job_url = h3.get("data-url", "")
                if not job_url:
                    # Fallback: construct from slug
                    card_slug = card.get("data-search--job-selection-job-slug-value", "")
                    if card_slug:
                        job_url = f"https://itviec.com/it-jobs/{card_slug}"
                if not job_url:
                    continue

                # Clean URL (remove tracking params)
                if "?" in job_url:
                    job_url = job_url.split("?")[0]

                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                # Company — in a[href*=/companies/] with text
                company = "N/A"
                company_links = card.select("a[href*='/companies/']")
                for cl in company_links:
                    text = cl.get_text(strip=True)
                    if text:
                        company = text
                        break

                # Posted time
                posted = ""
                time_span = card.select_one("span.small-text")
                if time_span:
                    posted = time_span.get_text(strip=True).replace("Posted", "").strip()

                # Tags/skills
                tag_els = card.select(".itag-light") or card.select("[class*='itag']")
                tags = [t.get_text(strip=True).lower() for t in tag_els if t.get_text(strip=True)]

                # Location — look for address/location indicators
                location = "Vietnam"
                all_spans = card.select("span")
                for span in all_spans:
                    text = span.get_text(strip=True)
                    if any(loc in text for loc in ["Ha Noi", "Ho Chi Minh", "Da Nang",
                                                     "Hà Nội", "Hồ Chí Minh", "Đà Nẵng",
                                                     "Remote", "Hà Nội"]):
                        location = text
                        break

                is_remote = "remote" in f"{title} {location}".lower()

                jobs.append(Job(
                    id=generate_job_id(self.source_name, job_url),
                    source=self.source_name,
                    url=job_url,
                    title=title,
                    company=company,
                    location=location,
                    is_remote=is_remote,
                    salary="Sign in to view",
                    tags=tags[:10],
                    posted_date=posted,
                    scraped_at=datetime.now().isoformat(),
                    first_seen=datetime.now().isoformat(),
                ))

                if len(jobs) >= max_results:
                    return jobs

        return jobs[:max_results]
