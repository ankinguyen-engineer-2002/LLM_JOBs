"""
Turing.com scraper — uses Playwright to render work.turing.com/jobs SPA.
"""

import time
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False


class TuringScraper(BaseJobScraper):
    source_name = "turing"
    BASE_URL = "https://work.turing.com/jobs"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        if not PLAYWRIGHT_OK:
            print("[turing] playwright not installed — skipping")
            return []

        jobs = []
        seen_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            try:
                page.goto(self.BASE_URL, timeout=20000)
                # Wait for job cards or links to appear
                page.wait_for_selector("a[href*='/jobs/'], [class*='job'], [class*='card']", timeout=10000)
                time.sleep(2)

                # Scroll to load more
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, 1500)")
                    time.sleep(0.5)
            except Exception as e:
                print(f"[turing] Page load failed: {e}")
                browser.close()
                return []

            # Strategy 1: Find direct job links
            all_links = page.query_selector_all("a[href*='/jobs/']")

            for link in all_links:
                try:
                    href = link.get_attribute("href") or ""
                    if not href or href == "/jobs/" or href == "/jobs":
                        continue

                    job_url = href if href.startswith("http") else f"https://work.turing.com{href}"
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    title = link.inner_text().strip()
                    if not title or len(title) < 5:
                        continue

                    # Keyword matching
                    if not any(kw.lower() in title.lower() for kw in keywords):
                        continue

                    jobs.append(Job(
                        id=generate_job_id(self.source_name, job_url),
                        source=self.source_name,
                        url=job_url,
                        title=title,
                        company="Turing",
                        location="Remote",
                        is_remote=True,
                        salary="N/A",
                        tags=["remote"],
                        scraped_at=datetime.now().isoformat(),
                        first_seen=datetime.now().isoformat(),
                    ))
                except Exception:
                    continue

            # Strategy 2: Find job cards with data
            if not jobs:
                cards = page.query_selector_all("[class*='job-card'], [class*='JobCard'], [class*='card']")
                for card in cards:
                    try:
                        title_el = card.query_selector("h2, h3, [class*='title']")
                        title = title_el.inner_text().strip() if title_el else ""
                        if not title or len(title) < 5:
                            continue

                        if not any(kw.lower() in title.lower() for kw in keywords):
                            continue

                        link_el = card.query_selector("a[href]")
                        href = link_el.get_attribute("href") if link_el else ""
                        job_url = href if href and href.startswith("http") else f"https://work.turing.com/jobs/{title.lower().replace(' ', '-')}"
                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)

                        salary_el = card.query_selector("[class*='salary'], [class*='comp']")
                        salary = salary_el.inner_text().strip() if salary_el else "N/A"

                        jobs.append(Job(
                            id=generate_job_id(self.source_name, job_url),
                            source=self.source_name,
                            url=job_url,
                            title=title,
                            company="Turing",
                            location="Remote",
                            is_remote=True,
                            salary=salary,
                            tags=["remote"],
                            scraped_at=datetime.now().isoformat(),
                            first_seen=datetime.now().isoformat(),
                        ))
                    except Exception:
                        continue

            browser.close()

        return jobs[:max_results]
