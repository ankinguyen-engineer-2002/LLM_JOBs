"""
Turing.com scraper — uses Playwright to render work.turing.com SPA.
Extracts remote job listings from Turing's job board.
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


class TuringScraper(BaseJobScraper):
    source_name = "turing"

    SEARCH_URLS = [
        "https://www.turing.com/remote-developer-jobs/data-engineer",
        "https://www.turing.com/remote-developer-jobs/machine-learning-engineer",
        "https://www.turing.com/remote-developer-jobs/ai-engineer",
        "https://www.turing.com/remote-developer-jobs/python-developer",
    ]

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        if not PLAYWRIGHT_OK:
            print("[turing] playwright not installed — skipping")
            return []

        jobs = []
        seen_urls = set()

        # Build keyword terms for matching
        search_terms = set()
        for kw in keywords:
            search_terms.update(kw.lower().split())

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            for search_url in self.SEARCH_URLS:
                try:
                    page.goto(search_url, timeout=30000, wait_until="domcontentloaded")
                    time.sleep(3)

                    # Check for Cloudflare
                    content = page.content()
                    if "challenge" in content.lower() and "cloudflare" in content.lower():
                        print(f"[turing] Cloudflare blocked for {search_url}")
                        continue

                    # Scroll to load content
                    for _ in range(5):
                        page.evaluate("window.scrollBy(0, 1500)")
                        time.sleep(0.5)

                    # Try multiple selector strategies
                    selectors = [
                        "a[href*='/remote-developer-jobs/']",
                        "a[href*='/jobs/']",
                        "[class*='job'] a",
                        "[class*='card'] a",
                        "main a[href]",
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

                    batch = 0
                    for link in links:
                        try:
                            href = link.get_attribute("href") or ""
                            if not href or href in ("#", "/", "javascript:void(0)"):
                                continue
                            if any(x in href for x in ["/login", "/signup", "/apply", "turing.com/blog"]):
                                continue

                            job_url = href if href.startswith("http") else f"https://www.turing.com{href}"

                            if job_url in seen_urls:
                                continue

                            title = link.inner_text().strip()
                            if not title or len(title) < 5 or len(title) > 200:
                                continue

                            # Keyword match
                            title_lower = title.lower()
                            if not any(term in title_lower for term in search_terms):
                                continue

                            seen_urls.add(job_url)

                            jobs.append(Job(
                                id=generate_job_id(self.source_name, job_url),
                                source=self.source_name,
                                url=job_url,
                                title=title,
                                company="Turing",
                                location="N/A",
                                is_remote=True,
                                salary="N/A",
                                tags=["remote"],
                                scraped_at=datetime.now().isoformat(),
                                first_seen=datetime.now().isoformat(),
                            ))
                            batch += 1
                        except Exception:
                            continue

                    print(f"[turing] {search_url.split('/')[-1]}: {batch} jobs")

                except Exception as e:
                    print(f"[turing] Error: {e}")
                    continue

                if len(jobs) >= max_results:
                    break

            browser.close()

        print(f"[turing] Total: {len(jobs)} jobs")
        return jobs[:max_results]
