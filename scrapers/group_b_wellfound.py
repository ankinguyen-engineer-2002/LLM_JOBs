"""
Wellfound (AngelList) scraper — RSS/Atom feed.
Feed URL: https://wellfound.com/jobs/feed
"""

import feedparser
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime


class WellfoundScraper(BaseJobScraper):
    source_name = "wellfound"
    FEED_URL = "https://wellfound.com/jobs/feed"

    def scrape(self, keywords: list[str], max_results: int = 50) -> list[Job]:
        feed = feedparser.parse(self.FEED_URL)
        jobs = []

        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "") or entry.get("description", "")

            # Keyword match
            searchable = f"{title} {summary}".lower()
            if not any(kw.lower() in searchable for kw in keywords):
                continue

            url = entry.get("link", "")
            if not url:
                continue

            company = entry.get("author", "N/A") or "N/A"
            # Try to extract company from title like "Title at Company"
            if " at " in title:
                parts = title.rsplit(" at ", 1)
                title = parts[0].strip()
                company = parts[1].strip() if len(parts) > 1 else company

            posted = ""
            if entry.get("published_parsed"):
                try:
                    posted = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
                except Exception:
                    pass

            tags = [t.get("term", "").lower() for t in entry.get("tags", []) if t.get("term")]

            jobs.append(Job(
                id=generate_job_id(self.source_name, url),
                source=self.source_name,
                url=url,
                title=title.strip(),
                company=company,
                location="N/A",
                is_remote=False,
                salary="N/A",
                tags=tags,
                description_snippet=strip_html(summary)[:300],
                posted_date=posted,
                scraped_at=datetime.now().isoformat(),
                first_seen=datetime.now().isoformat(),
            ))

            if len(jobs) >= max_results:
                break

        return jobs
