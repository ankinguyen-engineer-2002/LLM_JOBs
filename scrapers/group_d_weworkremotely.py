"""
We Work Remotely scraper — RSS feed for remote jobs.
Covers multiple categories for broad remote job coverage.
"""

import requests
import xml.etree.ElementTree as ET
from scrapers.base import BaseJobScraper
from processor.normalizer import Job, generate_job_id, strip_html
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime


class WeWorkRemotelyScraper(BaseJobScraper):
    source_name = "weworkremotely"

    # RSS feeds by category
    FEEDS = [
        "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
        "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
        "https://weworkremotely.com/categories/remote-data-jobs.rss",
    ]

    def scrape(self, keywords: list[str], max_results: int = 100) -> list[Job]:
        jobs = []
        seen_urls = set()
        cutoff = datetime.now() - timedelta(days=30)

        # Build broad keyword set
        search_terms = set()
        for kw in keywords:
            search_terms.update(kw.lower().split())
        search_terms.update(["data", "engineer", "analytics", "ml", "ai",
                             "machine", "learning", "llm", "prompt",
                             "python", "etl", "dbt", "platform", "nlp",
                             "devops", "cloud", "sql"])

        for feed_url in self.FEEDS:
            try:
                resp = requests.get(feed_url, timeout=15,
                                    headers={"User-Agent": "JobRadar/1.0"})
                if resp.status_code != 200:
                    print(f"[wwr] HTTP {resp.status_code} for {feed_url}")
                    continue

                root = ET.fromstring(resp.content)
                channel = root.find("channel")
                if channel is None:
                    continue

                batch = 0
                for item in channel.findall("item"):
                    title = (item.findtext("title") or "").strip()
                    link = (item.findtext("link") or "").strip()
                    pub_date = item.findtext("pubDate") or ""
                    desc = item.findtext("description") or ""
                    categories = [c.text.lower() for c in item.findall("category") if c.text]

                    if not title or not link or link in seen_urls:
                        continue

                    # Check 30-day cutoff
                    posted_date = ""
                    if pub_date:
                        try:
                            dt = parsedate_to_datetime(pub_date)
                            if dt.replace(tzinfo=None) < cutoff:
                                continue
                            posted_date = dt.strftime("%Y-%m-%d")
                        except Exception:
                            pass

                    # Keyword match
                    searchable = f"{title} {' '.join(categories)} {strip_html(desc)[:200]}".lower()
                    if not any(term in searchable for term in search_terms):
                        continue

                    seen_urls.add(link)

                    # Extract company from title format "Company: Title"
                    company = "N/A"
                    if ":" in title:
                        parts = title.split(":", 1)
                        company = parts[0].strip()
                        title = parts[1].strip()

                    jobs.append(Job(
                        id=generate_job_id(self.source_name, link),
                        source=self.source_name,
                        url=link,
                        title=title,
                        company=company,
                        location="Remote",
                        is_remote=True,
                        salary="N/A",
                        tags=categories[:10],
                        description_snippet=strip_html(desc)[:300],
                        posted_date=posted_date,
                        scraped_at=datetime.now().isoformat(),
                        first_seen=datetime.now().isoformat(),
                    ))
                    batch += 1

                print(f"[wwr] Feed '{feed_url.split('/')[-1]}': {batch} jobs")

            except Exception as e:
                print(f"[wwr] Feed failed: {e}")
                continue

            if len(jobs) >= max_results:
                break

        print(f"[wwr] Total: {len(jobs)} jobs")
        return jobs[:max_results]
