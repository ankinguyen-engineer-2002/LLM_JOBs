"""
VietnamWorks scraper — uses Playwright (headless Chromium) to render
the Next.js SPA and extract job data from the fully-rendered page.
"""

import time
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False


class VietnamWorksScraper(BaseJobScraper):
    source_name = "vietnamworks"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        if not PLAYWRIGHT_OK:
            print("[vietnamworks] playwright not installed — skipping")
            return []

        jobs = []
        seen_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="vi-VN",
            )
            page = context.new_page()

            for keyword in keywords:
                encoded = keyword.replace(" ", "+")
                url = f"https://www.vietnamworks.com/tim-kiem-viec-lam?q={encoded}"

                try:
                    page.goto(url, timeout=20000)
                    # Wait for job cards to render
                    page.wait_for_selector("[class*='JobItem'], [class*='job-item'], .job-card", timeout=10000)
                    time.sleep(1)  # Extra wait for hydration
                except Exception as e:
                    print(f"[vietnamworks] Page load failed for '{keyword}': {e}")
                    continue

                # Extract job cards
                cards = page.query_selector_all("[class*='JobItem']")
                if not cards:
                    cards = page.query_selector_all("[class*='job-item']")
                if not cards:
                    cards = page.query_selector_all(".job-card")

                for card in cards:
                    try:
                        # Title
                        title_el = card.query_selector("h2, h3, [class*='jobTitle'], [class*='title'] a")
                        title = title_el.inner_text().strip() if title_el else ""
                        if not title:
                            continue

                        # URL
                        link = card.query_selector("a[href*='/viec-lam/'], a[href*='/job/']")
                        if not link:
                            link = card.query_selector("a[href]")
                        href = link.get_attribute("href") if link else ""
                        if not href:
                            continue
                        job_url = href if href.startswith("http") else f"https://www.vietnamworks.com{href}"
                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)

                        # Company
                        company_el = card.query_selector("[class*='company'], [class*='Company']")
                        company = company_el.inner_text().strip() if company_el else "N/A"

                        # Salary
                        salary_el = card.query_selector("[class*='salary'], [class*='Salary']")
                        salary = salary_el.inner_text().strip() if salary_el else "N/A"

                        # Location
                        loc_el = card.query_selector("[class*='location'], [class*='Location']")
                        location = loc_el.inner_text().strip() if loc_el else "Vietnam"

                        jobs.append(Job(
                            id=generate_job_id(self.source_name, job_url),
                            source=self.source_name,
                            url=job_url,
                            title=title,
                            company=company,
                            location=location,
                            is_remote="remote" in f"{title} {location}".lower(),
                            salary=salary,
                            tags=[],
                            scraped_at=datetime.now().isoformat(),
                            first_seen=datetime.now().isoformat(),
                        ))
                    except Exception:
                        continue

                if len(jobs) >= max_results:
                    break

            browser.close()

        return jobs[:max_results]
