"""
Wellfound (AngelList) scraper — uses Playwright to bypass anti-bot 403.
Navigates to role-specific pages and extracts job listings.
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


class WellfoundScraper(BaseJobScraper):
    source_name = "wellfound"

    ROLE_MAP = {
        "data engineer": "data-engineer",
        "data engineering": "data-engineer",
        "analytics engineer": "data-analyst",
        "ML engineer": "machine-learning-engineer",
        "machine learning engineer": "machine-learning-engineer",
        "AI engineer": "artificial-intelligence-engineer",
        "data scientist": "data-scientist",
        "prompt engineer": "machine-learning-engineer",
        "LLM engineer": "machine-learning-engineer",
    }

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        if not PLAYWRIGHT_OK:
            print("[wellfound] playwright not installed — skipping")
            return []

        jobs = []
        seen_urls = set()

        slugs = set()
        for kw in keywords:
            slug = self.ROLE_MAP.get(kw.lower())
            if slug:
                slugs.add(slug)
        if not slugs:
            slugs = {"data-engineer", "machine-learning-engineer"}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            )
            page = context.new_page()

            for slug in slugs:
                url = f"https://wellfound.com/role/r/{slug}"

                try:
                    page.goto(url, timeout=20000)
                    page.wait_for_selector("a[href*='/jobs/'], [class*='job'], [class*='startup']", timeout=10000)
                    time.sleep(2)

                    # Scroll to load lazy content
                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, 1000)")
                        time.sleep(0.5)
                except Exception as e:
                    print(f"[wellfound] Page load failed for {slug}: {e}")
                    continue

                # Find job links
                links = page.query_selector_all("a[href*='/jobs/']")

                for link in links:
                    try:
                        href = link.get_attribute("href") or ""
                        if not href or "/jobs/" not in href:
                            continue

                        job_url = href if href.startswith("http") else f"https://wellfound.com{href}"

                        # Filter non-job URLs
                        parts = href.rstrip("/").split("/")
                        if len(parts) < 3:
                            continue

                        if job_url in seen_urls:
                            continue
                        seen_urls.add(job_url)

                        title = link.inner_text().strip()
                        if not title or len(title) < 5:
                            continue

                        # Try to get company + salary from parent
                        company = "N/A"
                        salary = "N/A"
                        parent = link.evaluate_handle("el => el.closest('div')")
                        if parent:
                            try:
                                parent_text = parent.as_element().inner_text()
                                lines = [l.strip() for l in parent_text.split("\n") if l.strip()]
                                # Usually: [Title, Company, Salary range, ...]
                                for line in lines:
                                    if "$" in line or "k" in line.lower():
                                        salary = line
                                    elif line != title and len(line) > 2 and not line.startswith("http"):
                                        company = line
                                        break
                            except Exception:
                                pass

                        jobs.append(Job(
                            id=generate_job_id(self.source_name, job_url),
                            source=self.source_name,
                            url=job_url,
                            title=title,
                            company=company,
                            location="Remote",
                            is_remote=True,
                            salary=salary,
                            tags=[slug.replace("-", " ")],
                            scraped_at=datetime.now().isoformat(),
                            first_seen=datetime.now().isoformat(),
                        ))
                    except Exception:
                        continue

                if len(jobs) >= max_results:
                    break

            browser.close()

        return jobs[:max_results]
