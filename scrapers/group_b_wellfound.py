"""
Wellfound (AngelList) scraper — uses Playwright with stealth settings.
Navigates to role-specific pages, extracts job listings via DOM parsing.
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


class WellfoundScraper(BaseJobScraper):
    source_name = "wellfound"

    ROLE_SLUGS = [
        "data-engineer",
        "machine-learning-engineer",
        "data-scientist",
    ]

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        if not PLAYWRIGHT_OK:
            print("[wellfound] playwright not installed — skipping")
            return []

        jobs = []
        seen_urls = set()

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
            )

            # Block unnecessary resources for speed
            page = context.new_page()
            try:
                from playwright_stealth import stealth_sync
                stealth_sync(page)
            except ImportError:
                pass

            for slug in self.ROLE_SLUGS:
                url = f"https://wellfound.com/role/r/{slug}"

                try:
                    page.goto(url, timeout=30000, wait_until="domcontentloaded")
                    # Wait for any content to load
                    time.sleep(5)

                    # Check if we hit Cloudflare challenge
                    content = page.content()
                    if "challenge" in content.lower() and "cloudflare" in content.lower():
                        print(f"[wellfound] Cloudflare blocked for {slug}")
                        continue

                    # Scroll to load lazy content
                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, 1000)")
                        time.sleep(1)

                    # Try multiple selector strategies
                    selectors = [
                        "a[href*='/jobs/']",
                        "a[href*='/l/']",
                        "[data-test='JobListing'] a",
                        ".styles_component__ICDIx a",
                        "main a[href*='wellfound.com']",
                    ]

                    links = []
                    for sel in selectors:
                        try:
                            found = page.query_selector_all(sel)
                            if found:
                                links = found
                                break
                        except Exception:
                            continue

                    if not links:
                        print(f"[wellfound] No job links found for {slug}")
                        continue

                    batch = 0
                    for link in links:
                        try:
                            href = link.get_attribute("href") or ""
                            if not href:
                                continue

                            # Filter navigation/non-job links
                            if any(x in href for x in ["/login", "/signup", "/role/", "javascript:", "#"]):
                                continue

                            job_url = href if href.startswith("http") else f"https://wellfound.com{href}"

                            if job_url in seen_urls:
                                continue
                            seen_urls.add(job_url)

                            title = link.inner_text().strip()
                            if not title or len(title) < 5 or len(title) > 200:
                                continue

                            # Extract company from parent
                            company = "N/A"
                            try:
                                parent = link.evaluate_handle("el => el.closest('[class*=\"styles\"]') || el.parentElement")
                                if parent:
                                    text = parent.as_element().inner_text()
                                    lines = [l.strip() for l in text.split("\n") if l.strip() and l.strip() != title]
                                    if lines:
                                        company = lines[0][:100]
                            except Exception:
                                pass

                            jobs.append(Job(
                                id=generate_job_id(self.source_name, job_url),
                                source=self.source_name,
                                url=job_url,
                                title=title,
                                company=company,
                                location="N/A",
                                is_remote=True,
                                salary="N/A",
                                tags=[slug.replace("-", " ")],
                                scraped_at=datetime.now().isoformat(),
                                first_seen=datetime.now().isoformat(),
                            ))
                            batch += 1
                        except Exception:
                            continue

                    print(f"[wellfound] {slug}: {batch} jobs")

                except Exception as e:
                    print(f"[wellfound] Error for {slug}: {e}")
                    continue

                if len(jobs) >= max_results:
                    break

            browser.close()

        print(f"[wellfound] Total: {len(jobs)} jobs")
        return jobs[:max_results]
